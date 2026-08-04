"""E2E tests for azure-functions-validation on a real Azure Functions host.

Usage:
    E2E_BASE_URL=https://<app>.azurewebsites.net pytest tests/e2e -v
"""

from __future__ import annotations

import os
import time

import pytest
import requests

BASE_URL = os.environ.get("E2E_BASE_URL", "").rstrip("/")
SKIP_REASON = "E2E_BASE_URL not set — skipping real-Azure e2e tests"


def _post(path: str, body: object) -> requests.Response:
    return requests.post(
        f"{BASE_URL}{path}",
        json=body,
        headers={"Content-Type": "application/json"},
        timeout=30,
    )


@pytest.fixture(scope="session", autouse=True)
def warmup() -> None:
    if not BASE_URL:
        return
    deadline = time.time() + 300
    while time.time() < deadline:
        try:
            r = requests.get(f"{BASE_URL}/api/health", timeout=10)
            if r.status_code == 200:
                return
        except requests.RequestException:
            pass
        time.sleep(3)
    pytest.fail("Warmup failed: /api/health did not respond within 300 s")


@pytest.mark.skipif(not BASE_URL, reason=SKIP_REASON)
def test_health_returns_200() -> None:
    r = requests.get(f"{BASE_URL}/api/health", timeout=30)
    assert r.status_code == 200
    body = r.json()
    if body.get("import_error"):
        pytest.fail(f"Library import failed on Azure host:\n{body['import_error']}")
    assert body["status"] == "ok"


@pytest.mark.skipif(not BASE_URL, reason=SKIP_REASON)
def test_valid_request_returns_200() -> None:
    r = _post("/api/items", {"name": "widget", "quantity": 5})
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "widget"
    assert body["quantity"] == 5
    assert "id" in body


@pytest.mark.skipif(not BASE_URL, reason=SKIP_REASON)
def test_missing_required_field_returns_422() -> None:
    # Missing 'quantity'
    r = _post("/api/items", {"name": "widget"})
    assert r.status_code == 422
    body = r.json()
    assert "detail" in body


@pytest.mark.skipif(not BASE_URL, reason=SKIP_REASON)
def test_invalid_field_type_returns_422() -> None:
    # quantity must be int >= 1, passing negative
    r = _post("/api/items", {"name": "widget", "quantity": -1})
    assert r.status_code == 422


@pytest.mark.skipif(not BASE_URL, reason=SKIP_REASON)
def test_empty_body_returns_422() -> None:
    r = _post("/api/items", {})
    assert r.status_code == 422


@pytest.mark.skipif(not BASE_URL, reason=SKIP_REASON)
def test_empty_name_returns_422() -> None:
    r = _post("/api/items", {"name": "", "quantity": 1})
    assert r.status_code == 422
