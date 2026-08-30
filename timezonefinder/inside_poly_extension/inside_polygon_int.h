#include <stdbool.h>

bool inside_polygon_int(int x, int y, int nr_coords, int x_coords[],
                        int y_coords[]);

bool inside_polygon_blocked_int(int x, int y, int nr_coords, int x_coords[],
                                int y_coords[], int nr_blocks,
                                int block_ranges[], int block_size);
