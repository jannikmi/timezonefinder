#include "inside_polygon_int.h"
#include <stdint.h>
#include <stdio.h>

// One step of the grid the source data is published on, in the
// tenth-of-a-microdegree units a coordinate is stored in. Mirrors
// SOURCE_COORD_STEP in timezonefinder/configs.py, which is where it is
// explained; a packed residual counts these rather than storage steps, which is
// what makes the fields ~3.3 bits narrower.
#define SOURCE_COORD_STEP 10

// The slope comparison below needs 63 bits (see the overflow note in
// inside_polygon_int), and `long` does not supply them everywhere: it is 64
// bits on LP64 (Linux, macOS) and 32 on LLP64 (Windows), which this package
// ships wheels for. int64_t is the width the arithmetic actually requires, on
// every platform.

bool inside_polygon_int(int x, int y, int nr_coords, int x_coords[],
                        int y_coords[]) {
  // naive implementation, vulnerable to overflow:
  //  bool inside;
  //  for (int i = 0, j = nr_coords - 1; i < nr_coords; j = i++) {
  //    if (((y_coords[i] > y) != (y_coords[j] > y)) &&
  //        (x < (x_coords[j] - x_coords[i]) * (y - y_coords[i]) /
  //                     (y_coords[j] - y_coords[i]) +
  //                 x_coords[i])) {
  //      inside = !inside;
  //    }
  //  }
  //  return inside;

  bool inside, y_gt_y1, y_gt_y2, x_le_x1, x_le_x2;
  int64_t y1, y2, x1, x2, slope1, slope2; // see the width note above
  int i, j;

  inside = false;
  // the edge from the last to the first point is checked first
  j = nr_coords - 1;
  y_gt_y1 = y > y_coords[j];
  for (i = 0; i < nr_coords; j = i++) {
    y_gt_y2 = y > y_coords[i];
    if (y_gt_y1 ^ y_gt_y2) { // XOR
      // [p1-p2] crosses horizontal line in p
      // only count crossings "right" of the point ( >= x)
      x_le_x1 = x <= x_coords[j];
      x_le_x2 = x <= x_coords[i];
      if (x_le_x1 || x_le_x2) {
        if (x_le_x1 && x_le_x2) {
          // p1 and p2 are both to the right -> valid crossing
          inside = !inside;
        } else {
          // compare the slope of the line [p1-p2] and [p-p2]
          // depending on the position of p2 this determines whether
          // the polygon edge is right or left of the point
          // to avoid expensive division the divisors (of the slope dy/dx)
          // are brought to the other side ( dy/dx > a  ==  dy > a * dx )
          // only one of the points is to the right
          // NOTE: int64 precision required to prevent overflow
          y1 = y_coords[j];
          y2 = y_coords[i];
          x1 = x_coords[j];
          x2 = x_coords[i];
          slope1 = (y2 - y) * (x2 - x1);
          slope2 = (y2 - y1) * (x2 - x);
          // NOTE: accept slope equality to also detect if p lies directly
          // on an edge
          if (y_gt_y1) {
            if (slope1 <= slope2) {
              inside = !inside;
            }
          } else { // NOT y_gt_y1
            if (slope1 >= slope2) {
              inside = !inside;
            }
          }
        }
      }
    }
    // next point
    y_gt_y1 = y_gt_y2;
  }
  return inside;
}

// One residual out of a block's axis region.
//
// The field is `width` bits wide and starts at bit `k * width` of `region`,
// least significant bit first. A payload is a stream of 32-bit words and every
// region begins on a word boundary, so a field - at most 32 bits wide,
// beginning at most 31 bits into a word - always lies inside two consecutive
// words. That is the whole reason for the word alignment: the byte-addressed
// form of this read is five dependent byte loads, which measured 2.2x the whole
// kernel on the numba backend. Reading the word after the last field is what
// PAYLOAD_PADDING_WORDS exists for.
static uint32_t residual_at(unsigned int region[], int width, int k) {
  uint64_t bit, chunk;

  if (width == 0) {
    return 0; // an axis the block is constant on occupies no words at all
  }
  bit = (uint64_t)k * (uint64_t)width;
  region += bit >> 5;
  chunk = (uint64_t)region[0] | ((uint64_t)region[1] << 32);
  return (uint32_t)((chunk >> (bit & 31)) & (((uint64_t)1 << width) - 1));
}

