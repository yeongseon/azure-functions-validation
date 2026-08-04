"""Tests for the _azure_functions_metadata convention.

Mirrors test_toolkit_metadata.py in sibling packages (db, logging, langgraph)
to ensure consistent convention compliance across the ecosystem.
"""

from __future__ import annotations

from unittest.mock import Mock

from azure.functions import HttpRequest
from pydantic import BaseModel

from azure_functions_validation import validate_http

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TOOLKIT_META_ATTR = "_azure_functions_metadata"


class UserModel(BaseModel):
    name: str
    age: int


class QueryModel(BaseModel):
    page: int = 1


class PathModel(BaseModel):
    item_id: str


class HeaderModel(BaseModel):
    x_request_id: str


def _make_request(body: bytes = b'{"name": "Alice", "age": 30}') -> Mock:
    mock_req = Mock(spec=HttpRequest)
    mock_req.method = "POST"
    mock_req.url = "http://test"
    mock_req.get_body.return_value = body
    mock_req.params = {}
    mock_req.route_params = {}
    mock_req.headers = {}
    return mock_req


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestToolkitMetadataConvention:
    """Verify _azure_functions_metadata convention compliance."""

    def test_metadata_attribute_exists_on_decorated_function(self) -> None:
        @validate_http(body=UserModel)
        def handler(req: HttpRequest, body: UserModel) -> dict[str, object]:
            return {"ok": True}

        assert hasattr(handler, _TOOLKIT_META_ATTR)

    def test_metadata_is_dict_with_validation_namespace(self) -> None:
        @validate_http(body=UserModel)
        def handler(req: HttpRequest, body: UserModel) -> dict[str, object]:
            return {"ok": True}

        meta = getattr(handler, _TOOLKIT_META_ATTR)
        assert isinstance(meta, dict)
        assert "validation" in meta

    def test_metadata_payload_has_version(self) -> None:
        @validate_http(body=UserModel)
        def handler(req: HttpRequest, body: UserModel) -> dict[str, object]:
            return {"ok": True}

        meta = getattr(handler, _TOOLKIT_META_ATTR)
        payload = meta["validation"]
        assert payload["version"] == 1

    def test_metadata_payload_contains_models(self) -> None:
        @validate_http(body=UserModel, query=QueryModel, response_model=UserModel)
        def handler(req: HttpRequest, body: UserModel, query: QueryModel) -> dict[str, object]:
            return {"ok": True}

        meta = getattr(handler, _TOOLKIT_META_ATTR)
        payload = meta["validation"]
        assert payload["body"] is UserModel
        assert payload["query"] is QueryModel
        assert payload["response_model"] is UserModel
        assert payload["path"] is None
        assert payload["headers"] is None

    def test_metadata_payload_none_when_no_models(self) -> None:
        @validate_http(response_model=UserModel)
        def handler(req: HttpRequest) -> dict[str, object]:
            return {"name": "Alice", "age": 30}

        meta = getattr(handler, _TOOLKIT_META_ATTR)
        payload = meta["validation"]
        assert payload["body"] is None
        assert payload["query"] is None
        assert payload["path"] is None
        assert payload["headers"] is None
        assert payload["response_model"] is UserModel

    def test_merge_preserves_preexisting_metadata(self) -> None:
        """Metadata set on func BEFORE @validate_http must survive decoration."""

        def handler(req: HttpRequest, body: UserModel) -> dict[str, object]:
            return {"ok": True}

        # Another decorator already wrote metadata before validation runs.
        setattr(
            handler,
            "_azure_functions_metadata",
            {"other_package": {"version": 1, "data": "test"}},
        )

        wrapped = validate_http(body=UserModel)(handler)

        current = getattr(wrapped, _TOOLKIT_META_ATTR)
        assert current["other_package"] == {"version": 1, "data": "test"}
        assert "validation" in current
        assert current["validation"]["body"] is UserModel

    def test_namespace_preservation_with_foreign_metadata(self) -> None:
        """Multiple foreign namespaces set before decoration must all survive."""

        def handler(req: HttpRequest, body: UserModel) -> dict[str, object]:
            return {"ok": True}

        # Two other packages already wrote metadata before validation.
        setattr(
            handler,
            "_azure_functions_metadata",
            {
                "package_a": {"version": 1, "foo": "bar"},
                "package_b": {"enabled": True},
            },
        )

        wrapped = validate_http(body=UserModel)(handler)

        updated = getattr(wrapped, _TOOLKIT_META_ATTR)
        assert "validation" in updated
        assert updated["package_a"] == {"version": 1, "foo": "bar"}
        assert updated["package_b"] == {"enabled": True}
        assert updated["validation"]["version"] == 1
        assert updated["validation"]["body"] is UserModel

    def test_async_handler_has_metadata(self) -> None:
        @validate_http(body=UserModel)
        async def handler(req: HttpRequest, body: UserModel) -> dict[str, object]:
            return {"ok": True}

        assert hasattr(handler, _TOOLKIT_META_ATTR)
        meta = getattr(handler, _TOOLKIT_META_ATTR)
        assert "validation" in meta
        assert meta["validation"]["body"] is UserModel

    def test_metadata_absent_on_undecorated_function(self) -> None:
        """Non-decorated function has no metadata attribute."""

        def handler(req: HttpRequest) -> dict[str, object]:
            return {"ok": True}

        assert not hasattr(handler, _TOOLKIT_META_ATTR)

    def test_request_model_shorthand_maps_to_body(self) -> None:
        """request_model= shorthand is stored as body in metadata."""

        @validate_http(request_model=UserModel)
        def handler(req: HttpRequest, body: UserModel) -> dict[str, object]:
            return {"ok": True}

        meta = getattr(handler, _TOOLKIT_META_ATTR)
        assert meta["validation"]["body"] is UserModel

    def test_metadata_all_param_types(self) -> None:
        """All five parameter types are captured in metadata."""

        @validate_http(
            body=UserModel,
            query=QueryModel,
            path=PathModel,
            headers=HeaderModel,
            response_model=UserModel,
        )
        def handler(
            req: HttpRequest,
            body: UserModel,
            query: QueryModel,
            path: PathModel,
            headers: HeaderModel,
        ) -> dict[str, object]:
            return {"ok": True}

        meta = getattr(handler, _TOOLKIT_META_ATTR)
        payload = meta["validation"]
        assert payload["body"] is UserModel
        assert payload["query"] is QueryModel
        assert payload["path"] is PathModel
        assert payload["headers"] is HeaderModel
        assert payload["response_model"] is UserModel
