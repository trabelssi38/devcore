"""Explicit local provisioning for the individual Cockpit qualification profile."""

import argparse
from contextlib import closing
import getpass
import json
import os
from pathlib import Path
import sys
import warnings

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from devcore_engine.security.identity import (
    ACTIONS, ROLES, add_user, disable_user, enable_user, initialize_store, issue_credential,
    remove_membership, revoke_credential, set_membership, store_path,
    connect_existing,
)
from devcore_engine.security.browser_sessions import upgrade_session_store
from devcore_engine.security.secret_files import (
    check_credential_file, protect_reserved_file, protect_empty_directory, validate_output_path,
)


def read_admin_authorization(path):
    if path is None:
        raise ValueError("An administrative credential file is required")
    check_credential_file(path)
    with store_path(path).open("rb") as stream:
        raw = stream.read(4097)
    if len(raw) > 4096:
        raise ValueError("Administrative credential file too large")
    value = json.loads(raw)
    token = value.get("token") if isinstance(value, dict) else None
    if not isinstance(token, str) or not token or len(token) > 512:
        raise ValueError("Invalid administrative credential file")
    return "Bearer " + token


def masked_password(*, confirm=False):
    if not sys.stdin.isatty():
        raise ValueError("An interactive terminal is required for password entry")
    with warnings.catch_warnings():
        warnings.simplefilter("error", getpass.GetPassWarning)
        password = getpass.getpass("Mot de passe (15..256 caracteres) : ")
        if confirm and password != getpass.getpass("Confirmer : "):
            raise ValueError("Password confirmation differs")
    return password


