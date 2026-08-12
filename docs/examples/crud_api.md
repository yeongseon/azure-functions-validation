# CRUD API Example

## Overview

This example implements a realistic task-management API and demonstrates how
`azure-functions-validation` scales from simple handlers to multi-route apps.

Source code path:

- `examples/crud_api/function_app.py`

The app includes list, read, create, update, and delete endpoints with explicit
request and response contracts.

## Prerequisites

1. Python 3.10+
2. Azure Functions Python v2 project
3. Installed dependencies (`azure-functions`, `azure-functions-validation`, `pydantic`)

!!! note "Recommended order"
    Read [Basic Validation](basic_validation.md) first,
    then use this page as the production-style extension.

## Endpoint Map

| Method | Route | Description |
| --- | --- | --- |
| `GET` | `/api/tasks` | List tasks with optional query filters |
| `GET` | `/api/tasks/{task_id}` | Get one task by id |
| `POST` | `/api/tasks` | Create task with `body` validation |
| `PATCH` | `/api/tasks/{task_id}` | Partial update with body + path validation |
| `DELETE` | `/api/tasks/{task_id}` | Delete task and return `204 No Content` |

## Complete Working Code

The complete code lives in `examples/crud_api/function_app.py`.

```python
from __future__ import annotations

import azure.functions as func
from pydantic import BaseModel, Field

from azure_functions_validation import validate_http


class TaskCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=1000)
    priority: int = Field(ge=1, le=5, default=3)


class TaskUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    priority: int | None = Field(default=None, ge=1, le=5)
    done: bool | None = None


class TaskResponse(BaseModel):
    id: int
    title: str
    description: str
    priority: int
    done: bool


class TaskPath(BaseModel):
    task_id: int = Field(ge=1)


class TaskListQuery(BaseModel):
    done: bool | None = None
    priority: int | None = Field(default=None, ge=1, le=5)


_TASKS: dict[int, dict[str, object]] = {
    1: {"id": 1, "title": "Write docs", "description": "Add examples", "priority": 2, "done": False},
    2: {"id": 2, "title": "Fix bug #42", "description": "", "priority": 5, "done": True},
    3: {"id": 3, "title": "Add tests", "description": "Cover edge cases", "priority": 3, "done": False},
}
_NEXT_ID = 4


app = func.FunctionApp()


@app.function_name(name="list_tasks")
@app.route(route="tasks", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
@validate_http(query=TaskListQuery, response_model=list[TaskResponse])
def list_tasks(req: func.HttpRequest, query: TaskListQuery) -> list[dict[str, object]]:
    results = list(_TASKS.values())
    if query.done is not None:
        results = [t for t in results if t["done"] == query.done]
    if query.priority is not None:
        results = [t for t in results if t["priority"] == query.priority]
    return results


@app.function_name(name="get_task")
@app.route(route="tasks/{task_id}", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
@validate_http(path=TaskPath, response_model=TaskResponse)
def get_task(req: func.HttpRequest, path: TaskPath) -> dict[str, object]:
    task = _TASKS.get(path.task_id)
    if task is None:
        return func.HttpResponse(  # type: ignore[return-value]
            body='{"detail": [{"msg": "Task not found"}]}',
            status_code=404,
            headers={"Content-Type": "application/json"},
        )
    return task


@app.function_name(name="create_task")
@app.route(route="tasks", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
@validate_http(body=TaskCreateRequest, response_model=TaskResponse)
def create_task(req: func.HttpRequest, body: TaskCreateRequest) -> TaskResponse:
    global _NEXT_ID  # noqa: PLW0603

    task = TaskResponse(
        id=_NEXT_ID,
        title=body.title,
        description=body.description,
        priority=body.priority,
        done=False,
    )
    _TASKS[_NEXT_ID] = task.model_dump()
    _NEXT_ID += 1
    return task


@app.function_name(name="update_task")
@app.route(route="tasks/{task_id}", methods=["PATCH"], auth_level=func.AuthLevel.ANONYMOUS)
@validate_http(body=TaskUpdateRequest, path=TaskPath, response_model=TaskResponse)
def update_task(
    req: func.HttpRequest,
    body: TaskUpdateRequest,
    path: TaskPath,
) -> dict[str, object] | func.HttpResponse:
    task = _TASKS.get(path.task_id)
    if task is None:
        return func.HttpResponse(
            body='{"detail": [{"msg": "Task not found"}]}',
            status_code=404,
            headers={"Content-Type": "application/json"},
        )

    updates = body.model_dump(exclude_unset=True)
    for key, value in updates.items():
        task[key] = value
    return task


@app.function_name(name="delete_task")
@app.route(route="tasks/{task_id}", methods=["DELETE"], auth_level=func.AuthLevel.ANONYMOUS)
@validate_http(path=TaskPath)
def delete_task(req: func.HttpRequest, path: TaskPath) -> func.HttpResponse:
    _TASKS.pop(path.task_id, None)
    return func.HttpResponse(status_code=204)
```

