"""Consistent error responses: {"error": {"code", "message", "details"}}."""

from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError
from starlette.exceptions import HTTPException as StarletteHTTPException


def error_response(
    status_code: int, message: str, details: list[dict[str, Any]] | None = None
) -> JSONResponse:
    code = HTTPStatus(status_code).phrase.lower().replace(" ", "_")
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "details": details or []}},
    )


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    return error_response(exc.status_code, str(exc.detail))


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    details = [
        {"loc": list(err["loc"]), "msg": err["msg"], "type": err["type"]}
        for err in exc.errors()
    ]
    return error_response(422, "Request validation failed", details)


async def database_unavailable_handler(request: Request, exc: OperationalError) -> JSONResponse:
    # Never expose the driver message: it can contain hostnames and SQL.
    return error_response(503, "Database temporarily unavailable")


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return error_response(500, "Internal server error")


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(OperationalError, database_unavailable_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
