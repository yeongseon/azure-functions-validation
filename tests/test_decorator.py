"""Tests for @validate_http decorator configuration (decoration-time errors).

Runtime pipeline behaviour (parsing, response building) is tested in
``test_pipeline.py``.  This file only covers configuration-time validation
that happens when ``@validate_http(...)`` is applied to a function.
"""

from collections.abc import Callable
from typing import TypeVar

from azure.functions import HttpRequest, HttpResponse
from pydantic import BaseModel, Field
import pytest

from azure_functions_validation import validate_http

_HandlerT = TypeVar("_HandlerT", bound=Callable[..., object])

# ---------------------------------------------------------------------------
# Minimal models used by configuration tests
# ---------------------------------------------------------------------------


class UserModel(BaseModel):
    name: str = Field(min_length=3, max_length=50)
    age: int = Field(ge=0, le=150)


class QueryModel(BaseModel):
    limit: int = Field(ge=1, le=100, default=10)
    offset: int = Field(ge=0, default=0)


class PathModel(BaseModel):
    user_id: int = Field(ge=1)


class HeaderModel(BaseModel):
    authorization: str
    user_agent: str = Field(default="unknown")


# ---------------------------------------------------------------------------
# Configuration error tests
# ---------------------------------------------------------------------------


class TestConfigurationErrors:
    """Tests for decorator configuration errors."""

    def test_request_model_with_body_conflict(self) -> None:
        """Test ValueError when request_model and body are both provided."""

        with pytest.raises(
            ValueError, match="Cannot use request_model together with body/query/path/headers"
        ):

            @validate_http(request_model=UserModel, body=UserModel)
            def handler(req: HttpRequest) -> HttpResponse:
                return HttpResponse("ok")

    def test_keyword_only_request_parameter_is_rejected(self) -> None:
        """Test ValueError when the request parameter is not positional."""

        with pytest.raises(
            ValueError,
            match="must accept an HttpRequest parameter as its first positional argument",
        ):

            @validate_http(body=UserModel)
            def handler(*, request: HttpRequest) -> HttpResponse:
                return HttpResponse("ok")

    def test_request_param_name_conflicts_with_body_injection(self) -> None:
        """Test ValueError when the first positional param is named 'body' and body= is set."""

        with pytest.raises(
            ValueError,
            match="conflicts with a @validate_http injected parameter of the same name",
        ):

            @validate_http(body=UserModel)
            def handler(body: HttpRequest, user: UserModel) -> HttpResponse:
                return HttpResponse("ok")

    def test_request_param_name_conflicts_with_query_injection(self) -> None:
        """Test ValueError when the first positional param is named 'query' and query= is set."""

        with pytest.raises(
            ValueError,
            match="conflicts with a @validate_http injected parameter of the same name",
        ):

            @validate_http(query=QueryModel)
            def handler(query: HttpRequest) -> HttpResponse:
                return HttpResponse("ok")

    def test_request_param_name_conflicts_with_path_injection(self) -> None:
        """Test ValueError when the first positional param is named 'path' and path= is set."""

        with pytest.raises(
            ValueError,
            match="conflicts with a @validate_http injected parameter of the same name",
        ):

            @validate_http(path=PathModel)
            def handler(path: HttpRequest) -> HttpResponse:
                return HttpResponse("ok")

    def test_request_param_name_conflicts_with_headers_injection(self) -> None:
        """Test a conflict when the first positional parameter is named `headers`."""

        with pytest.raises(
            ValueError,
            match="conflicts with a @validate_http injected parameter of the same name",
        ):

            @validate_http(headers=HeaderModel)
            def handler(headers: HttpRequest) -> HttpResponse:
                return HttpResponse("ok")

    def test_request_param_named_body_without_injection_is_allowed(self) -> None:
        """No error when param is named 'body' but no body= is configured."""

        # Should not raise – body injection is not enabled
        @validate_http()
        def handler(body: HttpRequest) -> HttpResponse:
            return HttpResponse("ok")

    def test_safe_request_param_names_are_allowed(self) -> None:
        """Standard param names like 'req' / 'request' / 'http_request' must not raise."""

        for name in ("req", "request", "http_request"):

            @validate_http(body=UserModel)
            def handler(req: HttpRequest, body: UserModel) -> HttpResponse:  # noqa: F811
                return HttpResponse("ok")


# ---------------------------------------------------------------------------
# Metadata isolation regression tests (issue #185)
# ---------------------------------------------------------------------------


