"""Builder for the cross-package ``endpoint`` metadata namespace.

``validate_http`` writes two namespaces onto the wrapped handler under the
shared ``_azure_functions_metadata`` convention attribute:

* ``"validation"`` — this package's own request/response model references
  (kept for the deprecation cycle; see :mod:`._metadata`).
* ``"endpoint"`` — the shared, OpenAPI-ready contract consumed by
  ``azure-functions-openapi``. Unlike the ``validation`` namespace (which
  carries Pydantic model *classes*), the ``endpoint`` payload is entirely
  *self-contained* JSON Schema: the consumer needs no import of this package
  and no access to the user's model classes.

The payload shape and canonicalization rules are pinned by
``schemas/endpoint.schema.json`` and documented in ``docs/METADATA_SPEC.md``.
"""

from __future__ import annotations

from typing import Any, TypedDict

from pydantic import BaseModel

from ._metadata import _merge_namespace
from .schemas import ENDPOINT_METADATA_VERSION, _contains_ref

#: Namespace owned by the shared endpoint contract.
ENDPOINT_NAMESPACE = "endpoint"

#: Pydantic ref template pinned by the SPEC so ``$defs`` stay unresolved and the
#: consumer (openapi) remains the sole ``$ref``-collision authority.
_REF_TEMPLATE = "#/$defs/{model}"


class EndpointMetadata(TypedDict, total=False):
    """Shape of ``_azure_functions_metadata["endpoint"]`` (schema version 1)."""

    version: int
    request_body: dict[str, Any] | None
    request_body_required: bool
    parameters: list[dict[str, Any]]
    responses: dict[str, dict[str, Any]] | None


def _is_model_type(model: Any) -> bool:
    """Return ``True`` if *model* is a Pydantic ``BaseModel`` subclass."""
    return isinstance(model, type) and issubclass(model, BaseModel)


def _model_schema(model: type[BaseModel], mode: str) -> dict[str, Any]:
    """Generate a model's JSON Schema using the SPEC-pinned canonicalization."""
    return model.model_json_schema(
        by_alias=True,
        ref_template=_REF_TEMPLATE,
        mode=mode,  # type: ignore[arg-type]
    )



def _attach_defs_if_ref(
    field_schema: dict[str, Any],
    defs: dict[str, Any] | None,
) -> dict[str, Any]:
    """Attach ``$defs`` to a per-field schema when it uses a ``$ref``.

    Keeps the SPEC's ``$defs``-if-``$ref`` invariant intact for parameter
    schemas that reference a nested model, so the consumer can hoist them.
    """
    if defs and _contains_ref(field_schema):
        merged = dict(field_schema)
        merged["$defs"] = defs
        return merged
    return field_schema


def _build_parameters(model: type[BaseModel], location: str) -> list[dict[str, Any]]:
    """Build OpenAPI parameter objects from a query/path/header model.

    Parameter ``name`` uses the field's serialization alias (``by_alias=True``)
    so it matches the wire contract. ``path`` parameters are always required.
    """
    schema = _model_schema(model, "validation")
    properties: dict[str, Any] = schema.get("properties", {})
    required_names = set(schema.get("required", []))
    defs = schema.get("$defs")

    params: list[dict[str, Any]] = []
    for name, field_schema in properties.items():
        params.append(
            {
                "name": name,
                "in": location,
                "required": location == "path" or name in required_names,
                "schema": _attach_defs_if_ref(dict(field_schema), defs),
            }
        )
    return params


def build_endpoint_metadata(config: Any) -> EndpointMetadata:
    """Build the ``endpoint`` namespace payload from a pipeline config.

    ``config`` exposes ``body``, ``query``, ``path``, ``headers``,
    ``response_model``, and ``success_status_code``.
    """
    body = config.body
    if _is_model_type(body):
        request_body: dict[str, Any] | None = _model_schema(body, "validation")
        request_body_required = any(field.is_required() for field in body.model_fields.values())
    else:
        request_body = None
        request_body_required = False

    parameters: list[dict[str, Any]] = []
    for model, location in (
        (config.query, "query"),
        (config.path, "path"),
        (config.headers, "header"),
    ):
        if _is_model_type(model):
            parameters.extend(_build_parameters(model, location))

    response_model = config.response_model
    if _is_model_type(response_model):
        status = str(getattr(config, "success_status_code", 200) or 200)
        responses: dict[str, dict[str, Any]] | None = {
            status: {"schema": _model_schema(response_model, "serialization")}
        }
    else:
        responses = None

    payload: EndpointMetadata = {
        "version": ENDPOINT_METADATA_VERSION,
        "request_body": request_body,
        "request_body_required": request_body_required,
        "parameters": parameters,
        "responses": responses,
    }
    return payload


def set_endpoint_metadata(wrapper: Any, source: Any, payload: EndpointMetadata) -> None:
    """Merge the ``endpoint`` namespace onto *wrapper* without clobbering others.

    Seeds from any existing convention attribute on *source* (e.g. the
    ``validation`` namespace already written by this decorator), merges in
    *payload* under the ``endpoint`` namespace, and writes the result onto
    *wrapper*.
    """
    _merge_namespace(wrapper, source, ENDPOINT_NAMESPACE, payload)
