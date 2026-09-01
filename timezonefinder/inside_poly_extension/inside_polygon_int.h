#include <stdbool.h>

bool inside_polygon_int(int x, int y, int nr_coords, int x_coords[],
                        int y_coords[]);

bool inside_polygon_packed_int(int x, int y, int nr_coords, int block_size,
                               int block_start, int nr_blocks,
                               unsigned int payload[], int block_ranges[],
                               int block_bases[], unsigned char block_widths[],
                               unsigned int block_payload_offsets[]);
