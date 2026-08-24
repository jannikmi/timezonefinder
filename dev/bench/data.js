window.BENCHMARK_DATA = {
  "lastUpdate": 1787539125348,
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
          "id": "85ca39ceca8311e423a9ba679445e08e6566e6b1",
          "message": "Add code-quality-pass agent skill with a persistent findings ledger (#466)\n\nTurns the standalone quality-pass prompt into a Claude Code skill so it\ntriggers on request instead of having to be pasted in.\n\nThe pass is meant to be run repeatedly, so its findings now accumulate in\npotential-improvements.md at the repository root: tracked and committed,\nso it reaches the next pass through master, and read before any source\nfile so earlier triage is reused rather than repeated. Statuses keep a\nshipped or rejected candidate from being raised again.\n\nThe skill names no files or suspected defects on purpose - an example in\nthe instructions would anchor every run on the same handful of findings.\nIt also does not restate CLAUDE.md or CONTRIBUTING.md, which would drift.\n\n.claude/skills/ is un-ignored (the rest of .claude/ stays local) and\nexcluded from the sdist alongside .cursor.\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-06T14:11:27+02:00",
          "tree_id": "c57d023b844fcb9465ac2626b78f218f48cce8c5",
          "url": "https://github.com/jannikmi/timezonefinder/commit/85ca39ceca8311e423a9ba679445e08e6566e6b1"
        },
        "date": 1786018450008,
        "tool": "pytest",
        "benches": [
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[random-in_memory]",
            "value": 75.25513371708776,
            "unit": "iter/sec",
            "range": "stddev: 0.0001716472962295132",
            "extra": "mean: 13.288129999999398 msec\nrounds: 60 on AMD EPYC 7763 64-Core Processor @ 3.2457 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[unique_shortcut-in_memory]",
            "value": 245.3123869262154,
            "unit": "iter/sec",
            "range": "stddev: 0.00010734150322608228",
            "extra": "mean: 4.076435000001766 msec\nrounds: 187 on AMD EPYC 7763 64-Core Processor @ 3.2457 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[ambiguous_shortcut-in_memory]",
            "value": 25.98995342756224,
            "unit": "iter/sec",
            "range": "stddev: 0.0003037061885494187",
            "extra": "mean: 38.47640600000091 msec\nrounds: 50 on AMD EPYC 7763 64-Core Processor @ 3.2457 GHz"
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
          "id": "8e1b48151709324633de207020b41e437d823dee",
          "message": "Stop the shortcut loader pinning the whole file buffer (#467)\n\n* Stop the shortcut loader pinning the whole file buffer\n\n`PolyIdsAsNumpy()` is `np.frombuffer` under the hood, so every poly id\narray the hybrid shortcut reader returned was a view onto the `bytes` it\nhad read the file into. 10,511 such views held the full 1,566,856 byte\nbuffer alive for the lifetime of every finder instance, although the\nlive poly id payload is only 46,746 bytes - ~33x more pinned than used.\n\nCopy each block out in the iteration that decodes it, so the view dies\nimmediately, and fill the entries with read-only slices of the\naccumulated payload afterwards. The buffer is released when the loader\nreturns: heap 7,433,653 -> 4,652,471 B (-37.4%), resident set ~2 MB\nlower per instance, load time unchanged at ~0.39 s (the per-entry\nflatbuffers decode dominates).\n\nCopying per block rather than holding the views and concatenating them\nat the end is what keeps the resident set moving in the same direction\nas the heap. Both free the buffer, but concatenating has the whole set\nof views alive while the replacement arrays are built, and that\ntransient peak (8.98 MiB, against 7.09 MiB for the pinning version)\nnever comes back: the allocator does not return the pages, so a 2.65 MiB\nheap saving turned into a 3.5 MiB RSS regression - measured, and the\nwrong trade for the constrained containers this is for. Streaming the\ncopy peaks at 6.14 MiB instead, below the version it replaces.\n\nOverwriting an existing dict key preserves its insertion position, so\nthe mapping is still iterated in file order by `test_shortcut_sorting`\nand `scripts/reporting.py`.\n\nBoth memory modes and both public classes were affected - `in_memory`\ndoes not reach this path.\n\n`test_shortcut_arrays_do_not_pin_the_file_buffer` asserts the ownership\ncontract by walking each array's `.base` chain, next to the opposite\ncontract for polygon coordinates, which are views onto the mmap by\ndesign. It asserts the size of the shared buffer rather than its type:\nthe whole file would satisfy any weaker check, and is what this used to\nhand out.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Regenerate the memory report against the compact shortcut mapping\n\n`make memory` + `scripts.render_benchmark_reports --memory-json`, on the\nsame machine and interpreter the committed report was measured on\n(Python 3.14.2, NumPy 2.3.5, Darwin arm64, numba). Re-rendering the\npre-change measurement first reproduced every committed heap figure\nexactly, so the diff below is the change, not the machine.\n\nHeap drops by 2.65 MiB in all three configurations - the shortcut\nmapping is loaded by each of them - which is 37% of `TimezoneFinderL`,\nwhose only large structure it is. RSS drops by 1.4-1.7 MiB. The\nin-memory-vs-file-based heap ratio in the summary rises from 8.58x to\n12.1x because the denominator shrank.\n\n`docs/alternatives.rst` quotes two of these figures by hand and is\nupdated with them.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n---------\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-07T15:15:54+02:00",
          "tree_id": "a3009cc671be5c069ca21a50f672341dcd8a8c84",
          "url": "https://github.com/jannikmi/timezonefinder/commit/8e1b48151709324633de207020b41e437d823dee"
        },
        "date": 1786108633974,
        "tool": "pytest",
        "benches": [
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[random-in_memory]",
            "value": 70.66048189613082,
            "unit": "iter/sec",
            "range": "stddev: 0.00035108508968047084",
            "extra": "mean: 14.152181999975255 msec\nrounds: 59 on AMD EPYC 9V74 80-Core Processor @ 2.8701 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[unique_shortcut-in_memory]",
            "value": 221.3514257146249,
            "unit": "iter/sec",
            "range": "stddev: 0.000056706195628151837",
            "extra": "mean: 4.517702999976336 msec\nrounds: 176 on AMD EPYC 9V74 80-Core Processor @ 2.8701 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[ambiguous_shortcut-in_memory]",
            "value": 24.071927883386987,
            "unit": "iter/sec",
            "range": "stddev: 0.00020578423903222138",
            "extra": "mean: 41.542165000009845 msec\nrounds: 50 on AMD EPYC 9V74 80-Core Processor @ 2.8701 GHz"
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
          "id": "68107f0282f567a7721afb0356e89d05b412fea6",
          "message": "Trim the unreleased changelog to end states (#474)\n\nSeveral unreleased bullets ran 8-15 lines and read as design journal\nentries, against this repository's own rule that a released section\nshould read as if each feature arrived in one step. The reasoning they\ncarried was also invisible to anyone not reading a changelog diff.\n\nEach is reduced to end state plus the one decision-relevant sentence,\nwith the reasoning left where it now lives:\n\n- the six bullets covering continuous benchmarking - CI setup,\n  merge-base comparison, machine stamping, estimator and threshold,\n  tracked core set, guardrails - become two, pointing at\n  docs/benchmarking_methodology.rst, which carries the ~25.5% ambiguous\n  ratio, the ~14x cost ratio, the 134-158% cross-machine spread and\n  every threshold derivation\n- the per-axis storage and layout_version bullets shrink to their user\n  visible consequence and link docs/data_format.rst, which documents\n  both already\n- the __slots__ item keeps the one line that matters (an unassigned slot\n  re-permits the attribute it names); the design context is in\n  docs/architecture.rst\n- pre-commit-clean generators, `make flatbuf`, the mypy exemption list,\n  the shortcut schema registry and the dead-code removal trim to end\n  state and leave the why at the point of decision, where it already is\n\nBullets describing one feature are merged: the BufferError fix and its\naccessor half, the weekly data update workflow across its three stages,\nthe update_data.sh changes, the quality-pass skill and its ledger, the\ntwo generator normalisations.\n\n28 Internal bullets become 17, 9 user-facing become 8, the section loses\na quarter of its lines. Every issue reference and contributor\nattribution is preserved - verified by extracting both sets before and\nafter. Released sections are untouched: they are historical record.\n\nNo changelog entry for this, deliberately. Amending the unreleased\nsection is the prescribed mechanism, and a bullet announcing that\nbullets were edited would be self-referential noise.\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-07T15:20:34+02:00",
          "tree_id": "abb8db7f6ca8afb681f0f99f1d36aef8f62e5c55",
          "url": "https://github.com/jannikmi/timezonefinder/commit/68107f0282f567a7721afb0356e89d05b412fea6"
        },
        "date": 1786108919539,
        "tool": "pytest",
        "benches": [
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[random-in_memory]",
            "value": 70.09237052957063,
            "unit": "iter/sec",
            "range": "stddev: 0.00022794022431988292",
            "extra": "mean: 14.266888000001643 msec\nrounds: 50 on AMD EPYC 7763 64-Core Processor @ 3.2417 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[unique_shortcut-in_memory]",
            "value": 228.7601360757112,
            "unit": "iter/sec",
            "range": "stddev: 0.00005778234620189392",
            "extra": "mean: 4.371390999999392 msec\nrounds: 190 on AMD EPYC 7763 64-Core Processor @ 3.2417 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[ambiguous_shortcut-in_memory]",
            "value": 24.53973578312042,
            "unit": "iter/sec",
            "range": "stddev: 0.0006073423425625873",
            "extra": "mean: 40.7502349999973 msec\nrounds: 50 on AMD EPYC 7763 64-Core Processor @ 3.2417 GHz"
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
          "id": "d36ebdee0912f7752492bade84a392800e55446b",
          "message": "Restructure the README around what the library does (#472)\n\nThe only page guaranteed to be read spent its budget on badges, a\nmaintainer-wanted notice, a six-line quickstart and a link list: one\nsentence on how the library works, zero numbers.\n\nThree short sections are added, all of it prose that already existed\nelsewhere in the repository:\n\n- *How it works* - the lookup pipeline, and the trade-off it exists to\n  serve: the polygons are never simplified, and the H3 index is what\n  makes carrying them affordable\n- *Performance* - one throughput figure with its configuration named,\n  the three point-in-polygon backends, and the pure-Python fallback that\n  costs speed but never results. Links to the trend chart, the reports\n  and the methodology\n- *Engineering notes* - architecture, data format, benchmarking\n  methodology, alternatives, changelog. The block that converts a\n  browsing reader into a reading one\n\nThe top of the page is reordered: banner, one-sentence positioning,\nbadges, quickstart. A reader now reaches a technical sentence within one\nscreen instead of ~10 badges and a maintainer notice.\n\nThe maintainers-wanted notice moves out of the first heading after the\nintro into a Contributing section at the bottom. The message is\nunchanged - as the second thing a reader saw it landed as \"this project\nis being wound down\" before any technical content. That section also\nlinks CONTRIBUTING.md, which the README did not link at all.\n\nEvery link and image source is absolute; verified by rendering the file\nthe way PyPI does rather than by rstcheck alone, which passes a valid\ndirective whose target does not resolve.\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-07T15:30:32+02:00",
          "tree_id": "afa08109f4d0c26466740a712a90f84bbc43155e",
          "url": "https://github.com/jannikmi/timezonefinder/commit/d36ebdee0912f7752492bade84a392800e55446b"
        },
        "date": 1786109511163,
        "tool": "pytest",
        "benches": [
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[random-in_memory]",
            "value": 84.97966564073681,
            "unit": "iter/sec",
            "range": "stddev: 0.00041772252509675865",
            "extra": "mean: 11.767520999995895 msec\nrounds: 62 on INTEL(R) XEON(R) PLATINUM 8573C @ 3.2521 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[unique_shortcut-in_memory]",
            "value": 272.21743421996626,
            "unit": "iter/sec",
            "range": "stddev: 0.000147407952162598",
            "extra": "mean: 3.6735340000007 msec\nrounds: 215 on INTEL(R) XEON(R) PLATINUM 8573C @ 3.2521 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[ambiguous_shortcut-in_memory]",
            "value": 29.181576141864543,
            "unit": "iter/sec",
            "range": "stddev: 0.0006106274216422634",
            "extra": "mean: 34.26819700000294 msec\nrounds: 50 on INTEL(R) XEON(R) PLATINUM 8573C @ 3.2521 GHz"
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
          "id": "46deb0ed04873d0c6e9590c765122e4d4338a808",
          "message": "Put the headline figure and the configuration above the fold in the benchmark reports (#473)\n\n`benchmark_results_timezonefinding.rst` made a reader parse four tables\nbefore learning \"~3.50us per lookup, ~286k/s\". Each of the four generated\nreports now opens with the figure that answers \"how fast/how big is it\",\nderived from the same parsed JSON as the tables below it - nothing here\nis hardcoded, or the block would go stale exactly when the numbers move.\n\nUnderneath it, a one-line banner names the platform, Python version and\nthe acceleration path that produced the numbers, and states whether that\nis the configuration CI tracks. It usually is not: the committed reports\nare rendered from a developer machine with Numba on and the C extension\noff, while CI measures the C extension without Numba - what a plain\n`pip install timezonefinder` gives you. That was already discoverable\nfrom the \"System Status\" section three screens down, as two separate\nbooleans; a reader comparing a table here against the trend chart was\ncomparing two implementations on two machines with nothing saying so.\nThe banner links the methodology page.\n\n`acceleration_path_label` collapses the two recorded flags to the one\npath that ran, since `utils.py` prefers Numba when both are importable -\nthey were never two independent choices.\n\nThe memory report gets the same treatment rather than being deferred: it\nis a fourth page in the same sidebar rendered by the same module, and a\nbanner on three of four pages is worse than none.\n\nThe three timing reports re-rendered byte-identically from the stored\nJSON before this change, so their diffs are the new block and nothing\nelse. The memory report was re-measured instead, because the stored JSON\npredates #467: every heap figure reproduces that PR's values exactly and\nonly four RSS digits move, which is the metric whose residency depends on\nmachine-wide pressure and which is deliberately not charted for that\nreason.\n\n`tests/test_render_benchmark_reports.py` covers the path label, the\nCI-configuration branch and the environment description. It also pins\nthat a headline never nests an RST literal inside bold - that shipped in\nan intermediate version of this change and rendered as stray backticks in\nthe HTML, with no warning from Sphinx or rstcheck.\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-07T15:35:18+02:00",
          "tree_id": "21bc221203c641bc1c1b1c314275dc7659145338",
          "url": "https://github.com/jannikmi/timezonefinder/commit/46deb0ed04873d0c6e9590c765122e4d4338a808"
        },
        "date": 1786109797338,
        "tool": "pytest",
        "benches": [
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[random-in_memory]",
            "value": 73.91828171340647,
            "unit": "iter/sec",
            "range": "stddev: 0.0003127409633987191",
            "extra": "mean: 13.528452999992169 msec\nrounds: 58 on AMD EPYC 9V74 80-Core Processor @ 2.8695 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[unique_shortcut-in_memory]",
            "value": 227.80454734290464,
            "unit": "iter/sec",
            "range": "stddev: 0.000045303650894134994",
            "extra": "mean: 4.3897280000066985 msec\nrounds: 183 on AMD EPYC 9V74 80-Core Processor @ 2.8695 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[ambiguous_shortcut-in_memory]",
            "value": 24.88993979746678,
            "unit": "iter/sec",
            "range": "stddev: 0.00029104484614172853",
            "extra": "mean: 40.17687499998601 msec\nrounds: 50 on AMD EPYC 9V74 80-Core Processor @ 2.8695 GHz"
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
          "id": "48ac98ba0b2e93f018220e9ab17155248131ddaa",
          "message": "Post the benchmark comparison where reviewers can see it (#476)\n\nThe comparison was posted with `POST /repos/{owner}/{repo}/commits/{sha}/comments`,\non the assumption - written into the workflow and CONTRIBUTING.md - that a\ncommit comment surfaces in the pull request's conversation timeline. It does\nnot. GitHub renders issue comments, reviews and review comments there; a commit\ncomment appears only on the commit's own page.\n\nSo the job went green, the API call returned 201, and the table reached nobody.\nConfirmed on PR #472: commitcomment-195337089 exists on its head commit with the\nfull body, while the pull request's timeline holds no `commit_commented` event\nat all.\n\nIt is now an issue comment on the pull request:\n\n- the number is resolved from the trusted `workflow_run.head_sha` via\n  `GET /commits/{sha}/pulls`, not read from `workflow_run.pull_requests`, which\n  is empty for fork pull requests - the case this split workflow exists to serve\n- a marker identifies the workflow's own comment so each run edits it in place.\n  Commit comments were one per commit; issue comments would otherwise stack a\n  full table on every push\n- no open pull request for the SHA exits 0 with a notice, so a comparison\n  landing after a merge does not fail the run\n\n`contents` drops from write to read - that write bought nothing but\ncreateCommitComment - and `pull-requests: write` takes its place.\n\n`tests/test_benchmark_workflows.py` pins the endpoint and the permission.\nNothing failed while the comparison was being posted somewhere invisible, which\nis exactly the class of silent breakage that module exists to catch.\n\nNo changelog entry: the unreleased bullet already describes posting the\ncomparison on the pull request, which this makes true.\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-07T15:54:16+02:00",
          "tree_id": "e9e0dc06060e7819e2599ab77f71a99906293f5b",
          "url": "https://github.com/jannikmi/timezonefinder/commit/48ac98ba0b2e93f018220e9ab17155248131ddaa"
        },
        "date": 1786110947327,
        "tool": "pytest",
        "benches": [
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[random-in_memory]",
            "value": 62.16852519469553,
            "unit": "iter/sec",
            "range": "stddev: 0.003937478563476201",
            "extra": "mean: 16.085310000008235 msec\nrounds: 52 on AMD EPYC 9V74 80-Core Processor @ 2.8704 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[unique_shortcut-in_memory]",
            "value": 209.32549255858413,
            "unit": "iter/sec",
            "range": "stddev: 0.0005774688590872399",
            "extra": "mean: 4.777248999999983 msec\nrounds: 168 on AMD EPYC 9V74 80-Core Processor @ 2.8704 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[ambiguous_shortcut-in_memory]",
            "value": 23.655317050552732,
            "unit": "iter/sec",
            "range": "stddev: 0.0020280056685056938",
            "extra": "mean: 42.27379400001041 msec\nrounds: 50 on AMD EPYC 9V74 80-Core Processor @ 2.8704 GHz"
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
          "id": "1478c266bf0eb7b930ba5096ce4ae73c5b64fe74",
          "message": "Stop restating generated figures in hand-written docs (#478)\n\n* Stop restating generated figures in hand-written docs\n\nExact numbers copied out of the generated pages go stale the moment the\ndata or the code moves, and nothing catches it. That had already\nhappened: #467 changed the memory footprint, leaving `~8 MiB`/`~71 MiB`\nwrong in `alternatives.rst` (twice), in the pytzwhere comparison and in\nthe changelog bullet describing the memory report.\n\nRemoved from the prose, with a link to the page that carries the live\nvalue instead:\n\n- the dataset counts - 7,925,313 boundary vertices, 1,322 polygons, 756\n  holes - from `alternatives.rst` and `architecture.rst`. These change\n  on every boundary-data update; `data_report.rst` is generated from the\n  packaged data\n- the shortcut index size, the wheel and installed sizes, and the\n  version-pinned `8.2.5`/`1.3.2` distribution figures\n- the memory footprints, now \"single-digit MiB\" against \"an order of\n  magnitude more\"\n- the lookup throughput, now \"hundreds of thousands of queries/s\", in\n  both the README and the comparison table\n\nThe tzfpy speed row becomes qualitative on both sides rather than a\nside-by-side of two numbers nobody measured together - which is what the\nnote under the table already told the reader to do with it.\n\nKept: figures fixed by a constant rather than by the data (`~1 cm`\nfollows from `COORD2INT_FACTOR`, `~41k` cells from H3 resolution 3, the\n`~400x` pure-Python penalty), and the pytzwhere figures, which describe a\npackage that has not moved since 2016.\n\nThe H3 resolution study in `data_format.rst` keeps its finding - the\n`>10 %` ratio that made resolution 4 not worth it - but drops the\nabsolute index size, which read as a current measurement and was already\noff. `CLAUDE.md` gains the rule under *Documentation Files*.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Round the ambiguous-query ratio, and rebase before the final test gate\n\nTwo follow-ups on the same theme as this branch.\n\n`~25.5 %` ambiguous queries in the benchmarking methodology page is\ndataset-derived and drifts with every boundary-data update. The argument\nit supports - that uniformly random points are the only globally\nrepresentative workload - does not need the decimal, so it is now `~25 %`,\nmatching the figure the same section already uses two paragraphs down.\n\n`CLAUDE.md` gains the ordering rule under *Testing*: fetch and rebase\nonto the latest `master` before running the final gate, not after. Other\nwork merges while a PR is open, and a rebase afterwards invalidates the\nrun - it tested a tree that never existed - so the wrong order costs a\nsecond `make testall`.\n\nAlso amends the package-comparison changelog bullet, which still\ndescribed the `Distribution Size` figure and the two-number speed row\nthat the previous commit removed. Per the amend-don't-append rule the\nunreleased section has to read as one end state.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n---------\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-07T16:04:17+02:00",
          "tree_id": "f9c6d02acd45e209e22f5fd7bac50d050d575c84",
          "url": "https://github.com/jannikmi/timezonefinder/commit/1478c266bf0eb7b930ba5096ce4ae73c5b64fe74"
        },
        "date": 1786111548221,
        "tool": "pytest",
        "benches": [
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[random-in_memory]",
            "value": 75.00028312610048,
            "unit": "iter/sec",
            "range": "stddev: 0.0002715624293672008",
            "extra": "mean: 13.333282999994367 msec\nrounds: 61 on AMD EPYC 7763 64-Core Processor @ 2.4454 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[unique_shortcut-in_memory]",
            "value": 233.3849736486208,
            "unit": "iter/sec",
            "range": "stddev: 0.000027752635016094322",
            "extra": "mean: 4.2847659999978305 msec\nrounds: 193 on AMD EPYC 7763 64-Core Processor @ 2.4454 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[ambiguous_shortcut-in_memory]",
            "value": 25.894087898098597,
            "unit": "iter/sec",
            "range": "stddev: 0.0005169994933174523",
            "extra": "mean: 38.61885400000631 msec\nrounds: 50 on AMD EPYC 7763 64-Core Processor @ 2.4454 GHz"
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
          "id": "4f38bbe3e8e5b7678aecad0de1461fe9554fd484",
          "message": "Make a stale generated report fail instead of reading plausible (#479)",
          "timestamp": "2026-08-08T12:34:33+02:00",
          "tree_id": "ea1e628828bf4386a8ce0b73113f3aa164a76c66",
          "url": "https://github.com/jannikmi/timezonefinder/commit/4f38bbe3e8e5b7678aecad0de1461fe9554fd484"
        },
        "date": 1786185351908,
        "tool": "pytest",
        "benches": [
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[random-in_memory]",
            "value": 71.52058777336747,
            "unit": "iter/sec",
            "range": "stddev: 0.0002285869414702787",
            "extra": "mean: 13.981987999997614 msec\nrounds: 59 on AMD EPYC 9V74 80-Core Processor @ 2.5961 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[unique_shortcut-in_memory]",
            "value": 226.15035334849549,
            "unit": "iter/sec",
            "range": "stddev: 0.000054314293948660763",
            "extra": "mean: 4.4218370000024265 msec\nrounds: 178 on AMD EPYC 9V74 80-Core Processor @ 2.5961 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[ambiguous_shortcut-in_memory]",
            "value": 24.469781434934752,
            "unit": "iter/sec",
            "range": "stddev: 0.0003098540711834759",
            "extra": "mean: 40.866731999997796 msec\nrounds: 50 on AMD EPYC 9V74 80-Core Processor @ 2.5961 GHz"
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
          "id": "dd7237138870af7a65b8f96df366aea623440152",
          "message": "Print the CLI result instead of routing it through a temp file (#480)\n\n* Print the CLI result instead of routing it through a temp file\n\nmain redirected stdout to a mkstemp file for the duration of the lookup\nand then, in verbose mode, reopened that file to read back a string it\nstill held in a local variable. Nothing inside the redirected block ever\nwrote to stdout: the lookup functions return their result rather than\nprinting it, and the only prints in the package are on data *write*\npaths a lookup never reaches. The context manager, the read-back, the\nwarning it raised when the file could not be read and the cleanup that\nremoved it are gone.\n\nThe lookup function is now resolved once per invocation instead of\ntwice, so -f 3 / -f 4 under -v no longer construct a second\nTimezoneFinderL and reload its shortcut data purely to read a function\nname off it. _print_lookup_details is renamed _format_lookup_details\nafter what it does; _lookup_timezone is dropped, since its only job was\nto pair the resolution with the call.\n\nOutput is unchanged character for character, verified across 5 function\nids x 2 modes x 4 coordinates plus --help and a rejected id.\n\ntests/cli_test.py covered none of this. Its single test passed the\ncaptured stdout through rstrip(\"\\n\\x1b[0m\"), which strips a *set* of\ncharacters rather than a suffix and so truncates 12 of the 444 packaged\nzone names (Europe/Amsterdam -> Europe/Amsterda); it held only because\nthe four hardcoded coordinates happened to miss all twelve. Two of its\nasserts were vacuous: res == \"None\" can never match, since the CLI\nprints an empty line and not the string None - and that dead branch\nmasked exactly the regression of printing None - while the\n\"command not found\" check is unreachable under check=True. The\nreplacement asserts the printed name verbatim and adds the missing\ncases: verbose mode, the empty line printed when no timezone is found,\nand the rejected function id.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Record pass 3 in the findings ledger\n\nCLI-1, CLI-2 and CLI-3 shipped, with the judgement call on CLI-3 (remove\nthe redirect rather than document it) written down. Adds CLI-4 for the\ntest defect found while covering them, TEST-1 and TEST-2 from this\npass's sweep, and folds a second A002 site into TYPE-4.\n\nCoverage log gains pass 3 and narrows what is left unswept to\nrender_benchmark_reports.py, describe_benchmark_machine.py and the\nbenchmarks/test_*.py suites, plus the ruff --select ALL families already\njudged not worth acting on so the next pass does not re-triage them.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Record that a local test run covers one point in the support matrix\n\nA test in this PR asserted argparse's exact wording, which renders the\nrejected value bare on 3.11 and quoted from 3.12 on. It passed a full\nlocal make testall and failed the 3.11 CI job.\n\nThe interpreter is only one axis, and not the sharpest one: tox spans\npy{311,312,313,314}{,-numba,-pytz}, and because the default dev\nenvironment installs numba, utils.py's import-time dispatch resolves\ninside_polygon to the numba path locally - so a local gate never\nexercises the C extension the bare CI envs use, however green it is.\n\nAdds the general rule to the Testing section, next to the existing note\non gate ordering, with the cheap way to test a single axis.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n---------\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-09T00:15:29+02:00",
          "tree_id": "9675950d2bb209fe3f02955a5001b8b8fb1a73e6",
          "url": "https://github.com/jannikmi/timezonefinder/commit/dd7237138870af7a65b8f96df366aea623440152"
        },
        "date": 1786227402962,
        "tool": "pytest",
        "benches": [
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[random-in_memory]",
            "value": 65.5923341976657,
            "unit": "iter/sec",
            "range": "stddev: 0.0001836665513561623",
            "extra": "mean: 15.245683999999926 msec\nrounds: 59 on AMD EPYC 9V74 80-Core Processor @ 2.8723 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[unique_shortcut-in_memory]",
            "value": 216.8435387128089,
            "unit": "iter/sec",
            "range": "stddev: 0.0001052792693790784",
            "extra": "mean: 4.611620000005701 msec\nrounds: 183 on AMD EPYC 9V74 80-Core Processor @ 2.8723 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[ambiguous_shortcut-in_memory]",
            "value": 23.400361250099344,
            "unit": "iter/sec",
            "range": "stddev: 0.0002996697201997306",
            "extra": "mean: 42.734382999995546 msec\nrounds: 50 on AMD EPYC 9V74 80-Core Processor @ 2.8723 GHz"
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
          "id": "d65001fe3c0feb2daf965ee47cdc3f331a0f629b",
          "message": "Make the docstrings describe the code that exists (#481)\n\n* Make the docstrings describe the code that exists\n\nSix docstrings documented something the implementation contradicts, and five\nmore documented parameters that no longer exist.\n\nThe consequential ones are public API. AbstractTimezoneFinder.__init__ called\nin_memory inert and \"kept for API compatibility\" when it is exactly what selects\nmemory-mapped against in-memory coordinate access - and since\nTimezoneFinder.__init__ carries no docstring of its own, inspect.getdoc inherits\nthat claim, so help(TimezoneFinder.__init__) told users the opposite of\ndocs/1_usage.rst. Both get_geometry docstrings named a timezone_names.json that\nhas never existed under that name. read_zone_names promised an empty list for a\nmissing file where it raises FileNotFoundError, and illustrated itself with a\nhardcoded zone count the packaged data had outgrown by three. zone_id_of and\nzone_name_from_id each advertised an exception type their handler converts away,\nsending callers to write an except clause that can never fire while omitting the\none that will.\n\nThe remaining five are :param:/Args: entries in scripts/ and tests/ for\narguments removed along with the parallel shortcut compilation they belonged to;\ncompile_shortcut_mapping's summary still claimed \"optimized parallel processing\"\nthat the NOTE at the foot of its own docstring contradicts.\n\ntests/test_documented_contracts.py pins the claims that are behaviour: the\nexception types both finder methods raise, and that in_memory really does select\nthe coordinate accessor. Every assertion was mutation-checked.\n\n* Record pass 4 in the findings ledger, and drop what has shipped\n\nThe ledger is a to-do list, not a history: entries a pass ships are deleted in\nthe same PR rather than kept with a `shipped` status. The code is the evidence\nthey are done, the changelog says what changed, and git log still has the text.\nRejected, out-of-scope and withdrawn entries stay, because those encode a dead\nend worth not re-discovering. That removes the ERR-*, CLI-* and DOC-* sections -\nevery entry in them had shipped - and takes the file from 575 lines to 384.\n\nAlso cuts the ledger's largest source of merge conflicts between concurrent\npasses: a shipped entry is dead weight that every later pass has to carry past.\n\nPass 4 itself: DOC-1 and DOC-2 shipped (and so removed), plus a first sweep of\nscripts/render_benchmark_reports.py, scripts/describe_benchmark_machine.py and\nthe benchmarks/test_*.py suites - the areas the previous pass flagged as\nuncovered. Adds a Behaviour defects section for the two findings a quality pass\nmay not act on: a negative id silently returns the last zone from both\nzone_id_of and zone_name_from_id, and AbstractTimezoneFinder.__init__ accepts an\nin_memory it never reads.",
          "timestamp": "2026-08-09T00:43:07+02:00",
          "tree_id": "6e99e58e0a9ddbb4cac04532645879bbf2a8b03c",
          "url": "https://github.com/jannikmi/timezonefinder/commit/d65001fe3c0feb2daf965ee47cdc3f331a0f629b"
        },
        "date": 1786229097257,
        "tool": "pytest",
        "benches": [
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[random-in_memory]",
            "value": 68.23223715291515,
            "unit": "iter/sec",
            "range": "stddev: 0.0006818031513835209",
            "extra": "mean: 14.655828999991627 msec\nrounds: 58 on AMD EPYC 9V74 80-Core Processor @ 2.8289 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[unique_shortcut-in_memory]",
            "value": 226.48820302201892,
            "unit": "iter/sec",
            "range": "stddev: 0.00006766843630032412",
            "extra": "mean: 4.415241000003789 msec\nrounds: 179 on AMD EPYC 9V74 80-Core Processor @ 2.8289 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[ambiguous_shortcut-in_memory]",
            "value": 23.523639340358482,
            "unit": "iter/sec",
            "range": "stddev: 0.0002630245569745943",
            "extra": "mean: 42.51042900000357 msec\nrounds: 50 on AMD EPYC 9V74 80-Core Processor @ 2.8289 GHz"
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
          "id": "c0a68875e457105cab72a71b600de329bf74d533",
          "message": "Let several quality passes run at once without colliding (#484)\n\nTwo passes running concurrently shared one repository, one ledger and one\nchangelog with nothing arranging that between them, and the skill actively made\nit worse: it hardcoded a single worktree path, so the second pass could not even\ncreate its tree, and it said nothing about when to push, so a branch became\nvisible only once the work was already done. Nothing stopped two passes from\npicking the same theme and doing it twice.\n\nThe remote branch list is now the coordination mechanism, used at two defined\nmoments: survey it before creating a worktree, and claim a theme by pushing the\nbranch the instant triage picks one - a slug that names the theme, pushed while\nit still points at master. First push wins a collision; the loser takes its\nnext-ranked candidate rather than racing. Worktree and branch names are per-pass.\n\nThe two files that collide regardless are named, with their resolutions: the\nchangelog, where both bullets are kept, and the ledger, whose remaining overlap\nis one entry both passes re-verified.\n\nThe ledger becomes a to-do list rather than a history: an entry is deleted by the\npull request that ships it, since the code is the evidence and git log keeps the\ntext. Only rejected, out-of-scope and withdrawn entries stay, because those\nencode a dead end worth not rediscovering. Shipped entries interleaved with live\nones were the ledger's largest conflict surface.\n\nThe changelog bullet is amended rather than appended, per CLAUDE.md - the skill\narrived in this same unreleased section.",
          "timestamp": "2026-08-09T00:45:45+02:00",
          "tree_id": "5b15034089463f4db849a2dae15ad8f4eab1580d",
          "url": "https://github.com/jannikmi/timezonefinder/commit/c0a68875e457105cab72a71b600de329bf74d533"
        },
        "date": 1786229229679,
        "tool": "pytest",
        "benches": [
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[random-in_memory]",
            "value": 73.1513644375189,
            "unit": "iter/sec",
            "range": "stddev: 0.0007713968759963417",
            "extra": "mean: 13.670285000003446 msec\nrounds: 60 on AMD EPYC 9V74 80-Core Processor @ 2.8689 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[unique_shortcut-in_memory]",
            "value": 221.45318911433432,
            "unit": "iter/sec",
            "range": "stddev: 0.000047389617343983655",
            "extra": "mean: 4.515626999996414 msec\nrounds: 182 on AMD EPYC 9V74 80-Core Processor @ 2.8689 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[ambiguous_shortcut-in_memory]",
            "value": 24.82648891033347,
            "unit": "iter/sec",
            "range": "stddev: 0.002417173662867126",
            "extra": "mean: 40.27955799999461 msec\nrounds: 50 on AMD EPYC 9V74 80-Core Processor @ 2.8689 GHz"
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
          "id": "ed54d346e509d33850542929b19feef375293ff3",
          "message": "Make the checks that cannot fail actually fail (#485)",
          "timestamp": "2026-08-09T07:01:24+02:00",
          "tree_id": "9ef73291fd7953132aeedb4a3fbf2764fd47e078",
          "url": "https://github.com/jannikmi/timezonefinder/commit/ed54d346e509d33850542929b19feef375293ff3"
        },
        "date": 1786251779019,
        "tool": "pytest",
        "benches": [
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[random-in_memory]",
            "value": 73.06862276245806,
            "unit": "iter/sec",
            "range": "stddev: 0.00017799155828772975",
            "extra": "mean: 13.685764999991079 msec\nrounds: 60 on AMD EPYC 7763 64-Core Processor @ 2.4454 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[unique_shortcut-in_memory]",
            "value": 231.23311998261576,
            "unit": "iter/sec",
            "range": "stddev: 0.00004570490879777784",
            "extra": "mean: 4.324639999992996 msec\nrounds: 188 on AMD EPYC 7763 64-Core Processor @ 2.4454 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[ambiguous_shortcut-in_memory]",
            "value": 25.415193400839367,
            "unit": "iter/sec",
            "range": "stddev: 0.0003545780800055254",
            "extra": "mean: 39.34654300002194 msec\nrounds: 50 on AMD EPYC 7763 64-Core Processor @ 2.4454 GHz"
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
          "id": "d34404e7ce9e59377f42cc3ee69ed730cc8dcc3b",
          "message": "Make the docs landing page state what the package does (#487)\n\ndocs/index.rst is the second front door - the docs badge, the PyPI project\nlinks and search results all land there - but carried three sentences and a\nflat 17-entry table of contents in which Architecture sat between Memory\nBenchmarks and Data Format. Nothing on it said how a lookup works or what\nthe package trades away to be accurate.\n\nIt now carries the same \"How it works\" summary as the README, adapted to use\n:doc: roles where the README needs absolute URLs, plus the no-simplification\ntrade-off and the ocean-zone consequence for timezone_at() - the single most\ncommon source of user confusion, which until now appeared only in the README\nand the architecture page.\n\nThe toctree is split into four captioned groups (Using it, Design,\nPerformance, Project). All 17 entries are preserved, each in exactly one\ngroup, so Sphinx warns about neither an orphaned document nor a duplicate\nentry.\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-10T04:56:49+02:00",
          "tree_id": "6e1f3ff865ead2c5b1519d53121a626793a6ab00",
          "url": "https://github.com/jannikmi/timezonefinder/commit/d34404e7ce9e59377f42cc3ee69ed730cc8dcc3b"
        },
        "date": 1786330684889,
        "tool": "pytest",
        "benches": [
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[random-in_memory]",
            "value": 74.07881511824121,
            "unit": "iter/sec",
            "range": "stddev: 0.00018109824831577794",
            "extra": "mean: 13.499136000000078 msec\nrounds: 62 on AMD EPYC 7763 64-Core Processor @ 3.2441 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[unique_shortcut-in_memory]",
            "value": 237.54436140947658,
            "unit": "iter/sec",
            "range": "stddev: 0.00020326803462425699",
            "extra": "mean: 4.209740000000295 msec\nrounds: 198 on AMD EPYC 7763 64-Core Processor @ 3.2441 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[ambiguous_shortcut-in_memory]",
            "value": 25.58743243574769,
            "unit": "iter/sec",
            "range": "stddev: 0.0014979965048630857",
            "extra": "mean: 39.08168599999584 msec\nrounds: 50 on AMD EPYC 7763 64-Core Processor @ 3.2441 GHz"
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
          "id": "efd04e929b6de9159c7959c46d5fd4bfe4ca7f6a",
          "message": "Show the timezone the shipped data actually returns (#491)\n\nEvery usage snippet in README.rst and docs/1_usage.rst queries the Berlin\ncoordinates lng=13.358, lat=52.5061 and annotated the answer as\n'Europe/Paris'. That is what the reduced timezones-now dataset returns,\nwhere Europe/Berlin is merged into Europe/Paris. The package ships the\nfull dataset by default, which returns 'Europe/Berlin', so all eleven\ncomments described a dataset the reader does not have.\n\nEach annotation was re-derived by running the call it sits on rather than\nby find-and-replace: the global and instance forms of timezone_at,\ntimezone_at_land, certain_timezone_at and unique_timezone_at, plus the two\nTimezoneFinderL snippets. The neighbouring 'Etc/GMT' and None annotations\nwere confirmed correct and left alone. The get_geometry example in the\nopening block now asks for Europe/Berlin too - Europe/Paris was a valid\ncall, but read as though it followed from the lookup above it.\n\nNothing tied those comments to the packaged data, which is how they stayed\nwrong across releases. test_documented_contracts.py now re-runs each\ndocumented lookup against the example coordinate, one case per lookup,\nsince only unique_timezone_at can start returning None without any of the\nothers changing.\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-10T05:12:20+02:00",
          "tree_id": "e4f3e0d98a6039b34a02089b6ffbb67eeb31b361",
          "url": "https://github.com/jannikmi/timezonefinder/commit/efd04e929b6de9159c7959c46d5fd4bfe4ca7f6a"
        },
        "date": 1786331626733,
        "tool": "pytest",
        "benches": [
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[random-in_memory]",
            "value": 73.60492717268728,
            "unit": "iter/sec",
            "range": "stddev: 0.00025716804881253556",
            "extra": "mean: 13.586047000003987 msec\nrounds: 61 on AMD EPYC 7763 64-Core Processor @ 3.2981 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[unique_shortcut-in_memory]",
            "value": 232.38212358704087,
            "unit": "iter/sec",
            "range": "stddev: 0.000052922376836108094",
            "extra": "mean: 4.303256999996563 msec\nrounds: 188 on AMD EPYC 7763 64-Core Processor @ 3.2981 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[ambiguous_shortcut-in_memory]",
            "value": 25.4616431421867,
            "unit": "iter/sec",
            "range": "stddev: 0.0004692236516049199",
            "extra": "mean: 39.274763000001656 msec\nrounds: 50 on AMD EPYC 7763 64-Core Processor @ 3.2981 GHz"
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
          "id": "4578be790822b7f7b7730a79c1391dfe5e8fd085",
          "message": "Build test distributions for the interpreter running the tests (#494)\n\n`uv build` was invoked without `--python`, so it targeted the newest\ninterpreter on the machine, while tests/test_integration.py creates its\nthrowaway venv from `sys.executable`. On a checkout whose `.venv` is older\nthan the newest installed Python the two disagree: `make testint` built a\ncp314 wheel and `test_install_from_artifacts[wheel]` died on pip's \"not a\nsupported wheel on this platform\", nowhere near the build that caused it.\n\nEvery tox environment offers a single interpreter, so the two agreed by\naccident in CI and this only ever hit developer machines, where the\nworkaround was pinning UV_PYTHON.\n\nPin the shared build command to `sys.executable` instead of teaching\nsetup_venv to guess which interpreter uv would have chosen - the target venv\nis the thing under test, so it is the build that should follow it. The sdist\nbuild takes the same pin: it carries no interpreter tag, but it keeps the two\nartefacts in dist/ from coming out of different interpreters.\n\ntest_build_commands_pin_the_running_interpreter guards the pin. It needs no\nbuild and so carries the `unit` marker, which matters because no CI\nenvironment can reproduce the mismatch - without it the next regression would\ngo unnoticed the same way.\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-10T05:46:41+02:00",
          "tree_id": "0d92c9940338e24d2a609c1ff776ff07ed5d1480",
          "url": "https://github.com/jannikmi/timezonefinder/commit/4578be790822b7f7b7730a79c1391dfe5e8fd085"
        },
        "date": 1786333676640,
        "tool": "pytest",
        "benches": [
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[random-in_memory]",
            "value": 79.94675546087025,
            "unit": "iter/sec",
            "range": "stddev: 0.0006568183233119599",
            "extra": "mean: 12.508324999998877 msec\nrounds: 56 on INTEL(R) XEON(R) PLATINUM 8573C @ 3.1000 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[unique_shortcut-in_memory]",
            "value": 261.479335026764,
            "unit": "iter/sec",
            "range": "stddev: 0.00006397459530551538",
            "extra": "mean: 3.8243939999986765 msec\nrounds: 214 on INTEL(R) XEON(R) PLATINUM 8573C @ 3.1000 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[ambiguous_shortcut-in_memory]",
            "value": 25.99854293765912,
            "unit": "iter/sec",
            "range": "stddev: 0.0004903410944675962",
            "extra": "mean: 38.463694000000714 msec\nrounds: 50 on INTEL(R) XEON(R) PLATINUM 8573C @ 3.1000 GHz"
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
          "id": "5a00273c87c2ef48bbbe800b6489c04f19deff8d",
          "message": "Land the documentation visibility stack on master (#495)\n\n* Document how the package is tested and shipped (#488)\n\nSearching docs/, README.rst and CONTRIBUTING.md for abi3, cibuildwheel,\nmusllinux or manylinux returned nothing outside a single acknowledgement\nline: the release pipeline existed only as workflow YAML. The property-based\ntests and the tox matrix were likewise mentioned nowhere outside the\nchangelog.\n\narchitecture.rst gains a \"How it ships\" section covering the choices and the\nreason each was made - one abi3 wheel per target instead of one per Python\nversion, with abi3audit --strict guarding a claim whose failure mode is a\nruntime crash on an interpreter CI never ran; three libc targets so an Alpine\ncontainer still gets the compiled path; an end-to-end job that installs the\nbuilt wheel on four interpreters and asserts clang_extension_loaded, because\nan import-only smoke test passes on a wheel whose extension silently failed\nto build; a tag from outside master aborting the release; and the weekly data\npipeline that regenerates, opens a PR and tags on green.\n\nThe testing section gains the property-based suite and the tox matrix, plus\nthe reason the matrix is a matrix: the acceleration paths are bound at import\ntime, so a passing run describes one configuration only. It also states why\nthe correctness sampler is pole-biased and cross-references\nbenchmarking_methodology, where the opposite choice is made - previously only\none half of that contrast appeared on each page.\n\nBoth sections land on an existing page, so there is no new toctree entry and\nno orphan risk. The two new README bullets use absolute URLs; their anchor\nslugs were read out of the built architecture.html rather than guessed, and\nthe rendered README was checked with readme-renderer.\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>\n\n* Stop answering docs questions by naming a file to go open (#489)\n\nThe three hand-written pages a docs visitor reads first were the only prose\nin docs/ that read as unmaintained.\n\n7_performance.rst is what the README calls \"benchmark reports\", but it opened\nwith a vendor-style bullet list about the binary format (\"Zero-Copy Access\",\n\"Optimized Data Layout\") that said nothing data_format.rst does not say\nproperly. That list is gone and the Benchmark Results section moves to the\ntop, so a reader lands on the four reports and the trend chart. The C\nextension and Numba sections are cut to what a user acts on - the call that\nreports the active backend - and defer the explanation to architecture.rst,\nwhich already carried a more precise version of the same material; a\nduplicated explanation that has drifted once will drift again, and here the\nduplicate was the worse copy.\n\nBoth referenced anchors survive: `.. _performance:` (0_getting_started.rst,\n3_about.rst) and `.. _speed-tests:` (1_usage.rst, data_format.rst). Verified\nagainst the built HTML - every inbound href=\"7_performance.html#...\" resolves\nto an id that exists.\n\n0_getting_started.rst answered \"Dependencies\" with \"please confer to the\npyproject.toml\". It now names the four runtime dependencies and what each\none carries, and says why the list is short and why numba is an extra rather\nthan a dependency, keeping pyproject.toml as the authoritative source for\nversion ranges so the page cannot go stale on a bound. Both \":ref:`HERE`\"\nlinks get descriptive text.\n\n2_use_cases.rst answered two of its four use cases with \"check out the\nexample script\". Each now has a runnable snippet, with the example script as\nthe follow-up. The snippets use the standard library's zoneinfo rather than\npytz, so neither requires an optional dependency; the pytz example scripts\nare still named for users already on pytz. Nothing under examples/ is\ntouched - tests/test_example_scripts.py executes those.\n\nEvery coordinate/zone pair in the new snippets was verified with an actual\nlookup rather than assumed.\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>\n\n* Say what the two root-level artifacts are (#490)\n\n* Say what the two root-level artifacts are\n\nBoth are read wrong by someone skimming the repository root.\n\npotential-improvements.md is a triaged register of internal quality debt,\nranked by expected value per line of review, with the judgement recorded for\nevery entry including the ones judged not worth doing. Its first paragraph\nopened on the machinery instead - how an automated pass consumes the file and\nwrites it back - so a reader met tooling exhaust rather than the triage. The\nheader now leads with what the file is and what the ranking rule is, states\nthat the findings are internal quality with the Behaviour defects section as\nthe one deliberate exception, and moves the maintenance mechanics to the end\nunder its own subheading. No entry changes.\n\nThe file stays at the repository root. docs/ is a Sphinx source tree with\nsource_suffix = \".rst\", so a .md placed there is invisible to the build\nrather than a documented page, and MANIFEST.in plus thirteen references in\n.claude/skills/code-quality-pass/SKILL.md all name the current path.\n\nprototypes/ had three scripts and no index, one of which is the study that\nchose H3 resolution 3 - the central algorithmic parameter of the package,\nalready cited from docs/data_format.rst. prototypes/README.md now states what\nthe directory is (exploratory studies behind committed decisions, run by\nhand, outside the package and the test suite) and what each script\nestablished, including the hierarchical-index idea that was measured and\ndropped.\n\ncheck-manifest failed on the new file as expected, since MANIFEST.in excluded\nonly prototypes/*.py from the sdist. The exclude is broadened to the whole\ndirectory rather than adding an ignore, since nothing in prototypes/ belongs\nin a distribution.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Record what the new documentation can go stale against\n\nThe preceding four commits added prose that paraphrases files elsewhere in\nthe repo, and duplicated the lookup summary across two front doors on\npurpose. Each of those is a place where the source changes and nothing\nre-reads the prose, so the discipline has to be written down where it is read\nbefore the edit rather than discovered after it.\n\nCLAUDE.md, Documentation Files - amended in place rather than opened as a new\nsection:\n\n- the badge-block bullet now covers both deliberate duplications, naming the\n  three files the How it works summary lives in and what kind of change has to\n  land in all of them\n- README.rst now deep-links into docs/ by anchor, and Sphinx derives an anchor\n  from the heading text. Renaming a heading breaks those links silently: the\n  page still loads at the top, rstcheck does not resolve targets and make docs\n  does not know README.rst exists. Says what to grep, and to read a new slug\n  out of the built HTML rather than deriving it\n- a zone name in a snippet is example output, not a constant - with how the\n  reduced timezones-now answer for Berlin came to annotate the default\n  dataset's running example\n- the three prose/source pairs that now exist: the dependency list against\n  pyproject.toml, How it ships against build.yml and the cibuildwheel config,\n  prototypes/README.md against its directory\n- the toctree bullet names the four captioned groups and the exactly-one rule\n\nCONTRIBUTING.md gets the reverse index instead: a changed-this / re-read-that\ntable for contributors, which is the direction a human needs it in, pointing\nat CLAUDE.md for what each one breaks rather than restating it.\n\nAlso corrects the PR checklist, which asked for a rebase onto `main`; this\nrepository's default branch is `master`.\n\nNo changelog entry - CLAUDE.md explicitly exempts edits confined to itself and\nCONTRIBUTING.md.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n---------\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>\n\n---------\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-10T05:50:27+02:00",
          "tree_id": "72053eccc52a497a421423c919e9c2e419ae12f3",
          "url": "https://github.com/jannikmi/timezonefinder/commit/5a00273c87c2ef48bbbe800b6489c04f19deff8d"
        },
        "date": 1786333900492,
        "tool": "pytest",
        "benches": [
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[random-in_memory]",
            "value": 69.70492788737229,
            "unit": "iter/sec",
            "range": "stddev: 0.00020345979255571977",
            "extra": "mean: 14.346188000018856 msec\nrounds: 61 on AMD EPYC 7763 64-Core Processor @ 3.2414 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[unique_shortcut-in_memory]",
            "value": 232.88200800165066,
            "unit": "iter/sec",
            "range": "stddev: 0.00015956113211435126",
            "extra": "mean: 4.294020000003229 msec\nrounds: 194 on AMD EPYC 7763 64-Core Processor @ 3.2414 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[ambiguous_shortcut-in_memory]",
            "value": 24.990461140988383,
            "unit": "iter/sec",
            "range": "stddev: 0.00034335189409628446",
            "extra": "mean: 40.015267999990556 msec\nrounds: 50 on AMD EPYC 7763 64-Core Processor @ 3.2414 GHz"
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
          "id": "a69f03ca1d926c51ebf972349144b7aa37bee440",
          "message": "Verify MANIFEST.in exclusions the other way round too (#493)\n\n* Verify MANIFEST.in exclusions the other way round too\n\nThe packaging guard asserts that nothing in the built sdist and wheel\nmatches a pattern in IGNORED_PATTERNS, and #486 made every hand-written\npattern name a path that actually exists. That closed one direction: a\npattern matching nothing now fails.\n\nThe converse stayed silent. MANIFEST.in and the pattern set are two\nhand-maintained statements of one intent, so an exclude/recursive-exclude/\nprune line added without a matching pattern left the file kept out by the\nbuild and verified by nothing - deleting that line later would ship it\nwith the suite still green.\n\ntest_every_manifest_exclusion_is_guarded parses the exclusion directives\nout of MANIFEST.in and fails when one of them covers a path in the\ncheckout that no pattern names. The four directive forms collapse into\none shape (prefix, glob, anchored), and the glob is matched a component\nat a time so `*` does not cross a separator, as it does not in\nMANIFEST.in but does in matches_pattern.\n\nFour directives name untracked artefacts whose presence is a property of\nthe machine rather than of the project - `.git` is a directory in a clone\nand a file in a linked worktree, numba's cache under\ntimezonefinder/__pycache__/ appears only after a numba-enabled run - so\nscanning them would pass here and fail elsewhere. Those are exempted\nagainst the pattern that carries the same intent, and\ntest_pattern_only_exclusions_stay_current fails if either side goes away.\nNeither global-exclude is load-bearing: dropping either changes neither\ndistribution, since setuptools already prunes __pycache__ from an sdist.\n\nBoth tests are unit tests - they need no build, so a drifted exclusion\nsurfaces in `make test`.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* List the packaging guard among the invariant-protecting tests\n\ndocs/architecture.rst's \"Tests that protect guarantees, not behaviour\"\ncollects the tests that exist to give an invariant a failure mode it\npreviously lacked. The packaging guard belongs there and was missing: a\ncheck that asserts nothing matched passes just as readily when its\npatterns match nothing at all, which is exactly how `.github` and\n`Agents.*` came to guard nothing while the suite stayed green.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Say what stops the wrong files reaching PyPI in How it ships\n\nThe section covers the checks that stop a broken wheel being published -\nthe abi3 audit, the end-to-end install job - but not the one that checks\nwhat is *in* the artifact. Both halves of that check are worth stating:\na missing runtime file fails on first use and gets reported, while an\nextra one ships quietly.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n---------\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-10T06:11:31+02:00",
          "tree_id": "0b67cf5e76359741e33278057c55f5e35fe55adf",
          "url": "https://github.com/jannikmi/timezonefinder/commit/a69f03ca1d926c51ebf972349144b7aa37bee440"
        },
        "date": 1786335174374,
        "tool": "pytest",
        "benches": [
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[random-in_memory]",
            "value": 113.16328964764071,
            "unit": "iter/sec",
            "range": "stddev: 0.00039600539074657616",
            "extra": "mean: 8.836788000010642 msec\nrounds: 66 on Intel(R) Xeon(R) 6973P-C @ 4.1992 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[unique_shortcut-in_memory]",
            "value": 378.27992336077784,
            "unit": "iter/sec",
            "range": "stddev: 0.000021765108810534807",
            "extra": "mean: 2.643544999997971 msec\nrounds: 329 on Intel(R) Xeon(R) 6973P-C @ 4.1992 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[ambiguous_shortcut-in_memory]",
            "value": 39.062940983985044,
            "unit": "iter/sec",
            "range": "stddev: 0.0005172377323306261",
            "extra": "mean: 25.599710999998138 msec\nrounds: 50 on Intel(R) Xeon(R) 6973P-C @ 4.1992 GHz"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "49699333+dependabot[bot]@users.noreply.github.com",
            "name": "dependabot[bot]",
            "username": "dependabot[bot]"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "a32de1afbbd2d3a1a5d222e9de85f6cb405fc965",
          "message": "Bump pypa/cibuildwheel from 4.1.1 to 4.2.0 (#496)",
          "timestamp": "2026-08-10T14:10:37+02:00",
          "tree_id": "9b3748053d4689d2d00d5e68aaaedd6abdca15ca",
          "url": "https://github.com/jannikmi/timezonefinder/commit/a32de1afbbd2d3a1a5d222e9de85f6cb405fc965"
        },
        "date": 1786363921721,
        "tool": "pytest",
        "benches": [
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[random-in_memory]",
            "value": 113.29629450876027,
            "unit": "iter/sec",
            "range": "stddev: 0.00024311858679197245",
            "extra": "mean: 8.82641399999784 msec\nrounds: 87 on AMD EPYC 9V45 96-Core Processor @ 4.4787 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[unique_shortcut-in_memory]",
            "value": 400.6973737086171,
            "unit": "iter/sec",
            "range": "stddev: 0.00015491134604192158",
            "extra": "mean: 2.4956490000036524 msec\nrounds: 278 on AMD EPYC 9V45 96-Core Processor @ 4.4787 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[ambiguous_shortcut-in_memory]",
            "value": 40.113156004033954,
            "unit": "iter/sec",
            "range": "stddev: 0.0008176728820422246",
            "extra": "mean: 24.92947700000059 msec\nrounds: 50 on AMD EPYC 9V45 96-Core Processor @ 4.4787 GHz"
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
          "id": "9e3ac2c272dcc1a24c306b18e77e522cfcd7e0d6",
          "message": "make names and docstrings describe what the code does (#507)\n\nShips three ledger entries (TEST-6, TEST-8, TEST-10) plus one finding from a\nwide-angle review, all on one theme: code whose name or docstring contradicts\nwhat it does. No behaviour change.\n\n- TimezoneFinder.timezone_at documents that the last remaining zone is returned\n  without a point in polygon test, and that this is correct only where the data\n  covers every point - certain_timezone_at is the method that tests every\n  candidate. The optimisation was explained in comments but not where\n  help(TimezoneFinder) and the API page show it.\n- test_rectify_coords_valid/_invalid were named for a rectify_coords that does\n  not exist; both call validate_coordinates. The first is deleted as subsumed by\n  test_validate_coordinates_accepts_finite_values, which covers all four of its\n  distinct corners and asserts the return value; the second is renamed\n  test_validate_coordinates_rejects_out_of_range.\n- test_single_element_arrays_should_not_occur asserted that they do occur. Its\n  triple-quoted string sat after the first statement, so it was a discarded\n  expression rather than a docstring and reached neither --collect-only nor a\n  failure report - leaving the contradicting name as the only thing a reader saw.\n  Renamed test_single_element_arrays_round_trip, string moved above the body.\n- Dropped a stale comment duplicated across the last two lines of main_test.py,\n  reading as a to-do for what TestTimezonefinderClassTestMEM already does.\n\nLedger: TEST-6/8/10 deleted as shipped; TEST-9's anchor updated for the rename.\nAdds API-2 (every submodule reachable as a package attribute, so the public API\nis wider than __all__ says) and PERF-1 (is_ocean_timezone runs a regex on the\ntimezone_at_land path), both open and both blocked - one on a maintainer\ndecision, one on a measurement. A scope note now points structural work at the\nroadmap (#506) and states the test for what belongs in the ledger at all.\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-13T03:16:45+02:00",
          "tree_id": "bd97e60b0cfabb9979b72646b1b64235a1add4f9",
          "url": "https://github.com/jannikmi/timezonefinder/commit/9e3ac2c272dcc1a24c306b18e77e522cfcd7e0d6"
        },
        "date": 1786583886816,
        "tool": "pytest",
        "benches": [
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[random-in_memory]",
            "value": 72.7763848781766,
            "unit": "iter/sec",
            "range": "stddev: 0.0005521433492322375",
            "extra": "mean: 13.740721000004896 msec\nrounds: 60 on AMD EPYC 7763 64-Core Processor @ 3.2387 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[unique_shortcut-in_memory]",
            "value": 232.75121478675734,
            "unit": "iter/sec",
            "range": "stddev: 0.00018652182254459113",
            "extra": "mean: 4.296433000000377 msec\nrounds: 192 on AMD EPYC 7763 64-Core Processor @ 3.2387 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[ambiguous_shortcut-in_memory]",
            "value": 24.831777125859308,
            "unit": "iter/sec",
            "range": "stddev: 0.0006037202365882388",
            "extra": "mean: 40.27098000000251 msec\nrounds: 50 on AMD EPYC 7763 64-Core Processor @ 3.2387 GHz"
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
          "id": "3c4253bd19a412d884b0b1012983b9f91ecdb857",
          "message": "Add roadmap-pass agent skill for advancing issue #506 (#508)\n\n* Add roadmap-pass agent skill for advancing issue #506\n\nAdvances the structural work tracked by roadmap issue #506 one pass at a\ntime: select an eligible item, check the sequencing preconditions #506\nrecords, put the item's open design decisions to the maintainer as\nconcrete choices, and only then implement one releasable slice.\n\nUnlike its code-quality-pass sibling it deliberately asks rather than\ndeciding alone, because a roadmap item's design choices outlive the pass.\nState is derived from the tracker rather than a progress file, so repeated\nand concurrent passes are idempotent.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Quote the skill description so YAML keeps all of it\n\nAn unquoted `#` preceded by a space starts a comment in a plain YAML\nscalar, so the roadmap-pass description was stored as \"Advances the\nstructural work tracked by roadmap issue\" - 53 of 831 characters, with\nevery trigger phrase discarded. The skill still loaded; it just stopped\nbeing discoverable by anything but its name.\n\ntests/test_agent_skills.py parses the frontmatter of every skill under\n.claude/skills/ and fails when the value a YAML parser stores ends before\nthe value the file writes.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n---------\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-13T12:12:48+02:00",
          "tree_id": "a565630af02e262ec724dd7f8b3ee41f8969414e",
          "url": "https://github.com/jannikmi/timezonefinder/commit/3c4253bd19a412d884b0b1012983b9f91ecdb857"
        },
        "date": 1786616043287,
        "tool": "pytest",
        "benches": [
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[random-in_memory]",
            "value": 71.73544027014812,
            "unit": "iter/sec",
            "range": "stddev: 0.00016051648161068263",
            "extra": "mean: 13.940111000003697 msec\nrounds: 60 on AMD EPYC 9V74 80-Core Processor @ 2.8530 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[unique_shortcut-in_memory]",
            "value": 219.5922391710443,
            "unit": "iter/sec",
            "range": "stddev: 0.00003751553283378558",
            "extra": "mean: 4.553895000000807 msec\nrounds: 182 on AMD EPYC 9V74 80-Core Processor @ 2.8530 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[ambiguous_shortcut-in_memory]",
            "value": 24.447107875361155,
            "unit": "iter/sec",
            "range": "stddev: 0.00047980202129747294",
            "extra": "mean: 40.90463399999322 msec\nrounds: 50 on AMD EPYC 9V74 80-Core Processor @ 2.8530 GHz"
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
          "id": "8f59f5e5ac0a89596365280315fd30e6290820c1",
          "message": "Stop two tests leaking numpy's global state, and give three silent drifts a failure mode (#511)\n\n* TEST-4: stop two tests leaking numpy's global error state\n\n`np.seterr` and the warning filters are process-global. `test_overflow`\n(tests/main_test.py) and `test_inside_polygon` (tests/utils_test.py, six\nparametrisations) each set them and never restored them, so every test\ncollected afterwards ran with `under` promoted from `ignore` to `warn` -\nand which module pytest collected first decided the state the other ran\nunder. The filters were undone only incidentally, by pytest's per-test\n`catch_warnings()`, not by the tests themselves.\n\nbenchmarks/conftest.py already had the correct pattern. Split it into a\n`strict_numpy_errors` context manager plus the thin `strict_numpy_warnings`\nfixture, both in tests/auxiliaries.py where the other shared helpers live,\nre-exported through the conftest of each suite. Both call sites now request\nthe fixture. The context manager form is what makes the seam directly\ntestable: two tests assert the promotion and the restore, the latter against\na deliberately distinct starting state so it cannot pass by coincidence.\n\n* DEAD-3: drop the negative-zone-id guard the dtype check makes unreachable\n\n`ZoneCollection.validate_structure` rejects any `poly_zone_ids` whose\n`dtype.kind != \"u\"` a dozen lines before taking `.min()`, so the array is\nunsigned by then and `if min_zone_id < 0` cannot fire. Left in, it reads as\nthe guard against negative zone ids - which matters because the real\nnegative-id exposure is elsewhere and still open (`zone_id_of` /\n`zone_name_from_id` index directly, BUG-1 in the ledger).\n\nThe validators had no tests at all, so what the class actually promises is now\npinned: the unsigned-dtype rejection that makes a negative id unrepresentable,\nthe ordering and max-id rules, and the shape zone_positions() returns.\n\n* DUP-3: enforce the zone-id ordering rule in one place\n\n`validate_structure` and `zone_positions` each walked `poly_zone_ids`\nelement by element checking it was non-decreasing, and each raised the same\nmessage built from its own locals - two places to edit if the rule changes,\nand two Python-level passes over every polygon during data generation.\n\nThe validator's scan moves into `_validate_non_decreasing`, beside the other\nmodule-level `_validate_*` helpers. `zone_positions` drops its copy: the\nvalidator is a pydantic `model_validator(mode=\"after\")`, so it runs at\nconstruction, and `poly_zone_ids` is only ever read afterwards - the copy\ncould fire only if a caller mutated the array in place, which nothing does.\nIts docstring now says what it is entitled to assume.\n\n* TEST-9: declare the out-of-range coordinate table once\n\nThe same seven (lng, lat) tuples - each one representable step outside the\nvalid WGS84 range - were written out verbatim in tests/main_test.py and again\nin the parametrize list of tests/utils_test.py, and only the first copy\ncarried the comment explaining what makes them interesting. Adding a corner\nto one left the other testing a smaller set, with nothing to notice.\n\nThe table moves to tests/locations.py, which already holds the shared\ncoordinate tables, and both modules import it. Collection count is unchanged\nat 551 across the two modules.\n\n* TYPE-1: annotate the shortcut compilation chain for what it is actually passed\n\nBoth annotations in the chain were the wrong way round.\n`check_shortcut_sorting(polygon_ids: np.ndarray, ...)` is only ever called by\n`process_single_hex` with the `list[int]` that `optimise_shortcut_ordering`\nreturns, and it in turn passes the `np.ndarray` produced by `all_zone_ids[\npolygon_ids]` to `has_coherent_sequences(lst: list[int])`.\n\nWidened rather than swapped: tests/shortcut_test.py calls\n`has_coherent_sequences` with real lists, so both forms are live. Also gives\n`check_shortcut_sorting` the `-> None` its siblings have. mypy reports the\nsame four pre-existing errors on this file as before (scripts/ is outside the\npre-commit mypy hook's scope).\n\n* CI-1: fail when the five declarations of the supported Python versions drift\n\npyproject.toml (requires-python plus one classifier per minor version),\ntox.ini (the py{...} envlist factors), build.yml (the test matrix and\nCIBW_BUILD_VERSIONS) and setup.py (py_limited_api) all state the same fact and\nnone can read the others. Two \"must match\" comments already said so and\nnothing enforced them.\n\nThe failure is silent in both directions: a classifier added without a matrix\nentry ships a version the package claims and CI never runs, and a\nrequires-python raised without the abi3 base moved builds wheels tagged for an\ninterpreter no longer supported.\n\nFive assertions, each verified to fail against the specific one-sided edit it\ntargets. Both existing comments now name the test. Same shape and reasoning as\ntests/test_benchmark_workflows.py.\n\n* Record this quality pass in the changelog\n\n* Record pass 7 in the findings ledger\n\nDeleted as shipped: TEST-4, TEST-9, DEAD-3, DUP-3, TYPE-1. Deleted as fixed\nby unrelated work: TEST-7 (the wheel/venv interpreter mismatch, closed by\nPR #494 pinning `uv build --python sys.executable`).\n\nAdded DEAD-4 (an unreachable None guard in `Hex.poly_candidates`) and REND-4\n(three cosmetic leftovers in scripts/reporting.py). Coverage log gains pass 7;\n.github/workflows/ is no longer an unswept area, leaving only docs/ prose.",
          "timestamp": "2026-08-14T07:12:18+02:00",
          "tree_id": "04c11d0d7f692961b0ba808524358524af99181f",
          "url": "https://github.com/jannikmi/timezonefinder/commit/8f59f5e5ac0a89596365280315fd30e6290820c1"
        },
        "date": 1786684423782,
        "tool": "pytest",
        "benches": [
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[random-in_memory]",
            "value": 94.1018910809595,
            "unit": "iter/sec",
            "range": "stddev: 0.000493385438514795",
            "extra": "mean: 10.626779000006081 msec\nrounds: 66 on INTEL(R) XEON(R) PLATINUM 8573C @ 3.4996 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[unique_shortcut-in_memory]",
            "value": 302.06689271308164,
            "unit": "iter/sec",
            "range": "stddev: 0.00016859601670266523",
            "extra": "mean: 3.310525000003395 msec\nrounds: 235 on INTEL(R) XEON(R) PLATINUM 8573C @ 3.4996 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[ambiguous_shortcut-in_memory]",
            "value": 30.591867592516778,
            "unit": "iter/sec",
            "range": "stddev: 0.0007542570951573416",
            "extra": "mean: 32.6884260000071 msec\nrounds: 50 on INTEL(R) XEON(R) PLATINUM 8573C @ 3.4996 GHz"
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
          "id": "8ceae1d6262131895b0055180fe95a0a14e6bdfe",
          "message": "Add a cut-release skill, and give the quality pass a diff budget (#512)\n\n* Make the quality pass work its ranking down to a diff budget\n\nThe pass took one coherent theme and stopped; it now takes the ledger's\nhighest-priority findings one at a time until ~400 changed lines are spent,\nso the ranking rather than a common story is what holds the PR together.\nEach item lands as its own commit naming its ledger entry, the budget is\nmeasured against the merge base with the ledger excluded and checked between\nitems rather than mid-item, and a ranking that runs dry ends the pass as\nlegitimately as a spent budget. The branch claim in §2.1 follows: it claims\nonly what it already holds, so a pass re-pushes after every finished item.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Add a cut-release skill that proposes the bump and stops\n\nTurns the accumulated `X.X.X (unreleased)` changelog section into a released\nversion, in two halves split by the maintainer's merge. Prepare checks the\nsection is release-ready and complete against every commit since the last tag,\nproposes patch/minor/major as three concrete version numbers with the bullets\nbehind each, stops for the decision, then lands the bump as a release PR. Tag\nruns only after that PR is merged and asks again, since the tag is the publish\nand PyPI will not let a version take it back.\n\nRecords what the pipeline makes non-obvious: the tag-push run re-reads\npyproject.toml at the tagged commit; the release commit is the bump and the\nchangelog and nothing else, so `make reports` must not run in it; and the tag\nhas to be pushed promptly after the merge, because the master push run's own\nrelease job creates the GitHub Release and with it the tag, after which\npushing that tag is a no-op that fires no webhook.\n\nCLAUDE.md's claim that regenerating data warrants a minor bump is corrected:\nupdate_data.sh bumps patch and the last four data releases were patches.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n---------\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-14T07:22:26+02:00",
          "tree_id": "ec4e3362dff760a796f4bf4facd476336473ca75",
          "url": "https://github.com/jannikmi/timezonefinder/commit/8ceae1d6262131895b0055180fe95a0a14e6bdfe"
        },
        "date": 1786685017923,
        "tool": "pytest",
        "benches": [
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[random-in_memory]",
            "value": 73.91733646863389,
            "unit": "iter/sec",
            "range": "stddev: 0.0009700183113695445",
            "extra": "mean: 13.528625999995825 msec\nrounds: 58 on AMD EPYC 7763 64-Core Processor @ 3.2439 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[unique_shortcut-in_memory]",
            "value": 230.17581980001603,
            "unit": "iter/sec",
            "range": "stddev: 0.00015826920416328486",
            "extra": "mean: 4.344504999998833 msec\nrounds: 190 on AMD EPYC 7763 64-Core Processor @ 3.2439 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[ambiguous_shortcut-in_memory]",
            "value": 25.49469914215551,
            "unit": "iter/sec",
            "range": "stddev: 0.0007074296761031074",
            "extra": "mean: 39.22383999999823 msec\nrounds: 50 on AMD EPYC 7763 64-Core Processor @ 3.2439 GHz"
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
          "id": "4f6da3f39e30939ceb6079a1049efab0e7f0d36a",
          "message": "Store holes that duplicate a boundary polygon as a reference (#509)\n\n* store holes that duplicate a boundary polygon as a reference\n\nAlmost every hole is an enclave: the upstream builder cuts it into the\nsurrounding zone using exactly the ring it also emits as the enclosed\nzone's own boundary polygon. Measured against release 2026c, 729 of 756\nhole rings trace the same closed path as some boundary polygon - the\nsame geometry stored under two IDs.\n\nThe hole coordinate file now holds only the 27 rings without a twin, and\nholes/poly_ref.npy records per hole id which boundary polygon to read\ninstead (v >= 0), or where its own ring sits (v < 0, at -(v + 1)). Hole\nids stay dense, so the hole registry and every caller above coords_of()\nis untouched, and the bbox vectors stay valid verbatim - a referenced\nring is identical, so its bbox already equals the boundary's. The bbox\nrejection test keeps reading a flat array with no indirection.\n\nHole data drops from ~2.0 MiB to ~0.16 MiB, on disk and in RAM alike.\n\nMatching compares integer coordinates in a canonical form (rotated to\nthe lexicographically smallest vertex, both winding directions tried),\nwith bbox and vertex count as a prefilter only - no tolerance, so two\nrings either trace the same path or they do not. Verified equivalent to\nthe all-inline data over both point-in-polygon backends, including every\nvertex and edge midpoint of the rings whose stored form changed.\n\nPOLYGON_LAYOUT_VERSION becomes 2 so a released version rejects this data\ninstead of resolving hole ids against the compacted file and returning\nplausible wrong answers; layout 1 stays readable, so a bin_file_location\ndirectory compiled by an older release still works.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* record the broken parse targets, and replace a test that could not fail\n\ntest_packaged_references_resolve_to_the_same_ring compared\nholes.coords_of(id) against boundaries.coords_of(ref), but resolving a\nreference *is* returning the boundary ring, so it asserted an expression\nagainst itself. Removed rather than repaired: the property it was\nreaching for is decided at build time, and on packaged data the bbox\nvectors are the only independent evidence - they are computed from the\noriginal hole rings before deduplication and never rewritten, so a\nreference pointing at the wrong polygon resolves to a ring whose extent\ndisagrees. Mutation-checked: an off-by-one in one reference fails it.\n\nAdded test_packaged_dedup_ratio_meets_the_floor, so the shipped data is\nheld to the bar the converter enforces even when the converter did not\nproduce it.\n\npotential-improvements.md gains TOOL-3: `make parse` and `make testparse`\nboth fail immediately with ModuleNotFoundError on master, since they\ninvoke the converter by path and its own `from scripts...` imports\ncannot resolve.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* move hole data integrity off the runtime path\n\nHoleArray._validate_refs ran on every construction, re-deriving in each\nuser's process something the build had already established - and paying\nfor it on an init path that latency-sensitive services carry per thread.\n\nThe checks now live in scripts/data_integrity.py and run in the two\nplaces where they mean something: the converter, over the files it just\nwrote, and the test suite, over the files the repository ships. One\nimplementation, so the two cannot drift into asserting different things.\n\nOff the init path the check can afford to be thorough rather than cheap,\nso it now does what the runtime version could not: resolve every hole\nring and compare its extent against the bounding box stored for that\nhole. Those bboxes are computed from the original rings before\ndeduplication and never rewritten, which makes them evidence independent\nof the references - a reference pointing at the wrong polygon resolves\nto a real, valid ring and is caught only here.\n\nThe deduplication ratio floor is split into its own check: it is a claim\nabout the upstream dataset, not about file consistency, and a small\ncustom region can legitimately have few enclaves while being perfectly\nwell formed.\n\nCLAUDE.md and CONTRIBUTING.md record the general rule, since the\ntempting version of this - a defensive check at load time - is both\nslower and, being forced to stay cheap, shallower.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* do not refuse to compile custom data with few enclave-shaped holes\n\nThe deduplication floor aborted the converter for any dataset below it,\nbut scripts/file_converter.py is documented for \"any other data in this\nformat\" (docs/2_use_cases.rst), and a dataset whose holes are ordinary\ninterior rings rather than enclaves is perfectly valid: those rings take\nthe inline path and answer correctly, the output is merely larger. Such\na user got an abort quoting \"the upstream dataset\", which is not their\ndataset, for data the fallback would have compiled correctly.\n\nThe floor is a claim about the packaged dataset specifically - the same\nreason validate_hole_dedup_ratio is already separate from the structural\ncheck - so it is enforced there and only there, by the test suite over\nthe packaged binaries. A real upstream regression still blocks the\nweekly data-update PR, which merges only once CI passes. The converter\nnow reports the ratio instead, naming both readings of a low value.\n\nReported by Codex review on #509.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* keep one polygon layout version instead of bumping it\n\nPOLYGON_LAYOUT_VERSION went to 2 so that a released version would reject\ndeduplicated hole data rather than resolve hole ids against a compacted\nfile. But layout 1 has never been released - it arrived with the\nper-axis coordinate encoding in 5947b1b, which is not an ancestor of\n8.2.5 - so no version in the wild reads or writes it, and there was\nnothing for version 2 to protect against. The same fact voids the other\nhalf of the justification: no earlier release wrote layout 1 either, so\nthe READABLE_LAYOUT_VERSIONS set was keeping open a compatibility path\nwith data that cannot exist.\n\nLayout 1 now simply describes what ships: per-axis coordinates and, for\na hole collection, only the rings that are not references. Both changes\nland in the same unreleased version, so they need one marker between\nthem, not two.\n\nThis takes boundaries/coordinates.fbs out of the diff. It had been\nrewritten for a single byte - the version stamp, at offset 22 - with all\n1322 polygons and 7,925,313 vertices identical either way. Regenerated\nfrom the pinned 2026c source; the file is now byte-identical to master\nand only the hole files change.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* require poly_ref.npy instead of falling back to inline rings\n\nThe fallback read a hole directory without poly_ref.npy as one where\nevery ring is stored inline. That was justified as compatibility with\ndata compiled by an older release - but this layout has never been\nreleased, so no such directory exists. What the branch actually covered\nwas data compiled from an intermediate master checkout, which per\nCLAUDE.md needs no compatibility.\n\nWorse, the interpretation it guessed at is unverifiable: the coordinate\nfile of a deduplicated directory holds only the inline rings, so hole\nids do not index it, and reading it that way returns wrong rings rather\nthan failing. Requiring the file means a missing one raises naming\nitself.\n\nAlso drops the `is None` branch from coords_of, which ran per hole\npoint-in-polygon test, and the corresponding branches from the two\nintegrity checks.\n\nThe equivalence test built its all-inline reference dataset by deleting\npoly_ref.npy; it now writes an all-negative vector instead, which is the\nsame directory expressed in the layout that ships.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* add the hole-removal experiment to prototypes/\n\nDropping holes is the obvious next step after storing them as\nreferences, and it looks safe on the coverage evidence: every hole is\nfully covered by other zones. The experiment shows it is not, and that\nis worth keeping runnable rather than describing.\n\nprototypes/hole_removal_impact.py rewrites the hole files of a mirrored\ndata directory - symlinking the rest, since the boundary coordinates\nalone are ~63 MB - and diffs timezone_at over interior points of every\nhole plus a uniform global sample. Dropping only the 27 holes with no\nboundary twin changes 160 of 6,048 hole-interior answers; dropping all\nof them changes 1,703, and 16 of 20,000 uniform points. The changes are\nwrong, not merely different: Asia/Hebron -> Asia/Jerusalem,\nAmerica/Argentina/Cordoba -> America/Asuncion.\n\nIts FINDINGS block records why the coverage argument is insufficient:\ncoverage puts the right zone among the shortcut candidates, ordering\ndecides whether it is reached first. Filed as #513.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* record the check that makes the no-internal-compatibility rule work\n\nBoth files already say internal code, data formats and binary assets\nneed no backward compatibility - CONTRIBUTING.md emphatically. The rule\nwas there and still did not prevent a fallback for \"a data directory\ncompiled by an older release\", because the step it depends on was\nunwritten: confirming that the older release exists.\n\nOn master an unreleased format marker is indistinguishable from a\nshipped one. POLYGON_LAYOUT_VERSION = 1 read as a settled fact while\nbeing unreleased, so a compatibility branch for it looked load-bearing,\nand guarding it cost a version bump that rewrote the 63 MB coordinate\nbinary for one changed byte.\n\nAmended into the existing bullets in both files rather than added as new\nguidance, so neither restates the rule it qualifies.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n---------\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-14T10:01:44+02:00",
          "tree_id": "379ac95ce1740aec9b6862bb28d85c75d7b725d5",
          "url": "https://github.com/jannikmi/timezonefinder/commit/4f6da3f39e30939ceb6079a1049efab0e7f0d36a"
        },
        "date": 1786694592237,
        "tool": "pytest",
        "benches": [
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[random-in_memory]",
            "value": 68.50192925405374,
            "unit": "iter/sec",
            "range": "stddev: 0.0008614080662329286",
            "extra": "mean: 14.598129000006566 msec\nrounds: 59 on Intel(R) Xeon(R) Platinum 8370C CPU @ 2.80GHz @ 2.8000 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[unique_shortcut-in_memory]",
            "value": 234.25929786808766,
            "unit": "iter/sec",
            "range": "stddev: 0.00006839260076048306",
            "extra": "mean: 4.268774000010467 msec\nrounds: 195 on Intel(R) Xeon(R) Platinum 8370C CPU @ 2.80GHz @ 2.8000 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[ambiguous_shortcut-in_memory]",
            "value": 23.9899861959192,
            "unit": "iter/sec",
            "range": "stddev: 0.0007425216467151772",
            "extra": "mean: 41.684059000004936 msec\nrounds: 50 on Intel(R) Xeon(R) Platinum 8370C CPU @ 2.80GHz @ 2.8000 GHz"
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
          "id": "76f63966e5d6b2a8fb933b4b8d41a3c91bc644b3",
          "message": "Make the data report generator derive its figures and describe its own types (#514)\n\n* REP-2: take the H3 cell count from h3 instead of a ladder of literals\n\n`calculate_shortcut_index_stats` derived `possible_cells` - the denominator\nof every coverage figure in docs/data_report.rst - from hard-coded constants\nfor resolutions 0 to 4, and fell through to `possible_cells = total_entries`\nfor anything else. That fallback makes `coverage_ratio` exactly 1.0, so an\nuntabulated resolution reports complete H3 coverage rather than failing.\n\nThe surrounding `except ImportError` could not fire at all: h3 is a runtime\ndependency of the package, not an optional one, and its fallback was the same\nsilent full-coverage value.\n\n`h3.get_num_cells` returns exactly the tabulated numbers (122, 842, 5882,\n41162, 288122), so the committed report regenerates byte-identically.\nThe h3 and SHORTCUT_H3_RES imports move to module level, matching every other\nmodule in scripts/ - neither guarded a cycle, and the resolution being a\nmodule attribute is what lets the new tests parametrize over it.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* BIG-2/REND-4: stop round-tripping the polygon count through its own label\n\n`print_polygon_distribution_table` built `distribution_items` as\n(count, frequency) pairs, rebound the same name to (label, frequency) by\nformatting the count into \"N polygon(s)\", then recovered the count with\n`int(category.split()[0])` to look up the example timezone. The label's\nwording was load-bearing for a lookup that had the number all along.\n\nThe function is also annotated `-> list[list[str]]` and documents a return\nvalue, while having no return statement at all; its one caller discards the\nresult. Both now say `None`.\n\nNeither changes the report: docs/data_report.rst regenerates byte-identically.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* TYPE-3/TYPE-2: make scripts/reporting.py's annotations describe its code\n\nmypy is not run over scripts/ by the pre-commit hook, and the module had\ndrifted 17 errors away from its own signatures. Running it by hand:\n\n- `calculate_shortcut_index_stats` claimed `dict[str, int | float]` while\n  returning two `list[int]` distributions, which the two `print_frequencies`\n  calls consume as lists. It and `load_binary_data`'s nine-key bag are now\n  `ShortcutIndexStats` / `BinaryData` TypedDicts in scripts/configs.py, where\n  this repo keeps its script-side types.\n- `redirect_output_to_file` declared `str` and is passed `DATA_REPORT_FILE`,\n  a Path, at all three call sites - its context-manager sibling already said\n  `str | Path`.\n- `main` was annotated `-> None` while returning 0 and 1 to `exit()`.\n- `print_rst_table` / `compute_column_widths` declared `list[list[str]]` rows\n  but render every cell through `str()`, and are handed ints and floats. They\n  take `TableRows` (a covariant Sequence, since list is invariant).\n- `generate_polygon_statistics_table`'s implicit-Optional `additional_rows`.\n- `generate_metrics_rows` took a `metric_type` its body never read; all four\n  call sites passed a label that went nowhere.\n\n`generate_metrics_rows`'s values are `Mapping[str, object]` rather than a\nnumeric type, so its non-numeric fallback stays reachable rather than being\ndeleted to satisfy an annotation.\n\nSince CI cannot check any of this, two tests assert each TypedDict's keys\nagainst the dict actually returned. docs/data_report.rst regenerates\nbyte-identically.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* REND-2/REND-4: look values up where they are declared\n\n`_memory_mode_label` spelled out \"in-memory\"/\"file-based\", which\n`PARAM_LABELS` - the module's declared display vocabulary, used by every other\nlabel - already maps from `in_memory`/`file_based`. Renaming a label there\nwould have left the comparison bullets on the old wording while the tables\nabove them moved to the new one.\n\nIn scripts/reporting.py the shortcut index's field widths were a local named\n`ENTRY_KEY_SIZE_BYTES` (so it read as a module constant while being rebound\nper call) plus two bare literals explained only by trailing comments. All\nthree are now named module constants. The median-polygons entry dropped a\n`list()` inside `sorted()`.\n\nRendering both report families against the same inputs before and after gives\nbyte-identical output.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* DEAD-1: delete five definitions nothing references\n\n- `scripts/utils.py`: `load_json`, `load_pickle` and `write_pickle`. The\n  pickle pair was the only thing keeping `import pickle` in a data-generation\n  path.\n- `timezonefinder/_numba_replacements.py`: `i8`. The shim exists to mirror the\n  numba names the package imports when numba is absent, and that import line\n  asks for `njit, boolean, Array, i4, f8` - an extra class is an unexercised\n  claim about the fallback. Verified by blocking `import numba` and taking the\n  fallback branch end to end.\n- `tests/auxiliaries.py`: `convert_to_reduced_timezone`, self-documented as\n  \"unused, but kept for future reference\", along with the commented-out call\n  in `single_location_test` and the now-unused import.\n\n`REDUCED_TIMEZONE_MAPPING` in tests/locations.py is left in place, now with no\nconsumer; it is reference data rather than code, and it goes to the ledger.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* DEAD-4: drop a guard against a None Hex._init_candidates cannot leave behind\n\n`poly_candidates` called `_init_candidates()`, re-read `_poly_candidates`,\nand returned an empty set if it were still `None`. No path through\n`_init_candidates` leaves it unset - it early-returns when already\ninitialised, assigns `set(range(nr_of_polygons))` at resolution 0, and\notherwise assigns the accumulated set - so the branch could not fire. It read\nas a guard against an uninitialised cache while meaning \"no candidate\npolygons\", which would have turned a converter bug into silently missing\nshortcuts instead of a failure.\n\n`_init_candidates` now returns the set it initialises, so the property does\nnot re-read the attribute and needs no guard. Its local accumulator was also\nannotated `HexIdSet` while holding polygon ids; both aliases are `set[int]`,\nso nothing could catch it.\n\nThe property had no direct test - it is reached only through `polys_in_cell`\nduring shortcut generation - so it gains one.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Record this quality pass in the changelog\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Record pass 8 in the findings ledger\n\nDeletes the five entries this pass shipped (DEAD-1, DEAD-4, TYPE-3, REND-2,\nREND-4) and narrows TYPE-2 to the two sites still open.\n\nCorrects BIG-2: its title claimed 13 branches / 57 statements, over ruff's\nPLR0912/PLR0915 defaults. Replacing the hard-coded H3 ladder removed six\nbranches, so it now trips neither and the entry is readability only.\n\nAdds DEAD-5 (REDUCED_TIMEZONE_MAPPING, orphaned by DEAD-1 and annotated as a\nset while being a dict), BIG-4 and TOOL-4.\n\nBoth new entries are stated as they look after rebasing onto #509, which\nlanded mid-pass: it rewrote load_binary_data through PolygonArray/HoleArray,\nso BIG-4 keeps only the hole branch that silently yields empty lists rather\nthan the size complaint it was written about. #509 also took the id TOOL-3\nfor a separate finding, so the mypy-exclusion entry is TOOL-4.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n---------\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-14T10:31:41+02:00",
          "tree_id": "44113dd2737ccb993464be784e042939f6387cea",
          "url": "https://github.com/jannikmi/timezonefinder/commit/76f63966e5d6b2a8fb933b4b8d41a3c91bc644b3"
        },
        "date": 1786696389778,
        "tool": "pytest",
        "benches": [
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[random-in_memory]",
            "value": 74.59858501404895,
            "unit": "iter/sec",
            "range": "stddev: 0.0001886781308507913",
            "extra": "mean: 13.405079999998293 msec\nrounds: 61 on AMD EPYC 7763 64-Core Processor @ 3.2425 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[unique_shortcut-in_memory]",
            "value": 230.96987252083204,
            "unit": "iter/sec",
            "range": "stddev: 0.0000876223724483392",
            "extra": "mean: 4.329568999999367 msec\nrounds: 194 on AMD EPYC 7763 64-Core Processor @ 3.2425 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[ambiguous_shortcut-in_memory]",
            "value": 25.594160763886407,
            "unit": "iter/sec",
            "range": "stddev: 0.00033507674877212727",
            "extra": "mean: 39.07141199999842 msec\nrounds: 50 on AMD EPYC 7763 64-Core Processor @ 3.2425 GHz"
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
          "id": "97a8e34180daced9c2efb9b0e7867db2b613169f",
          "message": "Make the file converter runnable again, and type-check the directory it lives in (#515)",
          "timestamp": "2026-08-15T08:41:03+02:00",
          "tree_id": "3c1e49cbbf892fdea7bf267f5291b9c9aaf45ebe",
          "url": "https://github.com/jannikmi/timezonefinder/commit/97a8e34180daced9c2efb9b0e7867db2b613169f"
        },
        "date": 1786776139651,
        "tool": "pytest",
        "benches": [
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[random-in_memory]",
            "value": 72.80164158966797,
            "unit": "iter/sec",
            "range": "stddev: 0.0015072944884529295",
            "extra": "mean: 13.735953999997719 msec\nrounds: 57 on AMD EPYC 9V74 80-Core Processor @ 2.8708 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[unique_shortcut-in_memory]",
            "value": 228.00971686137484,
            "unit": "iter/sec",
            "range": "stddev: 0.00005171773741419775",
            "extra": "mean: 4.385778000013829 msec\nrounds: 185 on AMD EPYC 9V74 80-Core Processor @ 2.8708 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[ambiguous_shortcut-in_memory]",
            "value": 24.45620227999062,
            "unit": "iter/sec",
            "range": "stddev: 0.0007756763571677018",
            "extra": "mean: 40.88942299999587 msec\nrounds: 50 on AMD EPYC 9V74 80-Core Processor @ 2.8708 GHz"
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
          "id": "3dca95ab33a36d586259b1af0dfac37167ae3c27",
          "message": "CLI: annotate delimited rows from stdin with their timezone (#517)\n\n* feat(cli): add --stdin streaming mode for batch lookups\n\nAdd a --stdin flag that reads lng,lat coordinate pairs from stdin,\none per line, and writes one timezone result per line to stdout.\n\nThe TimezoneFinder instance is constructed once, amortising the\ninitialisation cost across the entire input. This makes the CLI\nusable in shell pipelines:\n\n    cat points.csv | timezonefinder --stdin\n\nDesign decisions:\n- Malformed or blank lines produce a warning on stderr and an empty\n  line on stdout, so a caller reading one line per query stays in\n  step with its inputs (same contract as single-query mode).\n- --stdin and -v are mutually exclusive (verbose output is per-query\n  and would break the one-line-per-result contract).\n- -f/--function applies to the whole stream.\n- The existing single-pair form (timezonefinder LNG LAT) is unchanged.\n\nAlso add timezonefinder/__main__.py so that `python -m timezonefinder`\nworks (needed for running tests without installing the console script\nglobally).\n\nCloses #504.\n\nSigned-off-by: badhope <weed33834@users.noreply.github.com>\n\n* Revert the unrelated edit to the invalid-function-id message\n\nThe stdin PR also changed `4 (TimezoneFinderL.timezone_at_land)` into\n`4 (TimezoneFinderL.timezone_at_land()`, which leaves the parenthesis\nopened after `4` unclosed, so the list of valid ids renders as nested\ngarbage. Nothing asserts this string, so no test caught it.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Reject an unusable stdin line instead of ending the stream\n\nAn out-of-range coordinate parsed as two floats and only failed later,\ninside the lookup, where the ValueError was uncaught: `200,100` on line 2\nof 1000 aborted with a traceback and discarded the remaining 998 answers -\nthe outcome issue #504 singled out as hostile. NaN and infinity did the\nsame, since `float()` accepts them and the bounds check does not.\n\n`_parse_coordinate_line` now runs the package's own `validate_coordinates`\nbefore returning, so a coordinate that reaches the lookup cannot fail\nthere, and reports the reason a line was rejected by raising rather than\nreturning None. The warning quotes that reason, which the caller\npreviously had to guess: every rejected line read \"malformed input\".\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Flush each stdin result so the mode actually streams\n\n`print` leaves stdout block-buffered whenever it is not a terminal, which\nis every case `--stdin` exists for, so a consumer received nothing until\n~8 KB of results had accumulated: `tail -f coords | timezonefinder --stdin`\nproduced no output at all while the producer stayed open, despite every\nlookup having completed in milliseconds.\n\nFlushing also re-synchronises the two streams. stderr is unbuffered, so a\nwarning naming \"line 7\" used to appear before the results for lines 1-6\nwere flushed, leaving nothing to correlate it against.\n\n`flush=True` rather than reconfiguring the stream: `sys.stdout` is typed\n`TextIO`, which has no `reconfigure`, so the line-buffering form does not\ntype-check.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Exit quietly when the stdin consumer closes the pipe\n\n`timezonefinder --stdin < points.csv | head -5` printed its five lines and\nthen dumped a BrokenPipeError traceback, plus a second \"Exception ignored\nin: <_io.TextIOWrapper name='<stdout>'>\" from the interpreter's shutdown\nflush. Stopping early is how the pipelines this mode was built for are\nnormally driven, so the advertised use case ended in a traceback.\n\nRedirecting the fd to the null device before exiting is what suppresses\nthe shutdown flush; catching the error alone is not enough.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Drop the unused function_id parameter from _run_stdin\n\nDocumented as \"used only for stderr diagnostics\" and referenced nowhere in\nthe body. Ruff does not flag unused parameters, so it survived lint; the\ndocstring promising diagnostics that do not exist is the part that costs a\nreader, who has to diff the two to establish which is wrong.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Signal rejected stdin lines through the exit code\n\nAn empty output line meant two different things and the exit status was 0\nfor both: the input on that line was unusable, or the lookup genuinely\nfound no timezone there - which is what `-f 4` and `-f 5` return for every\nocean point. A script counting blank lines as ocean silently counted every\ntypo'd row as ocean too, with nothing in `$?` to contradict it.\n\nRejected lines now make the process exit 1, so the aggregate is\ndetectable without parsing stderr. A stream answered in full still exits\n0, including when every answer is a legitimate empty line.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Name only the missing coordinate, and reject coordinates with --stdin\n\nTwo consequences of making lng and lat `nargs=\"?\"`:\n\n`timezonefinder 4.89` reported \"the following arguments are required:\nlng, lat\" - naming the argument the user had just supplied. The hand-written\nreplacement for argparse's check always listed both; it now lists what is\nactually absent, as argparse did before.\n\n`timezonefinder --stdin 4.89 52.37` accepted the coordinates and discarded\nthem without a word, so appending `--stdin` to an existing invocation\nproduced a process that blocks on the terminal instead of answering. Stray\npositionals are now an error, the same treatment `--stdin -v` already got.\nThe mutual-exclusion test stops passing coordinates it never needed.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Let the CLI trade memory for lookup speed with --in-memory\n\nStreaming mode ran every lookup through the module-level singleton, which\nis `TimezoneFinder(in_memory=False)` and cannot be configured from here, so\nthe one workload whose length can amortise the extra footprint had no way\nto ask for it. `--in-memory` builds an own instance instead; ids 3 and 4\nalready built one and now pass the flag through.\n\nMeasured on a warm page cache, this is ~1.3x on the lookups themselves -\nabout 8% end-to-end over 50k points, where interpreter startup and data\nloading still dominate. It stays opt-in: the memory-mapped default is what\nkeeps this usable in a constrained container, and tens of MB is not a\nprice to charge a single query.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Route the stdin tests through run_cli\n\nFive of the six new cases inlined `subprocess.run([sys.executable, \"-m\",\n\"timezonefinder\", ...])`, duplicating the same five-line block and, more\nimportantly, exercising a different entry point than every other test in\nthe file. `run_cli` runs the installed console script precisely so that the\n`[project.scripts]` wiring is covered - as the module docstring claims - and\na `-m` invocation reaches `main` without it, so a broken entry point would\nhave left all six green.\n\n`run_cli` grows an `input` parameter, which is all the stdin cases needed;\n`test_stdin_and_verbose_are_mutually_exclusive` was already using it.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Make the -f case discriminating and cover the stdin failure modes\n\n`test_stdin_mode_respects_function_flag` sent one land point and asserted\n`Europe/Amsterdam`, which is what the default `-f 0` returns for it too, so\nit stayed green with the flag ignored entirely. It now also sends the ocean\npoint, whose answer differs between the two (`Etc/GMT+10` vs empty).\n\nAdds coverage for each defect fixed in this branch - an unusable line not\nending the stream, the warning naming line/content/reason, a genuine empty\nanswer still exiting 0, `| head -1` not raising BrokenPipeError, stray\npositionals rejected, and the missing-argument message naming only what is\nmissing. All twelve fail against the code as it stood before these fixes.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Document the CLI's streaming mode\n\nThe usage guide's syntax line listed neither `--stdin` nor `--in-memory`,\nand the note directly beneath it still told readers the CLI is \"orders of\nmagnitude slower ... as a separate Timezonefinder() instance is being\ncreated for every call\" - the exact claim `--stdin` exists to refute. A\nuser who hit the batch problem would read that note and conclude the CLI\ncould not help them.\n\nThe new section documents the contract that matters to a caller: one output\nline per input line, and an exit code that distinguishes a stream answered\nin full from one that dropped inputs, since an empty line means both. Also\ncorrects the syntax line's `{0,1,2,3,4,5}`, which has not matched the\naccepted choices since id 2 was removed.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Add the changelog entry for the CLI streaming mode\n\nOne bullet describing where the feature landed, per the repo's changelog\nrules, rather than one per commit in this branch.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Document and pin the stdin input format\n\nThe advertised entry point is `cat points.csv | timezonefinder --stdin`, but\nthe parser is `split(\",\")` and two `float()` calls - not a CSV dialect. A\nheader row, quoted fields, an extra id column and tab- or space-separated\npairs are all rejected, and nothing said so. The usage guide now states the\ncontract, including the tolerances that do hold (surrounding whitespace,\nCRLF, a final line without a newline), and gives a working one-liner for\nprojecting two columns out of a real CSV.\n\nThe ordering hazard gets a warning of its own: the pair is `lng,lat`,\nmatching this package's argument order and reversing the `lat,lng`\nconvention many geographic files use. A swapped pair is usually still a\nvalid coordinate, so it yields a confidently wrong answer and exit 0 -\n`52.37,4.89` resolves to the Indian Ocean, not Amsterdam.\n\nAlso covers two things this branch had added without any test: the\n`--in-memory` flag (same answers as the memory-mapped path, for every\nfunction id, in both modes) and the `__main__` module, which every other\ncase here bypasses by going through the console script.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Resolve stdin coordinate columns by name, never by position\n\nThe bare `lng,lat` line format guessed the column order from an unstated\nconvention, and a wrong guess did not fail: for any longitude between -90\nand 90 the swapped pair is still a valid coordinate, so it resolved to a\nreal timezone. Of 15 major cities, 13 have a silently valid swap, and the\nanswers look plausible - swapping Moscow gives Asia/Tehran, not an error.\nOnly |lng| > 90 (Tokyo, Sydney) was caught by range validation.\n\n--stdin now reads delimited rows and appends a `timezone` column. Columns\ncome from the header by name, or from --lng-col/--lat-col as a header name\nor 1-based number; headerless input with neither is rejected outright. The\norder is stated rather than assumed, which is what removes the failure mode\nrather than warning about it.\n\nAppending the column also makes the mode composable. Annotating a file used\nto mean projecting the coordinates out, running the lookup, and pasting the\nresults back onto the original - four commands reading the input twice, with\nthe projection step being exactly where the swap happened. It is now one\ncommand, and a rejected row identifies itself instead of becoming an\nanonymous blank line.\n\n-d/--delimiter sets the delimiter for input and output ('\\t' spelled out,\nsince a literal tab needs shell-specific quoting). Standard CSV quoting is\nhonoured both ways, so a field containing the delimiter survives; the\nguarantee is therefore one output row per input row, which differs from one\nline per line only when a quoted field spans a newline.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Let a row csv itself rejects cost one row, not the stream\n\n`csv.Error` derives from `Exception`, not `ValueError`, so it escaped the\nhandler written for bad coordinates and aborted `--stdin` with a traceback -\nthe outcome this mode exists to prevent. A field past csv's size limit, which\nany description or WKT column can reach, was enough to discard every row after\nit.\n\nRead the rows by hand instead of through `enumerate`, so the error is caught\nwhere it is raised. The reader resumes on the following line, so the row is\nrejected like any other unusable one; its fields are gone with it, so there is\nnothing to echo back but a blank row.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Read an unverifiable first row as data, never as a header\n\nWith both coordinate columns given as numbers the header names are never\nconsulted, so probing the first row decided nothing but its own fate - and\ndecided it wrongly whenever no field of a data row parsed as a number. A row\nlike `S-1,N/A,N/A` came back relabelled as a header, uncounted and with exit 0:\nsilent data loss, the failure mode addressing columns by number is supposed to\nrule out.\n\nProbe only when the header is actually needed to resolve a column. The two ways\nof being wrong are not symmetric - reading a data row as a header drops it in\nsilence, reading a header as data costs one warning naming the row - so the\nunverifiable case now reads as data.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Match a header column whose name carries a byte order mark\n\nA spreadsheet exported as \"CSV UTF-8\" - the format Excel offers under that\nname, and so a likely producer of the files this mode annotates - begins with a\nBOM. It decodes onto the front of the first column's name, so a file whose\nfirst column is `lng` or `lat` failed to match anything, with an error quoting\na raw `﻿` escape the reader cannot act on.\n\nStrip it where the names are compared. The row itself is still echoed back\nverbatim, so the annotated output stays the same flavour of CSV that was read.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Drop the usage paragraphs describing the superseded output format\n\nThree paragraphs from an earlier revision survived at the end of the section\nand described the format it replaced: an answer per line rather than a column\nappended to the row. They told the reader that a line that cannot be used\n\"produces an empty output line\", that there is \"one output line per input\nline\", and that a coordinate row is \"two numbers\" - none of which is true of\nwhat ships, and the paragraph immediately above them explains why one line per\nline is precisely not the guarantee. The --in-memory paragraph was there twice\nover as well.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Match an explicit column name the way auto-detection does\n\n`--lng-col`/`--lat-col` compared header names exactly, while the automatic\nlookup strips and lowercases them. That made the fallback stricter than the\nmechanism it is the fallback for: `--lng-col lng` did not match a header\nspelling it `LNG`, and a name padded with spaces matched nothing at all - both\nheaders the automatic lookup would have handled had the names been ones it\nknows.\n\nCompare both sides through the same normalisation.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Diagnose a column number wider than the input once, not per row\n\nA typo in `--lng-col` is a property of the flag, not of any one row, but it was\nonly noticed where each row was read: `--lng-col 9` against a three-column file\nproduced a warning and an empty answer for every line, exiting 1 with a\ncomplete but useless copy of the input on stdout. For the file sizes this mode\nexists for that is millions of warnings burying the one fact that matters.\n\nCheck the resolved columns once against the width of the first row, and fail\nthe way every other column-resolution problem does - one message, exit 2,\nnothing written. A row that is merely shorter than the rest is still rejected\non its own, as before.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Spell the tab delimiter in the changelog the way the CLI accepts it\n\nRST inline literals do not process backslash escapes, so ``'\\\\t'`` rendered as\na two-backslash string on the published changelog. Passing what it showed gets\n`--delimiter must be a single character` from the very flag the sentence is\nintroducing. The usage docs and the argparse help both had it right.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Echo a blank row back blank instead of as a quoted empty field\n\n`csv` writes a lone empty field as `\"\"`, to keep it distinguishable from an\nempty row on the way back in. So a blank line in the input became a one-column\nrow in an otherwise rectangular file, and any csv consumer of the output - the\nwhole point of appending the column rather than printing bare answers - trips\nover it. A trailing blank line in a hand-edited file was enough.\n\nThere is no row to append a cell to, so append none. The docs said the blank\nrow came back \"with an empty ``timezone`` cell\", which was never what happened;\nthey now describe the blank echo, and cover the csv-level parse failure the\nsame way.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Refuse --in-memory where there is no polygon data to hold\n\n`TimezoneFinderL` loads no polygon data, so `--in-memory` did nothing at all\nfor `-f 3` and `-f 4` while its help text promised tens of MB spent on faster\nlookups. Nothing in a passing run showed otherwise: the test covering those two\nids asserts the flag changes no answers, which a no-op satisfies perfectly.\n\nReject the combination the way the row-format flags are already rejected\noutside `--stdin`, and say why. The equivalence test now runs over the ids the\nflag reaches, so it would notice if it stopped working there.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Separate a closed pipe from a run that rejected rows\n\nBoth exited 1, so `timezonefinder --stdin < clean.csv | head -5` reported the\none thing the exit code of this mode is for - that some row could not be used -\nabout an input in which every row was fine. Exit 141 instead, which is what a\nshell reports for a process killed by a closed pipe, and what a caller already\nhas to tolerate from the other side of such a pipeline.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* State the in-memory trade-off as a magnitude, not a measured ratio\n\n\"roughly 1.3x faster lookups\" was a figure out of a generated benchmark page,\ncopied by hand into the usage docs, the changelog and the argparse help. The\npage it came from reports 1.02x to 1.51x depending on the workload, so the copy\nwas already narrower than its source, and the next `make reports` moves the\nsource while every copy stays as it was - which is exactly what CLAUDE.md says\nnot to write.\n\nGive the magnitude that survives a measurement, and link the two generated\npages that carry the current numbers for both sides of the trade.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Condense the --stdin changelog bullet to its end state\n\nIt had grown to a 270-word paragraph re-explaining the swapped-pair rationale,\nthe per-row rejection contract, the exit-code semantics and the --in-memory\ntrade-off - all of which the usage documentation covers at length, and none of\nwhich a reader scanning release notes for what changed is looking for. CLAUDE.md\nasks for a few sentences with the detail kept where it belongs.\n\nKeep what a user decides on: what the mode does, that the column order is\nstated rather than guessed and why, the one-row-per-row contract, and the new\nflags. Link the rest.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Let the input state whether it has a header, instead of only guessing\n\nThis mode makes a point of never inferring which column is which, then inferred\nsomething just as load-bearing: whether the first row is a header. The probe has\nno way to be right about a header whose names are all numbers - it reads as data,\nand the coordinate columns are then never found, so a well-formed input is simply\nunusable with no flag to say otherwise.\n\nAdd `--header` / `--no-header`, mutually exclusive, and probe only when neither\nis given. Like the other row-format flags they are refused outside `--stdin`.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Resolve the in-memory lookup function from a table\n\nThe same `TimezoneFinder(in_memory=True).X if in_memory else X` was spelled out\nonce per function id, so the in-memory policy lived in three places that had to\nbe changed together, and the TimezoneFinderL arm carried a comment asking to be\nkept in step with the constant naming those very ids.\n\nPair each id with its global function and the equivalent method name, and let\nthe two arms dispatch off the tables they already have.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Show the coordinates as optional in the usage synopsis\n\nThe synopsis still spelled `lng lat` bare, as it did when they were required.\nA reader following it alongside the `--stdin` section directly below passes\nboth and gets told not to. The flag order had drifted from what argparse\nprints as well.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Record that a push only reaches CI through an open PR\n\nNothing runs on a push to a topic branch: build.yml and benchmark.yml trigger\non pull_request, on master and tags, and on workflow_dispatch. So an empty\nActions list after pushing a branch means the run will never start, not that it\nhas not started yet - which is the same reason a thin green check list is no\nevidence that anything passed.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n---------\n\nSigned-off-by: badhope <weed33834@users.noreply.github.com>\nCo-authored-by: badhope <game33834@outlook.com>\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-15T19:51:19+02:00",
          "tree_id": "ffa4861c834d921705276d9be3d3bb9a1eeb45bb",
          "url": "https://github.com/jannikmi/timezonefinder/commit/3dca95ab33a36d586259b1af0dfac37167ae3c27"
        },
        "date": 1786816355293,
        "tool": "pytest",
        "benches": [
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[random-in_memory]",
            "value": 72.17237997663746,
            "unit": "iter/sec",
            "range": "stddev: 0.0003454198671307802",
            "extra": "mean: 13.8557159999948 msec\nrounds: 60 on AMD EPYC 9V74 80-Core Processor @ 2.8702 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[unique_shortcut-in_memory]",
            "value": 228.5468238732037,
            "unit": "iter/sec",
            "range": "stddev: 0.00033995957723088617",
            "extra": "mean: 4.375471000003017 msec\nrounds: 183 on AMD EPYC 9V74 80-Core Processor @ 2.8702 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[ambiguous_shortcut-in_memory]",
            "value": 23.9730864706337,
            "unit": "iter/sec",
            "range": "stddev: 0.0003177089210792669",
            "extra": "mean: 41.71344400000265 msec\nrounds: 50 on AMD EPYC 9V74 80-Core Processor @ 2.8702 GHz"
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
          "id": "fd3866eb57e4c9dc6fb78e86d569efa724d3c77b",
          "message": "Keep data-only releases from shipping pending work (#519)\n\n* Keep data-only releases from shipping pending work\n\n* Give the release tag step a git identity\n\n`git tag -a` records a tagger and asks git for the committer ident in\nstrict mode. A GitHub runner has no user.name/user.email configured and\nthe auto-detected `runner@fv-az...(none)` is rejected, so the annotated\ntag would fail after the update PR had already been squash-merged: the\ndata lands on master and the tag that starts build.yml is never pushed.\n\ncheck_data_updates.yml already configures both values before committing\nfor exactly this reason; this job did not.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Resolve the update PR through one shared action\n\nThe six jq extractions plus the five-way identity check were copy-pasted\nverbatim into three steps across both jobs. That check is what stops a\nfork branch named data-update-* from reaching the merge step, so three\ncopies meant three things to keep correct, and a one-sided edit would\nleave the weakest copy governing whichever path ran.\n\nIt now lives in .github/actions/resolve-update-pr and every consumer\ntakes the PR number from its output. Behaviour is unchanged; the\nresolution simply runs once, ahead of the changelog guard, because the\nsteps that only run after that guard fails need the number too.\n\nalert_failure gains a checkout of master, which a local `uses:` requires\n- master rather than the PR head, since the job runs code from it while\na pull request is in flight.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Fall back to a branch lookup when the run payload has no PR\n\ngithub.event.workflow_run.pull_requests is empty in more cases than it\nis documented to be, and the workflow had no fallback: the expression\nrendered as the empty string, `gh pr view \"\"` errored, and set -euo\npipefail failed the step. That took out alert_failure too, whose whole\npurpose is to reach the maintainer when something has already gone\nwrong.\n\nThe branch lookup this replaced in the first place is now the fallback\nrather than the only path. It is narrowed to open PRs against master and\nits result goes through the same identity check, so nothing is trusted\nthat was not trusted before.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Treat an already-handled update PR as nothing to do\n\nThe branch lookup this workflow used to do filtered on --state open and\nexited 0 with \"nothing to do\" when it found none. Replacing it with a\nhard identity check collapsed two different situations into one failure:\na PR that is not ours, and a PR that is ours but already merged or\nclosed.\n\nOnly the first is an error. The second is what a maintainer produces by\nre-running build.yml on a data update PR after it has landed - a common\nthing to do - and it re-fires workflow_run. That turned the workflow red\nand made Report pending work abort before commenting, so a genuine\nblocked release would have been announced by nothing at all.\n\nThe shared action now reports found=false for an absent or closed PR and\nerrors only on a mismatch, checking identity first so \"not ours\" can\nnever be softened into a no-op. Every step that merges, labels, comments\nor fails the job gates on found.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Wait for the squash merge commit before tagging\n\nGitHub applies a squash merge asynchronously, so `gh pr view --json\nmergeCommit` right after `gh pr merge` frequently reports null. `--jq\n.mergeCommit.oid` then failed on it and `set -e` aborted the step with\nthe PR already merged - before `merged=true` had been written. The data\nwas on master, no tag was pushed, and nothing downstream could tell that\nfrom a merge that never happened.\n\nThe merge is now recorded the moment it succeeds, the commit is polled\nfor with `// empty` so a null cannot abort the step, and failing to\nresolve it after ten attempts reports what actually happened. The\ncheckout and tag steps key off the resolved commit rather than the merge\nalone, so they can no longer run against an empty ref.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Prove the squash landed on the master the guard checked\n\nThe changelog guard reads master, then the merge step re-reads it and\nrefuses on a mismatch - but the merge follows that read, so a push\nlanding in between still slipped through. `--match-head-commit` pins the\nPR head, not the base, and the GitHub merge API has no equivalent for\nit. The window is small and the consequence is precisely what this\nworkflow exists to prevent: someone's unreleased work published under\ndata-only release notes.\n\nThe squash commit's first parent is the master tip the merge actually\napplied to, so comparing it against the guarded SHA settles the question\nafter the fact. A mismatch withholds the tag rather than the merge - the\nmerge is an ordinary one and stands; the tag is what publishes.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Give each notice cause its own dedup marker\n\nBoth notification steps searched for the same\n<!-- data-update-automation-notice --> marker before commenting, so\nwhichever cause fired first permanently silenced the other. Fix a failing\nCI run, re-run it, and the changelog guard then blocks the release - a\nnotice the workflow would have suppressed, because the earlier CI-failure\ncomment already carried the marker. The maintainer's only signal would\nhave been a red workflow.\n\nThe marker is now per cause. Rather than editing the same dedup block in\ntwo places - which is what let one marker end up shared - the label,\ndedup and comment sequence moves into .github/actions/notify-update-pr,\nwhere the marker is an input and two callers cannot silently agree on\none.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Tell the maintainer which thing actually went wrong\n\nOne step covered both failure causes, so its comment had to name all of\nthem at once - \"pending unreleased work, malformed changelog structure,\nor a concurrent change to master\" - and then asked the maintainer to cut\na release. But the step also fired on any merge failure: a conflict, a\nrequired check, a push landing mid-merge, a merge that succeeded without\nthe tag being pushed. Cutting a release helps with none of those, and\nthe comment carried no link to the run whose log holds the reason.\n\nThere are now two steps, one per cause, each stating only what its\ncondition proves and linking this workflow's run. They use the per-cause\nmarkers from the previous commit, so neither hides the other.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Reject a data release version no later check could find\n\nEvery check in this module recognises a release by _RELEASE_TITLE, which\nrequires <major>.<minor>.<patch>. insert_data_release accepted any string\nas the version, so a heading that pattern cannot match - a release\ncandidate, a two-component version, a stray \"v\" prefix - would be written\ninto the file as text no check can see. The validate_changelog_order call\nat the end of the insert would pass over it rather than reject it, and\nthe next data update would insert above it instead of below, quietly\nreducing the ordering guarantee to \"holds over whichever entries happen\nto be well-formed\".\n\n`uv version --bump patch` does not currently produce such a version, so\nthis is about what the function guarantees to its callers rather than an\nobserved failure.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Match release headings with one pattern instead of two\n\n_RELEASE_HEADING was _RELEASE_TITLE wrapped in a lookahead, purely so\nthat .start() would report the beginning of the heading rather than its\nend. A plain .search() with the same pattern already reports exactly\nthat, since .start() is the start of the match either way - the two\npatterns had to be kept character-identical for no gain.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Cover the check-empty exit code that releases data\n\nThe suite asserted only that a pending unreleased section returns 1. A\ncheck-empty that returned 1 unconditionally would have passed it, while\nsilently ensuring no data update is ever released again - and the\nsymptom, a workflow that merges nothing, is indistinguishable from\nupstream having published no new release.\n\nAdds the success path plus the two error paths the guard depends on\nbeing blocking rather than crashing: a changelog that cannot be parsed,\nand a path that does not exist.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Pin the dedup author filter to the token that comments\n\nThe dedup query only ignores comments it did not write while bot-login\nnames whoever the token authenticates as. Those are two independent\nsettings: secrets.GITHUB_TOKEN posts as github-actions[bot], while the\nGitHub App token this workflow also holds posts as the app. Switching a\nnotifier to the app token - the obvious move if a permission is ever\nmissing - would leave the filter matching no comment at all, so every\nre-run of build.yml would add another maintainer mention. Nothing would\nerror; commenting still succeeds.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Declare the .github paths once for the tests that read them\n\ntests/test_benchmark_workflows.py and tests/test_data_update_workflow.py\neach spelled out PROJECT_ROOT / \".github\" / \"workflows\", and the second\nalso spelled out the actions directory twice. The layout belongs to\nGitHub rather than to this repo, so it now sits with the other path\nconstants in tests/auxiliaries.py and both files import it.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Let a blocked release fail the job on its own\n\nThe guard and the merge both ran under continue-on-error, which meant\nneither could fail the job, which meant a third step existed whose only\nbody was `exit 1` - repeating the disjunction of failure causes a third\ntime. Adding a cause meant remembering to extend three conditions, and\nforgetting the last one would merge and release exactly the work the\nguard had just rejected.\n\nBoth steps now fail the job directly. The reporting steps run on\n`failure()` and each still names the step it reports on, and the merge\nstep needs no guard condition at all, since a step without a status\ncheck function is already skipped once an earlier one has failed.\n\nThe guard picks up the `found` condition the deleted step carried: a run\nwith no update PR has nothing to release, so pending work on master is\nnot a failure of it.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Describe the guard's end state and credit the contributors\n\nFolds the follow-up fixes into the bullets that already describe this\nfeature rather than appending corrections to them, per the changelog\nguidance: the squash-parent check, and the per-cause notices that name\nwhat happened and link the run.\n\nCredits Nice6042 for PR #518, which is the work this branch carries, and\nweed33834 for PR #517, whose --stdin bullet was missing its\nacknowledgement.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Pin the interpreter the changelog guard runs on\n\nThe guard step ran bare `python` with no setup-python before it, so it\nused whatever the runner image happens to default to - pinned by nothing\nthis repo controls. scripts/changelog.py is written against the\nproject's requires-python and annotates `list[str] | None` at module\nlevel, which is a TypeError before 3.10.\n\nThe failure mode is worse than a broken step: the guard failing is\nindistinguishable from the changelog having pending work, so an\ninterpreter change on the runner image would tell the maintainer to cut\na release that does not exist, and block data updates until someone read\nthe log.\n\nPinned to .python-version, matching how every other workflow in this\nrepo sets up Python. The script stays stdlib-only, so it still needs no\nuv sync.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Credit weed33834 for the --stdin contribution\n\nThe --stdin bullet credited #517, which is the maintainer PR that\nsuperseded the actual contribution. weed33834 opened #516 (issue #504);\nit was closed in favour of #517, so the squash merge is authored by the\nmaintainer and nothing in git records where the work came from.\n\nAdds the general rule to CLAUDE.md, since this is the second instance in\nthis release cycle - #518 behind #519 is the same shape - and the\nattribution is exactly what a superseding PR erases.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Cut the workflow tests down to invariants worth pinning\n\ntests/test_data_update_workflow.py had grown to 365 lines, most of it\nasserting that particular shell strings still appear in the YAML -\n\"retrying\", \"parents[0].sha\", the exact gh pr merge invocation. Those\nfail on any rewording and pass on any bug that keeps the wording, so\nthey measure nothing while making every future edit to the workflow look\nexpensive.\n\nWhat survives is the set the structure does not already enforce and\nwhose violation is silent: no step acting on a PR outside the shared\nidentity check, nothing acting when no PR was resolved, the guard\nordered before the merge and able to fail the job, one dedup marker per\nnotice cause, identity checked before state, and a checkout before any\nlocal `uses: ./`. Six tests, 179 lines.\n\ntests/test_changelog.py repeated a full changelog literal in each test;\na builder plus parametrisation covers more cases in half the lines.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Trim the composite action docs to what is not obvious\n\nThe description blocks restated the workflow's own comments and gave\nevery input a sentence, including the ones whose description was the\nexpression they take. What is kept is the part a reader cannot infer:\nwhy the identity check exists, why pr-number may be empty, and why\nbot-login has to match the token.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Record what the workflow tests should have asserted\n\nThe bloat in this PR was not duplicated code - the duplication was\ncaught in review - but 365 lines of tests asserting that particular\nshell strings still appeared in the workflow YAML. Nothing in CLAUDE.md\nwarned against that: the closest rule is about not asserting wording\nanother project owns, which is a different failure.\n\nAmended into Testing rather than opened as a section, and it names the\nrepo's own instance so it reads as a fact rather than advice.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Space the generated release entry like the file it lands in\n\nThe entry ended with one blank line where CHANGELOG.rst puts two above\nevery release title, so each automated data release would have left one\ninconsistent boundary behind. rstcheck accepts either gap and the hooks\nonly look at trailing whitespace, so nothing would have reported it.\n\nThe test fixture had the same one-blank-line gap, which is why it pinned\nthe deviation instead of exposing it; it now mirrors the real file. The\nadded test reads the convention off CHANGELOG.rst rather than restating\nit, since the entries at the bottom predate it and do not follow it.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Treat a superseded run as a no-op, not as a fork PR\n\nThe head-SHA comparison sat inside the identity check, so a run for a\ncommit the PR has moved past exited 1 like a PR from a fork. build.yml\ndeclares no concurrency group, so an older run does finish after a push\nrather than being cancelled: pushing a fix to an update PR while its CI\nis running produced exactly that.\n\nIn alert_failure the resolver failing means `found` is empty and the\nnotice step is skipped, so a genuinely failed CI run was reported\nnowhere - the job the pre-existing inline version did notify from.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Drop the merge output nothing reads\n\n`merged=true` was written with a comment claiming it makes a later error\nreport as \"merged but not released\", but no step or test ever read\n`steps.merge.outputs.merged` - only `merge_sha`. The distinction the\ncomment promised exists solely in the step's own `::error::` text, so the\ncomment read as documented behaviour that was not there.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Report a merge that went through without its tag\n\nBoth reporting steps keyed off the changelog guard or the merge step, so\na failure after the merge - a rejected tag push, a checkout that could\nnot fetch the merge commit - left the update PR unlabelled and without a\ncomment. master carried the new data, no release was built, and since a\nworkflow_run failure appears on no pull request the only trace was the\nActions tab. The docs and the changelog already claimed every cause\nleaves a comment.\n\nThe notice for it is the job's last step by construction, which the\nadded test pins: a step appended below would reopen the same hole.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n---------\n\nCo-authored-by: Ayush Lochab <193861067+Nice6042@users.noreply.github.com>\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-18T00:49:05+02:00",
          "tree_id": "b2d8063b7791411570ddf4447a4a01ced3b5bd9a",
          "url": "https://github.com/jannikmi/timezonefinder/commit/fd3866eb57e4c9dc6fb78e86d569efa724d3c77b"
        },
        "date": 1787007022333,
        "tool": "pytest",
        "benches": [
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[random-in_memory]",
            "value": 73.16839567234811,
            "unit": "iter/sec",
            "range": "stddev: 0.0002567326531456719",
            "extra": "mean: 13.667103000017278 msec\nrounds: 60 on AMD EPYC 7763 64-Core Processor @ 2.4454 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[unique_shortcut-in_memory]",
            "value": 234.21255163824839,
            "unit": "iter/sec",
            "range": "stddev: 0.00031461096343030813",
            "extra": "mean: 4.2696259999956965 msec\nrounds: 194 on AMD EPYC 7763 64-Core Processor @ 2.4454 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[ambiguous_shortcut-in_memory]",
            "value": 25.090842650351153,
            "unit": "iter/sec",
            "range": "stddev: 0.0003309209853007905",
            "extra": "mean: 39.85517800001048 msec\nrounds: 50 on AMD EPYC 7763 64-Core Processor @ 2.4454 GHz"
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
          "id": "e3a43ae189dd7f21a2fe4c038f71e354d0fc4af3",
          "message": "Retire the release stop for a state that can no longer arise (#520)\n\nThe cut-release skill stopped when a dated section sat above\n`X.X.X (unreleased)`, and explained it by `update_data.sh` splicing its\nentry under the file header. Since #519 it inserts below the unreleased\nsection and `release_data_update.yml` withholds the merge while anything\nis pending, so the automation cannot leave the file out of order - and\n`validate_changelog_order` fails the test suite over the committed file\nif anything else does, which the skill's green-master precondition\nalready stops on.\n\nThe skill's own maintenance section named this as its removal condition.\nThat entry is spent and goes with it; what replaces it is the record of\nwhy the row is absent, so it is not re-added on the next read.\n\nCloses #510\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-18T01:05:12+02:00",
          "tree_id": "ed8566bcda4190f94f5d93002510a7fd5f6bd83d",
          "url": "https://github.com/jannikmi/timezonefinder/commit/e3a43ae189dd7f21a2fe4c038f71e354d0fc4af3"
        },
        "date": 1787007994645,
        "tool": "pytest",
        "benches": [
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[random-in_memory]",
            "value": 72.70615357252687,
            "unit": "iter/sec",
            "range": "stddev: 0.00012482881504108294",
            "extra": "mean: 13.75399400000532 msec\nrounds: 60 on AMD EPYC 9V74 80-Core Processor @ 2.5961 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[unique_shortcut-in_memory]",
            "value": 223.11677173237894,
            "unit": "iter/sec",
            "range": "stddev: 0.00005564723182610773",
            "extra": "mean: 4.4819579999995085 msec\nrounds: 182 on AMD EPYC 9V74 80-Core Processor @ 2.5961 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[ambiguous_shortcut-in_memory]",
            "value": 24.558274612245814,
            "unit": "iter/sec",
            "range": "stddev: 0.001411422159300122",
            "extra": "mean: 40.71947300000289 msec\nrounds: 50 on AMD EPYC 9V74 80-Core Processor @ 2.5961 GHz"
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
          "id": "1d98d8849adee5808605ac0f5a27a34fb1c4abb5",
          "message": "Expose the packaged dataset version at runtime (#523)\n\n* Expose the packaged dataset version at runtime (#498)\n\nAn installed timezonefinder could not state which timezone-boundary-builder\nrelease it was answering from: the dataset version lived only in the repo-root\nDATA_VERSION file, which is not packaged, and the package had no __version__\nattribute. As a side effect, every generated benchmark report carried\ntimezonefinder_version: \"Unknown\" because benchmark_utils.py read a\nnon-existent __version__ attribute on a __slots__ class.\n\nImplementation follows the 5-step plan in issue #498:\n\n1. scripts/file_converter.py writes a data_version.txt stamp into the data\n   directory it generates, mirroring the repo-root DATA_VERSION the parse was\n   built from. update_data.sh re-stamps both together after a successful\n   upstream release.\n2. timezonefinder/configs.py declares DATA_VERSION_FILENAME so the runtime\n   and build sides share one filename; AbstractTimezoneFinder.data_version\n   reads it from the packaged data directory at runtime.\n3. timezonefinder.__version__ is exposed via importlib.metadata.\n4. scripts/benchmark_utils.py reads timezonefinder.__version__ from the\n   package instead of getattr(tf_instance, \"__version__\", \"Unknown\").\n5. The new file is covered by the existing MANIFEST.in recursive-include\n   *.txt and [tool.setuptools.package-data] **/*.txt globs, and\n   tests/test_package_contents.py asserts it ships in both wheel and sdist.\n\nVerified locally: full pytest suite green (2994 passed), ruff check + ruff\nformat --check pass, built wheel and sdist both contain\ntimezonefinder/data/data_version.txt.\n\n* Stamp a parse with the release it came from, not the repo's\n\nThe converter wrote data_version.txt from the repo-root DATA_VERSION\nwhatever it had just parsed, so compiling your own GeoJSON - a supported\nuse case - produced a directory whose data_version claimed a\ntimezone-boundary-builder release the data never came from. Silently:\nnothing errors, warns, or has any way to notice.\n\nWhich release an input came from is the caller's to state, so parse_data\ntakes it (`--data-version`, which update_data.sh will pass from the tag\nit records at download time). Unstated, it falls back to DATA_VERSION\nfor the one input that file does describe - the packaged\nDEFAULT_INPUT_PATH - and to \"unknown\" for anything else.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Say what to do when a data directory carries no version stamp\n\nEvery other file of a directory compiled before the stamp existed still\nloads, and lookups still answer, so `data_version` was the one thing that\nfailed - with a bare FileNotFoundError naming a path and nothing else.\nThe sibling check added this release (the coordinate file identifier)\nnames the file and the fix; this one now does too.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Let the parse write the stamp update_data.sh was copying over it\n\nThe script re-typed timezonefinder/data/data_version.txt to repair a\nstamp the converter had just written from the previous DATA_VERSION - a\nsecond spelling of a path the runtime and the converter share a constant\nfor, and one that a rename would leave writing to the old name. The tag\nrecorded at download time is now handed to the parse instead, so the\nstamp is right when it is written and there is nothing to copy over it.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Point the stamp-drift failure at the fix that applies\n\nIt told the reader to re-run scripts/file_converter, which needs a\ngitignored several-hundred-MB download and the full parse the data-update\njob budgets three hours for - to rewrite one line of text. The drift it\nreports is between two copies of a tag, so the fix is a copy; regenerating\nis only the answer when the binaries themselves are the wrong ones, which\nthe message now says instead of assuming.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* List the version stamp in the data directory reference\n\nThe page is what someone reads to build a compatible data directory, so a\nfile missing from it is a file they will not write - and the one thing\nthat then fails, data_version, fails at the point of use rather than at\nload. Its description of update_data.sh also predates the stamp.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Pin the stamp as an essential file instead of rebuilding for it\n\ntest_packaged_data_version_file_in_distribution asserted, over two freshly\nbuilt distributions, exactly what test_essential_files_in_distribution\nalready asserts for this file: ESSENTIAL_SOURCE_PATTERNS matches it via\n`*.txt`, and matches_pattern fnmatches the whole relative path. What that\nleaves unguarded is the pattern set narrowing, which is a statement about\nthe checkout and needs no build - so it is a unit test now, and the third\nhand-typed copy of the stamp's path goes with it.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Hold __version__ to the version pyproject declares\n\nAsserting only that it is not the literal \"unknown\" passes on the failure\nit exists to catch: __version__ reads the *installed* distribution's\nmetadata, so an environment left behind by a version bump answers with\nthe previous release - not the fallback, indistinguishable from a real\nanswer, and exactly what get_system_status() would then record in every\nbenchmark report. The pyproject path moves next to the repository's other\ntooling paths, since a second test already had its own copy.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Let the downloaded file carry the release it came from\n\nNothing inside a timezone-boundary-builder GeoJSON says which release it\nis, so the release could only be re-stated alongside the file - as a\nshell variable, true for one invocation of one script, and as a fallback\nthat read the repository's own DATA_VERSION for the input it recognised.\n\nupdate_data.sh now resolves the tag first and names the download after\nit, which also makes one answer govern the download URL, the file names\nand DATA_VERSION: fetching `releases/latest/download/` while separately\nasking the API what `latest` was were two questions, and a release\nlanding between them attributed one release's data to the other. Naming\nthe archive and the GeoJSON per release and variant additionally stops a\nleftover file satisfying the \"already downloaded\" checks.\n\nThe converter reads the tag back off the name, and refuses an unpacked\narchive that lacks one instead of stamping data that could never say\nwhere it came from - before creating the output directory, so a refusal\nleaves nothing behind. Data that is not a release stays \"unknown\", and\n--data-version remains for an input that cannot be renamed. No rule can\nnow produce a release tag the data did not come from.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Describe how a parse learns which release it compiled\n\nThe pipeline steps skipped the naming step, and the use-cases page still\ndescribed a default input (`combined.json` next to the package) that has\nnot been one for some time - both now say where the release comes from,\nand that data which is not a release needs no name.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Update CLAUDE.md\n\n---------\n\nCo-authored-by: MsfPablo <129399053+MsfPablo@users.noreply.github.com>\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-18T22:13:26+02:00",
          "tree_id": "9e0befe4adac781beba799845bd8c32ba3adce40",
          "url": "https://github.com/jannikmi/timezonefinder/commit/1d98d8849adee5808605ac0f5a27a34fb1c4abb5"
        },
        "date": 1787084097082,
        "tool": "pytest",
        "benches": [
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[random-in_memory]",
            "value": 74.051858516549,
            "unit": "iter/sec",
            "range": "stddev: 0.00014338465331506454",
            "extra": "mean: 13.50404999999455 msec\nrounds: 61 on AMD EPYC 7763 64-Core Processor @ 3.2377 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[unique_shortcut-in_memory]",
            "value": 231.53459508884873,
            "unit": "iter/sec",
            "range": "stddev: 0.00004271242878970631",
            "extra": "mean: 4.319008999999596 msec\nrounds: 193 on AMD EPYC 7763 64-Core Processor @ 3.2377 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[ambiguous_shortcut-in_memory]",
            "value": 25.430766023756217,
            "unit": "iter/sec",
            "range": "stddev: 0.0015784869718891731",
            "extra": "mean: 39.322448999996595 msec\nrounds: 50 on AMD EPYC 7763 64-Core Processor @ 3.2377 GHz"
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
          "id": "d6af064e46ce18d60f41a07b7d6a5e3a0ad788de",
          "message": "Give the shortcut binaries a file identifier and a layout version (#526)\n\nThe hybrid shortcut files finished their buffer bare and the reader picked a\nschema by substring-matching \"uint8\"/\"uint16\" in the file name, so a renamed or\nmispaired file was caught by nothing: the two schemas differ only in the width\nof UniqueZone.zone_id, and either width parses cleanly under the other and hands\nback wrong zone ids.\n\nBoth schemas now declare a file_identifier - TZS1 for uint8, TZS2 for uint16,\ndistinct on purpose - and a layout_version field mirroring PolygonCollection's.\nThe reader dispatches on the identifier stamped inside the buffer and then\nchecks the version, so the file name carries no meaning any more and\n_schema_for_file_name is gone. polygons.py's rejection message moves to\ntimezonefinder/flatbuf/io/layout.py so both binary kinds fail the same way.\n\nThe packaged hybrid_shortcuts_uint16.fbs is regenerated to carry the markers;\nits decoded mapping is unchanged entry for entry, and coordinates.fbs is\nuntouched.\n\nCloses #458\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-18T23:34:30+02:00",
          "tree_id": "3be670d0d81111510337ee9e4822c6294832d070",
          "url": "https://github.com/jannikmi/timezonefinder/commit/d6af064e46ce18d60f41a07b7d6a5e3a0ad788de"
        },
        "date": 1787088942149,
        "tool": "pytest",
        "benches": [
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[random-in_memory]",
            "value": 80.28838302575214,
            "unit": "iter/sec",
            "range": "stddev: 0.00021667857227594453",
            "extra": "mean: 12.455101999989893 msec\nrounds: 60 on INTEL(R) XEON(R) PLATINUM 8573C @ 3.1000 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[unique_shortcut-in_memory]",
            "value": 259.25219223635236,
            "unit": "iter/sec",
            "range": "stddev: 0.000037276416150018817",
            "extra": "mean: 3.8572480000027554 msec\nrounds: 210 on INTEL(R) XEON(R) PLATINUM 8573C @ 3.1000 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[ambiguous_shortcut-in_memory]",
            "value": 26.773712968879597,
            "unit": "iter/sec",
            "range": "stddev: 0.0005057930706958977",
            "extra": "mean: 37.35006799999496 msec\nrounds: 50 on INTEL(R) XEON(R) PLATINUM 8573C @ 3.1000 GHz"
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
          "id": "59531c5eba390a3aa12af0caf019fb7942d1b81f",
          "message": "Publish the boundary data as a separate distribution (#446) (#527)\n\n* Move the packaged data and its licence into packages/timezonefinder-data\n\nTree-only: the binaries and DATA_LICENSE are renamed, not rewritten, and the\nnew distribution's pyproject/README/__init__ are added alongside them. Nothing\nimports the new package yet - the wiring follows separately, so that the 62 MB\nrename can be reviewed apart from it.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Publish the boundary data as a separate distribution\n\n`timezonefinder-data` is now its own distribution, built from the same\nworkspace. `pip install timezonefinder` is unchanged - the dependency is hard -\nbut a dataset can be pinned without pinning old code, and a data update no\nlonger costs a `timezonefinder` release carrying ~65 MB across three platform\nwheels plus an sdist.\n\nThe version carries two facts, because two things drive a data release: the\ndata distribution's major *is* `DATA_FORMAT_VERSION`, and the root requires\n`timezonefinder-data>=1.2026.3,<2`. No ceiling on the data axis, so an ordinary\nupdate still needs no code release; a hard one on the format axis, so old code\npaired with a new format fails when resolving rather than at the first lookup.\nThe in-file identifier and layout_version markers stay: `bin_file_location`\ndirectories have no metadata to read, and only a per-file marker catches a\nmixed directory.\n\nThe two tag namespaces share a branch, so the separation is enforced rather\nthan conventional - build.yml excludes `data-v*` at its trigger and again on\nthe job creating the GitHub Release, since `release: types: [published]`\nconsults no tag filter, and each stream publishes with its own token.\nRetiring the pending-work guard follows from the split: a data tag now\npublishes a distribution containing no code, so unreleased code work has\nnothing to do with it.\n\nAlso: DATA_LICENSE moves with the database it covers, a compiled data\ndirectory carries a copy of the schemas its binaries were written by, and\ntest_package_contents.py asserts neither distribution carries the other's\npayload.\n\nRefs #446\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Point the improvement ledger at the data's new location\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Publish the data distribution by Trusted Publishing\n\nPyPI trusts the publish_data.yml workflow directly, gated on the `pypi-data`\ndeployment environment, so the job exchanges an OIDC identity for a\nshort-lived upload token instead of holding one. No long-lived credential\nexists that could upload `timezonefinder`, and the pending publisher covers\nthe very first upload - which a project-scoped token could not, since the\nproject does not exist yet.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Fix the tox bootstrap and drop issue references from code\n\ntox installs the package with bare pip, which resolved the new\n`timezonefinder-data` requirement from PyPI - where this checkout's version\nneed not exist, and does not at all before the first data release. Every tox\nenv now installs the workspace member from the source tree, which also keeps\nthem testing the data this checkout carries rather than a published one.\n\nSeparately: an issue number in a comment is an indirection to a tracker the\nreader may not be able to open, and one that gets retitled and re-scoped\nindependently of the code, so the reason stops being where the code is. The\nreasoning is now written out at each site. CLAUDE.md records the rule, with\nCHANGELOG.rst as the stated exception.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n---------\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-19T01:53:17+02:00",
          "tree_id": "f0f4b971c74cf1a2ba1c097210f180c97b752685",
          "url": "https://github.com/jannikmi/timezonefinder/commit/59531c5eba390a3aa12af0caf019fb7942d1b81f"
        },
        "date": 1787097257650,
        "tool": "pytest",
        "benches": [
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[random-in_memory]",
            "value": 125.92902564662903,
            "unit": "iter/sec",
            "range": "stddev: 0.00009086758186590737",
            "extra": "mean: 7.940980999933345 msec\nrounds: 93 on AMD EPYC 9V45 96-Core Processor @ 4.2795 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[unique_shortcut-in_memory]",
            "value": 389.385810075091,
            "unit": "iter/sec",
            "range": "stddev: 0.00006555138936445836",
            "extra": "mean: 2.568147000033605 msec\nrounds: 279 on AMD EPYC 9V45 96-Core Processor @ 4.2795 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[ambiguous_shortcut-in_memory]",
            "value": 42.417680537505596,
            "unit": "iter/sec",
            "range": "stddev: 0.000280897804850661",
            "extra": "mean: 23.575075000053403 msec\nrounds: 50 on AMD EPYC 9V45 96-Core Processor @ 4.2795 GHz"
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
          "id": "a52225c2b8babd9674412b0c5c3c60c741e2be5b",
          "message": "Name the packaged FlatBuffers binaries .bin, not .fbs (#528)\n\n* Move the packaged data and its licence into packages/timezonefinder-data\n\nTree-only: the binaries and DATA_LICENSE are renamed, not rewritten, and the\nnew distribution's pyproject/README/__init__ are added alongside them. Nothing\nimports the new package yet - the wiring follows separately, so that the 62 MB\nrename can be reviewed apart from it.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Publish the boundary data as a separate distribution\n\n`timezonefinder-data` is now its own distribution, built from the same\nworkspace. `pip install timezonefinder` is unchanged - the dependency is hard -\nbut a dataset can be pinned without pinning old code, and a data update no\nlonger costs a `timezonefinder` release carrying ~65 MB across three platform\nwheels plus an sdist.\n\nThe version carries two facts, because two things drive a data release: the\ndata distribution's major *is* `DATA_FORMAT_VERSION`, and the root requires\n`timezonefinder-data>=1.2026.3,<2`. No ceiling on the data axis, so an ordinary\nupdate still needs no code release; a hard one on the format axis, so old code\npaired with a new format fails when resolving rather than at the first lookup.\nThe in-file identifier and layout_version markers stay: `bin_file_location`\ndirectories have no metadata to read, and only a per-file marker catches a\nmixed directory.\n\nThe two tag namespaces share a branch, so the separation is enforced rather\nthan conventional - build.yml excludes `data-v*` at its trigger and again on\nthe job creating the GitHub Release, since `release: types: [published]`\nconsults no tag filter, and each stream publishes with its own token.\nRetiring the pending-work guard follows from the split: a data tag now\npublishes a distribution containing no code, so unreleased code work has\nnothing to do with it.\n\nAlso: DATA_LICENSE moves with the database it covers, a compiled data\ndirectory carries a copy of the schemas its binaries were written by, and\ntest_package_contents.py asserts neither distribution carries the other's\npayload.\n\nRefs #446\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Point the improvement ledger at the data's new location\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Publish the data distribution by Trusted Publishing\n\nPyPI trusts the publish_data.yml workflow directly, gated on the `pypi-data`\ndeployment environment, so the job exchanges an OIDC identity for a\nshort-lived upload token instead of holding one. No long-lived credential\nexists that could upload `timezonefinder`, and the pending publisher covers\nthe very first upload - which a project-scoped token could not, since the\nproject does not exist yet.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Fix the tox bootstrap and drop issue references from code\n\ntox installs the package with bare pip, which resolved the new\n`timezonefinder-data` requirement from PyPI - where this checkout's version\nneed not exist, and does not at all before the first data release. Every tox\nenv now installs the workspace member from the source tree, which also keeps\nthem testing the data this checkout carries rather than a published one.\n\nSeparately: an issue number in a comment is an indirection to a tracker the\nreader may not be able to open, and one that gets retitled and re-scoped\nindependently of the code, so the reason stops being where the code is. The\nreasoning is now written out at each site. CLAUDE.md records the rule, with\nCHANGELOG.rst as the stated exception.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Name the packaged FlatBuffers binaries .bin, not .fbs\n\n`.fbs` is the FlatBuffers *schema* extension, and since the data directory\nstarted shipping actual schemas next to the buffers, one extension named two\nunrelated kinds of file - which is why the schema copies needed a subdirectory\nto avoid the collision. Each buffer already states what it is through the file\nidentifier in its first bytes, which a rename cannot forge; the name never\ncarried that meaning.\n\nThe bytes are unchanged, so this is a `git mv` of identical blobs and adds\nnothing to history. No layout version moves and DATA_FORMAT_VERSION stays 1:\nno `timezonefinder-data` has been published yet, and no released\n`timezonefinder` reads a data distribution at all, so there is no pairing to\nprotect against. That is only true while this lands before the first `data-v`\ntag - afterwards it would be a format bump and an ordered two-distribution\nrelease.\n\nCustom `bin_file_location` directories must be regenerated, which this release\ncycle already required for the coordinate layout, the hole storage and the\nshortcut container; the changelog states the file names alongside those rather\nthan as a second obligation.\n\nAlso drops the pointer to a gitignored plans/ file from CLAUDE.md - the\nreasoning it pointed at is now stated where it can actually refuse the next\nproposal - and records the rule against citing anything outside the repository\nas a reason.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n---------\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>\nCo-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>",
          "timestamp": "2026-08-19T02:15:12+02:00",
          "tree_id": "9b3104e62db704f6982605a83f4f3f54701fe8a1",
          "url": "https://github.com/jannikmi/timezonefinder/commit/a52225c2b8babd9674412b0c5c3c60c741e2be5b"
        },
        "date": 1787098585145,
        "tool": "pytest",
        "benches": [
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[random-in_memory]",
            "value": 73.64043012788856,
            "unit": "iter/sec",
            "range": "stddev: 0.0002061586420139222",
            "extra": "mean: 13.579496999994944 msec\nrounds: 61 on AMD EPYC 7763 64-Core Processor @ 3.2405 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[unique_shortcut-in_memory]",
            "value": 233.09197436383894,
            "unit": "iter/sec",
            "range": "stddev: 0.00004942295133853405",
            "extra": "mean: 4.290151999995828 msec\nrounds: 193 on AMD EPYC 7763 64-Core Processor @ 3.2405 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[ambiguous_shortcut-in_memory]",
            "value": 25.382167879787087,
            "unit": "iter/sec",
            "range": "stddev: 0.00029835481454414787",
            "extra": "mean: 39.39773800000523 msec\nrounds: 50 on AMD EPYC 7763 64-Core Processor @ 3.2405 GHz"
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
          "id": "42696172134b385922d487b33773321cb7f2d99d",
          "message": "Refuse to publish the code before the data it requires exists (#529)\n\n* Refuse to publish the code before the data it requires exists\n\nThe two distributions release independently, and on a data format change the\norder is fixed: the data first, then the code requiring it. Backwards, the\nwheel is uninstallable for everyone until the data lands - and PyPI never\naccepts a version number twice, so the fix is a whole new release rather than\na re-upload. Until now that ordering was a checklist item with nothing\nenforcing it.\n\nThe guard runs in the publishing job, ahead of the upload, and reads the\nrequirement out of the wheel about to be published rather than out of\npyproject.toml: the wheel is what a user's resolver will read. It then asks\nthe index the same question that resolver will ask, instead of reimplementing\nthe answer - so a release whose files are all yanked does not count as one\nthat satisfies the bound.\n\n\"Nothing satisfies it\" and \"the check could not run\" exit differently. A\nrelease blocked because PyPI was unreachable is a retry; one blocked because\nthe data is genuinely missing needs the data published first, and collapsing\nthe two loses the only thing the operator needs to know. A wheel declaring no\ndata dependency at all is the second kind, not a pass - that would be the\nguard succeeding for the wrong reason.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Guard release on data dependency: require data published before code\n\nEnsure code releases cannot be published until the separate timezonefinder-data distribution is published. Update CI workflows, release scripts, documentation and tests to check and enforce the data dependency.\\n\\nFiles changed include workflow YAMLs, release helper scripts, docs, and tests to make the data dependency explicit and to prevent accidental code-only releases.\\n\\nCo-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>\n\n* Finish the release guard and assert what each distribution ships\n\nCompletes three items left open on this branch.\n\nThe data-dependency check ran twice: the move ahead of the GitHub Release\nlanded, but the copy next to the PyPI upload survived the merge. Drop it -\n`publish-pypi` needs `release`, so one placement covers both - and widen its\ntest from \"before the upload\" to \"before any publishing step\", satisfied\nin-job or through a dependency. The old test passed with the guard sitting\nafter the GitHub Release, which is the earlier irreversible step.\n\nAssert each distribution's build contents. setuptools copies package data\ninto build/lib and never prunes it, so the .fbs -> .bin rename left a 63 MB\ncoordinates.fbs shipping next to its replacement in every wheel built from a\ndeveloper checkout - 99 MiB instead of 50. Nothing caught it: the\nunwanted-file scan only knows .gitignore patterns, which cannot match a path\ninside an archive, and the essential-file checks only ask whether expected\nfiles are present. Compare the wheel's payload to the committed dataset as a\nset, and clear build/ before building so a local build matches CI's fresh\ncheckout.\n\nRestore the code sdist's assertions for the test fixtures it grafts. Dropping\n*.npy/*.json when the dataset moved out also dropped the only checks that\ntests/fixtures/benchmarks/ and tests/test_input.json still ship.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Let cut-release decide the bump level, reviewed on the release PR\n\nThe skill stopped twice: once to put patch/minor/major to the maintainer,\nonce before pushing the tag. The first stop asked them to answer, from §4's\ntable and with no diff attached, a question the release PR then asked again\nwith both attached. Drop it: §4 derives the level from the table, and §7's\n\"Why this level\" is the review surface instead.\n\nThat only works if the justification is checkable, so it now has a required\nshape - the one bullet that drove the level, quoted, the table row it matches,\nand the level ruled out with the reason. \"minor, not major: no exported\nsignature changed\" can be checked in seconds; \"minor\" cannot.\n\nThe tag stop stays and is different in kind: nothing reviews it afterwards,\nbuild.yml publishes on the push, and PyPI will not take a version twice. The\nmaintenance section records both directions so the next pass neither re-adds\nthe bump gate nor removes the tag one.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n---------\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-19T07:35:03+02:00",
          "tree_id": "728a8d1bd275eef1eb7a0f6165c853acec39fb4d",
          "url": "https://github.com/jannikmi/timezonefinder/commit/42696172134b385922d487b33773321cb7f2d99d"
        },
        "date": 1787117777533,
        "tool": "pytest",
        "benches": [
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[random-in_memory]",
            "value": 93.49897861720063,
            "unit": "iter/sec",
            "range": "stddev: 0.00055244958072303",
            "extra": "mean: 10.695303999995076 msec\nrounds: 64 on INTEL(R) XEON(R) PLATINUM 8573C @ 3.3248 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[unique_shortcut-in_memory]",
            "value": 302.80347569928307,
            "unit": "iter/sec",
            "range": "stddev: 0.000306113806639335",
            "extra": "mean: 3.302472000001444 msec\nrounds: 258 on INTEL(R) XEON(R) PLATINUM 8573C @ 3.3248 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[ambiguous_shortcut-in_memory]",
            "value": 32.18590164812281,
            "unit": "iter/sec",
            "range": "stddev: 0.001606563376866152",
            "extra": "mean: 31.069504000001302 msec\nrounds: 50 on INTEL(R) XEON(R) PLATINUM 8573C @ 3.3248 GHz"
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
          "id": "6671aadf82bbb91dc1b3f0a62cb9415dbe5e2f7e",
          "message": "Release 8.3.0 (#532)\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-19T07:58:10+02:00",
          "tree_id": "84b372e777e2f128ca5ef259b6c278c1e11338fb",
          "url": "https://github.com/jannikmi/timezonefinder/commit/6671aadf82bbb91dc1b3f0a62cb9415dbe5e2f7e"
        },
        "date": 1787119161661,
        "tool": "pytest",
        "benches": [
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[random-in_memory]",
            "value": 70.1001928035461,
            "unit": "iter/sec",
            "range": "stddev: 0.0003681912326230307",
            "extra": "mean: 14.265296000004923 msec\nrounds: 59 on AMD EPYC 9V74 80-Core Processor @ 2.7352 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[unique_shortcut-in_memory]",
            "value": 222.7170004117642,
            "unit": "iter/sec",
            "range": "stddev: 0.0000878725718099139",
            "extra": "mean: 4.490003000000797 msec\nrounds: 182 on AMD EPYC 9V74 80-Core Processor @ 2.7352 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[ambiguous_shortcut-in_memory]",
            "value": 24.250411887187465,
            "unit": "iter/sec",
            "range": "stddev: 0.00028724743429096725",
            "extra": "mean: 41.23641299999292 msec\nrounds: 50 on AMD EPYC 9V74 80-Core Processor @ 2.7352 GHz"
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
          "id": "f2cffeede3d1a9d666667b9c8b3ea328fdb99049",
          "message": "Run the tox matrix once per release, not twice (#534)\n\nThe matrix is the whole critical path of build.yml - four jobs of 6-10\nminutes each, against under a minute for every other job combined - and\nit ran for the push to master and again for the tag naming that same\ncommit. Skip it on tag refs, and gate the release job to tag refs only:\nmaster tests, the tag releases. That also removes the race the release\nprocedure worked around, since the release action is handed the tag name\nand so a master push created the tag on its own.\n\nThe skip is backed by a check, not an assumption. The pre-existing\nancestry step proves the commit is on master, not that it was ever\ngreen, so the release job now asks the API for a successful build run on\nmaster for that exact SHA and refuses to publish if none exists.\n\nIts `if` needs !cancelled() because a skipped `needs` job skips its\ndependents - and naming any status function drops the implicit\nsuccess(), so every dependency that does still run is checked by hand.\ntests/test_release_workflows.py evaluates those conditions rather than\nreading them, since the failure mode surfaces only during a release.\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-19T08:24:41+02:00",
          "tree_id": "2af6f3c18f6345f2a685d0b15a740d22be44ec8a",
          "url": "https://github.com/jannikmi/timezonefinder/commit/f2cffeede3d1a9d666667b9c8b3ea328fdb99049"
        },
        "date": 1787121038018,
        "tool": "pytest",
        "benches": [
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[random-in_memory]",
            "value": 68.64774446509198,
            "unit": "iter/sec",
            "range": "stddev: 0.0003934554357366776",
            "extra": "mean: 14.567120999998906 msec\nrounds: 60 on AMD EPYC 7763 64-Core Processor @ 3.2524 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[unique_shortcut-in_memory]",
            "value": 228.81420698169845,
            "unit": "iter/sec",
            "range": "stddev: 0.00008885842477503965",
            "extra": "mean: 4.3703580000169495 msec\nrounds: 183 on AMD EPYC 7763 64-Core Processor @ 3.2524 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[ambiguous_shortcut-in_memory]",
            "value": 24.433264325650782,
            "unit": "iter/sec",
            "range": "stddev: 0.0002274761119860143",
            "extra": "mean: 40.927809999999454 msec\nrounds: 50 on AMD EPYC 7763 64-Core Processor @ 3.2524 GHz"
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
          "id": "b0642ad3bdc488421ced2ae69af55bc64d0c05a7",
          "message": "Collapse the artifact-staging steps into one composite action (#535)\n\n`build.yml` wrote the same \"unzip every artifact, flatten into dist/\" block\nthree times, in `end-to-end-test`, `release` and `publish-pypi`. The copies had\ndrifted - two matched `artifact-*.zip`, one `artifact-*`, which unzips a\ndirectory and fails without anyone noticing, since `find -exec` does not\npropagate its command's exit status - and that accidental drift sat next to the\none difference that is deliberate: `publish-pypi` excludes the data wheel,\nbecause it uploads whatever is in dist/ as `timezonefinder` while the data\ndistribution publishes from publish_data.yml under its own tag and publisher.\nNothing told a reader which of the two was load-bearing.\n\nThe block is now `.github/actions/stage-artifacts`, taking that exclusion as a\nnamed input. Only the prologue moved: the data-dependency check and both\npublishing steps stay inline, so the ordering test that walks each job's steps\nstill sees them.\n\n`publish-pypi` also drops four steps nothing consumed. `Fetch version` set an\noutput only `release` reads; with it gone no step ran uv or pip, so setting up\nPython, upgrading pip and installing uv had no consumer either. Its checkout\nstays, now for one reason: `uses: ./...` resolves from the workspace.\n`end-to-end-test` gains a sparse, non-cone checkout for the same reason - a\nfull one would put this repository's pyproject.toml in the workspace root,\nwhere the job builds a throwaway project with `uv init`.\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-19T10:20:16+02:00",
          "tree_id": "9bf23e0d369ce8e2ef21f2d87ef07d20bc19da44",
          "url": "https://github.com/jannikmi/timezonefinder/commit/b0642ad3bdc488421ced2ae69af55bc64d0c05a7"
        },
        "date": 1787127700285,
        "tool": "pytest",
        "benches": [
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[random-in_memory]",
            "value": 71.81003660156122,
            "unit": "iter/sec",
            "range": "stddev: 0.0022837396253831835",
            "extra": "mean: 13.925630000002798 msec\nrounds: 61 on AMD EPYC 7763 64-Core Processor @ 2.4454 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[unique_shortcut-in_memory]",
            "value": 231.06219986473266,
            "unit": "iter/sec",
            "range": "stddev: 0.0001328697784832279",
            "extra": "mean: 4.327838999998335 msec\nrounds: 195 on AMD EPYC 7763 64-Core Processor @ 2.4454 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[ambiguous_shortcut-in_memory]",
            "value": 24.654009938967604,
            "unit": "iter/sec",
            "range": "stddev: 0.00041682151724125466",
            "extra": "mean: 40.56135300000108 msec\nrounds: 50 on AMD EPYC 7763 64-Core Processor @ 2.4454 GHz"
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
          "id": "64da9e1a30df7565d2742ab22b9ee755f03b9476",
          "message": "Type-check tests/, and close two surfaces nothing was checking (#539)\n\n* SURF-1: drop the three schema filenames from the schemas package __all__\n\nThey are .fbs data files next to the module, not submodules of it, so\n`from timezonefinder.flatbuf.schemas import *` raised AttributeError on a\nsurface declaration nothing checked. tests/test_documented_contracts.py now\nresolves every __all__ entry in the package against its module.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* TOOL-5: type-check tests/ with the mypy hook instead of excluding it\n\nClears the eight real disagreements the exclusion had been hiding - an\nundeclared attribute the base test class's fixture assigns, two subclasses\ncontradicting types inferred from the base's own values, a promised list[Path]\nbacked by an attribute only ever inferred as None, a dict literal annotated\nset[str, str], and an unmeasured metric reaching a float comparison as None -\nthen drops tests/ from the hook's exclude and extends the guard that keeps\nscripts/ out of it to cover tests/ too.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* PATH-1: import PROJECT_ROOT in the test helpers instead of re-deriving it\n\ntests/auxiliaries.py anchored the checkout root on the installed timezonefinder\npackage (PACKAGE_DIR.parent), which is site-packages for anything but an\neditable install. scripts.configs already declares it against the repository.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* DUP-2: create the converter's output directories once, in the caller\n\nwrite_numpy_binaries and write_flatbuffer_files each recomputed holes_dir and\nboundaries_dir and mkdir'd them, which reads as though either could run alone;\nthey cannot, since the reference vector one writes addresses the coordinate\nfile the other writes. The zone ids now go through store_per_polygon_vector\nlike every other vector. Verified byte-identical over tests/test_input.json.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* REND-1: choose the memory report's metric paragraph with an if, not a ternary\n\nThe conditional sat at the foot of twelve lines of implicitly concatenated\nprose, so a reader editing the long branch had no reason to look for it. Only\nthat branch interpolates the workload size. The rendered text is unchanged -\nthe diff moves no character of either paragraph.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* TEST-11: assert the metadata the build produces, not just the files it copies\n\ntest_essential_files_in_distribution is driven by paths that exist in the\nsource tree, so it structurally cannot notice PKG-INFO or the .dist-info\ndirectory going missing - a failure that would otherwise surface at upload.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* ledger: re-verify every entry against the data-package split, record pass 10\n\nDeletes the four entries this pass shipped (DUP-2, TEST-11, REND-1, TOOL-5),\ncorrects TOOL-1's B905 claim - the load-path zip it named cannot truncate, both\nlists being local accumulators appended in one loop - and narrows DEAD-5 to the\ndeletion decision now that its annotation half is fixed. Adds TOOL-7 for the\nrelease guard's silent single-wheel pick, a scope note for the thin data\ndistribution, and the pass 10 coverage row.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n---------\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-20T00:20:37+02:00",
          "tree_id": "e50a9152f1d951ecc7396043dabd687391b1bf78",
          "url": "https://github.com/jannikmi/timezonefinder/commit/64da9e1a30df7565d2742ab22b9ee755f03b9476"
        },
        "date": 1787178125695,
        "tool": "pytest",
        "benches": [
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[random-in_memory]",
            "value": 71.01147538339397,
            "unit": "iter/sec",
            "range": "stddev: 0.00028397787656812834",
            "extra": "mean: 14.082231000003276 msec\nrounds: 60 on AMD EPYC 7763 64-Core Processor @ 2.4454 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[unique_shortcut-in_memory]",
            "value": 231.92627527561274,
            "unit": "iter/sec",
            "range": "stddev: 0.00008478332651968453",
            "extra": "mean: 4.311715000000049 msec\nrounds: 195 on AMD EPYC 7763 64-Core Processor @ 2.4454 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[ambiguous_shortcut-in_memory]",
            "value": 24.865381930401142,
            "unit": "iter/sec",
            "range": "stddev: 0.00235419507327891",
            "extra": "mean: 40.21655500000065 msec\nrounds: 50 on AMD EPYC 7763 64-Core Processor @ 2.4454 GHz"
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
          "id": "db9c6f8532d1cd23ebb7c2b0fa4fc56edf538c0d",
          "message": "Merge pull request #538 from weed33834/docs/use-cases-503\n\ndocs(use-cases): drop pytz as the offset reference, warn about the Etc/GMT±X sign footgun (closes #503)",
          "timestamp": "2026-08-20T01:29:57+02:00",
          "tree_id": "1cba5ed8ef96df32b00a8a33d109822bac8760e9",
          "url": "https://github.com/jannikmi/timezonefinder/commit/db9c6f8532d1cd23ebb7c2b0fa4fc56edf538c0d"
        },
        "date": 1787182268531,
        "tool": "pytest",
        "benches": [
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[random-in_memory]",
            "value": 80.77718639007215,
            "unit": "iter/sec",
            "range": "stddev: 0.000342232534964755",
            "extra": "mean: 12.379732999995952 msec\nrounds: 57 on INTEL(R) XEON(R) PLATINUM 8573C @ 3.0089 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[unique_shortcut-in_memory]",
            "value": 260.4540391083969,
            "unit": "iter/sec",
            "range": "stddev: 0.00011863191604404065",
            "extra": "mean: 3.8394489999973302 msec\nrounds: 205 on INTEL(R) XEON(R) PLATINUM 8573C @ 3.0089 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[ambiguous_shortcut-in_memory]",
            "value": 27.086802475560113,
            "unit": "iter/sec",
            "range": "stddev: 0.0007145820815651182",
            "extra": "mean: 36.91834800000038 msec\nrounds: 50 on INTEL(R) XEON(R) PLATINUM 8573C @ 3.0089 GHz"
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
          "id": "20ae948fc8d72357e97ed0c01e6128afc550bd83",
          "message": "Merge pull request #537 from jannikmi/roadmap/497-profile-query-time\n\nProfile where per-query time actually goes (#497)",
          "timestamp": "2026-08-20T02:21:37+02:00",
          "tree_id": "ba0ad600fcde8de14e3b2bf5975bdc32f436ccf2",
          "url": "https://github.com/jannikmi/timezonefinder/commit/20ae948fc8d72357e97ed0c01e6128afc550bd83"
        },
        "date": 1787185366033,
        "tool": "pytest",
        "benches": [
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[random-in_memory]",
            "value": 94.89748556817491,
            "unit": "iter/sec",
            "range": "stddev: 0.0001317228235801293",
            "extra": "mean: 10.537686999953166 msec\nrounds: 76 on AMD EPYC 9V74 80-Core Processor @ 3.6939 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[unique_shortcut-in_memory]",
            "value": 291.5632103204143,
            "unit": "iter/sec",
            "range": "stddev: 0.00006367563943112333",
            "extra": "mean: 3.4297880000053738 msec\nrounds: 223 on AMD EPYC 9V74 80-Core Processor @ 3.6939 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[ambiguous_shortcut-in_memory]",
            "value": 31.676850510133608,
            "unit": "iter/sec",
            "range": "stddev: 0.00017991932629635754",
            "extra": "mean: 31.568794999998318 msec\nrounds: 50 on AMD EPYC 9V74 80-Core Processor @ 3.6939 GHz"
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
          "id": "10d6467457600b58cd7ceccc21ba7e428cb15a55",
          "message": "Merge pull request #540 from jannikmi/skill/improvement-pass\n\nOne improvement-pass skill, and one register behind it",
          "timestamp": "2026-08-20T23:13:26+02:00",
          "tree_id": "4a0e87cf90900a632e7ee6583b05aca38b14de24",
          "url": "https://github.com/jannikmi/timezonefinder/commit/10d6467457600b58cd7ceccc21ba7e428cb15a55"
        },
        "date": 1787260476668,
        "tool": "pytest",
        "benches": [
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[random-in_memory]",
            "value": 92.54755278359183,
            "unit": "iter/sec",
            "range": "stddev: 0.00038410664488100276",
            "extra": "mean: 10.805255999997598 msec\nrounds: 75 on AMD EPYC 9V74 80-Core Processor @ 3.6972 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[unique_shortcut-in_memory]",
            "value": 293.3203333764608,
            "unit": "iter/sec",
            "range": "stddev: 0.0001162412150673603",
            "extra": "mean: 3.409241999996482 msec\nrounds: 225 on AMD EPYC 9V74 80-Core Processor @ 3.6972 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[ambiguous_shortcut-in_memory]",
            "value": 30.977922839822927,
            "unit": "iter/sec",
            "range": "stddev: 0.00041852140462968174",
            "extra": "mean: 32.281053999994924 msec\nrounds: 50 on AMD EPYC 9V74 80-Core Processor @ 3.6972 GHz"
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
          "id": "ce69bf737258d9695ace3ddfbecfdb8c48b9380e",
          "message": "Merge pull request #541 from jannikmi/register/record-the-measurements\n\nRecord the measurements four entries were waiting on, and three decisions",
          "timestamp": "2026-08-21T14:34:33+02:00",
          "tree_id": "146ec5377351eedc190737a239eccb35ae1eb335",
          "url": "https://github.com/jannikmi/timezonefinder/commit/ce69bf737258d9695ace3ddfbecfdb8c48b9380e"
        },
        "date": 1787315746643,
        "tool": "pytest",
        "benches": [
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[random-in_memory]",
            "value": 69.80718487656529,
            "unit": "iter/sec",
            "range": "stddev: 0.00017867163238632265",
            "extra": "mean: 14.325173000003133 msec\nrounds: 59 on AMD EPYC 9V74 80-Core Processor @ 2.5961 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[unique_shortcut-in_memory]",
            "value": 217.59101505762328,
            "unit": "iter/sec",
            "range": "stddev: 0.00006218964569761348",
            "extra": "mean: 4.595778000002326 msec\nrounds: 179 on AMD EPYC 9V74 80-Core Processor @ 2.5961 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[ambiguous_shortcut-in_memory]",
            "value": 24.265527966320636,
            "unit": "iter/sec",
            "range": "stddev: 0.00026862001472689094",
            "extra": "mean: 41.21072500000622 msec\nrounds: 50 on AMD EPYC 9V74 80-Core Processor @ 2.5961 GHz"
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
          "id": "fb5a3a3f24d3f18dcd0e13fbf756b74841396c53",
          "message": "Merge pull request #544 from jannikmi/perf/coordinate-offset-table\n\nAddress polygon coordinates by offset instead of re-walking the FlatBuffers vtable",
          "timestamp": "2026-08-22T02:36:53+02:00",
          "tree_id": "903d7f3a9c4fe4e70de1205e404e460c4b085e55",
          "url": "https://github.com/jannikmi/timezonefinder/commit/fb5a3a3f24d3f18dcd0e13fbf756b74841396c53"
        },
        "date": 1787359093195,
        "tool": "pytest",
        "benches": [
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[random-in_memory]",
            "value": 72.54816581548758,
            "unit": "iter/sec",
            "range": "stddev: 0.0003440626536923643",
            "extra": "mean: 13.783946000003766 msec\nrounds: 60 on AMD EPYC 7763 64-Core Processor @ 2.4454 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[unique_shortcut-in_memory]",
            "value": 229.08001237954528,
            "unit": "iter/sec",
            "range": "stddev: 0.0006326486546850572",
            "extra": "mean: 4.36528699999883 msec\nrounds: 189 on AMD EPYC 7763 64-Core Processor @ 2.4454 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[ambiguous_shortcut-in_memory]",
            "value": 24.821621280287623,
            "unit": "iter/sec",
            "range": "stddev: 0.0011448916773541254",
            "extra": "mean: 40.28745700000513 msec\nrounds: 50 on AMD EPYC 7763 64-Core Processor @ 2.4454 GHz"
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
          "id": "1d2d6eba2688e7fd291f2080deed20718154b400",
          "message": "Merge pull request #546 from jannikmi/ci/benchmark-comment-reposted\n\nPost the benchmark comparison anew instead of editing it in place",
          "timestamp": "2026-08-22T11:58:53+02:00",
          "tree_id": "fa76d10a56b7341b18aa9eb6c2236d62d77b3517",
          "url": "https://github.com/jannikmi/timezonefinder/commit/1d2d6eba2688e7fd291f2080deed20718154b400"
        },
        "date": 1787392807395,
        "tool": "pytest",
        "benches": [
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[random-in_memory]",
            "value": 92.49899731088675,
            "unit": "iter/sec",
            "range": "stddev: 0.0008639219246772046",
            "extra": "mean: 10.810927999997944 msec\nrounds: 65 on INTEL(R) XEON(R) PLATINUM 8573C @ 2.3000 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[unique_shortcut-in_memory]",
            "value": 299.25604946099605,
            "unit": "iter/sec",
            "range": "stddev: 0.0003069013677915662",
            "extra": "mean: 3.341620000000489 msec\nrounds: 232 on INTEL(R) XEON(R) PLATINUM 8573C @ 2.3000 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[ambiguous_shortcut-in_memory]",
            "value": 30.749612516439953,
            "unit": "iter/sec",
            "range": "stddev: 0.001499271537087475",
            "extra": "mean: 32.52073500000563 msec\nrounds: 50 on INTEL(R) XEON(R) PLATINUM 8573C @ 2.3000 GHz"
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
          "id": "f80c89b11da6bcc5239b0eadafbd978351e88787",
          "message": "Merge pull request #548 from jannikmi/fix/cli-stderr-line-count-assertion\n\nAssert the CLI's one error, not the interpreter's stderr line count",
          "timestamp": "2026-08-22T13:00:32+02:00",
          "tree_id": "2d5da4b736234d1b6b605aec7f1aa6813eff8e59",
          "url": "https://github.com/jannikmi/timezonefinder/commit/f80c89b11da6bcc5239b0eadafbd978351e88787"
        },
        "date": 1787396514015,
        "tool": "pytest",
        "benches": [
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[random-in_memory]",
            "value": 72.77852468737841,
            "unit": "iter/sec",
            "range": "stddev: 0.00010224748622223278",
            "extra": "mean: 13.740317000042523 msec\nrounds: 59 on AMD EPYC 7763 64-Core Processor @ 3.2433 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[unique_shortcut-in_memory]",
            "value": 227.17478396350612,
            "unit": "iter/sec",
            "range": "stddev: 0.000033157558036621084",
            "extra": "mean: 4.401896999979726 msec\nrounds: 190 on AMD EPYC 7763 64-Core Processor @ 3.2433 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[ambiguous_shortcut-in_memory]",
            "value": 25.188324919211574,
            "unit": "iter/sec",
            "range": "stddev: 0.0002820196946465669",
            "extra": "mean: 39.70093300000599 msec\nrounds: 50 on AMD EPYC 7763 64-Core Processor @ 3.2433 GHz"
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
          "id": "f8b5df9801fd47a6657faf92262e7518cd17d89c",
          "message": "Merge pull request #547 from jannikmi/skills/maintainer-decisions",
          "timestamp": "2026-08-22T22:08:28+02:00",
          "tree_id": "bc817356b62d5a6ec7dd72db555fb208fd225906",
          "url": "https://github.com/jannikmi/timezonefinder/commit/f8b5df9801fd47a6657faf92262e7518cd17d89c"
        },
        "date": 1787429370575,
        "tool": "pytest",
        "benches": [
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[random-in_memory]",
            "value": 92.80194691055893,
            "unit": "iter/sec",
            "range": "stddev: 0.000225696514993787",
            "extra": "mean: 10.775636000005306 msec\nrounds: 67 on INTEL(R) XEON(R) PLATINUM 8573C @ 3.5994 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[unique_shortcut-in_memory]",
            "value": 302.1319639909147,
            "unit": "iter/sec",
            "range": "stddev: 0.00008181669344015246",
            "extra": "mean: 3.3098119999976916 msec\nrounds: 244 on INTEL(R) XEON(R) PLATINUM 8573C @ 3.5994 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[ambiguous_shortcut-in_memory]",
            "value": 31.6413080567434,
            "unit": "iter/sec",
            "range": "stddev: 0.0009902672366461516",
            "extra": "mean: 31.60425599999428 msec\nrounds: 50 on INTEL(R) XEON(R) PLATINUM 8573C @ 3.5994 GHz"
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
          "id": "bd65e3a8def9b79cfaa652bc8d53e87f56dde0b0",
          "message": "Merge pull request #550 from jannikmi/bench/tzfpy-comparison\n\nMeasure the tzfpy comparison instead of asserting it",
          "timestamp": "2026-08-23T22:30:35+02:00",
          "tree_id": "83649ae1d67c370588fd6f300cf84c402ce6846c",
          "url": "https://github.com/jannikmi/timezonefinder/commit/bd65e3a8def9b79cfaa652bc8d53e87f56dde0b0"
        },
        "date": 1787517179740,
        "tool": "pytest",
        "benches": [
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[random-in_memory]",
            "value": 132.2507813376249,
            "unit": "iter/sec",
            "range": "stddev: 0.00007208475174284629",
            "extra": "mean: 7.5613919999995005 msec\nrounds: 97 on INTEL(R) XEON(R) PLATINUM 8573C @ 2.9997 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[unique_shortcut-in_memory]",
            "value": 254.96603724948713,
            "unit": "iter/sec",
            "range": "stddev: 0.00006511283548688269",
            "extra": "mean: 3.9220909999926334 msec\nrounds: 233 on INTEL(R) XEON(R) PLATINUM 8573C @ 2.9997 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[ambiguous_shortcut-in_memory]",
            "value": 24.75592024216712,
            "unit": "iter/sec",
            "range": "stddev: 0.0003077884188878541",
            "extra": "mean: 40.39437800000201 msec\nrounds: 50 on INTEL(R) XEON(R) PLATINUM 8573C @ 2.9997 GHz"
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
          "id": "ddc207e72ea1b1b54d7ec390ca63ee172e0ae938",
          "message": "Merge pull request #551 from jannikmi/improve/bug-1-negative-ids\n\nReject a negative id instead of counting from the end",
          "timestamp": "2026-08-23T23:16:43+02:00",
          "tree_id": "e5838ba04a2d08af3aa81be00410df4517f4deb4",
          "url": "https://github.com/jannikmi/timezonefinder/commit/ddc207e72ea1b1b54d7ec390ca63ee172e0ae938"
        },
        "date": 1787519853686,
        "tool": "pytest",
        "benches": [
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[random-in_memory]",
            "value": 123.96487777477802,
            "unit": "iter/sec",
            "range": "stddev: 0.0001224088172390881",
            "extra": "mean: 8.066801000012447 msec\nrounds: 98 on AMD EPYC 7763 64-Core Processor @ 2.4454 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[unique_shortcut-in_memory]",
            "value": 243.10901421504866,
            "unit": "iter/sec",
            "range": "stddev: 0.00009867185685943308",
            "extra": "mean: 4.113380999996252 msec\nrounds: 222 on AMD EPYC 7763 64-Core Processor @ 2.4454 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[ambiguous_shortcut-in_memory]",
            "value": 23.605699832280852,
            "unit": "iter/sec",
            "range": "stddev: 0.00028619311099872965",
            "extra": "mean: 42.36265000000117 msec\nrounds: 50 on AMD EPYC 7763 64-Core Processor @ 2.4454 GHz"
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
          "id": "31c18bba3ef3c07ddc4ecb2d01f991111826a0f6",
          "message": "Merge pull request #553 from jannikmi/decisions/round-1\n\nRecord the maintainer decisions on DATA-BINARIES, GH-500, GH-501, GH-428 and PERF-4",
          "timestamp": "2026-08-24T04:37:50+02:00",
          "tree_id": "29db0f4fb55a5d3e3b168b5dd0141121b7792bf6",
          "url": "https://github.com/jannikmi/timezonefinder/commit/31c18bba3ef3c07ddc4ecb2d01f991111826a0f6"
        },
        "date": 1787539124409,
        "tool": "pytest",
        "benches": [
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[random-in_memory]",
            "value": 117.5002940445012,
            "unit": "iter/sec",
            "range": "stddev: 0.0012214530515568711",
            "extra": "mean: 8.510616999998888 msec\nrounds: 94 on AMD EPYC 7763 64-Core Processor @ 3.2446 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[unique_shortcut-in_memory]",
            "value": 241.79674323948743,
            "unit": "iter/sec",
            "range": "stddev: 0.00006256002444947966",
            "extra": "mean: 4.135705000003043 msec\nrounds: 218 on AMD EPYC 7763 64-Core Processor @ 3.2446 GHz"
          },
          {
            "name": "benchmarks/test_timezone_finding.py::test_timezone_at[ambiguous_shortcut-in_memory]",
            "value": 22.748907455284073,
            "unit": "iter/sec",
            "range": "stddev: 0.0007064689745973316",
            "extra": "mean: 43.958154999998555 msec\nrounds: 50 on AMD EPYC 7763 64-Core Processor @ 3.2446 GHz"
          }
        ]
      }
    ],
    "memory footprint (heap, min)": [
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
          "id": "8e1b48151709324633de207020b41e437d823dee",
          "message": "Stop the shortcut loader pinning the whole file buffer (#467)\n\n* Stop the shortcut loader pinning the whole file buffer\n\n`PolyIdsAsNumpy()` is `np.frombuffer` under the hood, so every poly id\narray the hybrid shortcut reader returned was a view onto the `bytes` it\nhad read the file into. 10,511 such views held the full 1,566,856 byte\nbuffer alive for the lifetime of every finder instance, although the\nlive poly id payload is only 46,746 bytes - ~33x more pinned than used.\n\nCopy each block out in the iteration that decodes it, so the view dies\nimmediately, and fill the entries with read-only slices of the\naccumulated payload afterwards. The buffer is released when the loader\nreturns: heap 7,433,653 -> 4,652,471 B (-37.4%), resident set ~2 MB\nlower per instance, load time unchanged at ~0.39 s (the per-entry\nflatbuffers decode dominates).\n\nCopying per block rather than holding the views and concatenating them\nat the end is what keeps the resident set moving in the same direction\nas the heap. Both free the buffer, but concatenating has the whole set\nof views alive while the replacement arrays are built, and that\ntransient peak (8.98 MiB, against 7.09 MiB for the pinning version)\nnever comes back: the allocator does not return the pages, so a 2.65 MiB\nheap saving turned into a 3.5 MiB RSS regression - measured, and the\nwrong trade for the constrained containers this is for. Streaming the\ncopy peaks at 6.14 MiB instead, below the version it replaces.\n\nOverwriting an existing dict key preserves its insertion position, so\nthe mapping is still iterated in file order by `test_shortcut_sorting`\nand `scripts/reporting.py`.\n\nBoth memory modes and both public classes were affected - `in_memory`\ndoes not reach this path.\n\n`test_shortcut_arrays_do_not_pin_the_file_buffer` asserts the ownership\ncontract by walking each array's `.base` chain, next to the opposite\ncontract for polygon coordinates, which are views onto the mmap by\ndesign. It asserts the size of the shared buffer rather than its type:\nthe whole file would satisfy any weaker check, and is what this used to\nhand out.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Regenerate the memory report against the compact shortcut mapping\n\n`make memory` + `scripts.render_benchmark_reports --memory-json`, on the\nsame machine and interpreter the committed report was measured on\n(Python 3.14.2, NumPy 2.3.5, Darwin arm64, numba). Re-rendering the\npre-change measurement first reproduced every committed heap figure\nexactly, so the diff below is the change, not the machine.\n\nHeap drops by 2.65 MiB in all three configurations - the shortcut\nmapping is loaded by each of them - which is 37% of `TimezoneFinderL`,\nwhose only large structure it is. RSS drops by 1.4-1.7 MiB. The\nin-memory-vs-file-based heap ratio in the summary rises from 8.58x to\n12.1x because the denominator shrank.\n\n`docs/alternatives.rst` quotes two of these figures by hand and is\nupdated with them.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n---------\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-07T15:15:54+02:00",
          "tree_id": "a3009cc671be5c069ca21a50f672341dcd8a8c84",
          "url": "https://github.com/jannikmi/timezonefinder/commit/8e1b48151709324633de207020b41e437d823dee"
        },
        "date": 1786108637040,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "memory::TimezoneFinderL::init_heap",
            "value": 4.466641426086426,
            "range": "± 0.000",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.5961 GHz"
          },
          {
            "name": "memory::TimezoneFinderL::steady_heap",
            "value": 4.466804504394531,
            "range": "± 0.000",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.5961 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::init_heap",
            "value": 4.529212951660156,
            "range": "± 0.000",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.5961 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::steady_heap",
            "value": 4.5380048751831055,
            "range": "± 0.000",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.5961 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::init_heap",
            "value": 67.84999752044678,
            "range": "± 0.000",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.5961 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::steady_heap",
            "value": 67.85872173309326,
            "range": "± 0.000",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.5961 GHz"
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
          "id": "68107f0282f567a7721afb0356e89d05b412fea6",
          "message": "Trim the unreleased changelog to end states (#474)\n\nSeveral unreleased bullets ran 8-15 lines and read as design journal\nentries, against this repository's own rule that a released section\nshould read as if each feature arrived in one step. The reasoning they\ncarried was also invisible to anyone not reading a changelog diff.\n\nEach is reduced to end state plus the one decision-relevant sentence,\nwith the reasoning left where it now lives:\n\n- the six bullets covering continuous benchmarking - CI setup,\n  merge-base comparison, machine stamping, estimator and threshold,\n  tracked core set, guardrails - become two, pointing at\n  docs/benchmarking_methodology.rst, which carries the ~25.5% ambiguous\n  ratio, the ~14x cost ratio, the 134-158% cross-machine spread and\n  every threshold derivation\n- the per-axis storage and layout_version bullets shrink to their user\n  visible consequence and link docs/data_format.rst, which documents\n  both already\n- the __slots__ item keeps the one line that matters (an unassigned slot\n  re-permits the attribute it names); the design context is in\n  docs/architecture.rst\n- pre-commit-clean generators, `make flatbuf`, the mypy exemption list,\n  the shortcut schema registry and the dead-code removal trim to end\n  state and leave the why at the point of decision, where it already is\n\nBullets describing one feature are merged: the BufferError fix and its\naccessor half, the weekly data update workflow across its three stages,\nthe update_data.sh changes, the quality-pass skill and its ledger, the\ntwo generator normalisations.\n\n28 Internal bullets become 17, 9 user-facing become 8, the section loses\na quarter of its lines. Every issue reference and contributor\nattribution is preserved - verified by extracting both sets before and\nafter. Released sections are untouched: they are historical record.\n\nNo changelog entry for this, deliberately. Amending the unreleased\nsection is the prescribed mechanism, and a bullet announcing that\nbullets were edited would be self-referential noise.\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-07T15:20:34+02:00",
          "tree_id": "abb8db7f6ca8afb681f0f99f1d36aef8f62e5c55",
          "url": "https://github.com/jannikmi/timezonefinder/commit/68107f0282f567a7721afb0356e89d05b412fea6"
        },
        "date": 1786108922427,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "memory::TimezoneFinderL::init_heap",
            "value": 4.4666948318481445,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 2.4454 GHz"
          },
          {
            "name": "memory::TimezoneFinderL::steady_heap",
            "value": 4.46685791015625,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 2.4454 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::init_heap",
            "value": 4.52925968170166,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 2.4454 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::steady_heap",
            "value": 4.537982940673828,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 2.4454 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::init_heap",
            "value": 67.85003471374512,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 2.4454 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::steady_heap",
            "value": 67.85880470275879,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 2.4454 GHz"
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
          "id": "d36ebdee0912f7752492bade84a392800e55446b",
          "message": "Restructure the README around what the library does (#472)\n\nThe only page guaranteed to be read spent its budget on badges, a\nmaintainer-wanted notice, a six-line quickstart and a link list: one\nsentence on how the library works, zero numbers.\n\nThree short sections are added, all of it prose that already existed\nelsewhere in the repository:\n\n- *How it works* - the lookup pipeline, and the trade-off it exists to\n  serve: the polygons are never simplified, and the H3 index is what\n  makes carrying them affordable\n- *Performance* - one throughput figure with its configuration named,\n  the three point-in-polygon backends, and the pure-Python fallback that\n  costs speed but never results. Links to the trend chart, the reports\n  and the methodology\n- *Engineering notes* - architecture, data format, benchmarking\n  methodology, alternatives, changelog. The block that converts a\n  browsing reader into a reading one\n\nThe top of the page is reordered: banner, one-sentence positioning,\nbadges, quickstart. A reader now reaches a technical sentence within one\nscreen instead of ~10 badges and a maintainer notice.\n\nThe maintainers-wanted notice moves out of the first heading after the\nintro into a Contributing section at the bottom. The message is\nunchanged - as the second thing a reader saw it landed as \"this project\nis being wound down\" before any technical content. That section also\nlinks CONTRIBUTING.md, which the README did not link at all.\n\nEvery link and image source is absolute; verified by rendering the file\nthe way PyPI does rather than by rstcheck alone, which passes a valid\ndirective whose target does not resolve.\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-07T15:30:32+02:00",
          "tree_id": "afa08109f4d0c26466740a712a90f84bbc43155e",
          "url": "https://github.com/jannikmi/timezonefinder/commit/d36ebdee0912f7752492bade84a392800e55446b"
        },
        "date": 1786109513858,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "memory::TimezoneFinderL::init_heap",
            "value": 4.466550827026367,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on INTEL(R) XEON(R) PLATINUM 8573C @ 3.1976 GHz"
          },
          {
            "name": "memory::TimezoneFinderL::steady_heap",
            "value": 4.466713905334473,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on INTEL(R) XEON(R) PLATINUM 8573C @ 3.1976 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::init_heap",
            "value": 4.529166221618652,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on INTEL(R) XEON(R) PLATINUM 8573C @ 3.1976 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::steady_heap",
            "value": 4.537917137145996,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on INTEL(R) XEON(R) PLATINUM 8573C @ 3.1976 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::init_heap",
            "value": 67.8499402999878,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on INTEL(R) XEON(R) PLATINUM 8573C @ 3.1976 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::steady_heap",
            "value": 67.85868263244629,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on INTEL(R) XEON(R) PLATINUM 8573C @ 3.1976 GHz"
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
          "id": "46deb0ed04873d0c6e9590c765122e4d4338a808",
          "message": "Put the headline figure and the configuration above the fold in the benchmark reports (#473)\n\n`benchmark_results_timezonefinding.rst` made a reader parse four tables\nbefore learning \"~3.50us per lookup, ~286k/s\". Each of the four generated\nreports now opens with the figure that answers \"how fast/how big is it\",\nderived from the same parsed JSON as the tables below it - nothing here\nis hardcoded, or the block would go stale exactly when the numbers move.\n\nUnderneath it, a one-line banner names the platform, Python version and\nthe acceleration path that produced the numbers, and states whether that\nis the configuration CI tracks. It usually is not: the committed reports\nare rendered from a developer machine with Numba on and the C extension\noff, while CI measures the C extension without Numba - what a plain\n`pip install timezonefinder` gives you. That was already discoverable\nfrom the \"System Status\" section three screens down, as two separate\nbooleans; a reader comparing a table here against the trend chart was\ncomparing two implementations on two machines with nothing saying so.\nThe banner links the methodology page.\n\n`acceleration_path_label` collapses the two recorded flags to the one\npath that ran, since `utils.py` prefers Numba when both are importable -\nthey were never two independent choices.\n\nThe memory report gets the same treatment rather than being deferred: it\nis a fourth page in the same sidebar rendered by the same module, and a\nbanner on three of four pages is worse than none.\n\nThe three timing reports re-rendered byte-identically from the stored\nJSON before this change, so their diffs are the new block and nothing\nelse. The memory report was re-measured instead, because the stored JSON\npredates #467: every heap figure reproduces that PR's values exactly and\nonly four RSS digits move, which is the metric whose residency depends on\nmachine-wide pressure and which is deliberately not charted for that\nreason.\n\n`tests/test_render_benchmark_reports.py` covers the path label, the\nCI-configuration branch and the environment description. It also pins\nthat a headline never nests an RST literal inside bold - that shipped in\nan intermediate version of this change and rendered as stray backticks in\nthe HTML, with no warning from Sphinx or rstcheck.\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-07T15:35:18+02:00",
          "tree_id": "21bc221203c641bc1c1b1c314275dc7659145338",
          "url": "https://github.com/jannikmi/timezonefinder/commit/46deb0ed04873d0c6e9590c765122e4d4338a808"
        },
        "date": 1786109800439,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "memory::TimezoneFinderL::init_heap",
            "value": 4.466736793518066,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.8702 GHz"
          },
          {
            "name": "memory::TimezoneFinderL::steady_heap",
            "value": 4.466899871826172,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.8702 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::init_heap",
            "value": 4.5291748046875,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.8702 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::steady_heap",
            "value": 4.5380659103393555,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.8702 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::init_heap",
            "value": 67.84981918334961,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.8702 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::steady_heap",
            "value": 67.85863780975342,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.8702 GHz"
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
          "id": "48ac98ba0b2e93f018220e9ab17155248131ddaa",
          "message": "Post the benchmark comparison where reviewers can see it (#476)\n\nThe comparison was posted with `POST /repos/{owner}/{repo}/commits/{sha}/comments`,\non the assumption - written into the workflow and CONTRIBUTING.md - that a\ncommit comment surfaces in the pull request's conversation timeline. It does\nnot. GitHub renders issue comments, reviews and review comments there; a commit\ncomment appears only on the commit's own page.\n\nSo the job went green, the API call returned 201, and the table reached nobody.\nConfirmed on PR #472: commitcomment-195337089 exists on its head commit with the\nfull body, while the pull request's timeline holds no `commit_commented` event\nat all.\n\nIt is now an issue comment on the pull request:\n\n- the number is resolved from the trusted `workflow_run.head_sha` via\n  `GET /commits/{sha}/pulls`, not read from `workflow_run.pull_requests`, which\n  is empty for fork pull requests - the case this split workflow exists to serve\n- a marker identifies the workflow's own comment so each run edits it in place.\n  Commit comments were one per commit; issue comments would otherwise stack a\n  full table on every push\n- no open pull request for the SHA exits 0 with a notice, so a comparison\n  landing after a merge does not fail the run\n\n`contents` drops from write to read - that write bought nothing but\ncreateCommitComment - and `pull-requests: write` takes its place.\n\n`tests/test_benchmark_workflows.py` pins the endpoint and the permission.\nNothing failed while the comparison was being posted somewhere invisible, which\nis exactly the class of silent breakage that module exists to catch.\n\nNo changelog entry: the unreleased bullet already describes posting the\ncomparison on the pull request, which this makes true.\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-07T15:54:16+02:00",
          "tree_id": "e9e0dc06060e7819e2599ab77f71a99906293f5b",
          "url": "https://github.com/jannikmi/timezonefinder/commit/48ac98ba0b2e93f018220e9ab17155248131ddaa"
        },
        "date": 1786110950863,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "memory::TimezoneFinderL::init_heap",
            "value": 4.466645240783691,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.5961 GHz"
          },
          {
            "name": "memory::TimezoneFinderL::steady_heap",
            "value": 4.466808319091797,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.5961 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::init_heap",
            "value": 4.529207229614258,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.5961 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::steady_heap",
            "value": 4.5379743576049805,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.5961 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::init_heap",
            "value": 67.84999752044678,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.5961 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::steady_heap",
            "value": 67.85881614685059,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.5961 GHz"
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
          "id": "1478c266bf0eb7b930ba5096ce4ae73c5b64fe74",
          "message": "Stop restating generated figures in hand-written docs (#478)\n\n* Stop restating generated figures in hand-written docs\n\nExact numbers copied out of the generated pages go stale the moment the\ndata or the code moves, and nothing catches it. That had already\nhappened: #467 changed the memory footprint, leaving `~8 MiB`/`~71 MiB`\nwrong in `alternatives.rst` (twice), in the pytzwhere comparison and in\nthe changelog bullet describing the memory report.\n\nRemoved from the prose, with a link to the page that carries the live\nvalue instead:\n\n- the dataset counts - 7,925,313 boundary vertices, 1,322 polygons, 756\n  holes - from `alternatives.rst` and `architecture.rst`. These change\n  on every boundary-data update; `data_report.rst` is generated from the\n  packaged data\n- the shortcut index size, the wheel and installed sizes, and the\n  version-pinned `8.2.5`/`1.3.2` distribution figures\n- the memory footprints, now \"single-digit MiB\" against \"an order of\n  magnitude more\"\n- the lookup throughput, now \"hundreds of thousands of queries/s\", in\n  both the README and the comparison table\n\nThe tzfpy speed row becomes qualitative on both sides rather than a\nside-by-side of two numbers nobody measured together - which is what the\nnote under the table already told the reader to do with it.\n\nKept: figures fixed by a constant rather than by the data (`~1 cm`\nfollows from `COORD2INT_FACTOR`, `~41k` cells from H3 resolution 3, the\n`~400x` pure-Python penalty), and the pytzwhere figures, which describe a\npackage that has not moved since 2016.\n\nThe H3 resolution study in `data_format.rst` keeps its finding - the\n`>10 %` ratio that made resolution 4 not worth it - but drops the\nabsolute index size, which read as a current measurement and was already\noff. `CLAUDE.md` gains the rule under *Documentation Files*.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Round the ambiguous-query ratio, and rebase before the final test gate\n\nTwo follow-ups on the same theme as this branch.\n\n`~25.5 %` ambiguous queries in the benchmarking methodology page is\ndataset-derived and drifts with every boundary-data update. The argument\nit supports - that uniformly random points are the only globally\nrepresentative workload - does not need the decimal, so it is now `~25 %`,\nmatching the figure the same section already uses two paragraphs down.\n\n`CLAUDE.md` gains the ordering rule under *Testing*: fetch and rebase\nonto the latest `master` before running the final gate, not after. Other\nwork merges while a PR is open, and a rebase afterwards invalidates the\nrun - it tested a tree that never existed - so the wrong order costs a\nsecond `make testall`.\n\nAlso amends the package-comparison changelog bullet, which still\ndescribed the `Distribution Size` figure and the two-number speed row\nthat the previous commit removed. Per the amend-don't-append rule the\nunreleased section has to read as one end state.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n---------\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-07T16:04:17+02:00",
          "tree_id": "f9c6d02acd45e209e22f5fd7bac50d050d575c84",
          "url": "https://github.com/jannikmi/timezonefinder/commit/1478c266bf0eb7b930ba5096ce4ae73c5b64fe74"
        },
        "date": 1786111551151,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "memory::TimezoneFinderL::init_heap",
            "value": 4.466641426086426,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 2.4454 GHz"
          },
          {
            "name": "memory::TimezoneFinderL::steady_heap",
            "value": 4.466804504394531,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 2.4454 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::init_heap",
            "value": 4.529175758361816,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 2.4454 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::steady_heap",
            "value": 4.53810977935791,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 2.4454 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::init_heap",
            "value": 67.84990501403809,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 2.4454 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::steady_heap",
            "value": 67.85866165161133,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 2.4454 GHz"
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
          "id": "4f38bbe3e8e5b7678aecad0de1461fe9554fd484",
          "message": "Make a stale generated report fail instead of reading plausible (#479)",
          "timestamp": "2026-08-08T12:34:33+02:00",
          "tree_id": "ea1e628828bf4386a8ce0b73113f3aa164a76c66",
          "url": "https://github.com/jannikmi/timezonefinder/commit/4f38bbe3e8e5b7678aecad0de1461fe9554fd484"
        },
        "date": 1786185354340,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "memory::TimezoneFinderL::init_heap",
            "value": 4.466646194458008,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.5961 GHz"
          },
          {
            "name": "memory::TimezoneFinderL::steady_heap",
            "value": 4.466809272766113,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.5961 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::init_heap",
            "value": 4.529247283935547,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.5961 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::steady_heap",
            "value": 4.538018226623535,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.5961 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::init_heap",
            "value": 67.85002613067627,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.5961 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::steady_heap",
            "value": 67.85881328582764,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.5961 GHz"
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
          "id": "dd7237138870af7a65b8f96df366aea623440152",
          "message": "Print the CLI result instead of routing it through a temp file (#480)\n\n* Print the CLI result instead of routing it through a temp file\n\nmain redirected stdout to a mkstemp file for the duration of the lookup\nand then, in verbose mode, reopened that file to read back a string it\nstill held in a local variable. Nothing inside the redirected block ever\nwrote to stdout: the lookup functions return their result rather than\nprinting it, and the only prints in the package are on data *write*\npaths a lookup never reaches. The context manager, the read-back, the\nwarning it raised when the file could not be read and the cleanup that\nremoved it are gone.\n\nThe lookup function is now resolved once per invocation instead of\ntwice, so -f 3 / -f 4 under -v no longer construct a second\nTimezoneFinderL and reload its shortcut data purely to read a function\nname off it. _print_lookup_details is renamed _format_lookup_details\nafter what it does; _lookup_timezone is dropped, since its only job was\nto pair the resolution with the call.\n\nOutput is unchanged character for character, verified across 5 function\nids x 2 modes x 4 coordinates plus --help and a rejected id.\n\ntests/cli_test.py covered none of this. Its single test passed the\ncaptured stdout through rstrip(\"\\n\\x1b[0m\"), which strips a *set* of\ncharacters rather than a suffix and so truncates 12 of the 444 packaged\nzone names (Europe/Amsterdam -> Europe/Amsterda); it held only because\nthe four hardcoded coordinates happened to miss all twelve. Two of its\nasserts were vacuous: res == \"None\" can never match, since the CLI\nprints an empty line and not the string None - and that dead branch\nmasked exactly the regression of printing None - while the\n\"command not found\" check is unreachable under check=True. The\nreplacement asserts the printed name verbatim and adds the missing\ncases: verbose mode, the empty line printed when no timezone is found,\nand the rejected function id.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Record pass 3 in the findings ledger\n\nCLI-1, CLI-2 and CLI-3 shipped, with the judgement call on CLI-3 (remove\nthe redirect rather than document it) written down. Adds CLI-4 for the\ntest defect found while covering them, TEST-1 and TEST-2 from this\npass's sweep, and folds a second A002 site into TYPE-4.\n\nCoverage log gains pass 3 and narrows what is left unswept to\nrender_benchmark_reports.py, describe_benchmark_machine.py and the\nbenchmarks/test_*.py suites, plus the ruff --select ALL families already\njudged not worth acting on so the next pass does not re-triage them.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Record that a local test run covers one point in the support matrix\n\nA test in this PR asserted argparse's exact wording, which renders the\nrejected value bare on 3.11 and quoted from 3.12 on. It passed a full\nlocal make testall and failed the 3.11 CI job.\n\nThe interpreter is only one axis, and not the sharpest one: tox spans\npy{311,312,313,314}{,-numba,-pytz}, and because the default dev\nenvironment installs numba, utils.py's import-time dispatch resolves\ninside_polygon to the numba path locally - so a local gate never\nexercises the C extension the bare CI envs use, however green it is.\n\nAdds the general rule to the Testing section, next to the existing note\non gate ordering, with the cheap way to test a single axis.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n---------\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-09T00:15:29+02:00",
          "tree_id": "9675950d2bb209fe3f02955a5001b8b8fb1a73e6",
          "url": "https://github.com/jannikmi/timezonefinder/commit/dd7237138870af7a65b8f96df366aea623440152"
        },
        "date": 1786227405382,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "memory::TimezoneFinderL::init_heap",
            "value": 4.466689109802246,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.7797 GHz"
          },
          {
            "name": "memory::TimezoneFinderL::steady_heap",
            "value": 4.466852188110352,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.7797 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::init_heap",
            "value": 4.529267311096191,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.7797 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::steady_heap",
            "value": 4.538111686706543,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.7797 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::init_heap",
            "value": 67.85002708435059,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.7797 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::steady_heap",
            "value": 67.85875225067139,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.7797 GHz"
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
          "id": "d65001fe3c0feb2daf965ee47cdc3f331a0f629b",
          "message": "Make the docstrings describe the code that exists (#481)\n\n* Make the docstrings describe the code that exists\n\nSix docstrings documented something the implementation contradicts, and five\nmore documented parameters that no longer exist.\n\nThe consequential ones are public API. AbstractTimezoneFinder.__init__ called\nin_memory inert and \"kept for API compatibility\" when it is exactly what selects\nmemory-mapped against in-memory coordinate access - and since\nTimezoneFinder.__init__ carries no docstring of its own, inspect.getdoc inherits\nthat claim, so help(TimezoneFinder.__init__) told users the opposite of\ndocs/1_usage.rst. Both get_geometry docstrings named a timezone_names.json that\nhas never existed under that name. read_zone_names promised an empty list for a\nmissing file where it raises FileNotFoundError, and illustrated itself with a\nhardcoded zone count the packaged data had outgrown by three. zone_id_of and\nzone_name_from_id each advertised an exception type their handler converts away,\nsending callers to write an except clause that can never fire while omitting the\none that will.\n\nThe remaining five are :param:/Args: entries in scripts/ and tests/ for\narguments removed along with the parallel shortcut compilation they belonged to;\ncompile_shortcut_mapping's summary still claimed \"optimized parallel processing\"\nthat the NOTE at the foot of its own docstring contradicts.\n\ntests/test_documented_contracts.py pins the claims that are behaviour: the\nexception types both finder methods raise, and that in_memory really does select\nthe coordinate accessor. Every assertion was mutation-checked.\n\n* Record pass 4 in the findings ledger, and drop what has shipped\n\nThe ledger is a to-do list, not a history: entries a pass ships are deleted in\nthe same PR rather than kept with a `shipped` status. The code is the evidence\nthey are done, the changelog says what changed, and git log still has the text.\nRejected, out-of-scope and withdrawn entries stay, because those encode a dead\nend worth not re-discovering. That removes the ERR-*, CLI-* and DOC-* sections -\nevery entry in them had shipped - and takes the file from 575 lines to 384.\n\nAlso cuts the ledger's largest source of merge conflicts between concurrent\npasses: a shipped entry is dead weight that every later pass has to carry past.\n\nPass 4 itself: DOC-1 and DOC-2 shipped (and so removed), plus a first sweep of\nscripts/render_benchmark_reports.py, scripts/describe_benchmark_machine.py and\nthe benchmarks/test_*.py suites - the areas the previous pass flagged as\nuncovered. Adds a Behaviour defects section for the two findings a quality pass\nmay not act on: a negative id silently returns the last zone from both\nzone_id_of and zone_name_from_id, and AbstractTimezoneFinder.__init__ accepts an\nin_memory it never reads.",
          "timestamp": "2026-08-09T00:43:07+02:00",
          "tree_id": "6e99e58e0a9ddbb4cac04532645879bbf2a8b03c",
          "url": "https://github.com/jannikmi/timezonefinder/commit/d65001fe3c0feb2daf965ee47cdc3f331a0f629b"
        },
        "date": 1786229100551,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "memory::TimezoneFinderL::init_heap",
            "value": 4.466689109802246,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.5961 GHz"
          },
          {
            "name": "memory::TimezoneFinderL::steady_heap",
            "value": 4.466852188110352,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.5961 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::init_heap",
            "value": 4.529219627380371,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.5961 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::steady_heap",
            "value": 4.537807464599609,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.5961 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::init_heap",
            "value": 67.8497314453125,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.5961 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::steady_heap",
            "value": 67.85850429534912,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.5961 GHz"
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
          "id": "c0a68875e457105cab72a71b600de329bf74d533",
          "message": "Let several quality passes run at once without colliding (#484)\n\nTwo passes running concurrently shared one repository, one ledger and one\nchangelog with nothing arranging that between them, and the skill actively made\nit worse: it hardcoded a single worktree path, so the second pass could not even\ncreate its tree, and it said nothing about when to push, so a branch became\nvisible only once the work was already done. Nothing stopped two passes from\npicking the same theme and doing it twice.\n\nThe remote branch list is now the coordination mechanism, used at two defined\nmoments: survey it before creating a worktree, and claim a theme by pushing the\nbranch the instant triage picks one - a slug that names the theme, pushed while\nit still points at master. First push wins a collision; the loser takes its\nnext-ranked candidate rather than racing. Worktree and branch names are per-pass.\n\nThe two files that collide regardless are named, with their resolutions: the\nchangelog, where both bullets are kept, and the ledger, whose remaining overlap\nis one entry both passes re-verified.\n\nThe ledger becomes a to-do list rather than a history: an entry is deleted by the\npull request that ships it, since the code is the evidence and git log keeps the\ntext. Only rejected, out-of-scope and withdrawn entries stay, because those\nencode a dead end worth not rediscovering. Shipped entries interleaved with live\nones were the ledger's largest conflict surface.\n\nThe changelog bullet is amended rather than appended, per CLAUDE.md - the skill\narrived in this same unreleased section.",
          "timestamp": "2026-08-09T00:45:45+02:00",
          "tree_id": "5b15034089463f4db849a2dae15ad8f4eab1580d",
          "url": "https://github.com/jannikmi/timezonefinder/commit/c0a68875e457105cab72a71b600de329bf74d533"
        },
        "date": 1786229232517,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "memory::TimezoneFinderL::init_heap",
            "value": 4.466689109802246,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.5961 GHz"
          },
          {
            "name": "memory::TimezoneFinderL::steady_heap",
            "value": 4.466852188110352,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.5961 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::init_heap",
            "value": 4.529081344604492,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.5961 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::steady_heap",
            "value": 4.537737846374512,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.5961 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::init_heap",
            "value": 67.84978199005127,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.5961 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::steady_heap",
            "value": 67.85864353179932,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.5961 GHz"
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
          "id": "ed54d346e509d33850542929b19feef375293ff3",
          "message": "Make the checks that cannot fail actually fail (#485)",
          "timestamp": "2026-08-09T07:01:24+02:00",
          "tree_id": "9ef73291fd7953132aeedb4a3fbf2764fd47e078",
          "url": "https://github.com/jannikmi/timezonefinder/commit/ed54d346e509d33850542929b19feef375293ff3"
        },
        "date": 1786251782319,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "memory::TimezoneFinderL::init_heap",
            "value": 4.466736793518066,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 3.2415 GHz"
          },
          {
            "name": "memory::TimezoneFinderL::steady_heap",
            "value": 4.466899871826172,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 3.2415 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::init_heap",
            "value": 4.529223442077637,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 3.2415 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::steady_heap",
            "value": 4.537896156311035,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 3.2415 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::init_heap",
            "value": 67.84990692138672,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 3.2415 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::steady_heap",
            "value": 67.85876846313477,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 3.2415 GHz"
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
          "id": "d34404e7ce9e59377f42cc3ee69ed730cc8dcc3b",
          "message": "Make the docs landing page state what the package does (#487)\n\ndocs/index.rst is the second front door - the docs badge, the PyPI project\nlinks and search results all land there - but carried three sentences and a\nflat 17-entry table of contents in which Architecture sat between Memory\nBenchmarks and Data Format. Nothing on it said how a lookup works or what\nthe package trades away to be accurate.\n\nIt now carries the same \"How it works\" summary as the README, adapted to use\n:doc: roles where the README needs absolute URLs, plus the no-simplification\ntrade-off and the ocean-zone consequence for timezone_at() - the single most\ncommon source of user confusion, which until now appeared only in the README\nand the architecture page.\n\nThe toctree is split into four captioned groups (Using it, Design,\nPerformance, Project). All 17 entries are preserved, each in exactly one\ngroup, so Sphinx warns about neither an orphaned document nor a duplicate\nentry.\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-10T04:56:49+02:00",
          "tree_id": "6e1f3ff865ead2c5b1519d53121a626793a6ab00",
          "url": "https://github.com/jannikmi/timezonefinder/commit/d34404e7ce9e59377f42cc3ee69ed730cc8dcc3b"
        },
        "date": 1786330687255,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "memory::TimezoneFinderL::init_heap",
            "value": 4.466736793518066,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 3.2435 GHz"
          },
          {
            "name": "memory::TimezoneFinderL::steady_heap",
            "value": 4.466899871826172,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 3.2435 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::init_heap",
            "value": 4.529223442077637,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 3.2435 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::steady_heap",
            "value": 4.537968635559082,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 3.2435 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::init_heap",
            "value": 67.8498592376709,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 3.2435 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::steady_heap",
            "value": 67.85863018035889,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 3.2435 GHz"
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
          "id": "efd04e929b6de9159c7959c46d5fd4bfe4ca7f6a",
          "message": "Show the timezone the shipped data actually returns (#491)\n\nEvery usage snippet in README.rst and docs/1_usage.rst queries the Berlin\ncoordinates lng=13.358, lat=52.5061 and annotated the answer as\n'Europe/Paris'. That is what the reduced timezones-now dataset returns,\nwhere Europe/Berlin is merged into Europe/Paris. The package ships the\nfull dataset by default, which returns 'Europe/Berlin', so all eleven\ncomments described a dataset the reader does not have.\n\nEach annotation was re-derived by running the call it sits on rather than\nby find-and-replace: the global and instance forms of timezone_at,\ntimezone_at_land, certain_timezone_at and unique_timezone_at, plus the two\nTimezoneFinderL snippets. The neighbouring 'Etc/GMT' and None annotations\nwere confirmed correct and left alone. The get_geometry example in the\nopening block now asks for Europe/Berlin too - Europe/Paris was a valid\ncall, but read as though it followed from the lookup above it.\n\nNothing tied those comments to the packaged data, which is how they stayed\nwrong across releases. test_documented_contracts.py now re-runs each\ndocumented lookup against the example coordinate, one case per lookup,\nsince only unique_timezone_at can start returning None without any of the\nothers changing.\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-10T05:12:20+02:00",
          "tree_id": "e4f3e0d98a6039b34a02089b6ffbb67eeb31b361",
          "url": "https://github.com/jannikmi/timezonefinder/commit/efd04e929b6de9159c7959c46d5fd4bfe4ca7f6a"
        },
        "date": 1786331629952,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "memory::TimezoneFinderL::init_heap",
            "value": 4.4666948318481445,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 2.4454 GHz"
          },
          {
            "name": "memory::TimezoneFinderL::steady_heap",
            "value": 4.46685791015625,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 2.4454 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::init_heap",
            "value": 4.528868675231934,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 2.4454 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::steady_heap",
            "value": 4.537759780883789,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 2.4454 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::init_heap",
            "value": 67.84999656677246,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 2.4454 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::steady_heap",
            "value": 67.85872459411621,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 2.4454 GHz"
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
          "id": "4578be790822b7f7b7730a79c1391dfe5e8fd085",
          "message": "Build test distributions for the interpreter running the tests (#494)\n\n`uv build` was invoked without `--python`, so it targeted the newest\ninterpreter on the machine, while tests/test_integration.py creates its\nthrowaway venv from `sys.executable`. On a checkout whose `.venv` is older\nthan the newest installed Python the two disagree: `make testint` built a\ncp314 wheel and `test_install_from_artifacts[wheel]` died on pip's \"not a\nsupported wheel on this platform\", nowhere near the build that caused it.\n\nEvery tox environment offers a single interpreter, so the two agreed by\naccident in CI and this only ever hit developer machines, where the\nworkaround was pinning UV_PYTHON.\n\nPin the shared build command to `sys.executable` instead of teaching\nsetup_venv to guess which interpreter uv would have chosen - the target venv\nis the thing under test, so it is the build that should follow it. The sdist\nbuild takes the same pin: it carries no interpreter tag, but it keeps the two\nartefacts in dist/ from coming out of different interpreters.\n\ntest_build_commands_pin_the_running_interpreter guards the pin. It needs no\nbuild and so carries the `unit` marker, which matters because no CI\nenvironment can reproduce the mismatch - without it the next regression would\ngo unnoticed the same way.\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-10T05:46:41+02:00",
          "tree_id": "0d92c9940338e24d2a609c1ff776ff07ed5d1480",
          "url": "https://github.com/jannikmi/timezonefinder/commit/4578be790822b7f7b7730a79c1391dfe5e8fd085"
        },
        "date": 1786333679301,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "memory::TimezoneFinderL::init_heap",
            "value": 4.466689109802246,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on INTEL(R) XEON(R) PLATINUM 8573C @ 3.0739 GHz"
          },
          {
            "name": "memory::TimezoneFinderL::steady_heap",
            "value": 4.466852188110352,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on INTEL(R) XEON(R) PLATINUM 8573C @ 3.0739 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::init_heap",
            "value": 4.529180526733398,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on INTEL(R) XEON(R) PLATINUM 8573C @ 3.0739 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::steady_heap",
            "value": 4.537940979003906,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on INTEL(R) XEON(R) PLATINUM 8573C @ 3.0739 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::init_heap",
            "value": 67.84995365142822,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on INTEL(R) XEON(R) PLATINUM 8573C @ 3.0739 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::steady_heap",
            "value": 67.85877132415771,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on INTEL(R) XEON(R) PLATINUM 8573C @ 3.0739 GHz"
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
          "id": "5a00273c87c2ef48bbbe800b6489c04f19deff8d",
          "message": "Land the documentation visibility stack on master (#495)\n\n* Document how the package is tested and shipped (#488)\n\nSearching docs/, README.rst and CONTRIBUTING.md for abi3, cibuildwheel,\nmusllinux or manylinux returned nothing outside a single acknowledgement\nline: the release pipeline existed only as workflow YAML. The property-based\ntests and the tox matrix were likewise mentioned nowhere outside the\nchangelog.\n\narchitecture.rst gains a \"How it ships\" section covering the choices and the\nreason each was made - one abi3 wheel per target instead of one per Python\nversion, with abi3audit --strict guarding a claim whose failure mode is a\nruntime crash on an interpreter CI never ran; three libc targets so an Alpine\ncontainer still gets the compiled path; an end-to-end job that installs the\nbuilt wheel on four interpreters and asserts clang_extension_loaded, because\nan import-only smoke test passes on a wheel whose extension silently failed\nto build; a tag from outside master aborting the release; and the weekly data\npipeline that regenerates, opens a PR and tags on green.\n\nThe testing section gains the property-based suite and the tox matrix, plus\nthe reason the matrix is a matrix: the acceleration paths are bound at import\ntime, so a passing run describes one configuration only. It also states why\nthe correctness sampler is pole-biased and cross-references\nbenchmarking_methodology, where the opposite choice is made - previously only\none half of that contrast appeared on each page.\n\nBoth sections land on an existing page, so there is no new toctree entry and\nno orphan risk. The two new README bullets use absolute URLs; their anchor\nslugs were read out of the built architecture.html rather than guessed, and\nthe rendered README was checked with readme-renderer.\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>\n\n* Stop answering docs questions by naming a file to go open (#489)\n\nThe three hand-written pages a docs visitor reads first were the only prose\nin docs/ that read as unmaintained.\n\n7_performance.rst is what the README calls \"benchmark reports\", but it opened\nwith a vendor-style bullet list about the binary format (\"Zero-Copy Access\",\n\"Optimized Data Layout\") that said nothing data_format.rst does not say\nproperly. That list is gone and the Benchmark Results section moves to the\ntop, so a reader lands on the four reports and the trend chart. The C\nextension and Numba sections are cut to what a user acts on - the call that\nreports the active backend - and defer the explanation to architecture.rst,\nwhich already carried a more precise version of the same material; a\nduplicated explanation that has drifted once will drift again, and here the\nduplicate was the worse copy.\n\nBoth referenced anchors survive: `.. _performance:` (0_getting_started.rst,\n3_about.rst) and `.. _speed-tests:` (1_usage.rst, data_format.rst). Verified\nagainst the built HTML - every inbound href=\"7_performance.html#...\" resolves\nto an id that exists.\n\n0_getting_started.rst answered \"Dependencies\" with \"please confer to the\npyproject.toml\". It now names the four runtime dependencies and what each\none carries, and says why the list is short and why numba is an extra rather\nthan a dependency, keeping pyproject.toml as the authoritative source for\nversion ranges so the page cannot go stale on a bound. Both \":ref:`HERE`\"\nlinks get descriptive text.\n\n2_use_cases.rst answered two of its four use cases with \"check out the\nexample script\". Each now has a runnable snippet, with the example script as\nthe follow-up. The snippets use the standard library's zoneinfo rather than\npytz, so neither requires an optional dependency; the pytz example scripts\nare still named for users already on pytz. Nothing under examples/ is\ntouched - tests/test_example_scripts.py executes those.\n\nEvery coordinate/zone pair in the new snippets was verified with an actual\nlookup rather than assumed.\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>\n\n* Say what the two root-level artifacts are (#490)\n\n* Say what the two root-level artifacts are\n\nBoth are read wrong by someone skimming the repository root.\n\npotential-improvements.md is a triaged register of internal quality debt,\nranked by expected value per line of review, with the judgement recorded for\nevery entry including the ones judged not worth doing. Its first paragraph\nopened on the machinery instead - how an automated pass consumes the file and\nwrites it back - so a reader met tooling exhaust rather than the triage. The\nheader now leads with what the file is and what the ranking rule is, states\nthat the findings are internal quality with the Behaviour defects section as\nthe one deliberate exception, and moves the maintenance mechanics to the end\nunder its own subheading. No entry changes.\n\nThe file stays at the repository root. docs/ is a Sphinx source tree with\nsource_suffix = \".rst\", so a .md placed there is invisible to the build\nrather than a documented page, and MANIFEST.in plus thirteen references in\n.claude/skills/code-quality-pass/SKILL.md all name the current path.\n\nprototypes/ had three scripts and no index, one of which is the study that\nchose H3 resolution 3 - the central algorithmic parameter of the package,\nalready cited from docs/data_format.rst. prototypes/README.md now states what\nthe directory is (exploratory studies behind committed decisions, run by\nhand, outside the package and the test suite) and what each script\nestablished, including the hierarchical-index idea that was measured and\ndropped.\n\ncheck-manifest failed on the new file as expected, since MANIFEST.in excluded\nonly prototypes/*.py from the sdist. The exclude is broadened to the whole\ndirectory rather than adding an ignore, since nothing in prototypes/ belongs\nin a distribution.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Record what the new documentation can go stale against\n\nThe preceding four commits added prose that paraphrases files elsewhere in\nthe repo, and duplicated the lookup summary across two front doors on\npurpose. Each of those is a place where the source changes and nothing\nre-reads the prose, so the discipline has to be written down where it is read\nbefore the edit rather than discovered after it.\n\nCLAUDE.md, Documentation Files - amended in place rather than opened as a new\nsection:\n\n- the badge-block bullet now covers both deliberate duplications, naming the\n  three files the How it works summary lives in and what kind of change has to\n  land in all of them\n- README.rst now deep-links into docs/ by anchor, and Sphinx derives an anchor\n  from the heading text. Renaming a heading breaks those links silently: the\n  page still loads at the top, rstcheck does not resolve targets and make docs\n  does not know README.rst exists. Says what to grep, and to read a new slug\n  out of the built HTML rather than deriving it\n- a zone name in a snippet is example output, not a constant - with how the\n  reduced timezones-now answer for Berlin came to annotate the default\n  dataset's running example\n- the three prose/source pairs that now exist: the dependency list against\n  pyproject.toml, How it ships against build.yml and the cibuildwheel config,\n  prototypes/README.md against its directory\n- the toctree bullet names the four captioned groups and the exactly-one rule\n\nCONTRIBUTING.md gets the reverse index instead: a changed-this / re-read-that\ntable for contributors, which is the direction a human needs it in, pointing\nat CLAUDE.md for what each one breaks rather than restating it.\n\nAlso corrects the PR checklist, which asked for a rebase onto `main`; this\nrepository's default branch is `master`.\n\nNo changelog entry - CLAUDE.md explicitly exempts edits confined to itself and\nCONTRIBUTING.md.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n---------\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>\n\n---------\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-10T05:50:27+02:00",
          "tree_id": "72053eccc52a497a421423c919e9c2e419ae12f3",
          "url": "https://github.com/jannikmi/timezonefinder/commit/5a00273c87c2ef48bbbe800b6489c04f19deff8d"
        },
        "date": 1786333902867,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "memory::TimezoneFinderL::init_heap",
            "value": 4.466680526733398,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 3.2450 GHz"
          },
          {
            "name": "memory::TimezoneFinderL::steady_heap",
            "value": 4.466843605041504,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 3.2450 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::init_heap",
            "value": 4.529123306274414,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 3.2450 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::steady_heap",
            "value": 4.5380096435546875,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 3.2450 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::init_heap",
            "value": 67.84995079040527,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 3.2450 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::steady_heap",
            "value": 67.85868072509766,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 3.2450 GHz"
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
          "id": "a69f03ca1d926c51ebf972349144b7aa37bee440",
          "message": "Verify MANIFEST.in exclusions the other way round too (#493)\n\n* Verify MANIFEST.in exclusions the other way round too\n\nThe packaging guard asserts that nothing in the built sdist and wheel\nmatches a pattern in IGNORED_PATTERNS, and #486 made every hand-written\npattern name a path that actually exists. That closed one direction: a\npattern matching nothing now fails.\n\nThe converse stayed silent. MANIFEST.in and the pattern set are two\nhand-maintained statements of one intent, so an exclude/recursive-exclude/\nprune line added without a matching pattern left the file kept out by the\nbuild and verified by nothing - deleting that line later would ship it\nwith the suite still green.\n\ntest_every_manifest_exclusion_is_guarded parses the exclusion directives\nout of MANIFEST.in and fails when one of them covers a path in the\ncheckout that no pattern names. The four directive forms collapse into\none shape (prefix, glob, anchored), and the glob is matched a component\nat a time so `*` does not cross a separator, as it does not in\nMANIFEST.in but does in matches_pattern.\n\nFour directives name untracked artefacts whose presence is a property of\nthe machine rather than of the project - `.git` is a directory in a clone\nand a file in a linked worktree, numba's cache under\ntimezonefinder/__pycache__/ appears only after a numba-enabled run - so\nscanning them would pass here and fail elsewhere. Those are exempted\nagainst the pattern that carries the same intent, and\ntest_pattern_only_exclusions_stay_current fails if either side goes away.\nNeither global-exclude is load-bearing: dropping either changes neither\ndistribution, since setuptools already prunes __pycache__ from an sdist.\n\nBoth tests are unit tests - they need no build, so a drifted exclusion\nsurfaces in `make test`.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* List the packaging guard among the invariant-protecting tests\n\ndocs/architecture.rst's \"Tests that protect guarantees, not behaviour\"\ncollects the tests that exist to give an invariant a failure mode it\npreviously lacked. The packaging guard belongs there and was missing: a\ncheck that asserts nothing matched passes just as readily when its\npatterns match nothing at all, which is exactly how `.github` and\n`Agents.*` came to guard nothing while the suite stayed green.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Say what stops the wrong files reaching PyPI in How it ships\n\nThe section covers the checks that stop a broken wheel being published -\nthe abi3 audit, the end-to-end install job - but not the one that checks\nwhat is *in* the artifact. Both halves of that check are worth stating:\na missing runtime file fails on first use and gets reported, while an\nextra one ships quietly.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n---------\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-10T06:11:31+02:00",
          "tree_id": "0b67cf5e76359741e33278057c55f5e35fe55adf",
          "url": "https://github.com/jannikmi/timezonefinder/commit/a69f03ca1d926c51ebf972349144b7aa37bee440"
        },
        "date": 1786335177383,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "memory::TimezoneFinderL::init_heap",
            "value": 4.466645240783691,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on Intel(R) Xeon(R) 6973P-C @ 2.6000 GHz"
          },
          {
            "name": "memory::TimezoneFinderL::steady_heap",
            "value": 4.466808319091797,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on Intel(R) Xeon(R) 6973P-C @ 2.6000 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::init_heap",
            "value": 4.529265403747559,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on Intel(R) Xeon(R) 6973P-C @ 2.6000 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::steady_heap",
            "value": 4.537899971008301,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on Intel(R) Xeon(R) 6973P-C @ 2.6000 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::init_heap",
            "value": 67.84997940063477,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on Intel(R) Xeon(R) 6973P-C @ 2.6000 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::steady_heap",
            "value": 67.8587007522583,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on Intel(R) Xeon(R) 6973P-C @ 2.6000 GHz"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "49699333+dependabot[bot]@users.noreply.github.com",
            "name": "dependabot[bot]",
            "username": "dependabot[bot]"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "a32de1afbbd2d3a1a5d222e9de85f6cb405fc965",
          "message": "Bump pypa/cibuildwheel from 4.1.1 to 4.2.0 (#496)",
          "timestamp": "2026-08-10T14:10:37+02:00",
          "tree_id": "9b3748053d4689d2d00d5e68aaaedd6abdca15ca",
          "url": "https://github.com/jannikmi/timezonefinder/commit/a32de1afbbd2d3a1a5d222e9de85f6cb405fc965"
        },
        "date": 1786363925308,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "memory::TimezoneFinderL::init_heap",
            "value": 4.466680526733398,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V45 96-Core Processor @ 4.2919 GHz"
          },
          {
            "name": "memory::TimezoneFinderL::steady_heap",
            "value": 4.466843605041504,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V45 96-Core Processor @ 4.2919 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::init_heap",
            "value": 4.528999328613281,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V45 96-Core Processor @ 4.2919 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::steady_heap",
            "value": 4.537803649902344,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V45 96-Core Processor @ 4.2919 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::init_heap",
            "value": 67.85012531280518,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V45 96-Core Processor @ 4.2919 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::steady_heap",
            "value": 67.85889530181885,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V45 96-Core Processor @ 4.2919 GHz"
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
          "id": "9e3ac2c272dcc1a24c306b18e77e522cfcd7e0d6",
          "message": "make names and docstrings describe what the code does (#507)\n\nShips three ledger entries (TEST-6, TEST-8, TEST-10) plus one finding from a\nwide-angle review, all on one theme: code whose name or docstring contradicts\nwhat it does. No behaviour change.\n\n- TimezoneFinder.timezone_at documents that the last remaining zone is returned\n  without a point in polygon test, and that this is correct only where the data\n  covers every point - certain_timezone_at is the method that tests every\n  candidate. The optimisation was explained in comments but not where\n  help(TimezoneFinder) and the API page show it.\n- test_rectify_coords_valid/_invalid were named for a rectify_coords that does\n  not exist; both call validate_coordinates. The first is deleted as subsumed by\n  test_validate_coordinates_accepts_finite_values, which covers all four of its\n  distinct corners and asserts the return value; the second is renamed\n  test_validate_coordinates_rejects_out_of_range.\n- test_single_element_arrays_should_not_occur asserted that they do occur. Its\n  triple-quoted string sat after the first statement, so it was a discarded\n  expression rather than a docstring and reached neither --collect-only nor a\n  failure report - leaving the contradicting name as the only thing a reader saw.\n  Renamed test_single_element_arrays_round_trip, string moved above the body.\n- Dropped a stale comment duplicated across the last two lines of main_test.py,\n  reading as a to-do for what TestTimezonefinderClassTestMEM already does.\n\nLedger: TEST-6/8/10 deleted as shipped; TEST-9's anchor updated for the rename.\nAdds API-2 (every submodule reachable as a package attribute, so the public API\nis wider than __all__ says) and PERF-1 (is_ocean_timezone runs a regex on the\ntimezone_at_land path), both open and both blocked - one on a maintainer\ndecision, one on a measurement. A scope note now points structural work at the\nroadmap (#506) and states the test for what belongs in the ledger at all.\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-13T03:16:45+02:00",
          "tree_id": "bd97e60b0cfabb9979b72646b1b64235a1add4f9",
          "url": "https://github.com/jannikmi/timezonefinder/commit/9e3ac2c272dcc1a24c306b18e77e522cfcd7e0d6"
        },
        "date": 1786583890293,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "memory::TimezoneFinderL::init_heap",
            "value": 4.466647148132324,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 2.4454 GHz"
          },
          {
            "name": "memory::TimezoneFinderL::steady_heap",
            "value": 4.46681022644043,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 2.4454 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::init_heap",
            "value": 4.529213905334473,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 2.4454 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::steady_heap",
            "value": 4.538060188293457,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 2.4454 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::init_heap",
            "value": 67.85003471374512,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 2.4454 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::steady_heap",
            "value": 67.85881233215332,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 2.4454 GHz"
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
          "id": "3c4253bd19a412d884b0b1012983b9f91ecdb857",
          "message": "Add roadmap-pass agent skill for advancing issue #506 (#508)\n\n* Add roadmap-pass agent skill for advancing issue #506\n\nAdvances the structural work tracked by roadmap issue #506 one pass at a\ntime: select an eligible item, check the sequencing preconditions #506\nrecords, put the item's open design decisions to the maintainer as\nconcrete choices, and only then implement one releasable slice.\n\nUnlike its code-quality-pass sibling it deliberately asks rather than\ndeciding alone, because a roadmap item's design choices outlive the pass.\nState is derived from the tracker rather than a progress file, so repeated\nand concurrent passes are idempotent.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Quote the skill description so YAML keeps all of it\n\nAn unquoted `#` preceded by a space starts a comment in a plain YAML\nscalar, so the roadmap-pass description was stored as \"Advances the\nstructural work tracked by roadmap issue\" - 53 of 831 characters, with\nevery trigger phrase discarded. The skill still loaded; it just stopped\nbeing discoverable by anything but its name.\n\ntests/test_agent_skills.py parses the frontmatter of every skill under\n.claude/skills/ and fails when the value a YAML parser stores ends before\nthe value the file writes.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n---------\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-13T12:12:48+02:00",
          "tree_id": "a565630af02e262ec724dd7f8b3ee41f8969414e",
          "url": "https://github.com/jannikmi/timezonefinder/commit/3c4253bd19a412d884b0b1012983b9f91ecdb857"
        },
        "date": 1786616046127,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "memory::TimezoneFinderL::init_heap",
            "value": 4.4665985107421875,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.8713 GHz"
          },
          {
            "name": "memory::TimezoneFinderL::steady_heap",
            "value": 4.466761589050293,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.8713 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::init_heap",
            "value": 4.529223442077637,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.8713 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::steady_heap",
            "value": 4.537895202636719,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.8713 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::init_heap",
            "value": 67.8500165939331,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.8713 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::steady_heap",
            "value": 67.85883331298828,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.8713 GHz"
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
          "id": "8f59f5e5ac0a89596365280315fd30e6290820c1",
          "message": "Stop two tests leaking numpy's global state, and give three silent drifts a failure mode (#511)\n\n* TEST-4: stop two tests leaking numpy's global error state\n\n`np.seterr` and the warning filters are process-global. `test_overflow`\n(tests/main_test.py) and `test_inside_polygon` (tests/utils_test.py, six\nparametrisations) each set them and never restored them, so every test\ncollected afterwards ran with `under` promoted from `ignore` to `warn` -\nand which module pytest collected first decided the state the other ran\nunder. The filters were undone only incidentally, by pytest's per-test\n`catch_warnings()`, not by the tests themselves.\n\nbenchmarks/conftest.py already had the correct pattern. Split it into a\n`strict_numpy_errors` context manager plus the thin `strict_numpy_warnings`\nfixture, both in tests/auxiliaries.py where the other shared helpers live,\nre-exported through the conftest of each suite. Both call sites now request\nthe fixture. The context manager form is what makes the seam directly\ntestable: two tests assert the promotion and the restore, the latter against\na deliberately distinct starting state so it cannot pass by coincidence.\n\n* DEAD-3: drop the negative-zone-id guard the dtype check makes unreachable\n\n`ZoneCollection.validate_structure` rejects any `poly_zone_ids` whose\n`dtype.kind != \"u\"` a dozen lines before taking `.min()`, so the array is\nunsigned by then and `if min_zone_id < 0` cannot fire. Left in, it reads as\nthe guard against negative zone ids - which matters because the real\nnegative-id exposure is elsewhere and still open (`zone_id_of` /\n`zone_name_from_id` index directly, BUG-1 in the ledger).\n\nThe validators had no tests at all, so what the class actually promises is now\npinned: the unsigned-dtype rejection that makes a negative id unrepresentable,\nthe ordering and max-id rules, and the shape zone_positions() returns.\n\n* DUP-3: enforce the zone-id ordering rule in one place\n\n`validate_structure` and `zone_positions` each walked `poly_zone_ids`\nelement by element checking it was non-decreasing, and each raised the same\nmessage built from its own locals - two places to edit if the rule changes,\nand two Python-level passes over every polygon during data generation.\n\nThe validator's scan moves into `_validate_non_decreasing`, beside the other\nmodule-level `_validate_*` helpers. `zone_positions` drops its copy: the\nvalidator is a pydantic `model_validator(mode=\"after\")`, so it runs at\nconstruction, and `poly_zone_ids` is only ever read afterwards - the copy\ncould fire only if a caller mutated the array in place, which nothing does.\nIts docstring now says what it is entitled to assume.\n\n* TEST-9: declare the out-of-range coordinate table once\n\nThe same seven (lng, lat) tuples - each one representable step outside the\nvalid WGS84 range - were written out verbatim in tests/main_test.py and again\nin the parametrize list of tests/utils_test.py, and only the first copy\ncarried the comment explaining what makes them interesting. Adding a corner\nto one left the other testing a smaller set, with nothing to notice.\n\nThe table moves to tests/locations.py, which already holds the shared\ncoordinate tables, and both modules import it. Collection count is unchanged\nat 551 across the two modules.\n\n* TYPE-1: annotate the shortcut compilation chain for what it is actually passed\n\nBoth annotations in the chain were the wrong way round.\n`check_shortcut_sorting(polygon_ids: np.ndarray, ...)` is only ever called by\n`process_single_hex` with the `list[int]` that `optimise_shortcut_ordering`\nreturns, and it in turn passes the `np.ndarray` produced by `all_zone_ids[\npolygon_ids]` to `has_coherent_sequences(lst: list[int])`.\n\nWidened rather than swapped: tests/shortcut_test.py calls\n`has_coherent_sequences` with real lists, so both forms are live. Also gives\n`check_shortcut_sorting` the `-> None` its siblings have. mypy reports the\nsame four pre-existing errors on this file as before (scripts/ is outside the\npre-commit mypy hook's scope).\n\n* CI-1: fail when the five declarations of the supported Python versions drift\n\npyproject.toml (requires-python plus one classifier per minor version),\ntox.ini (the py{...} envlist factors), build.yml (the test matrix and\nCIBW_BUILD_VERSIONS) and setup.py (py_limited_api) all state the same fact and\nnone can read the others. Two \"must match\" comments already said so and\nnothing enforced them.\n\nThe failure is silent in both directions: a classifier added without a matrix\nentry ships a version the package claims and CI never runs, and a\nrequires-python raised without the abi3 base moved builds wheels tagged for an\ninterpreter no longer supported.\n\nFive assertions, each verified to fail against the specific one-sided edit it\ntargets. Both existing comments now name the test. Same shape and reasoning as\ntests/test_benchmark_workflows.py.\n\n* Record this quality pass in the changelog\n\n* Record pass 7 in the findings ledger\n\nDeleted as shipped: TEST-4, TEST-9, DEAD-3, DUP-3, TYPE-1. Deleted as fixed\nby unrelated work: TEST-7 (the wheel/venv interpreter mismatch, closed by\nPR #494 pinning `uv build --python sys.executable`).\n\nAdded DEAD-4 (an unreachable None guard in `Hex.poly_candidates`) and REND-4\n(three cosmetic leftovers in scripts/reporting.py). Coverage log gains pass 7;\n.github/workflows/ is no longer an unswept area, leaving only docs/ prose.",
          "timestamp": "2026-08-14T07:12:18+02:00",
          "tree_id": "04c11d0d7f692961b0ba808524358524af99181f",
          "url": "https://github.com/jannikmi/timezonefinder/commit/8f59f5e5ac0a89596365280315fd30e6290820c1"
        },
        "date": 1786684427108,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "memory::TimezoneFinderL::init_heap",
            "value": 4.466689109802246,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on INTEL(R) XEON(R) PLATINUM 8573C @ 3.5428 GHz"
          },
          {
            "name": "memory::TimezoneFinderL::steady_heap",
            "value": 4.466852188110352,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on INTEL(R) XEON(R) PLATINUM 8573C @ 3.5428 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::init_heap",
            "value": 4.529267311096191,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on INTEL(R) XEON(R) PLATINUM 8573C @ 3.5428 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::steady_heap",
            "value": 4.538006782531738,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on INTEL(R) XEON(R) PLATINUM 8573C @ 3.5428 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::init_heap",
            "value": 67.84986782073975,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on INTEL(R) XEON(R) PLATINUM 8573C @ 3.5428 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::steady_heap",
            "value": 67.8586368560791,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on INTEL(R) XEON(R) PLATINUM 8573C @ 3.5428 GHz"
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
          "id": "8ceae1d6262131895b0055180fe95a0a14e6bdfe",
          "message": "Add a cut-release skill, and give the quality pass a diff budget (#512)\n\n* Make the quality pass work its ranking down to a diff budget\n\nThe pass took one coherent theme and stopped; it now takes the ledger's\nhighest-priority findings one at a time until ~400 changed lines are spent,\nso the ranking rather than a common story is what holds the PR together.\nEach item lands as its own commit naming its ledger entry, the budget is\nmeasured against the merge base with the ledger excluded and checked between\nitems rather than mid-item, and a ranking that runs dry ends the pass as\nlegitimately as a spent budget. The branch claim in §2.1 follows: it claims\nonly what it already holds, so a pass re-pushes after every finished item.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Add a cut-release skill that proposes the bump and stops\n\nTurns the accumulated `X.X.X (unreleased)` changelog section into a released\nversion, in two halves split by the maintainer's merge. Prepare checks the\nsection is release-ready and complete against every commit since the last tag,\nproposes patch/minor/major as three concrete version numbers with the bullets\nbehind each, stops for the decision, then lands the bump as a release PR. Tag\nruns only after that PR is merged and asks again, since the tag is the publish\nand PyPI will not let a version take it back.\n\nRecords what the pipeline makes non-obvious: the tag-push run re-reads\npyproject.toml at the tagged commit; the release commit is the bump and the\nchangelog and nothing else, so `make reports` must not run in it; and the tag\nhas to be pushed promptly after the merge, because the master push run's own\nrelease job creates the GitHub Release and with it the tag, after which\npushing that tag is a no-op that fires no webhook.\n\nCLAUDE.md's claim that regenerating data warrants a minor bump is corrected:\nupdate_data.sh bumps patch and the last four data releases were patches.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n---------\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-14T07:22:26+02:00",
          "tree_id": "ec4e3362dff760a796f4bf4facd476336473ca75",
          "url": "https://github.com/jannikmi/timezonefinder/commit/8ceae1d6262131895b0055180fe95a0a14e6bdfe"
        },
        "date": 1786685020577,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "memory::TimezoneFinderL::init_heap",
            "value": 4.466736793518066,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 3.2540 GHz"
          },
          {
            "name": "memory::TimezoneFinderL::steady_heap",
            "value": 4.466899871826172,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 3.2540 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::init_heap",
            "value": 4.529167175292969,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 3.2540 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::steady_heap",
            "value": 4.537881851196289,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 3.2540 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::init_heap",
            "value": 67.85004138946533,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 3.2540 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::steady_heap",
            "value": 67.85880374908447,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 3.2540 GHz"
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
          "id": "4f6da3f39e30939ceb6079a1049efab0e7f0d36a",
          "message": "Store holes that duplicate a boundary polygon as a reference (#509)\n\n* store holes that duplicate a boundary polygon as a reference\n\nAlmost every hole is an enclave: the upstream builder cuts it into the\nsurrounding zone using exactly the ring it also emits as the enclosed\nzone's own boundary polygon. Measured against release 2026c, 729 of 756\nhole rings trace the same closed path as some boundary polygon - the\nsame geometry stored under two IDs.\n\nThe hole coordinate file now holds only the 27 rings without a twin, and\nholes/poly_ref.npy records per hole id which boundary polygon to read\ninstead (v >= 0), or where its own ring sits (v < 0, at -(v + 1)). Hole\nids stay dense, so the hole registry and every caller above coords_of()\nis untouched, and the bbox vectors stay valid verbatim - a referenced\nring is identical, so its bbox already equals the boundary's. The bbox\nrejection test keeps reading a flat array with no indirection.\n\nHole data drops from ~2.0 MiB to ~0.16 MiB, on disk and in RAM alike.\n\nMatching compares integer coordinates in a canonical form (rotated to\nthe lexicographically smallest vertex, both winding directions tried),\nwith bbox and vertex count as a prefilter only - no tolerance, so two\nrings either trace the same path or they do not. Verified equivalent to\nthe all-inline data over both point-in-polygon backends, including every\nvertex and edge midpoint of the rings whose stored form changed.\n\nPOLYGON_LAYOUT_VERSION becomes 2 so a released version rejects this data\ninstead of resolving hole ids against the compacted file and returning\nplausible wrong answers; layout 1 stays readable, so a bin_file_location\ndirectory compiled by an older release still works.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* record the broken parse targets, and replace a test that could not fail\n\ntest_packaged_references_resolve_to_the_same_ring compared\nholes.coords_of(id) against boundaries.coords_of(ref), but resolving a\nreference *is* returning the boundary ring, so it asserted an expression\nagainst itself. Removed rather than repaired: the property it was\nreaching for is decided at build time, and on packaged data the bbox\nvectors are the only independent evidence - they are computed from the\noriginal hole rings before deduplication and never rewritten, so a\nreference pointing at the wrong polygon resolves to a ring whose extent\ndisagrees. Mutation-checked: an off-by-one in one reference fails it.\n\nAdded test_packaged_dedup_ratio_meets_the_floor, so the shipped data is\nheld to the bar the converter enforces even when the converter did not\nproduce it.\n\npotential-improvements.md gains TOOL-3: `make parse` and `make testparse`\nboth fail immediately with ModuleNotFoundError on master, since they\ninvoke the converter by path and its own `from scripts...` imports\ncannot resolve.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* move hole data integrity off the runtime path\n\nHoleArray._validate_refs ran on every construction, re-deriving in each\nuser's process something the build had already established - and paying\nfor it on an init path that latency-sensitive services carry per thread.\n\nThe checks now live in scripts/data_integrity.py and run in the two\nplaces where they mean something: the converter, over the files it just\nwrote, and the test suite, over the files the repository ships. One\nimplementation, so the two cannot drift into asserting different things.\n\nOff the init path the check can afford to be thorough rather than cheap,\nso it now does what the runtime version could not: resolve every hole\nring and compare its extent against the bounding box stored for that\nhole. Those bboxes are computed from the original rings before\ndeduplication and never rewritten, which makes them evidence independent\nof the references - a reference pointing at the wrong polygon resolves\nto a real, valid ring and is caught only here.\n\nThe deduplication ratio floor is split into its own check: it is a claim\nabout the upstream dataset, not about file consistency, and a small\ncustom region can legitimately have few enclaves while being perfectly\nwell formed.\n\nCLAUDE.md and CONTRIBUTING.md record the general rule, since the\ntempting version of this - a defensive check at load time - is both\nslower and, being forced to stay cheap, shallower.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* do not refuse to compile custom data with few enclave-shaped holes\n\nThe deduplication floor aborted the converter for any dataset below it,\nbut scripts/file_converter.py is documented for \"any other data in this\nformat\" (docs/2_use_cases.rst), and a dataset whose holes are ordinary\ninterior rings rather than enclaves is perfectly valid: those rings take\nthe inline path and answer correctly, the output is merely larger. Such\na user got an abort quoting \"the upstream dataset\", which is not their\ndataset, for data the fallback would have compiled correctly.\n\nThe floor is a claim about the packaged dataset specifically - the same\nreason validate_hole_dedup_ratio is already separate from the structural\ncheck - so it is enforced there and only there, by the test suite over\nthe packaged binaries. A real upstream regression still blocks the\nweekly data-update PR, which merges only once CI passes. The converter\nnow reports the ratio instead, naming both readings of a low value.\n\nReported by Codex review on #509.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* keep one polygon layout version instead of bumping it\n\nPOLYGON_LAYOUT_VERSION went to 2 so that a released version would reject\ndeduplicated hole data rather than resolve hole ids against a compacted\nfile. But layout 1 has never been released - it arrived with the\nper-axis coordinate encoding in 5947b1b, which is not an ancestor of\n8.2.5 - so no version in the wild reads or writes it, and there was\nnothing for version 2 to protect against. The same fact voids the other\nhalf of the justification: no earlier release wrote layout 1 either, so\nthe READABLE_LAYOUT_VERSIONS set was keeping open a compatibility path\nwith data that cannot exist.\n\nLayout 1 now simply describes what ships: per-axis coordinates and, for\na hole collection, only the rings that are not references. Both changes\nland in the same unreleased version, so they need one marker between\nthem, not two.\n\nThis takes boundaries/coordinates.fbs out of the diff. It had been\nrewritten for a single byte - the version stamp, at offset 22 - with all\n1322 polygons and 7,925,313 vertices identical either way. Regenerated\nfrom the pinned 2026c source; the file is now byte-identical to master\nand only the hole files change.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* require poly_ref.npy instead of falling back to inline rings\n\nThe fallback read a hole directory without poly_ref.npy as one where\nevery ring is stored inline. That was justified as compatibility with\ndata compiled by an older release - but this layout has never been\nreleased, so no such directory exists. What the branch actually covered\nwas data compiled from an intermediate master checkout, which per\nCLAUDE.md needs no compatibility.\n\nWorse, the interpretation it guessed at is unverifiable: the coordinate\nfile of a deduplicated directory holds only the inline rings, so hole\nids do not index it, and reading it that way returns wrong rings rather\nthan failing. Requiring the file means a missing one raises naming\nitself.\n\nAlso drops the `is None` branch from coords_of, which ran per hole\npoint-in-polygon test, and the corresponding branches from the two\nintegrity checks.\n\nThe equivalence test built its all-inline reference dataset by deleting\npoly_ref.npy; it now writes an all-negative vector instead, which is the\nsame directory expressed in the layout that ships.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* add the hole-removal experiment to prototypes/\n\nDropping holes is the obvious next step after storing them as\nreferences, and it looks safe on the coverage evidence: every hole is\nfully covered by other zones. The experiment shows it is not, and that\nis worth keeping runnable rather than describing.\n\nprototypes/hole_removal_impact.py rewrites the hole files of a mirrored\ndata directory - symlinking the rest, since the boundary coordinates\nalone are ~63 MB - and diffs timezone_at over interior points of every\nhole plus a uniform global sample. Dropping only the 27 holes with no\nboundary twin changes 160 of 6,048 hole-interior answers; dropping all\nof them changes 1,703, and 16 of 20,000 uniform points. The changes are\nwrong, not merely different: Asia/Hebron -> Asia/Jerusalem,\nAmerica/Argentina/Cordoba -> America/Asuncion.\n\nIts FINDINGS block records why the coverage argument is insufficient:\ncoverage puts the right zone among the shortcut candidates, ordering\ndecides whether it is reached first. Filed as #513.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* record the check that makes the no-internal-compatibility rule work\n\nBoth files already say internal code, data formats and binary assets\nneed no backward compatibility - CONTRIBUTING.md emphatically. The rule\nwas there and still did not prevent a fallback for \"a data directory\ncompiled by an older release\", because the step it depends on was\nunwritten: confirming that the older release exists.\n\nOn master an unreleased format marker is indistinguishable from a\nshipped one. POLYGON_LAYOUT_VERSION = 1 read as a settled fact while\nbeing unreleased, so a compatibility branch for it looked load-bearing,\nand guarding it cost a version bump that rewrote the 63 MB coordinate\nbinary for one changed byte.\n\nAmended into the existing bullets in both files rather than added as new\nguidance, so neither restates the rule it qualifies.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n---------\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-14T10:01:44+02:00",
          "tree_id": "379ac95ce1740aec9b6862bb28d85c75d7b725d5",
          "url": "https://github.com/jannikmi/timezonefinder/commit/4f6da3f39e30939ceb6079a1049efab0e7f0d36a"
        },
        "date": 1786694594892,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "memory::TimezoneFinderL::init_heap",
            "value": 4.466736793518066,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on Intel(R) Xeon(R) Platinum 8370C CPU @ 2.80GHz @ 3.3606 GHz"
          },
          {
            "name": "memory::TimezoneFinderL::steady_heap",
            "value": 4.466899871826172,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on Intel(R) Xeon(R) Platinum 8370C CPU @ 2.80GHz @ 3.3606 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::init_heap",
            "value": 4.5323076248168945,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on Intel(R) Xeon(R) Platinum 8370C CPU @ 2.80GHz @ 3.3606 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::steady_heap",
            "value": 4.541051864624023,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on Intel(R) Xeon(R) Platinum 8370C CPU @ 2.80GHz @ 3.3606 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::init_heap",
            "value": 65.69976902008057,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on Intel(R) Xeon(R) Platinum 8370C CPU @ 2.80GHz @ 3.3606 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::steady_heap",
            "value": 65.7084379196167,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on Intel(R) Xeon(R) Platinum 8370C CPU @ 2.80GHz @ 3.3606 GHz"
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
          "id": "76f63966e5d6b2a8fb933b4b8d41a3c91bc644b3",
          "message": "Make the data report generator derive its figures and describe its own types (#514)\n\n* REP-2: take the H3 cell count from h3 instead of a ladder of literals\n\n`calculate_shortcut_index_stats` derived `possible_cells` - the denominator\nof every coverage figure in docs/data_report.rst - from hard-coded constants\nfor resolutions 0 to 4, and fell through to `possible_cells = total_entries`\nfor anything else. That fallback makes `coverage_ratio` exactly 1.0, so an\nuntabulated resolution reports complete H3 coverage rather than failing.\n\nThe surrounding `except ImportError` could not fire at all: h3 is a runtime\ndependency of the package, not an optional one, and its fallback was the same\nsilent full-coverage value.\n\n`h3.get_num_cells` returns exactly the tabulated numbers (122, 842, 5882,\n41162, 288122), so the committed report regenerates byte-identically.\nThe h3 and SHORTCUT_H3_RES imports move to module level, matching every other\nmodule in scripts/ - neither guarded a cycle, and the resolution being a\nmodule attribute is what lets the new tests parametrize over it.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* BIG-2/REND-4: stop round-tripping the polygon count through its own label\n\n`print_polygon_distribution_table` built `distribution_items` as\n(count, frequency) pairs, rebound the same name to (label, frequency) by\nformatting the count into \"N polygon(s)\", then recovered the count with\n`int(category.split()[0])` to look up the example timezone. The label's\nwording was load-bearing for a lookup that had the number all along.\n\nThe function is also annotated `-> list[list[str]]` and documents a return\nvalue, while having no return statement at all; its one caller discards the\nresult. Both now say `None`.\n\nNeither changes the report: docs/data_report.rst regenerates byte-identically.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* TYPE-3/TYPE-2: make scripts/reporting.py's annotations describe its code\n\nmypy is not run over scripts/ by the pre-commit hook, and the module had\ndrifted 17 errors away from its own signatures. Running it by hand:\n\n- `calculate_shortcut_index_stats` claimed `dict[str, int | float]` while\n  returning two `list[int]` distributions, which the two `print_frequencies`\n  calls consume as lists. It and `load_binary_data`'s nine-key bag are now\n  `ShortcutIndexStats` / `BinaryData` TypedDicts in scripts/configs.py, where\n  this repo keeps its script-side types.\n- `redirect_output_to_file` declared `str` and is passed `DATA_REPORT_FILE`,\n  a Path, at all three call sites - its context-manager sibling already said\n  `str | Path`.\n- `main` was annotated `-> None` while returning 0 and 1 to `exit()`.\n- `print_rst_table` / `compute_column_widths` declared `list[list[str]]` rows\n  but render every cell through `str()`, and are handed ints and floats. They\n  take `TableRows` (a covariant Sequence, since list is invariant).\n- `generate_polygon_statistics_table`'s implicit-Optional `additional_rows`.\n- `generate_metrics_rows` took a `metric_type` its body never read; all four\n  call sites passed a label that went nowhere.\n\n`generate_metrics_rows`'s values are `Mapping[str, object]` rather than a\nnumeric type, so its non-numeric fallback stays reachable rather than being\ndeleted to satisfy an annotation.\n\nSince CI cannot check any of this, two tests assert each TypedDict's keys\nagainst the dict actually returned. docs/data_report.rst regenerates\nbyte-identically.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* REND-2/REND-4: look values up where they are declared\n\n`_memory_mode_label` spelled out \"in-memory\"/\"file-based\", which\n`PARAM_LABELS` - the module's declared display vocabulary, used by every other\nlabel - already maps from `in_memory`/`file_based`. Renaming a label there\nwould have left the comparison bullets on the old wording while the tables\nabove them moved to the new one.\n\nIn scripts/reporting.py the shortcut index's field widths were a local named\n`ENTRY_KEY_SIZE_BYTES` (so it read as a module constant while being rebound\nper call) plus two bare literals explained only by trailing comments. All\nthree are now named module constants. The median-polygons entry dropped a\n`list()` inside `sorted()`.\n\nRendering both report families against the same inputs before and after gives\nbyte-identical output.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* DEAD-1: delete five definitions nothing references\n\n- `scripts/utils.py`: `load_json`, `load_pickle` and `write_pickle`. The\n  pickle pair was the only thing keeping `import pickle` in a data-generation\n  path.\n- `timezonefinder/_numba_replacements.py`: `i8`. The shim exists to mirror the\n  numba names the package imports when numba is absent, and that import line\n  asks for `njit, boolean, Array, i4, f8` - an extra class is an unexercised\n  claim about the fallback. Verified by blocking `import numba` and taking the\n  fallback branch end to end.\n- `tests/auxiliaries.py`: `convert_to_reduced_timezone`, self-documented as\n  \"unused, but kept for future reference\", along with the commented-out call\n  in `single_location_test` and the now-unused import.\n\n`REDUCED_TIMEZONE_MAPPING` in tests/locations.py is left in place, now with no\nconsumer; it is reference data rather than code, and it goes to the ledger.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* DEAD-4: drop a guard against a None Hex._init_candidates cannot leave behind\n\n`poly_candidates` called `_init_candidates()`, re-read `_poly_candidates`,\nand returned an empty set if it were still `None`. No path through\n`_init_candidates` leaves it unset - it early-returns when already\ninitialised, assigns `set(range(nr_of_polygons))` at resolution 0, and\notherwise assigns the accumulated set - so the branch could not fire. It read\nas a guard against an uninitialised cache while meaning \"no candidate\npolygons\", which would have turned a converter bug into silently missing\nshortcuts instead of a failure.\n\n`_init_candidates` now returns the set it initialises, so the property does\nnot re-read the attribute and needs no guard. Its local accumulator was also\nannotated `HexIdSet` while holding polygon ids; both aliases are `set[int]`,\nso nothing could catch it.\n\nThe property had no direct test - it is reached only through `polys_in_cell`\nduring shortcut generation - so it gains one.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Record this quality pass in the changelog\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Record pass 8 in the findings ledger\n\nDeletes the five entries this pass shipped (DEAD-1, DEAD-4, TYPE-3, REND-2,\nREND-4) and narrows TYPE-2 to the two sites still open.\n\nCorrects BIG-2: its title claimed 13 branches / 57 statements, over ruff's\nPLR0912/PLR0915 defaults. Replacing the hard-coded H3 ladder removed six\nbranches, so it now trips neither and the entry is readability only.\n\nAdds DEAD-5 (REDUCED_TIMEZONE_MAPPING, orphaned by DEAD-1 and annotated as a\nset while being a dict), BIG-4 and TOOL-4.\n\nBoth new entries are stated as they look after rebasing onto #509, which\nlanded mid-pass: it rewrote load_binary_data through PolygonArray/HoleArray,\nso BIG-4 keeps only the hole branch that silently yields empty lists rather\nthan the size complaint it was written about. #509 also took the id TOOL-3\nfor a separate finding, so the mypy-exclusion entry is TOOL-4.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n---------\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-14T10:31:41+02:00",
          "tree_id": "44113dd2737ccb993464be784e042939f6387cea",
          "url": "https://github.com/jannikmi/timezonefinder/commit/76f63966e5d6b2a8fb933b4b8d41a3c91bc644b3"
        },
        "date": 1786696392611,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "memory::TimezoneFinderL::init_heap",
            "value": 4.466689109802246,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 2.4454 GHz"
          },
          {
            "name": "memory::TimezoneFinderL::steady_heap",
            "value": 4.466852188110352,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 2.4454 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::init_heap",
            "value": 4.532392501831055,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 2.4454 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::steady_heap",
            "value": 4.541015625,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 2.4454 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::init_heap",
            "value": 65.69977569580078,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 2.4454 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::steady_heap",
            "value": 65.70849227905273,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 2.4454 GHz"
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
          "id": "97a8e34180daced9c2efb9b0e7867db2b613169f",
          "message": "Make the file converter runnable again, and type-check the directory it lives in (#515)",
          "timestamp": "2026-08-15T08:41:03+02:00",
          "tree_id": "3c1e49cbbf892fdea7bf267f5291b9c9aaf45ebe",
          "url": "https://github.com/jannikmi/timezonefinder/commit/97a8e34180daced9c2efb9b0e7867db2b613169f"
        },
        "date": 1786776142055,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "memory::TimezoneFinderL::init_heap",
            "value": 4.466585159301758,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.8729 GHz"
          },
          {
            "name": "memory::TimezoneFinderL::steady_heap",
            "value": 4.466748237609863,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.8729 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::init_heap",
            "value": 4.532352447509766,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.8729 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::steady_heap",
            "value": 4.541023254394531,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.8729 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::init_heap",
            "value": 65.69977760314941,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.8729 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::steady_heap",
            "value": 65.7084846496582,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.8729 GHz"
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
          "id": "3dca95ab33a36d586259b1af0dfac37167ae3c27",
          "message": "CLI: annotate delimited rows from stdin with their timezone (#517)\n\n* feat(cli): add --stdin streaming mode for batch lookups\n\nAdd a --stdin flag that reads lng,lat coordinate pairs from stdin,\none per line, and writes one timezone result per line to stdout.\n\nThe TimezoneFinder instance is constructed once, amortising the\ninitialisation cost across the entire input. This makes the CLI\nusable in shell pipelines:\n\n    cat points.csv | timezonefinder --stdin\n\nDesign decisions:\n- Malformed or blank lines produce a warning on stderr and an empty\n  line on stdout, so a caller reading one line per query stays in\n  step with its inputs (same contract as single-query mode).\n- --stdin and -v are mutually exclusive (verbose output is per-query\n  and would break the one-line-per-result contract).\n- -f/--function applies to the whole stream.\n- The existing single-pair form (timezonefinder LNG LAT) is unchanged.\n\nAlso add timezonefinder/__main__.py so that `python -m timezonefinder`\nworks (needed for running tests without installing the console script\nglobally).\n\nCloses #504.\n\nSigned-off-by: badhope <weed33834@users.noreply.github.com>\n\n* Revert the unrelated edit to the invalid-function-id message\n\nThe stdin PR also changed `4 (TimezoneFinderL.timezone_at_land)` into\n`4 (TimezoneFinderL.timezone_at_land()`, which leaves the parenthesis\nopened after `4` unclosed, so the list of valid ids renders as nested\ngarbage. Nothing asserts this string, so no test caught it.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Reject an unusable stdin line instead of ending the stream\n\nAn out-of-range coordinate parsed as two floats and only failed later,\ninside the lookup, where the ValueError was uncaught: `200,100` on line 2\nof 1000 aborted with a traceback and discarded the remaining 998 answers -\nthe outcome issue #504 singled out as hostile. NaN and infinity did the\nsame, since `float()` accepts them and the bounds check does not.\n\n`_parse_coordinate_line` now runs the package's own `validate_coordinates`\nbefore returning, so a coordinate that reaches the lookup cannot fail\nthere, and reports the reason a line was rejected by raising rather than\nreturning None. The warning quotes that reason, which the caller\npreviously had to guess: every rejected line read \"malformed input\".\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Flush each stdin result so the mode actually streams\n\n`print` leaves stdout block-buffered whenever it is not a terminal, which\nis every case `--stdin` exists for, so a consumer received nothing until\n~8 KB of results had accumulated: `tail -f coords | timezonefinder --stdin`\nproduced no output at all while the producer stayed open, despite every\nlookup having completed in milliseconds.\n\nFlushing also re-synchronises the two streams. stderr is unbuffered, so a\nwarning naming \"line 7\" used to appear before the results for lines 1-6\nwere flushed, leaving nothing to correlate it against.\n\n`flush=True` rather than reconfiguring the stream: `sys.stdout` is typed\n`TextIO`, which has no `reconfigure`, so the line-buffering form does not\ntype-check.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Exit quietly when the stdin consumer closes the pipe\n\n`timezonefinder --stdin < points.csv | head -5` printed its five lines and\nthen dumped a BrokenPipeError traceback, plus a second \"Exception ignored\nin: <_io.TextIOWrapper name='<stdout>'>\" from the interpreter's shutdown\nflush. Stopping early is how the pipelines this mode was built for are\nnormally driven, so the advertised use case ended in a traceback.\n\nRedirecting the fd to the null device before exiting is what suppresses\nthe shutdown flush; catching the error alone is not enough.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Drop the unused function_id parameter from _run_stdin\n\nDocumented as \"used only for stderr diagnostics\" and referenced nowhere in\nthe body. Ruff does not flag unused parameters, so it survived lint; the\ndocstring promising diagnostics that do not exist is the part that costs a\nreader, who has to diff the two to establish which is wrong.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Signal rejected stdin lines through the exit code\n\nAn empty output line meant two different things and the exit status was 0\nfor both: the input on that line was unusable, or the lookup genuinely\nfound no timezone there - which is what `-f 4` and `-f 5` return for every\nocean point. A script counting blank lines as ocean silently counted every\ntypo'd row as ocean too, with nothing in `$?` to contradict it.\n\nRejected lines now make the process exit 1, so the aggregate is\ndetectable without parsing stderr. A stream answered in full still exits\n0, including when every answer is a legitimate empty line.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Name only the missing coordinate, and reject coordinates with --stdin\n\nTwo consequences of making lng and lat `nargs=\"?\"`:\n\n`timezonefinder 4.89` reported \"the following arguments are required:\nlng, lat\" - naming the argument the user had just supplied. The hand-written\nreplacement for argparse's check always listed both; it now lists what is\nactually absent, as argparse did before.\n\n`timezonefinder --stdin 4.89 52.37` accepted the coordinates and discarded\nthem without a word, so appending `--stdin` to an existing invocation\nproduced a process that blocks on the terminal instead of answering. Stray\npositionals are now an error, the same treatment `--stdin -v` already got.\nThe mutual-exclusion test stops passing coordinates it never needed.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Let the CLI trade memory for lookup speed with --in-memory\n\nStreaming mode ran every lookup through the module-level singleton, which\nis `TimezoneFinder(in_memory=False)` and cannot be configured from here, so\nthe one workload whose length can amortise the extra footprint had no way\nto ask for it. `--in-memory` builds an own instance instead; ids 3 and 4\nalready built one and now pass the flag through.\n\nMeasured on a warm page cache, this is ~1.3x on the lookups themselves -\nabout 8% end-to-end over 50k points, where interpreter startup and data\nloading still dominate. It stays opt-in: the memory-mapped default is what\nkeeps this usable in a constrained container, and tens of MB is not a\nprice to charge a single query.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Route the stdin tests through run_cli\n\nFive of the six new cases inlined `subprocess.run([sys.executable, \"-m\",\n\"timezonefinder\", ...])`, duplicating the same five-line block and, more\nimportantly, exercising a different entry point than every other test in\nthe file. `run_cli` runs the installed console script precisely so that the\n`[project.scripts]` wiring is covered - as the module docstring claims - and\na `-m` invocation reaches `main` without it, so a broken entry point would\nhave left all six green.\n\n`run_cli` grows an `input` parameter, which is all the stdin cases needed;\n`test_stdin_and_verbose_are_mutually_exclusive` was already using it.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Make the -f case discriminating and cover the stdin failure modes\n\n`test_stdin_mode_respects_function_flag` sent one land point and asserted\n`Europe/Amsterdam`, which is what the default `-f 0` returns for it too, so\nit stayed green with the flag ignored entirely. It now also sends the ocean\npoint, whose answer differs between the two (`Etc/GMT+10` vs empty).\n\nAdds coverage for each defect fixed in this branch - an unusable line not\nending the stream, the warning naming line/content/reason, a genuine empty\nanswer still exiting 0, `| head -1` not raising BrokenPipeError, stray\npositionals rejected, and the missing-argument message naming only what is\nmissing. All twelve fail against the code as it stood before these fixes.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Document the CLI's streaming mode\n\nThe usage guide's syntax line listed neither `--stdin` nor `--in-memory`,\nand the note directly beneath it still told readers the CLI is \"orders of\nmagnitude slower ... as a separate Timezonefinder() instance is being\ncreated for every call\" - the exact claim `--stdin` exists to refute. A\nuser who hit the batch problem would read that note and conclude the CLI\ncould not help them.\n\nThe new section documents the contract that matters to a caller: one output\nline per input line, and an exit code that distinguishes a stream answered\nin full from one that dropped inputs, since an empty line means both. Also\ncorrects the syntax line's `{0,1,2,3,4,5}`, which has not matched the\naccepted choices since id 2 was removed.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Add the changelog entry for the CLI streaming mode\n\nOne bullet describing where the feature landed, per the repo's changelog\nrules, rather than one per commit in this branch.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Document and pin the stdin input format\n\nThe advertised entry point is `cat points.csv | timezonefinder --stdin`, but\nthe parser is `split(\",\")` and two `float()` calls - not a CSV dialect. A\nheader row, quoted fields, an extra id column and tab- or space-separated\npairs are all rejected, and nothing said so. The usage guide now states the\ncontract, including the tolerances that do hold (surrounding whitespace,\nCRLF, a final line without a newline), and gives a working one-liner for\nprojecting two columns out of a real CSV.\n\nThe ordering hazard gets a warning of its own: the pair is `lng,lat`,\nmatching this package's argument order and reversing the `lat,lng`\nconvention many geographic files use. A swapped pair is usually still a\nvalid coordinate, so it yields a confidently wrong answer and exit 0 -\n`52.37,4.89` resolves to the Indian Ocean, not Amsterdam.\n\nAlso covers two things this branch had added without any test: the\n`--in-memory` flag (same answers as the memory-mapped path, for every\nfunction id, in both modes) and the `__main__` module, which every other\ncase here bypasses by going through the console script.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Resolve stdin coordinate columns by name, never by position\n\nThe bare `lng,lat` line format guessed the column order from an unstated\nconvention, and a wrong guess did not fail: for any longitude between -90\nand 90 the swapped pair is still a valid coordinate, so it resolved to a\nreal timezone. Of 15 major cities, 13 have a silently valid swap, and the\nanswers look plausible - swapping Moscow gives Asia/Tehran, not an error.\nOnly |lng| > 90 (Tokyo, Sydney) was caught by range validation.\n\n--stdin now reads delimited rows and appends a `timezone` column. Columns\ncome from the header by name, or from --lng-col/--lat-col as a header name\nor 1-based number; headerless input with neither is rejected outright. The\norder is stated rather than assumed, which is what removes the failure mode\nrather than warning about it.\n\nAppending the column also makes the mode composable. Annotating a file used\nto mean projecting the coordinates out, running the lookup, and pasting the\nresults back onto the original - four commands reading the input twice, with\nthe projection step being exactly where the swap happened. It is now one\ncommand, and a rejected row identifies itself instead of becoming an\nanonymous blank line.\n\n-d/--delimiter sets the delimiter for input and output ('\\t' spelled out,\nsince a literal tab needs shell-specific quoting). Standard CSV quoting is\nhonoured both ways, so a field containing the delimiter survives; the\nguarantee is therefore one output row per input row, which differs from one\nline per line only when a quoted field spans a newline.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Let a row csv itself rejects cost one row, not the stream\n\n`csv.Error` derives from `Exception`, not `ValueError`, so it escaped the\nhandler written for bad coordinates and aborted `--stdin` with a traceback -\nthe outcome this mode exists to prevent. A field past csv's size limit, which\nany description or WKT column can reach, was enough to discard every row after\nit.\n\nRead the rows by hand instead of through `enumerate`, so the error is caught\nwhere it is raised. The reader resumes on the following line, so the row is\nrejected like any other unusable one; its fields are gone with it, so there is\nnothing to echo back but a blank row.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Read an unverifiable first row as data, never as a header\n\nWith both coordinate columns given as numbers the header names are never\nconsulted, so probing the first row decided nothing but its own fate - and\ndecided it wrongly whenever no field of a data row parsed as a number. A row\nlike `S-1,N/A,N/A` came back relabelled as a header, uncounted and with exit 0:\nsilent data loss, the failure mode addressing columns by number is supposed to\nrule out.\n\nProbe only when the header is actually needed to resolve a column. The two ways\nof being wrong are not symmetric - reading a data row as a header drops it in\nsilence, reading a header as data costs one warning naming the row - so the\nunverifiable case now reads as data.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Match a header column whose name carries a byte order mark\n\nA spreadsheet exported as \"CSV UTF-8\" - the format Excel offers under that\nname, and so a likely producer of the files this mode annotates - begins with a\nBOM. It decodes onto the front of the first column's name, so a file whose\nfirst column is `lng` or `lat` failed to match anything, with an error quoting\na raw `﻿` escape the reader cannot act on.\n\nStrip it where the names are compared. The row itself is still echoed back\nverbatim, so the annotated output stays the same flavour of CSV that was read.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Drop the usage paragraphs describing the superseded output format\n\nThree paragraphs from an earlier revision survived at the end of the section\nand described the format it replaced: an answer per line rather than a column\nappended to the row. They told the reader that a line that cannot be used\n\"produces an empty output line\", that there is \"one output line per input\nline\", and that a coordinate row is \"two numbers\" - none of which is true of\nwhat ships, and the paragraph immediately above them explains why one line per\nline is precisely not the guarantee. The --in-memory paragraph was there twice\nover as well.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Match an explicit column name the way auto-detection does\n\n`--lng-col`/`--lat-col` compared header names exactly, while the automatic\nlookup strips and lowercases them. That made the fallback stricter than the\nmechanism it is the fallback for: `--lng-col lng` did not match a header\nspelling it `LNG`, and a name padded with spaces matched nothing at all - both\nheaders the automatic lookup would have handled had the names been ones it\nknows.\n\nCompare both sides through the same normalisation.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Diagnose a column number wider than the input once, not per row\n\nA typo in `--lng-col` is a property of the flag, not of any one row, but it was\nonly noticed where each row was read: `--lng-col 9` against a three-column file\nproduced a warning and an empty answer for every line, exiting 1 with a\ncomplete but useless copy of the input on stdout. For the file sizes this mode\nexists for that is millions of warnings burying the one fact that matters.\n\nCheck the resolved columns once against the width of the first row, and fail\nthe way every other column-resolution problem does - one message, exit 2,\nnothing written. A row that is merely shorter than the rest is still rejected\non its own, as before.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Spell the tab delimiter in the changelog the way the CLI accepts it\n\nRST inline literals do not process backslash escapes, so ``'\\\\t'`` rendered as\na two-backslash string on the published changelog. Passing what it showed gets\n`--delimiter must be a single character` from the very flag the sentence is\nintroducing. The usage docs and the argparse help both had it right.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Echo a blank row back blank instead of as a quoted empty field\n\n`csv` writes a lone empty field as `\"\"`, to keep it distinguishable from an\nempty row on the way back in. So a blank line in the input became a one-column\nrow in an otherwise rectangular file, and any csv consumer of the output - the\nwhole point of appending the column rather than printing bare answers - trips\nover it. A trailing blank line in a hand-edited file was enough.\n\nThere is no row to append a cell to, so append none. The docs said the blank\nrow came back \"with an empty ``timezone`` cell\", which was never what happened;\nthey now describe the blank echo, and cover the csv-level parse failure the\nsame way.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Refuse --in-memory where there is no polygon data to hold\n\n`TimezoneFinderL` loads no polygon data, so `--in-memory` did nothing at all\nfor `-f 3` and `-f 4` while its help text promised tens of MB spent on faster\nlookups. Nothing in a passing run showed otherwise: the test covering those two\nids asserts the flag changes no answers, which a no-op satisfies perfectly.\n\nReject the combination the way the row-format flags are already rejected\noutside `--stdin`, and say why. The equivalence test now runs over the ids the\nflag reaches, so it would notice if it stopped working there.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Separate a closed pipe from a run that rejected rows\n\nBoth exited 1, so `timezonefinder --stdin < clean.csv | head -5` reported the\none thing the exit code of this mode is for - that some row could not be used -\nabout an input in which every row was fine. Exit 141 instead, which is what a\nshell reports for a process killed by a closed pipe, and what a caller already\nhas to tolerate from the other side of such a pipeline.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* State the in-memory trade-off as a magnitude, not a measured ratio\n\n\"roughly 1.3x faster lookups\" was a figure out of a generated benchmark page,\ncopied by hand into the usage docs, the changelog and the argparse help. The\npage it came from reports 1.02x to 1.51x depending on the workload, so the copy\nwas already narrower than its source, and the next `make reports` moves the\nsource while every copy stays as it was - which is exactly what CLAUDE.md says\nnot to write.\n\nGive the magnitude that survives a measurement, and link the two generated\npages that carry the current numbers for both sides of the trade.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Condense the --stdin changelog bullet to its end state\n\nIt had grown to a 270-word paragraph re-explaining the swapped-pair rationale,\nthe per-row rejection contract, the exit-code semantics and the --in-memory\ntrade-off - all of which the usage documentation covers at length, and none of\nwhich a reader scanning release notes for what changed is looking for. CLAUDE.md\nasks for a few sentences with the detail kept where it belongs.\n\nKeep what a user decides on: what the mode does, that the column order is\nstated rather than guessed and why, the one-row-per-row contract, and the new\nflags. Link the rest.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Let the input state whether it has a header, instead of only guessing\n\nThis mode makes a point of never inferring which column is which, then inferred\nsomething just as load-bearing: whether the first row is a header. The probe has\nno way to be right about a header whose names are all numbers - it reads as data,\nand the coordinate columns are then never found, so a well-formed input is simply\nunusable with no flag to say otherwise.\n\nAdd `--header` / `--no-header`, mutually exclusive, and probe only when neither\nis given. Like the other row-format flags they are refused outside `--stdin`.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Resolve the in-memory lookup function from a table\n\nThe same `TimezoneFinder(in_memory=True).X if in_memory else X` was spelled out\nonce per function id, so the in-memory policy lived in three places that had to\nbe changed together, and the TimezoneFinderL arm carried a comment asking to be\nkept in step with the constant naming those very ids.\n\nPair each id with its global function and the equivalent method name, and let\nthe two arms dispatch off the tables they already have.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Show the coordinates as optional in the usage synopsis\n\nThe synopsis still spelled `lng lat` bare, as it did when they were required.\nA reader following it alongside the `--stdin` section directly below passes\nboth and gets told not to. The flag order had drifted from what argparse\nprints as well.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Record that a push only reaches CI through an open PR\n\nNothing runs on a push to a topic branch: build.yml and benchmark.yml trigger\non pull_request, on master and tags, and on workflow_dispatch. So an empty\nActions list after pushing a branch means the run will never start, not that it\nhas not started yet - which is the same reason a thin green check list is no\nevidence that anything passed.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n---------\n\nSigned-off-by: badhope <weed33834@users.noreply.github.com>\nCo-authored-by: badhope <game33834@outlook.com>\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-15T19:51:19+02:00",
          "tree_id": "ffa4861c834d921705276d9be3d3bb9a1eeb45bb",
          "url": "https://github.com/jannikmi/timezonefinder/commit/3dca95ab33a36d586259b1af0dfac37167ae3c27"
        },
        "date": 1786816358213,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "memory::TimezoneFinderL::init_heap",
            "value": 4.466599464416504,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.8717 GHz"
          },
          {
            "name": "memory::TimezoneFinderL::steady_heap",
            "value": 4.466762542724609,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.8717 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::init_heap",
            "value": 4.532289505004883,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.8717 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::steady_heap",
            "value": 4.54109001159668,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.8717 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::init_heap",
            "value": 65.69977188110352,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.8717 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::steady_heap",
            "value": 65.70842742919922,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.8717 GHz"
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
          "id": "fd3866eb57e4c9dc6fb78e86d569efa724d3c77b",
          "message": "Keep data-only releases from shipping pending work (#519)\n\n* Keep data-only releases from shipping pending work\n\n* Give the release tag step a git identity\n\n`git tag -a` records a tagger and asks git for the committer ident in\nstrict mode. A GitHub runner has no user.name/user.email configured and\nthe auto-detected `runner@fv-az...(none)` is rejected, so the annotated\ntag would fail after the update PR had already been squash-merged: the\ndata lands on master and the tag that starts build.yml is never pushed.\n\ncheck_data_updates.yml already configures both values before committing\nfor exactly this reason; this job did not.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Resolve the update PR through one shared action\n\nThe six jq extractions plus the five-way identity check were copy-pasted\nverbatim into three steps across both jobs. That check is what stops a\nfork branch named data-update-* from reaching the merge step, so three\ncopies meant three things to keep correct, and a one-sided edit would\nleave the weakest copy governing whichever path ran.\n\nIt now lives in .github/actions/resolve-update-pr and every consumer\ntakes the PR number from its output. Behaviour is unchanged; the\nresolution simply runs once, ahead of the changelog guard, because the\nsteps that only run after that guard fails need the number too.\n\nalert_failure gains a checkout of master, which a local `uses:` requires\n- master rather than the PR head, since the job runs code from it while\na pull request is in flight.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Fall back to a branch lookup when the run payload has no PR\n\ngithub.event.workflow_run.pull_requests is empty in more cases than it\nis documented to be, and the workflow had no fallback: the expression\nrendered as the empty string, `gh pr view \"\"` errored, and set -euo\npipefail failed the step. That took out alert_failure too, whose whole\npurpose is to reach the maintainer when something has already gone\nwrong.\n\nThe branch lookup this replaced in the first place is now the fallback\nrather than the only path. It is narrowed to open PRs against master and\nits result goes through the same identity check, so nothing is trusted\nthat was not trusted before.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Treat an already-handled update PR as nothing to do\n\nThe branch lookup this workflow used to do filtered on --state open and\nexited 0 with \"nothing to do\" when it found none. Replacing it with a\nhard identity check collapsed two different situations into one failure:\na PR that is not ours, and a PR that is ours but already merged or\nclosed.\n\nOnly the first is an error. The second is what a maintainer produces by\nre-running build.yml on a data update PR after it has landed - a common\nthing to do - and it re-fires workflow_run. That turned the workflow red\nand made Report pending work abort before commenting, so a genuine\nblocked release would have been announced by nothing at all.\n\nThe shared action now reports found=false for an absent or closed PR and\nerrors only on a mismatch, checking identity first so \"not ours\" can\nnever be softened into a no-op. Every step that merges, labels, comments\nor fails the job gates on found.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Wait for the squash merge commit before tagging\n\nGitHub applies a squash merge asynchronously, so `gh pr view --json\nmergeCommit` right after `gh pr merge` frequently reports null. `--jq\n.mergeCommit.oid` then failed on it and `set -e` aborted the step with\nthe PR already merged - before `merged=true` had been written. The data\nwas on master, no tag was pushed, and nothing downstream could tell that\nfrom a merge that never happened.\n\nThe merge is now recorded the moment it succeeds, the commit is polled\nfor with `// empty` so a null cannot abort the step, and failing to\nresolve it after ten attempts reports what actually happened. The\ncheckout and tag steps key off the resolved commit rather than the merge\nalone, so they can no longer run against an empty ref.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Prove the squash landed on the master the guard checked\n\nThe changelog guard reads master, then the merge step re-reads it and\nrefuses on a mismatch - but the merge follows that read, so a push\nlanding in between still slipped through. `--match-head-commit` pins the\nPR head, not the base, and the GitHub merge API has no equivalent for\nit. The window is small and the consequence is precisely what this\nworkflow exists to prevent: someone's unreleased work published under\ndata-only release notes.\n\nThe squash commit's first parent is the master tip the merge actually\napplied to, so comparing it against the guarded SHA settles the question\nafter the fact. A mismatch withholds the tag rather than the merge - the\nmerge is an ordinary one and stands; the tag is what publishes.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Give each notice cause its own dedup marker\n\nBoth notification steps searched for the same\n<!-- data-update-automation-notice --> marker before commenting, so\nwhichever cause fired first permanently silenced the other. Fix a failing\nCI run, re-run it, and the changelog guard then blocks the release - a\nnotice the workflow would have suppressed, because the earlier CI-failure\ncomment already carried the marker. The maintainer's only signal would\nhave been a red workflow.\n\nThe marker is now per cause. Rather than editing the same dedup block in\ntwo places - which is what let one marker end up shared - the label,\ndedup and comment sequence moves into .github/actions/notify-update-pr,\nwhere the marker is an input and two callers cannot silently agree on\none.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Tell the maintainer which thing actually went wrong\n\nOne step covered both failure causes, so its comment had to name all of\nthem at once - \"pending unreleased work, malformed changelog structure,\nor a concurrent change to master\" - and then asked the maintainer to cut\na release. But the step also fired on any merge failure: a conflict, a\nrequired check, a push landing mid-merge, a merge that succeeded without\nthe tag being pushed. Cutting a release helps with none of those, and\nthe comment carried no link to the run whose log holds the reason.\n\nThere are now two steps, one per cause, each stating only what its\ncondition proves and linking this workflow's run. They use the per-cause\nmarkers from the previous commit, so neither hides the other.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Reject a data release version no later check could find\n\nEvery check in this module recognises a release by _RELEASE_TITLE, which\nrequires <major>.<minor>.<patch>. insert_data_release accepted any string\nas the version, so a heading that pattern cannot match - a release\ncandidate, a two-component version, a stray \"v\" prefix - would be written\ninto the file as text no check can see. The validate_changelog_order call\nat the end of the insert would pass over it rather than reject it, and\nthe next data update would insert above it instead of below, quietly\nreducing the ordering guarantee to \"holds over whichever entries happen\nto be well-formed\".\n\n`uv version --bump patch` does not currently produce such a version, so\nthis is about what the function guarantees to its callers rather than an\nobserved failure.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Match release headings with one pattern instead of two\n\n_RELEASE_HEADING was _RELEASE_TITLE wrapped in a lookahead, purely so\nthat .start() would report the beginning of the heading rather than its\nend. A plain .search() with the same pattern already reports exactly\nthat, since .start() is the start of the match either way - the two\npatterns had to be kept character-identical for no gain.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Cover the check-empty exit code that releases data\n\nThe suite asserted only that a pending unreleased section returns 1. A\ncheck-empty that returned 1 unconditionally would have passed it, while\nsilently ensuring no data update is ever released again - and the\nsymptom, a workflow that merges nothing, is indistinguishable from\nupstream having published no new release.\n\nAdds the success path plus the two error paths the guard depends on\nbeing blocking rather than crashing: a changelog that cannot be parsed,\nand a path that does not exist.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Pin the dedup author filter to the token that comments\n\nThe dedup query only ignores comments it did not write while bot-login\nnames whoever the token authenticates as. Those are two independent\nsettings: secrets.GITHUB_TOKEN posts as github-actions[bot], while the\nGitHub App token this workflow also holds posts as the app. Switching a\nnotifier to the app token - the obvious move if a permission is ever\nmissing - would leave the filter matching no comment at all, so every\nre-run of build.yml would add another maintainer mention. Nothing would\nerror; commenting still succeeds.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Declare the .github paths once for the tests that read them\n\ntests/test_benchmark_workflows.py and tests/test_data_update_workflow.py\neach spelled out PROJECT_ROOT / \".github\" / \"workflows\", and the second\nalso spelled out the actions directory twice. The layout belongs to\nGitHub rather than to this repo, so it now sits with the other path\nconstants in tests/auxiliaries.py and both files import it.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Let a blocked release fail the job on its own\n\nThe guard and the merge both ran under continue-on-error, which meant\nneither could fail the job, which meant a third step existed whose only\nbody was `exit 1` - repeating the disjunction of failure causes a third\ntime. Adding a cause meant remembering to extend three conditions, and\nforgetting the last one would merge and release exactly the work the\nguard had just rejected.\n\nBoth steps now fail the job directly. The reporting steps run on\n`failure()` and each still names the step it reports on, and the merge\nstep needs no guard condition at all, since a step without a status\ncheck function is already skipped once an earlier one has failed.\n\nThe guard picks up the `found` condition the deleted step carried: a run\nwith no update PR has nothing to release, so pending work on master is\nnot a failure of it.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Describe the guard's end state and credit the contributors\n\nFolds the follow-up fixes into the bullets that already describe this\nfeature rather than appending corrections to them, per the changelog\nguidance: the squash-parent check, and the per-cause notices that name\nwhat happened and link the run.\n\nCredits Nice6042 for PR #518, which is the work this branch carries, and\nweed33834 for PR #517, whose --stdin bullet was missing its\nacknowledgement.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Pin the interpreter the changelog guard runs on\n\nThe guard step ran bare `python` with no setup-python before it, so it\nused whatever the runner image happens to default to - pinned by nothing\nthis repo controls. scripts/changelog.py is written against the\nproject's requires-python and annotates `list[str] | None` at module\nlevel, which is a TypeError before 3.10.\n\nThe failure mode is worse than a broken step: the guard failing is\nindistinguishable from the changelog having pending work, so an\ninterpreter change on the runner image would tell the maintainer to cut\na release that does not exist, and block data updates until someone read\nthe log.\n\nPinned to .python-version, matching how every other workflow in this\nrepo sets up Python. The script stays stdlib-only, so it still needs no\nuv sync.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Credit weed33834 for the --stdin contribution\n\nThe --stdin bullet credited #517, which is the maintainer PR that\nsuperseded the actual contribution. weed33834 opened #516 (issue #504);\nit was closed in favour of #517, so the squash merge is authored by the\nmaintainer and nothing in git records where the work came from.\n\nAdds the general rule to CLAUDE.md, since this is the second instance in\nthis release cycle - #518 behind #519 is the same shape - and the\nattribution is exactly what a superseding PR erases.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Cut the workflow tests down to invariants worth pinning\n\ntests/test_data_update_workflow.py had grown to 365 lines, most of it\nasserting that particular shell strings still appear in the YAML -\n\"retrying\", \"parents[0].sha\", the exact gh pr merge invocation. Those\nfail on any rewording and pass on any bug that keeps the wording, so\nthey measure nothing while making every future edit to the workflow look\nexpensive.\n\nWhat survives is the set the structure does not already enforce and\nwhose violation is silent: no step acting on a PR outside the shared\nidentity check, nothing acting when no PR was resolved, the guard\nordered before the merge and able to fail the job, one dedup marker per\nnotice cause, identity checked before state, and a checkout before any\nlocal `uses: ./`. Six tests, 179 lines.\n\ntests/test_changelog.py repeated a full changelog literal in each test;\na builder plus parametrisation covers more cases in half the lines.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Trim the composite action docs to what is not obvious\n\nThe description blocks restated the workflow's own comments and gave\nevery input a sentence, including the ones whose description was the\nexpression they take. What is kept is the part a reader cannot infer:\nwhy the identity check exists, why pr-number may be empty, and why\nbot-login has to match the token.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Record what the workflow tests should have asserted\n\nThe bloat in this PR was not duplicated code - the duplication was\ncaught in review - but 365 lines of tests asserting that particular\nshell strings still appeared in the workflow YAML. Nothing in CLAUDE.md\nwarned against that: the closest rule is about not asserting wording\nanother project owns, which is a different failure.\n\nAmended into Testing rather than opened as a section, and it names the\nrepo's own instance so it reads as a fact rather than advice.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Space the generated release entry like the file it lands in\n\nThe entry ended with one blank line where CHANGELOG.rst puts two above\nevery release title, so each automated data release would have left one\ninconsistent boundary behind. rstcheck accepts either gap and the hooks\nonly look at trailing whitespace, so nothing would have reported it.\n\nThe test fixture had the same one-blank-line gap, which is why it pinned\nthe deviation instead of exposing it; it now mirrors the real file. The\nadded test reads the convention off CHANGELOG.rst rather than restating\nit, since the entries at the bottom predate it and do not follow it.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Treat a superseded run as a no-op, not as a fork PR\n\nThe head-SHA comparison sat inside the identity check, so a run for a\ncommit the PR has moved past exited 1 like a PR from a fork. build.yml\ndeclares no concurrency group, so an older run does finish after a push\nrather than being cancelled: pushing a fix to an update PR while its CI\nis running produced exactly that.\n\nIn alert_failure the resolver failing means `found` is empty and the\nnotice step is skipped, so a genuinely failed CI run was reported\nnowhere - the job the pre-existing inline version did notify from.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Drop the merge output nothing reads\n\n`merged=true` was written with a comment claiming it makes a later error\nreport as \"merged but not released\", but no step or test ever read\n`steps.merge.outputs.merged` - only `merge_sha`. The distinction the\ncomment promised exists solely in the step's own `::error::` text, so the\ncomment read as documented behaviour that was not there.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Report a merge that went through without its tag\n\nBoth reporting steps keyed off the changelog guard or the merge step, so\na failure after the merge - a rejected tag push, a checkout that could\nnot fetch the merge commit - left the update PR unlabelled and without a\ncomment. master carried the new data, no release was built, and since a\nworkflow_run failure appears on no pull request the only trace was the\nActions tab. The docs and the changelog already claimed every cause\nleaves a comment.\n\nThe notice for it is the job's last step by construction, which the\nadded test pins: a step appended below would reopen the same hole.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n---------\n\nCo-authored-by: Ayush Lochab <193861067+Nice6042@users.noreply.github.com>\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-18T00:49:05+02:00",
          "tree_id": "b2d8063b7791411570ddf4447a4a01ced3b5bd9a",
          "url": "https://github.com/jannikmi/timezonefinder/commit/fd3866eb57e4c9dc6fb78e86d569efa724d3c77b"
        },
        "date": 1787007024932,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "memory::TimezoneFinderL::init_heap",
            "value": 4.466646194458008,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 3.1456 GHz"
          },
          {
            "name": "memory::TimezoneFinderL::steady_heap",
            "value": 4.466753005981445,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 3.1456 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::init_heap",
            "value": 4.532118797302246,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 3.1456 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::steady_heap",
            "value": 4.540905952453613,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 3.1456 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::init_heap",
            "value": 65.69964790344238,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 3.1456 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::steady_heap",
            "value": 65.70822143554688,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 3.1456 GHz"
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
          "id": "e3a43ae189dd7f21a2fe4c038f71e354d0fc4af3",
          "message": "Retire the release stop for a state that can no longer arise (#520)\n\nThe cut-release skill stopped when a dated section sat above\n`X.X.X (unreleased)`, and explained it by `update_data.sh` splicing its\nentry under the file header. Since #519 it inserts below the unreleased\nsection and `release_data_update.yml` withholds the merge while anything\nis pending, so the automation cannot leave the file out of order - and\n`validate_changelog_order` fails the test suite over the committed file\nif anything else does, which the skill's green-master precondition\nalready stops on.\n\nThe skill's own maintenance section named this as its removal condition.\nThat entry is spent and goes with it; what replaces it is the record of\nwhy the row is absent, so it is not re-added on the next read.\n\nCloses #510\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-18T01:05:12+02:00",
          "tree_id": "ed8566bcda4190f94f5d93002510a7fd5f6bd83d",
          "url": "https://github.com/jannikmi/timezonefinder/commit/e3a43ae189dd7f21a2fe4c038f71e354d0fc4af3"
        },
        "date": 1787007997446,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "memory::TimezoneFinderL::init_heap",
            "value": 4.466736793518066,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.8703 GHz"
          },
          {
            "name": "memory::TimezoneFinderL::steady_heap",
            "value": 4.466899871826172,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.8703 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::init_heap",
            "value": 4.5323896408081055,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.8703 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::steady_heap",
            "value": 4.541097640991211,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.8703 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::init_heap",
            "value": 65.69981384277344,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.8703 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::steady_heap",
            "value": 65.70852661132812,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.8703 GHz"
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
          "id": "1d98d8849adee5808605ac0f5a27a34fb1c4abb5",
          "message": "Expose the packaged dataset version at runtime (#523)\n\n* Expose the packaged dataset version at runtime (#498)\n\nAn installed timezonefinder could not state which timezone-boundary-builder\nrelease it was answering from: the dataset version lived only in the repo-root\nDATA_VERSION file, which is not packaged, and the package had no __version__\nattribute. As a side effect, every generated benchmark report carried\ntimezonefinder_version: \"Unknown\" because benchmark_utils.py read a\nnon-existent __version__ attribute on a __slots__ class.\n\nImplementation follows the 5-step plan in issue #498:\n\n1. scripts/file_converter.py writes a data_version.txt stamp into the data\n   directory it generates, mirroring the repo-root DATA_VERSION the parse was\n   built from. update_data.sh re-stamps both together after a successful\n   upstream release.\n2. timezonefinder/configs.py declares DATA_VERSION_FILENAME so the runtime\n   and build sides share one filename; AbstractTimezoneFinder.data_version\n   reads it from the packaged data directory at runtime.\n3. timezonefinder.__version__ is exposed via importlib.metadata.\n4. scripts/benchmark_utils.py reads timezonefinder.__version__ from the\n   package instead of getattr(tf_instance, \"__version__\", \"Unknown\").\n5. The new file is covered by the existing MANIFEST.in recursive-include\n   *.txt and [tool.setuptools.package-data] **/*.txt globs, and\n   tests/test_package_contents.py asserts it ships in both wheel and sdist.\n\nVerified locally: full pytest suite green (2994 passed), ruff check + ruff\nformat --check pass, built wheel and sdist both contain\ntimezonefinder/data/data_version.txt.\n\n* Stamp a parse with the release it came from, not the repo's\n\nThe converter wrote data_version.txt from the repo-root DATA_VERSION\nwhatever it had just parsed, so compiling your own GeoJSON - a supported\nuse case - produced a directory whose data_version claimed a\ntimezone-boundary-builder release the data never came from. Silently:\nnothing errors, warns, or has any way to notice.\n\nWhich release an input came from is the caller's to state, so parse_data\ntakes it (`--data-version`, which update_data.sh will pass from the tag\nit records at download time). Unstated, it falls back to DATA_VERSION\nfor the one input that file does describe - the packaged\nDEFAULT_INPUT_PATH - and to \"unknown\" for anything else.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Say what to do when a data directory carries no version stamp\n\nEvery other file of a directory compiled before the stamp existed still\nloads, and lookups still answer, so `data_version` was the one thing that\nfailed - with a bare FileNotFoundError naming a path and nothing else.\nThe sibling check added this release (the coordinate file identifier)\nnames the file and the fix; this one now does too.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Let the parse write the stamp update_data.sh was copying over it\n\nThe script re-typed timezonefinder/data/data_version.txt to repair a\nstamp the converter had just written from the previous DATA_VERSION - a\nsecond spelling of a path the runtime and the converter share a constant\nfor, and one that a rename would leave writing to the old name. The tag\nrecorded at download time is now handed to the parse instead, so the\nstamp is right when it is written and there is nothing to copy over it.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Point the stamp-drift failure at the fix that applies\n\nIt told the reader to re-run scripts/file_converter, which needs a\ngitignored several-hundred-MB download and the full parse the data-update\njob budgets three hours for - to rewrite one line of text. The drift it\nreports is between two copies of a tag, so the fix is a copy; regenerating\nis only the answer when the binaries themselves are the wrong ones, which\nthe message now says instead of assuming.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* List the version stamp in the data directory reference\n\nThe page is what someone reads to build a compatible data directory, so a\nfile missing from it is a file they will not write - and the one thing\nthat then fails, data_version, fails at the point of use rather than at\nload. Its description of update_data.sh also predates the stamp.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Pin the stamp as an essential file instead of rebuilding for it\n\ntest_packaged_data_version_file_in_distribution asserted, over two freshly\nbuilt distributions, exactly what test_essential_files_in_distribution\nalready asserts for this file: ESSENTIAL_SOURCE_PATTERNS matches it via\n`*.txt`, and matches_pattern fnmatches the whole relative path. What that\nleaves unguarded is the pattern set narrowing, which is a statement about\nthe checkout and needs no build - so it is a unit test now, and the third\nhand-typed copy of the stamp's path goes with it.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Hold __version__ to the version pyproject declares\n\nAsserting only that it is not the literal \"unknown\" passes on the failure\nit exists to catch: __version__ reads the *installed* distribution's\nmetadata, so an environment left behind by a version bump answers with\nthe previous release - not the fallback, indistinguishable from a real\nanswer, and exactly what get_system_status() would then record in every\nbenchmark report. The pyproject path moves next to the repository's other\ntooling paths, since a second test already had its own copy.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Let the downloaded file carry the release it came from\n\nNothing inside a timezone-boundary-builder GeoJSON says which release it\nis, so the release could only be re-stated alongside the file - as a\nshell variable, true for one invocation of one script, and as a fallback\nthat read the repository's own DATA_VERSION for the input it recognised.\n\nupdate_data.sh now resolves the tag first and names the download after\nit, which also makes one answer govern the download URL, the file names\nand DATA_VERSION: fetching `releases/latest/download/` while separately\nasking the API what `latest` was were two questions, and a release\nlanding between them attributed one release's data to the other. Naming\nthe archive and the GeoJSON per release and variant additionally stops a\nleftover file satisfying the \"already downloaded\" checks.\n\nThe converter reads the tag back off the name, and refuses an unpacked\narchive that lacks one instead of stamping data that could never say\nwhere it came from - before creating the output directory, so a refusal\nleaves nothing behind. Data that is not a release stays \"unknown\", and\n--data-version remains for an input that cannot be renamed. No rule can\nnow produce a release tag the data did not come from.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Describe how a parse learns which release it compiled\n\nThe pipeline steps skipped the naming step, and the use-cases page still\ndescribed a default input (`combined.json` next to the package) that has\nnot been one for some time - both now say where the release comes from,\nand that data which is not a release needs no name.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Update CLAUDE.md\n\n---------\n\nCo-authored-by: MsfPablo <129399053+MsfPablo@users.noreply.github.com>\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-18T22:13:26+02:00",
          "tree_id": "9e0befe4adac781beba799845bd8c32ba3adce40",
          "url": "https://github.com/jannikmi/timezonefinder/commit/1d98d8849adee5808605ac0f5a27a34fb1c4abb5"
        },
        "date": 1787084101106,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "memory::TimezoneFinderL::init_heap",
            "value": 4.466641426086426,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 3.2428 GHz"
          },
          {
            "name": "memory::TimezoneFinderL::steady_heap",
            "value": 4.466804504394531,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 3.2428 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::init_heap",
            "value": 4.532258987426758,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 3.2428 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::steady_heap",
            "value": 4.5408735275268555,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 3.2428 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::init_heap",
            "value": 65.69972705841064,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 3.2428 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::steady_heap",
            "value": 65.7084264755249,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 3.2428 GHz"
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
          "id": "d6af064e46ce18d60f41a07b7d6a5e3a0ad788de",
          "message": "Give the shortcut binaries a file identifier and a layout version (#526)\n\nThe hybrid shortcut files finished their buffer bare and the reader picked a\nschema by substring-matching \"uint8\"/\"uint16\" in the file name, so a renamed or\nmispaired file was caught by nothing: the two schemas differ only in the width\nof UniqueZone.zone_id, and either width parses cleanly under the other and hands\nback wrong zone ids.\n\nBoth schemas now declare a file_identifier - TZS1 for uint8, TZS2 for uint16,\ndistinct on purpose - and a layout_version field mirroring PolygonCollection's.\nThe reader dispatches on the identifier stamped inside the buffer and then\nchecks the version, so the file name carries no meaning any more and\n_schema_for_file_name is gone. polygons.py's rejection message moves to\ntimezonefinder/flatbuf/io/layout.py so both binary kinds fail the same way.\n\nThe packaged hybrid_shortcuts_uint16.fbs is regenerated to carry the markers;\nits decoded mapping is unchanged entry for entry, and coordinates.fbs is\nuntouched.\n\nCloses #458\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-18T23:34:30+02:00",
          "tree_id": "3be670d0d81111510337ee9e4822c6294832d070",
          "url": "https://github.com/jannikmi/timezonefinder/commit/d6af064e46ce18d60f41a07b7d6a5e3a0ad788de"
        },
        "date": 1787088945181,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "memory::TimezoneFinderL::init_heap",
            "value": 4.466585159301758,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on INTEL(R) XEON(R) PLATINUM 8573C @ 3.1099 GHz"
          },
          {
            "name": "memory::TimezoneFinderL::steady_heap",
            "value": 4.466748237609863,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on INTEL(R) XEON(R) PLATINUM 8573C @ 3.1099 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::init_heap",
            "value": 4.53233528137207,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on INTEL(R) XEON(R) PLATINUM 8573C @ 3.1099 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::steady_heap",
            "value": 4.541141510009766,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on INTEL(R) XEON(R) PLATINUM 8573C @ 3.1099 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::init_heap",
            "value": 65.69967937469482,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on INTEL(R) XEON(R) PLATINUM 8573C @ 3.1099 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::steady_heap",
            "value": 65.70839023590088,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on INTEL(R) XEON(R) PLATINUM 8573C @ 3.1099 GHz"
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
          "id": "59531c5eba390a3aa12af0caf019fb7942d1b81f",
          "message": "Publish the boundary data as a separate distribution (#446) (#527)\n\n* Move the packaged data and its licence into packages/timezonefinder-data\n\nTree-only: the binaries and DATA_LICENSE are renamed, not rewritten, and the\nnew distribution's pyproject/README/__init__ are added alongside them. Nothing\nimports the new package yet - the wiring follows separately, so that the 62 MB\nrename can be reviewed apart from it.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Publish the boundary data as a separate distribution\n\n`timezonefinder-data` is now its own distribution, built from the same\nworkspace. `pip install timezonefinder` is unchanged - the dependency is hard -\nbut a dataset can be pinned without pinning old code, and a data update no\nlonger costs a `timezonefinder` release carrying ~65 MB across three platform\nwheels plus an sdist.\n\nThe version carries two facts, because two things drive a data release: the\ndata distribution's major *is* `DATA_FORMAT_VERSION`, and the root requires\n`timezonefinder-data>=1.2026.3,<2`. No ceiling on the data axis, so an ordinary\nupdate still needs no code release; a hard one on the format axis, so old code\npaired with a new format fails when resolving rather than at the first lookup.\nThe in-file identifier and layout_version markers stay: `bin_file_location`\ndirectories have no metadata to read, and only a per-file marker catches a\nmixed directory.\n\nThe two tag namespaces share a branch, so the separation is enforced rather\nthan conventional - build.yml excludes `data-v*` at its trigger and again on\nthe job creating the GitHub Release, since `release: types: [published]`\nconsults no tag filter, and each stream publishes with its own token.\nRetiring the pending-work guard follows from the split: a data tag now\npublishes a distribution containing no code, so unreleased code work has\nnothing to do with it.\n\nAlso: DATA_LICENSE moves with the database it covers, a compiled data\ndirectory carries a copy of the schemas its binaries were written by, and\ntest_package_contents.py asserts neither distribution carries the other's\npayload.\n\nRefs #446\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Point the improvement ledger at the data's new location\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Publish the data distribution by Trusted Publishing\n\nPyPI trusts the publish_data.yml workflow directly, gated on the `pypi-data`\ndeployment environment, so the job exchanges an OIDC identity for a\nshort-lived upload token instead of holding one. No long-lived credential\nexists that could upload `timezonefinder`, and the pending publisher covers\nthe very first upload - which a project-scoped token could not, since the\nproject does not exist yet.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Fix the tox bootstrap and drop issue references from code\n\ntox installs the package with bare pip, which resolved the new\n`timezonefinder-data` requirement from PyPI - where this checkout's version\nneed not exist, and does not at all before the first data release. Every tox\nenv now installs the workspace member from the source tree, which also keeps\nthem testing the data this checkout carries rather than a published one.\n\nSeparately: an issue number in a comment is an indirection to a tracker the\nreader may not be able to open, and one that gets retitled and re-scoped\nindependently of the code, so the reason stops being where the code is. The\nreasoning is now written out at each site. CLAUDE.md records the rule, with\nCHANGELOG.rst as the stated exception.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n---------\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-19T01:53:17+02:00",
          "tree_id": "f0f4b971c74cf1a2ba1c097210f180c97b752685",
          "url": "https://github.com/jannikmi/timezonefinder/commit/59531c5eba390a3aa12af0caf019fb7942d1b81f"
        },
        "date": 1787097260638,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "memory::TimezoneFinderL::init_heap",
            "value": 4.466585159301758,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V45 96-Core Processor @ 2.5961 GHz"
          },
          {
            "name": "memory::TimezoneFinderL::steady_heap",
            "value": 4.466748237609863,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V45 96-Core Processor @ 2.5961 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::init_heap",
            "value": 4.532464981079102,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V45 96-Core Processor @ 2.5961 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::steady_heap",
            "value": 4.541314125061035,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V45 96-Core Processor @ 2.5961 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::init_heap",
            "value": 65.69955253601074,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V45 96-Core Processor @ 2.5961 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::steady_heap",
            "value": 65.70830059051514,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V45 96-Core Processor @ 2.5961 GHz"
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
          "id": "a52225c2b8babd9674412b0c5c3c60c741e2be5b",
          "message": "Name the packaged FlatBuffers binaries .bin, not .fbs (#528)\n\n* Move the packaged data and its licence into packages/timezonefinder-data\n\nTree-only: the binaries and DATA_LICENSE are renamed, not rewritten, and the\nnew distribution's pyproject/README/__init__ are added alongside them. Nothing\nimports the new package yet - the wiring follows separately, so that the 62 MB\nrename can be reviewed apart from it.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Publish the boundary data as a separate distribution\n\n`timezonefinder-data` is now its own distribution, built from the same\nworkspace. `pip install timezonefinder` is unchanged - the dependency is hard -\nbut a dataset can be pinned without pinning old code, and a data update no\nlonger costs a `timezonefinder` release carrying ~65 MB across three platform\nwheels plus an sdist.\n\nThe version carries two facts, because two things drive a data release: the\ndata distribution's major *is* `DATA_FORMAT_VERSION`, and the root requires\n`timezonefinder-data>=1.2026.3,<2`. No ceiling on the data axis, so an ordinary\nupdate still needs no code release; a hard one on the format axis, so old code\npaired with a new format fails when resolving rather than at the first lookup.\nThe in-file identifier and layout_version markers stay: `bin_file_location`\ndirectories have no metadata to read, and only a per-file marker catches a\nmixed directory.\n\nThe two tag namespaces share a branch, so the separation is enforced rather\nthan conventional - build.yml excludes `data-v*` at its trigger and again on\nthe job creating the GitHub Release, since `release: types: [published]`\nconsults no tag filter, and each stream publishes with its own token.\nRetiring the pending-work guard follows from the split: a data tag now\npublishes a distribution containing no code, so unreleased code work has\nnothing to do with it.\n\nAlso: DATA_LICENSE moves with the database it covers, a compiled data\ndirectory carries a copy of the schemas its binaries were written by, and\ntest_package_contents.py asserts neither distribution carries the other's\npayload.\n\nRefs #446\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Point the improvement ledger at the data's new location\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Publish the data distribution by Trusted Publishing\n\nPyPI trusts the publish_data.yml workflow directly, gated on the `pypi-data`\ndeployment environment, so the job exchanges an OIDC identity for a\nshort-lived upload token instead of holding one. No long-lived credential\nexists that could upload `timezonefinder`, and the pending publisher covers\nthe very first upload - which a project-scoped token could not, since the\nproject does not exist yet.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Fix the tox bootstrap and drop issue references from code\n\ntox installs the package with bare pip, which resolved the new\n`timezonefinder-data` requirement from PyPI - where this checkout's version\nneed not exist, and does not at all before the first data release. Every tox\nenv now installs the workspace member from the source tree, which also keeps\nthem testing the data this checkout carries rather than a published one.\n\nSeparately: an issue number in a comment is an indirection to a tracker the\nreader may not be able to open, and one that gets retitled and re-scoped\nindependently of the code, so the reason stops being where the code is. The\nreasoning is now written out at each site. CLAUDE.md records the rule, with\nCHANGELOG.rst as the stated exception.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Name the packaged FlatBuffers binaries .bin, not .fbs\n\n`.fbs` is the FlatBuffers *schema* extension, and since the data directory\nstarted shipping actual schemas next to the buffers, one extension named two\nunrelated kinds of file - which is why the schema copies needed a subdirectory\nto avoid the collision. Each buffer already states what it is through the file\nidentifier in its first bytes, which a rename cannot forge; the name never\ncarried that meaning.\n\nThe bytes are unchanged, so this is a `git mv` of identical blobs and adds\nnothing to history. No layout version moves and DATA_FORMAT_VERSION stays 1:\nno `timezonefinder-data` has been published yet, and no released\n`timezonefinder` reads a data distribution at all, so there is no pairing to\nprotect against. That is only true while this lands before the first `data-v`\ntag - afterwards it would be a format bump and an ordered two-distribution\nrelease.\n\nCustom `bin_file_location` directories must be regenerated, which this release\ncycle already required for the coordinate layout, the hole storage and the\nshortcut container; the changelog states the file names alongside those rather\nthan as a second obligation.\n\nAlso drops the pointer to a gitignored plans/ file from CLAUDE.md - the\nreasoning it pointed at is now stated where it can actually refuse the next\nproposal - and records the rule against citing anything outside the repository\nas a reason.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n---------\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>\nCo-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>",
          "timestamp": "2026-08-19T02:15:12+02:00",
          "tree_id": "9b3104e62db704f6982605a83f4f3f54701fe8a1",
          "url": "https://github.com/jannikmi/timezonefinder/commit/a52225c2b8babd9674412b0c5c3c60c741e2be5b"
        },
        "date": 1787098587486,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "memory::TimezoneFinderL::init_heap",
            "value": 4.466641426086426,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 2.4454 GHz"
          },
          {
            "name": "memory::TimezoneFinderL::steady_heap",
            "value": 4.466748237609863,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 2.4454 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::init_heap",
            "value": 4.532382965087891,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 2.4454 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::steady_heap",
            "value": 4.541144371032715,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 2.4454 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::init_heap",
            "value": 65.69963836669922,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 2.4454 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::steady_heap",
            "value": 65.70833206176758,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 2.4454 GHz"
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
          "id": "42696172134b385922d487b33773321cb7f2d99d",
          "message": "Refuse to publish the code before the data it requires exists (#529)\n\n* Refuse to publish the code before the data it requires exists\n\nThe two distributions release independently, and on a data format change the\norder is fixed: the data first, then the code requiring it. Backwards, the\nwheel is uninstallable for everyone until the data lands - and PyPI never\naccepts a version number twice, so the fix is a whole new release rather than\na re-upload. Until now that ordering was a checklist item with nothing\nenforcing it.\n\nThe guard runs in the publishing job, ahead of the upload, and reads the\nrequirement out of the wheel about to be published rather than out of\npyproject.toml: the wheel is what a user's resolver will read. It then asks\nthe index the same question that resolver will ask, instead of reimplementing\nthe answer - so a release whose files are all yanked does not count as one\nthat satisfies the bound.\n\n\"Nothing satisfies it\" and \"the check could not run\" exit differently. A\nrelease blocked because PyPI was unreachable is a retry; one blocked because\nthe data is genuinely missing needs the data published first, and collapsing\nthe two loses the only thing the operator needs to know. A wheel declaring no\ndata dependency at all is the second kind, not a pass - that would be the\nguard succeeding for the wrong reason.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Guard release on data dependency: require data published before code\n\nEnsure code releases cannot be published until the separate timezonefinder-data distribution is published. Update CI workflows, release scripts, documentation and tests to check and enforce the data dependency.\\n\\nFiles changed include workflow YAMLs, release helper scripts, docs, and tests to make the data dependency explicit and to prevent accidental code-only releases.\\n\\nCo-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>\n\n* Finish the release guard and assert what each distribution ships\n\nCompletes three items left open on this branch.\n\nThe data-dependency check ran twice: the move ahead of the GitHub Release\nlanded, but the copy next to the PyPI upload survived the merge. Drop it -\n`publish-pypi` needs `release`, so one placement covers both - and widen its\ntest from \"before the upload\" to \"before any publishing step\", satisfied\nin-job or through a dependency. The old test passed with the guard sitting\nafter the GitHub Release, which is the earlier irreversible step.\n\nAssert each distribution's build contents. setuptools copies package data\ninto build/lib and never prunes it, so the .fbs -> .bin rename left a 63 MB\ncoordinates.fbs shipping next to its replacement in every wheel built from a\ndeveloper checkout - 99 MiB instead of 50. Nothing caught it: the\nunwanted-file scan only knows .gitignore patterns, which cannot match a path\ninside an archive, and the essential-file checks only ask whether expected\nfiles are present. Compare the wheel's payload to the committed dataset as a\nset, and clear build/ before building so a local build matches CI's fresh\ncheckout.\n\nRestore the code sdist's assertions for the test fixtures it grafts. Dropping\n*.npy/*.json when the dataset moved out also dropped the only checks that\ntests/fixtures/benchmarks/ and tests/test_input.json still ship.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* Let cut-release decide the bump level, reviewed on the release PR\n\nThe skill stopped twice: once to put patch/minor/major to the maintainer,\nonce before pushing the tag. The first stop asked them to answer, from §4's\ntable and with no diff attached, a question the release PR then asked again\nwith both attached. Drop it: §4 derives the level from the table, and §7's\n\"Why this level\" is the review surface instead.\n\nThat only works if the justification is checkable, so it now has a required\nshape - the one bullet that drove the level, quoted, the table row it matches,\nand the level ruled out with the reason. \"minor, not major: no exported\nsignature changed\" can be checked in seconds; \"minor\" cannot.\n\nThe tag stop stays and is different in kind: nothing reviews it afterwards,\nbuild.yml publishes on the push, and PyPI will not take a version twice. The\nmaintenance section records both directions so the next pass neither re-adds\nthe bump gate nor removes the tag one.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n---------\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-19T07:35:03+02:00",
          "tree_id": "728a8d1bd275eef1eb7a0f6165c853acec39fb4d",
          "url": "https://github.com/jannikmi/timezonefinder/commit/42696172134b385922d487b33773321cb7f2d99d"
        },
        "date": 1787117779853,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "memory::TimezoneFinderL::init_heap",
            "value": 4.466585159301758,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on INTEL(R) XEON(R) PLATINUM 8573C @ 2.3000 GHz"
          },
          {
            "name": "memory::TimezoneFinderL::steady_heap",
            "value": 4.466748237609863,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on INTEL(R) XEON(R) PLATINUM 8573C @ 2.3000 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::init_heap",
            "value": 4.5325469970703125,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on INTEL(R) XEON(R) PLATINUM 8573C @ 2.3000 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::steady_heap",
            "value": 4.541166305541992,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on INTEL(R) XEON(R) PLATINUM 8573C @ 2.3000 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::init_heap",
            "value": 65.69967937469482,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on INTEL(R) XEON(R) PLATINUM 8573C @ 2.3000 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::steady_heap",
            "value": 65.70830726623535,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on INTEL(R) XEON(R) PLATINUM 8573C @ 2.3000 GHz"
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
          "id": "6671aadf82bbb91dc1b3f0a62cb9415dbe5e2f7e",
          "message": "Release 8.3.0 (#532)\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-19T07:58:10+02:00",
          "tree_id": "84b372e777e2f128ca5ef259b6c278c1e11338fb",
          "url": "https://github.com/jannikmi/timezonefinder/commit/6671aadf82bbb91dc1b3f0a62cb9415dbe5e2f7e"
        },
        "date": 1787119164474,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "memory::TimezoneFinderL::init_heap",
            "value": 4.4665937423706055,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.8726 GHz"
          },
          {
            "name": "memory::TimezoneFinderL::steady_heap",
            "value": 4.466756820678711,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.8726 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::init_heap",
            "value": 4.532416343688965,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.8726 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::steady_heap",
            "value": 4.5411787033081055,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.8726 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::init_heap",
            "value": 65.69963073730469,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.8726 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::steady_heap",
            "value": 65.70843505859375,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.8726 GHz"
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
          "id": "f2cffeede3d1a9d666667b9c8b3ea328fdb99049",
          "message": "Run the tox matrix once per release, not twice (#534)\n\nThe matrix is the whole critical path of build.yml - four jobs of 6-10\nminutes each, against under a minute for every other job combined - and\nit ran for the push to master and again for the tag naming that same\ncommit. Skip it on tag refs, and gate the release job to tag refs only:\nmaster tests, the tag releases. That also removes the race the release\nprocedure worked around, since the release action is handed the tag name\nand so a master push created the tag on its own.\n\nThe skip is backed by a check, not an assumption. The pre-existing\nancestry step proves the commit is on master, not that it was ever\ngreen, so the release job now asks the API for a successful build run on\nmaster for that exact SHA and refuses to publish if none exists.\n\nIts `if` needs !cancelled() because a skipped `needs` job skips its\ndependents - and naming any status function drops the implicit\nsuccess(), so every dependency that does still run is checked by hand.\ntests/test_release_workflows.py evaluates those conditions rather than\nreading them, since the failure mode surfaces only during a release.\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-19T08:24:41+02:00",
          "tree_id": "2af6f3c18f6345f2a685d0b15a740d22be44ec8a",
          "url": "https://github.com/jannikmi/timezonefinder/commit/f2cffeede3d1a9d666667b9c8b3ea328fdb99049"
        },
        "date": 1787121041005,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "memory::TimezoneFinderL::init_heap",
            "value": 4.4665985107421875,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 2.4454 GHz"
          },
          {
            "name": "memory::TimezoneFinderL::steady_heap",
            "value": 4.466748237609863,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 2.4454 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::init_heap",
            "value": 4.532293319702148,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 2.4454 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::steady_heap",
            "value": 4.54117488861084,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 2.4454 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::init_heap",
            "value": 65.69959163665771,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 2.4454 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::steady_heap",
            "value": 65.7084379196167,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 2.4454 GHz"
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
          "id": "b0642ad3bdc488421ced2ae69af55bc64d0c05a7",
          "message": "Collapse the artifact-staging steps into one composite action (#535)\n\n`build.yml` wrote the same \"unzip every artifact, flatten into dist/\" block\nthree times, in `end-to-end-test`, `release` and `publish-pypi`. The copies had\ndrifted - two matched `artifact-*.zip`, one `artifact-*`, which unzips a\ndirectory and fails without anyone noticing, since `find -exec` does not\npropagate its command's exit status - and that accidental drift sat next to the\none difference that is deliberate: `publish-pypi` excludes the data wheel,\nbecause it uploads whatever is in dist/ as `timezonefinder` while the data\ndistribution publishes from publish_data.yml under its own tag and publisher.\nNothing told a reader which of the two was load-bearing.\n\nThe block is now `.github/actions/stage-artifacts`, taking that exclusion as a\nnamed input. Only the prologue moved: the data-dependency check and both\npublishing steps stay inline, so the ordering test that walks each job's steps\nstill sees them.\n\n`publish-pypi` also drops four steps nothing consumed. `Fetch version` set an\noutput only `release` reads; with it gone no step ran uv or pip, so setting up\nPython, upgrading pip and installing uv had no consumer either. Its checkout\nstays, now for one reason: `uses: ./...` resolves from the workspace.\n`end-to-end-test` gains a sparse, non-cone checkout for the same reason - a\nfull one would put this repository's pyproject.toml in the workspace root,\nwhere the job builds a throwaway project with `uv init`.\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-19T10:20:16+02:00",
          "tree_id": "9bf23e0d369ce8e2ef21f2d87ef07d20bc19da44",
          "url": "https://github.com/jannikmi/timezonefinder/commit/b0642ad3bdc488421ced2ae69af55bc64d0c05a7"
        },
        "date": 1787127703548,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "memory::TimezoneFinderL::init_heap",
            "value": 4.466585159301758,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 2.4454 GHz"
          },
          {
            "name": "memory::TimezoneFinderL::steady_heap",
            "value": 4.466748237609863,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 2.4454 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::init_heap",
            "value": 4.532464981079102,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 2.4454 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::steady_heap",
            "value": 4.541266441345215,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 2.4454 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::init_heap",
            "value": 65.69916248321533,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 2.4454 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::steady_heap",
            "value": 65.70796012878418,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 2.4454 GHz"
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
          "id": "64da9e1a30df7565d2742ab22b9ee755f03b9476",
          "message": "Type-check tests/, and close two surfaces nothing was checking (#539)\n\n* SURF-1: drop the three schema filenames from the schemas package __all__\n\nThey are .fbs data files next to the module, not submodules of it, so\n`from timezonefinder.flatbuf.schemas import *` raised AttributeError on a\nsurface declaration nothing checked. tests/test_documented_contracts.py now\nresolves every __all__ entry in the package against its module.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* TOOL-5: type-check tests/ with the mypy hook instead of excluding it\n\nClears the eight real disagreements the exclusion had been hiding - an\nundeclared attribute the base test class's fixture assigns, two subclasses\ncontradicting types inferred from the base's own values, a promised list[Path]\nbacked by an attribute only ever inferred as None, a dict literal annotated\nset[str, str], and an unmeasured metric reaching a float comparison as None -\nthen drops tests/ from the hook's exclude and extends the guard that keeps\nscripts/ out of it to cover tests/ too.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* PATH-1: import PROJECT_ROOT in the test helpers instead of re-deriving it\n\ntests/auxiliaries.py anchored the checkout root on the installed timezonefinder\npackage (PACKAGE_DIR.parent), which is site-packages for anything but an\neditable install. scripts.configs already declares it against the repository.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* DUP-2: create the converter's output directories once, in the caller\n\nwrite_numpy_binaries and write_flatbuffer_files each recomputed holes_dir and\nboundaries_dir and mkdir'd them, which reads as though either could run alone;\nthey cannot, since the reference vector one writes addresses the coordinate\nfile the other writes. The zone ids now go through store_per_polygon_vector\nlike every other vector. Verified byte-identical over tests/test_input.json.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* REND-1: choose the memory report's metric paragraph with an if, not a ternary\n\nThe conditional sat at the foot of twelve lines of implicitly concatenated\nprose, so a reader editing the long branch had no reason to look for it. Only\nthat branch interpolates the workload size. The rendered text is unchanged -\nthe diff moves no character of either paragraph.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* TEST-11: assert the metadata the build produces, not just the files it copies\n\ntest_essential_files_in_distribution is driven by paths that exist in the\nsource tree, so it structurally cannot notice PKG-INFO or the .dist-info\ndirectory going missing - a failure that would otherwise surface at upload.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n* ledger: re-verify every entry against the data-package split, record pass 10\n\nDeletes the four entries this pass shipped (DUP-2, TEST-11, REND-1, TOOL-5),\ncorrects TOOL-1's B905 claim - the load-path zip it named cannot truncate, both\nlists being local accumulators appended in one loop - and narrows DEAD-5 to the\ndeletion decision now that its annotation half is fixed. Adds TOOL-7 for the\nrelease guard's silent single-wheel pick, a scope note for the thin data\ndistribution, and the pass 10 coverage row.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n\n---------\n\nCo-authored-by: Claude Opus 5 <noreply@anthropic.com>",
          "timestamp": "2026-08-20T00:20:37+02:00",
          "tree_id": "e50a9152f1d951ecc7396043dabd687391b1bf78",
          "url": "https://github.com/jannikmi/timezonefinder/commit/64da9e1a30df7565d2742ab22b9ee755f03b9476"
        },
        "date": 1787178128660,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "memory::TimezoneFinderL::init_heap",
            "value": 4.4665937423706055,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 3.1439 GHz"
          },
          {
            "name": "memory::TimezoneFinderL::steady_heap",
            "value": 4.466756820678711,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 3.1439 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::init_heap",
            "value": 4.532366752624512,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 3.1439 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::steady_heap",
            "value": 4.541225433349609,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 3.1439 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::init_heap",
            "value": 65.69972038269043,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 3.1439 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::steady_heap",
            "value": 65.70843696594238,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 3.1439 GHz"
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
          "id": "db9c6f8532d1cd23ebb7c2b0fa4fc56edf538c0d",
          "message": "Merge pull request #538 from weed33834/docs/use-cases-503\n\ndocs(use-cases): drop pytz as the offset reference, warn about the Etc/GMT±X sign footgun (closes #503)",
          "timestamp": "2026-08-20T01:29:57+02:00",
          "tree_id": "1cba5ed8ef96df32b00a8a33d109822bac8760e9",
          "url": "https://github.com/jannikmi/timezonefinder/commit/db9c6f8532d1cd23ebb7c2b0fa4fc56edf538c0d"
        },
        "date": 1787182270789,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "memory::TimezoneFinderL::init_heap",
            "value": 4.466551780700684,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on INTEL(R) XEON(R) PLATINUM 8573C @ 2.3000 GHz"
          },
          {
            "name": "memory::TimezoneFinderL::steady_heap",
            "value": 4.466714859008789,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on INTEL(R) XEON(R) PLATINUM 8573C @ 2.3000 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::init_heap",
            "value": 4.532465934753418,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on INTEL(R) XEON(R) PLATINUM 8573C @ 2.3000 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::steady_heap",
            "value": 4.541271209716797,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on INTEL(R) XEON(R) PLATINUM 8573C @ 2.3000 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::init_heap",
            "value": 65.69959545135498,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on INTEL(R) XEON(R) PLATINUM 8573C @ 2.3000 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::steady_heap",
            "value": 65.70835590362549,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on INTEL(R) XEON(R) PLATINUM 8573C @ 2.3000 GHz"
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
          "id": "20ae948fc8d72357e97ed0c01e6128afc550bd83",
          "message": "Merge pull request #537 from jannikmi/roadmap/497-profile-query-time\n\nProfile where per-query time actually goes (#497)",
          "timestamp": "2026-08-20T02:21:37+02:00",
          "tree_id": "ba0ad600fcde8de14e3b2bf5975bdc32f436ccf2",
          "url": "https://github.com/jannikmi/timezonefinder/commit/20ae948fc8d72357e97ed0c01e6128afc550bd83"
        },
        "date": 1787185369201,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "memory::TimezoneFinderL::init_heap",
            "value": 4.466641426086426,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.5961 GHz"
          },
          {
            "name": "memory::TimezoneFinderL::steady_heap",
            "value": 4.466804504394531,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.5961 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::init_heap",
            "value": 4.5323686599731445,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.5961 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::steady_heap",
            "value": 4.541172981262207,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.5961 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::init_heap",
            "value": 65.699538230896,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.5961 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::steady_heap",
            "value": 65.70815086364746,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.5961 GHz"
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
          "id": "10d6467457600b58cd7ceccc21ba7e428cb15a55",
          "message": "Merge pull request #540 from jannikmi/skill/improvement-pass\n\nOne improvement-pass skill, and one register behind it",
          "timestamp": "2026-08-20T23:13:26+02:00",
          "tree_id": "4a0e87cf90900a632e7ee6583b05aca38b14de24",
          "url": "https://github.com/jannikmi/timezonefinder/commit/10d6467457600b58cd7ceccc21ba7e428cb15a55"
        },
        "date": 1787260480092,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "memory::TimezoneFinderL::init_heap",
            "value": 4.466543197631836,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 3.6954 GHz"
          },
          {
            "name": "memory::TimezoneFinderL::steady_heap",
            "value": 4.466706275939941,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 3.6954 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::init_heap",
            "value": 4.532495498657227,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 3.6954 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::steady_heap",
            "value": 4.541296005249023,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 3.6954 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::init_heap",
            "value": 65.69932460784912,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 3.6954 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::steady_heap",
            "value": 65.70812606811523,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 3.6954 GHz"
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
          "id": "ce69bf737258d9695ace3ddfbecfdb8c48b9380e",
          "message": "Merge pull request #541 from jannikmi/register/record-the-measurements\n\nRecord the measurements four entries were waiting on, and three decisions",
          "timestamp": "2026-08-21T14:34:33+02:00",
          "tree_id": "146ec5377351eedc190737a239eccb35ae1eb335",
          "url": "https://github.com/jannikmi/timezonefinder/commit/ce69bf737258d9695ace3ddfbecfdb8c48b9380e"
        },
        "date": 1787315749655,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "memory::TimezoneFinderL::init_heap",
            "value": 4.466641426086426,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.5961 GHz"
          },
          {
            "name": "memory::TimezoneFinderL::steady_heap",
            "value": 4.466804504394531,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.5961 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::init_heap",
            "value": 4.532467842102051,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.5961 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::steady_heap",
            "value": 4.541265487670898,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.5961 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::init_heap",
            "value": 65.6995792388916,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.5961 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::steady_heap",
            "value": 65.70838165283203,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 9V74 80-Core Processor @ 2.5961 GHz"
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
          "id": "fb5a3a3f24d3f18dcd0e13fbf756b74841396c53",
          "message": "Merge pull request #544 from jannikmi/perf/coordinate-offset-table\n\nAddress polygon coordinates by offset instead of re-walking the FlatBuffers vtable",
          "timestamp": "2026-08-22T02:36:53+02:00",
          "tree_id": "903d7f3a9c4fe4e70de1205e404e460c4b085e55",
          "url": "https://github.com/jannikmi/timezonefinder/commit/fb5a3a3f24d3f18dcd0e13fbf756b74841396c53"
        },
        "date": 1787359096257,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "memory::TimezoneFinderL::init_heap",
            "value": 4.466585159301758,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 3.2317 GHz"
          },
          {
            "name": "memory::TimezoneFinderL::steady_heap",
            "value": 4.466748237609863,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 3.2317 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::init_heap",
            "value": 4.535082817077637,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 3.2317 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::steady_heap",
            "value": 4.543943405151367,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 3.2317 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::init_heap",
            "value": 65.54545593261719,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 3.2317 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::steady_heap",
            "value": 65.55424499511719,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 3.2317 GHz"
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
          "id": "1d2d6eba2688e7fd291f2080deed20718154b400",
          "message": "Merge pull request #546 from jannikmi/ci/benchmark-comment-reposted\n\nPost the benchmark comparison anew instead of editing it in place",
          "timestamp": "2026-08-22T11:58:53+02:00",
          "tree_id": "fa76d10a56b7341b18aa9eb6c2236d62d77b3517",
          "url": "https://github.com/jannikmi/timezonefinder/commit/1d2d6eba2688e7fd291f2080deed20718154b400"
        },
        "date": 1787392810339,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "memory::TimezoneFinderL::init_heap",
            "value": 4.4665937423706055,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on INTEL(R) XEON(R) PLATINUM 8573C @ 2.8990 GHz"
          },
          {
            "name": "memory::TimezoneFinderL::steady_heap",
            "value": 4.466756820678711,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on INTEL(R) XEON(R) PLATINUM 8573C @ 2.8990 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::init_heap",
            "value": 4.535087585449219,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on INTEL(R) XEON(R) PLATINUM 8573C @ 2.8990 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::steady_heap",
            "value": 4.5439043045043945,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on INTEL(R) XEON(R) PLATINUM 8573C @ 2.8990 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::init_heap",
            "value": 65.54558753967285,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on INTEL(R) XEON(R) PLATINUM 8573C @ 2.8990 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::steady_heap",
            "value": 65.55425548553467,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on INTEL(R) XEON(R) PLATINUM 8573C @ 2.8990 GHz"
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
          "id": "f80c89b11da6bcc5239b0eadafbd978351e88787",
          "message": "Merge pull request #548 from jannikmi/fix/cli-stderr-line-count-assertion\n\nAssert the CLI's one error, not the interpreter's stderr line count",
          "timestamp": "2026-08-22T13:00:32+02:00",
          "tree_id": "2d5da4b736234d1b6b605aec7f1aa6813eff8e59",
          "url": "https://github.com/jannikmi/timezonefinder/commit/f80c89b11da6bcc5239b0eadafbd978351e88787"
        },
        "date": 1787396517020,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "memory::TimezoneFinderL::init_heap",
            "value": 4.466641426086426,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 3.2435 GHz"
          },
          {
            "name": "memory::TimezoneFinderL::steady_heap",
            "value": 4.466804504394531,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 3.2435 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::init_heap",
            "value": 4.53516960144043,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 3.2435 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::steady_heap",
            "value": 4.543943405151367,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 3.2435 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::init_heap",
            "value": 65.54549884796143,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 3.2435 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::steady_heap",
            "value": 65.55421543121338,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 3.2435 GHz"
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
          "id": "f8b5df9801fd47a6657faf92262e7518cd17d89c",
          "message": "Merge pull request #547 from jannikmi/skills/maintainer-decisions",
          "timestamp": "2026-08-22T22:08:28+02:00",
          "tree_id": "bc817356b62d5a6ec7dd72db555fb208fd225906",
          "url": "https://github.com/jannikmi/timezonefinder/commit/f8b5df9801fd47a6657faf92262e7518cd17d89c"
        },
        "date": 1787429373118,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "memory::TimezoneFinderL::init_heap",
            "value": 4.466641426086426,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on INTEL(R) XEON(R) PLATINUM 8573C @ 3.5531 GHz"
          },
          {
            "name": "memory::TimezoneFinderL::steady_heap",
            "value": 4.466804504394531,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on INTEL(R) XEON(R) PLATINUM 8573C @ 3.5531 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::init_heap",
            "value": 4.534821510314941,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on INTEL(R) XEON(R) PLATINUM 8573C @ 3.5531 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::steady_heap",
            "value": 4.54355525970459,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on INTEL(R) XEON(R) PLATINUM 8573C @ 3.5531 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::init_heap",
            "value": 65.54545402526855,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on INTEL(R) XEON(R) PLATINUM 8573C @ 3.5531 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::steady_heap",
            "value": 65.5542573928833,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on INTEL(R) XEON(R) PLATINUM 8573C @ 3.5531 GHz"
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
          "id": "bd65e3a8def9b79cfaa652bc8d53e87f56dde0b0",
          "message": "Merge pull request #550 from jannikmi/bench/tzfpy-comparison\n\nMeasure the tzfpy comparison instead of asserting it",
          "timestamp": "2026-08-23T22:30:35+02:00",
          "tree_id": "83649ae1d67c370588fd6f300cf84c402ce6846c",
          "url": "https://github.com/jannikmi/timezonefinder/commit/bd65e3a8def9b79cfaa652bc8d53e87f56dde0b0"
        },
        "date": 1787517183029,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "memory::TimezoneFinderL::init_heap",
            "value": 1.0077552795410156,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on INTEL(R) XEON(R) PLATINUM 8573C @ 3.0013 GHz"
          },
          {
            "name": "memory::TimezoneFinderL::steady_heap",
            "value": 1.0079336166381836,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on INTEL(R) XEON(R) PLATINUM 8573C @ 3.0013 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::init_heap",
            "value": 1.0761327743530273,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on INTEL(R) XEON(R) PLATINUM 8573C @ 3.0013 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::steady_heap",
            "value": 1.0849943161010742,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on INTEL(R) XEON(R) PLATINUM 8573C @ 3.0013 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::init_heap",
            "value": 62.08662986755371,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on INTEL(R) XEON(R) PLATINUM 8573C @ 3.0013 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::steady_heap",
            "value": 62.095346450805664,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on INTEL(R) XEON(R) PLATINUM 8573C @ 3.0013 GHz"
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
          "id": "ddc207e72ea1b1b54d7ec390ca63ee172e0ae938",
          "message": "Merge pull request #551 from jannikmi/improve/bug-1-negative-ids\n\nReject a negative id instead of counting from the end",
          "timestamp": "2026-08-23T23:16:43+02:00",
          "tree_id": "e5838ba04a2d08af3aa81be00410df4517f4deb4",
          "url": "https://github.com/jannikmi/timezonefinder/commit/ddc207e72ea1b1b54d7ec390ca63ee172e0ae938"
        },
        "date": 1787519856756,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "memory::TimezoneFinderL::init_heap",
            "value": 1.0077552795410156,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 3.2425 GHz"
          },
          {
            "name": "memory::TimezoneFinderL::steady_heap",
            "value": 1.0079336166381836,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 3.2425 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::init_heap",
            "value": 1.0762577056884766,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 3.2425 GHz"
          },
          {
            "name": "memory::TimezoneFinder[file_based]::steady_heap",
            "value": 1.085078239440918,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 3.2425 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::init_heap",
            "value": 62.08636665344238,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 3.2425 GHz"
          },
          {
            "name": "memory::TimezoneFinder[in_memory]::steady_heap",
            "value": 62.0950870513916,
            "range": "± 0",
            "unit": "MiB",
            "extra": "min of 3 run(s) on AMD EPYC 7763 64-Core Processor @ 3.2425 GHz"
          }
        ]
      }
    ]
  }
}