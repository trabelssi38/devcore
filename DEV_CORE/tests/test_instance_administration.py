"""Administrative capabilities and rollback on a disposable identity store."""

from concurrent.futures import ThreadPoolExecutor
import hashlib
import sqlite3

import pytest

from devcore_engine.security import administration as admin, passwords
from devcore_engine.security.identity import (
    READ, WRITE, AuthenticationRequired, IdentityUnavailable, ProjectAccessDenied,
    SqliteIdentityProvider, add_user, disable_user, initialize_store, issue_credential, set_membership,
)
from devcore_engine.security.browser_sessions import (
    authorize_session, create_session, upgrade_session_store,
)

PASSWORD = "Une phrase privée de recette"
ORIGIN = "http://localhost"


@pytest.fixture
def prepared(tmp_path):
    path = tmp_path / "identity.db"
    initialize_store(path)
    upgrade_session_store(path)
    passwords.upgrade_password_store(path)
    for user, project, role in (("alice", "alpha", "owner"), ("bob", "beta", "reader")):
        add_user(path, user)
        set_membership(path, user, project, role)
        passwords.set_password(path, user, PASSWORD, now=1000)
    return path


@pytest.fixture
def managed(prepared):
    admin.upgrade_admin_store(prepared)
    admin.bootstrap_admin(prepared, "alice", now=1000)
    identifier, token = admin.login_admin(prepared, "alice", PASSWORD, now=1000)
    return prepared, identifier, token


def test_explicit_upgrade_preserves_sessions_credentials_and_is_repeatable(prepared, tmp_path):
    _, token = issue_credential(prepared, "alice", ["alpha"], [READ, WRITE], now=1000)
    _, cookie = create_session(prepared, "Bearer " + token, "alpha", ORIGIN, now=1001)
    admin.upgrade_admin_store(prepared)
    snapshot = prepared.read_bytes()
    admin.upgrade_admin_store(prepared)
    upgrade_session_store(prepared)
    passwords.upgrade_password_store(prepared)
    initialize_store(prepared)
    assert prepared.read_bytes() == snapshot
    assert authorize_session(prepared, cookie, "alpha", WRITE, ORIGIN, now=1002).principal.user_id == "alice"
    password_session, _ = passwords.create_password_session(prepared, "alice", PASSWORD, "alpha", ORIGIN, now=1002)
    assert password_session.principal.user_id == "alice"
    bad = tmp_path / "v1.db"
    initialize_store(bad)
    snapshot = bad.read_bytes()
    with pytest.raises(IdentityUnavailable):
        admin.upgrade_admin_store(bad)
    assert bad.read_bytes() == snapshot


def test_bootstrap_is_once_only_even_with_two_concurrent_local_operators(prepared):
    admin.upgrade_admin_store(prepared)
    def provision(user):
        try:
            admin.bootstrap_admin(prepared, user)
            return user
        except ProjectAccessDenied:
            return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        successes = [user for user in pool.map(provision, ("alice", "bob")) if user]
    assert len(successes) == 1
    with sqlite3.connect(prepared) as conn:
        assert conn.execute("SELECT user_id FROM identity_instance_admins").fetchall() == [(successes[0],)]
        assert conn.execute("SELECT actor,action FROM identity_audit").fetchall() == [("local-operator", "admin.bootstrap")]
    with pytest.raises(ProjectAccessDenied):
        admin.bootstrap_admin(prepared, successes[0])


def test_failed_bootstrap_audit_keeps_provisioning_open_without_admin(prepared):
    admin.upgrade_admin_store(prepared)
    with sqlite3.connect(prepared) as conn:
        conn.execute("DROP TABLE identity_audit")
    with pytest.raises(sqlite3.OperationalError):
        admin.bootstrap_admin(prepared, "alice")
    with sqlite3.connect(prepared) as conn:
        assert conn.execute("SELECT bootstrapped FROM identity_admin_state").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM identity_instance_admins").fetchone()[0] == 0


def test_project_owner_cannot_administer_and_instance_admin_has_no_implicit_task_rights(managed):
    path, _, token = managed
    _, project_token = issue_credential(path, "alice", ["alpha"], [READ, WRITE], now=1000)
    with pytest.raises(AuthenticationRequired):
        admin.administer(path, "Bearer " + project_token, "grant-admin", user="bob", now=1001)
    with pytest.raises(ProjectAccessDenied):
        admin.login_admin(path, "bob", PASSWORD, now=1001)
    provider = SqliteIdentityProvider(path)
    with pytest.raises(AuthenticationRequired):
        provider.authorize("Bearer " + token, "alpha", READ, now=1001)
    with pytest.raises(ProjectAccessDenied):
        provider.authorize("Bearer " + project_token, "beta", READ, now=1001)
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM identity_instance_admins").fetchone()[0] == 1


@pytest.mark.parametrize("timestamp", [999, 1900, 1901])
def test_admin_expiry_and_future_issuance_are_rejected(managed, timestamp):
    path, _, token = managed
    with pytest.raises(AuthenticationRequired):
        admin.administer(path, "Bearer " + token, "add-user", user="intruder", now=timestamp)
    assert admin.authorize_admin(path, "Bearer " + token, now=1899).user_id == "alice"
    assert token.encode() not in path.read_bytes()