class TestMetadataIsolation:
    """Regression tests: decorator must not leak state onto the original func."""

    def test_wrapper_dict_is_not_aliased_to_func_dict(self) -> None:
        """`wrapper.__dict__` must be a distinct dict from `func.__dict__`."""

        def handler(req: HttpRequest, body: UserModel) -> HttpResponse:
            return HttpResponse("ok")

        wrapped = validate_http(body=UserModel)(handler)
        assert wrapped.__dict__ is not handler.__dict__

    def test_metadata_is_not_leaked_onto_original_func(self) -> None:
        """`_azure_functions_metadata` must live on wrapper only, not original."""

        def handler(req: HttpRequest, body: UserModel) -> HttpResponse:
            return HttpResponse("ok")

        wrapped = validate_http(body=UserModel)(handler)
        assert hasattr(wrapped, "_azure_functions_metadata")
        assert not hasattr(handler, "_azure_functions_metadata")

    def test_wrapper_has_no_dunder_wrapped(self) -> None:
        """`__wrapped__` must not be set (Azure worker would follow it)."""

        def handler(req: HttpRequest, body: UserModel) -> HttpResponse:
            return HttpResponse("ok")

        wrapped = validate_http(body=UserModel)(handler)
        assert not hasattr(wrapped, "__wrapped__")


class TestCopyIdentityAttrs:
    """The canonical ``copy_identity_attrs`` primitive must not leak state."""

    def test_copies_identity_without_wrapped_or_dict_alias(self) -> None:
        from azure_functions_validation._metadata_helpers import (
            SAFE_IDENTITY_ATTRS,
            copy_identity_attrs,
        )

        def func(req: object, context: object) -> None:
            """Original docstring."""

        def wrapper(*args: object, **kwargs: object) -> None:
            pass

        copy_identity_attrs(wrapper, func)

        for attr in SAFE_IDENTITY_ATTRS:
            assert getattr(wrapper, attr) == getattr(func, attr)
        # __wrapped__ must NOT be set (defeats worker indexing otherwise).
        assert not hasattr(wrapper, "__wrapped__")
        # __dict__ must not be aliased: mutating wrapper must not touch func.
        wrapper.__dict__["_marker"] = 1
        assert "_marker" not in func.__dict__


# ---------------------------------------------------------------------------
# Wrong decorator order detection (issue #251)
# ---------------------------------------------------------------------------


class TestWrongDecoratorOrder:
    """@validate_http applied above @app.route must warn, not silently no-op."""

    def test_real_sdk_function_builder_warns_and_returns_unwrapped(self) -> None:
        """A genuine SDK ``FunctionBuilder`` (from ``@app.route``) must be detected.

        Uses the real ``azure.functions`` SDK so this test fails automatically if a
        future SDK release changes how ``FunctionBuilder`` is produced or named.
        """
        import azure.functions as azf
        from azure.functions.decorators.function_app import FunctionBuilder

        app = azf.FunctionApp()

        def handler(req: HttpRequest, body: UserModel) -> HttpResponse:  # pragma: no cover
            return HttpResponse("ok")

        # ``app.route(...)`` returns a FunctionBuilder; applying @validate_http on
        # top of that reproduces the wrong-order mistake (decorator above @app.route).
        builder = app.route(route="users", methods=["POST"])(handler)
        assert isinstance(builder, FunctionBuilder)

        with pytest.warns(RuntimeWarning, match=r"@app\.route"):
            result = validate_http(body=UserModel)(builder)
        assert result is builder

    def test_function_builder_by_type_name_fallback_warns(self) -> None:
        """SDK builds without the method are still caught by the type-name fallback."""

        class FunctionBuilder:  # name is the fallback signal
            pass

        builder = FunctionBuilder()
        with pytest.warns(RuntimeWarning, match="FunctionBuilder"):
            result = validate_http(body=UserModel)(builder)
        assert result is builder

    def test_normal_handler_is_not_flagged(self, recwarn: pytest.WarningsRecorder) -> None:
        """A normal handler must wrap without emitting the wrong-order warning."""

        def handler(req: HttpRequest, body: UserModel) -> HttpResponse:
            return HttpResponse("ok")

        wrapped = validate_http(body=UserModel)(handler)
        assert wrapped is not handler
        assert not any(issubclass(w.category, RuntimeWarning) for w in recwarn.list)


