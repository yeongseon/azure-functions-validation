"""Byte-identity drift guard for ``_metadata_helpers.py``.

``src/azure_functions_validation/_metadata_helpers.py`` is intentionally kept
**byte-identical** across sibling DX Toolkit packages (notably
``azure-functions-validation`` and ``azure-functions-logging``). The primitive
is hand-synced rather than shared via a runtime import, because these packages
are independent PyPI distributions with no common base dependency (sharing was
explicitly rejected in umbrella issue #270).

This test locks the invariant: any accidental edit or reformat of the file
flips the pinned hash and fails CI. When you *intentionally* change the file:

1. Apply the identical change to the mirror in ``azure-functions-logging``.
2. Update ``EXPECTED_SHA256`` below **and** the logging repo's mirror test to
   the new hash in lockstep.

The file is also excluded from ``ruff format`` (see ``[tool.ruff.format]`` in
``pyproject.toml``) and pinned to LF line endings (see ``.gitattributes``) so
formatters and platform checkouts cannot silently break byte-identity.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from azure_functions_validation import _metadata_helpers

# Pinned sha256 of the raw file bytes.
#
# Mirror: azure-functions-logging tests/test_metadata_helpers_drift.py MUST
# assert this exact same hash so drift in EITHER repository fails.
EXPECTED_SHA256 = "a3bde2d205f115faf225222dcbea503eb133f298ef8b8d2587d6030a72944287"

_HELPERS_PATH = Path(_metadata_helpers.__file__)


def test_metadata_helpers_is_byte_identical() -> None:
    """The raw bytes of ``_metadata_helpers.py`` match the pinned hash."""
    digest = hashlib.sha256(_HELPERS_PATH.read_bytes()).hexdigest()
    assert digest == EXPECTED_SHA256, (
        "_metadata_helpers.py drifted from its pinned byte-identical hash. "
        "If this change is intentional, mirror it into azure-functions-logging "
        "and update EXPECTED_SHA256 in BOTH repos in lockstep. See #273 / #270."
    )


def test_metadata_helpers_uses_lf_line_endings() -> None:
    """No CRLF bytes — LF is required for cross-platform byte-identity."""
    assert b"\r\n" not in _HELPERS_PATH.read_bytes()
