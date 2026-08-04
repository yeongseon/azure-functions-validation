"""Validation pipeline engine.

This module contains the request-parsing and response-building logic that was
previously inlined inside the ``validate_http`` decorator closure.  Extracting
it into standalone functions makes the pipeline independently testable and
keeps ``decorator.py`` focused on configuration and wiring.
"""

from __future__ import annotations

import logging


from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

from azure.functions import HttpResponse

from .adapter import PydanticAdapter, ValidationAdapter
from .errors import (
    AdapterValidationError,
    ErrorFormatter,
    HttpError,
    ResponseValidationError,
    SerializationError,
    format_error_response,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PipelineConfig:
    """Internal configuration for the validation pipeline.

    Created once by the ``validate_http`` decorator and reused on every
    invocation.  All fields are immutable after construction.
    """

    body: Any = None
    query: Any = None
    path: Any = None
    headers: Any = None
    request_model: Any = None
    response_model: Any = None
    adapter: ValidationAdapter = field(default_factory=PydanticAdapter)
    error_formatter: ErrorFormatter | None = None
    func_params: Mapping[str, Any] = field(default_factory=dict)
    request_param_name: str | None = None
    response_type_adapter: Any = None
    success_status_code: int = 200


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------


def _prepare_invocation(
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    config: PipelineConfig,
) -> tuple[HttpResponse | None, dict[str, Any]]:
    """Resolve the request and parse inputs shared by both pipelines.

    Returns a ``(early_response, merged_kwargs)`` pair.  When *early_response*
    is not ``None`` the caller must return it immediately without invoking the
    handler (request resolution or input validation failed).
    """
    try:
        http_request = _resolve_http_request(args, kwargs, config)
    except ValueError as e:
        return format_error_response(e, 400, config.adapter, config.error_formatter), {}
    parsed = _parse_inputs(http_request, config)
    if isinstance(parsed, HttpResponse):
        return parsed, {}
    merged = _merge_kwargs(args, kwargs, parsed)
    return None, merged


def run_pipeline(
    func: Callable[..., Any],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    config: PipelineConfig,
) -> HttpResponse:
    """Execute the sync validation pipeline."""
    early, merged = _prepare_invocation(args, kwargs, config)
    if early is not None:
        return early
    try:
        result = func(*args, **merged) if args else func(**merged)
    except HttpError as e:
        return format_error_response(
            e, e.status_code, config.adapter, config.error_formatter
        )
    return _build_response(result, config)


async def run_pipeline_async(
    func: Callable[..., Any],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    config: PipelineConfig,
) -> HttpResponse:
    """Execute the async validation pipeline."""
    early, merged = _prepare_invocation(args, kwargs, config)
    if early is not None:
        return early
    try:
        result = await (func(*args, **merged) if args else func(**merged))
    except HttpError as e:
        return format_error_response(
            e, e.status_code, config.adapter, config.error_formatter
        )
    return _build_response(result, config)


# ---------------------------------------------------------------------------
# Private helpers (moved from decorator.py)
# ---------------------------------------------------------------------------


def _is_http_request_like(candidate: Any) -> bool:
    """Return ``True`` if *candidate* looks like an ``HttpRequest``."""
    return (
        hasattr(candidate, "method")
        and hasattr(candidate, "url")
        and hasattr(candidate, "get_body")
        and hasattr(candidate, "headers")
    )


def _resolve_http_request(
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    config: PipelineConfig,
) -> Any:
    """Find the ``HttpRequest`` from positional or keyword arguments."""
    # Extract HttpRequest from positional args first
    for arg in args:
        if _is_http_request_like(arg):
            return arg

    # Prefer the declared request parameter name when invoked with kwargs
    if config.request_param_name is not None and _is_http_request_like(
        kwargs.get(config.request_param_name)
    ):
        return kwargs[config.request_param_name]

    # Support the explicit http_request alias too
    if config.request_param_name != "http_request" and _is_http_request_like(
        kwargs.get("http_request")
    ):
        return kwargs["http_request"]

    # Fall back to any HttpRequest-like keyword value
    for value in kwargs.values():
        if _is_http_request_like(value):
            return value

    raise ValueError("Function must receive an HttpRequest-like object as argument")


def _inject_named(
    name: str, parsed: Any, config: PipelineConfig, parsed_inputs: dict[str, Any]
) -> None:
    """Inject a parsed value under its own name when the handler declares it."""
    if name in config.func_params:
        parsed_inputs[name] = parsed


def _inject_body(
    name: str, parsed: Any, config: PipelineConfig, parsed_inputs: dict[str, Any]
) -> None:
    """Inject the parsed body under ``body`` or the ``req_model`` alias."""
    if "body" in config.func_params:
        parsed_inputs["body"] = parsed
    elif "req_model" in config.func_params and config.request_model is not None:
        parsed_inputs["req_model"] = parsed


def _parse_inputs(
    http_request: Any,
    config: PipelineConfig,
) -> dict[str, Any] | HttpResponse:
    """Parse and validate all configured request inputs."""
    parsed_inputs: dict[str, Any] = {}

    # (name, configured model, adapter parse method, injection strategy)
    parse_specs: tuple[
        tuple[
            str,
            Any,
            Callable[[Any, Any], Any],
            Callable[[str, Any, PipelineConfig, dict[str, Any]], None],
        ],
        ...,
    ] = (
        ("body", config.body, config.adapter.parse_body, _inject_body),
        ("query", config.query, config.adapter.parse_query, _inject_named),
        ("path", config.path, config.adapter.parse_path, _inject_named),
        ("headers", config.headers, config.adapter.parse_headers, _inject_named),
    )

    for name, model, parse, inject in parse_specs:
        if model is None:
            continue
        # Always validate the configured input, even if the handler ignores it.
        try:
            parsed = parse(http_request, model)
        except AdapterValidationError as e:
            return format_error_response(e, 422, config.adapter, config.error_formatter)
        except ValueError as e:
            return format_error_response(e, 400, config.adapter, config.error_formatter)
        except Exception as e:
            return format_error_response(e, 500, config.adapter, config.error_formatter)
        inject(name, parsed, config, parsed_inputs)

    # Add original HttpRequest if requested
    if "http_request" in config.func_params and config.request_param_name != "http_request":
        parsed_inputs["http_request"] = http_request

    return parsed_inputs


def _merge_kwargs(
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    parsed_inputs: dict[str, Any],
) -> dict[str, Any]:
    """Merge original kwargs with parsed/validated inputs.

    Removes keys from *kwargs* that would collide with *parsed_inputs* to
    avoid passing duplicate values to the wrapped function.
    """
    filtered_kwargs = {k: v for k, v in kwargs.items() if k not in parsed_inputs}
    return {**filtered_kwargs, **parsed_inputs}


def _build_response(result: Any, config: PipelineConfig) -> HttpResponse:
    """Validate and serialize the handler return value into an ``HttpResponse``."""
    # Handle HttpResponse bypass
    if isinstance(result, HttpResponse):
        return result

    # Handle None return → 204 No Content
    if result is None:
        return HttpResponse(status_code=204)

    # Validate and serialize response
    if config.response_model is not None:
        try:
            validated_result = config.adapter.validate_response(
                result, config.response_model, type_adapter=config.response_type_adapter
            )
        except AdapterValidationError:
            logger.error(
                "Response validation failed for handler %r",
                getattr(config, "request_param_name", None),
                exc_info=True,
            )
            response_error = ResponseValidationError("Response validation failed")
            return format_error_response(
                response_error, 500, config.adapter, config.error_formatter,
            )
        except Exception:
            logger.error(
                "Unexpected error during response validation",
                exc_info=True,
            )
            response_error = ResponseValidationError("Response validation failed")
            return format_error_response(
                response_error, 500, config.adapter, config.error_formatter,
            )

        try:
            content, content_type = config.adapter.serialize(validated_result)
        except (SerializationError, TypeError) as e:
            logger.error("Failed to serialize validated response", exc_info=True)
            return format_error_response(
                e, 500, config.adapter, config.error_formatter,
            )

        return HttpResponse(
            body=content,
            status_code=config.success_status_code,
            headers={"Content-Type": content_type},
        )

    # No response model, serialize directly
    try:
        content, content_type = config.adapter.serialize(result)
    except (SerializationError, TypeError) as e:
        logger.error("Failed to serialize response", exc_info=True)
        return format_error_response(
            e, 500, config.adapter, config.error_formatter,
        )

    return HttpResponse(
        body=content,
        status_code=config.success_status_code,
        headers={"Content-Type": content_type},
    )
