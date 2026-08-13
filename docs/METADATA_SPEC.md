# `endpoint` metadata convention — `azure-functions-validation` conformance

Status: **v1** · Owner namespace: `endpoint` · Issue: [#271](https://github.com/yeongseon/azure-functions-validation-python/issues/271) · Umbrella: [#270](https://github.com/yeongseon/azure-functions-validation-python/issues/270)

> **Canonical contract:** The neutral, canonical home for the `endpoint`
> metadata contract is
> [`azure-functions-python-dx` › `docs/endpoint-contract.md`](https://github.com/yeongseon/azure-functions-python-dx/blob/main/docs/endpoint-contract.md).
> This document is **not** that source of truth — it is a **convention**, not a
> centralized binding spec. What follows describes how `azure-functions-validation`
> conforms to the shared convention: its own emitted payload, canonicalization
> rules, and internal (non-published) conformance artifacts.

> **Localization:** This document is an English-only technical document
> (the JSON Schema it links to is an internal conformance artifact of this
> package, not a source of truth other packages bind to).
> It is intentionally **not** part of the translated README set
> (`README.ko.md`, `README.ja.md`, `README.zh-CN.md`) and requires no translation
> updates when it changes.

## Purpose

The Azure Functions Python DX Toolkit lets sibling packages cooperate without
importing one another. Decorators attach a single dict to the wrapped handler
under the conventional attribute `_azure_functions_metadata`, keyed by a
package-owned **namespace** string. Consumers discover metadata by reading that
attribute — never by importing the producer.

The `endpoint` namespace is a **versioned, OpenAPI-ready metadata convention**.
Producer packages (`azure-functions-validation`, `azure-functions-langgraph`, …)
write it; the consumer (`azure-functions-openapi`) reads it and derives the
OpenAPI spec directly, instead of reconstructing OpenAPI shapes per producer.

The JSON Schema in
[`src/azure_functions_validation/schemas/endpoint.schema.json`](https://github.com/yeongseon/azure-functions-validation-python/blob/main/src/azure_functions_validation/schemas/endpoint.schema.json)
is an **internal conformance artifact of `azure-functions-validation`**: this
package validates its own emitted payload against it in tests. It is not
published, dereferenced, or shared as a runtime contract — each package owns
its own local conformance tests against the versioned dict convention.

## Distribution & sync

- The schema ships as package data inside
  `azure_functions_validation.schemas`, loaded via `importlib.resources`. No
  new runtime dependency is introduced; `jsonschema` is required only to
  *validate* payloads and is test-only.
- The schema is an **internal conformance artifact** of this package, not a
  shared/hosted contract. Other packages that emit the `endpoint` namespace
  own their own local conformance tests against the same versioned dict
  convention (same philosophy as the vendored `_metadata_helpers.py`).
- Local drift is caught mechanically: `endpoint.schema.sha256` pins the file
  digest and `make check-schema-hash` (wired into `make check-all`) fails on
  any change. When you intentionally change the schema, update the pin and
  bump the `version` field if the change is breaking.

## Payload shape (version 1)

```jsonc
{
  "version": 1,                     // const 1; consumers WARN (not fail) on unknown
  "request_body": { /* JSON Schema */ } | null,
  "request_body_required": true,    // default true unless every body field has a default
  "parameters": [                   // OpenAPI parameter objects (query/path/header)
    { "name": "id", "in": "path", "required": true, "schema": { /* JSON Schema */ } }
  ],
  "responses": {                    // status-code (string) -> response object; or null
    "200": { "schema": { /* JSON Schema */ } },  // "description" optional; producer omits it in v1
    "422": { "schema": { /* validation-error envelope */ } } // added by this producer when request validation applies
  } | null,
  "summary": "…",                   // optional
  "description": "…",               // optional
  "tags": ["users"],                // optional
  "security": [ { /* requirement */ } ] // optional
}
```

### `path` and `method` are intentionally OMITTED

The Azure Functions route binding (`@app.route(route=…, methods=…)`) is the
single source of truth for path and HTTP methods. The consumer derives them at
scan time from the binding, so producers must not duplicate them here.

### `responses` describes the endpoint's actual runtime responses

`responses` is a **generic** part of the convention: a producer maps each HTTP
status code it can return to a response object carrying that response's JSON
Schema, or emits `null` when it has nothing to describe. What those responses
*are* is producer-specific. A non-Pydantic producer, or one that only emits
success responses, is under no obligation to document a `422` body — it simply
describes whatever its runtime actually returns.

## azure-functions-validation implementation

The rest of this document describes rules that are **specific to
`azure-functions-validation`** — how *this* producer generates its payload. They
are not obligations on the generic `endpoint` convention above; other producers
of the namespace implement their own equivalents.

### The `422` validation-error response (validation-specific)

`@validate_http` returns a `422` on request-validation failure, so when the
operation performs request validation — i.e. any of `body`, `query`, `path`, or
`headers` is a Pydantic model — **this producer** adds a `"422"` entry to
`responses` describing the standardized validation-error body the runtime
returns on invalid input:

```jsonc
{
  "type": "object",
  "required": ["detail"],
  "properties": {
    "detail": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["loc", "msg", "type"],
        "properties": {
          "loc": { "type": "array", "items": { "type": ["string", "integer"] } },
          "msg": { "type": "string" },
          "type": { "type": "string" }
        }
      }
    }
  }
}
```

The `422` schema is **self-contained** (no `$ref`, no `$defs`). It is emitted
independently of `response_model`: an operation with a request model but no
`response_model` still carries a `responses` map of just `{"422": …}`. When
there is no request model, no `422` is emitted. This documents the default
`{"detail": [...]}` envelope only; a custom `ErrorFormatter` may change the
runtime body without changing this schema. Adding `422` is an additive change
and does not bump the namespace version.


## Canonicalization rules (validation-specific)

`azure-functions-validation` generates its embedded schemas from Pydantic models
with **exactly** these settings so output is stable and consumer-mergeable. This
is how *this* producer happens to canonicalize; the generic convention only
requires plain JSON Schema with `$defs` left unresolved:

| Rule | Value |
| --- | --- |
| Alias handling | `by_alias=True` |
| Request schema mode | `mode='validation'` |
| Response schema mode | `mode='serialization'` |
| Ref template | Pydantic default `#/$defs/{model}` |
| `$defs` | **left UNRESOLVED** — the consumer hoists them to `components/schemas` |
| Generator class | Pydantic default `GenerateJsonSchema` (pin explicitly if customized; Pydantic minor bumps can change output) |
| `request_body_required` | `True` unless every field of the body model has a default |

The response-schema mode above applies to **Pydantic-derived response-model
schemas**. The `422` validation-error response schema is produced directly
(not from a Pydantic model) and is unaffected by these settings.

### Structural rule: `$defs` if `$ref`

Any embedded schema that contains a `$ref` **anywhere** MUST carry a top-level
`$defs` mapping. This guards against a producer pre-resolving (or dropping)
definitions, which would break the consumer's hoisting and make it no longer
the sole `$ref`-collision authority. This rule is not expressible in JSON Schema
alone and is enforced by
`azure_functions_validation.schemas.assert_defs_present_if_ref_used`.

## Consumer discipline

- Consumers MUST read the payload via an explicit allowlist / typed reader —
  never `**payload`-splat into a call. New optional keys must be additively
  ignorable.
- Consumers MUST treat an unknown `version` as a warning and fall back to their
  prior discovery path, not raise.
- Consumers remain the sole authority for `$ref` collision resolution; embedded
  `$defs` are inputs, not final `components/schemas`.

## Versioning policy

- `version` starts at `1`. Bump only on a **breaking** payload change.
- Additive, optional fields do **not** bump the version.
- On a bump, update the schema, its SHA-256 pin, and this spec, and coordinate
  producer/consumer support as needed before shipping the breaking version.
  Packages release independently — there is no coordinated release train.

## Internal helpers (not a public API)

This package ships a few schema helpers that it uses **for its own conformance
tests only**. They are intentionally **not** a supported cross-package public
API: sibling producers/consumers of the `endpoint` namespace MUST NOT import
them, and they may change or move without a deprecation cycle. Other packages
should implement their own local conformance checks against the versioned dict
convention described above (the same philosophy as the vendored
`_metadata_helpers.py`).

For reference, the internal helpers this package uses in its own test suite are:

- `ENDPOINT_METADATA_VERSION` — the current namespace version (`1`).
- `load_endpoint_schema()` — returns a fresh copy of the shipped JSON Schema.
- `endpoint_schema_sha256()` — hex digest of the shipped schema bytes.
- `assert_defs_present_if_ref_used()` — structural guard used in tests.

> These names are documented here to explain how this package validates itself,
> not to encourage `from azure_functions_validation.schemas import ...` in other
> packages. Treat them as internal.