class TestLoggingDecoratorOrder:
    """@validate_http above @with_context must warn (validation errors lose context)."""

    @staticmethod
    def _with_logging_metadata(handler: _HandlerT) -> _HandlerT:
        """Simulate ``@with_context`` having run first (inner) on *handler*."""
        from azure_functions_validation._metadata import METADATA_ATTR

        setattr(
            handler,
            METADATA_ATTR,
            {"logging": {"version": 1, "context_param": "context"}},
        )
        return handler

    def test_warns_when_logging_metadata_present(self) -> None:
        """Wrong order: @with_context applied inner leaves a ``logging`` namespace."""

        def handler(req: HttpRequest, body: UserModel) -> HttpResponse:
            return HttpResponse("ok")

        inner = self._with_logging_metadata(handler)
        with pytest.warns(RuntimeWarning, match=r"@with_context"):
            wrapped = validate_http(body=UserModel)(inner)
        assert wrapped is not inner

    def test_warns_for_async_handler(self) -> None:
        """The guard fires before sync/async dispatch, so async handlers warn too."""

        async def handler(req: HttpRequest, body: UserModel) -> HttpResponse:
            return HttpResponse("ok")

        inner = self._with_logging_metadata(handler)
        with pytest.warns(RuntimeWarning, match=r"@with_context"):
            wrapped = validate_http(body=UserModel)(inner)
        assert wrapped is not inner


    def test_warns_preserves_logging_namespace(self) -> None:
        """The wrapper keeps the pre-existing ``logging`` namespace (merge, no clobber)."""
        from azure_functions_validation._metadata import METADATA_ATTR

        def handler(req: HttpRequest, body: UserModel) -> HttpResponse:
            return HttpResponse("ok")

        inner = self._with_logging_metadata(handler)
        with pytest.warns(RuntimeWarning, match=r"@with_context"):
            wrapped = validate_http(body=UserModel)(inner)
        meta = getattr(wrapped, METADATA_ATTR)
        assert "logging" in meta
        assert "validation" in meta

    def test_no_warning_for_correct_order(
        self, recwarn: pytest.WarningsRecorder
    ) -> None:
        """Correct order: @validate_http runs first, sees no ``logging`` namespace."""

        def handler(req: HttpRequest, body: UserModel) -> HttpResponse:
            return HttpResponse("ok")

        wrapped = validate_http(body=UserModel)(handler)
        assert wrapped is not handler
        assert not any(issubclass(w.category, RuntimeWarning) for w in recwarn.list)

    def test_no_warning_for_unrelated_namespace(
        self, recwarn: pytest.WarningsRecorder
    ) -> None:
        """A non-logging namespace (e.g. another sibling) must not trigger the warning."""
        from azure_functions_validation._metadata import METADATA_ATTR

        def handler(req: HttpRequest, body: UserModel) -> HttpResponse:
            return HttpResponse("ok")

        setattr(handler, METADATA_ATTR, {"openapi": {"version": 1}})
        wrapped = validate_http(body=UserModel)(handler)
        assert wrapped is not handler
        assert not any(issubclass(w.category, RuntimeWarning) for w in recwarn.list)



# ---------------------------------------------------------------------------
# Worker-indexing regression: handlers declaring (req, context) (issue #284)
# ---------------------------------------------------------------------------


class TestReqContextWorkerIndexing:
    """Lock worker-compat behavior for handlers that declare ``(req, context)``.

    The Azure Functions worker indexes a handler by its exposed signature and
    ``co_argcount``. ``@validate_http`` must keep the exposed signature a single
    ``req`` parameter, clear annotations, and avoid ``__wrapped__`` even when the
    original handler also declares a worker-injected ``context`` binding, while
    still forwarding ``context`` through to the handler at call time.
    """

    def test_sync_exposes_single_req_signature(self) -> None:
        import inspect

        @validate_http(query=QueryModel)
        def handler(req: HttpRequest, context: object) -> HttpResponse:
            return HttpResponse("ok")

        assert list(inspect.signature(handler).parameters) == ["req"]
        assert handler.__annotations__ == {}
        assert not hasattr(handler, "__wrapped__")

    def test_sync_forwards_context_and_returns_success(self) -> None:
        from azure_functions_validation.testing import MockHttpRequest

        seen: dict[str, object] = {}

        @validate_http(query=QueryModel)
        def handler(req: HttpRequest, context: object, query: QueryModel) -> HttpResponse:
            seen["context"] = context
            seen["query"] = query
            return HttpResponse("ok")

        sentinel = object()
        response = handler(MockHttpRequest(params={"limit": "5"}), context=sentinel)

        assert response.status_code == 200
        assert seen["context"] is sentinel
        assert isinstance(seen["query"], QueryModel)
        assert seen["query"].limit == 5

    @pytest.mark.anyio
    async def test_async_exposes_single_req_and_forwards_context(self) -> None:
        import inspect

        from azure_functions_validation.testing import MockHttpRequest

        seen: dict[str, object] = {}

        @validate_http(query=QueryModel)
        async def handler(
            req: HttpRequest, context: object, query: QueryModel
        ) -> HttpResponse:
            seen["context"] = context
            return HttpResponse("ok")

        assert list(inspect.signature(handler).parameters) == ["req"]
        assert handler.__annotations__ == {}
        assert not hasattr(handler, "__wrapped__")

        sentinel = object()
        response = await handler(MockHttpRequest(params={"limit": "5"}), context=sentinel)

        assert response.status_code == 200
        assert seen["context"] is sentinel