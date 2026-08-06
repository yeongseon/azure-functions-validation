# PRD - azure-functions-validation

## Overview

`azure-functions-validation` is a **decorator-first request-and-response validation layer**
for the Azure Functions Python v2 programming model.

It targets HTTP-triggered `func.FunctionApp()` handlers that want typed parsing, structured
error responses, and response contract checking — without pulling in a full web framework.

## Problem Statement

Azure Functions Python HTTP handlers often repeat the same parsing and validation logic:

- parsing JSON bodies
- extracting query, path, and header values
- validating request shapes manually
- serializing and validating response payloads inconsistently

This creates duplication, uneven error handling, and drift between intended and actual API contracts.

## Goals

- Provide a decorator-first API for request and response validation.
- Normalize validation errors into predictable response payloads.
- Support typed request sources such as body, query, path, and headers.
- Keep the package small, focused, and independently useful.

## Non-Goals

1. Building a full web framework.
2. Replacing Azure Functions routing or hosting behavior.
3. Owning OpenAPI specification generation or schema rendering.
4. Supporting the legacy `function.json`-based Python v1 model.
5. Providing global mutable state such as error-handler registries.
6. Owning contract-testing utilities — that responsibility belongs to test tooling.

## Primary Users

- Azure Functions Python API developers
- Teams that want consistent input and output contracts
- Users who need structured validation without a full web framework

## Validation Pipeline

A decorated handler runs through the following stages:

```
HttpRequest
  │
  ├─ 1. Resolve HttpRequest from args/kwargs
  ├─ 2. Parse & validate body   (→ 400 on bad JSON, 422 on schema violation)
  ├─ 3. Parse & validate query  (→ 422)
  ├─ 4. Parse & validate path   (→ 422)
  ├─ 5. Parse & validate headers(→ 422)
  ├─ 6. Call handler with typed inputs
  └─ 7. Validate & serialize response (→ 500 on contract violation)
```

## Error Model

All validation errors use a **stable** `{"detail": [...]}` envelope:

```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "value is not a valid email address",
      "type": "value_error"
    }
  ],
  "error_format_version": 1
}
```

Each `loc` is prefixed with its input source (`body`, `query`, `path`, or
`headers`) so collisions across sources stay distinguishable. Pass
`legacy_loc=True` to `validate_http` for one release to opt out of the source
prefix during migration.

| HTTP status | Trigger |
|---|---|
| 400 | Malformed JSON body |
| 422 | Schema validation failure (body, query, path, headers) |
| 500 | Response model contract violation |

This format follows FastAPI / Pydantic conventions for broad tooling compatibility.

Every default envelope carries a top-level `error_format_version` integer (an
additive, backwards-compatible field). Downstream consumers may pin against it;
it is bumped only when the default error-response schema changes incompatibly.
Consumers validating responses must allow unknown/additional properties. Custom
`ErrorFormatter` output is never stamped — callers own that shape entirely.

## Compatibility

| Dependency | Supported versions |
|---|---|
| Python | ≥ 3.10 |
| azure-functions | ≥ 1.17 |
| Pydantic | ≥ 2.0 |

## Core Use Cases

- Validate a JSON request body into a typed model
- Validate query, path, or header models
- Validate and serialize a typed response
- Return structured validation errors for invalid input

## Success Criteria

- Representative examples pass smoke tests in CI
- Validation error payloads remain stable across releases
- Runtime validation behavior stays aligned with tests and documentation
- `make check-all` is the minimum merge gate


## Example-First Design

### Philosophy

Small-ecosystem libraries live or die by the quality of their examples.
If a developer cannot go from `pip install` to a working handler in under five minutes,
the library has already lost. `azure-functions-validation` treats runnable examples as a
first-class deliverable, not an afterthought.

### Quick Start (Hello World)

The shortest path from zero to validated endpoint:

```python
import azure.functions as func
from pydantic import BaseModel

from azure_functions_validation import validate_http


class Greeting(BaseModel):
    name: str


app = func.FunctionApp()


@app.function_name(name="hello")
@app.route(route="hello", methods=["POST"])
@validate_http(body=Greeting)
def hello(req: func.HttpRequest, body: Greeting) -> dict:
    return {"message": f"Hello {body.name}"}
```

Invalid input returns a structured `422` response automatically:

```json
{
  "detail": [
    {
      "loc": ["body", "name"],
      "msg": "Field required",
      "type": "missing"
    }
  ]
}
```

### Why Examples Matter

1. **Lower entry barrier.** A working Hello World in the PRD and README lets developers
   evaluate the library before reading any reference documentation.
2. **AI agent discoverability.** Tools like GitHub Copilot, Cursor, and Claude Code recommend
   libraries based on README, PRD, and example content. Rich examples increase the chance
   that AI agents surface `azure-functions-validation` for relevant prompts.
3. **Cookbook role.** For niche ecosystems, `examples/` and `docs/` often serve as the primary
   learning material. Every new pattern should ship with a runnable example project.
4. **Proven approach.** FastAPI, LangChain, SQLAlchemy, and Pandas all achieved early adoption
   through extensive, copy-paste-friendly examples.

### Examples Inventory

| Role | Path | Pattern |
|---|---|---|
| Representative | `examples/hello_validation` | Minimal body validation and typed response |
| Complex | `examples/profile_validation` | Query, path, header, and response model |
| Focused | `examples/async_validation` | Async handler with typed models |
| Focused | `examples/custom_error_handler` | Custom error formatting |
| Comprehensive | `examples/crud_api` | Full CRUD with body, query, path, list response |

All examples are smoke-tested in CI. New features must ship with a corresponding example
or an extension to an existing one.
