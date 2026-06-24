from __future__ import annotations

import hashlib
import hmac
import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.login_throttle import LoginThrottle


@dataclass(frozen=True)
class LoginThrottleStatus:
    blocked: bool
    retry_after_seconds: int = 0


class LoginThrottleService:
    """Theo dõi và khóa tạm các nguồn đăng nhập thất bại."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = get_settings()

    def build_account_key(
        self,
        *,
        user_id: str | None,
        identifier: str,
    ) -> str:
        raw_value = (
            f"user:{user_id}"
            if user_id is not None
            else f"identifier:{identifier.strip().lower()}"
        )
        return self._hash_scope_value(raw_value)

    def build_ip_key(self, ip_address: str) -> str:
        return self._hash_scope_value(f"ip:{ip_address.strip() or 'unknown'}")

    def check(
        self,
        *,
        scope_type: str,
        scope_key: str,
    ) -> LoginThrottleStatus:
        record = self._get_record(scope_type, scope_key)
        if record is None:
            return LoginThrottleStatus(blocked=False)

        now = datetime.now(timezone.utc)
        blocked_until = self._as_utc(record.blocked_until)

        if blocked_until is None or blocked_until <= now:
            return LoginThrottleStatus(blocked=False)

        retry_after = max(
            1,
            math.ceil((blocked_until - now).total_seconds()),
        )
        return LoginThrottleStatus(
            blocked=True,
            retry_after_seconds=retry_after,
        )

    def cleanup_stale_records(self) -> None:
        """Xóa bộ đếm cũ để tránh bảng tăng vô hạn khi bị dò username."""

        now = datetime.now(timezone.utc)
        retention = timedelta(
            minutes=max(
                self.settings.login_attempt_window_minutes,
                self.settings.login_lockout_minutes,
            )
            * 2
        )
        cutoff = now - retention
        self.db.execute(
            delete(LoginThrottle).where(
                LoginThrottle.last_failed_at < cutoff,
                (
                    LoginThrottle.blocked_until.is_(None)
                    | (LoginThrottle.blocked_until < now)
                ),
            )
        )

    def register_failure(
        self,
        *,
        scope_type: str,
        scope_key: str,
        max_attempts: int,
    ) -> LoginThrottleStatus:
        now = datetime.now(timezone.utc)
        window = timedelta(
            minutes=self.settings.login_attempt_window_minutes
        )
        lock_duration = timedelta(
            minutes=self.settings.login_lockout_minutes
        )
        record = self._get_record(scope_type, scope_key, for_update=True)

        if record is None:
            try:
                with self.db.begin_nested():
                    record = LoginThrottle(
                        scope_type=scope_type,
                        scope_key=scope_key,
                        failed_attempts=0,
                        window_started_at=now,
                    )
                    self.db.add(record)
                    self.db.flush()
            except IntegrityError:
                # Request khác vừa tạo cùng scope. Đọc lại và khóa row đó.
                record = self._get_record(
                    scope_type,
                    scope_key,
                    for_update=True,
                )
                if record is None:
                    raise

        window_started_at = self._as_utc(record.window_started_at)
        if window_started_at is None or now - window_started_at >= window:
            record.failed_attempts = 0
            record.window_started_at = now
            record.blocked_until = None

        record.failed_attempts += 1
        record.last_failed_at = now

        if record.failed_attempts >= max_attempts:
            record.blocked_until = now + lock_duration

        self.db.flush()
        return self.check(scope_type=scope_type, scope_key=scope_key)

    def clear(
        self,
        *,
        account_key: str,
        ip_key: str,
    ) -> None:
        self.db.execute(
            delete(LoginThrottle).where(
                (
                    (LoginThrottle.scope_type == "account")
                    & (LoginThrottle.scope_key == account_key)
                )
                | (
                    (LoginThrottle.scope_type == "ip")
                    & (LoginThrottle.scope_key == ip_key)
                )
            )
        )
        self.db.flush()

    def _get_record(
        self,
        scope_type: str,
        scope_key: str,
        *,
        for_update: bool = False,
    ) -> LoginThrottle | None:
        statement = select(LoginThrottle).where(
            LoginThrottle.scope_type == scope_type,
            LoginThrottle.scope_key == scope_key,
        )
        if for_update:
            statement = statement.with_for_update()
        return self.db.scalar(statement)

    def _hash_scope_value(self, value: str) -> str:
        secret = self.settings.secret_key.get_secret_value().encode("utf-8")
        return hmac.new(
            secret,
            value.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    @staticmethod
    def _as_utc(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
