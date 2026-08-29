# Public API and compatibility contract

- Before adding any version-gated import, `__future__` feature, or compatibility shim, check `requires-python` and confirm the feature actually needs it on the minimum supported version.
- Keep `__all__` in `__init__.py` files: they define the declared public surface. No test asserts their contents directly; emptying the top-level one only fails incidentally during collection.

- External: Avoid breaking changes to public APIs unless absolutely necessary. If a change is required, provide a clear migration path and update all relevant documentation. A major version bump is warranted for breaking changes.
- Internal: When modifying internal assets like code, data formats or binary assets the changes must NOT be backward compatible. The code is packaged and versioned together and must only work with the exact version of the data files it was built with.
- Before writing compatibility code anyway, check that the thing you would be compatible with was ever released — `git merge-base --is-ancestor <commit> <latest tag>`. This is the step that is easy to skip: on `master`, a format marker or interface introduced since the last tag looks exactly like one that has shipped, so a fallback written for "data compiled by an older release" can read as necessary while no such data exists. The cost is not only an unreachable branch. Guarding an unreleased format version rewrote a 63 MB binary for one changed byte, and the branch itself sat on the lookup path, tested per query for a case that could not arise.
