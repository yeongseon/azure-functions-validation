"""Tests for the ``azure_functions_validation.testing`` helpers."""

from __future__ import annotations

import azure.functions as func
from azure.functions import HttpRequest
from pydantic import BaseModel
import pytest

from azure_functions_validation import validate_http
from azure_functions_validation.testing import MockHttpRequest


class _CreateUser(BaseModel):
    name: str
    email: str


class _CreateUserResponse(BaseModel):
    message: str
    status: str = "success"


class _Filters(BaseModel):
    limit: int


class TestMockHttpRequestConstruction:
    def test_is_a_real_http_request(self) -> None:
        request = MockHttpRequest()
        assert isinstance(request, HttpRequest)

    def test_defaults(self) -> None:
        request = MockHttpRequest()
        assert request.method == "GET"
        assert request.url == "http://localhost/api/test"
        assert request.get_body() == b""

    def test_json_body_is_encoded_and_content_type_set(self) -> None:
        request = MockHttpRequest(method="POST", json={"name": "Alice"})
        assert request.get_json() == {"name": "Alice"}
        assert request.headers.get("Content-Type") == "application/json"

    def test_json_none_encodes_null(self) -> None:
        request = MockHttpRequest(json=None)
        assert request.get_body() == b"null"

    def test_explicit_content_type_is_preserved(self) -> None:
        request = MockHttpRequest(
            json={"a": 1}, headers={"Content-Type": "application/vnd.custom+json"}
        )
        assert request.headers["Content-Type"] == "application/vnd.custom+json"

    def test_str_body_is_utf8_encoded(self) -> None:
        request = MockHttpRequest(body="héllo")
        assert request.get_body() == "héllo".encode("utf-8")

    def test_bytes_body_passthrough(self) -> None:
        request = MockHttpRequest(body=b"\x00\x01")
        assert request.get_body() == b"\x00\x01"

    def test_params_and_route_params_and_headers(self) -> None:
        request = MockHttpRequest(
            params={"limit": "10"},
            route_params={"id": "42"},
            headers={"X-Trace": "abc"},
        )
        assert request.params["limit"] == "10"
        assert request.route_params["id"] == "42"
        assert request.headers["X-Trace"] == "abc"

    def test_body_and_json_are_mutually_exclusive(self) -> None:
        with pytest.raises(ValueError, match="either 'body' or 'json'"):
            MockHttpRequest(body=b"{}", json={})


class TestMockHttpRequestDrivesPipeline:
    def test_valid_request_returns_200(self) -> None:
        @validate_http(body=_CreateUser, response_model=_CreateUserResponse)
        def create_user(req: func.HttpRequest, body: _CreateUser) -> _CreateUserResponse:
            return _CreateUserResponse(message=f"Hello {body.name}")

        request = MockHttpRequest(
            method="POST", json={"name": "Alice", "email": "alice@example.com"}
        )
        response = create_user(request)
        assert response.status_code == 200
        assert b"Hello Alice" in response.get_body()

    def test_invalid_request_returns_422(self) -> None:
        @validate_http(body=_CreateUser)
        def create_user(req: func.HttpRequest, body: _CreateUser) -> dict[str, bool]:
            return {"ok": True}

        request = MockHttpRequest(method="POST", json={"name": "Alice"})
        response = create_user(request)
        assert response.status_code == 422

    def test_query_params_validated(self) -> None:
        @validate_http(query=_Filters)
        def search(req: func.HttpRequest, query: _Filters) -> dict[str, int]:
            return {"limit": query.limit}

        response = search(MockHttpRequest(params={"limit": "5"}))
        assert response.status_code == 200
        assert b'"limit": 5' in response.get_body()

    @pytest.mark.anyio
    async def test_async_handler(self) -> None:
        @validate_http(body=_CreateUser, response_model=_CreateUserResponse)
        async def create_user(req: func.HttpRequest, body: _CreateUser) -> _CreateUserResponse:
            return _CreateUserResponse(message=f"Hello {body.name}")

        request = MockHttpRequest(method="POST", json={"name": "Bob", "email": "bob@example.com"})
        response = await create_user(request)
        assert response.status_code == 200
        assert b"Hello Bob" in response.get_body()
