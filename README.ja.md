# Azure Functions Validation

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

他の言語: [English](README.md) | [한국어](README.ko.md) | [简体中文](README.zh-CN.md)

**Azure Functions Python v2 プログラミング モデル**向けの validation と serialization を提供します。
このパッケージは、decorator ベースの `FunctionApp` HTTP ハンドラー向けに typed request parsing と response validation を提供します。

## Why Use It

Azure Functions Python v2 のハンドラーは、次のような問題を繰り返し抱えがちです。

- `req.get_json()` の繰り返しと手動のリクエスト解析
- 一貫しない `400` / `422` validation レスポンス
- 意図したスキーマから静かにずれていく response payload

`azure-functions-validation` は、Azure Functions のプログラミング モデルに近い decorator-first の validation レイヤーによって、これらの問題に対応します。

## Scope

- Azure Functions Python **v2 プログラミング モデル**
- `func.FunctionApp()` に登録された HTTP トリガー関数
- Pydantic v2 ベースの request / response validation

このパッケージは従来の `function.json` ベースの v1 プログラミング モデルを対象としていません。

## Features

- `@validate_http` による typed body / query / path / header validation
- `{"detail": [...]}` 形式の自動 `400` / `422` レスポンス
- response model validation。不一致時は `ResponseValidationError` を送出（HTTP 500）
- `ErrorFormatter` によるハンドラー単位の custom error formatting

## How it works

`@validate_http` はインポート時に検証パイプラインを一度構築し、リクエストごとに実行します:

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

## Package names

3 つのコンテキストで 3 つの名前を使い分けています。

| Context        | Name                                |
|----------------|-------------------------------------|
| GitHub repo    | `azure-functions-validation-python` |
| PyPI package   | `azure-functions-validation`        |
| Python import  | `azure_functions_validation`        |

リポジトリ名は Python 実装であることを示すために `-python` サフィックスを付けています。PyPI パッケージ名は Python エコシステムの慣例に従いサフィックスを付けずに公開されているため、インストールは自然に `pip install azure-functions-validation` のままです。詳細は [FAQ](https://yeongseon.github.io/azure-functions-validation-python/faq/#why-does-the-repo-use--python-but-the-pypi-package-does-not) を参照してください。

## Installation

```bash
pip install azure-functions-validation
```

Azure Functions アプリの依存関係には次も含めてください。

```text
azure-functions
azure-functions-validation
```

ローカル開発用:

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


@app.function_name(name="create_user")
@app.route(route="users", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
@validate_http(body=CreateUserRequest, response_model=CreateUserResponse)
def create_user(req: func.HttpRequest, body: CreateUserRequest) -> CreateUserResponse:
    return CreateUserResponse(message=f"Hello {body.name}")
```

## Documentation

- プロジェクトドキュメント: `docs/`
- スモークテスト済みサンプル: `examples/`
- 製品要件: `PRD.md`
- 設計原則: `DESIGN.md`

## Ecosystem

このパッケージは **Azure Functions Python DX Toolkit** の一部です。

**設計原則:** `azure-functions-validation` はリクエスト/レスポンスのバリデーションとシリアライズを担当します。 `azure-functions-openapi` は API ドキュメントとスペック生成を担当します。 `azure-functions-langgraph` は LangGraph ランタイムの公開を担当します。

| パッケージ | 役割 |
|---------|------|
| [azure-functions-openapi-python](https://github.com/yeongseon/azure-functions-openapi-python) | OpenAPI スペック生成と Swagger UI |
| **azure-functions-validation-python** | リクエスト/レスポンスのバリデーションとシリアライズ |
| [azure-functions-db-python](https://github.com/yeongseon/azure-functions-db-python) | SQLAlchemy ベースの DB 統合ヘルパー（ポーリングベースの擬似トリガー、入力/出力/クライアント注入） |
| [azure-functions-langgraph-python](https://github.com/yeongseon/azure-functions-langgraph-python) | Azure Functions 向け LangGraph デプロイアダプター |
| [azure-functions-scaffold-python](https://github.com/yeongseon/azure-functions-scaffold-python) | プロジェクトスキャフォールディング CLI |
| [azure-functions-logging-python](https://github.com/yeongseon/azure-functions-logging-python) | 構造化ロギングと可観測性 |
| [azure-functions-doctor-python](https://github.com/yeongseon/azure-functions-doctor-python) | デプロイ前診断 CLI |
| [azure-functions-durable-graph-python](https://github.com/yeongseon/azure-functions-durable-graph-python) | Durable Functions によるマニフェストファーストのグラフランタイム *(実験的)* |
| [azure-functions-knowledge-python](https://github.com/yeongseon/azure-functions-knowledge-python) | 知識検索（RAG）デコレーター |
| [azure-functions-cookbook-python](https://github.com/yeongseon/azure-functions-cookbook-python) | ドッグフード例 — ツールキット全体を活用する実行可能なレシピ |

## Disclaimer

このプロジェクトは独立したコミュニティプロジェクトであり、Microsoft と提携・承認・保守関係にはありません。

Azure および Azure Functions は Microsoft Corporation の商標です。

## License

MIT
