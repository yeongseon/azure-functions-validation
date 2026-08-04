"""Validation adapter layer for request/response validation."""

import dataclasses
import json
from typing import Any, Callable, Protocol

from azure.functions import HttpRequest
from pydantic import BaseModel, TypeAdapter
from pydantic import ValidationError as PydanticValidationError

from .errors import AdapterValidationError, SerializationError


def _prefix_loc(source: str | None, loc: list[Any], *, legacy_loc: bool) -> list[Any]:
    """Prepend the input *source* segment to a Pydantic ``loc`` tuple.

    Produces source-disambiguated locations such as ``["body", "email"]`` so
    that body/query/path/header collisions are distinguishable.  When
    *legacy_loc* is ``True`` (or *source* is ``None``) the raw ``loc`` is
    returned unchanged for one-cycle backward compatibility.
    """
    if legacy_loc or source is None:
        return loc
    return [source, *loc]


def _json_default(value: Any) -> Any:
    """Fallback JSON encoder for nested models/dataclasses inside dict/list."""
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return dataclasses.asdict(value)
    raise SerializationError(type(value).__name__)


def _is_dataclass_instance(obj: Any) -> bool:
    return dataclasses.is_dataclass(obj) and not isinstance(obj, type)


# Ordered serialization dispatch table: (type predicate, serializer).
# The first matching predicate wins, mirroring the previous isinstance ladder.
_SERIALIZERS: tuple[
    tuple[Callable[[Any], bool], Callable[[Any], tuple[str | bytes, str]]], ...
] = (
    (lambda o: isinstance(o, BaseModel), lambda o: (o.model_dump_json(), "application/json")),
    (
        lambda o: isinstance(o, (dict, list)),
        lambda o: (json.dumps(o, default=_json_default), "application/json"),
    ),
    (lambda o: isinstance(o, str), lambda o: (o, "text/plain; charset=utf-8")),
    (lambda o: isinstance(o, bytes), lambda o: (o, "application/octet-stream")),
    (lambda o: isinstance(o, (int, float, bool)), lambda o: (json.dumps(o), "application/json")),
    (_is_dataclass_instance, lambda o: (json.dumps(dataclasses.asdict(o)), "application/json")),
)

class ValidationAdapter(Protocol):
    """Protocol defining the interface for validation adapters."""

    def parse_body(self, req: HttpRequest, model: type[BaseModel]) -> Any:
        """Parse and validate request body.

        Args:
            req: Azure Functions HttpRequest
            model: Pydantic model class to validate against

        Returns:
            Validated model instance

        Raises:
            AdapterValidationError: If body is missing or validation fails
            ValueError: If JSON parsing fails
        """
        ...

    def parse_query(self, req: HttpRequest, model: type[BaseModel]) -> Any:
        """Parse and validate query parameters.

        Args:
            req: Azure Functions HttpRequest
            model: Pydantic model class to validate against

        Returns:
            Validated model instance

        Raises:
            AdapterValidationError: If validation fails
        """
        ...

    def parse_path(self, req: HttpRequest, model: type[BaseModel]) -> Any:
        """Parse and validate path parameters.

        Args:
            req: Azure Functions HttpRequest
            model: Pydantic model class to validate against

        Returns:
            Validated model instance

        Raises:
            AdapterValidationError: If validation fails
        """
        ...

    def parse_headers(self, req: HttpRequest, model: type[BaseModel]) -> Any:
        """Parse and validate headers.

        Args:
            req: Azure Functions HttpRequest
            model: Pydantic model class to validate against

        Returns:
            Validated model instance

        Raises:
            AdapterValidationError: If validation fails
        """
        ...

    def validate_response(
        self, obj: Any, model: Any,
        *, type_adapter: TypeAdapter[Any] | None = None,
    ) -> Any:
        """Validate response object against model.

        Args:
            obj: Response object (BaseModel instance, dict, list, etc.)
            model: Pydantic model class or generic type (e.g. list[SomeModel]) to validate against
            type_adapter: Optional pre-built TypeAdapter for reuse.

        Returns:
            Validated model instance

        Raises:
            AdapterValidationError: If validation fails
        """
        ...

    def serialize(self, obj: Any) -> tuple[str | bytes, str]:
        """Serialize response object to content and content-type.

        Args:
            obj: Object to serialize

        Returns:
            Tuple of (content, content_type)

        Raises:
            SerializationError: If object type is not supported
        """
        ...

    def format_error(self, exc: Exception) -> dict[str, Any]:
        """Format exception into standardized error response.

        Args:
            exc: Exception to format

        Returns:
            Error response dict with 'detail' key
        """
        ...


