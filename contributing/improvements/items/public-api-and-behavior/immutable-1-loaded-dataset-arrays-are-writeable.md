# IMMUTABLE-1 — loaded dataset arrays are writeable

- **Location:** `timezonefinder/np_binary_helpers.py`,
  `read_per_polygon_vector`; `timezonefinder/shortcut_index.py`,
  `read_shortcuts_binary`; and `timezonefinder/coord_accessors.py`,
  `FileCoordAccessor.__init__`.
- **Defect:** the finder exposes ordinary writeable arrays for polygon-to-zone ids,
  bounding boxes, hole references and most shortcut-index columns. Its mapped coordinate
  offset tables are writeable too. An accidental assignment succeeds and silently changes
  later lookup answers or redirects coordinate reads; only shortcut payloads and coordinate
  views currently reject it.
- **Fix:** freeze every array that represents loaded or derived dataset state after
  construction, including the lazy zone-name gather array. Keep builder inputs, temporary
  arrays and fresh public result arrays writeable. Replace the one test that mutates a
  loaded shortcut table with a purpose-built replacement index.
- **Trade-off:** callers lose unsupported mutation of publicly reachable implementation
  arrays in exchange for lookup state that enforces its read-only contract. Array reads,
  storage, construction shape and returned result ownership are unchanged, so there is no
  latency, memory or low-memory-mode trade.
- **Verification:** exercise both mapped and in-memory finders, enumerate every persistent
  NumPy array they retain, and prove assignment raises rather than altering state. Run the
  slow geometry and property suites because the touched loaders feed both lookup modes.
- **Status:** open — no maintainer decision or external prerequisite.
