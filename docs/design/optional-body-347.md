# Design note: optional request body is an explicit opt-in (issue #347)

Status: **Accepted** · Scope: `azure-functions-validation` · Issue:
[#347](https://github.com/yeongseon/azure-functions-validation-python/issues/347)

> This is a durable design decision, not a task. It exists so the decision below
> is **not re-litigated** every time someone notices that a body model with only
> optional fields still reports `request_body_required: true`.

## Context

`@validate_http(body=Model)` installs a runtime adapter that **unconditionally
rejects an empty request body with a `422`** whenever a body model is
configured — regardless of whether every field on that model is optional. The
cross-package `endpoint` metadata (see [`METADATA_SPEC.md`](../METADATA_SPEC.md))
therefore reports:

```jsonc
"request_body_required": true   // whenever a body model is configured
```

This keeps the emitted metadata **truthful to actual runtime behavior**: a
consumer such as `azure-functions-openapi` documents the body as required
because the server really does require it.

## Decision

1. **Metadata must never lie about the runtime.** As long as the runtime returns
   `422` on an empty body when a body model is present, the metadata MUST report
   `request_body_required: true`. The metadata layer must not independently
   soften this to `false` based on field optionality — that would advertise a
   contract the server does not honor.

2. **Optional-body support, if ever added, is an explicit opt-in that ALSO
   relaxes the runtime `422`.** It is not enough to flip the metadata flag. Any
   future optional-body feature MUST:
   - be **explicitly opted into** (e.g. a dedicated decorator argument), never
     inferred from field optionality; and
   - **relax the runtime 422** in the same change, so an empty body is actually
     accepted end-to-end — keeping metadata and runtime in lockstep.

3. **Do not implement it speculatively.** Optional-body support is deferred until
   (a) the typed-query endpoint-metadata contract has stabilized, and (b) a real
   user need appears. Absent both, the current always-required behavior stands.

## Consequences

- A body model with only optional fields still reports `request_body_required:
  true`. This is intentional and correct given the runtime.
- Anyone proposing to change this must change the **runtime and the metadata
  together**, behind an explicit opt-in — not the metadata alone.

## References

- Issue [#347](https://github.com/yeongseon/azure-functions-validation-python/issues/347)
- [`docs/METADATA_SPEC.md`](../METADATA_SPEC.md) — `request_body_required` row in
  the canonicalization rules.
- `src/azure_functions_validation/_endpoint.py` — `build_endpoint_metadata`
  (the comment there points back to this note).
