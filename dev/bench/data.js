window.BENCHMARK_DATA = {
  "lastUpdate": 1786109798139,
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
      }
    ]
  }
}