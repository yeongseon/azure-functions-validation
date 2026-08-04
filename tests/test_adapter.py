"""Tests for validation adapter."""

from typing import TYPE_CHECKING, Any, List, cast

import azure.functions as func
from pydantic import BaseModel, ConfigDict, Field
import pytest

from azure_functions_validation.adapter import PydanticAdapter
from azure_functions_validation.errors import AdapterValidationError

if TYPE_CHECKING:
    import pytest


# Test models
class UserModel(BaseModel):
    """Test model for user data."""

    name: str = Field(min_length=3, max_length=50)
    age: int = Field(ge=0, le=150)


class SimpleModel(BaseModel):
    """Simple test model."""

    message: str


class QueryModel(BaseModel):
    tag: str
    tags: List[str]


class HeaderModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    request_id: str = Field(alias="X-Request-Id")
    values: List[str] = Field(alias="X-Values")


# Fixtures
@pytest.fixture
def adapter() -> PydanticAdapter:
    """Create a PydanticAdapter instance."""
    return PydanticAdapter()


@pytest.fixture
def mock_request() -> type:
    """Create a mock HttpRequest class for testing."""

    class MockHttpRequest:
        """Mock Azure Functions HttpRequest."""

        def __init__(self, body: bytes = b""):
            self._body = body

        def get_body(self) -> bytes:
            return self._body

    return MockHttpRequest


# Test parse_body
class TestParseBody:
    """Tests for parse_body method."""

    def test_valid_json_body(self, adapter: PydanticAdapter, mock_request: type) -> None:
        """Test parsing valid JSON body."""
        req = mock_request(b'{"name": "Alice", "age": 30}')
        result = adapter.parse_body(req, UserModel)

        assert isinstance(result, UserModel)
        assert result.name == "Alice"
        assert result.age == 30

    def test_empty_body(self, adapter: PydanticAdapter, mock_request: type) -> None:
        """Test parsing empty body raises AdapterValidationError with type='missing'."""
        req = mock_request(b"")

        with pytest.raises(AdapterValidationError) as exc_info:
            adapter.parse_body(req, UserModel)

        errors = exc_info.value.errors
        assert len(errors) == 1
        assert errors[0]["type"] == "missing"
        assert errors[0]["loc"] == ["body"]

    def test_missing_body_error_is_stable_and_isolated(
        self, adapter: PydanticAdapter, mock_request: type
    ) -> None:
        """Repeated empty-body parses yield identical but independent errors."""
        errors = []
        for _ in range(2):
            with pytest.raises(AdapterValidationError) as exc_info:
                adapter.parse_body(mock_request(b""), UserModel)
            errors.append(exc_info.value.errors)

        # Identical normalized output across calls (hoisted, not regenerated).
        assert errors[0] == errors[1]
        assert errors[0] == [
            {"loc": ["body"], "msg": "Field required", "type": "missing"}
        ]
        # Fresh list per call — mutating one must not affect the next.
        assert errors[0] is not errors[1]
        errors[0].append({"tampered": True})
        with pytest.raises(AdapterValidationError) as exc_info:
            adapter.parse_body(mock_request(b""), UserModel)
        assert len(exc_info.value.errors) == 1

    def test_invalid_json(self, adapter: PydanticAdapter, mock_request: type) -> None:
        """Test parsing invalid JSON raises ValueError."""
        req = mock_request(b"{invalid json}")

        with pytest.raises(ValueError) as exc_info:
            adapter.parse_body(req, UserModel)

        assert "Invalid JSON" in str(exc_info.value)

    def test_validation_error_field_constraints(
        self, adapter: PydanticAdapter, mock_request: type
    ) -> None:
        """Test validation errors for field constraints."""
        # Name too short
        req = mock_request(b'{"name": "Al", "age": 30}')
        with pytest.raises(AdapterValidationError) as exc_info:
            adapter.parse_body(req, UserModel)

        errors = exc_info.value.errors
        assert any(e["type"] == "string_too_short" for e in errors)

    def test_validation_error_missing_field(
        self, adapter: PydanticAdapter, mock_request: type
    ) -> None:
        """Test validation errors for missing required field."""
        req = mock_request(b'{"name": "Alice"}')
        with pytest.raises(AdapterValidationError) as exc_info:
            adapter.parse_body(req, UserModel)

        errors = exc_info.value.errors
        assert any(e["type"] == "missing" for e in errors)

    def test_validation_error_wrong_type(
        self, adapter: PydanticAdapter, mock_request: type
    ) -> None:
        """Test validation errors for wrong field type."""
        req = mock_request(b'{"name": "Alice", "age": "not a number"}')
        with pytest.raises(AdapterValidationError) as exc_info:
            adapter.parse_body(req, UserModel)

        errors = exc_info.value.errors
        assert any("int_parsing" in e["type"] for e in errors)

    def test_whitespace_body_is_treated_as_missing(
        self, adapter: PydanticAdapter, mock_request: type
    ) -> None:
        req = mock_request(b"   ")

        with pytest.raises(AdapterValidationError) as exc_info:
            adapter.parse_body(req, UserModel)

        errors = exc_info.value.errors
        assert errors[0]["type"] == "missing"

    def test_invalid_utf8_body_raises_value_error(
        self, adapter: PydanticAdapter, mock_request: type
    ) -> None:
        """Test that non-UTF-8 body bytes raise ValueError, not UnicodeDecodeError."""
        req = mock_request(b"\x80\x81\x82")
        with pytest.raises(ValueError, match="Invalid JSON"):
            adapter.parse_body(req, UserModel)


