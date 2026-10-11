"""user accounts, per-user search history, token revocation and login throttle tables

`users` are the public site's accounts; `user_search_history` is each user's own search
history (kept apart from the anonymous `search_queries`). `revoked_tokens` lets a sign-out
end a token before it expires and `login_failures` moves the login throttle out of process
memory. Grants: pgs_api reads and writes them, pgs_jobs only purges the last two.

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-10-11 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from pgs_db import grants


# revision identifiers, used by Alembic.
revision: str = 'c9d0e1f2a3b4'
down_revision: Union[str, Sequence[str], None] = 'b8c9d0e1f2a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NOW = sa.text('now()')


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('display_name', sa.String(length=100), nullable=True),
        sa.Column('password_hash', sa.Text(), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('save_history', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.CheckConstraint('email = lower(email)', name=op.f('ck_users_email_lowercase')),
        sa.CheckConstraint("position('@' in email) > 1", name=op.f('ck_users_email_has_at')),
        sa.CheckConstraint('length(password_hash) > 0', name=op.f('ck_users_password_hash_not_empty')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_users')),
        sa.UniqueConstraint('email', name=op.f('uq_users_email')),
    )
    op.execute(
        'CREATE TRIGGER trg_users_updated_at BEFORE UPDATE ON users '
        'FOR EACH ROW EXECUTE FUNCTION pgs_set_updated_at()'
    )

    op.create_table(
        'user_search_history',
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('query_text', sa.Text(), nullable=False),
        sa.Column('filters', sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column('result_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('searched_at', sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.CheckConstraint('result_count >= 0', name=op.f('ck_user_search_history_result_count_non_negative')),
        sa.ForeignKeyConstraint(
            ['user_id'], ['users.id'],
            name=op.f('fk_user_search_history_user_id_users'), ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_user_search_history')),
    )
    op.create_index(
        op.f('ix_user_search_history_user_id_searched_at'),
        'user_search_history', ['user_id', 'searched_at'], unique=False,
    )

    op.create_table(
        'revoked_tokens',
        sa.Column('jti', sa.String(length=64), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('jti', name=op.f('pk_revoked_tokens')),
    )
    op.create_index(op.f('ix_revoked_tokens_expires_at'), 'revoked_tokens', ['expires_at'], unique=False)

    op.create_table(
        'login_failures',
        sa.Column('key', sa.String(length=400), nullable=False),
        sa.Column('failed_at', sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_login_failures')),
    )
    op.create_index(
        op.f('ix_login_failures_key_failed_at'), 'login_failures', ['key', 'failed_at'], unique=False
    )

    grants.apply(op.execute)


def downgrade() -> None:
    for table in ('login_failures', 'revoked_tokens', 'user_search_history', 'users'):
        op.drop_table(table)
