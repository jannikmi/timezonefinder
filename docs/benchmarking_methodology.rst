.. _benchmarking_methodology:

=========================
Benchmarking Methodology
=========================

``timezonefinder`` publishes performance pages, a `trend chart
<https://jannikmi.github.io/timezonefinder/dev/bench/>`__ of every push to ``master``, and a
comparison on every pull request. This page explains how to read those numbers. The scripts named
below hold the details.


What is measured
----------------

Each benchmark times **one pass over a fixed batch of query points**, not a single call, so every
round does identical work and the spread between rounds is noise rather than a difference in what was
measured. The points are committed fixtures (``tests/fixtures/benchmarks/``), drawn uniformly per
unit of surface area - the distribution of real queries, not one that oversamples the poles - and
split into classes:

- **random** - uniformly random points, the representative mix and the headline figure;
- **on land** - the same, restricted to land;
- **unique shortcut** - points whose shortcut cell holds one zone, answered without any geometry;
- **ambiguous shortcut** - points whose cell holds several zones, which need point-in-polygon tests
  and are by far the most expensive class.

A random workload is mostly cheap queries with an expensive minority, so the per-class figures show
what the headline averages over. The batch figures cannot show a tail at all; the per-query
distribution (p50 to p99.9) on :doc:`benchmark_results_timezonefinding` is measured separately for
that, by ``make latency``.

All published numbers use the C extension with memory-mapped data - what a plain
``pip install timezonefinder`` runs - and every measuring target asserts that path before it starts.


Why CI numbers are noisy
------------------------

GitHub's ``ubuntu-latest`` runners pin the operating system image, not the hardware. Runs land on
different CPU models at different clocks, and the same code can measure tens of percent apart on two
runs. So:

- **Every page and every chart point names the CPU it was measured on.** Check it first when a
  number jumps.
- **A pull request is measured against its own merge base, in the same job, on the same machine**,
  never against a stored baseline. The base is measured before and after the head, so a runner that
  drifts during the job shows up in the base's own spread rather than as a code change.
- **The tracked value is the fastest round (``min``)**, because every round does the same work and
  the fastest one is the least disturbed by whatever else the shared machine was doing. The trend
  chart shows it as lookups per second.
- **Do not compare a local run with a CI run**, or two unpaired CI runs with each other: different
  machines, different numbers.


How to read a comparison
------------------------

The pull request comment lists each tracked benchmark with the change from base to head, under two
estimators: the fastest round, and the median beside it. A row is flagged when it moves by more than
10 %, and marked **unresolved** when the two estimators disagree - read that as "no demonstrable
difference". A change of a few percent is within one machine's own jitter.

The trend chart alerts only on very large changes, because consecutive points come from different
machines; the paired pull request comparison is where a regression is caught. Neither one fails a
build.


Comparing two implementations of one stage
------------------------------------------

Deciding between two implementations of the same step is a different measurement, and an easy one
to get wrong. ``benchmarks/candidate_comparison.py`` does it the way that holds up:

- time the **whole public call**, not the step in isolation, since two implementations rarely split
  the work at the same place;
- **alternate which candidate runs first** in each round, so neither gets a cache warmed by the
  other;
- **draw the inputs at random**, as real queries arrive, rather than in an order the data structure
  favours;
- report the ratio of the fastest rounds **and** how many rounds each candidate won, and believe a
  difference only when both agree.

Two implementations that cannot share one process, such as the Numba and pure-Python kernels, are
each compared against the C extension in their own environment instead of against each other; see
:doc:`benchmark_results_acceleration_paths`.


Batch size: where batching pays
-------------------------------

:doc:`benchmark_results_batch_break_even` repeats that paired comparison at a range of batch sizes,
the batched call against a loop of single calls on the same points:

- Every batch size answers about the same number of points per round, so the sizes are comparable.
  The largest sizes answer more, because each round still needs several calls.
- **Where batching starts paying** is given as a range between two measured sizes. A ladder of sizes
  cannot locate it more precisely, and the sizes inside that range show no clear winner by
  definition.
- **Where it stops improving** is the smallest size after which no larger one is more than 5 %
  faster per point. Very large batches can get slower again once they outgrow the CPU cache, and the
  page says where. This answer compares absolute times across batch sizes, so the page only states it
  when the single-call loop - which does identical work at every size - stayed steady across the
  run.

Both answers depend on the machine and on how clustered the coordinates are. Run
``scripts/measure_batch_break_even.py --points your.csv`` to get them for your own data.


Calibrating the shortcut-ordering model
---------------------------------------

When a point falls into a cell shared by several zones, ``timezone_at`` tests the candidate polygons
in turn and stops at the first match. Candidates are reordered only where that cannot change the
answer, so the order affects how much work a lookup does, never what it returns. The order is chosen
when the data is built, by a cost model of how often each candidate is reached and what testing it
costs; building the data never times the machine, so the order is the same wherever it is built.

``make shortcut-calibration`` checks that model against measured timings. It fits the per-step costs
on part of the cells, scores the prediction on the rest, confirms that a refitted order returns
identical answers, and times complete lookups under both orders. The latest run and the decision
taken on it are kept in `benchmarks/shortcut_ordering_model.json
<https://github.com/jannikmi/timezonefinder/blob/master/benchmarks/shortcut_ordering_model.json>`__;
fitted costs change the shipped order only through a reviewed change and a data release.


Memory
------

Memory is measured by ``scripts/measure_memory.py``, each configuration in a fresh process and as a
difference from a process that has only imported the package. Two figures are reported per
checkpoint: the **heap** (Python and NumPy allocations) and the **resident set**, which also counts
memory-mapped pages. With the default memory-mapped mode the heap stays small while the resident set
grows as lookups touch the data, which is why there is both an after-construction and an
after-workload checkpoint. Only the heap is charted, since the resident set depends on the machine's
memory pressure. See :doc:`benchmark_results_memory`.


Comparing against another package
---------------------------------

:doc:`benchmark_results_vs_tzfpy` compares against `tzfpy <https://github.com/ringsaturn/tzfpy>`__
on the same machine, in the same process and on the same query points, each package called through
its own API. Published figures from two projects come from different machines and workloads, so they
cannot be compared directly.

Startup is measured as the time to the **first answer** in a fresh process, not the time to
construct a finder, because the two packages do their loading at different moments. The comparison
is not on the trend chart, since the other package releases on its own schedule, and it says nothing
about which package's answers are correct.


Running the benchmarks yourself
-------------------------------

``make speedtest`` runs a quick subset, ``make benchmarks`` the full suite, ``make latency`` the
per-query distribution, ``make memory`` the footprint and ``make batch-break-even`` the batch-size
sweep. Your numbers describe your machine; compare them with each other, not with the published
pages.
