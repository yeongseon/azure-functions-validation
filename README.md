# Azure Functions Validation

> Part of the **Azure Functions Python DX Toolkit** — dogfood-tested by [azure-functions-cookbook-python](https://github.com/yeongseon/azure-functions-cookbook-python).

[![PyPI](https://img.shields.io/pypi/v/azure-functions-validation.svg)](https://pypi.org/project/azure-functions-validation/)
[![Downloads](https://static.pepy.tech/badge/azure-functions-validation/month)](https://pepy.tech/project/azure-functions-validation)
[![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue)](https://pypi.org/project/azure-functions-validation/)
[![CI](https://github.com/yeongseon/azure-functions-validation-python/actions/workflows/ci-test.yml/badge.svg)](https://github.com/yeongseon/azure-functions-validation-python/actions/workflows/ci-test.yml)
[![Release](https://github.com/yeongseon/azure-functions-validation-python/actions/workflows/publish-pypi.yml/badge.svg)](https://github.com/yeongseon/azure-functions-validation-python/actions/workflows/publish-pypi.yml)
[![Security Scans](https://github.com/yeongseon/azure-functions-validation-python/actions/workflows/security.yml/badge.svg)](https://github.com/yeongseon/azure-functions-validation-python/actions/workflows/security.yml)
[![codecov](https://codecov.io/gh/yeongseon/azure-functions-validation-python/branch/main/graph/badge.svg)](https://codecov.io/gh/yeongseon/azure-functions-validation-python)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://pre-commit.com/)
[![Docs](https://img.shields.io/badge/docs-gh--pages-blue)](https://yeongseon.github.io/azure-functions-validation-python/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Read this in: [한국어](README.ko.md) | [日本語](README.ja.md) | [简体中文](README.zh-CN.md)

Validation and serialization for the **Azure Functions Python v2 programming model**.

---

Part of the **Azure Functions Python DX Toolkit**
→ Bring FastAPI-like developer experience to Azure Functions

## Why this exists

Azure Functions Python v2 handlers often drift into the same repeated problems:

- **Repeated manual parsing** — every handler calls `req.get_json()`, `req.params.get()`, handles `ValueError` individually
- **Inconsistent error responses** — some handlers return 400, others 422, formats vary across the project
- **Missing response contracts** — response payloads silently diverge from the intended schema
- **No type safety** — request data flows through as untyped dicts, bugs surface only at runtime

## What it does

- **Typed validation** — body, query, path, and header parameters validated via Pydantic v2
- **Automatic error responses** — invalid requests get consistent `400`/`422` JSON error bodies
- **Response model enforcement** — mismatches raise `ResponseValidationError` (HTTP 500)
- **Decorator-first API** — `@validate_http` wraps your handler, no boilerplate needed

## How it works

`@validate_http` builds a validation pipeline once at import time, then runs it for every request:

```mermaid
flowchart LR
    Client([HTTP Client]) --> AZ[Azure Functions wrapper]
    AZ --> DEC["@validate_http"]
    DEC --> PL[pipeline]
    PL -->|parse / validate| AD[adapter]
    AD --> H[your handler]
    H --> PL2[pipeline]
    PL2 -->|validate / serialize| AD2[adapter]
    AD2 --> RESP([HttpResponse])
```

## Before / After

<details>
<summary><strong>Without</strong> this package — manual parsing, manual errors, no contracts</summary>

```python
import json
import azure.functions as func

app = func.FunctionApp()


@app.route(route="users", methods=["POST"])
def create_user(req: func.HttpRequest) -> func.HttpResponse:
    try:
        body = req.get_json()
    except ValueError:
        return func.HttpResponse(
            json.dumps({"error": "Invalid JSON"}),
            status_code=400,
            mimetype="application/json",
        )

    name = body.get("name")
    email = body.get("email")
    if not name or not isinstance(name, str):
        return func.HttpResponse(
            json.dumps({"error": "name is required"}),
            status_code=400,
            mimetype="application/json",
        )
    if not email or not isinstance(email, str):
        return func.HttpResponse(
            json.dumps({"error": "email is required"}),
            status_code=400,
            mimetype="application/json",
        )

    return func.HttpResponse(
        json.dumps({"message": f"Hello {name}", "status": "success"}),
        mimetype="application/json",
    )
```

</details>

**With** `@validate_http` — typed, consistent, contract-enforced:

```python
import azure.functions as func
from pydantic import BaseModel

from azure_functions_validation import validate_http

app = func.FunctionApp()


class CreateUserRequest(BaseModel):
    name: str
    email: str


class CreateUserResponse(BaseModel):
    message: str
    status: str = "success"


@app.route(route="users", methods=["POST"])
@validate_http(body=CreateUserRequest, response_model=CreateUserResponse)
def create_user(req: func.HttpRequest, body: CreateUserRequest) -> CreateUserResponse:
    return CreateUserResponse(message=f"Hello {body.name}")
```

> Manual parsing and validation disappear from the handler. Error formatting and response contracts — handled.

### What you get

**Valid request** → typed response:

```bash
$ curl -s -X POST http://localhost:7071/api/users \
    -H "Content-Type: application/json" \
    -d '{"name": "Alice", "email": "alice@example.com"}'
```

```json
{"message": "Hello Alice", "status": "success"}
```

> HTTP 200

**Missing required field** → automatic error response:

```bash
$ curl -s -X POST http://localhost:7071/api/users \
    -H "Content-Type: application/json" \
    -d '{"name": "Alice"}'
```

```json
{
  "detail": [
    {
      "loc": ["email"],
      "msg": "Field required",
      "type": "missing"
    }
  ]
}
```

> HTTP 422 — standardized error response, automatic

**Invalid JSON** → clear error:

```bash
$ curl -s -X POST http://localhost:7071/api/users \
    -H "Content-Type: application/json" \
    -d 'not json'
```

```json
{"detail": [{"loc": [], "msg": "Invalid JSON", "type": "value_error"}]}
```

> HTTP 400

## FastAPI comparison

| Feature | FastAPI | azure-functions-validation |
|---------|---------|---------------------------|
| Request body parsing | Built-in via type hints | `@validate_http(body=Model)` |
| Query/path/header validation | `Query()`, `Path()`, `Header()` | `@validate_http(query=Model, path=Model, headers=Model)` |
| Response model | `response_model=` | `@validate_http(response_model=Model)` |
| Validation errors | Automatic 422 | Automatic 422 with `{"detail": [...]}` |
| Error customization | Exception handlers | `ErrorFormatter` callback |

## Scope

- Azure Functions Python **v2 programming model**
- HTTP-triggered functions registered on `func.FunctionApp()`
- Pydantic v2-based request and response validation

This package does **not** target the legacy `function.json`-based v1 programming model.

## What this package does not do

API documentation ([`azure-functions-openapi`](https://github.com/yeongseon/azure-functions-openapi-python)), runtime/graph deployment ([`azure-functions-langgraph`](https://github.com/yeongseon/azure-functions-langgraph-python)), and project scaffolding ([`azure-functions-scaffold`](https://github.com/yeongseon/azure-functions-scaffold-python)) are handled by sibling packages.

## Features

- Typed body, query, path, and header validation via `@validate_http`
- Automatic 400 / 422 responses with `{"detail": [...]}` envelope
- Response model validation — mismatches raise `ResponseValidationError` (HTTP 500)
- Custom per-handler error formatting via `ErrorFormatter`

## Package names

Three names cover three different contexts:

| Context        | Name                                |
|----------------|-------------------------------------|
| GitHub repo    | `azure-functions-validation-python` |
| PyPI package   | `azure-functions-validation`        |
| Python import  | `azure_functions_validation`        |

The repository carries the `-python` suffix to mark it as the Python implementation. The PyPI package follows Python ecosystem conventions and is published without the suffix, so installation stays idiomatic: `pip install azure-functions-validation`. See the [FAQ entry](https://yeongseon.github.io/azure-functions-validation-python/faq/#why-does-the-repo-use--python-but-the-pypi-package-does-not) for the long version.

## Installation

```bash
pip install azure-functions-validation
```

Your Azure Functions app should also include:

```text
azure-functions
azure-functions-validation
```

For local development:

```bash
git clone https://github.com/yeongseon/azure-functions-validation-python.git
cd azure-functions-validation-python
pip install -e .[dev]
```

## Quick Start

```python
import azure.functions as func
from pydantic import BaseModel

from azure_functions_validation import validate_http


class CreateUserRequest(BaseModel):
    name: str
    email: str


class CreateUserResponse(BaseModel):
    message: str
    status: str = "success"


app = func.FunctionApp()


@app.route(route="users", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
@validate_http(body=CreateUserRequest, response_model=CreateUserResponse)
def create_user(req: func.HttpRequest, body: CreateUserRequest) -> CreateUserResponse:
    return CreateUserResponse(message=f"Hello {body.name}")
```

Start the Functions host locally:

```bash
func start
```

### Verify locally and on Azure

After deploying (see [docs/deployment.md](docs/deployment.md)), the same request produces the same response in both environments.

#### Local

```bash
curl -s http://localhost:7071/api/users \
  -H "Content-Type: application/json" \
  -d '{"name": "Alice", "email": "alice@example.com"}'
```

```json
{"message": "Hello Alice", "status": "success"}
```

#### Azure

```bash
curl -s "https://<your-app>.azurewebsites.net/api/users" \
  -H "Content-Type: application/json" \
  -d '{"name": "Alice", "email": "alice@example.com"}'
```

```json
{"message": "Hello Alice", "status": "success"}
```
Invalid requests return the same `400` error in both environments:

#### Local

```bash
curl -s http://localhost:7071/api/users \
  -H "Content-Type: application/json" \
  -d 'not json'
```

```json
{"detail": [{"loc": [], "msg": "Invalid JSON", "type": "value_error"}]}
```

> HTTP 400

#### Azure

```bash
curl -s "https://<your-app>.azurewebsites.net/api/users" \
  -H "Content-Type: application/json" \
  -d 'not json'
```

```json
{"detail": [{"loc": [], "msg": "Invalid JSON", "type": "value_error"}]}
```

> HTTP 400

> Manually verified by maintainers against a temporary Azure Functions deployment (koreacentral, Python 3.12, Consumption plan); response captured and URL anonymized. See [docs/deployment.md](docs/deployment.md#verification-status) for the verification status and context.

## When to use

- You have HTTP-triggered Azure Functions that accept JSON request bodies
- You want Pydantic-based validation without writing manual parsing code
- You need consistent error response formats across handlers
- You want response schema enforcement to catch contract drift

## Documentation

- Project docs live under `docs/`
- Smoke-tested examples live under `examples/`
- Product requirements: `PRD.md`
- Design principles: `DESIGN.md`

## Ecosystem

This package is part of the **Azure Functions Python DX Toolkit**.

**Design principle:** `azure-functions-validation` owns request/response validation and serialization. `azure-functions-openapi` owns API documentation and spec generation. `azure-functions-langgraph` owns LangGraph runtime exposure.

| Package | Role |
|---------|------|
| [azure-functions-openapi-python](https://github.com/yeongseon/azure-functions-openapi-python) | OpenAPI spec generation and Swagger UI |
| **azure-functions-validation-python** | Request/response validation and serialization |
| [azure-functions-db-python](https://github.com/yeongseon/azure-functions-db-python) | Database bindings for SQL, PostgreSQL, MySQL, SQLite, and Cosmos DB |
| [azure-functions-langgraph-python](https://github.com/yeongseon/azure-functions-langgraph-python) | LangGraph deployment adapter for Azure Functions |
| [azure-functions-scaffold-python](https://github.com/yeongseon/azure-functions-scaffold-python) | Project scaffolding CLI |
| [azure-functions-logging-python](https://github.com/yeongseon/azure-functions-logging-python) | Structured logging and observability |
| [azure-functions-doctor-python](https://github.com/yeongseon/azure-functions-doctor-python) | Pre-deploy diagnostic CLI |
| [azure-functions-durable-graph-python](https://github.com/yeongseon/azure-functions-durable-graph-python) | Manifest-first graph runtime with Durable Functions *(experimental)* |
| [azure-functions-knowledge-python](https://github.com/yeongseon/azure-functions-knowledge-python) | Knowledge retrieval (RAG) decorators |
| [azure-functions-cookbook-python](https://github.com/yeongseon/azure-functions-cookbook-python) | Dogfood examples — runnable recipes that exercise the full toolkit |


## For AI Coding Assistants

When integrating with LLM-powered coding assistants, provide these files for context:

- **`llms.txt`** — Concise index with quick start and API overview
- **`llms-full.txt`** — Expanded reference with full signatures and patterns

Reference the files at repository root:
- https://github.com/yeongseon/azure-functions-validation-python/blob/main/llms.txt
- https://github.com/yeongseon/azure-functions-validation-python/blob/main/llms-full.txt

## Disclaimer

This project is an independent community project and is not affiliated with,
endorsed by, or maintained by Microsoft.

Azure and Azure Functions are trademarks of Microsoft Corporation.

## License

MIT
