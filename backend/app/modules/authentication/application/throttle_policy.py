"""Политики throttling для административного входа."""

from dataclasses import dataclass

from app.config.settings import Settings


@dataclass(slots=True, frozen=True)
class LoginThrottlePolicy:
    """Снимок конфигурации трёхуровневого throttling."""

    login_limit_count: int
    login_window_seconds: int
    ip_limit_count: int
    ip_window_seconds: int
    api_limit_count: int
    api_window_seconds: int
    lockout_base_seconds: int
    lockout_max_seconds: int

    @classmethod
    def from_settings(cls, settings: Settings) -> "LoginThrottlePolicy":
        """Создаёт политику на основе `.env`-конфигурации."""

        return cls(
            login_limit_count=settings.auth_login_rate_limit_count,
            login_window_seconds=settings.auth_login_rate_limit_window_seconds,
            ip_limit_count=settings.auth_ip_rate_limit_count,
            ip_window_seconds=settings.auth_ip_rate_limit_window_seconds,
            api_limit_count=settings.auth_api_rate_limit_count,
            api_window_seconds=settings.auth_api_rate_limit_window_seconds,
            lockout_base_seconds=settings.auth_lockout_base_seconds,
            lockout_max_seconds=settings.auth_lockout_max_seconds,
        )

