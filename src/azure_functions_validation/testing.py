"""Testing helpers for validated Azure Functions handlers.

This module ships :class:`MockHttpRequest`, an ergonomic subclass of
``azure.functions.HttpRequest`` that removes the boilerplate of hand-building
request objects in unit tests.  Because it subclasses the real request type, it
drives the genuine ``@validate_http`` pipeline end-to-end — ``get_json`` and
``get_body`` behave exactly as they do at runtime.

Example
-------
.. code-block:: python

    from azure_functions_validation import validate_http
    from azure_functions_validation.testing import MockHttpRequest


    @validate_http(body=CreateUserRequest, response_model=CreateUserResponse)
    def create_user(req, body):
        return CreateUserResponse(message=f"Hello {body.name}")


    def test_create_user():
        request = MockHttpRequest(
            method="POST",
            json={"name": "Alice", "email": "alice@example.com"},
        )
        response = create_user(request)
        assert response.status_code == 200
"""

from __future__ import annotations

import json as _json
from typing import Any, Mapping

from azure.functions import HttpRequest

__all__ = ["MockHttpRequest"]

_JSON_CONTENT_TYPE = "application/json"


class _Unset:
    """Sentinel type so ``json=None`` can be distinguished from *omitted*."""


_UNSET: Any = _Unset()


class MockHttpRequest(HttpRequest):
    """A convenient ``HttpRequest`` for unit-testing validated handlers.

    Args:
        method: HTTP method. Defaults to ``"GET"``.
        url: Request URL. Defaults to a local test URL.
        body: Raw request body as ``bytes`` or ``str``. Mutually exclusive
            with *json*. A ``str`` is UTF-8 encoded.
        json: A JSON-serializable value encoded as the request body. When
            supplied, a ``Content-Type: application/json`` header is added
            unless one is already present. Mutually exclusive with *body*.
        params: Query-string parameters.
        route_params: Route (path) parameters.
        headers: Request headers.

    Raises:
        ValueError: If both *body* and *json* are provided.
    """

    def __init__(
        self,
        method: str = "GET",
        url: str = "http://localhost/api/test",
        *,
        body: bytes | str | None = None,
        json: Any = _UNSET,
        params: Mapping[str, str] | None = None,
        route_params: Mapping[str, str] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        if json is not _UNSET and body is not None:
            raise ValueError("Provide either 'body' or 'json', not both.")

        resolved_headers = dict(headers or {})
        if json is not _UNSET:
            encoded = _json.dumps(json).encode("utf-8")
            resolved_headers.setdefault("Content-Type", _JSON_CONTENT_TYPE)
        elif isinstance(body, str):
            encoded = body.encode("utf-8")
        elif body is None:
            encoded = b""
        else:
            encoded = body

        super().__init__(
            method,
            url,
            headers=resolved_headers,
            params=dict(params or {}),
            route_params=dict(route_params or {}),
            body=encoded,
        )
