"""Tests for the validation pipeline (request parsing, response building).

These tests exercise the runtime behaviour of ``validate_http``-decorated
handlers.  They were originally part of ``test_decorator.py`` and cover
request body/query/path/header parsing, error responses, custom formatters,
async handlers, and response model validation — all of which now live in
``pipeline.py``.
"""

import asyncio
import json
import logging
import json
from typing import Callable, TypeAlias
from unittest.mock import Mock

from azure.functions import HttpRequest
from pydantic import BaseModel, Field
import pytest

from azure_functions_validation import validate_http

RequestFactory: TypeAlias = Callable[..., HttpRequest]


# ---------------------------------------------------------------------------
# Test models
# ---------------------------------------------------------------------------


class UserModel(BaseModel):
    """Test model for user data."""

    name: str = Field(min_length=3, max_length=50)
    age: int = Field(ge=0, le=150)


class ResponseModel(BaseModel):
    """Test model for response data."""

    message: str
    status: str = "success"


class ItemResponseModel(BaseModel):
    """Test model for list response validation."""

    id: int
    name: str


class QueryModel(BaseModel):
    """Test model for query parameters."""

    limit: int = Field(ge=1, le=100, default=10)
    offset: int = Field(ge=0, default=0)


class PathModel(BaseModel):
    """Test model for path parameters."""

    user_id: int = Field(ge=1)


class HeaderModel(BaseModel):
    """Test model for headers."""

    authorization: str
    user_agent: str = Field(default="unknown")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


# ``mock_request_factory`` is provided by ``tests/conftest.py``.

# ---------------------------------------------------------------------------
# Successful validation
# ---------------------------------------------------------------------------


