# Configuration

This page documents every parameter of `validate_http` and how to combine them
in production handlers.

```python
@validate_http(
    body=...,
    query=...,
    path=...,
    headers=...,
    request_model=...,
    response_model=...,
    adapter=...,
    error_formatter=...,
)
```

## Signature overview

Public keyword-only parameters:

- `body`
- `query`
- `path`
- `headers`
- `request_model`
- `response_model`
- `adapter`
- `error_formatter`

!!! note "Keyword-only API"
    `validate_http` parameters are keyword-only. Prefer explicit names for
    readability and maintainability.

## Parameter details

### `body`

Use `body=YourBodyModel` to validate JSON request body content.

```python
class CreateBody(BaseModel):
    name: str


@validate_http(body=CreateBody)
def create(req: func.HttpRequest, body: CreateBody) -> dict[str, str]:
    return {"name": body.name}
```

Behavior:

- Empty body -> `422` (`missing` error)
- Invalid JSON syntax -> `400`
- Invalid field values -> `422`

### `query`

Use `query=QueryModel` to validate query-string parameters.

```python
class QueryModel(BaseModel):
    page: int = Field(default=1, ge=1)


@validate_http(query=QueryModel)
def list_items(req: func.HttpRequest, query: QueryModel) -> dict[str, int]:
    return {"page": query.page}
```

### `path`

Use `path=PathModel` for route variables from `@app.route(route="...")`.

```python
class PathModel(BaseModel):
    item_id: int = Field(ge=1)


@validate_http(path=PathModel)
def get_item(req: func.HttpRequest, path: PathModel) -> dict[str, int]:
    return {"item_id": path.item_id}
```

### `headers`

Use `headers=HeadersModel` to validate inbound request headers.

```python
class HeadersModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    x_request_id: str = Field(alias="x-request-id")


@validate_http(headers=HeadersModel)
def inspect(req: func.HttpRequest, headers: HeadersModel) -> dict[str, str]:
    return {"request_id": headers.x_request_id}
```

### `request_model` (deprecated)

!!! warning "Deprecated — use `body`"
    `request_model` is a deprecated alias for `body` and emits a
    `DeprecationWarning`. Prefer `body=` (which injects a parameter named
    `body`). `request_model` will be removed in a future release.

`request_model` is shorthand for body validation and injects a parameter named
`req_model`.

```python
class RequestModel(BaseModel):
    text: str


# Deprecated form (emits DeprecationWarning):
@validate_http(request_model=RequestModel)
def post(req: func.HttpRequest, req_model: RequestModel) -> dict[str, str]:
    return {"text": req_model.text}


# Preferred form:
@validate_http(body=RequestModel)
def post_preferred(req: func.HttpRequest, body: RequestModel) -> dict[str, str]:
    return {"text": body.text}
```

!!! warning "Mutual exclusivity"
    Do not combine `request_model` with `body`, `query`, `path`, or `headers`.

### `response_model`

Use `response_model=ModelOrType` to validate your handler output.

```python
class ResultModel(BaseModel):
    status: str


@validate_http(response_model=ResultModel)
def health(req: func.HttpRequest) -> dict[str, str]:
    return {"status": "ok"}
```

Also supports generic type forms like `list[ResultModel]`.

### `adapter`

`adapter` allows plugging a custom implementation of the internal
`ValidationAdapter` protocol.

Default behavior uses `PydanticAdapter()` when omitted.

```python
@validate_http(body=RequestModel)  # adapter defaults to PydanticAdapter()
def handler(req: func.HttpRequest, body: RequestModel) -> dict[str, str]:
    return {"text": body.text}
```

!!! note "Advanced extension point"
    Most projects should keep the default adapter.

### `error_formatter`

`error_formatter` customizes error response payloads per handler.

```python
from typing import Any


def formatter(exc: Exception, status_code: int) -> dict[str, Any]:
    return {
        "error": {
            "code": f"VALIDATION_{status_code}",
            "message": str(exc),
        }
    }


@validate_http(body=RequestModel, error_formatter=formatter)
def handler_custom(req: func.HttpRequest, body: RequestModel) -> dict[str, str]:
    return {"text": body.text}
```

## Configuration patterns

### Pattern 1: simple body API

```python
@validate_http(body=RequestModel, response_model=ResultModel)
def create(req: func.HttpRequest, body: RequestModel) -> ResultModel:
    return ResultModel(status="created")
```

### Pattern 2: route-driven read API

```python
@validate_http(path=PathModel, query=QueryModel, response_model=ResultModel)
def get(req: func.HttpRequest, path: PathModel, query: QueryModel) -> ResultModel:
    return ResultModel(status=f"item={path.item_id},page={query.page}")
```

### Pattern 3: custom error contract

```python
@validate_http(body=RequestModel, response_model=ResultModel, error_formatter=formatter)
def create_custom(req: func.HttpRequest, body: RequestModel) -> ResultModel:
    return ResultModel(status="created")
```

## Defaults and operational behavior

- `adapter` defaults to `PydanticAdapter()`.
- No `response_model` means output is serialized without response schema validation.
- Returning `func.HttpResponse` bypasses response serialization/validation.
- 500-level internal pipeline errors are sanitized by default when no formatter is set.

!!! tip "Choose explicit response models"
    `response_model` catches accidental contract drift and is strongly recommended
    for public APIs.

## Related references

- [API Reference](api.md)
- [Usage](usage.md)
- [Troubleshooting](troubleshooting.md)
- [FAQ](faq.md)