def test_admin_mutations_are_audited_and_project_tokens_keep_explicit_scope(managed):
    path, _, token = managed
    auth = "Bearer " + token
    admin.administer(path, auth, "add-user", user="charlie", now=1001)
    admin.administer(path, auth, "set-password", user="charlie", password=PASSWORD, now=1002)
    admin.administer(path, auth, "grant", user="charlie", project="gamma", role="reader", now=1003)
    identifier, project_token = admin.administer(path, auth, "issue-token", user="charlie",
        projects=["gamma"], actions=[READ], ttl_seconds=60, now=1004)
    assert SqliteIdentityProvider(path).authorize("Bearer " + project_token, "gamma", READ, now=1005).user_id == "charlie"
    with pytest.raises(ValueError):
        admin.administer(path, auth, "issue-token", user="charlie", projects=["gamma"], actions=[WRITE], now=1005)
    admin.administer(path, auth, "revoke-token", credential_id=identifier, now=1006)
    with pytest.raises(AuthenticationRequired):
        SqliteIdentityProvider(path).authorize("Bearer " + project_token, "gamma", READ, now=1007)
    with sqlite3.connect(path) as conn:
        rows = conn.execute("SELECT actor,action,target_user,project_id,details FROM identity_audit WHERE action LIKE 'identity.%'").fetchall()
        assert len(rows) == 5 and all(row[0] == "alice" and row[2] == "charlie" for row in rows)
        assert all(secret not in str(rows) for secret in (PASSWORD, token, project_token))
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []


@pytest.mark.parametrize("operation", ["disable-user", "remove-admin"])
def test_last_enabled_admin_cannot_be_disabled_or_demoted(managed, operation):
    path, _, token = managed
    with pytest.raises(ProjectAccessDenied, match="last enabled"):
        admin.administer(path, "Bearer " + token, operation, user="alice", now=1001)
    with pytest.raises(ProjectAccessDenied, match="last enabled"):
        disable_user(path, "alice")  # Trusted legacy helper also preserves this invariant.
    assert admin.authorize_admin(path, "Bearer " + token, now=1002).user_id == "alice"


def test_concurrent_removal_preserves_one_enabled_administrator(managed):
    path, _, token = managed
    admin.administer(path, "Bearer " + token, "grant-admin", user="bob", now=1001)
    _, bob_token = admin.login_admin(path, "bob", PASSWORD, now=1002)
    def remove(authorization, target):
        try:
            admin.administer(path, authorization, "remove-admin", user=target, now=1003)
            return True
        except (AuthenticationRequired, ProjectAccessDenied):
            return False
    with ThreadPoolExecutor(max_workers=2) as pool:
        a = pool.submit(remove, "Bearer " + token, "bob")
        b = pool.submit(remove, "Bearer " + bob_token, "alice")
        assert sum((a.result(), b.result())) == 1
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM identity_instance_admins a JOIN identity_users u ON u.id=a.user_id WHERE u.enabled=1").fetchone()[0] == 1


@pytest.mark.parametrize("operation", ["disable-user", "reset-password", "remove-admin"])
def test_administrative_access_revoked_on_disable_reset_and_role_removal(managed, operation):
    path, _, token = managed
    admin.administer(path, "Bearer " + token, "grant-admin", user="bob", now=1001)
    _, bob_token = admin.login_admin(path, "bob", PASSWORD, now=1002)
    kwargs = {"password": "Une nouvelle phrase de recette"} if operation == "reset-password" else {}
    admin.administer(path, "Bearer " + token, operation, user="bob", now=1003, **kwargs)
    with pytest.raises(AuthenticationRequired):
        admin.authorize_admin(path, "Bearer " + bob_token, now=1004)
    assert admin.authorize_admin(path, "Bearer " + token, now=1004).user_id == "alice"
    if operation == "disable-user":
        admin.administer(path, "Bearer " + token, "enable-user", user="bob", now=1005)
        with pytest.raises(AuthenticationRequired):
            admin.authorize_admin(path, "Bearer " + bob_token, now=1006)


@pytest.mark.parametrize("operation", ["add-user", "grant-admin", "disable-user"])
def test_missing_identity_audit_rolls_back_administration(managed, operation):
    path, _, token = managed
    target = "charlie" if operation == "add-user" else "bob"
    with sqlite3.connect(path) as conn:
        conn.execute("DROP TABLE identity_audit")
    snapshot = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(sqlite3.OperationalError):
        admin.administer(path, "Bearer " + token, operation, user=target, now=1001)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == snapshot


def test_role_removed_during_password_verification_prevents_admin_login(managed, monkeypatch):
    path, _, token = managed
    admin.administer(path, "Bearer " + token, "grant-admin", user="bob", now=1001)
    original = passwords.verify_password
    def verify(encoded, password):
        accepted = original(encoded, password)
        admin.administer(path, "Bearer " + token, "remove-admin", user="bob", now=1002)
        return accepted
    monkeypatch.setattr(passwords, "verify_password", verify)
    with pytest.raises(ProjectAccessDenied):
        admin.login_admin(path, "bob", PASSWORD, now=1003)
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM identity_admin_credentials WHERE user_id='bob'").fetchone()[0] == 0


def test_expired_admin_can_log_in_again_and_failed_delivery_rolls_back_issuance(managed):
    path, _, token = managed
    with pytest.raises(AuthenticationRequired):
        admin.authorize_admin(path, "Bearer " + token, now=1900)
    _, replacement = admin.login_admin(path, "alice", PASSWORD, now=1901)
    assert admin.authorize_admin(path, "Bearer " + replacement, now=1902).user_id == "alice"
    with sqlite3.connect(path) as conn:
        before = conn.execute("SELECT COUNT(*) FROM identity_admin_credentials").fetchone()[0]
    def broken_delivery(*_):
        raise OSError("fixture output failure")
    with pytest.raises(OSError):
        admin.login_admin(path, "alice", PASSWORD, now=1903, deliver=broken_delivery)
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM identity_admin_credentials").fetchone()[0] == before
