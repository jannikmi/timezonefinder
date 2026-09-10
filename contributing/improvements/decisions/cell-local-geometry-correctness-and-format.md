# Cell-local geometry: correctness, formats and reproduction method

This is the technical companion to [the findings and reopening conditions](cell-local-geometry-findings.md). The [dated evidence record](../measurements/cell-local-geometry-2026-09-09.json) preserves the measured bytes and inputs. The experiments did not modify the production package or dataset; temporary programs and binary outputs were not promoted into a maintained toolchain. The algorithms, record layouts, witnesses and sampling protocol below preserve the reproduction contract without depending on temporary file paths.

## Two independent failures of naive clipping

The first implementation intersected each candidate polygon, including holes, with a planar polygon joining `h3.cell_to_boundary` coordinates, using Shapely 2.1.2 on coordinates scaled by 10^7. A seeded 512-cell pilot preceded enumeration of all ambiguous shortcuts. Antimeridian cells were excluded rather than silently unwrapped or repaired. No invalid source candidate pairs were encountered in the included census.

To probe curved edges, convert neighboring boundary vertices to unit vectors, normalize their sum and nudge the midpoint toward the cell center by 10^-7. Convert back to longitude/latitude, ask actual `latlng_to_cell` membership, and check the planar clip. Of 185,237 deliberately adversarial probes, 92,266 belonged to the cell but lay outside its planar clip. There were 94,801 candidate-membership disagreements; these are **not a production query error rate or counts of wrong timezone names**.

