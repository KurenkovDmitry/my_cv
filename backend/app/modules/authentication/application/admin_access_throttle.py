"""In-memory throttling административного входа и admin API."""

from __future__ import annotations

import hashlib
import math
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from functools import lru_cache

from app.config.settings import get_settings
from app.modules.authentication.application.throttle_policy import LoginThrottlePolicy


class AdminThrottleExceededError(PermissionError):
    """Сигнализирует, что запрос временно заблокирован throttling-политикой."""

    def __init__(self, retry_after_seconds: int, message: str) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


@dataclass(slots=True)
class _CounterState:
    """Хранит состояние временного окна и lockout для одного ключа throttling."""

    timestamps: list[float] = field(default_factory=list)
    lockout_until_epoch_seconds: float = 0.0
    lockout_level: int = 0


class AdminAccessThrottle:
    """Ограничивает частоту логина и административных API-вызовов."""

    def __init__(self, throttle_policy: LoginThrottlePolicy, pepper: str) -> None:
        self._throttle_policy = throttle_policy
        self._pepper = pepper
        self._lock = threading.RLock()
        self._login_states: dict[str, _CounterState] = defaultdict(_CounterState)
        self._ip_states: dict[str, _CounterState] = defaultdict(_CounterState)
        self._api_states: dict[str, _CounterState] = defaultdict(_CounterState)

    def assert_login_allowed(self, *, login: str, client_ip: str) -> None:
        """Проверяет, что логин и IP не находятся в активном lockout."""

        with self._lock:
            current_epoch_seconds = time.time()
            self._ensure_not_locked(
                self._login_states[self._build_storage_key("login", login)],
                current_epoch_seconds,
                "Login is temporarily locked due to repeated failures.",
            )
            self._ensure_not_locked(
                self._ip_states[self._build_storage_key("ip", client_ip)],
                current_epoch_seconds,
                "This IP address is temporarily locked due to repeated failures.",
            )

    def register_login_failure(self, *, login: str, client_ip: str) -> int | None:
        """Регистрирует неуспешный вход и при необходимости включает lockout."""

        with self._lock:
            current_epoch_seconds = time.time()
            login_retry_after_seconds = self._record_failure(
                state=self._login_states[self._build_storage_key("login", login)],
                current_epoch_seconds=current_epoch_seconds,
                window_seconds=self._throttle_policy.login_window_seconds,
                limit_count=self._throttle_policy.login_limit_count,
            )
            ip_retry_after_seconds = self._record_failure(
                state=self._ip_states[self._build_storage_key("ip", client_ip)],
                current_epoch_seconds=current_epoch_seconds,
                window_seconds=self._throttle_policy.ip_window_seconds,
                limit_count=self._throttle_policy.ip_limit_count,
            )

            retry_after_candidates = [
                retry_after_seconds
                for retry_after_seconds in (login_retry_after_seconds, ip_retry_after_seconds)
                if retry_after_seconds is not None
            ]
            return max(retry_after_candidates) if retry_after_candidates else None

    def register_login_success(self, *, login: str, client_ip: str) -> None:
        """Сбрасывает временные счётчики после успешного входа."""

        with self._lock:
            self._login_states.pop(self._build_storage_key("login", login), None)
            self._ip_states.pop(self._build_storage_key("ip", client_ip), None)

    def register_admin_api_request(self, *, client_ip: str) -> None:
        """Считает административный API-вызов и блокирует при превышении лимита."""

        with self._lock:
            current_epoch_seconds = time.time()
            storage_key = self._build_storage_key("api", client_ip)
            state = self._api_states[storage_key]
            self._prune_old_timestamps(
                timestamps=state.timestamps,
                current_epoch_seconds=current_epoch_seconds,
                window_seconds=self._throttle_policy.api_window_seconds,
            )

            if len(state.timestamps) >= self._throttle_policy.api_limit_count:
                oldest_timestamp = state.timestamps[0]
                retry_after_seconds = max(
                    1,
                    math.ceil(
                        oldest_timestamp
                        + self._throttle_policy.api_window_seconds
                        - current_epoch_seconds
                    ),
                )
                raise AdminThrottleExceededError(
                    retry_after_seconds=retry_after_seconds,
                    message="Administrative API rate limit exceeded.",
                )

            state.timestamps.append(current_epoch_seconds)

    def _record_failure(
        self,
        *,
        state: _CounterState,
        current_epoch_seconds: float,
        window_seconds: int,
        limit_count: int,
    ) -> int | None:
        """Увеличивает счётчик ошибок и вычисляет длительность lockout."""

        self._prune_old_timestamps(
            timestamps=state.timestamps,
            current_epoch_seconds=current_epoch_seconds,
            window_seconds=window_seconds,
        )
        state.timestamps.append(current_epoch_seconds)

        if len(state.timestamps) < limit_count:
            return None

        state.lockout_level += 1
        lockout_seconds = min(
            self._throttle_policy.lockout_base_seconds * (2 ** (state.lockout_level - 1)),
            self._throttle_policy.lockout_max_seconds,
        )
        state.lockout_until_epoch_seconds = current_epoch_seconds + lockout_seconds
        state.timestamps.clear()
        return int(lockout_seconds)

    def _ensure_not_locked(
        self,
        state: _CounterState,
        current_epoch_seconds: float,
        message: str,
    ) -> None:
        """Проверяет активный lockout и возвращает retry-after при блокировке."""

        if state.lockout_until_epoch_seconds <= current_epoch_seconds:
            return

        retry_after_seconds = max(
            1,
            math.ceil(state.lockout_until_epoch_seconds - current_epoch_seconds),
        )
        raise AdminThrottleExceededError(retry_after_seconds=retry_after_seconds, message=message)

    def _prune_old_timestamps(
        self,
        *,
        timestamps: list[float],
        current_epoch_seconds: float,
        window_seconds: int,
    ) -> None:
        """Удаляет из окна устаревшие отметки времени."""

        threshold_epoch_seconds = current_epoch_seconds - window_seconds
        while timestamps and timestamps[0] < threshold_epoch_seconds:
            timestamps.pop(0)

    def _build_storage_key(self, namespace: str, raw_value: str) -> str:
        """Хеширует значения для безопасного хранения служебных ключей throttling."""

        return hashlib.sha256(
            f"{namespace}:{raw_value}:{self._pepper}".encode("utf-8"),
        ).hexdigest()


@lru_cache(maxsize=1)
def get_admin_access_throttle() -> AdminAccessThrottle:
    """Возвращает singleton throttling-контура для административного доступа."""

    settings = get_settings()
    return AdminAccessThrottle(
        throttle_policy=LoginThrottlePolicy.from_settings(settings),
        pepper=settings.auth_rate_limit_key_pepper,
    )
