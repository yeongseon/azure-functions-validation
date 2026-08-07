"""Tests for the ``endpoint`` namespace written by ``validate_http`` (issue #272).

These assert that the decorator emits ``_azure_functions_metadata["endpoint"]``
alongside the existing ``validation`` namespace, that the payload validates
against the shipped ``endpoint.schema.json`` for every model combination, and
that the SPEC canonicalization rules (aliases, request/response mode, $defs,
request_body_required) are honoured.
"""

from __future__ import annotations

from typing import Any, Mapping, cast

import azure.functions as func
import jsonschema
from pydantic import BaseModel, Field

from azure_functions_validation import validate_http
from azure_functions_validation._endpoint import (
    ENDPOINT_NAMESPACE,
    build_endpoint_metadata,
)
from azure_functions_validation._metadata import METADATA_ATTR, NAMESPACE
from azure_functions_validation.schemas import (
    ENDPOINT_METADATA_VERSION,
    _contains_ref,
    assert_defs_present_if_ref_used,
    load_endpoint_schema,
)

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class Address(BaseModel):
    street: str
    city: str


class CreateUser(BaseModel):
    name: str = Field(alias="fullName")
    email: str
    address: Address
    nickname: str | None = None


class AllOptional(BaseModel):
    a: str = "x"
    b: int = 0


class UserResponse(BaseModel):
    id: int
    name: str


class ListQuery(BaseModel):
    limit: int = 10
    cursor: str | None = None


class PathParams(BaseModel):
    user_id: int


class Headers(BaseModel):
    x_token: str = Field(alias="x-token")


def _endpoint_of(handler: Any) -> dict[str, Any]:
    meta = getattr(handler, METADATA_ATTR)
    return cast("dict[str, Any]", meta[ENDPOINT_NAMESPACE])


def _validate(payload: Mapping[str, Any]) -> None:
    jsonschema.validate(payload, load_endpoint_schema())


# ---------------------------------------------------------------------------
# Namespace presence / backward compat
# ---------------------------------------------------------------------------


class TestNamespaceEmission:
    def test_both_namespaces_written(self) -> None:
        @validate_http(body=CreateUser, response_model=UserResponse)
        def handler(req: func.HttpRequest, body: CreateUser) -> UserResponse:
            return UserResponse(id=1, name=body.name)

        meta = getattr(handler, METADATA_ATTR)
        assert NAMESPACE in meta
        assert ENDPOINT_NAMESPACE in meta

    def test_version_matches_constant(self) -> None:
        @validate_http(body=CreateUser)
        def handler(req: func.HttpRequest, body: CreateUser) -> Any:
            return {}

        assert _endpoint_of(handler)["version"] == ENDPOINT_METADATA_VERSION


# ---------------------------------------------------------------------------
# Schema validity across combinations
# ---------------------------------------------------------------------------


class TestSchemaValidity:
    def test_body_only(self) -> None:
        @validate_http(body=CreateUser)
        def handler(req: func.HttpRequest, body: CreateUser) -> Any:
            return {}

        _validate(_endpoint_of(handler))

    def test_full_combination(self) -> None:
        @validate_http(
            body=CreateUser,
            query=ListQuery,
            path=PathParams,
            headers=Headers,
            response_model=UserResponse,
            status_code=201,
        )
        def handler(req: func.HttpRequest, body: CreateUser) -> UserResponse:
            return UserResponse(id=1, name=body.name)

        payload = _endpoint_of(handler)
        _validate(payload)
        assert set(payload["responses"]) == {"201"}

    def test_no_models(self) -> None:
        @validate_http()
        def handler(req: func.HttpRequest) -> Any:
            return {}

        payload = _endpoint_of(handler)
        _validate(payload)
        assert payload["request_body"] is None
        assert payload["request_body_required"] is False
        assert payload["parameters"] == []
        assert payload["responses"] is None


# ---------------------------------------------------------------------------
# Canonicalization rules
# ---------------------------------------------------------------------------


