# AGENTS.md

## Purpose
`azure-functions-validation` provides request and response validation for Azure Functions Python v2 applications using Pydantic.

## Repository Identity
- Project: `azure-functions-validation`
- Project type: Python library
- Runtime scope: Azure Functions Python v2 programming model
- Minimum supported Python: `3.10`
- Packaging: `pyproject.toml` with Hatch

## Read First
- `README.md`
- `CONTRIBUTING.md`

## Working Rules

### Test Coverage
- Maintain test coverage at **95% or above** for committed changes and PRs.
- Run `hatch run pytest --cov --cov-report=term-missing -q` to verify before submitting changes.
- Any PR that drops coverage below 95% must include additional tests to compensate.
- Runtime code must remain compatible with Python 3.10+.
- Public APIs must be fully typed.
- `azure-functions` (>=1.17) is a required runtime dependency; import it directly. This library only runs inside an Azure Functions app, where the package is always present.
- Keep documentation examples, decorator behaviour, and tests synchronized.
- The version test in `tests/test_public_api.py` reads from `importlib.metadata` and needs no manual edits across releases.

### Documentation & Translations
- English (`README.md`) is the **canonical** source of truth for all documentation. Translated READMEs (`README.ko.md`, `README.ja.md`, `README.zh-CN.md`) are **best-effort**, community-maintained, and may lag the English source.
- Translation sync is **not** required in the same PR as an English change, and a PR is **never** blocked by translation drift. Update translations opportunistically; when you do, keep them faithful to the current English source.
- Each translated README carries a staleness banner linking back to the canonical English README. Keep that banner in place so readers always know the translation may be out of date.

## Issue Conventions

Follow these conventions when opening issues so the backlog stays consistent with sibling DX Toolkit repositories.

### Title

- Use Conventional Commit prefixes: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`, `ci:`, `build:`, `perf:`.
- Add a scope qualifier when it narrows the area: `feat(decorator):`, `docs(serializer):`, `refactor(merge):`.
- Keep the title imperative, under ~80 characters, no trailing period.
- Do **not** put `[P0]` / `[P1]` / `[P2]` (or any priority marker) in the title — priority is tracked with a `priority:p0` / `priority:p1` / `priority:p2` label.

### Body

Use the following sections, in order, omitting any that do not apply:

```
## Context
What problem this issue addresses and why now. Note the target release (e.g. vX.Y.Z) here if known.

## Acceptance Checklist
- [ ] Concrete, verifiable items.

## Out of scope
- Items intentionally excluded, with links to the issues that track them.

## References
- PRs, ADRs, sibling issues, external docs.
```

### Labels

- Apply at least one of `bug`, `enhancement`, `documentation`, `chore`.
- Apply exactly one `priority:p0` / `priority:p1` / `priority:p2` label to record priority (replaces the old `## Priority` body line).
- Add `area:*` labels when they exist in the repository.
- Use `blocker` only when the issue blocks a release.

### Umbrella issues

When splitting a large piece of work into focused issues, keep the umbrella open as a tracker that links each child issue with a checkbox; close it once every child is closed or explicitly deferred.

## Validation
- `make test`
- `make lint`
- `make typecheck`
- `make build`

## Release Process
- Version is managed via `hatch` (dynamic from `src/azure_functions_validation/__init__.py`).
- **Do NOT manually edit version strings.** Use the Makefile targets below. The public-API test reads `__version__` against `importlib.metadata.version(...)`, so no test changes are needed when bumping.

### Commands
- `make release-patch` — bump patch version, update changelog, tag, and push
- `make release-minor` — bump minor version, update changelog, tag, and push
- `make release-major` — bump major version, update changelog, tag, and push
- `make release VERSION=x.y.z` — set explicit version, update changelog, tag, and push
- `make tag-release VERSION=x.y.z` — create and push an annotated tag (used internally by release targets)

### Tiered runtime verification (what gates a release)

Release verification is layered; each tier catches a different failure class, and **every tier is a pre-publish gate** (not a post-publish check):

| Tier | Runs where | Catches |
| --- | --- | --- |
| `lib-tests` | publish-pypi.yml (per publish) | library unit regressions |
| `cookbook-smoke` | publish-pypi.yml (per publish) | downstream import/registration drift (0.21.0 class) |
| `cookbook-host-smoke` | publish-pypi.yml (per publish) | candidate wheel installs cleanly and a real `func` host + Azurite boots with it present, no cloud. NOTE: the cookbook HTTP examples do not import this package, so this is a host-boot smoke, **not** proof of this package's own runtime behavior (tracked separately) |
| `verify-azure-certification` | publish-pypi.yml (per publish) | requires a fresh, SHA+version-matched **real-Azure** certification for the exact release commit |
| Azure Release Certification (`e2e-azure.yml`) | `workflow_dispatch`, per release | cloud-only drift — deploys to real Azure, runs live e2e, records a certification artifact. **Certified per release, not per publish** (it no longer triggers on tag, which used to race the publish and could not gate it). |

