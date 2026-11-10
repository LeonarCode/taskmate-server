from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from google.auth.exceptions import TransportError

from utils.exceptions import (
    AppError, BadRequestError, EmailAlreadyExistsError, FileTooLargeError, ForbiddenError, InvalidCredentialsError,
    InvalidResetCodeError, NotFoundError, StorageError, UnauthorizedError, UserNotFoundError, UsernameAlreadyExistsError
)

# (HTTP status, "code" na babasahin ng Flutter app para malaman kung anong screen/field ang may problema)
_ERRORS = {
    InvalidCredentialsError: (401, "invalid_credentials"),
    UnauthorizedError: (401, "unauthorized"),
    UserNotFoundError: (404, "user_not_found"),
    NotFoundError: (404, "not_found"),
    BadRequestError: (400, "bad_request"),
    ForbiddenError: (403, "forbidden"),
    InvalidResetCodeError: (400, "invalid_code"),
    EmailAlreadyExistsError: (409, "email_taken"),
    UsernameAlreadyExistsError: (409, "username_taken"),
    FileTooLargeError: (413, "file_too_large"),
    StorageError: (503, "storage_unavailable"),
}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError):
        status_code, code = _ERRORS.get(type(exc), (400, "bad_request"))
        headers = {"WWW-Authenticate": "Bearer"} if status_code == 401 else None
        return JSONResponse(
            status_code=status_code,
            content={"detail": str(exc) or code, "code": code},
            headers=headers,
        )

    @app.exception_handler(TransportError)
    async def handle_google_unreachable(request: Request, exc: TransportError):
        return JSONResponse(
            status_code=503,
            content={"detail": "Cannot reach Google, try again", "code": "google_unavailable"},
        )
