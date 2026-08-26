# Troubleshooting

This guide covers the most common issues when using
`azure-functions-validation` in Azure Functions Python v2 apps.

If you are still setting up, read [Installation](installation.md) and
[Quickstart](getting-started.md) first.

## Fast triage checklist

Before deep debugging, confirm:

1. Python 3.10+
2. Pydantic v2 installed
3. Azure Functions Python v2 decorator model in use
4. `@validate_http` placed directly above function definition
5. Handler first positional argument is request-like (`req`)

## Import and environment issues

### `ImportError: No module named 'azure_functions_validation'`

Cause:

- package not installed in active environment

Fix:

- reinstall package in the same interpreter used by the function host
- verify environment activation before running host

### `ModuleNotFoundError: No module named 'azure.functions'`

Cause:

- `azure-functions` dependency missing

Fix:

- add `azure-functions` to dependencies
- ensure local and deployment environments both include it

### Pydantic version mismatch

Symptoms:

- attribute errors or model behavior inconsistent with v2

Cause:

- Pydantic v1 installed transitively

Fix:

- pin and install `pydantic>=2,<3`

!!! warning "Version drift"
    If local tests pass but deployed runtime fails, compare the lockfile and the
    deployed package set.

## Validation errors not showing as expected

### Problem: handler runs even though input seems invalid

Likely causes:

- wrong decorator order
- decorator not attached to the targeted function
- validating wrong source (`body` vs `query` vs `path` vs `headers`)

Fix pattern:

```python
@app.function_name(name="my_handler")
@app.route(route="items", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
@validate_http(body=MyBodyModel)
def my_handler(req: func.HttpRequest, body: MyBodyModel) -> dict[str, str]:
    return {"ok": "true"}
```

Decorator order matters because the Azure Functions worker binds handler parameters by **name**, and `@validate_http` must wrap the handler without disturbing the worker's signature introspection. For the underlying mechanism see [How the worker binds handlers §2–§3](https://yeongseon.dev/azure-functions-python/platform/how-the-worker-binds-handlers/) (parameter passthrough and `req`/`context` resolution). This repo's WorkerCompat suite (`tests/test_decorator.py`, `tests/test_worker_compat_2x_spike.py`) is the executable proof of that contract.

### Problem: expected body validation but got `400 Invalid JSON`

Cause:

- payload is not valid JSON syntax

Fix:

- ensure body is valid JSON with double-quoted keys/strings

### Problem: expected optional body but got `422`

Cause:

- empty body is treated as missing when `body=` or `request_model=` is configured

Fix:

- send `{}` and model optional fields explicitly
- or remove body validation for endpoints that truly allow empty body

!!! note "Optional field vs optional body"
    Optional model fields do not make the request body itself optional.

## Response model mismatch

### Problem: HTTP `500` with `response_validation_error`

Cause:

- return value does not conform to `response_model`

Typical examples:

- missing required field
- wrong field type
- wrong shape for `list[Model]`

Fix:

1. compare returned object to response schema
2. ensure nested objects match schema types
3. add unit tests for both happy and edge paths

Example mismatch:

```python
class OutModel(BaseModel):
    message: str


@validate_http(response_model=OutModel)
def handler(req: func.HttpRequest) -> dict[str, str]:
    return {"msg": "wrong key"}
```

Corrected:

```python
@validate_http(response_model=OutModel)
def handler(req: func.HttpRequest) -> dict[str, str]:
    return {"message": "ok"}
```

### Problem: response validation seems skipped

Cause:

- handler returns `func.HttpResponse` directly

Fix:

- return model/dict if you want response validation
- keep direct `HttpResponse` only when bypass is intentional

## Async handler issues

### Problem: confusion about async support

Answer:

- `@validate_http` supports `async def` out of the box

### Problem: `RuntimeError: no running event loop` in tests

Cause:

- async handler test executed in sync-only test context

Fix:

- run async tests with an async-capable test runner setup

Example:

```python
import pytest


@pytest.mark.anyio
async def test_async_handler() -> None:
    ...
```

### Problem: unexpected blocking in async handlers

Cause:

- blocking I/O used inside `async def`

Fix:

- switch to async-compatible libraries for network/database calls

!!! tip "Keep async valuable"
    Use `async def` for I/O-bound paths. Keep CPU-heavy work outside request path
    or offload as needed.

## Decorator configuration errors

### `ValueError: Cannot use request_model together with body/query/path/headers`

Fix:

- use `request_model` alone
- or switch to explicit `body=...` if combining sources

### `ValueError: must accept an HttpRequest parameter as its first positional argument`

Fix:

- make first positional parameter the request object

### Parameter name conflict errors

Cause:

- first positional parameter uses injected names like `body` or `query`

Fix:

- rename request parameter to `req` or `http_request`

## Custom formatter issues

### Problem: formatter not called

Check:

- formatter passed to the same handler decorator
- signature is exactly `(Exception, int) -> dict[...]`

### Problem: inconsistent custom error payload

Fix:

- keep a stable schema (`code`, `message`, optional `details`)
- do not rely on raw exception text for client logic

!!! example "Stable formatter"
    ```python
    def formatter(exc: Exception, status_code: int) -> dict[str, object]:
        return {
            "error": {
                "code": f"VALIDATION_{status_code}",
                "message": str(exc),
            }
        }
    ```

## Still stuck?

- Compare behavior with examples in `examples/`
- Confirm your handler signatures match docs exactly
- Re-check [Configuration](configuration.md) parameter semantics
- Review [Usage](usage.md) patterns for multi-source and response validation
