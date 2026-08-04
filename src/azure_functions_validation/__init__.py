"""azure-functions-validation package."""

from .adapter import PydanticAdapter, ValidationAdapter
from .decorator import validate_http
from .errors import ErrorFormatter, ResponseValidationError, SerializationError

__all__ = [
    "__version__",
    "validate_http",
    "ResponseValidationError",
    "SerializationError",
    "ErrorFormatter",
    "ValidationAdapter",
    "PydanticAdapter",
]

__version__ = "0.7.7"
