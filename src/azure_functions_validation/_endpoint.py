"""Builder for the cross-package ``endpoint`` metadata namespace.

``validate_http`` writes two namespaces onto the wrapped handler under the
shared ``_azure_functions_metadata`` convention attribute:

* ``"validation"`` — this package's own request/response model references
  (kept for the deprecation cycle; see :mod:`._metadata`).
* ``"endpoint"`` — this package's local, OpenAPI-ready endpoint payload,
  consumed by ``azure-functions-openapi``. Unlike the ``validation`` namespace
  (which carries Pydantic model *classes*), the ``endpoint`` payload is entirely
  *self-contained* JSON Schema: the consumer needs no import of this package
  and no access to the user's model classes.

This package's payload shape and canonicalization rules are checked against
``schemas/endpoint.schema.json`` — a local conformance artifact — and
documented in ``docs/METADATA_SPEC.md``.
"""

from __future__ import annotations

from typing import Any, TypedDict

from pydantic import BaseModel

from ._metadata import _merge_namespace
from .schemas import ENDPOINT_METADATA_VERSION, _contains_ref

#: Namespace for this package's local endpoint payload.
ENDPOINT_NAMESPACE = "endpoint"

#: Pydantic ref template used by this producer so ``$defs`` stay unresolved and
#: the consumer (openapi) remains the sole ``$ref``-collision authority.
_REF_TEMPLATE = "#/$defs/{model}"

#: HTTP status code under which the standardized validation-error response is
#: documented. Emitted whenever request validation can fail (any of
#: ``body``/``query``/``path``/``headers`` is a model).
_VALIDATION_ERROR_STATUS = "422"


def _validation_error_schema() -> dict[str, Any]:
    """Return a self-contained JSON Schema for the ``{"detail": [...]}`` envelope.

    Mirrors the runtime 422 body produced by the pipeline (see
    ``pipeline.format_error_response``): a ``detail`` array of items with
    ``loc`` / ``msg`` / ``type``. A fresh dict is built on every call so
    consumers may mutate the embedded schema freely without cross-handler
    aliasing. Contains no ``$ref``, so the ``$defs``-if-``$ref`` rule does not
    apply.
    """
    return {
        "type": "object",
        "properties": {
            "detail": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "loc": {
                            "type": "array",
                            "items": {"type": ["string", "integer"]},
                        },
                        "msg": {"type": "string"},
                        "type": {"type": "string"},
                    },
                    "required": ["loc", "msg", "type"],
                },
            }
        },
        "required": ["detail"],
    }


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
        # The runtime adapter unconditionally rejects an empty body (422) whenever
        # a body model is configured, regardless of individual field optionality,
        # so the metadata must report the body as required to stay truthful to
        # actual server behaviour (#347). Optional-body support, if ever added,
        # must be an explicit opt-in that also relaxes the runtime 422.
        request_body_required = True
    else:
        request_body = None
        request_body_required = False

    parameters: list[dict[str, Any]] = []
    has_request_model = False
    for model, location in (
        (config.query, "query"),
        (config.path, "path"),
        (config.headers, "header"),
    ):
        if _is_model_type(model):
            has_request_model = True
            parameters.extend(_build_parameters(model, location))

    # A request body model also makes request validation (and thus a 422) possible.
    has_request_model = has_request_model or _is_model_type(body)

    responses: dict[str, dict[str, Any]] = {}
    response_model = config.response_model
    if _is_model_type(response_model):
        status = str(getattr(config, "success_status_code", 200) or 200)
        responses[status] = {"schema": _model_schema(response_model, "serialization")}
    if has_request_model:
        # Document the standardized validation-error contract the runtime emits
        # on invalid input, so consumers (openapi) need not hand-author it.
        responses[_VALIDATION_ERROR_STATUS] = {"schema": _validation_error_schema()}

    payload: EndpointMetadata = {
        "version": ENDPOINT_METADATA_VERSION,
        "request_body": request_body,
        "request_body_required": request_body_required,
        "parameters": parameters,
        "responses": responses or None,
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
