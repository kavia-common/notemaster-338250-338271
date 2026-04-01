from fastapi import HTTPException, status
from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standard error response returned by API."""

    code: str = Field(..., description="Stable machine-readable error code.")
    message: str = Field(..., description="Human-readable error message.")
    details: dict | None = Field(
        default=None, description="Optional structured error details."
    )


class AppError(Exception):
    """Base application error with a stable error code."""

    def __init__(self, code: str, message: str, details: dict | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details


class NotFoundError(AppError):
    """Raised when a requested entity is not found."""

    pass


class ConflictError(AppError):
    """Raised when an operation conflicts with existing state (e.g., unique constraint)."""

    pass


class ValidationAppError(AppError):
    """Raised when domain validation fails."""

    pass


# PUBLIC_INTERFACE
def http_error_from_app_error(err: AppError) -> HTTPException:
    """Convert an AppError into a FastAPI HTTPException.

    Contract:
    - Inputs: AppError subclass
    - Output: HTTPException with consistent error shape in `detail`
    """
    if isinstance(err, NotFoundError):
        http_status = status.HTTP_404_NOT_FOUND
    elif isinstance(err, ConflictError):
        http_status = status.HTTP_409_CONFLICT
    elif isinstance(err, ValidationAppError):
        http_status = status.HTTP_422_UNPROCESSABLE_ENTITY
    else:
        http_status = status.HTTP_400_BAD_REQUEST

    return HTTPException(
        status_code=http_status,
        detail=ErrorResponse(code=err.code, message=err.message, details=err.details).model_dump(),
    )
