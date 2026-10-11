"""End-user accounts, per-user search history, token revocation and the login-failure count."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from pgs_db import AccountsRepository


def test_accounts_are_unique_by_lowercase_email(session: Session) -> None:
    accounts = AccountsRepository(session)
    user = accounts.create_user(" Asha@Example.com ", password_hash="h", display_name=" Asha ")
    assert (user.email, user.display_name) == ("asha@example.com", "Asha")
    assert accounts.get_user_by_email("ASHA@example.com") is user
    with pytest.raises(IntegrityError), session.begin_nested():
        accounts.create_user("asha@example.com", password_hash="h")


def test_inactive_accounts_are_hidden(session: Session) -> None:
    accounts = AccountsRepository(session)
    user = accounts.create_user("off@example.com", password_hash="h")
    user.is_active = False
    session.flush()
    assert accounts.get_user_by_email("off@example.com") is None
    assert accounts.get_user(user.id) is None
    assert accounts.get_user(user.id, active_only=False) is user


def test_history_is_recorded_only_when_allowed(session: Session) -> None:
    accounts = AccountsRepository(session)
    user = accounts.create_user("h@example.com", password_hash="h")
    assert accounts.record_search(user.id, query_text="pokhara", result_count=3, filters={"a": 1})
    assert not accounts.record_search(user.id, query_text="   ", result_count=0)

    accounts.set_save_history(user.id, False)
    session.flush()
    assert not accounts.record_search(user.id, query_text="private", result_count=1)

    accounts.set_save_history(user.id, True)
    accounts.revoke_token("jti-x", datetime.now(UTC) + timedelta(hours=1))
    session.flush()
    assert not accounts.record_search(
        user.id, query_text="signed out", result_count=1, token_id="jti-x"
    )
    assert accounts.record_search(user.id, query_text="again", result_count=1, token_id="jti-y")

    rows = accounts.list_history(user.id)
    assert [r.query_text for r in rows] == ["again", "pokhara"]
    assert rows[1].filters == {"a": 1}


def test_history_paging_delete_and_cascade(session: Session) -> None:
    accounts = AccountsRepository(session)
    mine = accounts.create_user("m@example.com", password_hash="h")
    other = accounts.create_user("o@example.com", password_hash="h")
    for n in range(5):
        accounts.record_search(mine.id, query_text=f"q{n}", result_count=n)
    accounts.record_search(other.id, query_text="theirs", result_count=0)

    first = accounts.list_history(mine.id, limit=2)
    assert [r.query_text for r in first] == ["q4", "q3"]
    assert [
        r.query_text for r in accounts.list_history(mine.id, limit=2, before_id=first[-1].id)
    ] == ["q2", "q1"]

    assert not accounts.delete_history_item(other.id, first[0].id)  # not theirs
    assert accounts.delete_history_item(mine.id, first[0].id)
    assert accounts.clear_history(mine.id) == 4
    assert len(accounts.list_history(other.id)) == 1

    assert accounts.delete_user(other.id)
    session.flush()
    assert accounts.list_history(other.id) == []


def test_revoked_tokens_and_purge(session: Session) -> None:
    accounts = AccountsRepository(session)
    now = datetime.now(UTC)
    accounts.revoke_token("old", now - timedelta(hours=1))
    accounts.revoke_token("old", now - timedelta(hours=1))  # idempotent
    accounts.revoke_token("live", now + timedelta(hours=1))
    assert accounts.is_token_revoked("old") and not accounts.is_token_revoked("nope")
    assert accounts.purge_auth_bookkeeping(now=now)["revoked_tokens_deleted"] == 1
    assert accounts.is_token_revoked("live") and not accounts.is_token_revoked("old")


def test_login_failures_count_in_a_window_and_clear(session: Session) -> None:
    accounts = AccountsRepository(session)
    accounts.add_login_failure("ip:1.1.1.1|a", "acct:a")
    accounts.add_login_failure("ip:1.1.1.1|a", "acct:a")
    since = datetime.now(UTC) - timedelta(minutes=15)
    count, oldest = accounts.count_login_failures("ip:1.1.1.1|a", since)
    assert count == 2 and oldest is not None
    assert accounts.count_login_failures("acct:a", datetime.now(UTC) + timedelta(minutes=1)) == (
        0,
        None,
    )
    accounts.clear_login_failures("ip:1.1.1.1|a")
    assert accounts.count_login_failures("ip:1.1.1.1|a", since)[0] == 0
    assert accounts.count_login_failures("acct:a", since)[0] == 2
