window.BENCHMARK_DATA = {
  "lastUpdate": 1786018109329,
  "repoUrl": "https://github.com/jannikmi/timezonefinder",
  "entries": {
    "timezone lookup (clang, min)": [
      {
        "commit": {
          "author": {
            "email": "github@michelfe.it",
            "name": "Jannik Kissinger",
            "username": "jannikmi"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "72ea6452cd0421d7fd8e7f670038327aef599f69",
          "message": "Add benchmark CI workflow with noise-derived alert threshold (#454)\n\n* Add benchmark CI workflow with noise-derived alert threshold\n\nImplements plan 03 (closes #150). Continuous benchmarking of the tracked\ncore subset on every PR and every push to master, kept entirely separate\nfrom the release/publish pipeline in build.yml.\n\nFork-PR safety: the measuring job holds no write permissions and no\nsecrets, so it behaves identically for branch and fork PRs. The privileged\ncomparison comment is posted by a separate workflow_run-triggered workflow\nrunning the base repo's own definition. pull_request_target was rejected -\nit would grant write permissions alongside untrusted PR code, which is not\na trade a package published to PyPI should make.\n\nRunner noise: the tracked value is pytest-benchmark's min rather than its\nmean, since every round performs an identical fixed batch of work. The\naction's pytest extractor only reads stats.ops (= 1/mean), so\nscripts/normalize_benchmark_json.py rewrites ops/mean from the chosen\nestimator, leaving an ordinary pytest-benchmark JSON the action still\nparses natively. scripts/benchmark_noise.py + `make benchmark-noise`\nderive the alert threshold from repeated identical runs; until that has\nbeen measured on this repo's runners the shipped threshold is provisional\nand fail-on-alert stays false.\n\nAcceleration path: CI tracks the no-numba/clang configuration and asserts\nit via scripts/assert_acceleration_path.py rather than assuming it - a\nsilent numba install would corrupt the whole trend history.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Track a globally representative benchmark set\n\nThe tracked core benchmark was ambiguous_shortcut-in_memory alone - a\nworst-case workload, not a representative one. It weighted the most\nexpensive path as if it were all of the traffic and made unique-shortcut\nimprovements invisible.\n\nThe core set is now the uniformly-random headline plus the two per-class\ndiagnostics. Measured: a unique lookup costs 1.19us, an ambiguous one\n8.75us (7.4x), so ambiguous work takes ~72% of the wall clock despite\nbeing ~25% of the queries. The random headline therefore weights a change\nby how much real query load it helps; the per-class benchmarks show a\nunique-path win undiluted and attribute a change to a path.\n\nThe random fixture was also not uniform over the globe: lat ~ U(-90, 90)\noversampled the poles 2.5x (33.3% of points beyond 60 deg latitude vs\n13.4% area-uniform), inflating the ambiguous share to 30.5% where the\nshortcut index implies 25.5%. Benchmark fixtures now draw from a new\narea-weighted sampler; the regenerated fixtures measure 13.2% and 26.0%.\nget_rnd_query_pt is deliberately unchanged - correctness and fuzz tests\nbenefit from the polar edge cases.\n\nFIXTURE_VERSION was written into metadata.json and never read, and the\nloader validated only DEBUG and DATA_VERSION - so new generator code with\nstale committed fixtures loaded cleanly and benchmarked a workload nobody\nhad described. The loader now enforces both FIXTURE_VERSION and the\nrecorded point_sampler, and a distribution test fails if the pole-biased\nsampler is ever reinstated.\n\nBATCH_SIZE 1,000 -> 2,500: the unique benchmark is the shortest and so the\nnoisiest in relative terms, and the noisiest sets the single shared alert\nthreshold. More rounds cannot help when the tracked estimator is the min.\n\nThe alert threshold still has to be re-derived against the new set.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Assert the constants shared by the two benchmark workflows agree\n\nGitHub Actions workflows cannot import constants from each other, so\nBENCHMARK_SUITE_NAME, ALERT_THRESHOLD and REPORT_FILENAME are duplicated\nliterally in benchmark.yml and benchmark-comment.yml, held together by\nnothing but a \"must match\" comment. A one-sided edit has no failure mode:\nthe comparison job looks up a suite name or a filename that no longer\ncorresponds to what the measuring job produced and silently compares\nagainst nothing.\n\ntests/test_benchmark_workflows.py parses both workflows and asserts the\nshared env constants match, that the trend data location agrees, and that\nthe artifact both consumers download is the one the measure job uploads.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Re-derive the alert threshold for the three-benchmark core set\n\nThe 130% threshold came from 5 runs of the ambiguous benchmark alone.\nRe-measured against the new core set - 5 runs of identical code on 5\nseparate ubuntu-latest runners - the spread is at most 106.8%:\n\n  random    106.8%  (CV 2.7%)\n  unique    105.0%  (CV 1.6%)\n  ambiguous 104.9%  (CV 1.7%)\n\nWorst spread + 20% headroom rounds to 110%, which is also the floor\nbenchmark_noise.py will suggest. The larger BATCH_SIZE is what bought the\nresolution: the shortest benchmark turned out to be the least noisy of the\nthree, not the most, so the batch was sized correctly. fail-on-alert stays\nfalse until the trend chart confirms this holds over time.\n\nAlso corrects the cost ratio quoted in the docs and the benchmark comment.\nThe ~7.4x / ~72% figures were measured locally with numba; CI tracks the\nclang path, where an ambiguous lookup costs ~14x a unique one and takes\n~83% of the wall clock - so a unique-path win moves the headline by ~0.17x\nits true size, not ~0.28x. The case for tracking the per-class diagnostics\nis stronger, not weaker.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Stamp the benchmark reports with their input provenance\n\ndocs/benchmark_results_*.rst named the machine and batch size behind\ntheir numbers but not the workload: regenerating the fixtures or\nupdating the boundary data left the committed reports describing\ninputs that no longer existed, with nothing in the file to say so.\nThe numbers stay plausible, so nothing flags them.\n\nRecord fixture_version and data_version into machine_info through the\nexisting pytest_benchmark_update_machine_info hook, alongside the\nnumba/clang flags and batch size already threaded that way, and render\nthem under System Status.\n\nThe values come from the fixture loader's own validated metadata\nrather than a second read of the files, so a fixture set out of sync\nwith the checkout fails the benchmark run instead of being stamped\ninto a report. Reading them back is loud on absence, mirroring\nget_batch_size(): a JSON predating the fields fails to render rather\nthan silently producing an unstamped report, which is the failure\nthis stamp exists to prevent.\n\nThe changelog entry for this landed in 583f062 by way of a concurrent\nstaging overlap.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Condense the unreleased changelog to its end state\n\nThe benchmark work was described across 15 bullets that narrated their\nown development: fixtures added, then pinned, then re-sampled; the alert\nthreshold set to 130%, then re-derived to 110%. Collapse them into seven\nbullets describing where the code landed, dropping superseded values and\nreview-round narration.\n\nAdd the rules that keep it that way to CLAUDE.md: amend the existing\nbullet rather than appending a correcting one, one bullet per\nuser-visible change, final values instead of tuning history.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n---------\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-05T01:59:28+02:00",
          "tree_id": "1ccf029689a40bd3da20accd3fbef75a209ff365",
          "url": "https://github.com/jannikmi/timezonefinder/commit/72ea6452cd0421d7fd8e7f670038327aef599f69"
        },
        "date": 1785888682636,
        "tool": "pytest",
        "benches": [
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[random-in_memory]",
            "value": 61.33135028632948,
            "unit": "iter/sec",
            "range": "stddev: 0.00008241621190456379",
            "extra": "mean: 16.304875000002994 msec\nrounds: 54"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[unique_shortcut-in_memory]",
            "value": 289.84893942855547,
            "unit": "iter/sec",
            "range": "stddev: 0.00005350981758861343",
            "extra": "mean: 3.450072999996223 msec\nrounds: 228"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[ambiguous_shortcut-in_memory]",
            "value": 19.436601343881733,
            "unit": "iter/sec",
            "range": "stddev: 0.0015613569380360651",
            "extra": "mean: 51.44932399998936 msec\nrounds: 50"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "github@michelfe.it",
            "name": "Jannik Kissinger",
            "username": "jannikmi"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "5947b1b720b58bf9fcbfefb58187b80ec2340a64",
          "message": "Store polygon coordinates one axis at a time (#449) (#457)\n\n* Store polygon coordinates one axis at a time (#449)\n\nPolygon coordinates move from interleaved [x0,y0,x1,y1,...] to per-axis\nblocks [x0...xN-1, y0...yN-1] inside the same coords:[int] vector. The\nraycasting point-in-polygon scan touches one axis at a time, so per-axis\nblocks keep cache lines fully used and let both acceleration backends read\nan axis without copying: ~2.5x faster on the largest polygons and ~1.6x on\na median one via the C extension, 14-25% via Numba.\n\nThe clang wrapper's two ascontiguousarray calls are deleted rather than\nleft as no-ops: in place they are a silent fallback that would let a future\nstrided producer keep returning correct answers while copying on every PIP\ncall. The numba signature changes from \"F\" to \"C\" order, which is a hard\nrequirement - the signature is eager, so an F-ordered array is rejected at\ncall time.\n\nThe layout change is a pure permutation inside an unchanged container, so\nan old coordinates.fbs read by the new code parses cleanly and returns\nwrong timezones with no error. coordinates.fbs therefore now carries a\nFlatBuffers file identifier and a layout_version, checked once per accessor\nconstruction in get_polygon_collection. bin_file_location is documented\npublic API, so the affected population is real; the guard converts silent\ncorruption into a startup error naming the offending file.\n\nThe bundled data was regenerated from the pinned 2026c release. Verified\nlossless: a re-parse reproduces every output file except the two\ncoordinates.fbs, each exactly 16 bytes larger (identifier + one vtable\nslot), every polygon compares equal against the old blobs read from git,\nand 30,000 fixture points produce byte-identical timezone_at /\ntimezone_at_land / TimezoneFinderL results before and after.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Stop `make flatbuf` from wiping hand-maintained __init__.py files\n\nflatc derives its output path from the schema namespace and writes an empty\n__init__.py at *every* level of it, overwriting existing ones. Generating\nwith `-o .` therefore emptied timezonefinder/__init__.py - the entire public\nAPI surface - along with flatbuf/__init__.py and generated/__init__.py.\n\nThe target now generates into a scratch tree and copies back only the three\ngenerated packages, so the blast radius is exactly what it is meant to\nregenerate.\n\nIt also runs the pre-commit formatters afterwards. The committed bindings are\nflatc output after ruff-format and pyupgrade, so a bare regeneration left a\ndiff in which all 13 files churned on formatting and a real codegen change was\ninvisible.\n\nCLAUDE.md claimed the __all__ lists are test-checked; nothing references them.\nCorrected to state the actual, incidental protection: tests/conftest.py\nimports from the top-level package, so emptying it fails collection outright.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Correct the documented data compatibility contract\n\nThe guard keys on POLYGON_LAYOUT_VERSION, a hand-maintained literal that is\nbumped only when the coordinate encoding changes. It has no connection to the\npackage version, so data compiled by any release writing a given layout stays\nreadable by any release reading it.\n\nThe docs said the opposite - that a bin_file_location directory must be\ncompiled by the same timezonefinder version that reads it. That describes a\nper-release regeneration obligation the code does not impose, and would have\npushed users into regenerating ~65MB on every patch bump.\n\nRestate the actual contract in docs/1_usage.rst, docs/data_format.rst and the\nchangelog: regeneration is needed once here because this release does change\nthe encoding, and thereafter only when the changelog reports a format change.\nAlso note in data_format.rst that the check covers the coordinate files only -\nthe shortcut index and NumPy arrays carry no marker yet (#458).\n\nThe error message led with \"written by an incompatible timezonefinder version\",\nwhich pointed the reader at the release rather than the encoding. It now names\nthe two layout versions as the mismatch.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Document that committed generated files are post-pre-commit output\n\nThree times in one migration a diff taken straight after regenerating was\nmisread: `make flatbuf` churned all 13 binding files on formatting alone and\nhid the real codegen change; `hole_registry.json` appeared modified because\npretty-format-json sorts keys the converter emits in insertion order; and\ndocs/data_report.rst always looks dirty because the reporting script emits\ntrailing whitespace the hooks strip.\n\nAll three are the same mistake - comparing raw generator output against\ncommitted bytes that have been through pre-commit. Add a Generated Files\nsection naming each generator and the hook that rewrites its output, with the\nrule: run `make hook` before reading any diff meant to prove a regeneration\nchanged nothing.\n\nAlso correct the Development Setup bullet, which advertised \"custom FlatBuffers\nand unused-Numba checks\" in `make hook`. Neither exists; every hook in\n.pre-commit-config.yaml is a stock one.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Emit pre-commit-clean output from the data pipeline\n\nBoth generators produced files that the hooks then rewrote, so every\n`make parse`/`make reports` left hole_registry.json and docs/data_report.rst\nlooking modified until `make hook` had run - masking whether a re-parse had\nactually changed anything.\n\nwrite_json now sorts keys the way pretty-format-json does. The subtlety is that\nthe registry's keys are ints in memory: sorting those directly yields numeric\norder (16, 26, 1165), while the hook re-reads the file - where JSON keys are\nnecessarily strings - and sorts lexicographically (\"1165\", \"16\", \"26\"). So the\nkeys are stringified before sorting.\n\nscripts/reporting.py no longer emits `   * - ` with a dangling space for the\nempty cells of spacer rows, and trims the trailing blank line the last table\nleaves behind.\n\nVerified end to end: a full re-parse now produces hole_registry.json\nbyte-identical to the committed file, and docs/data_report.rst regenerates\nbyte-identical, both with no hook run. Neither committed file changes - they\nwere already in the normalised form the hooks imposed.\n\nRegression tests for both in tests/utils_test.py, since the failure mode is\ninvisible until a diff surprises someone months later. CLAUDE.md's Generated\nFiles section now states the invariant to maintain rather than listing traps to\nwork around.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n---------\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-06T01:28:47+02:00",
          "tree_id": "938021b53ab6346d823bc002b0b80e402cc0810c",
          "url": "https://github.com/jannikmi/timezonefinder/commit/5947b1b720b58bf9fcbfefb58187b80ec2340a64"
        },
        "date": 1785972584909,
        "tool": "pytest",
        "benches": [
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[random-in_memory]",
            "value": 69.34893554934533,
            "unit": "iter/sec",
            "range": "stddev: 0.0017872343498658045",
            "extra": "mean: 14.419831999994415 msec\nrounds: 60"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[unique_shortcut-in_memory]",
            "value": 229.5851717367877,
            "unit": "iter/sec",
            "range": "stddev: 0.00013617321835197052",
            "extra": "mean: 4.355681999996364 msec\nrounds: 187"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[ambiguous_shortcut-in_memory]",
            "value": 23.841384413884363,
            "unit": "iter/sec",
            "range": "stddev: 0.005321676764769119",
            "extra": "mean: 41.943872999993914 msec\nrounds: 50"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "github@michelfe.it",
            "name": "Jannik Kissinger",
            "username": "jannikmi"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "94a5f3e169f6ba7982f24f2653b453823404aed4",
          "message": "Type-check the whole package except generated bindings (#459)\n\n* Type-check the whole package except generated bindings\n\nmypy's `ignore_errors` list covered seven hand-written modules alongside the\n`flatc` output: coord_accessors, polygon_array, np_binary_helpers, utils_numba,\nutils_clang, _numba_replacements and flatbuf.io.*. `ignore_errors` silences\n*every* error in a module, so roughly 800 lines of real logic were not type\nchecked at all - a `def f() -> int: return \"x\"` dropped into coord_accessors\nstill made `mypy timezonefinder` report \"Success\".\n\nAll seven pass once the exemption is lifted, bar three findings fixed here:\n\n- `AbstractCoordAccessor.__getitem__` and `read_polygon_array_from_binary`\n  declared `idx: int`, but polygon ids reach them as numpy integers straight\n  out of the shortcut arrays. Widened to `IntegerLike` rather than converting\n  at the call site, which would cost a conversion per candidate polygon on the\n  lookup fast path.\n- `FileCoordAccessor.coord_file` was annotated `object`, which says nothing;\n  `.fileno()` only type-checked because mypy narrows locally within `__init__`.\n- `ffi.from_buffer` trips a `types-cffi`/numpy stub gap - ignored at the two\n  offending lines with a note, rather than for the whole module.\n\nTwo `__del__` methods also gained `-> None`: without a single annotation mypy\nskips a function body even with the module exemption gone, so un-exempting\nthem would otherwise have bought nothing.\n\ntests/test_mypy_config.py keeps the list restricted to generated packages,\nsince appending a module is the cheapest way to make a real error disappear.\n\nAnnotations, comments and config only - the bytecode of every per-call\nfunction on the lookup path is unchanged.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Add changelog entry for the mypy coverage change\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n---------\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-06T01:48:02+02:00",
          "tree_id": "83a00f11757474768b3fc902cc5fa216a67e543e",
          "url": "https://github.com/jannikmi/timezonefinder/commit/94a5f3e169f6ba7982f24f2653b453823404aed4"
        },
        "date": 1785973739503,
        "tool": "pytest",
        "benches": [
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[random-in_memory]",
            "value": 81.20414046922033,
            "unit": "iter/sec",
            "range": "stddev: 0.00028586064967666954",
            "extra": "mean: 12.314642999996295 msec\nrounds: 60"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[unique_shortcut-in_memory]",
            "value": 251.41597476974383,
            "unit": "iter/sec",
            "range": "stddev: 0.000043821879463010236",
            "extra": "mean: 3.9774720000025354 msec\nrounds: 213"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[ambiguous_shortcut-in_memory]",
            "value": 27.672954930576957,
            "unit": "iter/sec",
            "range": "stddev: 0.00028238160771667424",
            "extra": "mean: 36.13636500000439 msec\nrounds: 50"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "github@michelfe.it",
            "name": "Jannik Kissinger",
            "username": "jannikmi"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "86f23fd2403adbe468f438f7f15ce384a49f709a",
          "message": "Link the benchmark trend chart from the docs (#460)\n\nThe chart github-action-benchmark publishes to gh-pages was reachable\nonly at /dev/bench/, and that URL appeared nowhere in the repo -\nCONTRIBUTING.md described the location in prose without linking it, so\nthe natural guess (the Pages root) 404s.\n\nLink it from the README and docs/index.rst reference lists, from the\nPerformance page next to the static per-data-update tables, and turn the\nCONTRIBUTING sentence into an actual link that also names\nbenchmark-data-dir-path and marks dev/bench as action-owned.\n\nThe Performance page notes that CI measures the default installation\n(C extension, no Numba) on shared runners, so its absolute numbers are\nnot comparable to the committed tables.\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-06T02:03:20+02:00",
          "tree_id": "c051c59015f06fb8af35921a79f98f92e068c8e9",
          "url": "https://github.com/jannikmi/timezonefinder/commit/86f23fd2403adbe468f438f7f15ce384a49f709a"
        },
        "date": 1785974649662,
        "tool": "pytest",
        "benches": [
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[random-in_memory]",
            "value": 72.96772126915656,
            "unit": "iter/sec",
            "range": "stddev: 0.000351248780909782",
            "extra": "mean: 13.7046899999973 msec\nrounds: 60"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[unique_shortcut-in_memory]",
            "value": 225.64154403802675,
            "unit": "iter/sec",
            "range": "stddev: 0.00006687011271233858",
            "extra": "mean: 4.4318079999996485 msec\nrounds: 176"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[ambiguous_shortcut-in_memory]",
            "value": 24.435867454967106,
            "unit": "iter/sec",
            "range": "stddev: 0.0003958112982050958",
            "extra": "mean: 40.92345000000108 msec\nrounds: 50"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "github@michelfe.it",
            "name": "Jannik Kissinger",
            "username": "jannikmi"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "3d9c1f7d6801e10a670d42cfaf590a381a772e84",
          "message": "Collapse the uint8/uint16 shortcut schema dispatch into one registry (#461)",
          "timestamp": "2026-08-06T09:05:56+02:00",
          "tree_id": "dcaebafeb3ecbc5a0683acf2ca8edafac1e25565",
          "url": "https://github.com/jannikmi/timezonefinder/commit/3d9c1f7d6801e10a670d42cfaf590a381a772e84"
        },
        "date": 1786000030780,
        "tool": "pytest",
        "benches": [
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[random-in_memory]",
            "value": 73.54273597793839,
            "unit": "iter/sec",
            "range": "stddev: 0.00015409488121831012",
            "extra": "mean: 13.597536000020227 msec\nrounds: 61"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[unique_shortcut-in_memory]",
            "value": 231.00540714274769,
            "unit": "iter/sec",
            "range": "stddev: 0.00008987398869743909",
            "extra": "mean: 4.328903000015316 msec\nrounds: 195"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[ambiguous_shortcut-in_memory]",
            "value": 25.112727265791364,
            "unit": "iter/sec",
            "range": "stddev: 0.00037062811069100786",
            "extra": "mean: 39.820445999993126 msec\nrounds: 50"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "github@michelfe.it",
            "name": "Jannik Kissinger",
            "username": "jannikmi"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "fcba8d7db491ec857bf12feff3cc1efe2c363bb2",
          "message": "Compare benchmarks on one runner instead of across the pool (#462)",
          "timestamp": "2026-08-06T09:30:52+02:00",
          "tree_id": "b1f610da761b2870011a4dbfdb06e3795980f168",
          "url": "https://github.com/jannikmi/timezonefinder/commit/fcba8d7db491ec857bf12feff3cc1efe2c363bb2"
        },
        "date": 1786001507905,
        "tool": "pytest",
        "benches": [
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[random-in_memory]",
            "value": 68.7684411171036,
            "unit": "iter/sec",
            "range": "stddev: 0.00025711244281631415",
            "extra": "mean: 14.541553999997348 msec\nrounds: 60 on AMD EPYC 7763 64-Core Processor @ 3.2009 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[unique_shortcut-in_memory]",
            "value": 232.76161649225503,
            "unit": "iter/sec",
            "range": "stddev: 0.00011161919497904683",
            "extra": "mean: 4.296240999998702 msec\nrounds: 187 on AMD EPYC 7763 64-Core Processor @ 3.2009 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[ambiguous_shortcut-in_memory]",
            "value": 24.132780683000167,
            "unit": "iter/sec",
            "range": "stddev: 0.0007085043308702564",
            "extra": "mean: 41.43741300000414 msec\nrounds: 50 on AMD EPYC 7763 64-Core Processor @ 3.2009 GHz"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "github@michelfe.it",
            "name": "Jannik Kissinger",
            "username": "jannikmi"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "3b095869728c8e600e22bf8c949ec74af2789120",
          "message": "Remove code and assertions that provably do nothing (#463)",
          "timestamp": "2026-08-06T09:42:13+02:00",
          "tree_id": "3044ba0cc7274984b1ba91a50e5b0e21c69ead65",
          "url": "https://github.com/jannikmi/timezonefinder/commit/3b095869728c8e600e22bf8c949ec74af2789120"
        },
        "date": 1786002192848,
        "tool": "pytest",
        "benches": [
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[random-in_memory]",
            "value": 70.52980011005238,
            "unit": "iter/sec",
            "range": "stddev: 0.0003412710874961649",
            "extra": "mean: 14.17840400000614 msec\nrounds: 59 on AMD EPYC 7763 64-Core Processor @ 2.4454 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[unique_shortcut-in_memory]",
            "value": 222.9587789354164,
            "unit": "iter/sec",
            "range": "stddev: 0.000057361647360525064",
            "extra": "mean: 4.485133999992286 msec\nrounds: 187 on AMD EPYC 7763 64-Core Processor @ 2.4454 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[ambiguous_shortcut-in_memory]",
            "value": 24.96576756365622,
            "unit": "iter/sec",
            "range": "stddev: 0.0007112642784788309",
            "extra": "mean: 40.0548470000075 msec\nrounds: 50 on AMD EPYC 7763 64-Core Processor @ 2.4454 GHz"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "github@michelfe.it",
            "name": "Jannik Kissinger",
            "username": "jannikmi"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "a9206faa4a9d188715647419386d701e8a28170a",
          "message": "Record the triaged quality backlog in potential-improvements.md (#465)\n\nFindings from a code-quality pass that were deliberately left out of #464 to\nkeep that PR to a single theme. Each entry names a location, the defect and\nwhy it is worth doing, ordered by expected value per line of review.\n\nNotable: tests/auxiliaries.py's run_command assembles the subprocess stdout\nand stderr into an error message and then raises without it, so a failing\nwheel build reports only an exit code; scripts/reporting.py omits the\nfile_path argument that exists to name the offending file in a layout error;\nand two public docstrings still point users at timezone_names.json, which has\nbeen timezone_names.txt for some time.\n\nThe coordinate-bounds duplication is recorded with the reason it was not\nfixed: both remaining copies sit on the lookup fast path, so it needs a\nno-numba benchmark, and the bounds are physical constants that will not drift.\n\nExcluded from the sdist via MANIFEST.in, as CLAUDE.md and AGENTS.md are.\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-06T14:07:35+02:00",
          "tree_id": "ec9cbc2e218175fed249948659c3b9907572695f",
          "url": "https://github.com/jannikmi/timezonefinder/commit/a9206faa4a9d188715647419386d701e8a28170a"
        },
        "date": 1786018108447,
        "tool": "pytest",
        "benches": [
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[random-in_memory]",
            "value": 92.62191428927795,
            "unit": "iter/sec",
            "range": "stddev: 0.00022830568634465043",
            "extra": "mean: 10.796581000008132 msec\nrounds: 74 on AMD EPYC 9V74 80-Core Processor @ 2.5961 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[unique_shortcut-in_memory]",
            "value": 294.35538231704186,
            "unit": "iter/sec",
            "range": "stddev: 0.00005463387680290109",
            "extra": "mean: 3.3972540000064555 msec\nrounds: 220 on AMD EPYC 9V74 80-Core Processor @ 2.5961 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[ambiguous_shortcut-in_memory]",
            "value": 30.88061191044319,
            "unit": "iter/sec",
            "range": "stddev: 0.00023993728126517593",
            "extra": "mean: 32.38277799999878 msec\nrounds: 50 on AMD EPYC 9V74 80-Core Processor @ 2.5961 GHz"
          }
        ]
      }
    ]
  }
}