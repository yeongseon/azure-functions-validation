# Usage

This guide covers production patterns for `@validate_http` in the Azure Functions
Python v2 programming model.

If you are new to the package, start with [Quickstart](getting-started.md) and
then return here for deeper patterns.

## Baseline Pattern

```python
import azure.functions as func
from pydantic import BaseModel, Field

from azure_functions_validation import validate_http


class CreateUserBody(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: str


class CreateUserResult(BaseModel):
    user_id: int
    message: str


app = func.FunctionApp()


@app.function_name(name="create_user")
@app.route(route="users", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
@validate_http(body=CreateUserBody, response_model=CreateUserResult)
def create_user(req: func.HttpRequest, body: CreateUserBody) -> CreateUserResult:
    return CreateUserResult(user_id=1, message=f"Created {body.name}")
```

!!! tip "Mental model"
    Think of the decorator as a request/response contract layer:
    parse -> validate -> call handler -> validate response -> serialize.

## Input source patterns

### Body only

Use `body=Model` when your endpoint is driven only by JSON payload data.

```python
@validate_http(body=CreateUserBody)
def handler(req: func.HttpRequest, body: CreateUserBody) -> dict[str, str]:
    return {"name": body.name}
```

### Query only

```python
class ListQuery(BaseModel):
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


@validate_http(query=ListQuery)
def list_items(req: func.HttpRequest, query: ListQuery) -> dict[str, int]:
    return {"limit": query.limit, "offset": query.offset}
```

### Path only

```python
class UserPath(BaseModel):
    user_id: int = Field(ge=1)


@validate_http(path=UserPath)
def get_user(req: func.HttpRequest, path: UserPath) -> dict[str, int]:
    return {"user_id": path.user_id}
```

### Headers only

```python
from pydantic import ConfigDict


class RequestHeaders(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    x_request_id: str = Field(alias="x-request-id")


@validate_http(headers=RequestHeaders)
def inspect_headers(req: func.HttpRequest, headers: RequestHeaders) -> dict[str, str]:
    return {"request_id": headers.x_request_id}
```

!!! note "Header aliases"
    Header keys usually contain hyphens. Use `Field(alias="x-header-name")`
    plus `ConfigDict(populate_by_name=True)` when your Python attribute uses
    underscores.

## Combining body + query + headers

This is a common production shape for list/search endpoints.

```python
import azure.functions as func
from pydantic import BaseModel, ConfigDict, Field

from azure_functions_validation import validate_http


class SearchBody(BaseModel):
    terms: list[str]


class SearchQuery(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class SearchHeaders(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    x_request_id: str = Field(alias="x-request-id")


class SearchResponse(BaseModel):
    request_id: str
    page: int
    page_size: int
    count: int
    items: list[str]


app = func.FunctionApp()


@app.function_name(name="search")
@app.route(route="search", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
@validate_http(
    body=SearchBody,
    query=SearchQuery,
    headers=SearchHeaders,
    response_model=SearchResponse,
)
def search(
    req: func.HttpRequest,
    body: SearchBody,
    query: SearchQuery,
    headers: SearchHeaders,
) -> SearchResponse:
    items = [term.upper() for term in body.terms]
    return SearchResponse(
        request_id=headers.x_request_id,
        page=query.page,
        page_size=query.page_size,
        count=len(items),
        items=items,
    )
```

!!! example "When to combine"
    Use combined validation when each source has distinct semantics:
    body for domain payload, query for paging/filtering, headers for metadata.

## `request_model` shorthand (deprecated)

!!! warning "Deprecated — use `body`"
    `request_model` is a deprecated alias for `body` and emits a
    `DeprecationWarning`. Prefer `body=` (which injects a parameter named
    `body`). `request_model` will be removed in a future release.

`request_model` is shorthand for body validation and injects `req_model`.

```python
class CreateTaskBody(BaseModel):
    title: str


# Preferred:
@validate_http(body=CreateTaskBody)
def create_task(req: func.HttpRequest, body: CreateTaskBody) -> dict[str, str]:
    return {"title": body.title}
```

!!! warning "Non-combinable shorthand"
    Do not combine `request_model` with `body`, `query`, `path`, or `headers`.
    The decorator rejects this configuration at import time.

## Response validation patterns

### Pattern A: model instance return

```python
class PingResponse(BaseModel):
    status: str


@validate_http(response_model=PingResponse)
def ping(req: func.HttpRequest) -> PingResponse:
    return PingResponse(status="ok")
```

### Pattern B: dict return validated against model

```python
class HealthResponse(BaseModel):
    name: str
    status: str


@validate_http(response_model=HealthResponse)
def health(req: func.HttpRequest) -> dict[str, str]:
    return {"name": "api", "status": "ready"}
```

