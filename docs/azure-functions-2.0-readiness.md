# azure-functions 2.0 readiness

This document is the canonical tracker for the `azure-functions>=1.17,<2.0.0`
dependency cap in `azure-functions-validation` (and, by extension, the wider
Azure Functions Python DX Toolkit). It records **why** the `<2.0.0` cap exists,
**what** would have to be verified before it is lifted, and **how** to detect a
break against a candidate `azure-functions` 2.x release.

> **Status:** cap in place. The cap-lift conditions below are **not yet
> verified** against a released `azure-functions` 2.x. See
> [`tests/test_worker_compat_2x_spike.py`](../tests/test_worker_compat_2x_spike.py)
> for the opt-in spike that verifies them once a 2.x candidate is available.

## Why the cap exists

`@validate_http` replaces the user's handler with a wrapper whose *visible*
signature is a single `req` positional plus a hidden `**_kw` catch-all. The
Azure Functions Python worker (`azure_functions_worker`, specifically
`index_function_app` / `loader.py`) does **not** call the handler through a
stable public API — it *introspects* the registered callable to index it and to
build its binding map. `WorkerCompat`
(`src/azure_functions_validation/decorator.py`) exists solely to make our
wrapper survive that introspection.

Because these are **worker-internal, introspection-based** contracts rather than
documented public APIs, a major `azure-functions` release (2.0) is the most
likely place for them to change. The cap is conservative on purpose: we would
rather block an untested major than ship a silently non-registering decorator
(the failure mode is an app that deploys "successfully" but exposes **zero**
functions).

## The five worker-internal behaviors we depend on

`WorkerCompat.apply()` shims each of these. If `azure-functions` 2.x preserves
all five (or `WorkerCompat` is updated to match 2.x), the cap can be lifted.

1. **`co_argcount` / `co_varnames` trigger-param discovery.** The worker
   inspects the code object of the registered callable to locate the HTTP
   trigger parameter. A `*args`/`**kwargs`-only wrapper has `co_argcount == 0`
   and is **silently skipped**, producing an empty function list on the deployed
   app. We declare a real `req` positional (`co_argcount == 1`).
   *See `_make_wrapper` docstring.*

2. **`__signature__` override to hide `**_kw`.** The worker reads
   `inspect.signature()` and rejects params "declared in Python but not in the
   function definition." An exposed `**_kw` raises
   `FunctionLoadError: ... {'_kw'}` at load time. We set `wrapper.__signature__`
   to expose `req` plus the passthrough binding params only.
   *See `WorkerCompat._override_signature`.*

3. **No `__wrapped__`.** `functools.update_wrapper` sets `__wrapped__ = func`,
   and some worker builds follow it back to the *original* handler, see
   `co_argcount > 1`, and fail to register. We copy only `SAFE_IDENTITY_ATTRS`
   via `copy_identity_attrs` and deliberately never set `__wrapped__`.
   *See `WorkerCompat._copy_safe_metadata`.*

4. **`get_type_hints`-based binding resolution against handler globals.** The
   worker resolves binding annotations with `get_type_hints` against the
   *handler's* module globals. Our wrapper lives in a different module, so we
   pre-resolve passthrough annotations to concrete type objects at decoration
   time (handles PEP 563 `from __future__ import annotations` string
   annotations). *See `WorkerCompat._resolve_passthrough_annotations`.*

5. **`req` left unannotated.** With `req: typing.Any` the worker raises
   `binding req has invalid non-type annotation`; with no annotation it falls
   back to `HttpRequest` type inference, which is what we want. We set
   `__annotations__` to the passthrough binding types only, never `req`.
   *See `WorkerCompat._set_annotations`.*

## Cap-lift conditions

The `<2.0.0` cap may be lifted to (e.g.) `<3.0.0` when **all** of the following
hold:

- [ ] A released (non-prerelease) `azure-functions` 2.x is available on PyPI.
- [ ] The opt-in spike (`tests/test_worker_compat_2x_spike.py`) passes against
      that 2.x with **zero** new `RuntimeWarning` / `DeprecationWarning` from
      `@validate_http`.
- [ ] A real Azure deployment (the release-certification e2e in `e2e-azure.yml`)
      registers `@validate_http` handlers and serves them — i.e. the deployed
      function list is **non-empty** and requests validate as expected.
- [ ] If any of the five behaviors changed, `WorkerCompat` is updated and its
      unit tests (`tests/test_decorator.py::TestReqContextWorkerIndexing` and
      neighbors) still lock the exposed-signature invariants.

Lifting the cap is a coordinated fleet action: the same cap lives in every DX
Toolkit library (see below), and they should move together to avoid a resolver
split in downstream apps.

## Fleet cap inventory

All toolkit libraries cap `azure-functions` below the next major. As of this
writing the lower bounds differ (historical), but the upper bound is being
normalized to `<2.0.0` everywhere:

| Package | Cap |
| --- | --- |
| azure-functions-validation | `>=1.17,<2.0.0` |
| azure-functions-openapi | `>=1.21.0,<2.0.0` |
| azure-functions-db | `>=1.22.0,<2.0.0` |
| azure-functions-langgraph | `>=1.17,<2.0.0` |
| azure-functions-knowledge | `>=1.22.0,<2.0.0` |
| azure-functions-scaffold | `>=1.23.0,<2.0.0` |
| azure-functions-durable-graph | `>=1.17,<2.0.0` (normalized from `<3`) |

> The upper bound is the load-bearing part. Lower bounds vary by the minimum
> feature each package needs and are not part of the 2.0 readiness contract.

## How to run the spike

The spike is **off by default** — it is excluded from normal CI (`-m 'not e2e
and not compat2x'`) and additionally gated on an environment variable so a bare
`pytest -m compat2x` does not accidentally reinstall `azure-functions` in a
developer's working environment:

```bash
# In a throwaway virtualenv — the spike may install a 2.x/prerelease build.
export AZFUNC_2X_SPIKE=1
pip install --pre --upgrade 'azure-functions>=2.0.0.dev0'   # or a real 2.x when released
pytest -m compat2x -o addopts='' tests/test_worker_compat_2x_spike.py
```

If the spike passes cleanly, capture the `azure-functions` version and attach it
to the tracking issue as evidence toward the cap-lift checklist above.
