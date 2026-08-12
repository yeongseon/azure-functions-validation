# API Reference

This page documents the public API exported from `azure_functions_validation`.

```python
from azure_functions_validation import (
    ErrorFormatter,
    HttpError,
    PydanticAdapter,
    ResponseValidationError,
    SerializationError,
    ValidationAdapter,
    validate_http,
)
```

!!! note "Public surface"
    The package exports (`__all__`): `validate_http`, `ResponseValidationError`,
    `SerializationError`, `ErrorFormatter`, `ValidationAdapter`, `PydanticAdapter`,
    and `HttpError`. Pipeline internals (`PipelineConfig`, `run_pipeline`) are not
    public contracts.

## `validate_http`

::: azure_functions_validation.validate_http

### Usage example: body + response validation

```python
import azure.functions as func
from pydantic import BaseModel

from azure_functions_validation import validate_http


class CreateInvoiceBody(BaseModel):
    customer_id: str
    amount: float


class CreateInvoiceResponse(BaseModel):
    invoice_id: str
    status: str


app = func.FunctionApp()


@app.function_name(name="create_invoice")
@app.route(route="invoices", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
@validate_http(body=CreateInvoiceBody, response_model=CreateInvoiceResponse)
def create_invoice(req: func.HttpRequest, body: CreateInvoiceBody) -> CreateInvoiceResponse:
    return CreateInvoiceResponse(invoice_id="inv_1001", status="created")
```

### Usage example: status codes and controlled errors

Use `status_code=` to set the success status (e.g. `201` for creation), and
raise `HttpError` to return a controlled error through the standard
`{"detail": [...]}` envelope without bypassing validation.

```python
import azure.functions as func
from pydantic import BaseModel

from azure_functions_validation import HttpError, validate_http


class CreateUserBody(BaseModel):
    name: str


class UserResponse(BaseModel):
    id: int
    name: str


app = func.FunctionApp()

_USERS: dict[int, UserResponse] = {}


@app.function_name(name="create_user")
@app.route(route="users", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
@validate_http(body=CreateUserBody, response_model=UserResponse, status_code=201)
def create_user(req: func.HttpRequest, body: CreateUserBody) -> UserResponse:
    user = UserResponse(id=len(_USERS) + 1, name=body.name)
    _USERS[user.id] = user
    return user  # HTTP 201


@app.function_name(name="get_user")
@app.route(route="users/{user_id}", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
@validate_http(response_model=UserResponse)
def get_user(req: func.HttpRequest) -> UserResponse:
    user = _USERS.get(int(req.route_params["user_id"]))
    if user is None:
        raise HttpError(404, "User not found")
    return user
```

### Usage example: query + path + headers

```python
import azure.functions as func
from pydantic import BaseModel, ConfigDict, Field

from azure_functions_validation import validate_http


class UserQuery(BaseModel):
    include_deleted: bool = False


class UserPath(BaseModel):
    user_id: int = Field(ge=1)


class UserHeaders(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    x_request_id: str = Field(alias="x-request-id")


app = func.FunctionApp()


@app.function_name(name="get_user")
@app.route(route="users/{user_id}", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
@validate_http(query=UserQuery, path=UserPath, headers=UserHeaders)
def get_user(
    req: func.HttpRequest,
    query: UserQuery,
    path: UserPath,
    headers: UserHeaders,
) -> dict[str, object]:
    return {
        "user_id": path.user_id,
        "include_deleted": query.include_deleted,
        "request_id": headers.x_request_id,
    }
```

### Usage example: `request_model` shorthand (deprecated)

!!! warning "Deprecated"
    `request_model` is a deprecated alias for `body` and emits a
    `DeprecationWarning`. Use `body=` instead; it injects a parameter named
    `body` (rather than `req_model`). `request_model` will be removed in a
    future release. See the migration below.

```python
import azure.functions as func
from pydantic import BaseModel

from azure_functions_validation import validate_http


class CreateTaskRequest(BaseModel):
    title: str


app = func.FunctionApp()


@app.function_name(name="create_task")
@app.route(route="tasks", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
@validate_http(body=CreateTaskRequest)
def create_task(req: func.HttpRequest, body: CreateTaskRequest) -> dict[str, str]:
    return {"title": body.title}
```

!!! note "Migrating from `request_model`"
    Replace `@validate_http(request_model=Model)` (injects `req_model`) with
    `@validate_http(body=Model)` (injects `body`).

!!! warning "Conflict rule"
    `request_model` cannot be combined with `body`, `query`, `path`, or `headers`.
    The decorator raises `ValueError` at import time if combined.

## `ResponseValidationError`

::: azure_functions_validation.ResponseValidationError

### Usage example: handling response contract failures

```python
import azure.functions as func
from pydantic import BaseModel

from azure_functions_validation import validate_http


class HealthResponse(BaseModel):
    status: str


app = func.FunctionApp()


@app.function_name(name="health")
@app.route(route="health", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
@validate_http(response_model=HealthResponse)
def health(req: func.HttpRequest) -> dict[str, str]:
    # Returning an invalid shape to show failure behavior
    return {"state": "ok"}
```

