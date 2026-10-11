"""End-user accounts, their search history, and the API's auth bookkeeping.

`users` are the public site's accounts (separate from `admin_users`, which log in to the
dashboard). A user's history lives in `user_search_history`, apart from the anonymous
`search_queries` log, and goes with the account (ON DELETE CASCADE). `revoked_tokens`
holds the ids of tokens that were signed out before they expired, and `login_failures`
the failed logins the throttle counts; both are short-lived and purged by the jobs.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base, IdMixin, TimestampMixin


class User(IdMixin, TimestampMixin, Base):
    """A public-site account. Only the password hash is stored."""

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("email = lower(email)", name="email_lowercase"),
        CheckConstraint("position('@' in email) > 1", name="email_has_at"),
        CheckConstraint("length(password_hash) > 0", name="password_hash_not_empty"),
    )

    email: Mapped[str] = mapped_column(String(255), unique=True)
    display_name: Mapped[str | None] = mapped_column(String(100))
    password_hash: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    # Off: searches are not recorded in the user's history.
    save_history: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class UserSearchHistory(IdMixin, Base):
    """One search a signed-in user ran. Append-only apart from the user's own deletes."""

    __tablename__ = "user_search_history"
    __table_args__ = (
        CheckConstraint("result_count >= 0", name="result_count_non_negative"),
        Index("ix_user_search_history_user_id_searched_at", "user_id", "searched_at"),
    )

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    query_text: Mapped[str] = mapped_column(Text)
    filters: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    result_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    searched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class RevokedToken(Base):
    """A token id (`jti`) signed out before `expires_at`; rows are purged after that."""

    __tablename__ = "revoked_tokens"

    jti: Mapped[str] = mapped_column(String(64), primary_key=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class LoginFailure(IdMixin, Base):
    """One failed login attempt under a throttle key (see pgs_api.auth.throttle)."""

    __tablename__ = "login_failures"
    __table_args__ = (Index("ix_login_failures_key_failed_at", "key", "failed_at"),)

    key: Mapped[str] = mapped_column(String(400))
    failed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