class TestSuccessfulValidation:
    """Tests for successful request/response validation."""

    def test_custom_request_parameter_name(self, mock_request_factory: RequestFactory) -> None:
        """Test body validation with a non-standard request parameter name."""

        @validate_http(body=UserModel)
        def handler(request: HttpRequest, body: UserModel) -> ResponseModel:
            return ResponseModel(message=f"Hello, {body.name}")

        request = mock_request_factory(body=b'{"name": "Taylor", "age": 29}')
        response = handler(request)

        assert response.status_code == 200
        data = json.loads(response.get_body().decode())
        assert data["message"] == "Hello, Taylor"

    def test_first_parameter_named_http_request(self, mock_request_factory: RequestFactory) -> None:
        """Test that the first request parameter can be named http_request."""

        @validate_http(body=UserModel)
        def handler(http_request: HttpRequest, body: UserModel) -> ResponseModel:
            return ResponseModel(message=f"Hello, {body.name}")

        request = mock_request_factory(body=b'{"name": "Jordan", "age": 31}')
        response = handler(request)

        assert response.status_code == 200
        data = json.loads(response.get_body().decode())
        assert data["message"] == "Hello, Jordan"

    def test_request_can_be_passed_by_keyword(self, mock_request_factory: RequestFactory) -> None:
        """Test that the primary request parameter can be passed via kwargs."""

        @validate_http(body=UserModel)
        def handler(request: HttpRequest, body: UserModel) -> ResponseModel:
            return ResponseModel(message=f"Hello, {body.name}")

        request = mock_request_factory(body=b'{"name": "Taylor", "age": 29}')
        response = handler(request=request)

        assert response.status_code == 200
        data = json.loads(response.get_body().decode())
        assert data["message"] == "Hello, Taylor"

    def test_http_request_alias_can_be_passed_by_keyword(
        self, mock_request_factory: RequestFactory
    ) -> None:
        """Test that the http_request alias can be passed via kwargs."""

        @validate_http(body=UserModel)
        def handler(http_request: HttpRequest, body: UserModel) -> ResponseModel:
            return ResponseModel(message=f"Hello, {body.name}")

        request = mock_request_factory(body=b'{"name": "Jordan", "age": 31}')
        response = handler(http_request=request)

        assert response.status_code == 200
        data = json.loads(response.get_body().decode())
        assert data["message"] == "Hello, Jordan"

    def test_request_model_shorthand_maps_to_req_model_parameter(
        self, mock_request_factory: RequestFactory
    ) -> None:
        @validate_http(request_model=UserModel)
        def handler(req: HttpRequest, req_model: UserModel) -> ResponseModel:
            return ResponseModel(message=f"Hello, {req_model.name}")

        request = mock_request_factory(body=b'{"name": "Nova", "age": 20}')
        response = handler(request)

        assert response.status_code == 200
        data = json.loads(response.get_body().decode())
        assert data["message"] == "Hello, Nova"

    def test_request_model_emits_deprecation_warning(
        self, mock_request_factory: RequestFactory
    ) -> None:
        with pytest.warns(DeprecationWarning, match="request_model"):

            @validate_http(request_model=UserModel)
            def handler(req: HttpRequest, req_model: UserModel) -> ResponseModel:
                return ResponseModel(message=f"Hello, {req_model.name}")

    def test_body_param_does_not_warn(
        self, mock_request_factory: RequestFactory
    ) -> None:
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("error", DeprecationWarning)

            @validate_http(body=UserModel)
            def handler(req: HttpRequest, body: UserModel) -> ResponseModel:
                return ResponseModel(message=f"Hello, {body.name}")

    def test_basic_body_validation(self, mock_request_factory: RequestFactory) -> None:
        """Test basic body validation."""

        @validate_http(body=UserModel)
        def handler(req: HttpRequest, body: UserModel) -> ResponseModel:
            return ResponseModel(message=f"Hello, {body.name}")

        request = mock_request_factory(body=b'{"name": "Alice", "age": 30}')
        response = handler(request)

        assert response.status_code == 200
        data = json.loads(response.get_body().decode())
        assert data["message"] == "Hello, Alice"

    def test_query_validation(self, mock_request_factory: RequestFactory) -> None:
        """Test query parameter validation."""

        @validate_http(body=UserModel, query=QueryModel)
        def handler(req: HttpRequest, body: UserModel, query: QueryModel) -> ResponseModel:
            return ResponseModel(message=f"Hello, {body.name}")

        request = mock_request_factory(
            body=b'{"name": "Bob", "age": 25}',
            params={"limit": "10", "offset": "0"},
        )
        response = handler(request)

        assert response.status_code == 200

    def test_path_validation(self, mock_request_factory: RequestFactory) -> None:
        """Test path parameter validation."""

        @validate_http(body=UserModel, path=PathModel)
        def handler(req: HttpRequest, body: UserModel, path: PathModel) -> ResponseModel:
            return ResponseModel(message=f"Hello, {body.name}")

        request = mock_request_factory(
            body=b'{"name": "Charlie", "age": 35}', route_params={"user_id": "42"}
        )
        response = handler(request)

        assert response.status_code == 200

    def test_headers_validation(self, mock_request_factory: RequestFactory) -> None:
        """Test headers validation."""

        @validate_http(body=UserModel, headers=HeaderModel)
        def handler(req: HttpRequest, body: UserModel, headers: HeaderModel) -> ResponseModel:
            return ResponseModel(message=f"Hello, {body.name}")

        request = mock_request_factory(
            body=b'{"name": "David", "age": 28}',
            headers={"authorization": "Bearer token123", "user_agent": "Mozilla"},
        )
        response = handler(request)

        assert response.status_code == 200

    def test_list_response_model_validation(self, mock_request_factory: RequestFactory) -> None:
        """Test list response validation with a generic response model."""

        @validate_http(response_model=list[ItemResponseModel])
        def handler(req: HttpRequest) -> list[dict[str, object]]:
            return [
                {"id": 1, "name": "Alice"},
                {"id": 2, "name": "Bob"},
            ]

        request = mock_request_factory()
        response = handler(request)

        assert response.status_code == 200
        data = json.loads(response.get_body().decode())
        assert data == [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
        ]

    def test_request_inputs_are_parsed_once(self, mock_request_factory: RequestFactory) -> None:
        """Test that configured request inputs are parsed only once."""

        adapter = Mock()
        adapter.parse_body.return_value = UserModel(name="Robin", age=26)
        adapter.parse_query.return_value = QueryModel(limit=10, offset=0)
        adapter.parse_path.return_value = PathModel(user_id=42)
        adapter.parse_headers.return_value = HeaderModel(
            authorization="Bearer token123",
            user_agent="Mozilla",
        )
        adapter.serialize.return_value = (json.dumps({"message": "ok"}), "application/json")

        @validate_http(
            body=UserModel,
            query=QueryModel,
            path=PathModel,
            headers=HeaderModel,
            adapter=adapter,
        )
        def handler(
            req: HttpRequest,
            body: UserModel,
            query: QueryModel,
            path: PathModel,
            headers: HeaderModel,
        ) -> dict[str, str]:
            return {"message": "ok"}

        request = mock_request_factory(
            body=b'{"name": "Robin", "age": 26}',
            params={"limit": "10", "offset": "0"},
            route_params={"user_id": "42"},
            headers={"authorization": "Bearer token123", "user_agent": "Mozilla"},
        )
        response = handler(request)

        assert response.status_code == 200
        adapter.parse_body.assert_called_once_with(request, UserModel)
        adapter.parse_query.assert_called_once_with(request, QueryModel)
        adapter.parse_path.assert_called_once_with(request, PathModel)
        adapter.parse_headers.assert_called_once_with(request, HeaderModel)

    def test_http_request_alias_kwarg_for_non_alias_request_name(
        self, mock_request_factory: RequestFactory
    ) -> None:
        @validate_http(body=UserModel)
        def handler(request: HttpRequest, body: UserModel, **kwargs: object) -> ResponseModel:
            return ResponseModel(message=f"Hello, {body.name}")

        request = mock_request_factory(body=b'{"name": "Sky", "age": 22}')
        response = handler(request="placeholder", http_request=request)

        assert response.status_code == 200
        data = json.loads(response.get_body().decode())
        assert data["message"] == "Hello, Sky"

    def test_http_request_can_be_resolved_from_any_kwarg_value(
        self, mock_request_factory: RequestFactory
    ) -> None:
        @validate_http(body=UserModel)
        def handler(req: object, body: UserModel, **kwargs: object) -> ResponseModel:
            return ResponseModel(message=f"Hello, {body.name}")

        request = mock_request_factory(body=b'{"name": "Pax", "age": 45}')
        response = handler(req="placeholder", client=request)

        assert response.status_code == 200
        data = json.loads(response.get_body().decode())
        assert data["message"] == "Hello, Pax"

    def test_body_fallback_parameter_ignores_reserved_names(
        self, mock_request_factory: RequestFactory
    ) -> None:
        @validate_http(body=UserModel, query=QueryModel)
        def handler(req: HttpRequest, body: UserModel, query: QueryModel) -> ResponseModel:
            return ResponseModel(message=f"{body.name}:{query.limit}")

        request = mock_request_factory(
            body=b'{"name": "Rae", "age": 33}',
            params={"limit": "7", "offset": "0"},
        )
        response = handler(request)

        assert response.status_code == 200
        data = json.loads(response.get_body().decode())
        assert data["message"] == "Rae:7"


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------


