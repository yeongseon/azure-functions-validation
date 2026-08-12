import asyncio
from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path
from typing import Any

import azure.functions as func


def _load_example_module(example_name: str) -> Any:
    module_path = (
        Path(__file__).resolve().parents[1] / "examples" / example_name / "function_app.py"
    )
    spec = spec_from_file_location(f"validation_example_{example_name}", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load example module from {module_path}")

    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_hello_validation_example_returns_validated_response() -> None:
    function_app = _load_example_module("hello_validation")
    request = func.HttpRequest(
        method="POST",
        url="/api/hello_validation",
        body=json.dumps({"name": "Azure"}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )

    response = function_app.hello_validation(request)

    assert response.status_code == 200
    assert json.loads(response.get_body()) == {"message": "Hello Azure"}


def test_hello_validation_example_returns_validation_error() -> None:
    function_app = _load_example_module("hello_validation")
    request = func.HttpRequest(
        method="POST",
        url="/api/hello_validation",
        body=json.dumps({}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )

    response = function_app.hello_validation(request)

    assert response.status_code == 422
    payload = json.loads(response.get_body())
    assert "detail" in payload


def test_raw_http_response_example_returns_json() -> None:
    function_app = _load_example_module("hello_validation")
    request = func.HttpRequest(
        method="GET",
        url="/api/raw_http_response",
        body=b"",
        headers={},
    )

    response = function_app.raw_http_response(request)

    assert response.status_code == 200
    assert json.loads(response.get_body()) == {"message": "ok"}


def test_profile_validation_example_returns_typed_response() -> None:
    function_app = _load_example_module("profile_validation")
    request = func.HttpRequest(
        method="GET",
        url="/api/users/7?verbose=true",
        body=b"",
        params={"verbose": "true"},
        headers={"x-request-id": "req-123"},
        route_params={"user_id": "7"},
    )

    response = function_app.get_profile(request)

    assert response.status_code == 200
    assert json.loads(response.get_body()) == {
        "user_id": 7,
        "view": "detailed",
        "request_id": "req-123",
    }


def test_profile_validation_example_returns_header_validation_error() -> None:
    function_app = _load_example_module("profile_validation")
    request = func.HttpRequest(
        method="GET",
        url="/api/users/7",
        body=b"",
        params={},
        headers={},
        route_params={"user_id": "7"},
    )

    response = function_app.get_profile(request)

    assert response.status_code == 422
    payload = json.loads(response.get_body())
    assert "detail" in payload


def test_custom_error_handler_example_returns_custom_error_shape() -> None:
    function_app = _load_example_module("custom_error_handler")
    request = func.HttpRequest(
        method="POST",
        url="/api/comments",
        body=json.dumps({}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )

    response = function_app.create_comment(request)

    assert response.status_code == 422
    assert json.loads(response.get_body())["error"]["code"] == "VALIDATION_422"


def test_async_validation_example_returns_typed_response() -> None:
    function_app = _load_example_module("async_validation")
    request = func.HttpRequest(
        method="POST",
        url="/api/async_validation",
        body=json.dumps({"name": "Azure"}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )

    response = asyncio.run(function_app.async_validation(request))

    assert response.status_code == 200
    assert json.loads(response.get_body()) == {"message": "Hello Azure", "source": "async"}


def test_async_validation_example_returns_validation_error() -> None:
    function_app = _load_example_module("async_validation")
    request = func.HttpRequest(
        method="POST",
        url="/api/async_validation",
        body=json.dumps({}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )

    response = asyncio.run(function_app.async_validation(request))

    assert response.status_code == 422
    payload = json.loads(response.get_body())
    assert "detail" in payload


# ---------------------------------------------------------------------------
# CRUD API example
# ---------------------------------------------------------------------------


def _crud_module() -> Any:
    """Load the CRUD API example module and return it with state helpers."""
    return _load_example_module("crud_api")


def _reset_crud_state(mod: Any) -> None:
    """Restore the CRUD module's in-memory store to its initial state."""
    mod._TASKS.clear()
    mod._TASKS.update(
        {
            1: {
                "id": 1,
                "title": "Write docs",
                "description": "Add examples",
                "priority": 2,
                "done": False,
            },
            2: {
                "id": 2,
                "title": "Fix bug #42",
                "description": "",
                "priority": 5,
                "done": True,
            },
            3: {
                "id": 3,
                "title": "Add tests",
                "description": "Cover edge cases",
                "priority": 3,
                "done": False,
            },
        }
    )
    mod._NEXT_ID = 4


class TestCrudListTasks:
    """GET /api/tasks — list with optional query filters."""

    def setup_method(self) -> None:
        self.mod = _crud_module()
        _reset_crud_state(self.mod)

    def test_list_all_tasks(self) -> None:
        request = func.HttpRequest(
            method="GET",
            url="/api/tasks",
            body=b"",
            headers={},
            params={},
        )
        response = self.mod.list_tasks(request)
        assert response.status_code == 200
        tasks = json.loads(response.get_body())
        assert len(tasks) == 3

    def test_list_filter_done_true(self) -> None:
        request = func.HttpRequest(
            method="GET",
            url="/api/tasks?done=true",
            body=b"",
            headers={},
            params={"done": "true"},
        )
        response = self.mod.list_tasks(request)
        assert response.status_code == 200
        tasks = json.loads(response.get_body())
        assert len(tasks) == 1
        assert tasks[0]["title"] == "Fix bug #42"

    def test_list_filter_done_false(self) -> None:
        request = func.HttpRequest(
            method="GET",
            url="/api/tasks?done=false",
            body=b"",
            headers={},
            params={"done": "false"},
        )
        response = self.mod.list_tasks(request)
        assert response.status_code == 200
        tasks = json.loads(response.get_body())
        assert len(tasks) == 2

    def test_list_filter_priority(self) -> None:
        request = func.HttpRequest(
            method="GET",
            url="/api/tasks?priority=5",
            body=b"",
            headers={},
            params={"priority": "5"},
        )
        response = self.mod.list_tasks(request)
        assert response.status_code == 200
        tasks = json.loads(response.get_body())
        assert len(tasks) == 1
        assert tasks[0]["id"] == 2

    def test_list_filter_combined(self) -> None:
        request = func.HttpRequest(
            method="GET",
            url="/api/tasks?done=false&priority=3",
            body=b"",
            headers={},
            params={"done": "false", "priority": "3"},
        )
        response = self.mod.list_tasks(request)
        assert response.status_code == 200
        tasks = json.loads(response.get_body())
        assert len(tasks) == 1
        assert tasks[0]["title"] == "Add tests"

    def test_list_invalid_query_returns_422(self) -> None:
        request = func.HttpRequest(
            method="GET",
            url="/api/tasks?priority=99",
            body=b"",
            headers={},
            params={"priority": "99"},
        )
        response = self.mod.list_tasks(request)
        assert response.status_code == 422


class TestCrudGetTask:
    """GET /api/tasks/{task_id} — single task by id."""

    def setup_method(self) -> None:
        self.mod = _crud_module()
        _reset_crud_state(self.mod)

    def test_get_existing_task(self) -> None:
        request = func.HttpRequest(
            method="GET",
            url="/api/tasks/1",
            body=b"",
            headers={},
            route_params={"task_id": "1"},
        )
        response = self.mod.get_task(request)
        assert response.status_code == 200
        task = json.loads(response.get_body())
        assert task["id"] == 1
        assert task["title"] == "Write docs"

    def test_get_nonexistent_task_returns_404(self) -> None:
        request = func.HttpRequest(
            method="GET",
            url="/api/tasks/999",
            body=b"",
            headers={},
            route_params={"task_id": "999"},
        )
        response = self.mod.get_task(request)
        assert response.status_code == 404

    def test_get_invalid_task_id_returns_422(self) -> None:
        request = func.HttpRequest(
            method="GET",
            url="/api/tasks/0",
            body=b"",
            headers={},
            route_params={"task_id": "0"},
        )
        response = self.mod.get_task(request)
        assert response.status_code == 422

    def test_get_non_numeric_task_id_returns_422(self) -> None:
        request = func.HttpRequest(
            method="GET",
            url="/api/tasks/abc",
            body=b"",
            headers={},
            route_params={"task_id": "abc"},
        )
        response = self.mod.get_task(request)
        assert response.status_code == 422


class TestCrudCreateTask:
    """POST /api/tasks — create via body validation."""

    def setup_method(self) -> None:
        self.mod = _crud_module()
        _reset_crud_state(self.mod)

    def test_create_task_success(self) -> None:
        request = func.HttpRequest(
            method="POST",
            url="/api/tasks",
            body=json.dumps({"title": "New task", "priority": 2}).encode(),
            headers={"Content-Type": "application/json"},
        )
        response = self.mod.create_task(request)
        assert response.status_code == 200
        task = json.loads(response.get_body())
        assert task["id"] == 4
        assert task["title"] == "New task"
        assert task["priority"] == 2
        assert task["done"] is False
        assert task["description"] == ""

    def test_create_task_minimal_body(self) -> None:
        request = func.HttpRequest(
            method="POST",
            url="/api/tasks",
            body=json.dumps({"title": "Minimal"}).encode(),
            headers={"Content-Type": "application/json"},
        )
        response = self.mod.create_task(request)
        assert response.status_code == 200
        task = json.loads(response.get_body())
        assert task["title"] == "Minimal"
        assert task["priority"] == 3  # default

    def test_create_task_missing_title_returns_422(self) -> None:
        request = func.HttpRequest(
            method="POST",
            url="/api/tasks",
            body=json.dumps({"priority": 1}).encode(),
            headers={"Content-Type": "application/json"},
        )
        response = self.mod.create_task(request)
        assert response.status_code == 422

    def test_create_task_empty_title_returns_422(self) -> None:
        request = func.HttpRequest(
            method="POST",
            url="/api/tasks",
            body=json.dumps({"title": ""}).encode(),
            headers={"Content-Type": "application/json"},
        )
        response = self.mod.create_task(request)
        assert response.status_code == 422

    def test_create_task_invalid_priority_returns_422(self) -> None:
        request = func.HttpRequest(
            method="POST",
            url="/api/tasks",
            body=json.dumps({"title": "Bad priority", "priority": 10}).encode(),
            headers={"Content-Type": "application/json"},
        )
        response = self.mod.create_task(request)
        assert response.status_code == 422


class TestCrudUpdateTask:
    """PATCH /api/tasks/{task_id} — partial update (body + path)."""

    def setup_method(self) -> None:
        self.mod = _crud_module()
        _reset_crud_state(self.mod)

    def test_update_task_mark_done(self) -> None:
        request = func.HttpRequest(
            method="PATCH",
            url="/api/tasks/1",
            body=json.dumps({"done": True}).encode(),
            headers={"Content-Type": "application/json"},
            route_params={"task_id": "1"},
        )
        response = self.mod.update_task(request)
        assert response.status_code == 200
        task = json.loads(response.get_body())
        assert task["done"] is True
        assert task["title"] == "Write docs"  # unchanged

    def test_update_task_change_title_and_priority(self) -> None:
        request = func.HttpRequest(
            method="PATCH",
            url="/api/tasks/1",
            body=json.dumps({"title": "Updated", "priority": 5}).encode(),
            headers={"Content-Type": "application/json"},
            route_params={"task_id": "1"},
        )
        response = self.mod.update_task(request)
        assert response.status_code == 200
        task = json.loads(response.get_body())
        assert task["title"] == "Updated"
        assert task["priority"] == 5

    def test_update_nonexistent_task_returns_404(self) -> None:
        request = func.HttpRequest(
            method="PATCH",
            url="/api/tasks/999",
            body=json.dumps({"done": True}).encode(),
            headers={"Content-Type": "application/json"},
            route_params={"task_id": "999"},
        )
        response = self.mod.update_task(request)
        assert response.status_code == 404

    def test_update_invalid_body_returns_422(self) -> None:
        request = func.HttpRequest(
            method="PATCH",
            url="/api/tasks/1",
            body=json.dumps({"priority": 99}).encode(),
            headers={"Content-Type": "application/json"},
            route_params={"task_id": "1"},
        )
        response = self.mod.update_task(request)
        assert response.status_code == 422


class TestCrudDeleteTask:
    """DELETE /api/tasks/{task_id} — HttpResponse bypass (204)."""

    def setup_method(self) -> None:
        self.mod = _crud_module()
        _reset_crud_state(self.mod)

    def test_delete_existing_task(self) -> None:
        request = func.HttpRequest(
            method="DELETE",
            url="/api/tasks/1",
            body=b"",
            headers={},
            route_params={"task_id": "1"},
        )
        response = self.mod.delete_task(request)
        assert response.status_code == 204
        assert 1 not in self.mod._TASKS

    def test_delete_nonexistent_task_still_204(self) -> None:
        request = func.HttpRequest(
            method="DELETE",
            url="/api/tasks/999",
            body=b"",
            headers={},
            route_params={"task_id": "999"},
        )
        response = self.mod.delete_task(request)
        assert response.status_code == 204

    def test_delete_invalid_task_id_returns_422(self) -> None:
        request = func.HttpRequest(
            method="DELETE",
            url="/api/tasks/0",
            body=b"",
            headers={},
            route_params={"task_id": "0"},
        )
        response = self.mod.delete_task(request)
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# E2E App example
# ---------------------------------------------------------------------------


def test_e2e_app_health_endpoint() -> None:
    function_app = _load_example_module("e2e_app")
    request = func.HttpRequest(
        method="GET",
        url="/api/health",
        body=b"",
        headers={},
    )
    response = function_app.health(request)
    assert response.status_code == 200
    assert json.loads(response.get_body()) == {"status": "ok"}


def test_e2e_app_create_item_success() -> None:
    function_app = _load_example_module("e2e_app")
    request = func.HttpRequest(
        method="POST",
        url="/api/items",
        body=json.dumps({"name": "Widget", "quantity": 5}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    response = function_app.create_item(request)
    assert response.status_code == 200
    payload = json.loads(response.get_body())
    assert payload == {"id": 1, "name": "Widget", "quantity": 5}


def test_e2e_app_create_item_validation_error() -> None:
    function_app = _load_example_module("e2e_app")
    request = func.HttpRequest(
        method="POST",
        url="/api/items",
        body=json.dumps({"name": "", "quantity": 0}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    response = function_app.create_item(request)
    assert response.status_code == 422
    assert "detail" in json.loads(response.get_body())


# ---------------------------------------------------------------------------
# README Quick Start - docs <-> runtime sync verification
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_README_FILES = [
    "README.md",
    "README.ko.md",
    "README.ja.md",
    "README.zh-CN.md",
]


def _extract_quickstart_code(readme_path: Path) -> str:
    import re

    text = readme_path.read_text(encoding="utf-8")
    qs_match = re.search(r"^## Quick Start\s*$", text, re.MULTILINE)
    if qs_match is None:
        raise ValueError(f"No '## Quick Start' section in {readme_path.name}")

    after_qs = text[qs_match.end() :]
    code_match = re.search(r"```python\n(.*?)```", after_qs, re.DOTALL)
    if code_match is None:
        raise ValueError(f"No python code block in Quick Start of {readme_path.name}")

    return code_match.group(1)


class TestReadmeQuickStart:
    def test_quickstart_code_compiles(self) -> None:
        code = _extract_quickstart_code(_PROJECT_ROOT / "README.md")
        compile(code, "README.md-quick-start", "exec")

    def test_quickstart_imports_resolve(self) -> None:
        import importlib

        validate_http = getattr(
            importlib.import_module("azure_functions_validation"),
            "validate_http",
        )
        base_model = getattr(importlib.import_module("pydantic"), "BaseModel")

        assert callable(validate_http)
        assert isinstance(base_model, type)

    def test_quickstart_decorated_function_works(self) -> None:
        code = _extract_quickstart_code(_PROJECT_ROOT / "README.md")
        namespace: dict[str, Any] = {}
        exec(code, namespace)

        create_user = namespace["create_user"]
        request = func.HttpRequest(
            method="POST",
            url="/api/users",
            body=json.dumps({"name": "Azure", "email": "test@example.com"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        response = create_user(request)
        assert response.status_code == 200
        payload = json.loads(response.get_body())
        assert payload["message"] == "Hello Azure"
        assert payload["status"] == "success"

    def test_quickstart_validation_error(self) -> None:
        code = _extract_quickstart_code(_PROJECT_ROOT / "README.md")
        namespace: dict[str, Any] = {}
        exec(code, namespace)

        create_user = namespace["create_user"]
        request = func.HttpRequest(
            method="POST",
            url="/api/users",
            body=json.dumps({}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        response = create_user(request)
        assert response.status_code == 422

    def test_all_readme_variants_have_identical_quickstart(self) -> None:
        codes = {}
        for name in _README_FILES:
            path = _PROJECT_ROOT / name
            if path.exists():
                codes[name] = _extract_quickstart_code(path)

        assert len(codes) >= 2, "Expected at least 2 README variants"
        reference = codes["README.md"]
        for name, code in codes.items():
            assert code == reference, f"{name} Quick Start differs from README.md"
