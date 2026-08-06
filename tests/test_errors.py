"""Tests for the errors module."""

import json
from unittest.mock import Mock

from azure.functions import HttpResponse
import pytest

from azure_functions_validation.errors import (
    ERROR_FORMAT_VERSION,
    ErrorFormatter,
    ResponseValidationError,
    SerializationError,
    format_error_response,
)

# ---------------------------------------------------------------------------
# ResponseValidationError
# ---------------------------------------------------------------------------


class TestResponseValidationError:
    """Tests for the ResponseValidationError exception class."""

    def test_defaults(self) -> None:
        error = ResponseValidationError()
        assert str(error) == "Response validation error"
        assert error.message == "Response validation error"

    def test_custom_message(self) -> None:
        error = ResponseValidationError("Custom response error")
        assert str(error) == "Custom response error"
        assert error.message == "Custom response error"

    def test_is_exception_subclass(self) -> None:
        assert issubclass(ResponseValidationError, Exception)

    def test_raisable(self) -> None:
        import pytest

        with pytest.raises(ResponseValidationError, match="boom"):
            raise ResponseValidationError("boom")


# ---------------------------------------------------------------------------
# ErrorFormatter type alias
# ---------------------------------------------------------------------------


class TestErrorFormatterType:
    """ErrorFormatter is a callable type alias and must be importable."""

    def test_importable(self) -> None:
        assert ErrorFormatter is not None

    def test_usable_as_annotation(self) -> None:
        def fmt(exc: Exception, code: int) -> dict[str, str]:
            return {"err": str(exc)}

        result = fmt(ValueError("test"), 422)
        assert result["err"] == "test"


# ---------------------------------------------------------------------------
# format_error_response
# ---------------------------------------------------------------------------