# Test validate_response
class TestValidateResponse:
    """Tests for validate_response method."""

    def test_validate_basemodel_instance(self, adapter: PydanticAdapter) -> None:
        """Test validating BaseModel instance."""
        user = UserModel(name="Alice", age=30)
        result = adapter.validate_response(user, UserModel)

        assert result is user
        assert isinstance(result, UserModel)

    def test_validate_dict(self, adapter: PydanticAdapter) -> None:
        """Test validating dict against model."""
        data = {"name": "Bob", "age": 25}
        result = adapter.validate_response(data, UserModel)

        assert isinstance(result, UserModel)
        assert result.name == "Bob"
        assert result.age == 25

    def test_validate_dict_invalid(self, adapter: PydanticAdapter) -> None:
        """Test validating invalid dict raises AdapterValidationError."""
        data = {"name": "Al", "age": 25}  # Name too short

        with pytest.raises(AdapterValidationError) as exc_info:
            adapter.validate_response(data, UserModel)

        errors = exc_info.value.errors
        assert any(e["type"] == "string_too_short" for e in errors)

    def test_validate_invalid_type(self, adapter: PydanticAdapter) -> None:
        """Test validating invalid response type raises AdapterValidationError."""
        with pytest.raises(AdapterValidationError):
            adapter.validate_response("invalid", UserModel)

    def test_validate_list_of_dicts_against_list_type(self, adapter: PydanticAdapter) -> None:
        result = adapter.validate_response(
            [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}],
            list[UserModel],
        )

        assert len(result) == 2
        assert all(isinstance(item, UserModel) for item in result)

    def test_validate_list_of_any_returns_list(self, adapter: PydanticAdapter) -> None:
        """Test that list[Any] passes through a plain list."""
        payload = [{"name": "Alice", "age": 30}]
        result = adapter.validate_response(payload, list[Any])

        assert result == payload

    def test_validate_plain_list_type_returns_list(self, adapter: PydanticAdapter) -> None:
        """Test that plain list type validates and returns the list."""
        payload = [{"name": "Alice", "age": 30}]
        result = adapter.validate_response(payload, list)

        assert result == payload

    def test_validate_list_type_rejects_non_list_payload(self, adapter: PydanticAdapter) -> None:
        """Test that list[UserModel] rejects a dict payload."""
        with pytest.raises(AdapterValidationError):
            adapter.validate_response({"name": "Alice", "age": 30}, list[UserModel])


class TestRequestParsing:
    def test_parse_query_handles_scalar_values(self, adapter: PydanticAdapter) -> None:
        """Azure Functions params dict returns scalar values."""

        class ScalarQueryModel(BaseModel):
            tag: str

        class Request:
            params = {"tag": "primary"}

        request = Request()

        result = adapter.parse_query(cast(Any, request), ScalarQueryModel)

        assert result.tag == "primary"

    def test_parse_headers_handles_scalar_values(self, adapter: PydanticAdapter) -> None:
        """Azure Functions headers dict returns scalar values."""

        class ScalarHeaderModel(BaseModel):
            model_config = ConfigDict(populate_by_name=True)

            request_id: str = Field(alias="X-Request-Id")

        class Request:
            headers = {"X-Request-Id": "req-1"}

        request = Request()

        result = adapter.parse_headers(cast(Any, request), ScalarHeaderModel)

        assert result.request_id == "req-1"

    def test_parse_path_uses_route_params(self, adapter: PydanticAdapter) -> None:
        class PathModel(BaseModel):
            user_id: int

        request = func.HttpRequest(
            method="GET",
            url="/api/users/1",
            body=b"",
            params={},
            headers={},
            route_params={"user_id": "1"},
        )

        result = adapter.parse_path(request, PathModel)

        assert result.user_id == 1


