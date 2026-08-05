window.BENCHMARK_DATA = {
  "lastUpdate": 1785888683563,
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
      }
    ]
  }
}