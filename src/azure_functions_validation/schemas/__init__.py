"""Public schema package for the Azure Functions Python DX Toolkit.

This subpackage ships the JSON Schema for the cross-package ``endpoint``
metadata namespace and a small, dependency-free loader. Producer packages
(this one, ``azure-functions-langgraph``, ...) write the ``endpoint`` payload;
consumer packages (``azure-functions-openapi``) read it. The schema is the
single source of truth for the payload shape so the dict cannot silently
drift across packages.

The schema JSON is distributed as package data and loaded via
:mod:`importlib.resources`, so it is importable at runtime without any new
runtime dependency. ``jsonschema`` is only required to *validate* payloads
against the schema and is a test-only dependency.

See ``docs/METADATA_SPEC.md`` for the full contract, version policy, and
canonicalization rules.
"""

from __future__ import annotations

import hashlib
from importlib import resources
import json
from typing import Any

__all__ = [
    "ENDPOINT_METADATA_VERSION",
    "ENDPOINT_SCHEMA_FILENAME",
    "assert_defs_present_if_ref_used",
    "endpoint_schema_sha256",
    "load_endpoint_schema",
    "pinned_endpoint_schema_sha256",
]

#: Current version of the ``endpoint`` namespace payload. Bump only on a
#: breaking payload change; consumers warn (not fail) on unknown versions.
ENDPOINT_METADATA_VERSION = 1

#: Name of the shipped JSON Schema file within this package.
ENDPOINT_SCHEMA_FILENAME = "endpoint.schema.json"

#: Name of the shipped SHA-256 pin file within this package.
_ENDPOINT_SCHEMA_SHA256_FILENAME = "endpoint.schema.sha256"


def _read_schema_bytes() -> bytes:
    """Return the raw bytes of the shipped schema file."""
    return resources.files(__name__).joinpath(ENDPOINT_SCHEMA_FILENAME).read_bytes()


def load_endpoint_schema() -> dict[str, Any]:
    """Load and parse the ``endpoint`` namespace JSON Schema.

    Returns a fresh ``dict`` on each call so callers may mutate it freely.
    """
    data: dict[str, Any] = json.loads(_read_schema_bytes().decode("utf-8"))
    return data


def endpoint_schema_sha256() -> str:
    """Return the SHA-256 hex digest of the shipped schema file bytes."""
    return hashlib.sha256(_read_schema_bytes()).hexdigest()


def pinned_endpoint_schema_sha256() -> str:
    """Return the pinned SHA-256 digest recorded alongside the schema."""
    text = (
        resources.files(__name__)
        .joinpath(_ENDPOINT_SCHEMA_SHA256_FILENAME)
        .read_text(encoding="utf-8")
    )
    # The pin file may carry a trailing filename (``<digest>  <name>``); take
    # the first whitespace-delimited token.
    return text.strip().split()[0]


def assert_defs_present_if_ref_used(schema: dict[str, Any]) -> None:
    """Enforce the structural rule: any ``$ref`` requires a sibling ``$defs``.

    Producers MUST embed Pydantic schemas with ``$defs`` left unresolved so the
    consumer (openapi) stays the sole ``$ref``-collision authority. A schema
    that contains a ``$ref`` anywhere but omits a top-level ``$defs`` block
    indicates a producer pre-resolved (or dropped) definitions, which breaks
    consumer hoisting. This is not expressible in JSON Schema alone, so it is
    checked here.

    Raises:
        ValueError: if a ``$ref`` occurs anywhere in ``schema`` without a
            top-level ``$defs`` mapping.
    """
    if not isinstance(schema, dict):
        return
    if _contains_ref(schema) and not isinstance(schema.get("$defs"), dict):
        raise ValueError(
            "embedded schema uses '$ref' but has no top-level '$defs'; "
            "producers must keep Pydantic '$defs' unresolved"
        )


def _contains_ref(node: Any) -> bool:
    """Return True if ``$ref`` appears anywhere within ``node``."""
    if isinstance(node, dict):
        if "$ref" in node:
            return True
        return any(_contains_ref(value) for value in node.values())
    if isinstance(node, list):
        return any(_contains_ref(item) for item in node)
    return False