A witness is cell `0x8400001ffffffff`, original polygon 1234, longitude `38.760102079734025`, latitude `79.3817262348777`: the original runtime contains the point but the floating planar clip does not. H3 constructs cell boundaries through spherical transformations, including vertices at face crossings; see [boundary construction](https://h3geo.org/docs/core-library/cellToBoundaryDesc/) and [gnomonic indexing](https://h3geo.org/docs/core-library/latLngToCellDesc/).

Rounding cut vertices is a separate failure. Probe integer neighbors of interpolated points on clipped edges with fractional endpoints, retain queries assigned to the actual cell, and exclude points within 100 scaled units of the artificial mask boundary. Compare original and rounded-clipped containment with the repository integer kernel and its pure-Python form. Both witnesses below lie about 0.001326 degrees from the artificial seam; the unrounded floating clip agrees with the original.

| Cut-vertex grid | Cell / original polygon | Integer query (longitude, latitude) | Original | Rounded clip |
| --- | --- | --- | --- | --- |
| 10^-7 degrees | 0x8403569ffffffff / 1290 | (-817275056, 830386731) | inside | outside |
| 10^-6 degrees | 0x8403569ffffffff / 1290 | (-817275055, 830386731) | outside | inside |

The integer pairs are authoritative; converting a displayed decimal through floating-point truncation can produce another integer. A cell safety margin cannot fix a moved source edge. Retaining float64 intersections alone is not a proof of exact border behavior either.

## Exact clipping construction

Use axis-aligned windows enclosing each cell and apply four Sutherland-Hodgman half-plane clips independently to each original exterior/hole ring. For endpoints p and q, intersect coordinate axis a at bound b using exact rational `t = (b - p[a]) / (q[a] - p[a])` and `p + t*(q-p)`. Uncut original coordinates remain integers; new coordinates are exact fractions. A vectorized integer-floor cache may accelerate classification, but inherited fractional coordinates must be consulted when comparing against later cutting planes.

For a query strictly inside the window, clipping preserves the ring's odd/even interior and original edge equations. Artificial segments lie on the window boundary. A disconnected intersection may be a weakly simple walk with doubled boundary connectors that cancel in ray parity; this is a containment representation, not a general-purpose polygon export. The predicate retains the package's `(y > y1) != (y > y2)` latitude rule and crossing longitude `>= x`. Artificial vertices can share a query's latitude, so their contributions must use the same convention. Local original boundary geometry is unchanged at valid queries, including source vertices and edge ties.

Keep the exterior first and subtract each surviving hole. An empty exterior is a zero-ring candidate; empty clipped holes contribute nothing and need no records. Keep candidate order and the original shortcut stop index: correctness is not derived from a new cell-dependent precedence rule. Python integers/Fractions make this reference predicate overflow-safe; a native implementation needs its own arithmetic audit.

## Conservative windows and the outstanding proof obligation

Take the largest angular distance between the H3 center and its boundary vertices and add 10^-6 radians. A spherical cap below pi/2 is geodesically convex: enclosing the boundary vertices encloses the minor great-circle arcs and the small cell interior. Latitude limits are center latitude plus/minus radius. If the cap excludes the poles, its longitude half-width is `asin(sin(radius)/cos(center_latitude))`; otherwise retain all longitudes. Round outward to the six-decimal source grid and pad by another source step, including world limits, so valid integer queries remain strictly inside.

Split a cap crossing the antimeridian into two rectangles in the original longitude frame. Do not reinterpret the source polygon's longitude edges. This includes the cells excluded by the naive census and handles pole queries with a full-longitude window.

The argument is analytic, but the implementation used ordinary floating-point trigonometry with an approximately six-meter angular guard. **It was not certified interval arithmetic or a proof of every H3 rounding branch.** Coverage probes sampled minor arcs at fractions 0, 0.25, 0.5 and 0.75, their midpoint perturbations toward/away from the center, and the center itself. Checking those samples does not discharge the numerical proof obligation.

## Serialized exact format

All columns are little-endian, checked for overflow before writing. The base coordinate payload uses the existing block encoder, including bridging vertices and padding; exact exceptions restore every changed coordinate before containment.

| Record/file | Layout |
| --- | --- |
| Window table | uint32 first-window index per compact H3 slot; max uint32 means absent |
| Window | 24 bytes: four int32 bounds, uint32 candidate start, uint16 candidate count/window count |
| Candidate | 12 bytes: uint16 original polygon/zone IDs, uint32 ring start/count |
| Ring | 28 bytes: uint32 vertex count, block start/count, payload word start/count, exception start/count |
| Block | 14 bytes: int32 x base/y minimum/y maximum, uint8 x/y residual widths |
| Exact exception | 28 bytes: uint32 vertex index; int64 numerator and uint32 denominator per coordinate |
| Other files | Packed payload, original shortcut/name files, format identity/version metadata |

The payload's floor-to-source-grid coordinates are **encoding bases, not replacement geometry**. Exceptions include integer intersections off that grid as well as fractions. Exact rational endpoints preserve the retained source edge equation without an external edge table. Stored y ranges describe the coarse encoding base: a future block filter must expand the upper bound by a source step or store conservative exact ranges. Using them unchanged would introduce a new correctness defect. The reference reader restored whole rings; it was not a measured low-memory implementation.

No rotation optimization or nonempty-fragment deduplication was included. The initial naive size model used 128-vertex blocks, independently word-padded bit widths, 14-byte block frames and 28-byte ring metadata, but omitted the costs enumerated in the findings. Do not compare that estimate with a complete encoding as though it were a competing correct file format.

## Lossless sharing format

Retain the original dataset once. Replace repeated fragment coordinates with 16-byte runs: uint32 source ring ID, starting vertex, count, and output offset. The output offset supports random seeking without decoding a variable-length prefix. Split source-ring wraparound into separate runs. A 12-byte ring index stores first run, run count and vertex count. Reuse the exact predecessor's window/candidate records byte for byte.

Boundary IDs address boundary storage. A high source-ID bit plus storage index addresses an inline hole; resolve hole references before choosing that ID. All bits set denotes the new-vertex pool. New vertices use int32 integer-floor pairs with the same 28-byte rational override layout. Fractional points must not match a source vertex merely because their floors coincide. A coordinate match with a source vertex is lossless; selecting another occurrence of an identical coordinate may split runs but cannot change the reconstructed geometry.

The shared writer reconstructed every ring and compared canonical coordinate fingerprints against the exact predecessor: integer floors plus canonical nonintegral values. All rings matched, establishing representation equivalence rather than only agreement at sampled queries. The recorded source manifest hashes identify the original dataset; the experimental reader did not enforce them independently. Release pairing must be enforced before production use. Its 64-entry source-ring cache and eager exception dictionary are reference-code choices, not memory claims.

## Reproducing the measurements

Use the recorded source commit, dataset hashes and fixture hashes, not an arbitrary newer release. Enumerate ambiguous `shortcuts.items()` entries, retaining every candidate even if normal lookup can eliminate it. For the exact census, write all windows, candidates and nonempty rings; then reload every ring and compare exact coordinate fingerprints before testing queries. On the seeded 512-cell detailed subset, probe retained vertices, exact edge midpoints and their integer neighbors; compare candidate membership with `inside_of_polygon`. Replay all four committed benchmark fixture strata with the original stop rule and metadata loaded from the artifact. Test exact poles at longitudes spaced by 15 degrees and both antimeridian representations at latitudes spaced by 5 degrees. These replay methods complement, rather than replace, the geometric argument.

For timing, wrap the whole current lookup and whole shared-oracle lookup with `perf_counter_ns` inside `benchmarks/candidate_comparison.py`'s paired harness. Seed 20260909; seven rounds; 5,000 identical replacement draws per arm/round; discard one warm-up batch per arm. Assertions and timing-list bookkeeping occur after the stop timestamp. Compute each round's 99th percentile, then report the median of those seven values and their spread. Do not substitute the harness's mean-throughput verdict. Construction is outside timing; reconstruction during a query is inside. Preserve the Python/C backend distinction and the limitations in the findings when interpreting a repeat.