# Test loc source-prefixing (#257)
class TestLocSourcePrefix:
    """Error ``loc`` values carry their input-source segment."""

    def test_body_error_loc_is_prefixed(
        self, adapter: PydanticAdapter, mock_request: type
    ) -> None:
        req = mock_request(b'{"name": "Al", "age": 30}')
        with pytest.raises(AdapterValidationError) as exc_info:
            adapter.parse_body(req, UserModel)

        loc = exc_info.value.errors[0]["loc"]
        assert loc[0] == "body"
        assert "name" in loc

    def test_query_error_loc_is_prefixed(self, adapter: PydanticAdapter) -> None:
        class QueryOnly(BaseModel):
            count: int

        class Request:
            params = {"count": "not-an-int"}

        with pytest.raises(AdapterValidationError) as exc_info:
            adapter.parse_query(cast(Any, Request()), QueryOnly)

        assert exc_info.value.errors[0]["loc"][0] == "query"

    def test_path_error_loc_is_prefixed(self, adapter: PydanticAdapter) -> None:
        class PathModel(BaseModel):
            user_id: int

        request = func.HttpRequest(
            method="GET",
            url="/api/users/x",
            body=b"",
            params={},
            headers={},
            route_params={"user_id": "not-a-number"},
        )
        with pytest.raises(AdapterValidationError) as exc_info:
            adapter.parse_path(request, PathModel)

        assert exc_info.value.errors[0]["loc"][0] == "path"

    def test_headers_error_loc_is_prefixed(self, adapter: PydanticAdapter) -> None:
        class HeaderOnly(BaseModel):
            model_config = ConfigDict(populate_by_name=True)

            request_id: str = Field(alias="X-Request-Id")

        class Request:
            headers: dict[str, str] = {}

        with pytest.raises(AdapterValidationError) as exc_info:
            adapter.parse_headers(cast(Any, Request()), HeaderOnly)

        assert exc_info.value.errors[0]["loc"][0] == "headers"

    def test_missing_body_loc_is_not_double_prefixed(
        self, adapter: PydanticAdapter, mock_request: type
    ) -> None:
        req = mock_request(b"")
        with pytest.raises(AdapterValidationError) as exc_info:
            adapter.parse_body(req, UserModel)

        assert exc_info.value.errors[0]["loc"] == ["body"]

    def test_legacy_loc_disables_prefixing(self, mock_request: type) -> None:
        legacy = PydanticAdapter(legacy_loc=True)
        req = mock_request(b'{"name": "Al", "age": 30}')
        with pytest.raises(AdapterValidationError) as exc_info:
            legacy.parse_body(req, UserModel)

        loc = exc_info.value.errors[0]["loc"]
        assert loc[0] != "body"
        assert loc == ["name"]


# Test serialize
class TestSerialize:
    """Tests for serialize method."""

    def test_serialize_basemodel(self, adapter: PydanticAdapter) -> None:
        """Test serializing BaseModel instance."""
        user = UserModel(name="Alice", age=30)
        content, content_type = adapter.serialize(user)

        assert content_type == "application/json"
        assert '"name":"Alice"' in content or '"name": "Alice"' in content
        assert '"age":30' in content or '"age": 30' in content

    def test_serialize_dict(self, adapter: PydanticAdapter) -> None:
        """Test serializing dict."""
        data = {"key": "value", "number": 42}
        content, content_type = adapter.serialize(data)

        assert content_type == "application/json"
        assert '"key":"value"' in content or '"key": "value"' in content
        assert '"number":42' in content or '"number": 42' in content

    def test_serialize_list(self, adapter: PydanticAdapter) -> None:
        """Test serializing list."""
        data = [1, 2, 3, "test"]
        content, content_type = adapter.serialize(data)

        assert content_type == "application/json"
        assert "[1" in content or '["test"]' in content

    def test_serialize_string(self, adapter: PydanticAdapter) -> None:
        """Test serializing string."""
        data = "Hello, World!"
        content, content_type = adapter.serialize(data)

        assert content_type == "text/plain; charset=utf-8"
        assert content == "Hello, World!"

    def test_serialize_bytes(self, adapter: PydanticAdapter) -> None:
        """Test serializing bytes."""
        data = b"binary data"
        content, content_type = adapter.serialize(data)

        assert content_type == "application/octet-stream"
        assert content == b"binary data"

    def test_serialize_invalid_type(self, adapter: PydanticAdapter) -> None:
        """Test serializing invalid type raises TypeError."""
        with pytest.raises(TypeError) as exc_info:
            adapter.serialize(object())

        assert "Cannot serialize type" in str(exc_info.value)

    def test_serialize_nested_unsupported_type_raises_type_error(
        self, adapter: PydanticAdapter
    ) -> None:
        with pytest.raises(TypeError, match="Cannot serialize type object"):
            adapter.serialize({"nested": object()})


