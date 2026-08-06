"""Tests for the ``endpoint`` metadata namespace schema (issue #271).

These tests pin the shape of ``_azure_functions_metadata["endpoint"]`` so the
cross-package contract cannot drift. They validate that the shipped JSON Schema
is itself a valid JSON Schema, that a representative payload passes, that an
invalid payload fails, and that the ``$defs``-if-``$ref`` structural rule and the
SHA-256 pin hold.
"""

from __future__ import annotations

import hashlib
from importlib import resources
from typing import Any

import jsonschema
from jsonschema.validators import Draft202012Validator
import pytest

from azure_functions_validation.schemas import (
    ENDPOINT_METADATA_VERSION,
    ENDPOINT_SCHEMA_FILENAME,
    assert_defs_present_if_ref_used,
    endpoint_schema_sha256,
    load_endpoint_schema,
    pinned_endpoint_schema_sha256,
)


def _representative_payload() -> dict[str, Any]:
    return {
        "version": 1,
        "request_body": {
            "type": "object",
            "title": "CreateUserRequest",
            "properties": {
                "name": {"type": "string"},
                "email": {"type": "string"},
            },
            "required": ["name", "email"],
        },
        "request_body_required": True,
        "parameters": [
            {
                "name": "user_id",
                "in": "path",
                "required": True,
                "schema": {"type": "integer"},
            }
        ],
        "responses": {
            "200": {
                "description": "OK",
                "schema": {
                    "type": "object",
                    "title": "UserResponse",
                    "properties": {"id": {"type": "integer"}, "name": {"type": "string"}},
                },
            }
        },
        "summary": "Create a user",
        "description": "Creates a user and returns it.",
        "tags": ["users"],
        "security": [{"apiKey": []}],
    }


class TestSchemaDocument:
    def test_schema_is_valid_json_schema(self) -> None:
        schema = load_endpoint_schema()
        # Raises jsonschema.exceptions.SchemaError if the document is invalid.
        Draft202012Validator.check_schema(schema)

    def test_schema_declares_2020_12(self) -> None:
        schema = load_endpoint_schema()
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"

    def test_load_returns_fresh_copy(self) -> None:
        first = load_endpoint_schema()
        first["mutated"] = True
        second = load_endpoint_schema()
        assert "mutated" not in second

    def test_version_constant_matches_schema(self) -> None:
        schema = load_endpoint_schema()
        assert ENDPOINT_METADATA_VERSION == schema["properties"]["version"]["const"]
        assert ENDPOINT_METADATA_VERSION == 1


class TestPayloadValidation:
    def test_representative_payload_passes(self) -> None:
        jsonschema.validate(_representative_payload(), load_endpoint_schema())

    def test_minimal_payload_passes(self) -> None:
        jsonschema.validate({"version": 1}, load_endpoint_schema())

    def test_null_request_body_and_responses_pass(self) -> None:
        payload = {"version": 1, "request_body": None, "responses": None}
        jsonschema.validate(payload, load_endpoint_schema())

    def test_missing_version_fails(self) -> None:
        payload = _representative_payload()
        del payload["version"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(payload, load_endpoint_schema())

    def test_wrong_version_fails(self) -> None:
        payload = _representative_payload()
        payload["version"] = 2
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(payload, load_endpoint_schema())

    def test_unknown_top_level_key_fails(self) -> None:
        payload = _representative_payload()
        payload["path"] = "/users"  # path is intentionally not part of the contract
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(payload, load_endpoint_schema())

    def test_bad_parameter_location_fails(self) -> None:
        payload = _representative_payload()
        payload["parameters"][0]["in"] = "body"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(payload, load_endpoint_schema())

    def test_non_status_response_key_fails(self) -> None:
        payload = _representative_payload()
        payload["responses"] = {"ok": {"description": "OK"}}
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(payload, load_endpoint_schema())


class TestDefsIfRefRule:
    def test_ref_with_defs_passes(self) -> None:
        schema = {
            "type": "object",
            "properties": {"pet": {"$ref": "#/$defs/Pet"}},
            "$defs": {"Pet": {"type": "object"}},
        }
        assert_defs_present_if_ref_used(schema)  # no raise

    def test_ref_without_defs_raises(self) -> None:
        schema = {
            "type": "object",
            "properties": {"pet": {"$ref": "#/$defs/Pet"}},
        }
        with pytest.raises(ValueError, match=r"\$defs"):
            assert_defs_present_if_ref_used(schema)

    def test_nested_ref_without_defs_raises(self) -> None:
        schema = {
            "type": "object",
            "properties": {
                "items": {"type": "array", "items": {"$ref": "#/$defs/Item"}},
            },
        }
        with pytest.raises(ValueError, match=r"\$defs"):
            assert_defs_present_if_ref_used(schema)

    def test_no_ref_no_defs_passes(self) -> None:
        assert_defs_present_if_ref_used({"type": "object"})

    def test_ref_inside_list_without_defs_raises(self) -> None:
        schema = {"type": "object", "anyOf": [{"$ref": "#/$defs/A"}]}
        with pytest.raises(ValueError, match=r"\$defs"):
            assert_defs_present_if_ref_used(schema)

    def test_non_dict_is_ignored(self) -> None:
        assert_defs_present_if_ref_used("not a dict")


class TestSchemaHashPin:
    def test_runtime_digest_matches_pin(self) -> None:
        assert endpoint_schema_sha256() == pinned_endpoint_schema_sha256()

    def test_digest_matches_file_bytes(self) -> None:
        raw = (
            resources.files("azure_functions_validation.schemas")
            .joinpath(ENDPOINT_SCHEMA_FILENAME)
            .read_bytes()
        )
        assert endpoint_schema_sha256() == hashlib.sha256(raw).hexdigest()
