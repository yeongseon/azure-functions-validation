# Azure Functions Validation

Typed request and response validation for Azure Functions Python v2 HTTP handlers.

`azure-functions-validation` helps you remove repetitive `req.get_json()` parsing,
enforce consistent validation behavior, and keep your handler contracts explicit.
It is designed for the decorator-based `func.FunctionApp()` model.

!!! tip "5-second rule"
    If you can paste one decorator and one Pydantic model, you can get immediate
    request validation plus typed response serialization.

## Quick Copy-Paste Example

```python
import azure.functions as func
from pydantic import BaseModel

from azure_functions_validation import validate_http


class CreateUserRequest(BaseModel):
    name: str
    email: str


class CreateUserResponse(BaseModel):
    message: str
    status: str = "ok"


app = func.FunctionApp()


@app.function_name(name="create_user")
@app.route(route="users", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
@validate_http(body=CreateUserRequest, response_model=CreateUserResponse)
def create_user(req: func.HttpRequest, body: CreateUserRequest) -> CreateUserResponse:
    return CreateUserResponse(message=f"Created user {body.name}")
```

### What you get

1. Incoming JSON is validated against `CreateUserRequest`.
2. Invalid input returns a structured `422` response.
3. Return values are validated against `CreateUserResponse`.
4. Output is serialized as JSON with a consistent content type.

!!! note "Default error envelope"
    Validation errors are returned as JSON with a `detail` array.

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

## Why teams use this package

- **Less boilerplate**: no repeated parsing and validation glue in each handler.
- **Typed contracts**: request and response schemas are first-class and testable.
- **Consistent client experience**: same error shape across endpoints.
- **Safer changes**: response validation catches drift before clients do.
- **Async support**: same decorator works for `def` and `async def` handlers.

## Feature Snapshot

### Request validation sources

- `body`: JSON request body validation.
- `query`: query string validation.
- `path`: route parameter validation.
- `headers`: header validation.
- `request_model`: **deprecated** alias for `body` (emits `DeprecationWarning`; use `body=`).

### Response validation

- `response_model` validates what your handler returns.
- Invalid response payloads return a `500` with a safe validation envelope.
- Returning `func.HttpResponse` bypasses model validation intentionally.

!!! warning "`request_model` is deprecated"
    `request_model` is a deprecated alias for `body` and emits a
    `DeprecationWarning`. Use explicit `body=...` instead. It cannot be
    combined with `body`, `query`, `path`, or `headers`.

## Where to go next

- Start with [Quickstart](getting-started.md).
- Learn all decorator options in [Configuration](configuration.md).
- See full patterns in [Usage](usage.md).
- Browse production-style scenarios in [Examples](examples/basic_validation.md).
- Explore public APIs in [API Reference](api.md).

## Compatibility

- Python 3.10+
- Azure Functions Python v2 programming model
- Pydantic v2

For dependency setup details, see [Installation](installation.md).

!!! info "About the names"
    The repository is `azure-functions-validation-python`, the PyPI package is `azure-functions-validation`, and the import is `azure_functions_validation`. See the [FAQ](faq.md#why-does-the-repo-use--python-but-the-pypi-package-does-not) for why.

## Example Index

- [Basic Validation](examples/basic_validation.md)
- [Query / Path / Header Validation](examples/query_validation.md)
- [Async Validation](examples/async_validation.md)
- [Custom Error Handler](examples/custom_error_handler.md)
- [CRUD API](examples/crud_api.md)

## Need help?

- Common fixes: [Troubleshooting](troubleshooting.md)
- Frequent questions: [FAQ](faq.md)
- Contribution workflow: [Guidelines](contributing.md)
