from contextlib import closing
import hashlib
import sqlite3

import pytest

from devcore_engine.security import passwords
from devcore_engine.security.identity import (
    AuthenticationRequired, IdentityUnavailable, ProjectAccessDenied, READ, WRITE, CONTEXT_READ,
    SqliteIdentityProvider, add_user, disable_user, enable_user, initialize_store,
    issue_credential, remove_membership, set_membership,
)
from devcore_engine.security.browser_sessions import authorize_session, create_session, upgrade_session_store

PASSWORD = "  Une phrase secrète locale  "
ORIGIN = "http://localhost"


@pytest.fixture
def store(tmp_path):
    path = tmp_path / "identity.db"
    initialize_store(path)
    for user, project in (("alice", "alpha"), ("bob", "beta")):
        add_user(path, user)
        set_membership(path, user, project, "contributor")
    upgrade_session_store(path)
    passwords.upgrade_password_store(path)
    passwords.set_password(path, "alice", PASSWORD, now=1000)
    passwords.set_password(path, "bob", PASSWORD, now=1000)
    return path


def login(path, user="alice", password=PASSWORD, project="alpha", now=1001):
    return passwords.create_password_session(path, user, password, project, ORIGIN, now=now)


def test_upgrade_requires_explicit_session_schema_and_preserves_existing_credentials(tmp_path):
    path = tmp_path / "identity.db"
    initialize_store(path)
    before = path.read_bytes()
    with pytest.raises(IdentityUnavailable):
        passwords.upgrade_password_store(path)
    assert path.read_bytes() == before
    add_user(path, "alice")
    set_membership(path, "alice", "alpha", "reader")
    _, token = issue_credential(path, "alice", ["alpha"], [READ], now=1000)
    upgrade_session_store(path)
    _, secret = create_session(path, "Bearer " + token, "alpha", ORIGIN, now=1001)
    passwords.upgrade_password_store(path)
    before = path.read_bytes()
    passwords.upgrade_password_store(path)
    upgrade_session_store(path)
    initialize_store(path)
    assert path.read_bytes() == before
    assert authorize_session(path, secret, "alpha", READ, ORIGIN, now=1002).principal.user_id == "alice"


def test_argon2id_salted_hashes_and_password_policy_do_not_normalize_spaces(store):
    with closing(sqlite3.connect(store)) as conn:
        hashes = [row[0] for row in conn.execute("SELECT password_hash FROM identity_passwords")]
    assert hashes[0] != hashes[1]
    assert all(value.startswith("$argon2id$v=19$m=65536,t=3,p=4$") for value in hashes)
    assert PASSWORD.encode() not in store.read_bytes()
    for invalid in (None, "a" * 14, "a" * 257):
        with pytest.raises(ValueError):
            passwords.set_password(store, "alice", invalid)
    with pytest.raises(AuthenticationRequired):
        login(store, password=PASSWORD.strip())
    login(store)


def test_password_sessions_keep_project_role_scope_and_return_no_api_token(store):
    session, secret = login(store)
    assert session.actions == (READ, WRITE, CONTEXT_READ)
    assert authorize_session(store, secret, "alpha", READ, ORIGIN, now=1002).principal.user_id == "alice"
    with pytest.raises(ProjectAccessDenied):
        authorize_session(store, secret, "beta", READ, ORIGIN, now=1002)
    with pytest.raises(ProjectAccessDenied):
        login(store, project="beta")
    set_membership(store, "alice", "alpha", "reader")
    assert authorize_session(store, secret, "alpha", READ, ORIGIN, now=1002).actions == (READ, CONTEXT_READ)
    reader, _ = login(store)
    assert reader.actions == (READ, CONTEXT_READ)
    assert secret.encode() not in store.read_bytes()


def test_recovery_revokes_all_credentials_and_sessions_of_only_that_user(store):
    _, old_session = login(store)
    _, bob_session = login(store, user="bob", project="beta")
    _, token = issue_credential(store, "alice", ["alpha"], [READ, WRITE], now=1001)
    passwords.set_password(store, "alice", "Nouvelle phrase pour Alice", now=1002)
    for operation in (
        lambda: login(store, now=1003),
        lambda: authorize_session(store, old_session, "alpha", READ, ORIGIN, now=1003),
        lambda: SqliteIdentityProvider(store).authorize("Bearer " + token, "alpha", READ, now=1003),
    ):
        with pytest.raises(AuthenticationRequired):
            operation()
    login(store, password="Nouvelle phrase pour Alice", now=1003)
    assert authorize_session(store, bob_session, "beta", READ, ORIGIN, now=1003).principal.user_id == "bob"
    with closing(sqlite3.connect(store)) as conn:
        assert conn.execute("SELECT role FROM identity_memberships WHERE user_id='alice'").fetchone()[0] == "contributor"
    disable_user(store, "alice")
    passwords.set_password(store, "alice", PASSWORD, now=1004)
    with pytest.raises(AuthenticationRequired):
        login(store, now=1005)
    enable_user(store, "alice")
    login(store, now=1005)


def test_failure_cooldown_persists_without_blocking_other_users_and_expires(store):
    for n in range(5):
        with pytest.raises(AuthenticationRequired):
            login(store, password="wrong password", now=1001+n)
    with closing(sqlite3.connect(store)) as conn:
        assert conn.execute("SELECT failures,blocked_until FROM identity_passwords WHERE user_id='alice'").fetchone() == (5, 1065)
    with pytest.raises(AuthenticationRequired):
        login(store, now=1064)
    login(store, user="bob", project="beta", now=1064)
    login(store, now=1065)
    with closing(sqlite3.connect(store)) as conn:
        assert conn.execute("SELECT failures,blocked_until FROM identity_passwords WHERE user_id='alice'").fetchone() == (0, 0)


@pytest.mark.parametrize("change", ["reset", "disable", "membership"])
def test_change_during_verification_cannot_admit_stale_account_state(store, monkeypatch, change):
    original = passwords.verify_password
    def concurrent_change(encoded, password):
        result = original(encoded, password)
        if change == "reset":
            passwords.set_password(store, "alice", "Une autre phrase très secrète", now=1002)
        elif change == "disable":
            disable_user(store, "alice")
        else:
            remove_membership(store, "alice", "alpha")
        return result
    monkeypatch.setattr(passwords, "verify_password", concurrent_change)
    with pytest.raises(ProjectAccessDenied if change == "membership" else AuthenticationRequired):
        login(store)
    with closing(sqlite3.connect(store)) as conn:
        assert conn.execute("SELECT COUNT(*) FROM identity_browser_sessions").fetchone()[0] == 0


def test_unknown_user_checks_dummy_hash_without_creating_state_and_missing_store_stays_absent(store, tmp_path, monkeypatch):
    calls = []
    original = passwords.verify_password
    def verify(encoded, password):
        calls.append(encoded)
        return original(encoded, password)
    monkeypatch.setattr(passwords, "verify_password", verify)
    before = hashlib.sha256(store.read_bytes()).hexdigest()
    with pytest.raises(AuthenticationRequired):
        login(store, user="unknown")
    assert len(calls) == 1
    assert hashlib.sha256(store.read_bytes()).hexdigest() == before
    missing = tmp_path / "absent.db"
    with pytest.raises(IdentityUnavailable):
        login(missing)
    assert not missing.exists()
