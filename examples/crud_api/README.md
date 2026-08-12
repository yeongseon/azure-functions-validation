# CRUD API Example

A realistic task management REST API that demonstrates the full range of
`azure-functions-validation` features in a single function app.

## Endpoints

| Method | Route | Description |
| --- | --- | --- |
| `GET` | `/api/tasks` | List tasks (optional `done` / `priority` query filters) |
| `GET` | `/api/tasks/{task_id}` | Get a single task |
| `POST` | `/api/tasks` | Create a task (`request_model` shorthand) |
| `PATCH` | `/api/tasks/{task_id}` | Partial update (body + path combined) |
| `DELETE` | `/api/tasks/{task_id}` | Delete a task (HttpResponse bypass, 204) |

## Features demonstrated

- **Body validation** — `TaskCreateRequest` / `TaskUpdateRequest` with field constraints
- **Body + query combination** — list endpoint filters via query params
- **Path parameter validation** — `task_id` with `ge=1` constraint
- **List response model** — `response_model=list[TaskResponse]`
- **HttpResponse bypass** — delete returns `204 No Content` directly
- **Partial update** — `model_dump(exclude_unset=True)` pattern for PATCH
