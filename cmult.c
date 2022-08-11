#include <stdio.h>
#include "cmult.h"

bool cmult(long x, long y, long nr_coords, long x_coords[], long y_coords[]) {
    bool inside = false;
    for (int i = 0, j = nr_coords - 1; i < nr_coords; j = i++)
    {
        if (((y_coords[i] > y) != (y_coords[j] > y)) &&
          (x < (x_coords[j] - x_coords[i]) * (y - y_coords[i]) / (y_coords[j] - y_coords[i]) + x_coords[i])) {
            inside = !inside;
        }
    }
    return inside;
}