bool inside_polygon_packed_int(int x, int y, int nr_coords, int block_size,
                               int block_start, int nr_blocks,
                               unsigned int payload[], int block_ranges[],
                               int block_bases[], unsigned char block_widths[],
                               unsigned int block_payload_offsets[]) {
  // inside_polygon_blocked_int over the packed payload of polygon layout 3.
  //
  // Same filter, same predicate, same answer: a block whose [min, max] latitude
  // excludes y holds no edge that can flip parity, and the surviving blocks are
  // tested in their own coordinate frame instead of in absolute coordinates.
  // Translating the query into that frame is exact because every quantity the
  // predicate forms is a difference of two coordinates - x2 - xq below *is*
  // x2_absolute - x - so the frame origin is never added back per vertex and
  // the arithmetic stays inside the same int64 bounds inside_polygon_int
  // documents.
  //
  // A block stores its bridging vertex, so both endpoints of every edge it owns
  // are inside it and no edge needs two frames. That is why the loop runs over
  // the block's own n edges with no wrap-around case: the wrap is already
  // encoded, as the last block's bridging vertex being vertex 0.
  //
  // Every array here belongs to the whole *collection*, and `block_start` is
  // where this ring's blocks begin in it; `payload` is the whole coordinate
  // buffer, which the per-block offsets address absolutely. Nothing is sliced
  // per call, because the caller would have to rebuild a buffer handle per
  // point-in-polygon test to do it - 0.30 us each through cffi, against the
  // ~1.5 us the whole test costs.

  bool inside, y_gt_y1, y_gt_y2, x_le_x1, x_le_x2;
  int64_t xq, yq, y1, y2, x1, x2, slope1, slope2; // see the width note above
  unsigned int *x_region, *y_region;
  int b, k, n, width_x, width_y;

  inside = false;
  for (b = block_start; b < block_start + nr_blocks; b++) {
    if (y < block_ranges[2 * b] || y > block_ranges[2 * b + 1]) {
      continue;
    }
    n = nr_coords - (b - block_start) * block_size;
    if (n > block_size) {
      n = block_size;
    }
    width_x = block_widths[2 * b];
    width_y = block_widths[2 * b + 1];
    x_region = payload + block_payload_offsets[b];
    // the y region follows the word-aligned x one; n + 1 values are stored per
    // axis
    y_region = x_region + (((n + 1) * width_x + 31) >> 5);
    xq = (int64_t)x - (int64_t)block_bases[b];
    // the y frame origin is the latitude index's own lower bound, already read
    // above to decide whether this block survives at all - so it costs nothing
    // here and is not stored a second time (see
    // timezonefinder/block_payload.py)
    yq = (int64_t)y - (int64_t)block_ranges[2 * b];

    // A residual counts source grid steps (see
    // timezonefinder/block_payload.py), so it is scaled back into coordinate
    // units here; the predicate below is then the same arithmetic on the same
    // numbers the unpacked kernel sees.
    y1 = SOURCE_COORD_STEP * (int64_t)residual_at(y_region, width_y, 0);
    y_gt_y1 = yq > y1;
    for (k = 0; k < n; k++) {
      y2 = SOURCE_COORD_STEP * (int64_t)residual_at(y_region, width_y, k + 1);
      y_gt_y2 = yq > y2;
      if (y_gt_y1 ^ y_gt_y2) { // XOR
        // the x residuals are read only here, on the edges that survive the
        // latitude test, which is what keeps unpacking off the common path
        x1 = SOURCE_COORD_STEP * (int64_t)residual_at(x_region, width_x, k);
        x2 = SOURCE_COORD_STEP * (int64_t)residual_at(x_region, width_x, k + 1);
        x_le_x1 = xq <= x1;
        x_le_x2 = xq <= x2;
        if (x_le_x1 || x_le_x2) {
          if (x_le_x1 && x_le_x2) {
            inside = !inside;
          } else {
            // NOTE: int64 precision required to prevent overflow
            slope1 = (y2 - yq) * (x2 - x1);
            slope2 = (y2 - y1) * (x2 - xq);
            // NOTE: accept slope equality to also detect if p lies directly
            // on an edge
            if (y_gt_y1) {
              if (slope1 <= slope2) {
                inside = !inside;
              }
            } else { // NOT y_gt_y1
              if (slope1 >= slope2) {
                inside = !inside;
              }
            }
          }
        }
      }
      // next edge of this block; the next block re-seeds this
      y1 = y2;
      y_gt_y1 = y_gt_y2;
    }
  }
  return inside;
}