class PydanticAdapter:
    """Concrete validation adapter implementation using Pydantic v2."""

    def __init__(self, *, legacy_loc: bool = False) -> None:
        """Initialize the adapter.

        Args:
            legacy_loc: When ``True``, error ``loc`` values are emitted without
                the leading input-source segment (``["email"]`` instead of
                ``["body", "email"]``).  This is a one-cycle migration escape
                hatch and will be removed in a future release.
        """
        self._legacy_loc = legacy_loc

    @staticmethod
    def _to_adapter_error(
        exc: PydanticValidationError,
        *,
        source: str | None = None,
        legacy_loc: bool = False,
    ) -> AdapterValidationError:
        """Convert a Pydantic ``ValidationError`` into an ``AdapterValidationError``.

        The library-specific exception is preserved as ``__cause__`` while the
        normalized ``errors`` list keeps the pipeline and downstream callers
        decoupled from Pydantic.  When *source* is provided, each ``loc`` is
        prefixed with it (unless *legacy_loc* is set).
        """
        detail = [
            {
                "loc": _prefix_loc(source, list(error["loc"]), legacy_loc=legacy_loc),
                "msg": error["msg"],
                "type": error["type"],
            }
            for error in exc.errors()
        ]
        return AdapterValidationError(str(exc), detail)

    def _source_error(
        self, exc: PydanticValidationError, source: str
    ) -> AdapterValidationError:
        """Convert *exc*, prefixing ``loc`` with *source* per ``legacy_loc``."""
        return self._to_adapter_error(
            exc, source=source, legacy_loc=self._legacy_loc
        )

    @staticmethod
    def _missing_body_validation_error() -> AdapterValidationError:
        class _MissingBodyPayload(BaseModel):
            body: Any

        try:
            _MissingBodyPayload.model_validate({})
        except PydanticValidationError as exc:
            return PydanticAdapter._to_adapter_error(exc)

        raise RuntimeError("Unreachable: expected missing body validation error")

    def parse_body(self, req: HttpRequest, model: type[BaseModel]) -> Any:
        """Parse and validate request body from JSON.

        Args:
            req: Azure Functions HttpRequest
            model: Pydantic model class to validate against

        Returns:
            Validated model instance

        Raises:
            AdapterValidationError: If body is missing (with type="missing")
            ValueError: If JSON is invalid (with "Invalid JSON" message)
        """
        body = req.get_body()

        # Handle empty body
        if not body:
            raise self._missing_body_validation_error()

        # Parse JSON
        try:
            body_str = body.decode("utf-8")
        except UnicodeDecodeError as e:
            raise ValueError("Invalid JSON") from e

        if not body_str.strip():
            # Empty JSON string - this is a missing body, not invalid JSON
            raise self._missing_body_validation_error()

        try:
            data = json.loads(body_str)
        except json.JSONDecodeError as e:
            raise ValueError("Invalid JSON") from e

        # Validate with Pydantic
        try:
            return model.model_validate(data)
        except PydanticValidationError as exc:
            raise self._source_error(exc, "body") from exc

    def parse_query(self, req: HttpRequest, model: type[BaseModel]) -> Any:
        """Parse and validate query parameters.

        Args:
            req: Azure Functions HttpRequest
            model: Pydantic model class to validate against

        Returns:
            Validated model instance

        Raises:
            AdapterValidationError: If validation fails
        """
        # Parse query parameters
        query_params = req.params or {}

        # Convert MultiDict to regular dict
        query_data = {}
        for key, value in query_params.items():
            query_data[key] = value

        # Validate with Pydantic
        try:
            return model.model_validate(query_data)
        except PydanticValidationError as exc:
            raise self._source_error(exc, "query") from exc

    def parse_path(self, req: HttpRequest, model: type[BaseModel]) -> Any:
        """Parse and validate path parameters.

        Args:
            req: Azure Functions HttpRequest
            model: Pydantic model class to validate against

        Returns:
            Validated model instance

        Raises:
            AdapterValidationError: If validation fails
        """
        # Parse route parameters
        route_params = req.route_params or {}

        # Validate with Pydantic
        try:
            return model.model_validate(route_params)
        except PydanticValidationError as exc:
            raise self._source_error(exc, "path") from exc

    def parse_headers(self, req: HttpRequest, model: type[BaseModel]) -> Any:
        """Parse and validate headers.

        Args:
            req: Azure Functions HttpRequest
            model: Pydantic model class to validate against

        Returns:
            Validated model instance

        Raises:
            AdapterValidationError: If validation fails
        """
        # Parse headers
        headers = req.headers or {}

        # Convert to regular dict and handle multi-value headers
        header_data = {}
        for key, value in headers.items():
            header_data[key] = value

        # Validate with Pydantic
        try:
            return model.model_validate(header_data)
        except PydanticValidationError as exc:
            raise self._source_error(exc, "headers") from exc

    def validate_response(
        self, obj: Any, model: Any,
        *, type_adapter: TypeAdapter[Any] | None = None,
    ) -> Any:
        """Validate response object against model.

        Uses ``TypeAdapter`` to support both concrete ``BaseModel`` subclasses
        and parameterized generic types such as ``list[SomeModel]``.

        When *type_adapter* is provided (pre-built at decoration time), it is
        reused to avoid per-request allocation.

        Args:
            obj: Response object (BaseModel instance, dict, list, etc.)
            model: Pydantic model class or generic type (e.g. list[SomeModel]) to validate against
            type_adapter: Optional pre-built TypeAdapter for reuse.

        Returns:
            Validated model instance

        Raises:
            AdapterValidationError: If validation fails
        """
        ta = type_adapter if type_adapter is not None else TypeAdapter(model)
        try:
            return ta.validate_python(obj)
        except PydanticValidationError as exc:
            raise self._source_error(exc, "response") from exc

    def serialize(self, obj: Any) -> tuple[str | bytes, str]:
        """Serialize response object to content and content-type.

        Args:
            obj: Object to serialize.
                Supported: BaseModel, dict, list, str,
                bytes, int, float, bool, dataclass.

        Returns:
            Tuple of (content, content_type)

        Raises:
            SerializationError: If object type is not supported
        """
        for predicate, serializer in _SERIALIZERS:
            if predicate(obj):
                return serializer(obj)
        raise SerializationError(type(obj).__name__)

    def format_error(self, exc: Exception) -> dict[str, Any]:
        """Format exception into standardized error response.

        Args:
            exc: Exception to format (typically AdapterValidationError)

        Returns:
            Error response dict with 'detail' key containing list of errors
        """
        if isinstance(exc, AdapterValidationError):
            return {"detail": exc.errors}
        if isinstance(exc, PydanticValidationError):
            detail = []
            for error in exc.errors():
                detail.append(
                    {
                        "loc": list(error["loc"]),
                        "msg": error["msg"],
                        "type": error["type"],
                    }
                )
            return {"detail": detail}
        else:
            # Generic exception
            return {
                "detail": [
                    {
                        "loc": [],
                        "msg": str(exc),
                        "type": "value_error",
                    }
                ]
            }
