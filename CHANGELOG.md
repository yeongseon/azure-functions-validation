# Changelog

All notable changes to this project will be documented in this file.
## [0.11.2] - 2026-08-14

### ⚙️ Miscellaneous Tasks

- Stop auto-deploying docs to GitHub Pages (#335) 
- Skip test matrix for docs-only PRs via ci-required aggregator (#329) 
- *(ci)* Normalize action version-comment labels (#328) 
- Add fleet-wide workflow pin-hygiene lint (#327) 
- Automate release-gate action floor bumps via Renovate (#326) 
- *(deps)* Document azure-functions 2.0 readiness and add opt-in compat spike (#324) 
- Add release-gate workflow drift lint (#317) 
- Normalize release-gate action pins to canonical SHAs (#316) 
- Rename cookbook-local-e2e to cookbook-host-smoke and correct tier claims (#309) 
- Add local func-host e2e + real-Azure certification gates to publish (#302) 
- Bump ruff to 0.16.2 and repair pre-commit hooks (#300) 
- Gate PyPI publish on library + cookbook verification (#301) 

### 💼 Other

- Bump version to 0.11.2 

### 📚 Documentation

- Add 'Why not just use Pydantic directly?' section (#337) 
- Consolidate official documentation URL onto yeongseon.dev (#333) 
- *(i18n)* Adopt best-effort translation policy with staleness banners (#325) 
- *(metadata)* Reframe endpoint metadata doc as a convention (#323) 
- Sync docs with deprecated request_model and public adapter exports (#311) 
## [0.11.1] - 2026-08-12

### ⚙️ Miscellaneous Tasks

- Stop tracking .sisyphus orchestration artifacts 

### 🐛 Bug Fixes

- *(decorator)* Raise RuntimeError when @validate_http wraps a FunctionBuilder (#299) 

### 💼 Other

- Bump version to 0.11.1 

### 📚 Documentation

- Update changelog 
## [0.11.0] - 2026-08-12

### 💼 Other

- Bump version to 0.11.0 

### 📚 Documentation

- Update changelog 
- Add Branch Hygiene section to AGENTS.md 

### 🚀 Features

- *(decorator)* Let @validate_http compose with extra input/output bindings (#298) 
## [0.10.1] - 2026-08-11

### 💼 Other

- Bump version to 0.10.1 

### 📚 Documentation

- Update changelog 
- *(metadata)* Use absolute URL for endpoint schema link to fix strict mkdocs build 
- Backfill changelog history and require cookbook dogfood verification on release 
## [0.10.0] - 2026-08-11

### 🐛 Bug Fixes

- *(metadata)* Drop dead schema $id and remove public-contract claims (#289) 

### 💼 Other

- Bump version to 0.10.0 

### 📚 Documentation

- Update changelog 
- *(metadata)* Drop 'same release train' wording from versioning section (#296) 
- *(metadata)* Separate generic endpoint convention from validation-specific 422/Pydantic rules (#292) 

### 🚀 Features

- *(endpoint)* Document 422 validation-error contract in endpoint metadata (#286) 

### 🚜 Refactor

- *(schemas)* Drop __all__ from internal schemas subpackage (#294) 

### 🧪 Testing

- *(decorator)* Lock worker-indexing for (req, context) handlers (#287) 
## [0.9.1] - 2026-08-09

### 🐛 Bug Fixes

- *(build)* Drop src/-prefixed force-include so wheel builds from sdist 

### 💼 Other

- Bump version to 0.9.1 

### 📚 Documentation

- Update changelog 
## [0.9.0] - 2026-08-09

### ⚙️ Miscellaneous Tasks

- *(deps)* Cap azure-functions below 2.0.0 (#285) 
- *(deps)* Bump github/codeql-action/analyze from 4.37.3 to 4.37.6 (#281) 
- *(deps)* Bump github/codeql-action/init from 4.37.3 to 4.37.6 (#280) 
- *(deps)* Bump ruff from 0.16.0 to 0.16.1 (#279) 
- *(deps)* Bump azure/login from 3.0.0 to 3.0.1 (#282) 

### 💼 Other

- Bump version to 0.9.0 

### 📚 Documentation

- Update changelog 

### 🚀 Features

- *(decorator)* Warn when @validate_http is applied above @with_context (#278) 
- *(decorator)* Write endpoint namespace in _make_wrapper (#275) 
- *(metadata)* Define endpoint namespace SPEC and JSON Schema (#274) 

### 🧪 Testing

- *(metadata)* Add _metadata_helpers byte-identical drift test (#276) 
## [0.8.1] - 2026-08-06

### ⚙️ Miscellaneous Tasks

- Track issue priority via priority:* labels instead of body line (#269) 

### 🐛 Bug Fixes

- Correct wrong-order detection, 500 log attribution, and error-envelope stability 

### 💼 Other

- Bump version to 0.8.1 

### 📚 Documentation

- Update changelog 
## [0.8.0] - 2026-08-04

### Deprecate

- *(api)* Warn on request_model in favor of body (#228) 

### ⚙️ Miscellaneous Tasks

- Normalize imports and formatting after PR integration 
- *(deps)* Bump actions/stale from 10.4.0 to 11.0.0 
- *(deps)* Bump github/codeql-action/init from 4.37.1 to 4.37.3 (#248) 
- *(deps)* Bump actions/setup-node from 6.4.0 to 7.0.0 (#247) 
- *(deps)* Bump actions/checkout from 7.0.0 to 7.0.1 (#245) 
- *(deps)* Bump ruff from 0.15.22 to 0.16.0 (#244) 
- *(deps)* Bump actions/setup-python from 6.3.0 to 7.0.0 (#243) 
- *(worker)* Add nightly WorkerCompat matrix against azure-functions pre-release (#230) 

### 🐛 Bug Fixes

- *(errors)* Source-prefix error loc and correct PRD v2 syntax 
- *(decorator)* Warn instead of silently disabling on wrong order 
- *(pipeline)* Log response-validation 500s with exc_info 
- *(ci)* Replace fragile Core Tools apt install with pinned npm (#227) 

### 💼 Other

- Bump version to 0.8.0 
- Pin azure-functions>=1.17 and drop optional-import rule 

### 📚 Documentation

- Update changelog 
- *(agents)* Consolidate AGENT.md into AGENTS.md 
- Sync translated Quick Start with English README 
- Require translation sync in the same PR as English changes (Closes #241) (#242) 
- Merge redundant Features list into What it does (#240) 
- Add blank line after JSON block in Quick Start (#238) 
- Correct azure-functions-db description in ecosystem table (#236) 
- Trim Quick Start boilerplate and fold Before section (#233) (#234) 

### 🚀 Features

- *(testing)* Ship MockHttpRequest test helper 
- *(errors)* Add error_format_version stability field to error envelope 
- *(decorator)* Support status_code and public HttpError 
- *(api)* Export ValidationAdapter and PydanticAdapter 

### 🚜 Refactor

- *(adapter)* Hoist missing-body model to module constant 
- *(decorator)* Adopt canonical copy_identity_attrs helper (#231) (#232) 
- *(metadata)* Type the validation cross-package metadata contract (#229) 
## [0.7.7] - 2026-07-18

### ⚙️ Miscellaneous Tasks

- *(deps)* Bump github/codeql-action/analyze from 4.36.3 to 4.37.1 (#218) 
- *(deps)* Bump github/codeql-action/init from 4.36.3 to 4.37.1 (#216) 
- *(deps)* Bump actions/setup-python from 6.2.0 to 6.3.0 (#206) 
- *(deps)* Bump softprops/action-gh-release from 3.0.1 to 3.0.2 (#213) 
- *(deps)* Bump actions/stale from 10.3.0 to 10.4.0 (#214) 
- *(deps)* Bump ruff from 0.15.20 to 0.15.22 (#215) 
- *(deps)* Bump mypy from 2.1.0 to 2.3.0 (#217) 
- *(ci)* Pin external actions to commit SHAs and document policy (#204) 
- *(deps)* Bump github/codeql-action init+analyze to v4.36.3 (#202) 
- *(deps)* Bump actions/checkout from 6 to 7 (#196) 
- *(deps)* Bump softprops/action-gh-release from 3.0.0 to 3.0.1 (#198) 
- *(deps)* Bump ruff from 0.15.16 to 0.15.20 (#199) 
- *(deps)* Bump codecov/codecov-action from 6.0.1 to 7.0.0 (#194) 
- *(deps)* Bump mypy from 2.0.0 to 2.1.0 (#177) 
- *(deps)* Bump ruff from 0.15.12 to 0.15.16 (#189) 
- *(deps)* Bump github/codeql-action from 4.35.4 to 4.36.2 (#188) 
- *(deps)* Bump codecov/codecov-action from 6.0.0 to 6.0.1 (#182) 
- *(deps)* Bump actions/stale from 10.2.0 to 10.3.0 (#181) 

### 💼 Other

- Bump version to 0.7.7 

### 📚 Documentation

- Update changelog 
- Add e2e_app README, verify links, and substantiate Azure claim (#220) 
- Correct pipeline sequence diagram and add README flow diagram (#221) 
- Add discoverability metadata (pepy badge + llms.txt) (#226) 
- *(ci)* Document e2e-azure OIDC federated credential setup (#192) 
- Fix stale llms metadata and codecov badge (#191) 

### 🚜 Refactor

- *(pipeline)* Decouple adapter contract and harden worker-compat (#210) (#224) 

### 🧪 Testing

- Unskip error-location test and add shared conftest fixtures (#222) 
## [0.7.6] - 2026-05-23

### 🐛 Bug Fixes

- *(decorator)* Isolate wrapper __dict__ from func to prevent metadata leak 

### 💼 Other

- Bump version to 0.7.6 

### 📚 Documentation

- Update changelog 
## [0.7.5] - 2026-05-14

### ⚙️ Miscellaneous Tasks

- *(deps)* Bump mypy from 1.20.2 to 2.0.0 
- *(deps)* Bump ruff from 0.15.11 to 0.15.12 
- *(deps)* Bump github/codeql-action from 4.35.2 to 4.35.4 
- *(release)* Fix changelog template and decouple version test from literals 

### 💼 Other

- Bump version to 0.7.5 

### 📚 Documentation

- Update changelog 
- *(agents)* Remove stale manual version-test instruction 
- Fix ecosystem table names, badges, and Part of intro line 
- Mark cookbook as dogfood, fix ecosystem table description 
- Fix ecosystem table — add knowledge row, fix labels and links 

### 🧪 Testing

- Raise coverage to 95%+ and enforce via AGENTS.md and pyproject.toml 
## [0.7.4] - 2026-04-30

### 🐛 Bug Fixes

- Handle FunctionBuilder from azure-functions SDK in validate_http decorator (#173) 

### 📚 Documentation

- *(agents)* Add Issue Conventions section to AGENTS.md 
## [0.7.3] - 2026-04-26

### ⚙️ Miscellaneous Tasks

- *(deps)* Bump mypy from 1.20.1 to 1.20.2 (#166) 
- Replace stale repo-slug links and broken badge references (#171) 
- *(deps)* Bump github/codeql-action from 4.35.1 to 4.35.2 
- *(deps)* Bump mypy from 1.20.0 to 1.20.1 
- *(deps)* Bump softprops/action-gh-release from 2.6.1 to 3.0.0 
- *(deps)* Bump actions/upload-artifact from 7.0.0 to 7.0.1 
- *(deps)* Bump ruff from 0.15.10 to 0.15.11 

### 💼 Other

- Bump version to 0.7.3 and align test assertion 

### 📚 Documentation

- Update changelog 
- Explain repo (-python) vs PyPI (no suffix) vs import naming (#172) 
- Fix GitHub Pages base URL after repo rename (#170) 

### 🚜 Refactor

- Remove redundant metadata tests, consolidate into test_toolkit_metadata 
## [0.7.1] - 2026-04-10

### ⚙️ Miscellaneous Tasks

- *(deps)* Bump actions/github-script from 8.0.0 to 9.0.0 (#147) 
- *(deps)* Bump softprops/action-gh-release from 2.2.2 to 2.6.1 (#146) 
- Bump ruff from 0.15.9 to 0.15.10 (#150) 

### 🐛 Bug Fixes

- Strengthen merge regression tests to seed metadata before decoration (#158) 

### 💼 Other

- Bump version to 0.7.1 

### 📚 Documentation

- Update changelog 
- Apply Oracle review fixes to Before/After section (#152) 
- Standardize ecosystem table in README 

### 🚀 Features

- Expose ValidationMetadata for OpenAPI bridge integration (#153) 

### 🚜 Refactor

- Rename metadata attr to _azure_functions_metadata (#157) 

### 🧪 Testing

- Add dedicated toolkit metadata convention tests 
## [0.7.0] - 2026-04-07

### ⚙️ Miscellaneous Tasks

- Add automatic GitHub Release creation on tag push (#112) 
- *(deps)* Bump github/codeql-action from 4.34.1 to 4.35.1 (#113) 
- *(deps)* Bump mypy from 1.19.1 to 1.20.0 (#114) 
- *(deps)* Bump ruff from 0.15.8 to 0.15.9 (#115) 

### 🐛 Bug Fixes

- Align terminology with Oracle-reviewed openapi PR #146 
- Apply Oracle terminology — 'runtime exposure' for cross-repo consistency 
- Switch Mermaid fence format to fence_div_format for rendering 
- Add type annotation to caplog parameter for mypy strict mode (#120) 
- Handle custom error formatter exceptions safely (#119) 
- Replace internal missing-body validation construction (#118) 

### 💼 Other

- Bump version to 0.7.0 

### 📚 Documentation

- Update changelog 
- Document ValidationMetadata and get_validation_metadata public API 
- Add llms.txt for LLM-friendly documentation (#141) (#142) 
- Normalize storage naming rule to use en-dash (3–24) 
- Rewrite deployment guide for developer-friendly Azure Functions experience 
- Fix invalid-JSON status code (422→400) and add Azure verification note (#137) 
- Add Azure-verified sample output to README (#136) 
- Add deployment guide with validation examples (#134) 
- Align ecosystem positioning with toolkit restructuring 
- Pin Mermaid JS version and add site_url 
- Standardize architecture.md sections and fix factual accuracy (#127) 
- Add architecture diagram, MS Learn sources, and cross-repo See Also links (#125) 
- Add release process to AGENTS.md 

### 🚀 Features

- Write convention-based _azure_functions_toolkit_metadata for toolkit interop 
- Expose ValidationMetadata for OpenAPI bridge integration (#143) 

### 🧪 Testing

- Update version assertion to 0.7.0 for upcoming release 
## [0.6.0] - 2026-03-29

### ⚙️ Miscellaneous Tasks

- Release v0.6.0 
- *(deps)* Bump github/codeql-action from 4.33.0 to 4.34.1 (#96) 
- *(deps)* Bump ruff from 0.15.7 to 0.15.8 (#95) 
- *(deps)* Bump anchore/sbom-action from 0.23.1 to 0.24.0 (#94) 
- *(deps)* Bump codecov/codecov-action from 5.5.3 to 6.0.0 (#93) 
- Use standard pypi environment name for Trusted Publisher 
- Rename publish environment from production to release 
- Rename release.yml to publish-pypi.yml 

### 📚 Documentation

- Update README with Azure Functions Python DX Toolkit branding 

### 🚀 Features

- Normalize error paths in validation pipeline (#104) 
- Support broader return types in response serialization (#102) 
- Cache TypeAdapter at decoration time to avoid per-request allocation (#101) 

### 🧪 Testing

- Add docs-runtime sync verification for README examples (#110) 
- Add golden snapshot tests for error response shapes (400/422/500) (#109) 
## [0.5.7] - 2026-03-21

### ⚙️ Miscellaneous Tasks

- Release v0.5.7 
- Remove nonexistent docs/agent-playbook.md ref from AGENTS.md, standardize .gitignore (#88) 
- Fix ruff version, coverage threshold, pre-commit refs, mkdocstrings version, add CodeQL and codecov (#87) 
- *(deps)* Bump azure/login from 2.3.0 to 3.0.0 (#83) 
- *(deps)* Bump github/codeql-action from 4.32.6 to 4.33.0 (#84) 
- *(deps)* Bump codecov/codecov-action from 5.5.2 to 5.5.3 (#85) 
- *(deps)* Bump ruff from 0.15.6 to 0.15.7 (#86) 
- *(deps)* Bump anchore/sbom-action from 0.23.0 to 0.23.1 (#78) 
- *(deps)* Update mkdocstrings[python] requirement from <1.0 to <2.0 (#80) 
- *(deps)* Bump ruff from 0.15.5 to 0.15.6 (#81) 

### 🐛 Bug Fixes

- Clear wrapper __annotations__ to prevent FunctionLoadError on Azure 
- *(e2e)* Build local wheel and pre-install with --no-build to avoid PyPI stale version 
- Set __signature__ on wrapper to hide **_kw from Azure Functions worker 
- *(e2e)* Add [DIAG] module-level logging to diagnose empty _function_builders on Azure 
- *(e2e)* Switch to remote build deployment to fix azure namespace package conflict 
- *(e2e)* Switch to local build deployment and add Application Insights diagnostics 
- *(ci)* Add az webapp log to capture worker errors in e2e workflow 
- *(e2e)* Remove 'from __future__ import annotations' from function_app.py 

### 📚 Documentation

- Add mermaid diagrams to architecture and README 
- Add mermaid support to mkdocs configuration 
## [0.5.6] - 2026-03-17

### 🐛 Bug Fixes

- Remove __annotations__ copy in _make_wrapper to prevent NameError in Azure Functions worker 
- *(ci)* Add environment: azure-e2e to e2e workflow for OIDC tag support 
## [0.5.5] - 2026-03-17

### 🐛 Bug Fixes

- Replace exec()-based wrapper with closure to fix Azure Functions registration 
- *(e2e)* Use PydanticAdapter directly in e2e_app to avoid decorator Azure registration issue 
## [0.5.4] - 2026-03-16

### ⚙️ Miscellaneous Tasks

- Trigger e2e only on release tag push (v*) 

### 🐛 Bug Fixes

- Remove __wrapped__ from validate_http wrapper to fix Azure Functions worker registration 
- *(e2e)* Pin pydantic<2.12 in e2e_app, improve log capture in workflow 

### 📚 Documentation

- Add real Azure e2e test section to testing.md and CHANGELOG 

### 🚀 Features

- *(e2e)* Use @validate_http decorator directly in e2e app, bump to v0.5.3 
## [0.5.3] - 2026-03-16

### ⚙️ Miscellaneous Tasks

- Upgrade GitHub Actions to Node.js 24 compatible versions 
- Probe5 — direct adapter API, no @validate_http decorator 
- Probe4 — full function_app with @validate_http 
- Probe3 — pydantic models only, no decorator apply 
- Import probe — report azure_functions_validation import error via health 
- Minimal probe — health only, no library import 
- *(e2e)* Add host/status + Kudu logstream diagnostics, enable AppInsights 
- *(e2e)* Minimal probe build to isolate infra vs library import failure 
- Enforce coverage fail_under = 97 
- Add keywords to pyproject.toml 
- Add AGENTS.md, Typing classifier, test_public_api, Dev Status 4-Beta, .venv-review in .gitignore 

### 🐛 Bug Fixes

- Restore correct co_argcount in @validate_http wrapper for Azure Functions worker 
- *(e2e)* Add import error capture for diagnostics, revert to --build remote 
- *(e2e)* Disable SCM_DO_BUILD_DURING_DEPLOYMENT before --no-build publish 
- *(e2e)* Switch to local build to eliminate oryx pydantic resolution 
- Restore full validation e2e app with pydantic<2.10 pin 
- Add log capture step and startup log to diagnose worker initialization failure 
- Pin pydantic<2.10 in e2e_app to avoid typing-inspection incompatibility on Azure Functions host 
- Add restart step after deploy to force function discovery on Consumption plan 
- Add post-deploy wait and status probe for Consumption cold-start diagnosis 
- Extend warmup timeout to 300s for Consumption plan cold starts 
- Fix e2e warmup to wait for 200 instead of non-5xx 
- Add --no-cov and pytest-html artifact to e2e workflow 

### 🚀 Features

- *(e2e)* Full function_app without try/except guard 
- Add real Azure e2e tests and CI workflow 
## [0.5.2] - 2026-03-15

### ⚙️ Miscellaneous Tasks

- Add production environment to release.yml for trusted publishing 

### 💼 Other

- Bump version to 0.5.2 

### 📚 Documentation

- Remove openapi pairing references from documentation 
- Remove openapi integration sections from DESIGN.md and PRD.md 

### 🚀 Features

- Add py.typed marker for PEP 561 compliance (#82) 
## [0.5.1] - 2026-03-14

### ⚙️ Miscellaneous Tasks

- Update pre-commit hook versions and unify forbid-korean targets 

### 🎨 Styling

- Unify tooling — remove black, standardize pre-commit and Makefile 
- Modernize type annotations to PEP 604 

### 🐛 Bug Fixes

- Harden error handling and sanitize server error responses 
- Use absolute GitHub URL for CODE_OF_CONDUCT link in contributing docs 

### 💼 Other

- Bump version to 0.5.1 

### 📚 Documentation

- Overhaul documentation to production quality 
- Sync translated READMEs (ko, ja, zh-CN) with English 
- Unify README — Title Case H1, manual Python badge, add Ecosystem, reorder sections 
- Add example-first design section to PRD 
- Fix stale tool versions in contributing.md and development.md 
- Fix stale test counts, tool versions, and missing CRUD entry across docs 
- Align documentation with v0.5.0 API and add CRUD example page 
- Add CRUD API example with smoke tests 
- Expand example pages and installation with working code 
- Elevate validation documentation to production quality 
- Add localized README translations 
- Replace openapi_aligned_validation reference with custom_error_handler in index 
- *(examples)* Replace stale openapi_aligned_validation with custom_error_handler 
- *(readme)* Move disclaimer before license section 
- *(readme)* Add Microsoft trademark disclaimer 

### 🚜 Refactor

- Use TypeAdapter and pass through native Pydantic error types 

### 🧪 Testing

- Cover UnicodeDecodeError, error hierarchy branches, and 500 sanitization 
## [0.5.0] - 2026-03-11

### ⚙️ Miscellaneous Tasks

- Remove invalid secrets reference from workflow if condition 
- Do not fail build on codecov upload errors 
- Restore validation lint and test hygiene 
- Add pytest-anyio to dev deps and include test app in pythonpath 
- Use trusted publishing for validation releases 
- Ci: 
- Support manual validation releases 
- Chore: 
- Remove validation scratch files 
- Pin validation docs dependencies 
- Align validation docs dependencies 
- Align validation maintenance workflows 
- Apply remaining dependabot updates 
- *(deps)* Bump ruff from 0.14.14 to 0.15.5 
- *(deps)* Bump black from 26.1.0 to 26.3.0 
- Align tooling and repository maintenance 
- Align workflows and tooling 

### 🐛 Bug Fixes

- Correct _map_error_type inversion for greater_than/less_than mappings 
- Align tests with updated openapi examples and registry specificity 
- Remove unused imports in test files 
- Prevent serialize() infinite recursion and fix TypeError message 
- Handle generic response models in validate_http 
- Prevent caller kwargs from overwriting validated inputs 
- Resolve HttpRequest from keyword arguments 
- Raise ResponseValidationError and fix adapter type hints and error mapping 
- Improve error handler registry to prefer most specific exception type 
- Remove no-op try/except wrapper from parse_inputs 
- Support async validation handlers without asyncio.run 
- Guard against request param name conflicting with injected inputs 
- Relax HttpRequest handler signature constraints 
- Allow dependabot branch names 

### 📚 Documentation

- *(changelog)* Add v0.5.0 release notes 
- *(readme)* Align Features and Why-Use-It with public API (validate_http, ErrorFormatter, ResponseValidationError) 
- *(readme)* Replace OpenAPI-scoped pain point with validation-scoped wording 
- Update api.md and DESIGN.md for v0.5.0 module structure 
- *(prd)* Rewrite PRD for v0.4 scope 
- Update openapi example with bridge helper usage 
- Document package ownership boundary and expand API reference 
- Expand focused validation example docs 
- Docs: 
- Docs: 
- Expand validation example coverage 
- Strengthen validation README problem framing 
- Capture validation improvement priorities 
- Docs: 
- Standardize repository planning documents 
- Slow down validation demo and add final snapshot 
- Fix validation demo rendering workflow 
- Use workspace-based validation demo setup 
- Refine validation demo output 
- Simplify validation demo scenario 
- Add README validation demo 
- Document validation example policy 
- Position validation for Azure Functions Python v2 
- Refresh documentation structure 

### 🚀 Features

- Reduce public API to validation core for v0.4.0 
- Add OpenAPI bridge helper and multi-source validation support 
- Define validation contract metadata helpers 

### 🚜 Refactor

- Split decorator into pipeline/errors modules for v0.5.0 
- Align OpenAPI helpers with validation metadata 
- Use validated body params and remove sys.path hacks in tests 
- Remove dead code and expand openapi validation examples 
- Reuse parsed request inputs in validation decorator 

### 🧪 Testing

- Achieve 97% coverage with comprehensive test additions 
- Add complex validation example coverage 
- Raise validation coverage for adapter paths 
- Cover validation example app 
- Improve contract coverage and logging behavior 
## [0.3.0] - 2026-01-31

### ⚙️ Miscellaneous Tasks

- Bump version to 0.3.0 and complete v0.3 features 
- Bump version to 0.2.0 and establish version management 
- Update package version to 0.1.0 and export public API (#27) 
- Update condition for codecov upload 
- *(deps)* Bump ruff from 0.14.13 to 0.14.14 
- Add GitHub templates (#12) 
- Add CI workflow (#9) 
- Add repo tooling (#8) 
- Scaffold package layout (#7) 

### 🐛 Bug Fixes

- Resolve code quality issues in HTTP validation implementation 

### 📚 Documentation

- Add process improvement documentation 
- Update PRD and TDD based on feedback 
- Add project metadata (#10) 
- Clarify PRD injection rules 
- Update PRD error handling 
- Add initial PRD 

### 🚀 Features

- Add contract testing utilities MVP 
- Add OpenAPI integration utilities for 422 error schemas 
- Add global error handler registration 
- Add custom error formatter hook 
- Implement comprehensive HTTP validation for Azure Functions 
- Implement core validation adapter with Pydantic v2 
- *(docs)* Create Technical Design Document 

### 🚜 Refactor

- Move json import to top level per code review 

### 🧪 Testing

- Fix failing tests and improve code quality 
- Add scaffolding (#11) 
<!-- generated by git-cliff -->
