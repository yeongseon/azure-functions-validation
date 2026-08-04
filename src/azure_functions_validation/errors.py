"""Error types and formatting for azure-functions-validation."""

from __future__ import annotations

import json
import logging
from typing import Any, Callable, Protocol

from azure.functions import HttpResponse

logger = logging.getLogger(__name__)

ErrorFormatter = Callable[[Exception, int], dict[str, Any]]

_SANITIZED_500_BODY = json.dumps(
    {
        "detail": [
            {
                "loc": [],
                "msg": "Internal Server Error",
                "type": "server_error",
            }
        ]
    }
)


class ErrorAdapter(Protocol):
    def format_error(self, exc: Exception) -> dict[str, Any]: ...


class ResponseValidationError(Exception):
    """Raised when response validation fails."""

    def __init__(self, message: str = "Response validation error"):
        """Initialize ResponseValidationError.

        Args:
            message: Error message
        """
        super().__init__(message)
        self.message = message


class SerializationError(TypeError):
    """Raised when an unsupported type is encountered during serialization."""

    def __init__(self, type_name: str) -> None:
        """Initialize SerializationError.

        Args:
            type_name: Name of the unsupported type.
        """
        super().__init__(f"Cannot serialize type {type_name}")
        self.type_name = type_name
        self.type_name = type_name


class HttpError(Exception):
    """Raised by a handler to return a controlled HTTP error response.

    Rendered through the standard error envelope (``{"detail": [...]}``) by the
    validation pipeline, so controlled errors (e.g. 404, 409) share the same
    shape as automatic validation errors.

    Args:
        status_code: HTTP status code for the response (e.g. ``404``).
        detail: Either a human-readable message (wrapped into a single
            ``{"loc": [], "msg": ..., "type": ...}`` entry) or a pre-built list
            of detail mappings matching the error-envelope schema.
        error_type: ``type`` value used when *detail* is a plain message.
    """

    def __init__(
        self,
        status_code: int,
        detail: Any = "Error",
        *,
        error_type: str = "http_error",
    ) -> None:
        super().__init__(str(detail))
        self.status_code = status_code
        self.detail = detail
        self.error_type = error_type

    def to_detail(self) -> list[dict[str, Any]]:
        """Return the error-envelope ``detail`` list for this error."""
        if isinstance(self.detail, list):
            return self.detail
        return [{"loc": [], "msg": str(self.detail), "type": self.error_type}]

class AdapterValidationError(Exception):
    """Raised by validation adapters when request/response validation fails.

    Decouples the pipeline and downstream callers from the underlying
    validation library (e.g. Pydantic).  The normalized ``errors`` list mirrors
    the public error-response ``detail`` schema: each entry is a mapping with
    ``loc`` (list), ``msg`` (str), and ``type`` (str) keys.
    """

    def __init__(self, message: str, errors: list[dict[str, Any]]) -> None:
        """Initialize AdapterValidationError.

        Args:
            message: Human-readable error message.
            errors: Normalized list of error detail mappings.
        """
        super().__init__(message)
        self.errors: list[dict[str, Any]] = errors


def format_error_response(
    exception: Exception,
    status_code: int,
    adapter: ErrorAdapter,
    error_formatter: ErrorFormatter | None = None,
) -> HttpResponse:
    """Build an ``HttpResponse`` for a validation or parsing error.

    Args:
        exception: The caught exception.
        status_code: HTTP status code for the response.
        adapter: The validation adapter used for default formatting.
        error_formatter: Optional per-handler custom formatter.

    Returns:
        An ``HttpResponse`` with a JSON error body.
    """
    response_status_code = status_code

    if error_formatter is not None:
        try:
            error_response = error_formatter(exception, status_code)
        except Exception:
            logger.exception("error_formatter raised an unexpected exception")
            response_status_code = 500

            error_response = json.loads(_SANITIZED_500_BODY)
    elif isinstance(exception, HttpError) and status_code < 500:
        # Controlled handler error — render its detail through the envelope.
        error_response = {"detail": exception.to_detail()}
    elif status_code >= 500:
        # Sanitize server errors — never leak internal details to the client
        error_response = json.loads(_SANITIZED_500_BODY)
    else:
        error_response = adapter.format_error(exception)

    try:
        body = json.dumps(error_response)
    except (TypeError, ValueError):
        logger.exception(
            "error_response could not be serialized to JSON"
        )
        body = _SANITIZED_500_BODY
        response_status_code = 500

    return HttpResponse(
        body=body,
        status_code=response_status_code,
        headers={"Content-Type": "application/json"},
    )
