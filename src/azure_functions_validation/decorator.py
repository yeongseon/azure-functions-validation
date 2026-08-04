"""Core decorator for HTTP request/response validation."""

from __future__ import annotations

import inspect
from typing import Any, Callable, Mapping
import warnings

from pydantic import TypeAdapter

from ._metadata import ValidationMetadata, set_validation_metadata
from ._metadata_helpers import SAFE_IDENTITY_ATTRS, copy_identity_attrs
from .adapter import PydanticAdapter, ValidationAdapter
from .errors import ErrorFormatter
from .pipeline import PipelineConfig, run_pipeline, run_pipeline_async


def validate_http(
    *,
    body: Any = None,
    query: Any = None,
    path: Any = None,
    headers: Any = None,
    request_model: Any = None,
    response_model: Any = None,
    adapter: ValidationAdapter | None = None,
    error_formatter: ErrorFormatter | None = None,
) -> Callable[..., Any]:
    """Decorator for validating HTTP request inputs and response outputs.

    Args:
        body: Pydantic model for request body validation.
        query: Pydantic model for query parameter validation.
        path: Pydantic model for path parameter validation.
        headers: Pydantic model for header validation.
        request_model: Deprecated shorthand alias for *body*. Use ``body`` instead;
            passing ``request_model`` emits a ``DeprecationWarning``.
        response_model: Pydantic model for response validation.
        adapter: Custom validation adapter (defaults to ``PydanticAdapter``).
        error_formatter: Per-handler custom error formatter.

    Returns:
        A decorator that wraps the handler with validation logic.
    """
    # Handle request_model shorthand
    if request_model is not None:
        warnings.warn(
            "The 'request_model' parameter of validate_http() is deprecated in favor "
            "of 'body' and will be removed in a future release. See "
            "https://github.com/yeongseon/azure-functions-validation-python/issues/223.",
            DeprecationWarning,
            stacklevel=2,
        )
        if any([body, query, path, headers]):
            raise ValueError("Cannot use request_model together with body/query/path/headers")
        body = request_model

    # Use default adapter if none provided
    if adapter is None:
        adapter = PydanticAdapter()

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        if _is_function_builder(func):
            warnings.warn(
                "@validate_http received an Azure Functions FunctionBuilder instead of "
                "your handler, which means it was applied ABOVE @app.route. Validation "
                "is NOT active for this function. Place @validate_http BELOW @app.route "
                "so it wraps the handler directly.",
                RuntimeWarning,
                stacklevel=2,
            )
            return func

        is_async = inspect.iscoroutinefunction(func)

        func_sig = inspect.signature(func)
        func_params = func_sig.parameters

        request_param_name = _find_request_param(func, func_params)
        _validate_no_conflicts(func, request_param_name, body, query, path, headers, request_model)

        # Pre-build TypeAdapter for response_model at decoration time (#97)
        response_type_adapter = TypeAdapter(response_model) if response_model is not None else None

        config = PipelineConfig(
            body=body,
            query=query,
            path=path,
            headers=headers,
            request_model=request_model,
            response_model=response_model,
            adapter=adapter,
            error_formatter=error_formatter,
            func_params=func_params,
            request_param_name=request_param_name,
            response_type_adapter=response_type_adapter,
        )

        wrapper = _make_wrapper(func, config, is_async=is_async)
        return wrapper

    return decorator


# ---------------------------------------------------------------------------
# Decorator-time helpers (configuration validation, not request processing)
# ---------------------------------------------------------------------------

def _is_function_builder(func: Any) -> bool:
    """Return ``True`` if *func* is an Azure Functions ``FunctionBuilder``.

    A ``FunctionBuilder`` reaches this decorator only when ``@validate_http`` was
    applied *above* ``@app.route`` (wrong order), in which case the real handler
    is never wrapped and validation is silently disabled.  We detect it via the
    ``configure_function_builder`` method that the ``@app.route`` machinery adds
    to the builder, falling back to a type-name match for SDK builds that lack it.
    """
    if hasattr(func, "configure_function_builder"):
        return True
    return type(func).__name__ == "FunctionBuilder"


def _find_request_param(
    func: Callable[..., Any],
    func_params: Mapping[str, inspect.Parameter],
) -> str:
    """Find the first positional parameter name (the HttpRequest slot).

    Raises:
        ValueError: If no positional parameter exists.
    """
    request_param_name = next(
        (
            param_name
            for param_name, param in func_params.items()
            if param.kind
            in (
                inspect.Parameter.POSITIONAL_ONLY,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
            )
        ),
        None,
    )

    if request_param_name is None:
        func_name = getattr(func, "__name__", repr(func))
        raise ValueError(
            f"Function {func_name} must accept an HttpRequest parameter "
            f"as its first positional argument"
        )

    return request_param_name


def _validate_no_conflicts(
    func: Callable[..., Any],
    request_param_name: str,
    body: Any,
    query: Any,
    path: Any,
    headers: Any,
    request_model: Any,
) -> None:
    """Raise ``ValueError`` if the first positional parameter name collides
    with an injected parameter name.
    """
    _injected: dict[str, Any] = {
        "body": body,
        "query": query,
        "path": path,
        "headers": headers,
        "req_model": request_model,
    }
    if request_param_name in _injected and _injected[request_param_name] is not None:
        func_name = getattr(func, "__name__", repr(func))
        raise ValueError(
            f"Function {func_name}: first positional parameter '{request_param_name}' "
            f"conflicts with a @validate_http injected parameter of the same name. "
            f"Rename it (e.g. to 'req' or 'http_request')."
        )


