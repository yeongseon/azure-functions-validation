# `endpoint` metadata namespace — SPEC

Status: **v1** · Owner namespace: `endpoint` · Issue: [#271](https://github.com/yeongseon/azure-functions-validation-python/issues/271) · Umbrella: [#270](https://github.com/yeongseon/azure-functions-validation-python/issues/270)

> **Localization:** This specification is a canonical, English-only technical
> document (the machine-readable source of truth is the JSON Schema it links to).
> It is intentionally **not** part of the translated README set
> (`README.ko.md`, `README.ja.md`, `README.zh-CN.md`) and requires no translation
> updates when it changes.

## Purpose

The Azure Functions Python DX Toolkit lets sibling packages cooperate without
importing one another. Decorators attach a single dict to the wrapped handler
under the conventional attribute `_azure_functions_metadata`, keyed by a
package-owned **namespace** string. Consumers discover metadata by reading that
attribute — never by importing the producer.

The `endpoint` namespace is the **shared, OpenAPI-ready contract**. Producer
packages (`azure-functions-validation`, `azure-functions-langgraph`, …) write
it; the consumer (`azure-functions-openapi`) reads it and derives the OpenAPI
spec directly, instead of reconstructing OpenAPI shapes per producer.

The JSON Schema in
[`src/azure_functions_validation/schemas/endpoint.schema.json`](../src/azure_functions_validation/schemas/endpoint.schema.json)
is the **single source of truth** for the payload shape. Every producer
validates its emitted payload against this schema in tests so the dict cannot
drift.

## Distribution & sync

- The schema is a **public** subpackage
  (`azure_functions_validation.schemas`), shipped as package data and loaded
  via `importlib.resources`. No new runtime dependency is introduced;
  `jsonschema` is required only to *validate* payloads and is test-only.
- The contract is **replicated** across packages, not shared through a runtime
  dependency (same philosophy as the vendored `_metadata_helpers.py`).
- Drift is caught mechanically: `endpoint.schema.sha256` pins the file digest
  and `make check-schema-hash` (wired into `make check-all`) fails on any
  change. When you intentionally change the schema, update the pin and
  hand-sync sibling packages in the same release train.

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
    "422": { "schema": { /* validation-error envelope */ } } // present when request validation applies
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

### The `422` validation-error response

When the operation performs request validation — i.e. any of `body`, `query`,
`path`, or `headers` is a Pydantic model — producers MUST add a `"422"` entry to
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


## Canonicalization rules (producers MUST follow)

Producers generate embedded schemas from Pydantic models with **exactly** these
settings so output is stable and consumer-mergeable:

| Rule | Value |
| --- | --- |
| Alias handling | `by_alias=True` |
| Request schema mode | `mode='validation'` |
| Response schema mode | `mode='serialization'` |
| Ref template | Pydantic default `#/$defs/{model}` |
| `$defs` | **left UNRESOLVED** — the consumer hoists them to `components/schemas` |
| Generator class | Pydantic default `GenerateJsonSchema` (pin explicitly if customized; Pydantic minor bumps can change output) |
| `request_body_required` | `True` unless every field of the body model has a default |

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
- On a bump, update the schema, its SHA-256 pin, this spec, and every sibling
  producer/consumer in the same release train.

## API

```python
from azure_functions_validation.schemas import (
    ENDPOINT_METADATA_VERSION,      # 1
    load_endpoint_schema,           # -> dict (fresh copy)
    endpoint_schema_sha256,         # -> hex digest of shipped bytes
    assert_defs_present_if_ref_used # structural guard, raises ValueError
)
```