class TestValidationErrors:
    """Tests for validation error responses."""

    def test_body_validation_error(self, mock_request_factory: RequestFactory) -> None:
        """Test 422 error for invalid body."""

        @validate_http(body=UserModel)
        def handler(req: HttpRequest, body: UserModel) -> ResponseModel:
            return ResponseModel(message="ok")

        request = mock_request_factory(body=b'{"name": "ab", "age": 30}')
        response = handler(request)

        assert response.status_code == 422

        data = json.loads(response.get_body().decode())
        assert "detail" in data
        assert any(
            error["type"] in ["string_too_short", "too_small", "too_large"]
            for error in data["detail"]
        )

    def test_query_validation_error(self, mock_request_factory: RequestFactory) -> None:
        """Test 422 error for invalid query params."""

        @validate_http(query=QueryModel)
        def handler(req: HttpRequest, query: QueryModel) -> ResponseModel:
            return ResponseModel(message="ok")

        request = mock_request_factory(params={"limit": "0"})
        response = handler(request)

        assert response.status_code == 422

        data = json.loads(response.get_body().decode())
        assert "detail" in data

    def test_path_validation_error(self, mock_request_factory: RequestFactory) -> None:
        """Test 422 error for invalid path params."""

        @validate_http(path=PathModel)
        def handler(req: HttpRequest, path: PathModel) -> ResponseModel:
            return ResponseModel(message="ok")

        request = mock_request_factory(route_params={"user_id": "0"})
        response = handler(request)

        assert response.status_code == 422

        data = json.loads(response.get_body().decode())
        assert "detail" in data

    def test_headers_validation_error(self, mock_request_factory: RequestFactory) -> None:
        """Test 422 error for invalid headers."""

        @validate_http(headers=HeaderModel)
        def handler(req: HttpRequest, headers: HeaderModel) -> ResponseModel:
            return ResponseModel(message="ok")

        request = mock_request_factory()
        response = handler(request)

        assert response.status_code == 422

        data = json.loads(response.get_body().decode())
        assert "detail" in data

    def test_json_parsing_error(self, mock_request_factory: RequestFactory) -> None:
        """Test 400 error for malformed JSON."""

        @validate_http(body=UserModel)
        def handler(req: HttpRequest, body: UserModel) -> ResponseModel:
            return ResponseModel(message="ok")

        request = mock_request_factory(body=b"invalid json")
        response = handler(request)

        assert response.status_code == 400

        data = json.loads(response.get_body().decode())
        assert "detail" in data

    def test_missing_http_request_like_argument_returns_400(self) -> None:
        @validate_http(body=UserModel)
        def handler(req: HttpRequest, body: UserModel) -> ResponseModel:
            return ResponseModel(message="ok")

        response = handler(req="not-a-request")

        assert response.status_code == 400
        data = json.loads(response.get_body().decode())
        assert "detail" in data

    def test_non_value_error_body_parse_returns_500(
        self, mock_request_factory: RequestFactory
    ) -> None:
        adapter = Mock()
        adapter.parse_body.side_effect = RuntimeError("adapter exploded")

        @validate_http(body=UserModel, adapter=adapter)
        def handler(req: HttpRequest, body: UserModel) -> ResponseModel:
            return ResponseModel(message="ok")

        request = mock_request_factory(body=b'{"name": "Valid", "age": 30}')
        response = handler(request)

        assert response.status_code == 500
        data = json.loads(response.get_body().decode())
        assert data["detail"][0]["msg"] == "Internal Server Error"

    def test_all_validation_sources(self, mock_request_factory: RequestFactory) -> None:
        """Test validation of all input sources at once."""

        @validate_http(body=UserModel, query=QueryModel, path=PathModel, headers=HeaderModel)
        def handler(
            req: HttpRequest,
            body: UserModel,
            query: QueryModel,
            path: PathModel,
            headers: HeaderModel,
        ) -> ResponseModel:
            return ResponseModel(message="ok")

        request = mock_request_factory(
            body=b'{"name": "Eve", "age": 27}',
            params={"limit": "5"},
            route_params={"user_id": "100"},
            headers={"authorization": "Bearer token123", "user_agent": "Mozilla"},
        )
        response = handler(request)

        assert response.status_code == 200

    def test_validation_error_location(self, mock_request_factory: RequestFactory) -> None:
        """Error location is reported in the ``loc`` field (format-tolerant across Pydantic v2)."""

        @validate_http(body=UserModel)
        def handler(req: HttpRequest, body: UserModel) -> ResponseModel:
            return ResponseModel(message="ok")

        request = mock_request_factory(body=b'{"age": 30}')
        response = handler(request)

        assert response.status_code == 422

        data = json.loads(response.get_body().decode())
        assert any("name" in str(error.get("loc", [])) for error in data["detail"])