class TestFormatErrorResponse:
    """Tests for the format_error_response helper."""

    def test_uses_adapter_when_no_formatter(self) -> None:
        adapter = Mock()
        adapter.format_error.return_value = {"detail": [{"msg": "oops"}]}

        exc = ValueError("oops")
        resp = format_error_response(exc, 422, adapter)

        assert isinstance(resp, HttpResponse)
        assert resp.status_code == 422
        data = json.loads(resp.get_body().decode())
        assert data == {"detail": [{"msg": "oops"}], "error_format_version": 1}
        adapter.format_error.assert_called_once_with(exc)

    def test_uses_custom_formatter(self) -> None:
        adapter = Mock()

        def fmt(exc: Exception, status: int) -> dict[str, object]:
            return {"custom": True, "status": status}

        exc = ValueError("err")
        resp = format_error_response(exc, 400, adapter, error_formatter=fmt)

        assert resp.status_code == 400
        data = json.loads(resp.get_body().decode())
        assert data["custom"] is True
        assert data["status"] == 400
        # adapter.format_error should NOT be called
        adapter.format_error.assert_not_called()

    def test_content_type_is_json(self) -> None:
        adapter = Mock()
        adapter.format_error.return_value = {"detail": []}

        resp = format_error_response(RuntimeError("x"), 500, adapter)
        assert resp.headers["Content-Type"] == "application/json"

    def test_500_response_is_sanitized(self) -> None:
        """Test that 500 responses use generic message, not adapter.format_error."""
        adapter = Mock()

        resp = format_error_response(RuntimeError("secret db error"), 500, adapter)

        assert resp.status_code == 500
        data = json.loads(resp.get_body().decode())
        assert data == {
            "detail": [{"loc": [], "msg": "Internal Server Error", "type": "server_error"}],
            "error_format_version": 1,
        }
        adapter.format_error.assert_not_called()

    def test_500_sanitization_bypassed_by_custom_formatter(self) -> None:
        """Test that custom error_formatter takes precedence over sanitization."""
        adapter = Mock()

        def fmt(exc: Exception, status: int) -> dict[str, object]:
            return {"custom": True, "status": status}

        resp = format_error_response(RuntimeError("x"), 500, adapter, error_formatter=fmt)

        assert resp.status_code == 500
        data = json.loads(resp.get_body().decode())
        assert data["custom"] is True
        assert data["status"] == 500
        adapter.format_error.assert_not_called()

    def test_formatter_exception_returns_sanitized_500(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        adapter = Mock()

        def fmt(exc: Exception, status: int) -> dict[str, object]:
            raise RuntimeError("formatter failed")

        resp = format_error_response(ValueError("bad input"), 422, adapter, error_formatter=fmt)

        assert resp.status_code == 500
        data = json.loads(resp.get_body().decode())
        assert data == {
            "detail": [{"loc": [], "msg": "Internal Server Error", "type": "server_error"}],
            "error_format_version": 1,
        }
        adapter.format_error.assert_not_called()
        # Verify that the exception was logged
        assert "error_formatter raised an unexpected exception" in caplog.text
        assert caplog.records[0].levelname == "ERROR"

    def test_default_envelope_carries_format_version(self) -> None:
        """Every default envelope is stamped with the stability marker."""
        adapter = Mock()
        adapter.format_error.return_value = {"detail": [{"msg": "oops"}]}

        resp = format_error_response(ValueError("oops"), 422, adapter)

        data = json.loads(resp.get_body().decode())
        assert data["error_format_version"] == ERROR_FORMAT_VERSION

    def test_adapter_supplied_version_is_not_overwritten(self) -> None:
        """An adapter that already sets the marker keeps its own value."""
        adapter = Mock()
        adapter.format_error.return_value = {"detail": [], "error_format_version": 99}

        resp = format_error_response(ValueError("x"), 422, adapter)

        data = json.loads(resp.get_body().decode())
        assert data["error_format_version"] == 99

    def test_custom_formatter_output_is_not_stamped(self) -> None:
        """A successful custom formatter owns its shape — no marker injected."""
        adapter = Mock()

        def fmt(exc: Exception, status: int) -> dict[str, object]:
            return {"custom": True}

        resp = format_error_response(ValueError("x"), 400, adapter, error_formatter=fmt)

        data = json.loads(resp.get_body().decode())
        assert "error_format_version" not in data

    def test_non_serializable_error_response_returns_sanitized_500(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test that non-JSON-serializable error_response is caught and sanitized."""
        import datetime

        adapter = Mock()

        def fmt(exc: Exception, status: int) -> dict[str, object]:
            return {
                "custom": True,
                "timestamp": datetime.datetime.now(),  # Non-serializable
            }

        resp = format_error_response(ValueError("bad input"), 422, adapter, error_formatter=fmt)

        # Should return 500 with sanitized body
        assert resp.status_code == 500
        data = json.loads(resp.get_body().decode())
        # N2 regression: the JSON-dump-failure fallback must also carry the
        # stability marker so pinning consumers never hit an unversioned envelope.
        assert data == {
            "detail": [{"loc": [], "msg": "Internal Server Error", "type": "server_error"}],
            "error_format_version": 1,
        }
        adapter.format_error.assert_not_called()
        # Verify that the serialization error was logged
        assert "error_response could not be serialized to JSON" in caplog.text
        assert caplog.records[0].levelname == "ERROR"


# ---------------------------------------------------------------------------
# SerializationError
# ---------------------------------------------------------------------------


class TestSerializationError:
    """Tests for the SerializationError exception class."""

    def test_is_type_error_subclass(self) -> None:
        assert issubclass(SerializationError, TypeError)

    def test_message_contains_type_name(self) -> None:
        error = SerializationError("MyClass")
        assert str(error) == "Cannot serialize type MyClass"
        assert error.type_name == "MyClass"

    def test_raisable(self) -> None:
        import pytest

        with pytest.raises(SerializationError, match="Cannot serialize type Foo"):
            raise SerializationError("Foo")
