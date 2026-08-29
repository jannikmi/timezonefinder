# Public API, compatibility, and runtime loading decisions

Do not re-propose these settled or refused options without new evidence.

- **Border proximity — conditional on publicly voiced user interest.** See GH-505. The demand
  signal comes first, because it is an L-sized permanent maintenance surface justified by a
  hypothesis about who wants it.

- **Breaking API changes are batched into one major, never trickled out.** Settled 2026-08-21,
  while deciding API-1 and API-2. Each is individually small — a dead parameter, a wider-than-stated
  attribute surface — and each on its own would be a major version whose entire content is one
  removal nobody asked for. Every *known* breaking change ships together instead: API-1 (drop
  `in_memory` from the base and from `TimezoneFinderL`), API-2 (PEP 562 submodule access), and any
  further removal found before that release. Consequences worth stating, because they are what the
  rule costs: an entry can be *decided* and still not eligible for a pass, so decided-and-held is a
  real state the ranking has to show; API-2 goes first within the major, since it decides how much
  surface API-1 touches; and additive work that does not need a major (GH-502) should still
  ride the same release, so the API documentation is rewritten once rather than three times. The
  public API must not break between minors — that constraint is unchanged; this is about not
  spending majors one removal at a time.

- **A free-threaded wheel tag is not a GIL declaration.** Settled 2026-08-21 while scoping GH-364,
  and recorded because the wrong version of this was written into that entry a day earlier and read
  as settled. A `cp313t`/`cp314t` wheel says a package *builds* on a free-threaded interpreter; only
  a `Py_mod_gil` declaration says it will not force the GIL back on. `h3` 4.5.0 ships the wheel and
  omits the declaration, so `import timezonefinder` re-enables the GIL today — which the wheel
  survey missed entirely. The check that means anything is `sys._is_gil_enabled()` after the import,
  on a real free-threaded build; anything derived from PyPI metadata alone is a necessary condition
  presented as a sufficient one.

- **Data serving an optional path is cached lazily, not loaded at construction.** Settled
  2026-08-20 for BIG-1. Construction is not a free place to put work here: it is a tracked benchmark
  (`docs/benchmark_results_initialization.rst`), and the documented one-instance-per-thread pattern
  multiplies whatever it costs by the thread count — so an eager load charges the whole user base
  for something only some methods read. `zone_positions` is read by `certain_timezone_at` and
  `get_geometry` and by nothing on the `timezone_at` path, which makes it exactly that case.
  Rejected: reading it eagerly in `__init__`, which is otherwise attractive because the array is a
  kilobyte and eager loading opens no mapping. The rule pairs with the validation decision below —
  both are about **not making every construction pay for a question only some callers ask**, which
  is also why data-directory validation is opt-in.

- **The other side of that rule, and it is not symmetric: data the object's primary method
  certainly needs is built eagerly, and cheapness is not what decides it.** Settled 2026-08-21 with
  the coordinate offset table. It was briefly argued the lazy way — it read as the same trade at a
  larger size — and that was wrong twice over. The table is not optional-path data: a
  `TimezoneFinder` exists to test points against polygons, so every query not answered outright by
  a unique-zone shortcut cell reaches it, and there is no population of callers who never do.
  Deferring it would move a certain cost to the first query instead of avoiding one. And it would
  buy that with two things worth more than the milliseconds: an `is None` branch per fetch on the
  hot path, and **a write to `self` from a lookup** — which is what a shared instance being safe
  for concurrent reads currently rests on (GH-364's finding (c): every attribute assigned in
  `__init__`/`cleanup`, nothing on the lookup path mutating state). A lazy cache would be the first
  thing to break that, silently and only under load. Rejected, therefore: making it lazy *because*
  it costs something, and equally, defending it as eager *because* it is cheap — the derivation
  cost decides how the table is derived, never whether to defer it.
  `tests/test_coord_offset_table.py::test_a_lookup_mutates_no_accessor_state` pins the invariant.
  The separate lesson that work does carry for the rule above: check whether a cheaper thing than
  the object can be cached before paying for a cache policy at all — caching integers rather than
  views is what removed its pinning half.

- **An id-taking interface validates at the public edge, never on the internal path.** Settled
  2026-08-20 for the four public methods that take an id — `zone_id_of`, `zone_ids_of`,
  `zone_name_from_id` and `zone_name_from_boundary_id` — which indexed a list or array directly and
  so read a negative id as a valid index from the end: `zone_name_from_id(-1)` answered
  `Etc/GMT+12` rather than raising. Guarding in place was measured at ~10 ns, order 1 % of a
  unique-shortcut query, on a method called once per successful `timezone_at`; guarding the public
  methods and routing the internal callers through unchecked private accessors costs about nine more
  lines and nothing per query. **Implemented as decided**, 2026-08-23. Rejected: guarding in place everywhere (pays the check on a path that cannot produce a bad
  id), and documenting the behaviour instead (leaves a public method answering a bad question with a
  real timezone name). The generalisable half is the placement rule, and it is the same shape as the
  validation decision above: a check belongs where the untrusted value enters, not where the
  settled one is used. It binds any future id-taking or sentinel-returning API, and the batch
  lookups are the case that exercised it: `NO_ZONE_ID` is `-1`, which is safe to hand out only
  because the public id-taking methods now refuse it.

- **Ask what the originating issue actually asked before designing for its audience.** Settled 2026-08-24 when GH-428 dropped `update-data`.
  That entry recommended a `convert` subcommand twice, for "people compiling custom data who have no supported entry point" — an audience that appears in neither #428 nor the #363 it inherits from.
  #363 wanted the *full official dataset* rather than the reduced one, which `timezonefinder-data` now ships.
  The generalisable half: an item restated often enough starts being designed against the restatement, and the cheapest correction is reading the first report.
  It cost one issue view here and reversed a recommendation that had survived two rounds.