# ---------------------------------------------------------------------------
# Error hierarchy for non-body sources (query, path, headers)
# ---------------------------------------------------------------------------


class TestNonBodyErrorHierarchy:
    """Tests that ValueError→400 and Exception→500 branches work for query/path/headers."""

    def test_query_value_error_returns_400(self, mock_request_factory: RequestFactory) -> None:
        adapter = Mock()
        adapter.parse_query.side_effect = ValueError("bad query param")
        adapter.format_error.return_value = {
            "detail": [{"loc": [], "msg": "bad query param", "type": "value_error"}]
        }

        @validate_http(query=QueryModel, adapter=adapter)
        def handler(req: HttpRequest, query: QueryModel) -> ResponseModel:
            return ResponseModel(message="ok")

        request = mock_request_factory(params={"limit": "10"})
        response = handler(request)

        assert response.status_code == 400
        data = json.loads(response.get_body().decode())
        assert data["detail"][0]["msg"] == "bad query param"

    def test_query_generic_exception_returns_500(
        self, mock_request_factory: RequestFactory
    ) -> None:
        adapter = Mock()
        adapter.parse_query.side_effect = RuntimeError("query exploded")

        @validate_http(query=QueryModel, adapter=adapter)
        def handler(req: HttpRequest, query: QueryModel) -> ResponseModel:
            return ResponseModel(message="ok")

        request = mock_request_factory(params={"limit": "10"})
        response = handler(request)

        assert response.status_code == 500
        data = json.loads(response.get_body().decode())
        assert data["detail"][0]["msg"] == "Internal Server Error"

    def test_path_value_error_returns_400(self, mock_request_factory: RequestFactory) -> None:
        adapter = Mock()
        adapter.parse_path.side_effect = ValueError("bad path param")
        adapter.format_error.return_value = {
            "detail": [{"loc": [], "msg": "bad path param", "type": "value_error"}]
        }

        @validate_http(path=PathModel, adapter=adapter)
        def handler(req: HttpRequest, path: PathModel) -> ResponseModel:
            return ResponseModel(message="ok")

        request = mock_request_factory(route_params={"user_id": "1"})
        response = handler(request)

        assert response.status_code == 400
        data = json.loads(response.get_body().decode())
        assert data["detail"][0]["msg"] == "bad path param"

    def test_path_generic_exception_returns_500(self, mock_request_factory: RequestFactory) -> None:
        adapter = Mock()
        adapter.parse_path.side_effect = RuntimeError("path exploded")

        @validate_http(path=PathModel, adapter=adapter)
        def handler(req: HttpRequest, path: PathModel) -> ResponseModel:
            return ResponseModel(message="ok")

        request = mock_request_factory(route_params={"user_id": "1"})
        response = handler(request)

        assert response.status_code == 500
        data = json.loads(response.get_body().decode())
        assert data["detail"][0]["msg"] == "Internal Server Error"

    def test_headers_value_error_returns_400(self, mock_request_factory: RequestFactory) -> None:
        adapter = Mock()
        adapter.parse_headers.side_effect = ValueError("bad header")
        adapter.format_error.return_value = {
            "detail": [{"loc": [], "msg": "bad header", "type": "value_error"}]
        }

        @validate_http(headers=HeaderModel, adapter=adapter)
        def handler(req: HttpRequest, headers: HeaderModel) -> ResponseModel:
            return ResponseModel(message="ok")

        request = mock_request_factory(headers={"authorization": "Bearer x"})
        response = handler(request)

        assert response.status_code == 400
        data = json.loads(response.get_body().decode())
        assert data["detail"][0]["msg"] == "bad header"

    def test_headers_generic_exception_returns_500(
        self, mock_request_factory: RequestFactory
    ) -> None:
        adapter = Mock()
        adapter.parse_headers.side_effect = RuntimeError("headers exploded")

        @validate_http(headers=HeaderModel, adapter=adapter)
        def handler(req: HttpRequest, headers: HeaderModel) -> ResponseModel:
            return ResponseModel(message="ok")

        request = mock_request_factory(headers={"authorization": "Bearer x"})
        response = handler(request)

        assert response.status_code == 500
        data = json.loads(response.get_body().decode())
        assert data["detail"][0]["msg"] == "Internal Server Error"


