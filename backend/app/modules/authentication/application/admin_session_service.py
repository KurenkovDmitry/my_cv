"""Сервис подписи и проверки административной cookie-сессии."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache

from fastapi import Request

from app.config.settings import Settings, get_settings


@dataclass(slots=True, frozen=True)
class AdminSessionSnapshot:
    """Проверенный снимок административной сессии из cookie."""

    login: str
    expires_at: str
    csrf_token: str


class AdminSessionService:
    """Создаёт, подписывает и проверяет cookie-сессию админки."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._secret_bytes = settings.admin_session_secret.encode("utf-8")

    @property
    def cookie_name(self) -> str:
        """Возвращает имя cookie административной сессии."""

        return self._settings.admin_session_cookie_name

    def validate_credentials(self, *, login: str, password: str) -> bool:
        """Сверяет логин и пароль с `.env` без прямого сравнения строк."""

        return hmac.compare_digest(login, self._settings.admin_login) and hmac.compare_digest(
            password,
            self._settings.admin_password,
        )

    def create_session(self) -> tuple[str, AdminSessionSnapshot]:
        """Создаёт подписанную cookie-сессию и возвращает её snapshot для frontend."""

        issued_at = datetime.now(timezone.utc)
        expires_at = issued_at + timedelta(seconds=self._settings.admin_session_ttl_seconds)
        payload = {
            "login": self._settings.admin_login,
            "issuedAt": self._format_datetime(issued_at),
            "expiresAt": self._format_datetime(expires_at),
            "csrfToken": secrets.token_urlsafe(24),
        }
        signed_token = self._sign_payload(payload)
        return signed_token, AdminSessionSnapshot(
            login=payload["login"],
            expires_at=payload["expiresAt"],
            csrf_token=payload["csrfToken"],
        )

    def read_session_from_request(self, request: Request) -> AdminSessionSnapshot | None:
        """Извлекает и проверяет cookie-сессию из входящего HTTP-запроса."""

        raw_token = request.cookies.get(self.cookie_name)
        if not raw_token:
            return None

        return self.verify_signed_token(raw_token)

    def verify_signed_token(self, raw_token: str) -> AdminSessionSnapshot | None:
        """Проверяет подпись, срок жизни и обязательные поля административной сессии."""

        try:
            encoded_payload, encoded_signature = raw_token.split(".", 1)
        except ValueError:
            return None

        expected_signature = self._build_signature(encoded_payload)
        if not hmac.compare_digest(encoded_signature, expected_signature):
            return None

        try:
            payload_bytes = self._urlsafe_b64decode(encoded_payload)
            payload = json.loads(payload_bytes.decode("utf-8"))
        except (ValueError, json.JSONDecodeError):
            return None

        login = payload.get("login")
        expires_at = payload.get("expiresAt")
        csrf_token = payload.get("csrfToken")
        if not all(isinstance(value, str) and value for value in (login, expires_at, csrf_token)):
            return None

        try:
            expires_at_datetime = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        except ValueError:
            return None

        if expires_at_datetime <= datetime.now(timezone.utc):
            return None

        return AdminSessionSnapshot(
            login=login,
            expires_at=expires_at,
            csrf_token=csrf_token,
        )

    def build_cookie_parameters(self) -> dict[str, object]:
        """Возвращает согласованный набор параметров cookie-сессии админки."""

        return {
            "httponly": True,
            "secure": self._settings.admin_cookie_secure,
            "samesite": self._settings.admin_session_cookie_same_site,
            "path": "/",
            "max_age": self._settings.admin_session_ttl_seconds,
        }

    def _sign_payload(self, payload: dict[str, str]) -> str:
        """Подписывает JSON-представление payload сессионной cookie."""

        payload_bytes = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        encoded_payload = self._urlsafe_b64encode(payload_bytes)
        encoded_signature = self._build_signature(encoded_payload)
        return f"{encoded_payload}.{encoded_signature}"

    def _build_signature(self, encoded_payload: str) -> str:
        """Строит HMAC-подпись payload без хранения состояния на сервере."""

        signature_bytes = hmac.new(
            self._secret_bytes,
            encoded_payload.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        return self._urlsafe_b64encode(signature_bytes)

    def _urlsafe_b64encode(self, raw_bytes: bytes) -> str:
        """Кодирует байты в компактный URL-safe base64 без символов padding."""

        return base64.urlsafe_b64encode(raw_bytes).decode("utf-8").rstrip("=")

    def _urlsafe_b64decode(self, encoded_value: str) -> bytes:
        """Декодирует компактный URL-safe base64 с восстановлением padding."""

        padding = "=" * (-len(encoded_value) % 4)
        return base64.urlsafe_b64decode(f"{encoded_value}{padding}")

    def _format_datetime(self, value: datetime) -> str:
        """Нормализует дату в ISO UTC-формат, пригодный для frontend-контракта."""

        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


@lru_cache(maxsize=1)
def get_admin_session_service() -> AdminSessionService:
    """Возвращает singleton-сервис cookie-сессии админки."""

    return AdminSessionService(get_settings())