_MISSING: Any = object()  # sentinel for absent req argument


class WorkerCompat:
    """Make a validation wrapper look like the original handler to the worker.

    The Azure Functions worker (``index_function_app`` / ``loader.py``) inspects
    the registered callable to locate the HTTP trigger parameter and to build
    its annotation map.  Our wrapper uses a ``req`` positional plus a ``**_kw``
    catch-all, which — if exposed verbatim — makes the worker either skip the
    handler or raise ``FunctionLoadError``.  This strategy object applies the
    three compatibility shims that hide those internals.
    """

    # See ._metadata_helpers.copy_identity_attrs for the rationale (no
    # __wrapped__, no __dict__ aliasing).  The attribute set is the canonical
    # SAFE_IDENTITY_ATTRS shared across the DX toolkit.

    def apply(self, wrapper: Callable[..., Any], func: Callable[..., Any]) -> None:
        """Apply all worker-compatibility shims to *wrapper* in place."""
        self._copy_safe_metadata(wrapper, func)
        self._override_signature(wrapper)
        self._clear_annotations(wrapper)

    def _copy_safe_metadata(
        self, wrapper: Callable[..., Any], func: Callable[..., Any]
    ) -> None:
        """Copy safe identity attributes without setting ``__wrapped__``.

        Delegates to the canonical :func:`copy_identity_attrs` helper.
        ``functools.update_wrapper`` is intentionally not used because it sets
        ``__wrapped__ = func``; some worker builds follow it back to the
        original function, see ``co_argcount > 1``, and fail to register.
        """
        copy_identity_attrs(wrapper, func, SAFE_IDENTITY_ATTRS)

    def _override_signature(self, wrapper: Callable[..., Any]) -> None:
        """Expose only the single ``req`` parameter, hiding ``**_kw``.

        Prevents ``FunctionLoadError: 'the following parameters are declared in
        Python but not in the function definition: {'_kw'}'`` at load time.
        """
        _req_param = inspect.Parameter("req", inspect.Parameter.POSITIONAL_OR_KEYWORD)
        setattr(wrapper, "__signature__", inspect.Signature([_req_param]))

    def _clear_annotations(self, wrapper: Callable[..., Any]) -> None:
        """Clear ``__annotations__`` so ``get_type_hints`` returns ``{}``.

        Otherwise the worker sees ``req: typing.Any`` and raises
        ``FunctionLoadError: binding req has invalid non-type annotation``.
        With no annotations it falls back to HttpRequest type inference.
        """
        wrapper.__annotations__ = {}


_WORKER_COMPAT = WorkerCompat()


def _make_wrapper(
    func: Callable[..., Any],
    config: Any,
    *,
    is_async: bool,
) -> Callable[..., Any]:
    """Return a wrapper whose visible signature satisfies the Azure Functions worker.

    The worker (``index_function_app`` / ``loader.py``) inspects ``co_argcount``
    and ``co_varnames`` on the registered callable to locate the HTTP trigger
    parameter.  A ``*args``/``**kwargs``-only wrapper has ``co_argcount == 0``
    and is silently skipped — producing an empty function list on the deployed app.

    We declare a real ``req`` positional parameter (``co_argcount == 1``) so the
    worker recognises the handler.  Callers may also pass the request via its
    *original* parameter name as a keyword argument (e.g. ``handler(request=r)``).
    In that case ``req`` receives a sentinel value and we look up the real object
    from ``**_kw`` using ``config.request_param_name``.

    ``functools.update_wrapper`` is intentionally **not** used because it sets
    ``__wrapped__ = func``, and some Azure Functions worker builds follow
    ``__wrapped__`` to the original function — seeing ``co_argcount > 1`` and
    failing to register the handler.  We copy only the safe metadata attributes.
    """
    orig_name: str = config.request_param_name or "req"

    if is_async:

        async def _async_wrapper(  # noqa: ANN202
            req: Any = _MISSING, **_kw: Any
        ) -> Any:  # noqa: ANN401
            _req = _kw.pop(orig_name, req) if req is _MISSING else req
            return await run_pipeline_async(func, (_req,), _kw, config)

        wrapper: Callable[..., Any] = _async_wrapper
    else:

        def _sync_wrapper(  # noqa: ANN202
            req: Any = _MISSING, **_kw: Any
        ) -> Any:  # noqa: ANN401
            _req = _kw.pop(orig_name, req) if req is _MISSING else req
            return run_pipeline(func, (_req,), _kw, config)

        wrapper = _sync_wrapper

    _WORKER_COMPAT.apply(wrapper, func)

    # Expose validation metadata for external tool integration (e.g., OpenAPI bridge).
    # Uses the ecosystem-wide convention attribute so consumers never need to import
    # this package.  The "validation" namespace is reserved for this package.
    _payload: ValidationMetadata = {
        "version": 1,
        "body": config.body,
        "query": config.query,
        "path": config.path,
        "headers": config.headers,
        "response_model": config.response_model,
    }
    set_validation_metadata(wrapper, func, _payload)

    return wrapper
