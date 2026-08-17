# Deploy to Azure

This guide walks you through deploying `azure-functions-validation` examples to Azure, **step by step**.
No Azure experience required - every command is explained and copy-paste ready.

## Who this guide is for

You know Python and pip. You can run this repo locally. Now you want to deploy it to Azure so your validation endpoints run in the cloud.
This guide assumes you have **never used Azure before**.

## What you are deploying

`azure-functions-validation` provides request validation for Azure Functions using Pydantic models.
In this deployment guide, you publish three validation-focused examples:

- **`hello_validation`** - JSON body validation (`200`, `400`, `422` behaviors)
- **`profile_validation`** - path/query/header validation
- **`crud_api`** - CRUD routes with request validation and error handling

After this guide, your validation examples are live on Azure and testable with `curl`.

## Azure concepts you need for this guide

> New to Azure? Read [Choose an Azure Functions Hosting Plan](choose-a-plan.md) first. It explains Function App, hosting plans, resource groups, and storage accounts in beginner-friendly terms.

## Recommended plan for this repo

| | |
|---|---|
| **Default plan** | Flex Consumption |
| **Why** | This repo is focused on lightweight HTTP validation examples. Flex Consumption is cost-efficient for low-to-moderate traffic and scales automatically. |
| **Switch to Premium if** | You need faster cold starts or larger dependency footprints. |

## Before you start

