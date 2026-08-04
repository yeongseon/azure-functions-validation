# Changelog

This page documents the version history and migration paths for the `azure-functions-validation` package.

## Versioning Scheme

This project follows Semantic Versioning (semver.org). Given a version number MAJOR.MINOR.PATCH, increment the:

- MAJOR version when you make incompatible API changes
- MINOR version when you add functionality in a backward compatible manner
- PATCH version when you make backward compatible bug fixes

The changelog is generated from Conventional Commits using git-cliff. Breaking changes are explicitly listed under the "Breaking Changes" section for each release.

## Migration Guides

### Error `loc` now carries an input-source prefix (upcoming minor)

Validation error `loc` values are now prefixed with their input source, so a
body field error reports `["body", "email"]` instead of `["email"]`. This
disambiguates collisions across `body` / `query` / `path` / `headers` when the
same field name appears in more than one source.

- **Before:** `{"loc": ["email"], "msg": "Field required", "type": "missing"}`
- **After:** `{"loc": ["body", "email"], "msg": "Field required", "type": "missing"}`

If your clients parse `loc` positionally, update them to expect the leading
source segment. For a one-release migration window, pass `legacy_loc=True` to
`@validate_http` to restore the previous unprefixed shape:

```python
@validate_http(body=CreateUserRequest, legacy_loc=True)
def create_user(req, body):
    ...
```

`legacy_loc` is a temporary escape hatch and will be removed in a later release.


### Migrating from v0.3.0 to v0.5.0

The v0.5.0 release significantly reduced the public API surface to focus on the core validation decorator.

- **Global error handler removed**: `register_global_error_handler` and `GlobalErrorHandlerRegistry` are deleted. Use the `error_formatter` parameter on the `@validate_http` decorator instead for per-handler or shared formatting.
- **OpenAPI utilities removed**: `openapi.py` and `generate_422_error_schema` are removed. Use the `azure-functions-openapi` package for OpenAPI generation.
- **Contract testing removed**: `contract.py`, `@contract_test`, and `verify_contracts` were experimental and have been removed.
- **Metadata helpers removed**: `metadata.py` helpers are no longer part of the public API.
- **Exceptions merged**: `exceptions.py` is merged into `errors.py`. You should now import `ResponseValidationError` directly from the package root.

## Full Version History

### v0.6.0 (2026-03-29)

#### Features

- Normalize error paths in validation pipeline (#104)
- Support broader return types in response serialization (#102)
- Cache TypeAdapter at decoration time to avoid per-request allocation (#101)

#### Tests

- Docs-runtime sync verification tests for README examples (#110)
- Golden snapshot tests for error response shapes (400/422/500) (#109)

#### Internal

- Update README with Azure Functions Python DX Toolkit branding
- CI/CD workflow unification

### v0.5.1 (2026-03-14)

#### Changed

- Switched to `TypeAdapter` for response validation; pass through native Pydantic v2 error types
- Modernized type annotations to PEP 604 (`X | Y` instead of `Optional[X]`)

#### Fixed

- Guard against `UnicodeDecodeError` when parsing non-UTF-8 request bodies
- Harden error handling hierarchy: body → 400/422, query/path/headers → 400/422, unexpected → 500
- Sanitize 500 error responses to prevent leaking internal details

#### Added

- Test coverage for `UnicodeDecodeError`, query/path/headers error branches, and 500 sanitization
- CRUD API example (`examples/crud_api`) with 21 smoke tests covering list, get, create, update, delete
- Unified tooling: Ruff (lint + format), pre-commit hooks, standardized Makefile
- Comprehensive documentation overhaul (MkDocs site with 15+ pages)
- Translated README files (Korean, Japanese, Chinese)
- Runnable examples with smoke tests

#### Docs

- Remove stale `register_global_error_handler` and `metadata.py` references from docs
- Update architecture docs to reflect v0.5.0 module structure
- Add `request_model` shorthand example to usage guide
- Add CRUD API example documentation to mkdocs site
- Standardized nav structure and documentation quality across ecosystem

### v0.5.0 (2026-03-11)

#### Breaking Changes

- Removed `registry.py` — `register_global_error_handler()` and `GlobalErrorHandlerRegistry` deleted
- Removed `openapi.py` — `generate_422_error_schema()` deleted
- Removed `contract.py` — `@contract_test` and `verify_contracts()` deleted
- Removed `metadata.py`
- Removed `exceptions.py` — merged into `errors.py`
- Public API reduced to 3 exports: `validate_http`, `ErrorFormatter`, `ResponseValidationError`

#### Changed

- Split `decorator.py` into `decorator.py` (config/wiring), `pipeline.py` (runtime engine), `errors.py` (error types/formatting)
- Rewrote all documentation: README, PRD, DESIGN.md, api.md aligned with actual implementation
- Removed demo directory and assets
- Removed `openapi_aligned_validation` example

#### Improved

- 120 tests, 98% coverage (up from 72 tests)
- 0 lint, 0 type errors, 0 security issues
- `make check-all` passes cleanly

### v0.3.0 (2026-03-08)

#### Added

- Contract testing utilities MVP
- OpenAPI integration utilities for 422 error schemas
- Global error handler registration
- Custom error formatter hook
- Comprehensive HTTP validation for Azure Functions
- Technical design documentation

#### Fixed

- HTTP validation code quality issues
- Test failures and related code quality regressions

#### Changed

- Project metadata and repository tooling
- CI and GitHub templates
- Version management for the 0.3.0 release
- Documentation updates for PRD, process, and error handling

### v0.2.0 (2025-12-28)

#### Added

- Core validation adapter with Pydantic v2

#### Changed

- Version management for the 0.2.0 release

### v0.1.0 (2025-12-20)

#### Added

- Initial package layout and scaffolding
- Public API export
