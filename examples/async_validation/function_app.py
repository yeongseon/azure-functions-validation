import asyncio

import azure.functions as func
from pydantic import BaseModel

from azure_functions_validation import validate_http


class AsyncGreetingRequest(BaseModel):
    name: str


class AsyncGreetingResponse(BaseModel):
    message: str
    source: str = "async"


app = func.FunctionApp()


@app.function_name(name="async_validation")
@app.route(route="async_validation", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
@validate_http(body=AsyncGreetingRequest, response_model=AsyncGreetingResponse)
async def async_validation(
    req: func.HttpRequest, body: AsyncGreetingRequest
) -> AsyncGreetingResponse:
    await asyncio.sleep(0)
    return AsyncGreetingResponse(message=f"Hello {body.name}")
