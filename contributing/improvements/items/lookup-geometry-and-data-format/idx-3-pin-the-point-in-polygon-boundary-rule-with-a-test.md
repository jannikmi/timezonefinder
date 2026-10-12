# IDX-3 — pin the point-in-polygon boundary rule with a test

- **Location:** the point-in-polygon kernels — `pt_in_poly_python` and `pt_in_poly_packed` in `timezonefinder/utils_numba.py`, compiled and interpreted, and `pt_in_poly_clang` and `pt_in_poly_clang_packed` in `timezonefinder/utils_clang.py`.
- **What it is:** which polygon owns a point exactly on its boundary follows from the ray cast's comparisons alone — a polygon owns it when its interior lies immediately west of the point, or immediately south along an east–west edge — and nothing pins that: `tests/utils_test.py` comments its boundary cases out as undefined. [IDX-6](idx-6-replace-the-h3-shortcut-index-with-the-grid-tree.md)'s exactness rests on the rule, and so already does the ordering gate in `scripts/shortcut_ordering.py`, which lets zones that touch be reordered.
- **Size:** S.
- **Status:** open — the first slice of the H3 index's replacement.