# ---------------------------------------------------------------------------
# Async handler support
# ---------------------------------------------------------------------------


class TestAsyncHandlers:
    """Tests for async handler support."""

    @pytest.mark.anyio
    async def test_async_handler(
        self,
        mock_request_factory: RequestFactory,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test async handler support without asyncio.run inside the decorator."""

        def fail_asyncio_run(*args: object, **kwargs: object) -> object:
            raise AssertionError("validate_http should not call asyncio.run() internally")

        monkeypatch.setattr(asyncio, "run", fail_asyncio_run)

        @validate_http(body=UserModel)
        async def async_handler(req: HttpRequest, body: UserModel) -> ResponseModel:
            return ResponseModel(message=f"Hello, {body.name}")

        request = mock_request_factory(body=b'{"name": "Lucas", "age": 32}')
        response = await async_handler(request)

        assert response.status_code == 200
        data = json.loads(response.get_body().decode())
        assert data["message"] == "Hello, Lucas"

    @pytest.mark.anyio
    async def test_async_handler_with_kwargs_only(
        self, mock_request_factory: RequestFactory
    ) -> None:
        @validate_http(body=UserModel)
        async def async_handler(request: HttpRequest, body: UserModel) -> ResponseModel:
            return ResponseModel(message=f"Hello, {body.name}")

        request = mock_request_factory(body=b'{"name": "Quinn", "age": 38}')
        response = await async_handler(request=request)

        assert response.status_code == 200
        data = json.loads(response.get_body().decode())
        assert data["message"] == "Hello, Quinn"


# ---------------------------------------------------------------------------
# HttpRequest injection
# ---------------------------------------------------------------------------


class TestHttpRequestInjection:
    """Tests for injecting the original HttpRequest."""

    def test_httprequest_injectable(self, mock_request_factory: RequestFactory) -> None:
        """Test that original HttpRequest can be accessed."""

        @validate_http(body=UserModel)
        def handler(req: HttpRequest, body: UserModel, http_request: HttpRequest) -> ResponseModel:
            user_agent = http_request.headers.get("User-Agent", "unknown")
            return ResponseModel(message=f"Hello, {body.name} (UA: {user_agent})")

        request = mock_request_factory(body=b'{"name": "Mia", "age": 24}')
        response = handler(request)

        assert response.status_code == 200

        data = json.loads(response.get_body().decode())
        assert "UA:" in data["message"]


# ---------------------------------------------------------------------------
# Custom error formatter
# ---------------------------------------------------------------------------


class TestCustomErrorFormatter:
    """Tests for custom error formatter functionality."""

    def test_custom_formatter_for_validation_error(
        self, mock_request_factory: RequestFactory
    ) -> None:
        """Test custom error formatter for validation errors."""

        def custom_formatter(exc: Exception, status_code: int) -> dict[str, object]:
            return {
                "custom": True,
                "code": f"ERR_{status_code}",
                "message": str(exc),
            }

        @validate_http(body=UserModel, error_formatter=custom_formatter)
        def handler(req: HttpRequest, body: UserModel) -> dict[str, object]:
            return {"message": "ok"}

        request = mock_request_factory(body=b'{"name": "ab", "age": 30}')
        response = handler(request)

        assert response.status_code == 422

        data = json.loads(response.get_body().decode())
        assert data["custom"] is True
        assert data["code"] == "ERR_422"
        assert "string_too_short" in data["message"] or "min_length" in data["message"]

    def test_custom_formatter_for_json_error(self, mock_request_factory: RequestFactory) -> None:
        """Test custom error formatter for JSON parsing errors."""

        def custom_formatter(exc: Exception, status_code: int) -> dict[str, object]:
            return {
                "error": "JSON_ERROR",
                "status": status_code,
                "details": str(exc),
            }

        @validate_http(body=UserModel, error_formatter=custom_formatter)
        def handler(req: HttpRequest, body: UserModel) -> dict[str, object]:
            return {"message": "ok"}

        request = mock_request_factory(body=b"invalid json")
        response = handler(request)

        assert response.status_code == 400

        data = json.loads(response.get_body().decode())
        assert data["error"] == "JSON_ERROR"
        assert data["status"] == 400

    def test_default_formatter_when_not_provided(
        self, mock_request_factory: RequestFactory
    ) -> None:
        """Test default FastAPI-style formatter when custom formatter not provided."""

        @validate_http(body=UserModel)
        def handler(req: HttpRequest, body: UserModel) -> dict[str, object]:
            return {"message": "ok"}

        request = mock_request_factory(body=b'{"name": "ab", "age": 30}')
        response = handler(request)

        assert response.status_code == 422

        data = json.loads(response.get_body().decode())
        assert "detail" in data
        assert len(data["detail"]) > 0
        assert "loc" in data["detail"][0]
        assert "msg" in data["detail"][0]
        assert "type" in data["detail"][0]

    def test_custom_formatter_for_response_validation_error(
        self, mock_request_factory: RequestFactory
    ) -> None:
        """Test custom error formatter for response validation errors."""

        def custom_formatter(exc: Exception, status_code: int) -> dict[str, object]:
            return {
                "error_type": "CONTRACT_VIOLATION",
                "http_status": status_code,
            }

        class ResponseModel(BaseModel):
            message: str

        @validate_http(
            body=UserModel,
            response_model=ResponseModel,
            error_formatter=custom_formatter,
        )
        def handler(req: HttpRequest, body: UserModel) -> dict[str, object]:
            return {"invalid": "data"}

        request = mock_request_factory(body=b'{"name": "Frank", "age": 40}')
        response = handler(request)

        assert response.status_code == 500

        data = json.loads(response.get_body().decode())
        assert data["error_type"] == "CONTRACT_VIOLATION"
        assert data["http_status"] == 500

    def test_response_validation_failure_is_logged_with_exc_info(
        self, mock_request_factory: RequestFactory, caplog: pytest.LogCaptureFixture
    ) -> None:
        """A response-validation 500 must leave a log record with exception info (#250)."""

        class ResponseModel(BaseModel):
            message: str

        @validate_http(body=UserModel, response_model=ResponseModel)
        def handler(req: HttpRequest, body: UserModel) -> dict[str, object]:
            return {"invalid": "data"}

        request = mock_request_factory(body=b'{"name": "Frank", "age": 40}')
        with caplog.at_level(logging.ERROR, logger="azure_functions_validation.pipeline"):
            response = handler(request)

        assert response.status_code == 500
        records = [r for r in caplog.records if r.levelno == logging.ERROR]
        assert records, "expected an ERROR log record for the response-validation failure"
        assert any(r.exc_info is not None for r in records), (
            "expected exc_info to be attached so the cause is visible in App Insights"
        )


# ---------------------------------------------------------------------------
# None return → 204 (Issue #98)
# ---------------------------------------------------------------------------


class TestNoneReturn:
    """Tests for None return type producing 204 No Content."""

    def test_none_return_gives_204(
        self, mock_request_factory: RequestFactory,
    ) -> None:
        """Test that returning None produces a 204 response."""

        @validate_http()
        def handler(req: HttpRequest) -> None:
            return None

        request = mock_request_factory()
        response = handler(request)

        assert response.status_code == 204

    def test_none_return_with_response_model_gives_204(
        self, mock_request_factory: RequestFactory,
    ) -> None:
        """Test that None return bypasses response model validation with 204."""

        @validate_http(response_model=ResponseModel)
        def handler(req: HttpRequest) -> None:
            return None

        request = mock_request_factory()
        response = handler(request)

        assert response.status_code == 204


class TestScalarReturn:
    """Tests for scalar return types (Issue #98)."""

    def test_int_return(self, mock_request_factory: RequestFactory) -> None:
        @validate_http()
        def handler(req: HttpRequest) -> int:
            return 42

        request = mock_request_factory()
        response = handler(request)

        assert response.status_code == 200
        data = json.loads(response.get_body().decode())
        assert data == 42

    def test_float_return(
        self, mock_request_factory: RequestFactory,
    ) -> None:
        @validate_http()
        def handler(req: HttpRequest) -> float:
            return 3.14

        request = mock_request_factory()
        response = handler(request)

        assert response.status_code == 200
        data = json.loads(response.get_body().decode())
        assert data == 3.14

    def test_bool_return(
        self, mock_request_factory: RequestFactory,
    ) -> None:
        @validate_http()
        def handler(req: HttpRequest) -> bool:
            return True

        request = mock_request_factory()
        response = handler(request)

        assert response.status_code == 200
        data = json.loads(response.get_body().decode())
        assert data is True


class TestDataclassReturn:
    """Tests for dataclass return type (Issue #98)."""

    def test_dataclass_return_serializes_to_json(
        self, mock_request_factory: RequestFactory,
    ) -> None:
        import dataclasses

        @dataclasses.dataclass
        class Point:
            x: int
            y: int

        @validate_http()
        def handler(req: HttpRequest) -> Point:
            return Point(x=1, y=2)

        request = mock_request_factory()
        response = handler(request)

        assert response.status_code == 200
        data = json.loads(response.get_body().decode())
        assert data == {"x": 1, "y": 2}


# ---------------------------------------------------------------------------
# Error path normalization (Issue #99)
# ---------------------------------------------------------------------------


class TestErrorPathNormalization:
    """Tests for normalized error handling (Issue #99)."""

    def test_resolve_http_request_error_returns_400(
        self, mock_request_factory: RequestFactory,
    ) -> None:
        """Test that _resolve_http_request ValueError produces 400."""

        @validate_http(body=UserModel)
        def handler(req: HttpRequest, body: UserModel) -> ResponseModel:
            return ResponseModel(message="ok")

        # Pass non-HttpRequest-like to trigger ValueError
        response = handler(req="not-a-request")

        assert response.status_code == 400
        data = json.loads(response.get_body().decode())
        assert "detail" in data

    def test_serialization_error_without_response_model_returns_500(
        self, mock_request_factory: RequestFactory,
    ) -> None:
        """Test that unsupported return type without response_model returns 500."""

        @validate_http()
        def handler(req: HttpRequest) -> object:
            return object()

        request = mock_request_factory()
        response = handler(request)

        assert response.status_code == 500
        data = json.loads(response.get_body().decode())
        assert "detail" in data

    def test_serialization_error_with_response_model_returns_500(
        self, mock_request_factory: RequestFactory,
    ) -> None:
        """Test serialization failure after validation returns structured 500."""
        adapter = Mock()
        adapter.validate_response.return_value = object()
        adapter.serialize.side_effect = TypeError(
            "Cannot serialize type object",
        )

        @validate_http(response_model=ResponseModel, adapter=adapter)
        def handler(req: HttpRequest) -> object:
            return object()

        request = mock_request_factory()
        response = handler(request)

        assert response.status_code == 500
        data = json.loads(response.get_body().decode())
        assert "detail" in data



# ---------------------------------------------------------------------------
# Success status_code + public HttpError (Issue #254)
# ---------------------------------------------------------------------------


class TestSuccessStatusCode:
    """``status_code=`` overrides the default 200 on the success path."""

    def test_status_code_applies_with_response_model(
        self, mock_request_factory: RequestFactory,
    ) -> None:
        @validate_http(body=UserModel, response_model=ResponseModel, status_code=201)
        def handler(req: HttpRequest, body: UserModel) -> ResponseModel:
            return ResponseModel(message=f"created {body.name}")

        response = handler(mock_request_factory(body=b'{"name": "Alice", "age": 30}'))
        assert response.status_code == 201
        data = json.loads(response.get_body().decode())
        assert data["message"] == "created Alice"

    def test_status_code_applies_without_response_model(
        self, mock_request_factory: RequestFactory,
    ) -> None:
        @validate_http(body=UserModel, status_code=202)
        def handler(req: HttpRequest, body: UserModel) -> dict[str, str]:
            return {"name": body.name}

        response = handler(mock_request_factory(body=b'{"name": "Bob", "age": 40}'))
        assert response.status_code == 202

    def test_default_status_code_is_200(
        self, mock_request_factory: RequestFactory,
    ) -> None:
        @validate_http(body=UserModel, response_model=ResponseModel)
        def handler(req: HttpRequest, body: UserModel) -> ResponseModel:
            return ResponseModel(message="ok")

        response = handler(mock_request_factory(body=b'{"name": "Cara", "age": 22}'))
        assert response.status_code == 200


class TestHttpError:
    """Public ``HttpError`` renders through the standard error envelope."""

    def test_http_error_returns_status_and_envelope(
        self, mock_request_factory: RequestFactory,
    ) -> None:
        from azure_functions_validation import HttpError

        @validate_http(body=UserModel)
        def handler(req: HttpRequest, body: UserModel) -> ResponseModel:
            raise HttpError(404, "User not found")

        response = handler(mock_request_factory(body=b'{"name": "Dan", "age": 33}'))
        assert response.status_code == 404
        data = json.loads(response.get_body().decode())
        assert data["detail"] == [
            {"loc": [], "msg": "User not found", "type": "http_error"}
        ]

    def test_http_error_accepts_structured_detail(
        self, mock_request_factory: RequestFactory,
    ) -> None:
        from azure_functions_validation import HttpError

        detail = [{"loc": ["body", "name"], "msg": "taken", "type": "conflict"}]

        @validate_http(body=UserModel)
        def handler(req: HttpRequest, body: UserModel) -> ResponseModel:
            raise HttpError(409, detail)

        response = handler(mock_request_factory(body=b'{"name": "Eve", "age": 27}'))
        assert response.status_code == 409
        data = json.loads(response.get_body().decode())
        assert data["detail"] == detail

    def test_http_error_5xx_is_sanitized(
        self, mock_request_factory: RequestFactory,
    ) -> None:
        from azure_functions_validation import HttpError

        @validate_http(body=UserModel)
        def handler(req: HttpRequest, body: UserModel) -> ResponseModel:
            raise HttpError(503, "database down: secret-host:5432")

        response = handler(mock_request_factory(body=b'{"name": "Fay", "age": 44}'))
        assert response.status_code == 503
        data = json.loads(response.get_body().decode())
        # Internal detail must not leak on server errors.
        assert data["detail"][0]["msg"] == "Internal Server Error"
        assert "secret-host" not in json.dumps(data)

    @pytest.mark.anyio
    async def test_async_http_error(
        self, mock_request_factory: RequestFactory
    ) -> None:
        from azure_functions_validation import HttpError

        @validate_http(body=UserModel)
        async def handler(req: HttpRequest, body: UserModel) -> ResponseModel:
            raise HttpError(404, "missing")

        response = await handler(
            mock_request_factory(body=b'{"name": "Gus", "age": 51}')
        )
        assert response.status_code == 404
        data = json.loads(response.get_body().decode())
        assert data["detail"][0]["msg"] == "missing"