### Flow
1. `make release-patch` (or `-minor` / `-major`) on `main`
2. This runs: `hatch version` → `git commit` → `make changelog` → `git commit` → `git tag` → `git push`
3. Tag push triggers the **Publish to PyPI** GitHub Actions workflow. **Verification is a pre-publish gate, not a post-publish check.** The `publish` job runs only after `build → lib-tests → cookbook-smoke → cookbook-host-smoke → verify-azure-certification` all pass, and it uploads the exact artifact that was tested (it never rebuilds). `cookbook-host-smoke` proves the candidate installs cleanly and a real Functions host boots with it present (import/dependency-resolution regressions), while `verify-azure-certification` requires a matching real-Azure certification — so a 0.21.0-class regression cannot reach PyPI. NOTE: the cookbook HTTP examples do not import this package, so decorator-level runtime behavior is exercised by `lib-tests` and (partially, at import time) `cookbook-smoke`, not by `cookbook-host-smoke`; package-native HTTP e2e is tracked separately.
4. Update `docs/changelog.md` separately if needed (different format from `CHANGELOG.md`).
5. **Failed-gate recovery (stuck tag).** A git tag is immutable and may already have been consumed, so if the gate fails do **not** move or reuse the tag. Fix forward on `main` and cut the next patch tag (`make release-patch`). The unpublished version number is simply skipped.
6. **Local pre-tag dry run (recommended before releasing).** Reproduce the automated gate locally before pushing the tag so failures surface before a version is burned:
   - Build the candidate: `make build` (produces `dist/*.whl`).
   - In [`azure-functions-cookbook-python`](https://github.com/yeongseon/azure-functions-cookbook-python): `make install`, then install the candidate over the PyPI floor with `hatch run pip install --force-reinstall --no-deps <path-to-candidate-wheel>`, confirm `importlib.metadata.version("azure-functions-validation")` equals the tag, and run `hatch run smoke`.
   - Reproduce the host-boot smoke tier: in the cookbook, with the candidate wheel installed, run `hatch run e2e tests/e2e/test_http_examples.py` (starts a real `func` host + Azurite). This confirms the candidate installs and the host boots with it present; it is the local stand-in for `cookbook-host-smoke` and must pass before tagging. NOTE: these HTTP examples do not import this package, so this is not a decorator runtime test — rely on `lib-tests` for `@validate_http` behavior.
   - Treat any new `RuntimeWarning`/`DeprecationWarning` from `@validate_http` as release-blocking — the library surfaces decorator-order and API-drift problems as warnings, so a clean run (zero validation warnings) is part of the gate.
   - If the cookbook pins a lower bound (`azure-functions-validation>=X.Y,<1`), bump it to the new minor in the same release PR so examples are tested against the version they advertise.
7. **Real-Azure certification (required once per release, before the final tag).** `cookbook-host-smoke` substitutes for Azure on every publish, but a release must still be certified against real Azure at least once. Before pushing the release tag, dispatch the **Azure Release Certification** workflow on the exact release commit and version:
   - `gh workflow run e2e-azure.yml --ref main -f ref=<release-sha> -f version=<x.y.z>`
   - The run deploys to real Azure, executes the live e2e suite, and uploads the `azure-cert` artifact (keyed by commit SHA + version).
   - `verify-azure-certification` in `publish-pypi.yml` later requires a successful, SHA+version-matched, non-stale (<14 day) certification for the release commit; without it the publish gate fails and the version stays unpublished.

## Golden Commands

Use Makefile entry points only. Do not bypass the Makefile in CI or contributor guidance.

| Purpose | Command |
| --- | --- |
| Environment setup | `make install` |
| Format code | `make format` |
| Lint | `make lint` |
| Type check | `make typecheck` |
| Tests | `make test` |
| Coverage | `make cov` |
| Full validation | `make check-all` |
| Docs build | `make docs` |
| Package build | `make build` |

## Testing Rules

- Public APIs require tests.
- Bug fixes require regression tests.
- Representative and complex examples must remain smoke-tested.
- `make check-all` is the minimum merge gate.

## Commit Rules

Use Conventional Commits:

```text
<type>: <short imperative summary>
```

Allowed types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `ci`

## Agent Rules

When using AI-assisted development:

- Prefer small, reviewable changes.
- Do not guess about behavior that can be verified.
- Keep repository structure aligned with sibling repositories.
- Update docs, examples, and tests together when behavior changes.

## Final Rule

If it is not automated, it will drift.
If it is not documented, it is not a stable rule.

## Branch Hygiene

- Merged PR branches are deleted automatically ("Automatically delete head branches" is enabled on this repository); keep that setting on.
- When merging from the CLI, always pass `--delete-branch` (e.g. `gh pr merge --squash --delete-branch`) so the head branch is removed.
- Never delete `main` or `gh-pages`, and never delete a branch that still has an open PR.
- Run `git fetch -p` periodically to prune stale local tracking refs.
