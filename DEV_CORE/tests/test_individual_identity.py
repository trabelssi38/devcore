import hashlib
import json
import sqlite3

import pytest

from devcore_engine.security.identity import (
    AuthenticationRequired, IdentityUnavailable, ProjectAccessDenied, READ, WRITE, CONTEXT_READ,
    SqliteIdentityProvider, add_user, disable_user, initialize_store, issue_credential,
    remove_membership, revoke_credential, set_membership,
)


@pytest.fixture
def store(tmp_path):
    path = tmp_path / "local" / "identity.db"
    initialize_store(path)
    add_user(path, "alice")
    set_membership(path, "alice", "alpha", "contributor")
    return path


def test_scope_roles_and_secrets_are_enforced_at_issue_and_each_request(store):
    identifier, token = issue_credential(store, "alice", ["alpha"], [READ, WRITE], now=1000)
    provider = SqliteIdentityProvider(store)
    principal = provider.authorize("Bearer " + token, "alpha", READ, now=1001)
    assert (principal.user_id, principal.credential_id, principal.project_id) == ("alice", identifier, "alpha")
    with pytest.raises(ProjectAccessDenied):
        provider.authorize("Bearer " + token, "beta", READ, now=1001)
    set_membership(store, "alice", "alpha", "reader")
    assert provider.authorize("Bearer " + token, "alpha", READ, now=1001).action == READ
    with pytest.raises(ProjectAccessDenied):
        provider.authorize("Bearer " + token, "alpha", WRITE, now=1001)
    with pytest.raises(ValueError):
        issue_credential(store, "alice", ["alpha"], [WRITE])
    remove_membership(store, "alice", "alpha")
    with pytest.raises(ProjectAccessDenied):
        provider.authorize("Bearer " + token, "alpha", READ, now=1001)
    with sqlite3.connect(store) as conn:
        saved = conn.execute("SELECT token_hash,projects,actions FROM identity_credentials").fetchone()
    assert saved[0] == hashlib.sha256(token.encode()).hexdigest()
    assert token not in json.dumps(saved)


@pytest.mark.parametrize("role,allowed", [("reader", [READ, CONTEXT_READ]),
                                          ("contributor", [READ, WRITE, CONTEXT_READ]),
                                          ("owner", [READ, WRITE, CONTEXT_READ])])
def test_project_role_matrix(store, role, allowed):
    set_membership(store, "alice", "alpha", role)
    _, token = issue_credential(store, "alice", ["alpha"], allowed)
    provider = SqliteIdentityProvider(store)
    for action in allowed:
        assert provider.authorize("Bearer " + token, "alpha", action).user_id == "alice"
    if WRITE not in allowed:
        with pytest.raises(ProjectAccessDenied):
            provider.authorize("Bearer " + token, "alpha", WRITE)


@pytest.mark.parametrize("revocation", ["credential", "user"])
def test_revocation_expiry_and_future_issuance(store, revocation):
    identifier, token = issue_credential(store, "alice", ["alpha"], [READ], ttl_seconds=60, now=1000)
    provider = SqliteIdentityProvider(store)
    for now in (999, 1060, 1061):
        with pytest.raises(AuthenticationRequired):
            provider.authorize("Bearer " + token, "alpha", READ, now=now)
    assert provider.authorize("Bearer " + token, "alpha", READ, now=1059).user_id == "alice"
    if revocation == "credential":
        revoke_credential(store, identifier)
    else:
        disable_user(store, "alice")
    with pytest.raises(AuthenticationRequired):
        provider.authorize("Bearer " + token, "alpha", READ, now=1001)


def test_missing_store_never_creates_database_and_unknown_schema_is_preserved(tmp_path):
    path = tmp_path / "identity.db"
    provider = SqliteIdentityProvider(path)
    with pytest.raises(IdentityUnavailable):
        provider.authorize("Bearer fake", "alpha", READ)
    assert not path.exists()
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE unrelated(value TEXT)")
        conn.execute("INSERT INTO unrelated VALUES ('existing data')")
    original = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(IdentityUnavailable):
        initialize_store(path)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == original


def test_read_requests_do_not_change_store_and_initialization_is_repeatable(store):
    _, token = issue_credential(store, "alice", ["alpha"], [READ])
    original = hashlib.sha256(store.read_bytes()).hexdigest()
    provider = SqliteIdentityProvider(store)
    for _ in range(3):
        provider.authorize("Bearer " + token, "alpha", READ)
    initialize_store(store)
    assert hashlib.sha256(store.read_bytes()).hexdigest() == original