def deliver_credential(output, operation):
    """Exclusive output; callback runs inside the credential's write transaction."""
    validate_output_path(output)
    destination = store_path(output)
    fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            protect_reserved_file(destination)  # No credential created and no secret written yet.
            def deliver(identifier, token):
                json.dump({"credential_id": identifier, "token": token}, stream)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            identifier, _ = operation(deliver)
        return {"credential_id": identifier, "secret_file": str(destination)}
    except Exception:
        destination.unlink(missing_ok=True)
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", required=True, type=Path)
    parser.add_argument("--admin-credential-file", type=Path)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init")
    commands.add_parser("init-private-store")
    commands.add_parser("check-store-protection")
    commands.add_parser("upgrade-sessions")
    commands.add_parser("upgrade-passwords")
    commands.add_parser("upgrade-admin")
    private_dir = commands.add_parser("protect-secret-dir")
    private_dir.add_argument("--directory", required=True, type=Path)
    bootstrap = commands.add_parser("bootstrap-admin")
    bootstrap.add_argument("--user", required=True)
    bootstrap.add_argument("--confirm-local-bootstrap", action="store_true")
    recovery = commands.add_parser("recover-local-admin")
    recovery.add_argument("--user", required=True)
    recovery.add_argument("--confirm-local-recovery", action="store_true")
    recovery.add_argument("--confirm-services-stopped", action="store_true")
    backup = commands.add_parser("backup-private-store")
    backup.add_argument("--output", required=True, type=Path)
    backup.add_argument("--confirm-services-stopped", action="store_true")
    restore = commands.add_parser("restore-private-store")
    restore.add_argument("--backup", required=True, type=Path)
    restore.add_argument("--expected-sha256", required=True)
    restore.add_argument("--confirm-local-restore", action="store_true")
    restore.add_argument("--confirm-services-stopped", action="store_true")
    login = commands.add_parser("login-admin")
    login.add_argument("--user", required=True)
    login.add_argument("--ttl-seconds", type=int, default=900)
    login.add_argument("--output", required=True, type=Path)
    for name in ("add-user", "disable-user", "enable-user", "set-password", "reset-password", "grant-admin", "remove-admin"):
        command = commands.add_parser(name)
        command.add_argument("--user", required=True)
    grant = commands.add_parser("grant")
    grant.add_argument("--user", required=True)
    grant.add_argument("--project", required=True)
    grant.add_argument("--role", required=True, choices=ROLES)
    remove = commands.add_parser("remove-membership")
    remove.add_argument("--user", required=True)
    remove.add_argument("--project", required=True)
    issue = commands.add_parser("issue-token")
    issue.add_argument("--user", required=True)
    issue.add_argument("--project", action="append", required=True)
    issue.add_argument("--action", action="append", required=True, choices=sorted(ACTIONS))
    issue.add_argument("--ttl-seconds", type=int, default=3600)
    issue.add_argument("--output", required=True, type=Path)
    revoke = commands.add_parser("revoke-token")
    revoke.add_argument("--credential-id", required=True)
    revoke_admin = commands.add_parser("revoke-admin-token")
    revoke_admin.add_argument("--credential-id", required=True)
    args = parser.parse_args(argv)
    path = store_path(args.store)
    result = {"command": args.command, "status": "success"}
    if args.command in {"init-private-store", "check-store-protection"}:
        from devcore_engine.security.private_store import initialize_private_store, check_store_protection
        operation = initialize_private_store if args.command == "init-private-store" else check_store_protection
        result["protection"] = operation(args.store)
        print(json.dumps(result))
        return
    if args.command == "protect-secret-dir":
        result["protection"] = protect_empty_directory(args.directory)
        print(json.dumps(result))
        return
    if args.command == "recover-local-admin":
        if not sys.stdin.isatty() or not args.confirm_local_recovery or not args.confirm_services_stopped:
            raise ValueError("Recovery requires an interactive local terminal and explicit maintenance confirmation")
        from devcore_engine.security.local_recovery import preflight_recovery, recover_admin
        # Preserve the supplied path so a junction alias cannot hide behind resolve().
        preflight_recovery(args.store, args.user)
        password = masked_password(confirm=True)
        result.update(recover_admin(args.store, args.user, password))
        print(json.dumps(result))
        return
    if args.command in {"backup-private-store", "restore-private-store"}:
        if (not sys.stdin.isatty() or not args.confirm_services_stopped or
                (args.command == "restore-private-store" and not args.confirm_local_restore)):
            raise ValueError("Snapshot requires an interactive local terminal and maintenance confirmation")
        from devcore_engine.security.identity_backup import backup_identity_store, restore_identity_store
        if args.command == "backup-private-store":
            result.update(backup_identity_store(args.store, args.output))
        else:
            result.update(restore_identity_store(args.backup, args.store, args.expected_sha256))
        print(json.dumps(result))
        return
    if args.command in {"upgrade-admin", "bootstrap-admin", "login-admin"}:
        from devcore_engine.security.administration import bootstrap_admin, login_admin, upgrade_admin_store
        if args.command == "upgrade-admin":
            upgrade_admin_store(path)
        elif args.command == "bootstrap-admin":
            if not sys.stdin.isatty() or not args.confirm_local_bootstrap:
                raise ValueError("Bootstrap requires an interactive local terminal and explicit confirmation")
            bootstrap_admin(path, args.user)
        else:
            password = masked_password()
            result.update(deliver_credential(args.output, lambda deliver: login_admin(
                path, args.user, password, ttl_seconds=args.ttl_seconds, deliver=deliver)))
        print(json.dumps(result))
        return
    if args.command not in {"init", "upgrade-sessions", "upgrade-passwords"}:
        with closing(connect_existing(path)) as conn:
            version = conn.execute("SELECT version FROM identity_schema").fetchone()[0]
        if version == 4:
            from devcore_engine.security.administration import administer, authorize_admin
            authorization = read_admin_authorization(args.admin_credential_file)
            authorize_admin(path, authorization)
            arguments = {name: getattr(args, name, None) for name in ("user", "project", "role", "credential_id")}
            if args.command in {"set-password", "reset-password"}:
                arguments["password"] = masked_password(confirm=True)
            if args.command == "issue-token":
                arguments.update(project=None, projects=args.project, actions=args.action, ttl_seconds=args.ttl_seconds)
                result.update(deliver_credential(args.output, lambda deliver: administer(
                    path, authorization, args.command, deliver=deliver, **arguments)))
            else:
                administer(path, authorization, args.command, **arguments)
            print(json.dumps(result))
            return
        if args.command in {"grant-admin", "remove-admin", "revoke-admin-token"}:
            raise ValueError("Administration requires explicit schema upgrade")
    if args.command == "init":
        initialize_store(path)
    elif args.command == "upgrade-sessions":
        upgrade_session_store(path)
    elif args.command == "upgrade-passwords":
        from devcore_engine.security.passwords import upgrade_password_store
        upgrade_password_store(path)
    elif args.command == "add-user":
        add_user(path, args.user)
    elif args.command == "disable-user":
        disable_user(path, args.user)
    elif args.command == "enable-user":
        enable_user(path, args.user)
    elif args.command in {"set-password", "reset-password"}:
        from devcore_engine.security.passwords import set_password
        password = masked_password(confirm=True)
        set_password(path, args.user, password)
    elif args.command == "grant":
        set_membership(path, args.user, args.project, args.role)
    elif args.command == "remove-membership":
        remove_membership(path, args.user, args.project)
    elif args.command == "revoke-token":
        revoke_credential(path, args.credential_id)
    else:
        validate_output_path(args.output)
        destination = store_path(args.output)
        # Exclusive creation: never overwrite an existing secret or other file.
        fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        identifier = None
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                protect_reserved_file(destination)
                identifier, token = issue_credential(
                    path, args.user, args.project, args.action, ttl_seconds=args.ttl_seconds,
                )
                json.dump({"credential_id": identifier, "token": token}, stream)
                stream.write("\n")
            result["credential_id"] = identifier
            result["secret_file"] = str(destination)
        except Exception:
            if identifier is not None:
                revoke_credential(path, identifier)
            destination.unlink(missing_ok=True)
            raise
    print(json.dumps(result))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Local identity command failed: {type(exc).__name__}", file=sys.stderr)
        raise SystemExit(2)
