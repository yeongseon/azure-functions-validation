"""azure-functions-validation package."""

from .adapter import PydanticAdapter, ValidationAdapter
from .decorator import validate_http
from .errors import ErrorFormatter, HttpError, ResponseValidationError, SerializationError

__all__ = [
    "__version__",
    "validate_http",
    "ResponseValidationError",
    "SerializationError",
    "ErrorFormatter",
    "ValidationAdapter",
    "PydanticAdapter",
    "HttpError",
]

__version__ = "0.9.0"
