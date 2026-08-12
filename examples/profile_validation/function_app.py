import azure.functions as func
from pydantic import BaseModel, ConfigDict, Field

from azure_functions_validation import validate_http


class ProfileQuery(BaseModel):
    verbose: bool = False


class ProfilePath(BaseModel):
    user_id: int = Field(ge=1)


class ProfileHeaders(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    x_request_id: str = Field(alias="x-request-id")


class ProfileResponse(BaseModel):
    user_id: int
    view: str
    request_id: str


app = func.FunctionApp()


@app.function_name(name="get_profile")
@app.route(route="users/{user_id}", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
@validate_http(
    query=ProfileQuery,
    path=ProfilePath,
    headers=ProfileHeaders,
    response_model=ProfileResponse,
)
def get_profile(
    req: func.HttpRequest,
    query: ProfileQuery,
    path: ProfilePath,
    headers: ProfileHeaders,
) -> ProfileResponse:
    view = "detailed" if query.verbose else "summary"
    return ProfileResponse(
        user_id=path.user_id,
        view=view,
        request_id=headers.x_request_id,
    )
