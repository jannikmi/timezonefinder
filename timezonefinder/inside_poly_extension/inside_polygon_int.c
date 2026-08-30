#include "inside_polygon_int.h"
#include <stdint.h>
#include <stdio.h>

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

bool inside_polygon_blocked_int(int x, int y, int nr_coords, int x_coords[],
                                int y_coords[], int nr_blocks,
                                int block_ranges[], int block_size) {
  // inside_polygon_int with the blocks the ray cannot cross skipped.
  //
  // block_ranges holds this ring's [min, max] latitude per block of block_size
  // vertices, as two ints per block. Ray casting flips parity only on an edge
  // spanning y - (y > y1) ^ (y > y2) is exactly min(y1,y2) < y <= max(y1,y2) -
  // and every edge lies inside the range of the block owning its first vertex,
  // so a block whose range excludes y holds nothing that can flip parity.
  // Parity is a sum mod 2 over independent per-edge predicates, so skipping a
  // block (or visiting blocks in any order) cannot change the result. The
  // predicate below is inside_polygon_int's, unchanged; only which edges it
  // runs on differs.
  //
  // The y_gt_y1 carry of the unblocked loop above is deliberately not kept: it
  // is only valid between consecutive edges, and a skipped block breaks that
  // adjacency. Recomputing one comparison per edge is what the skipping buys
  // many times over.

  bool inside, y_gt_y1, y_gt_y2, x_le_x1, x_le_x2;
  int64_t y1, y2, x1, x2, slope1, slope2; // see the width note above
  int b, i, j, start, stop;

  inside = false;
  for (b = 0; b < nr_blocks; b++) {
    if (y < block_ranges[2 * b] || y > block_ranges[2 * b + 1]) {
      continue;
    }
    start = b * block_size;
    stop = start + block_size;
    if (stop > nr_coords) {
      stop = nr_coords;
    }
    // Only a block's first vertex needs its comparison made from scratch:
    // inside a block consecutive edges still share a vertex, so the rest carry
    // exactly as the unblocked loop's do. It is the block *boundary* that
    // breaks that adjacency, so the carry is re-seeded per block rather than
    // abandoned - which halves the work on the edges that survive the filter.
    y_gt_y1 = y > y_coords[start];
    for (i = start; i < stop; i++) {
      // the edge leaving vertex i, wrapping to vertex 0 on the very last one
      j = i + 1;
      if (j == nr_coords) {
        j = 0;
      }
      y_gt_y2 = y > y_coords[j];
      if (y_gt_y1 ^ y_gt_y2) { // XOR
        x_le_x1 = x <= x_coords[i];
        x_le_x2 = x <= x_coords[j];
        if (x_le_x1 || x_le_x2) {
          if (x_le_x1 && x_le_x2) {
            inside = !inside;
          } else {
            // NOTE: int64 precision required to prevent overflow
            y1 = y_coords[i];
            y2 = y_coords[j];
            x1 = x_coords[i];
            x2 = x_coords[j];
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
      // next edge of this block; the next block re-seeds this
      y_gt_y1 = y_gt_y2;
    }
  }
  return inside;
}
