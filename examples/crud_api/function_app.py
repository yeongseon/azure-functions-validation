"""Task management CRUD API — a realistic example of azure-functions-validation.

Demonstrates:
  - Body validation (create / update)
  - Body + query combination (list with filters)
  - Path parameter validation (get / update / delete by id)
  - List response model (response_model=list[Model])
  - request_model shorthand
  - Response model validation (typed JSON responses)
  - HttpResponse bypass (delete returns 204 with no body)
"""

from __future__ import annotations

import azure.functions as func
from pydantic import BaseModel, Field

from azure_functions_validation import validate_http

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class TaskCreateRequest(BaseModel):
    """Body for creating a new task."""

    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=1000)
    priority: int = Field(ge=1, le=5, default=3)


class TaskUpdateRequest(BaseModel):
    """Body for updating a task."""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    priority: int | None = Field(default=None, ge=1, le=5)
    done: bool | None = None


class TaskResponse(BaseModel):
    """Single task in API responses."""

    id: int
    title: str
    description: str
    priority: int
    done: bool


class TaskPath(BaseModel):
    """Path parameter for task endpoints."""

    task_id: int = Field(ge=1)


class TaskListQuery(BaseModel):
    """Query parameters for listing tasks."""

    done: bool | None = None
    priority: int | None = Field(default=None, ge=1, le=5)


# ---------------------------------------------------------------------------
# In-memory store (replaced by a real database in production)
# ---------------------------------------------------------------------------

_TASKS: dict[int, dict[str, object]] = {
    1: {
        "id": 1,
        "title": "Write docs",
        "description": "Add examples",
        "priority": 2,
        "done": False,
    },
    2: {"id": 2, "title": "Fix bug #42", "description": "", "priority": 5, "done": True},
    3: {
        "id": 3,
        "title": "Add tests",
        "description": "Cover edge cases",
        "priority": 3,
        "done": False,
    },
}
_NEXT_ID = 4

# ---------------------------------------------------------------------------
# Function app
# ---------------------------------------------------------------------------

app = func.FunctionApp()


@app.function_name(name="list_tasks")
@app.route(route="tasks", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
@validate_http(query=TaskListQuery, response_model=list[TaskResponse])
def list_tasks(req: func.HttpRequest, query: TaskListQuery) -> list[dict[str, object]]:
    """List tasks with optional filters.

    GET /api/tasks
    GET /api/tasks?done=true
    GET /api/tasks?priority=5
    GET /api/tasks?done=false&priority=3
    """
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
    """Get a single task by id.

    GET /api/tasks/1
    """
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
    """Create a new task using body validation.

    POST /api/tasks  {"title": "New task", "priority": 2}
    """
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
    """Partial update of a task.

    PATCH /api/tasks/1  {"done": true}
    PATCH /api/tasks/1  {"title": "Updated", "priority": 5}
    """
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
    """Delete a task — returns 204 No Content (HttpResponse bypass).

    DELETE /api/tasks/1
    """
    _TASKS.pop(path.task_id, None)
    return func.HttpResponse(status_code=204)
