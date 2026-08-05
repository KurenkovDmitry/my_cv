"""Router административной аутентификации."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse

from app.modules.authentication.api.requests import AdminLoginRequest
from app.modules.authentication.api.responses import AdminSessionResponse
from app.modules.authentication.application.admin_access_throttle import (
    AdminThrottleExceededError,
    get_admin_access_throttle,
)
from app.modules.authentication.application.admin_session_service import get_admin_session_service

router = APIRouter(prefix="/auth", tags=["admin-auth"])


def _resolve_client_ip(request: Request) -> str:
    """Возвращает IP-адрес клиента для локального throttling административного доступа."""

    return request.client.host if request.client else "unknown"


@router.get("/session", response_model=AdminSessionResponse)
async def get_admin_session(request: Request) -> AdminSessionResponse:
    """Возвращает текущую административную сессию, если вход уже выполнен."""

    admin_session_service = get_admin_session_service()
    admin_session = admin_session_service.read_session_from_request(request)
    if admin_session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Administrative session was not found.",
        )

    return AdminSessionResponse(
        login=admin_session.login,
        expiresAt=admin_session.expires_at,
        csrfToken=admin_session.csrf_token,
    )


@router.post("/session", response_model=AdminSessionResponse)
async def create_admin_session(
    request_payload: AdminLoginRequest,
    request: Request,
) -> Response:
    """Проверяет `.env`-учётные данные и открывает защищённую cookie-сессию админки."""

    admin_access_throttle = get_admin_access_throttle()
    admin_session_service = get_admin_session_service()
    client_ip = _resolve_client_ip(request)

    try:
        admin_access_throttle.assert_login_allowed(login=request_payload.login, client_ip=client_ip)
    except AdminThrottleExceededError as error:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(error),
            headers={"Retry-After": str(error.retry_after_seconds)},
        ) from error

    if not admin_session_service.validate_credentials(
        login=request_payload.login,
        password=request_payload.password,
    ):
        retry_after_seconds = admin_access_throttle.register_login_failure(
            login=request_payload.login,
            client_ip=client_ip,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Administrative credentials are invalid.",
            headers={"Retry-After": str(retry_after_seconds)} if retry_after_seconds else None,
        )

    admin_access_throttle.register_login_success(login=request_payload.login, client_ip=client_ip)
    signed_token, admin_session = admin_session_service.create_session()

    response = JSONResponse(
        status_code=status.HTTP_200_OK,
        content=AdminSessionResponse(
            login=admin_session.login,
            expiresAt=admin_session.expires_at,
            csrfToken=admin_session.csrf_token,
        ).model_dump(by_alias=True),
    )
    response.set_cookie(
        key=admin_session_service.cookie_name,
        value=signed_token,
        **admin_session_service.build_cookie_parameters(),
    )
    return response


@router.delete("/session", status_code=status.HTTP_204_NO_CONTENT)
async def delete_admin_session() -> Response:
    """Закрывает текущую административную cookie-сессию."""

    admin_session_service = get_admin_session_service()
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(
        key=admin_session_service.cookie_name,
        path="/",
    )
    return response