### Pattern C: list response model

```python
class ItemOut(BaseModel):
    id: int
    name: str


@validate_http(response_model=list[ItemOut])
def list_items(req: func.HttpRequest) -> list[dict[str, object]]:
    return [{"id": 1, "name": "alpha"}, {"id": 2, "name": "beta"}]
```

### Pattern D: bypass with `HttpResponse`

```python
@validate_http(response_model=HealthResponse)
def custom_status(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse(status_code=204)
```

!!! note "Bypass behavior"
    Returning `func.HttpResponse` skips response model validation intentionally.

## Error handling strategies

### Default strategy: standardized envelope

Without custom formatting, parsing/validation errors are emitted as:

```json
{
  "detail": [
    {
      "loc": ["query", "limit"],
      "msg": "Input should be less than or equal to 100",
      "type": "less_than_equal"
    }
  ]
}
```

### Custom strategy: per-handler `error_formatter`

```python
from typing import Any


def formatter(exc: Exception, status_code: int) -> dict[str, Any]:
    return {
        "error": {
            "code": f"VALIDATION_{status_code}",
            "message": str(exc),
        }
    }


@validate_http(body=CreateUserBody, error_formatter=formatter)
def create_user_custom(req: func.HttpRequest, body: CreateUserBody) -> dict[str, str]:
    return {"name": body.name}
```

### Strategy guidance

- Keep one default format for most handlers.
- Use custom formatters only when external contracts require it.
- Include status-coded machine fields in custom payloads.
- Avoid exposing internal implementation details in `500` errors.

!!! tip "Formatter scope"
    Formatters apply per handler; there is no global registry in this package.

## Async handlers

`@validate_http` supports `async def` handlers directly.

```python
import asyncio


class AsyncBody(BaseModel):
    name: str


class AsyncResult(BaseModel):
    message: str


@validate_http(body=AsyncBody, response_model=AsyncResult)
async def async_hello(req: func.HttpRequest, body: AsyncBody) -> AsyncResult:
    await asyncio.sleep(0)
    return AsyncResult(message=f"Hello {body.name}")
```

## Testing validated handlers

You can unit-test decorated handlers by constructing a mocked `HttpRequest`.

```python
import json
from unittest.mock import Mock

from azure.functions import HttpRequest


def make_request(body: bytes, params: dict[str, str] | None = None) -> Mock:
    req = Mock(spec=HttpRequest)
    req.method = "POST"
    req.url = "http://localhost"
    req.get_body.return_value = body
    req.params = params or {}
    req.route_params = {}
    req.headers = {}
    return req


def test_create_user_success() -> None:
    response = create_user(make_request(b'{"name": "Ada", "email": "ada@example.com"}'))
    payload = json.loads(response.get_body().decode())
    assert response.status_code == 200
    assert payload["message"] == "Created Ada"


def test_create_user_validation_error() -> None:
    response = create_user(make_request(b'{"name": "", "email": "bad"}'))
    payload = json.loads(response.get_body().decode())
    assert response.status_code == 422
    assert "detail" in payload
```

!!! note "Test level"
    Use unit tests for validation behavior and integration tests for full
    route wiring inside an Azure Functions host.

## External tool integration

`@validate_http` attaches metadata to the wrapper function via the ecosystem-wide
`_azure_functions_metadata` convention attribute. External packages can discover
Pydantic models without importing this package:

```python
meta = getattr(handler, "_azure_functions_metadata", None)
if meta and "validation" in meta:
    validation = meta["validation"]
    print(validation["body"])           # Pydantic model class or None
    print(validation["query"])          # Pydantic model class or None
    print(validation["response_model"]) # Pydantic model class or None
```

!!! tip "Bridge integration"
    This is the integration point used by `azure-functions-openapi`'s
    `scan_validation_metadata()` bridge to auto-generate OpenAPI specs from
    validation decorators. See the
    [azure-functions-openapi docs](https://yeongseon.github.io/azure-functions-openapi/)
    for details.


## Common gotchas

- Empty request body with `body=` configured returns `422`.
- Invalid JSON syntax returns `400`.
- Response shape mismatch with `response_model=` returns `500`.
- First positional parameter must be the request object.
- Naming the first positional parameter `body`/`query`/`path`/`headers` can conflict.

See [Troubleshooting](troubleshooting.md) for issue-by-issue fixes.

## Related pages

- [Configuration](configuration.md)
- [API Reference](api.md)
- [Architecture](architecture.md)
- [FAQ](faq.md)
- [Basic Validation Example](examples/basic_validation.md)