When response validation fails, the runtime returns HTTP `500` with this payload:

```json
{
  "detail": [
    {
      "loc": ["response"],
      "msg": "Response validation failed",
      "type": "response_validation_error"
    }
  ]
}
```

!!! note "HttpResponse bypass"
    Returning `azure.functions.HttpResponse` directly bypasses response model
    validation by design.

## `ErrorFormatter`

::: azure_functions_validation.ErrorFormatter

### Usage example: custom validation error shape

```python
import azure.functions as func
from pydantic import BaseModel

from azure_functions_validation import ErrorFormatter, validate_http


class InputModel(BaseModel):
    value: int


def app_error_formatter(exc: Exception, status_code: int) -> dict[str, object]:
    return {
        "error": {
            "code": f"VALIDATION_{status_code}",
            "message": str(exc),
        }
    }


formatter: ErrorFormatter = app_error_formatter

app = func.FunctionApp()


@app.function_name(name="custom_error")
@app.route(route="custom_error", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
@validate_http(body=InputModel, error_formatter=formatter)
def custom_error(req: func.HttpRequest, body: InputModel) -> dict[str, int]:
    return {"value": body.value}
```

!!! tip "Formatter signature"
    Keep the formatter signature exactly `(exc: Exception, status_code: int) -> dict[str, Any]`.

## `HttpError`

::: azure_functions_validation.HttpError

Raise `HttpError(status_code, detail)` from a handler to return a controlled
HTTP error rendered through the standard `{"detail": [...]}` envelope. `detail`
may be a plain message (wrapped into a single entry) or a pre-built list of
`{"loc", "msg", "type"}` mappings. Errors with `status_code >= 500` are
sanitized so internal details never leak to clients.

## `azure_functions_validation.testing.MockHttpRequest`

A public test helper for unit-testing validated handlers. It subclasses the real
`azure.functions.HttpRequest`, so it drives the genuine `@validate_http` pipeline
end-to-end without a running Functions host.

```python
from azure_functions_validation.testing import MockHttpRequest

request = MockHttpRequest(
    method="POST",
    json={"name": "Alice", "email": "alice@example.com"},
    params={"debug": "true"},
)
response = create_user(request)
assert response.status_code == 200
```

See [Testing](testing.md#testing-your-handlers-with-mockhttprequest) for the full
list of constructor options.

## Error response shape reference

Default validation and parsing errors use this envelope:

```json
{
  "detail": [
    {
      "loc": ["body", "field_name"],
      "msg": "Field required",
      "type": "missing"
    }
  ],
  "error_format_version": 1
}
```

### Stability contract

Every **default** error envelope carries a top-level `error_format_version`
integer. It lets downstream consumers (frontends, API gateways) pin against a
known schema and detect breaking changes explicitly instead of silently
misparsing new fields.

- The current version is `1`.
- The integer is bumped **only** when the default envelope changes in a
  backwards-incompatible way; additive, optional fields do not bump it.
- The marker is present on all built-in envelopes — validation errors (`4xx`),
  sanitized server errors (`5xx`), and the internal-failure fallback.
- A **custom** `ErrorFormatter` owns its output shape entirely: the marker is
  never injected into a successful custom formatter's response. Emit your own
  version field there if you need one.

Common status codes:

- `400`: invalid JSON parsing (`"Invalid JSON"`).
- `422`: request validation failed.
- `500`: response validation failure or internal adapter failure.

!!! example "Typical loc values"
    - body errors: `loc` starts with `"body"`
    - query errors: `loc` starts with `"query"`
    - path errors: `loc` starts with `"path"`
    - header errors: `loc` starts with `"headers"`
    - response errors: `loc` equals `["response"]`

!!! tip "Opting out of the source prefix"
    The leading source segment (`body` / `query` / `path` / `headers`) was
    added to disambiguate same-named fields across inputs. To keep the previous
    unprefixed `loc` for one migration cycle, pass `legacy_loc=True` to
    `validate_http`. This escape hatch will be removed in a future release.

## Custom adapters

`ValidationAdapter` (the adapter protocol) and `PydanticAdapter` (the default
implementation) are part of the public API. Pass a custom `adapter=` to
`validate_http` to plug in a non-Pydantic validation backend; most deployments
should keep the default `PydanticAdapter`.

```python
from azure_functions_validation import PydanticAdapter, ValidationAdapter, validate_http

adapter: ValidationAdapter = PydanticAdapter(legacy_loc=False)


@validate_http(body=RequestModel, adapter=adapter)
def handler(req, body): ...
```

## Internal references

These modules are useful for advanced extension work but are internal APIs:

- `pipeline.py`: `PipelineConfig`, `run_pipeline`, `run_pipeline_async`

For full implementation patterns, see [Usage](usage.md) and
[Architecture](architecture.md).