| Requirement | How to check | Install if missing |
|---|---|---|
| Azure account | [portal.azure.com](https://portal.azure.com) | [Create free account](https://azure.microsoft.com/free/) |
| Azure CLI | `az --version` | [Install Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) |
| Azure Functions Core Tools v4 | `func --version` | [Install Core Tools](https://learn.microsoft.com/azure/azure-functions/functions-run-local#install-the-azure-functions-core-tools) |
| Python 3.10-3.13 | `python3 --version` | [python.org](https://www.python.org/downloads/) |
| Validation package installed | `python3 -m pip show azure-functions-validation` | `python3 -m pip install -U azure-functions-validation` |
| Local app works | `func start` + local `curl` checks | See [`getting-started.md`](./getting-started.md) |

> ⚠️ **Verify locally first.** If it fails locally, Azure deployment will not fix it.

## Verification status

The request/response behavior documented in this guide and in the project README was
**manually verified by the maintainers** against a temporary Azure Functions deployment
(region `koreacentral`, Python 3.12, Consumption plan). Responses were captured and their
URLs anonymized. This was a one-time manual verification, not a continuously running
environment — the temporary resources were deleted afterward (see
[Clean up resources](#clean-up-resources)). For ongoing automated verification, the
[`e2e-azure` workflow](https://github.com/yeongseon/azure-functions-validation-python/blob/main/.github/workflows/e2e-azure.yml) deploys
[`examples/e2e_app`](https://github.com/yeongseon/azure-functions-validation-python/tree/main/examples/e2e_app) to a fresh Azure instance on demand.

The portal screens below were captured against that temporary deployment. See
[`screenshot-capture.md`](./screenshot-capture.md) for how these are captured and
tracked for staleness.

![Function App Overview](assets/portal-functionapp-overview.png)

![Functions list](assets/portal-functionapp-functions.png)

---

## Read these warnings before provisioning

1. **Storage account names must be globally unique** across all of Azure. Use a name like `stmyapp` + a random suffix. Only lowercase letters and numbers, 3–24 characters.
2. **Use one region for all resources.** Mixing regions adds latency and can cause failures.
3. **Local `.env` values don't automatically appear on Azure.** You must set app settings separately via `az functionapp config appsettings set`.
4. **First deploy takes longer than expected.** Azure runs a remote build to install your Python dependencies. Wait for the "Deployment successful" message before testing.
5. **Deleting local files does not delete Azure resources.** You must explicitly delete the resource group to stop billing (see [Clean up resources](#clean-up-resources)).
6. **Validation endpoints expect JSON requests with `Content-Type: application/json`.** Missing or incorrect JSON content headers can produce `400` parsing errors before field validation runs.
7. **`400` and `422` are different failure classes.** `400 Bad Request` means malformed JSON; `422 Unprocessable Entity` means JSON is valid but does not satisfy schema constraints.

---

## Example 1: hello_validation

### Step 1 - Move to your project root

```bash
cd /path/to/your/azure-functions-validation-project
```

### Step 2 - Ensure dependencies are installed

```bash
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
```

### Step 3 - Verify locally before Azure deploy

```bash
func start
```

In another terminal:

```bash
curl -i -s -X POST "http://localhost:7071/api/hello_validation" \
  -H "Content-Type: application/json" \
  -d '{"name":"Local"}'
```

Stop the local server with `Ctrl+C`.

### Step 4 - Sign in and select your subscription

```bash
az login
AZURE_SUBSCRIPTION_ID="$(az account show --query id --output tsv)"
az account set --subscription "$AZURE_SUBSCRIPTION_ID"
```

### Step 5 - Set shell variables

```bash
RESOURCE_GROUP="rg-validation-hello"
LOCATION="koreacentral"
STORAGE_ACCOUNT="stvalidation$(date +%s | tail -c 6)"
FUNCTIONAPP_NAME="func-validation-hello"
```

To see valid Flex Consumption regions:

```bash
az functionapp list-flexconsumption-locations -o table
```

### Step 6 - Create a resource group

```bash
az group create --name "$RESOURCE_GROUP" --location "$LOCATION"
```

### Step 7 - Create a storage account

```bash
az storage account create \
  --name "$STORAGE_ACCOUNT" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --sku Standard_LRS
```

### Step 8 - Create the Function App (Flex Consumption)

```bash
az functionapp create \
  --name "$FUNCTIONAPP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --storage-account "$STORAGE_ACCOUNT" \
  --flexconsumption-location "$LOCATION" \
  --runtime python \
  --runtime-version 3.11
```

### Step 9 - Publish your code

```bash
func azure functionapp publish "$FUNCTIONAPP_NAME"
```

Expected publish output includes your validation endpoints, such as:

```text
Functions in func-validation-hello:
    hello_validation - [httpTrigger]
    get_profile - [httpTrigger]
    list_tasks - [httpTrigger]
    get_task - [httpTrigger]
    create_task - [httpTrigger]
    update_task - [httpTrigger]
    delete_task - [httpTrigger]
```

### Step 10 - Set base URL for verification

```bash
BASE_URL="https://$FUNCTIONAPP_NAME.azurewebsites.net"
```

### Step 11 - Verify `hello_validation` valid request

`POST /api/hello_validation` (valid body)

```bash
curl -i -s -X POST "$BASE_URL/api/hello_validation" \
  -H "Content-Type: application/json" \
  -d '{"name":"Azure"}'
```

Representative response:

```text
HTTP/1.1 200 OK
Content-Type: application/json

{"message":"Hello Azure"}
```

### Step 12 - Verify missing required field error

`POST /api/hello_validation` (missing required field)

```bash
curl -i -s -X POST "$BASE_URL/api/hello_validation" \
  -H "Content-Type: application/json" \
  -d '{}'
```

Representative response:

```text
HTTP/1.1 422 Unprocessable Entity
Content-Type: application/json

{"detail":[{"loc":["name"],"msg":"Field required","type":"missing"}]}
```

### Step 13 - Verify malformed JSON error

`POST /api/hello_validation` (invalid JSON)

```bash
curl -i -s -X POST "$BASE_URL/api/hello_validation" \
  -H "Content-Type: application/json" \
  -d '{"name":"Azure"'
```

Representative response:

```text
HTTP/1.1 400 Bad Request
Content-Type: application/json

{"detail":[{"loc":[],"msg":"Invalid JSON","type":"value_error"}]}
```

✅ **`hello_validation` is now running on Azure with schema validation behavior confirmed.**

---

## Example 2: profile_validation

Assume you already created Azure resources and deployed once (Example 1).

### Step 1 - Publish current code

```bash
func azure functionapp publish "$FUNCTIONAPP_NAME"
```

### Step 2 - Verify valid path/query/header request

`GET /api/users/42?verbose=true` (valid path, query, header)

```bash
curl -i -s "$BASE_URL/api/users/42?verbose=true" \
  -H "x-request-id: req-001"
```

Representative response:

```text
HTTP/1.1 200 OK
Content-Type: application/json

{"user_id":42,"view":"detailed","request_id":"req-001"}
```

### Step 3 - Verify path constraint violation

`GET /api/users/0` (path constraint violation)

```bash
curl -i -s "$BASE_URL/api/users/0?verbose=true" \
  -H "x-request-id: req-001"
```

Representative response:

```text
HTTP/1.1 422 Unprocessable Entity
Content-Type: application/json

{"detail":[{"loc":["user_id"],"msg":"Input should be greater than or equal to 1","type":"greater_than_equal"}]}
```

### Step 4 - Verify missing required header

`GET /api/users/42` (missing required header)

```bash
curl -i -s "$BASE_URL/api/users/42?verbose=true"
```

Representative response:

```text
HTTP/1.1 422 Unprocessable Entity
Content-Type: application/json

{"detail":[{"loc":["x-request-id"],"msg":"Field required","type":"missing"}]}
```

✅ **`profile_validation` request validation is verified on Azure.**

---

## Example 3: crud_api

Assume resources already exist and `BASE_URL` is set.

### Step 1 - Publish current code

```bash
func azure functionapp publish "$FUNCTIONAPP_NAME"
```

### Step 2 - Understand seeded data

This sample starts with three pre-seeded tasks and `_NEXT_ID = 4`:

Representative response:

```json
[
  {"id":1,"title":"Write docs","description":"Add examples","priority":2,"done":false},
  {"id":2,"title":"Fix bug #42","description":"","priority":5,"done":true},
  {"id":3,"title":"Add tests","description":"Cover edge cases","priority":3,"done":false}
]
```

### Step 3 - List tasks

`GET /api/tasks` (list tasks)

```bash
curl -i -s "$BASE_URL/api/tasks"
```

Representative response:

```text
HTTP/1.1 200 OK
Content-Type: application/json

[{"id":1,"title":"Write docs","description":"Add examples","priority":2,"done":false},{"id":2,"title":"Fix bug #42","description":"","priority":5,"done":true},{"id":3,"title":"Add tests","description":"Cover edge cases","priority":3,"done":false}]
```

### Step 4 - Create a task

`POST /api/tasks` (create task)

`TaskCreateRequest` constraints:
- `title`: `min_length=1`, `max_length=200`
- `description`: default `""`, `max_length=1000`
- `priority`: `ge=1`, `le=5`, default `3`

```bash
curl -i -s -X POST "$BASE_URL/api/tasks" \
  -H "Content-Type: application/json" \
  -d '{"title":"Deploy app","priority":2}'
```

Representative response:

```text
HTTP/1.1 200 OK
Content-Type: application/json

{"id":4,"title":"Deploy app","description":"","priority":2,"done":false}
```

### Step 5 - Get a task by ID

`GET /api/tasks/4` (get task)

```bash
curl -i -s "$BASE_URL/api/tasks/4"
```

Representative response:

```text
HTTP/1.1 200 OK
Content-Type: application/json

{"id":4,"title":"Deploy app","description":"","priority":2,"done":false}
```

### Step 6 - Patch a task

`PATCH /api/tasks/4` (partial update)

```bash
curl -i -s -X PATCH "$BASE_URL/api/tasks/4" \
  -H "Content-Type: application/json" \
  -d '{"done":true}'
```

Representative response:

```text
HTTP/1.1 200 OK
Content-Type: application/json

{"id":4,"title":"Deploy app","description":"","priority":2,"done":true}
```

### Step 7 - Delete a task

`DELETE /api/tasks/4` (no content)

```bash
curl -i -s -X DELETE "$BASE_URL/api/tasks/4"
```

Representative response:

```text
HTTP/1.1 204 No Content
```

### Step 8 - Verify not-found behavior

`GET /api/tasks/999` (not found)

This endpoint returns a raw `HttpResponse` with status `404` and does not use the validation adapter error formatter.

```bash
curl -i -s "$BASE_URL/api/tasks/999"
```

Representative response:

```text
HTTP/1.1 404 Not Found
Content-Type: application/json

{"detail":[{"msg":"Task not found"}]}
```

### Step 9 - Verify multiple validation errors

`POST /api/tasks` (multiple validation errors)

```bash
curl -i -s -X POST "$BASE_URL/api/tasks" \
  -H "Content-Type: application/json" \
  -d '{"title":"","priority":6}'
```

Representative response:

```text
HTTP/1.1 422 Unprocessable Entity
Content-Type: application/json

{"detail":[{"loc":["title"],"msg":"String should have at least 1 character","type":"string_too_short"},{"loc":["priority"],"msg":"Input should be less than or equal to 5","type":"less_than_equal"}]}
```

### Step 10 - Verify malformed JSON behavior

`POST /api/tasks` (invalid JSON)

```bash
curl -i -s -X POST "$BASE_URL/api/tasks" \
  -H "Content-Type: application/json" \
  -d '{"title":"Deploy app","priority":2'
```

Representative response:

```text
HTTP/1.1 400 Bad Request
Content-Type: application/json

{"detail":[{"loc":[],"msg":"Invalid JSON","type":"value_error"}]}
```

✅ **`crud_api` validation and error-path behavior is verified on Azure.**

---

## If you need a different plan

The examples above use **Flex Consumption**. If you need a different plan, only the Function App creation command changes - everything else stays the same.

See [Choose an Azure Functions Hosting Plan](choose-a-plan.md) for complete per-plan commands with copy-paste blocks.

### Premium (EP1) - for faster cold starts

Replace the `az functionapp create` step with:

```bash
# Create the Premium plan
az functionapp plan create \
  --name "${FUNCTIONAPP_NAME}-plan" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --sku EP1 \
  --is-linux

# Create the Function App on that plan
az functionapp create \
  --name "$FUNCTIONAPP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --storage-account "$STORAGE_ACCOUNT" \
  --plan "${FUNCTIONAPP_NAME}-plan" \
  --runtime python \
  --runtime-version 3.11 \
  --os-type Linux
```

### Dedicated (B1) - for fixed-cost hosting

Replace the `az functionapp create` step with:

```bash
# Create the App Service plan
az appservice plan create \
  --name "${FUNCTIONAPP_NAME}-plan" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --sku B1 \
  --is-linux

# Create the Function App on that plan
az functionapp create \
  --name "$FUNCTIONAPP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --storage-account "$STORAGE_ACCOUNT" \
  --plan "${FUNCTIONAPP_NAME}-plan" \
  --runtime python \
  --runtime-version 3.11 \
  --os-type Linux
```

---

## Troubleshooting

### Provisioning failed

| Symptom | Usually means | How to fix |
|---|---|---|
| `StorageAccountAlreadyTaken` | Storage account name is not globally unique | Use a unique suffix, for example: `stvalidation$(date +%s \| tail -c 6)` |
| `LocationNotAvailableForResourceType` | Flex Consumption is not enabled in this region | Run `az functionapp list-flexconsumption-locations -o table` and pick an available region |
| `SubscriptionNotFound` | Wrong subscription selected | Run `az account list -o table`, then `az account set --subscription "$AZURE_SUBSCRIPTION_ID"` |

### Deployment failed

| Symptom | Usually means | How to fix |
|---|---|---|
| `ModuleNotFoundError` in publish output | Missing dependency or incorrect `requirements.txt` | Ensure `requirements.txt` includes required packages and is in project root |
| Deployment hangs for several minutes | Remote build is still running | Wait and retry `func azure functionapp publish "$FUNCTIONAPP_NAME"` |
| `Can't find app with name` | Function App provisioning not complete yet | Wait 30-60 seconds and re-run publish |

### App deployed but not behaving

| Symptom | Usually means | How to fix |
|---|---|---|
| `400 Bad Request` on POST | Malformed JSON or wrong/missing `Content-Type` | Send valid JSON and include `-H "Content-Type: application/json"` |
| `422 Unprocessable Entity` | JSON parsed successfully but schema validation failed | Inspect `detail` and fix request fields/types/constraints |
| `404 Not Found` on expected route | Function route not loaded or wrong URL | Confirm publish output lists the function and use `/api/...` prefix |
| `500 Internal Server Error` | Runtime exception in your function code | Stream logs and inspect traceback |

### Logs and monitoring

```bash
# Live log stream (real-time)
func azure functionapp logstream "$FUNCTIONAPP_NAME"

# Recent request events via Application Insights
az monitor app-insights events show \
  --app "$FUNCTIONAPP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --type requests \
  --offset 1h
```

### Before opening an issue

If you're stuck, include these outputs in your issue:

```bash
# 1. Azure CLI version
az --version

# 2. Functions Core Tools version
func --version

# 3. Python version
python3 --version

# 4. Package version
python3 -m pip show azure-functions-validation

# 5. Function App status
az functionapp show --name "$FUNCTIONAPP_NAME" --resource-group "$RESOURCE_GROUP" --query "{state:state, runtimeVersion:siteConfig.linuxFxVersion}"

# 6. Recent logs
func azure functionapp logstream "$FUNCTIONAPP_NAME"
```

---

## Clean up resources

> ⚠️ **Azure resources cost money until deleted.** Clean up when finished.

Delete resource groups created in this guide:

```bash
az group delete --name "rg-validation-hello" --yes --no-wait
az group delete --name "rg-validation-profile" --yes --no-wait
az group delete --name "rg-validation-crud" --yes --no-wait
```

To verify deletion:

```bash
az group list --query "[?starts_with(name, 'rg-validation')]" -o table
```

---

## Sources

- [Azure Functions Python quickstart](https://learn.microsoft.com/azure/azure-functions/create-first-function-cli-python) - Official getting-started path
- [Azure Functions Core Tools reference](https://learn.microsoft.com/azure/azure-functions/functions-core-tools-reference) - `func` command reference
- [Azure Functions app settings](https://learn.microsoft.com/azure/azure-functions/functions-how-to-use-azure-function-app-settings) - Environment configuration
- [Azure Functions hosting plans](https://learn.microsoft.com/azure/azure-functions/functions-scale) - Plan behavior and trade-offs
- [Flex Consumption plan](https://learn.microsoft.com/azure/azure-functions/flex-consumption-plan) - Flex-specific guidance

## See Also

- [Choose an Azure Functions Hosting Plan](choose-a-plan.md) - Plan selection guide
- [`azure-functions-scaffold`](https://github.com/yeongseon/azure-functions-scaffold)
- [`azure-functions-openapi`](https://github.com/yeongseon/azure-functions-openapi)
- [`azure-functions-doctor`](https://github.com/yeongseon/azure-functions-doctor)
- [`azure-functions-logging`](https://github.com/yeongseon/azure-functions-logging)
- [`azure-functions-langgraph`](https://github.com/yeongseon/azure-functions-langgraph)