## Step-by-step walkthrough

### Step 1: model each request source

- `TaskCreateRequest`: create body contract
- `TaskUpdateRequest`: partial update body contract
- `TaskPath`: route id contract
- `TaskListQuery`: list filter query contract

### Step 2: enforce response contracts

- collection endpoints use `list[TaskResponse]`
- item endpoints use `TaskResponse`

This catches accidental response drift early.

### Step 3: implement create with `body`

`body=TaskCreateRequest` validates the request body and injects `body`.

### Step 4: implement PATCH safely

```python
updates = body.model_dump(exclude_unset=True)
for key, value in updates.items():
    task[key] = value
```

This applies only fields provided by the client.

### Step 5: return raw `HttpResponse` for `204`

Delete endpoint intentionally bypasses model serialization.

!!! tip "Practical pattern"
    Use typed model responses for normal JSON paths, and return `HttpResponse`
    directly for no-content or custom-status control paths.

## curl checks with expected output

### List tasks

```bash
curl -i "http://localhost:7071/api/tasks"
```

Expected response:

```http
HTTP/1.1 200 OK
Content-Type: application/json

[{"id":1,"title":"Write docs","description":"Add examples","priority":2,"done":false}, ...]
```

### List tasks with filter

```bash
curl -i "http://localhost:7071/api/tasks?done=true"
```

Expected response:

```http
HTTP/1.1 200 OK
Content-Type: application/json

[{"id":2,"title":"Fix bug #42","description":"","priority":5,"done":true}]
```

### Create task

```bash
curl -i -X POST http://localhost:7071/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"title":"Ship release notes","priority":2}'
```

Expected response:

```http
HTTP/1.1 200 OK
Content-Type: application/json

{"id":4,"title":"Ship release notes","description":"","priority":2,"done":false}
```

### Invalid path parameter

```bash
curl -i "http://localhost:7071/api/tasks/0"
```

Expected response:

```http
HTTP/1.1 422 Unprocessable Entity
Content-Type: application/json

{"detail":[{"loc":["path","task_id"],"msg":"Input should be greater than or equal to 1","type":"greater_than_equal"}]}
```

### Delete task

```bash
curl -i -X DELETE "http://localhost:7071/api/tasks/2"
```

Expected response:

```http
HTTP/1.1 204 No Content
```

!!! warning "404 handling"
    This example uses custom `HttpResponse` for not-found cases, which bypasses
    response model validation by design.

## What you learned

- How to apply validation consistently across CRUD endpoints
- How list response validation works in production APIs
- How to perform safe partial updates with typed optional fields
- How to combine strict contracts with custom status-code behavior

## Related docs

- [Usage](../usage.md)
- [Configuration](../configuration.md)
- [API Reference](../api.md)
- [Troubleshooting](../troubleshooting.md)
