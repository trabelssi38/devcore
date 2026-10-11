import hashlib

import pytest

from devcore_engine.security.identity import (
    AuthenticationRequired, IdentityUnavailable, ProjectAccessDenied, READ, WRITE,
    add_user, initialize_store, issue_credential, revoke_credential, set_membership,
)
from devcore_engine.security.browser_sessions import (
    authorize_session, create_session, csrf_for_session, upgrade_session_store,
)


def provision(tmp_path, ttl=3600):
    path = tmp_path / "identity.db"
    initialize_store(path)
    add_user(path, "alice")
    set_membership(path, "alice", "alpha", "contributor")
    identifier, token = issue_credential(path, "alice", ["alpha"], [READ, WRITE], now=1000, ttl_seconds=ttl)
    return path, identifier, "Bearer " + token


def test_session_upgrade_is_explicit_repeatable_and_preserves_credentials(tmp_path):
    path, _, authorization = provision(tmp_path)
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(IdentityUnavailable):
        create_session(path, authorization, "alpha", "http://localhost", now=1001)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before
    upgrade_session_store(path)
    after = hashlib.sha256(path.read_bytes()).hexdigest()
    upgrade_session_store(path)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == after
    create_session(path, authorization, "alpha", "http://localhost", now=1001)


def test_sessions_bind_project_origin_csrf_expiry_and_source_revocation(tmp_path):
    path, identifier, authorization = provision(tmp_path, ttl=60)
    upgrade_session_store(path)
    session, secret = create_session(path, authorization, "alpha", "http://localhost", now=1010)
    assert session.expires_at == 1060
    assert authorize_session(path, secret, "alpha", READ, "http://localhost", now=1059).principal.user_id == "alice"
    for project, origin in (("beta", "http://localhost"), ("alpha", "http://evil")):
        with pytest.raises(ProjectAccessDenied):
            authorize_session(path, secret, project, READ, origin, now=1011)
    for csrf in ("wrong", "é" * 64, "a" * 65):
        with pytest.raises(ProjectAccessDenied):
            authorize_session(path, secret, "alpha", WRITE, "http://localhost", mutate=True, csrf=csrf, now=1011)
    authorize_session(path, secret, "alpha", WRITE, "http://localhost", mutate=True, csrf=csrf_for_session(secret), now=1011)
    with pytest.raises(AuthenticationRequired):
        authorize_session(path, secret, "alpha", READ, "http://localhost", now=1060)
    revoke_credential(path, identifier)
    with pytest.raises(AuthenticationRequired):
        authorize_session(path, secret, "alpha", READ, "http://localhost", now=1011)


def test_session_rotation_retires_previous_cookie_and_read_requests_are_pure(tmp_path):
    path, _, authorization = provision(tmp_path)
    upgrade_session_store(path)
    _, previous = create_session(path, authorization, "alpha", "http://localhost", now=1001)
    _, secret = create_session(path, authorization, "alpha", "http://localhost", previous=previous, now=1002)
    assert secret != previous
    with pytest.raises(AuthenticationRequired):
        authorize_session(path, previous, "alpha", READ, "http://localhost", now=1003)
    original = hashlib.sha256(path.read_bytes()).hexdigest()
    authorize_session(path, secret, "alpha", READ, "http://localhost", now=1003)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == original
    assert secret.encode() not in path.read_bytes()
    create_session(path, authorization, "alpha", "http://localhost", previous="x" * 513, now=1004)
