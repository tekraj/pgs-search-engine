from __future__ import annotations

from datetime import UTC, datetime

from pgs_api.auth.tokens import ADMIN_AUDIENCE, USER_AUDIENCE, TokenCodec
from pgs_api.db.database import HistoryItem, SearchLogEntry
from pgs_db.security import hash_password

from .conftest import AUTH_SECRET, PASSWORD, Harness

EMAIL = "Asha@Example.com"


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _register(harness: Harness, email: str = EMAIL, password: str = PASSWORD) -> dict[str, object]:
    response = harness.client.post(
        "/api/v1/account/register",
        json={"email": email, "password": password, "display_name": "Asha"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_register_signs_in_and_stores_a_hash(harness: Harness) -> None:
    body = _register(harness)

    assert body["user"] == {
        "email": "asha@example.com",
        "display_name": "Asha",
        "save_history": True,
    }
    account = harness.db.find_user("asha@example.com")
    assert account is not None and account.password_hash != PASSWORD
    claims = TokenCodec(AUTH_SECRET, 60).verify(str(body["access_token"]), USER_AUDIENCE)
    assert claims.user_id == account.id and claims.role == "USER"
    me = harness.client.get("/api/v1/account/me", headers=_bearer(str(body["access_token"])))
    assert me.status_code == 200 and me.json()["email"] == "asha@example.com"


def test_register_rejects_duplicates_bad_emails_and_short_passwords(harness: Harness) -> None:
    _register(harness)
    post = harness.client.post
    assert (
        post(
            "/api/v1/account/register", json={"email": "ASHA@example.com", "password": PASSWORD}
        ).status_code
        == 409
    )
    assert (
        post(
            "/api/v1/account/register", json={"email": "not-an-email", "password": PASSWORD}
        ).status_code
        == 400
    )
    assert (
        post(
            "/api/v1/account/register", json={"email": "b@example.com", "password": "short"}
        ).status_code
        == 400
    )


def test_login_succeeds_and_fails_without_revealing_which(harness: Harness) -> None:
    _register(harness)
    ok = harness.client.post("/api/v1/account/login", json={"email": EMAIL, "password": PASSWORD})
    assert ok.status_code == 200 and ok.json()["user"]["email"] == "asha@example.com"
    wrong = harness.client.post(
        "/api/v1/account/login", json={"email": EMAIL, "password": "wrong password!"}
    )
    unknown = harness.client.post(
        "/api/v1/account/login", json={"email": "no@one.com", "password": "wrong password!"}
    )
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


def test_login_is_throttled_per_address_only(harness: Harness) -> None:
    _register(harness)
    bad = {"email": EMAIL, "password": "wrong password!"}
    for _ in range(5):
        assert (
            harness.client.post(
                "/api/v1/account/login", json=bad, headers={"X-Real-IP": "1.1.1.1"}
            ).status_code
            == 401
        )
    blocked = harness.client.post(
        "/api/v1/account/login",
        json={"email": EMAIL, "password": PASSWORD},
        headers={"X-Real-IP": "1.1.1.1"},
    )
    assert blocked.status_code == 429 and int(blocked.headers["Retry-After"]) > 0
    other = harness.client.post(
        "/api/v1/account/login",
        json={"email": EMAIL, "password": PASSWORD},
        headers={"X-Real-IP": "2.2.2.2"},
    )
    assert other.status_code == 200


def test_logout_revokes_the_token(harness: Harness) -> None:
    token = str(_register(harness)["access_token"])
    assert harness.client.post("/api/v1/account/logout", headers=_bearer(token)).status_code == 204
    assert harness.client.get("/api/v1/account/me", headers=_bearer(token)).status_code == 401


def test_admin_and_user_tokens_are_not_interchangeable(harness: Harness) -> None:
    user_token = str(_register(harness)["access_token"])
    assert (
        harness.client.get("/api/v1/admin/summary", headers=_bearer(user_token)).status_code == 401
    )
    assert harness.client.get("/api/v1/auth/me", headers=_bearer(user_token)).status_code == 401
    admin_token = TokenCodec(AUTH_SECRET, 600).issue(
        subject="ops", user_id=1, role="AUDITOR", audience=ADMIN_AUDIENCE
    )
    assert harness.client.get("/api/v1/account/me", headers=_bearer(admin_token)).status_code == 401


def test_search_with_a_user_token_carries_the_user_to_the_log(harness: Harness) -> None:
    token = str(_register(harness)["access_token"])
    harness.client.get("/api/v1/search", params={"q": "pokhara"}, headers=_bearer(token))
    anonymous = harness.client.get("/api/v1/search", params={"q": "kathmandu"})
    assert anonymous.status_code == 200
    first, second = harness.search_log.entries
    assert isinstance(first, SearchLogEntry) and first.user_id is not None and first.token_id
    assert second.user_id is None
    # A bad token is not an error on a public route: the search just is not attributed.
    bad = harness.client.get("/api/v1/search", params={"q": "x"}, headers=_bearer("junk"))
    assert bad.status_code == 200 and harness.search_log.entries[-1].user_id is None


def test_history_list_delete_clear_and_isolation(harness: Harness) -> None:
    token = str(_register(harness)["access_token"])
    other = str(_register(harness, "other@example.com")["access_token"])
    uid = harness.db.find_user("asha@example.com").id  # type: ignore[union-attr]
    now = datetime(2026, 10, 11, tzinfo=UTC)
    for n in range(1, 4):
        harness.db.history.append((uid, HistoryItem(n, f"q{n}", {}, n, now)))
    harness.db.history.append((999, HistoryItem(4, "private", {}, 0, now)))

    page = harness.client.get(
        "/api/v1/account/history", params={"limit": 2}, headers=_bearer(token)
    ).json()
    assert [i["query"] for i in page["items"]] == ["q3", "q2"] and page["next_before"] == 2
    rest = harness.client.get(
        "/api/v1/account/history", params={"before": 2}, headers=_bearer(token)
    ).json()
    assert [i["query"] for i in rest["items"]] == ["q1"] and rest["next_before"] is None

    assert (
        harness.client.delete("/api/v1/account/history/1", headers=_bearer(other)).status_code
        == 404
    )
    assert (
        harness.client.delete("/api/v1/account/history/1", headers=_bearer(token)).status_code
        == 204
    )
    assert harness.client.delete("/api/v1/account/history", headers=_bearer(token)).json() == {
        "deleted": 2
    }
    assert [h.query_text for _, h in harness.db.history] == ["private"]


def test_settings_toggle_and_account_deletion(harness: Harness) -> None:
    token = str(_register(harness)["access_token"])
    off = harness.client.patch(
        "/api/v1/account/settings", json={"save_history": False}, headers=_bearer(token)
    )
    assert off.status_code == 200 and off.json()["save_history"] is False

    wrong = harness.client.post(
        "/api/v1/account/delete", json={"password": "wrong password!"}, headers=_bearer(token)
    )
    assert wrong.status_code == 401 and harness.db.find_user("asha@example.com") is not None
    gone = harness.client.post(
        "/api/v1/account/delete", json={"password": PASSWORD}, headers=_bearer(token)
    )
    assert gone.status_code == 204 and harness.db.find_user("asha@example.com") is None
    assert harness.client.get("/api/v1/account/me", headers=_bearer(token)).status_code == 401


def test_admin_logout_revokes_the_token(harness: Harness) -> None:
    from pgs_api.db.database import AdminAccount

    harness.db.admins["ops"] = AdminAccount(7, "ops", None, "AUDITOR", hash_password(PASSWORD))
    token = harness.client.post(
        "/api/v1/auth/login", json={"username": "ops", "password": PASSWORD}
    ).json()["access_token"]
    assert harness.client.post("/api/v1/auth/logout", headers=_bearer(token)).status_code == 204
    assert harness.client.get("/api/v1/auth/me", headers=_bearer(token)).status_code == 401