class TestCanonicalization:
    def test_request_body_keeps_defs_and_ref(self) -> None:
        @validate_http(body=CreateUser)
        def handler(req: func.HttpRequest, body: CreateUser) -> Any:
            return {}

        rb = _endpoint_of(handler)["request_body"]
        assert "$defs" in rb
        assert "Address" in rb["$defs"]
        # Structural invariant holds.
        assert_defs_present_if_ref_used(rb)

    def test_request_body_uses_alias(self) -> None:
        @validate_http(body=CreateUser)
        def handler(req: func.HttpRequest, body: CreateUser) -> Any:
            return {}

        rb = _endpoint_of(handler)["request_body"]
        assert "fullName" in rb["properties"]
        assert "name" not in rb["properties"]

    def test_request_body_required_true_when_field_required(self) -> None:
        @validate_http(body=CreateUser)
        def handler(req: func.HttpRequest, body: CreateUser) -> Any:
            return {}

        assert _endpoint_of(handler)["request_body_required"] is True

    def test_request_body_required_false_when_all_optional(self) -> None:
        @validate_http(body=AllOptional)
        def handler(req: func.HttpRequest, body: AllOptional) -> Any:
            return {}

        assert _endpoint_of(handler)["request_body_required"] is False

    def test_path_parameter_always_required(self) -> None:
        @validate_http(path=PathParams)
        def handler(req: func.HttpRequest) -> Any:
            return {}

        params = _endpoint_of(handler)["parameters"]
        assert params == [
            {
                "name": "user_id",
                "in": "path",
                "required": True,
                "schema": {"type": "integer", "title": "User Id"},
            }
        ]

    def test_query_optional_parameter_not_required(self) -> None:
        @validate_http(query=ListQuery)
        def handler(req: func.HttpRequest) -> Any:
            return {}

        params = {p["name"]: p for p in _endpoint_of(handler)["parameters"]}
        assert params["limit"]["required"] is False
        assert params["cursor"]["required"] is False
        assert all(p["in"] == "query" for p in params.values())

    def test_header_parameter_uses_alias(self) -> None:
        @validate_http(headers=Headers)
        def handler(req: func.HttpRequest) -> Any:
            return {}

        params = _endpoint_of(handler)["parameters"]
        assert params[0]["name"] == "x-token"
        assert params[0]["in"] == "header"

    def test_response_uses_serialization_mode(self) -> None:
        @validate_http(response_model=UserResponse)
        def handler(req: func.HttpRequest) -> UserResponse:
            return UserResponse(id=1, name="a")

        responses = _endpoint_of(handler)["responses"]
        assert set(responses) == {"200"}
        assert responses["200"]["schema"]["properties"].keys() == {"id", "name"}


# ---------------------------------------------------------------------------
# builder unit coverage (non-model inputs)
# ---------------------------------------------------------------------------


class _Config:
    def __init__(self, **kw: Any) -> None:
        self.body = kw.get("body")
        self.query = kw.get("query")
        self.path = kw.get("path")
        self.headers = kw.get("headers")
        self.response_model = kw.get("response_model")
        self.success_status_code = kw.get("success_status_code", 200)


class TestBuilderDirect:
    def test_non_model_inputs_are_ignored(self) -> None:
        payload = build_endpoint_metadata(
            _Config(body="not a model", query=None, response_model=object())
        )
        _validate(payload)
        assert payload["request_body"] is None
        assert payload["parameters"] == []
        assert payload["responses"] is None

    def test_falsy_status_code_defaults_to_200(self) -> None:
        payload = build_endpoint_metadata(
            _Config(response_model=UserResponse, success_status_code=0)
        )
        assert set(payload["responses"] or {}) == {"200"}

    def test_nested_model_param_attaches_defs(self) -> None:
        class NestedQuery(BaseModel):
            addr: Address

        payload = build_endpoint_metadata(_Config(query=NestedQuery))
        _validate(payload)
        schema = payload["parameters"][0]["schema"]
        assert "$defs" in schema
        assert_defs_present_if_ref_used(schema)


class TestContainsRef:
    def test_ref_nested_in_list(self) -> None:
        node = {"anyOf": [{"type": "null"}, {"$ref": "#/$defs/Address"}]}
        assert _contains_ref(node) is True

    def test_no_ref_in_nested_dict(self) -> None:
        node = {"type": "object", "properties": {"name": {"type": "string"}}}
        assert _contains_ref(node) is False

    def test_scalar_is_not_a_ref(self) -> None:
        assert _contains_ref("string") is False
        assert _contains_ref(42) is False
