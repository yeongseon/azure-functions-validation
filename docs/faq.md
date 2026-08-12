# FAQ

## Why does the repo use `-python` but the PyPI package does not?

The names map to three different contexts:

| Context        | Name                                |
|----------------|-------------------------------------|
| GitHub repo    | `azure-functions-validation-python` |
| PyPI package   | `azure-functions-validation`        |
| Python import  | `azure_functions_validation`        |

The GitHub repository carries the `-python` suffix to mark it as the
Python implementation of the project. The PyPI package follows the
Python ecosystem convention and is published without the suffix, so
the install command stays idiomatic:

```bash
pip install azure-functions-validation
```

The Python import name uses underscores, as required by the language:

```python
from azure_functions_validation import validate_http
```

This is intentional naming, not an inconsistency. The repo describes
*what kind of implementation this is*, while the PyPI and import names
describe *how Python users actually install and use it*.

## Can I use this without Pydantic?

Short answer: not directly.

`azure-functions-validation` is designed around Pydantic model validation and the
default `PydanticAdapter`. Your request and response schemas should be Pydantic
v2 models (or compatible typing forms for response validation).

!!! note "Advanced adapter option"
    The `adapter` parameter exists for custom integrations, but most users should
    rely on the default Pydantic behavior.

## How do I handle an optional body?

The body itself is expected to exist when `body=` or `request_model=` is set.
An empty request body returns `422`.

Recommended pattern:

1. Keep body present.
2. Make fields optional in the model.
3. Send `{}` for "no values" cases.

```python
class PatchBody(BaseModel):
    title: str | None = None
    done: bool | None = None
```

!!! warning "Empty body vs optional fields"
    Optional fields do not make the entire request body optional.

## What about file uploads?

This package validates JSON-centric request/response flows.
Multipart file upload parsing is not the primary use case.

Typical approach for file uploads:

- Handle multipart parsing in your function logic.
- Use `validate_http` for metadata endpoints or JSON envelope endpoints.

## What is the difference between `body` and `request_model`?

- `body=Model`: validates request body and injects `body` parameter. **Preferred.**
- `request_model=Model`: **deprecated** alias for `body` that injects a
  `req_model` parameter and emits a `DeprecationWarning`. Use `body=` instead.

```python
# Preferred:
@validate_http(body=CreateBody)
def a(req: func.HttpRequest, body: CreateBody) -> dict[str, str]:
    return {"name": body.name}


# Deprecated (emits DeprecationWarning):
@validate_http(request_model=CreateBody)
def b(req: func.HttpRequest, req_model: CreateBody) -> dict[str, str]:
    return {"name": req_model.name}
```

!!! warning "Do not mix"
    `request_model` cannot be combined with `body`, `query`, `path`, or `headers`.

## How do I validate multiple sources at once?

Use explicit parameters together:

```python
@validate_http(body=BodyModel, query=QueryModel, path=PathModel, headers=HeaderModel)
def handler(
    req: func.HttpRequest,
    body: BodyModel,
    query: QueryModel,
    path: PathModel,
    headers: HeaderModel,
) -> dict[str, object]:
    return {"ok": True}
```

This is ideal for endpoints that combine payload, route context, and metadata.

## Does it work with async handlers?

Yes. `@validate_http` automatically supports both `def` and `async def`.

```python
@validate_http(body=BodyModel, response_model=ResponseModel)
async def handler(req: func.HttpRequest, body: BodyModel) -> ResponseModel:
    return ResponseModel(status="ok")
```

No extra async-specific decorator options are required.

## How do I test validated handlers?

Unit-test the decorated function directly with a mocked `HttpRequest`.

```python
import json
from unittest.mock import Mock

from azure.functions import HttpRequest


def request(body: bytes) -> Mock:
    req = Mock(spec=HttpRequest)
    req.method = "POST"
    req.url = "http://localhost"
    req.get_body.return_value = body
    req.params = {}
    req.route_params = {}
    req.headers = {}
    return req


def test_valid() -> None:
    response = handler(request(b'{"name":"Ada"}'))
    data = json.loads(response.get_body().decode())
    assert response.status_code == 200
    assert data["status"] == "ok"
```

See [Usage](usage.md) for a fuller testing pattern.

## What does the error response format look like?

By default, errors use:

```json
{
  "detail": [
    {
      "loc": ["body", "field"],
      "msg": "Field required",
      "type": "missing"
    }
  ]
}
```

Common status codes:

- `400` for malformed JSON.
- `422` for validation failures.
- `500` for response validation failure or internal pipeline errors.

## Can I customize the error format?

Yes, with `error_formatter`.

```python
from typing import Any


def formatter(exc: Exception, status_code: int) -> dict[str, Any]:
    return {"error": {"code": status_code, "message": str(exc)}}


@validate_http(body=BodyModel, error_formatter=formatter)
def custom(req: func.HttpRequest, body: BodyModel) -> dict[str, str]:
    return {"status": "ok"}
```

## Is response validation optional?

Yes. Omit `response_model` to skip response schema validation.

```python
@validate_http(body=BodyModel)
def no_response_model(req: func.HttpRequest, body: BodyModel) -> dict[str, str]:
    return {"status": "ok"}
```

For public APIs, using `response_model` is strongly recommended.

## Can I return `HttpResponse` directly?

Yes. Returning `func.HttpResponse` bypasses decorator response validation and
serialization logic.

This is useful for:

- `204 No Content`
- custom status codes
- non-JSON responses

## Where should I go next?

- Setup and first handler: [Quickstart](getting-started.md)
- Parameter deep dive: [Configuration](configuration.md)
- Advanced patterns: [Usage](usage.md)
- Public API details: [API Reference](api.md)
- Common failures: [Troubleshooting](troubleshooting.md)
