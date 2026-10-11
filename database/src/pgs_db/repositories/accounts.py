"""End-user accounts, their search history, token revocation and the login-failure count.

The API hashes and verifies passwords itself (`pgs_db.security`); this stores the hash.
A user's history is written by `record_search` only while the account is active, has
`save_history` on and the token has not been signed out, all decided in one statement.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import and_, delete, exists, func, insert, literal, select
from sqlalchemy.orm import Session

from ..models import LoginFailure, RevokedToken, User, UserSearchHistory


def _utcnow() -> datetime:
    return datetime.now(UTC)


def normalize_email(email: str) -> str:
    return email.strip().lower()


class AccountsRepository:
    """User, history and auth-bookkeeping access for one SQLAlchemy session."""

    def __init__(self, session: Session) -> None:
        self.session = session

    # ---------------------------------------------------------------------- users

    def create_user(
        self, email: str, *, password_hash: str, display_name: str | None = None
    ) -> User:
        """Add an account. Raises `IntegrityError` on flush if the email is taken."""
        if not password_hash:
            raise ValueError("password_hash must not be empty")
        user = User(
            email=normalize_email(email),
            password_hash=password_hash,
            display_name=(display_name or "").strip() or None,
        )
        self.session.add(user)
        self.session.flush()
        return user

    def get_user_by_email(self, email: str, *, active_only: bool = True) -> User | None:
        stmt = select(User).where(User.email == normalize_email(email))
        if active_only:
            stmt = stmt.where(User.is_active.is_(True))
        return self.session.scalar(stmt)

    def get_user(self, user_id: int, *, active_only: bool = True) -> User | None:
        user = self.session.get(User, user_id)
        if user is None or (active_only and not user.is_active):
            return None
        return user

    def record_login(self, user_id: int, *, when: datetime | None = None) -> None:
        self._require(user_id).last_login_at = when or _utcnow()

    def set_password_hash(self, user_id: int, password_hash: str) -> None:
        if not password_hash:
            raise ValueError("password_hash must not be empty")
        self._require(user_id).password_hash = password_hash

    def set_save_history(self, user_id: int, enabled: bool) -> User:
        user = self._require(user_id)
        user.save_history = enabled
        return user

    def delete_user(self, user_id: int) -> bool:
        """Erase the account and, by cascade, its history."""
        result = self.session.execute(delete(User).where(User.id == user_id))
        return bool(result.rowcount)  # type: ignore[attr-defined]

    def _require(self, user_id: int) -> User:
        user = self.session.get(User, user_id)
        if user is None:
            raise LookupError(f"user {user_id} does not exist")
        return user

    # -------------------------------------------------------------------- history

    def record_search(
        self,
        user_id: int,
        *,
        query_text: str,
        result_count: int,
        filters: dict[str, Any] | None = None,
        token_id: str | None = None,
    ) -> bool:
        """Add a history row if the user is active, saves history and the token is not revoked.

        One statement, so the search path needs no extra round trip. Empty queries (a pure
        map click) are not history. Returns whether a row was written.
        """
        if not query_text.strip():
            return False
        allowed = and_(User.id == user_id, User.is_active.is_(True), User.save_history.is_(True))
        if token_id is not None:
            allowed = and_(allowed, ~exists().where(RevokedToken.jti == token_id))
        stmt = insert(UserSearchHistory).from_select(
            ["user_id", "query_text", "filters", "result_count"],
            select(
                User.id,
                literal(query_text),
                literal(filters or None, type_=UserSearchHistory.filters.type),
                literal(result_count),
            ).where(allowed),
        )
        return bool(self.session.execute(stmt).rowcount)  # type: ignore[attr-defined]

    def list_history(
        self, user_id: int, *, limit: int = 50, before_id: int | None = None
    ) -> list[UserSearchHistory]:
        """Newest first. Pass the last id of a page as `before_id` for the next one."""
        stmt = select(UserSearchHistory).where(UserSearchHistory.user_id == user_id)
        if before_id is not None:
            stmt = stmt.where(UserSearchHistory.id < before_id)
        stmt = stmt.order_by(UserSearchHistory.id.desc()).limit(limit)
        return list(self.session.scalars(stmt).all())

    def delete_history_item(self, user_id: int, item_id: int) -> bool:
        result = self.session.execute(
            delete(UserSearchHistory).where(
                UserSearchHistory.id == item_id, UserSearchHistory.user_id == user_id
            )
        )
        return bool(result.rowcount)  # type: ignore[attr-defined]

    def clear_history(self, user_id: int) -> int:
        result = self.session.execute(
            delete(UserSearchHistory).where(UserSearchHistory.user_id == user_id)
        )
        return int(result.rowcount or 0)  # type: ignore[attr-defined]

    # ----------------------------------------------------------- token revocation

    def revoke_token(self, token_id: str, expires_at: datetime) -> None:
        """Refuse the token from now on. Idempotent."""
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        self.session.execute(
            pg_insert(RevokedToken)
            .values(jti=token_id, expires_at=expires_at)
            .on_conflict_do_nothing(index_elements=[RevokedToken.jti])
        )

    def is_token_revoked(self, token_id: str) -> bool:
        return bool(self.session.scalar(select(exists().where(RevokedToken.jti == token_id))))

    # ------------------------------------------------------------- login failures

    def count_login_failures(self, key: str, since: datetime) -> tuple[int, datetime | None]:
        """Failures under `key` since `since`, and the oldest of them."""
        count, oldest = self.session.execute(
            select(func.count(), func.min(LoginFailure.failed_at)).where(
                LoginFailure.key == key, LoginFailure.failed_at >= since
            )
        ).one()
        return int(count), oldest

    def add_login_failure(self, *keys: str) -> None:
        self.session.execute(insert(LoginFailure), [{"key": key} for key in keys])

    def clear_login_failures(self, *keys: str) -> None:
        self.session.execute(delete(LoginFailure).where(LoginFailure.key.in_(keys)))

    def purge_auth_bookkeeping(
        self, *, now: datetime | None = None, failure_window: timedelta = timedelta(days=1)
    ) -> dict[str, int]:
        """Drop revoked ids whose token has expired and failures older than the window."""
        moment = now or _utcnow()
        revoked = self.session.execute(delete(RevokedToken).where(RevokedToken.expires_at < moment))
        failures = self.session.execute(
            delete(LoginFailure).where(LoginFailure.failed_at < moment - failure_window)
        )
        return {
            "revoked_tokens_deleted": int(revoked.rowcount or 0),  # type: ignore[attr-defined]
            "login_failures_deleted": int(failures.rowcount or 0),  # type: ignore[attr-defined]
        }
