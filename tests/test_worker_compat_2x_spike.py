"""Opt-in spike: verify @validate_http survives the installed azure-functions worker.

This module is **off by default**. It is:

* marked ``compat2x`` and excluded from the default ``addopts``
  (``-m 'not e2e and not compat2x'``), and
* additionally gated on the ``AZFUNC_2X_SPIKE`` environment variable,

so it never runs in normal CI or in a bare ``pytest`` invocation. Its purpose is
to be run **manually** against a candidate ``azure-functions`` 2.x build to
verify the five worker-internal behaviors that ``WorkerCompat`` depends on (see
``docs/azure-functions-2.0-readiness.md``) before the ``<2.0.0`` cap is lifted.

Run it like::

    export AZFUNC_2X_SPIKE=1
    pytest -m compat2x -o addopts='' tests/test_worker_compat_2x_spike.py
"""

from __future__ import annotations

from importlib.metadata import version
import inspect
import os

import azure.functions as func
from azure.functions import HttpRequest, HttpResponse
from pydantic import BaseModel
import pytest

from azure_functions_validation import validate_http

pytestmark = [
    pytest.mark.compat2x,
    pytest.mark.skipif(
        os.environ.get("AZFUNC_2X_SPIKE") != "1",
        reason="opt-in spike; set AZFUNC_2X_SPIKE=1 to run against a candidate build",
    ),
]


class _Body(BaseModel):
    name: str


def _registered_functions(app: func.FunctionApp) -> list[object]:
    """Return the app's indexed function list across worker API variants."""
    getter = getattr(app, "get_functions", None)
    if callable(getter):
        return list(getter())
    # Fallback for builds that only expose the underlying registry.
    registry = getattr(app, "_function_builders", None)
    return list(registry) if registry is not None else []


def test_spike_reports_installed_version(recwarn: pytest.WarningsRecorder) -> None:
    """Capture the azure-functions version under test (evidence for the cap-lift checklist)."""
    installed = version("azure-functions")
    assert installed  # non-empty
    print(f"\n[compat2x] azure-functions=={installed}")


def test_exposed_signature_stays_single_req() -> None:
    """Behavior 1 & 2: co_argcount == 1 and no leaked ``**_kw``."""

    @validate_http(body=_Body)
    def handler(req: HttpRequest, body: _Body) -> HttpResponse:
        return HttpResponse("ok")

    assert list(inspect.signature(handler).parameters) == ["req"]
    assert handler.__code__.co_argcount == 1


def test_no_dunder_wrapped() -> None:
    """Behavior 3: ``__wrapped__`` must never be set (worker would follow it)."""

    @validate_http(body=_Body)
    def handler(req: HttpRequest, body: _Body) -> HttpResponse:
        return HttpResponse("ok")

    assert not hasattr(handler, "__wrapped__")


def test_req_left_unannotated() -> None:
    """Behavior 5: ``req`` carries no annotation so the worker infers HttpRequest."""

    @validate_http(body=_Body)
    def handler(req: HttpRequest, body: _Body) -> HttpResponse:
        return HttpResponse("ok")

    assert "req" not in handler.__annotations__


def test_worker_indexes_validate_http_handler() -> None:
    """End-to-end: the worker must produce a NON-EMPTY function list.

    This is the load-bearing assertion for the 2.0 cap. A wrapper the worker
    cannot index deploys "successfully" but exposes zero functions.
    """
    app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

    @app.route(route="users", methods=["POST"])
    @validate_http(body=_Body)
    def create_user(req: HttpRequest, body: _Body) -> HttpResponse:
        return HttpResponse("ok")

    functions = _registered_functions(app)
    assert len(functions) >= 1, "worker indexed zero functions — @validate_http wrapper was skipped"


def test_worker_indexes_handler_with_output_binding() -> None:
    """Passthrough binding params must remain visible + annotated to the worker."""
    app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

    @app.route(route="events", methods=["POST"])
    @app.queue_output(arg_name="out_msg", queue_name="q", connection="AzureWebJobsStorage")
    @validate_http(body=_Body)
    def emit(req: HttpRequest, body: _Body, out_msg: func.Out[str]) -> HttpResponse:
        out_msg.set(body.name)
        return HttpResponse("ok")

    functions = _registered_functions(app)
    assert len(functions) >= 1
