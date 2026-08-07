"""Typed cross-package metadata contract for the ``validation`` namespace.

Toolkit convention (shared across the Azure Functions Python DX Toolkit):
decorators attach an ``_azure_functions_metadata`` dict onto the wrapped
handler, keyed by a package-owned *namespace* string, so sibling packages
(e.g. ``azure-functions-openapi``) can discover metadata **without importing
this package**.

This module gives the ``"validation"`` namespace payload a checked
``TypedDict`` shape plus a single merge helper. The contract is intentionally
*replicated* across toolkit packages (not shared via a runtime dependency);
keep the ``_BaseMetadata`` ``version`` field and the merge-without-clobber
semantics identical to the sibling packages. Consumers keep their own
read-side mirror of :class:`ValidationMetadata`.

Ref: https://github.com/yeongseon/azure-functions-validation-python/issues/223
"""

from __future__ import annotations

from typing import Any, TypedDict, cast

#: Convention attribute name shared across all toolkit packages.
METADATA_ATTR = "_azure_functions_metadata"

#: Namespace owned by this package.
NAMESPACE = "validation"

#: Schema version for the ``validation`` namespace payload.
VALIDATION_METADATA_VERSION = 1


class _BaseMetadata(TypedDict):
    """Fields common to every toolkit namespace payload."""

    version: int


class ValidationMetadata(_BaseMetadata):
    """Shape of ``_azure_functions_metadata["validation"]`` (schema version 1).

    The model fields hold the Pydantic model *type* (or ``None``) supplied to
    ``@validate_http`` — deliberately typed ``Any`` because the concrete model
    class varies per user.
    """

    body: Any
    query: Any
    path: Any
    headers: Any
    response_model: Any


def _merge_namespace(wrapper: Any, source: Any, namespace: str, payload: Any) -> None:
    """Merge *payload* under *namespace* onto *wrapper* without clobbering others.

    Seeds from any pre-existing convention attribute on *source* (set by other
    decorators applied before this one, or by an earlier namespace write in the
    same decorator), merges in *payload* under *namespace*, and writes the
    result onto *wrapper*.
    """
    existing = getattr(source, METADATA_ATTR, None)
    base: dict[str, Any] = dict(existing) if isinstance(existing, dict) else {}
    base[namespace] = payload
    setattr(wrapper, METADATA_ATTR, base)


def set_validation_metadata(
    wrapper: Any,
    func: Any,
    payload: ValidationMetadata,
) -> None:
    """Merge the ``validation`` namespace onto ``wrapper`` without clobbering others.

    Seeds from any pre-existing convention attribute on ``func`` (set by other
    decorators applied before this one), merges in ``payload`` under the
    ``validation`` namespace, and writes the result onto ``wrapper``.
    """
    _merge_namespace(wrapper, func, NAMESPACE, payload)


def read_validation_metadata(func: Any) -> ValidationMetadata | None:
    """Return the typed ``validation`` namespace payload, or ``None`` if absent."""
    md = getattr(func, METADATA_ATTR, None)
    if isinstance(md, dict):
        entry = md.get(NAMESPACE)
        if isinstance(entry, dict):
            return cast("ValidationMetadata", entry)
    return None