# Test format_error
class TestFormatError:
    """Tests for format_error method."""

    def test_format_validation_error(self, adapter: PydanticAdapter, mock_request: type) -> None:
        """Test formatting ValidationError."""
        req = mock_request(b'{"name": "Al", "age": 30}')
        try:
            adapter.parse_body(req, UserModel)
        except AdapterValidationError as e:
            result = adapter.format_error(e)

            assert "detail" in result
            assert isinstance(result["detail"], list)
            assert len(result["detail"]) > 0

            error = result["detail"][0]
            assert "loc" in error
            assert "msg" in error
            assert "type" in error

    def test_format_raw_pydantic_error_backward_compat(self, adapter: PydanticAdapter) -> None:
        """format_error still handles a raw Pydantic ValidationError directly."""
        from pydantic import ValidationError as PydanticValidationError

        try:
            UserModel.model_validate({"name": "Al", "age": 30})
        except PydanticValidationError as e:
            result = adapter.format_error(e)

            assert "detail" in result
            assert isinstance(result["detail"], list)
            assert len(result["detail"]) > 0
            error = result["detail"][0]
            assert "loc" in error
            assert "msg" in error
            assert "type" in error

    def test_format_generic_exception(self, adapter: PydanticAdapter) -> None:
        """Test formatting generic exception."""
        exc = Exception("Something went wrong")
        result = adapter.format_error(exc)

        assert "detail" in result
        assert isinstance(result["detail"], list)
        assert len(result["detail"]) == 1

        error = result["detail"][0]
        assert error["loc"] == []
        assert error["msg"] == "Something went wrong"
        assert error["type"] == "value_error"


class TestValidateResponseWithTypeAdapter:
    """Tests for validate_response with pre-built TypeAdapter (Issue #97)."""

    def test_reuses_prebuilt_type_adapter(self, adapter: PydanticAdapter) -> None:
        """Test that a pre-built TypeAdapter is used instead of creating a new one."""
        from pydantic import TypeAdapter

        ta = TypeAdapter(UserModel)
        data = {"name": "Alice", "age": 30}
        result = adapter.validate_response(data, UserModel, type_adapter=ta)

        assert isinstance(result, UserModel)
        assert result.name == "Alice"
        assert result.age == 30

    def test_falls_back_when_no_type_adapter(self, adapter: PydanticAdapter) -> None:
        """Test that validate_response still works without pre-built TypeAdapter."""
        data = {"name": "Bob", "age": 25}
        result = adapter.validate_response(data, UserModel, type_adapter=None)

        assert isinstance(result, UserModel)
        assert result.name == "Bob"

    def test_prebuilt_type_adapter_with_generic(
        self, adapter: PydanticAdapter,
    ) -> None:
        """Test pre-built TypeAdapter with generic type like list[UserModel]."""
        from pydantic import TypeAdapter

        ta = TypeAdapter(list[UserModel])
        data = [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]
        result = adapter.validate_response(
            data, list[UserModel], type_adapter=ta,
        )

        assert len(result) == 2
        assert all(isinstance(item, UserModel) for item in result)


class TestSerializeBroaderTypes:
    """Tests for broader return type support in serialize (Issue #98)."""

    def test_serialize_int(self, adapter: PydanticAdapter) -> None:
        content, content_type = adapter.serialize(42)
        assert content_type == "application/json"
        assert content == "42"

    def test_serialize_float(self, adapter: PydanticAdapter) -> None:
        content, content_type = adapter.serialize(3.14)
        assert content_type == "application/json"
        assert content == "3.14"

    def test_serialize_bool(self, adapter: PydanticAdapter) -> None:
        content, content_type = adapter.serialize(True)
        assert content_type == "application/json"
        assert content == "true"

    def test_serialize_dataclass(self, adapter: PydanticAdapter) -> None:
        import dataclasses

        @dataclasses.dataclass
        class Point:
            x: int
            y: int

        content, content_type = adapter.serialize(Point(x=1, y=2))
        assert content_type == "application/json"
        import json
        assert json.loads(content) == {"x": 1, "y": 2}

    def test_serialize_nested_dataclass_in_dict(
        self, adapter: PydanticAdapter,
    ) -> None:
        import dataclasses

        @dataclasses.dataclass
        class Point:
            x: int
            y: int

        content, content_type = adapter.serialize({"point": Point(x=1, y=2)})
        assert content_type == "application/json"
        import json
        assert json.loads(content) == {"point": {"x": 1, "y": 2}}

    def test_serialize_unsupported_type_raises(
        self, adapter: PydanticAdapter,
    ) -> None:
        from azure_functions_validation.errors import SerializationError

        with pytest.raises(SerializationError, match="Cannot serialize type object"):
            adapter.serialize(object())
