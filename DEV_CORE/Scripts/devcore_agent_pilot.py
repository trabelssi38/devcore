"""Opt-in DevCore agent pilot: read-only proposal, exact human-approved patch.

This entry point is deliberately not connected to task_sync or a schedule.
Only the dedicated pilot checkout may be used. The Codex subprocess has a
read-only sandbox; applying its proposal is a separate interactive operation.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import difflib
import getpass
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from uuid import uuid4


PROJECT = "devcore"
PILOT_REPO = Path("E:/DevCoreRuntime/qualification/devcore-agent-pilot")
MAX_PATCH_BYTES = 128_000
MAX_TASK_BYTES = 8_000
MAX_SNIPPET_BYTES = 8_000
PATCH_HEADER = re.compile(r"diff --git a/([A-Za-z0-9_./-]+) b/([A-Za-z0-9_./-]+)$")


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=repo, capture_output=True,
                            text=True, timeout=45, check=True)
    return result.stdout.strip()


def _repo(repo: Path) -> tuple[Path, str]:
    repo = repo.resolve(strict=True)
    if repo != PILOT_REPO.resolve(strict=True):
        raise ValueError("Only the dedicated devcore pilot checkout is allowed")
    if Path(_git(repo, "rev-parse", "--show-toplevel")).resolve(strict=True) != repo:
        raise ValueError("Repository root mismatch")
    if not (repo / "README.md").is_file() or not (repo / "DEV_CORE").is_dir():
        raise ValueError("DevCore project markers missing")
    if _git(repo, "status", "--porcelain", "--untracked-files=all"):
        raise ValueError("Pilot checkout must be clean")
    return repo, _git(repo, "rev-parse", "HEAD")


def _patch_paths(patch: str) -> list[str]:
    if not patch or len(patch.encode("utf-8")) > MAX_PATCH_BYTES:
        raise ValueError("Patch missing or exceeds pilot quota")
    if "\x00" in patch or "\r" in patch or not patch.endswith("\n"):
        raise ValueError("Patch contains unsupported bytes or line endings")
    if any(marker in patch for marker in ("GIT binary patch", "Binary files ",
                                           "rename from ", "rename to ",
                                           "copy from ", "copy to ",
                                           "new file mode ", "deleted file mode ",
                                           "old mode ", "new mode ")):
        raise ValueError("Only text edits to existing files are allowed")
    paths = []
    for line in patch.splitlines():
        if line.startswith("diff --git "):
            match = PATCH_HEADER.fullmatch(line)
            if not match or match.group(1) != match.group(2):
                raise ValueError("Unsupported diff path")
            path = match.group(1)
            parts = Path(path).parts
            if (not path.startswith("DEV_CORE/") or ".." in parts or
                    ".git" in parts or len(paths) >= 8):
                raise ValueError("Patch exceeds the DevCore code path quota")
            paths.append(path)
        elif line.startswith("--- ") and line != f"--- a/{paths[-1] if paths else ''}":
            raise ValueError("Patch old path differs from diff header")
        elif line.startswith("+++ ") and line != f"+++ b/{paths[-1] if paths else ''}":
            raise ValueError("Patch new path differs from diff header")
    if not paths or len(set(paths)) != len(paths):
        raise ValueError("Patch has no unique file paths")
    return paths


def _proposal_patch(repo: Path, response: dict, target: str) -> str:
    if (set(response) != {"summary", "path", "old", "new"} or
            not all(isinstance(value, str) for value in response.values()) or
            response["path"] != target):
        raise ValueError("Invalid Codex replacement structure")
    if (not re.fullmatch(r"DEV_CORE/[A-Za-z0-9_./-]+", target) or
            ".." in Path(target).parts or ".git" in Path(target).parts or
            _git(repo, "ls-files", "--", target) != target):
        raise ValueError("Pilot target must be an existing DevCore source file")
    original = subprocess.run(["git", "show", "HEAD:" + target], cwd=repo,
                              capture_output=True, text=True, timeout=45,
                              check=True).stdout
    old = response["old"].replace("\r\n", "\n")
    new = response["new"].replace("\r\n", "\n")
    if (not old or len(old.encode("utf-8")) > MAX_SNIPPET_BYTES or
            len(new.encode("utf-8")) > MAX_SNIPPET_BYTES or
            original.count(old) != 1 or old == new):
        raise ValueError("Replacement must match exactly once within quota")
    revised = original.replace(old, new, 1)
    patch = (f"diff --git a/{target} b/{target}\n" + "".join(
        difflib.unified_diff(original.splitlines(keepends=True),
                             revised.splitlines(keepends=True),
                             fromfile="a/" + target, tofile="b/" + target)))
    _patch_paths(patch)
    return patch


def _digest(payload: dict) -> str:
    source = {key: payload[key] for key in ("project", "base", "task", "summary", "patch")}
    encoded = json.dumps(source, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _apply_check(repo: Path, patch: str) -> None:
    result = subprocess.run(["git", "apply", "--check", "--index",
                             "--ignore-whitespace", "-"],
                            cwd=repo, input=patch, text=True, capture_output=True,
                            timeout=45, check=False)
    if result.returncode:
        raise ValueError("Patch does not apply: " + result.stderr.strip()[:500])


def _verify_staged_patch(repo: Path, paths: list[str], expected: str) -> None:
    check = subprocess.run(["git", "diff", "--cached", "--check"], cwd=repo,
                           capture_output=True, text=True, timeout=45, check=False)
    if check.returncode:
        raise ValueError("Applied patch has whitespace errors: " + check.stdout[:500])
    result = subprocess.run(["git", "diff", "--cached", "--no-ext-diff",
                             "--no-color", "--no-renames", "--unified=3",
                             "--", *paths], cwd=repo, capture_output=True,
                            text=True, timeout=45, check=True)
    actual = "".join(line for line in result.stdout.splitlines(keepends=True)
                     if not line.startswith("index "))
    if actual != expected:
        raise ValueError("Applied patch differs from the approved proposal")


def _audit(state: Path, event: dict) -> None:
    state.mkdir(parents=True, exist_ok=True)
    record = {"at_utc": datetime.now(timezone.utc).isoformat(), **event}
    with (state / "audit.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def propose(repo: Path, state: Path, task: str, target: str,
            *, codex: str = "codex") -> dict:
    run_project = os.environ.get("DEVCORE_PROJECT_ID")
    if run_project and run_project != PROJECT:
        raise ValueError("Agent pilot run belongs to another project")
    repo, base = _repo(repo)
    state = state.resolve()
    if state.is_relative_to(repo):
        raise ValueError("Pilot state must be outside the repository")
    if not task.strip() or len(task.encode("utf-8")) > MAX_TASK_BYTES:
        raise ValueError("Task missing or exceeds pilot quota")
    if (not re.fullmatch(r"DEV_CORE/[A-Za-z0-9_./-]+", target) or
            ".." in Path(target).parts or ".git" in Path(target).parts or
            _git(repo, "ls-files", "--", target) != target):
        raise ValueError("Pilot target must be an existing DevCore source file")
    state.mkdir(parents=True, exist_ok=True)
    run_id = os.environ.get("DEVCORE_RUN_ID", "")
    if run_id and not re.fullmatch(r"[A-Za-z0-9._-]{1,128}", run_id):
        raise ValueError("Invalid durable run id")
    proposal_id = (hashlib.sha256(f"{PROJECT}:{run_id}".encode()).hexdigest()[:32]
                   if run_id else uuid4().hex)
    existing_path = state / f"{proposal_id}.json"
    if existing_path.exists():
        existing = read_proposal(state, proposal_id)
        if (existing["base"] != base or existing["task"] != task or
                existing["paths"] != [target]):
            raise ValueError("Durable run proposal conflicts with existing state")
        return {"id": proposal_id, "sha256": existing["sha256"],
                "summary": existing["summary"], "paths": existing["paths"],
                "status": existing["status"]}
    _audit(state, {"event": "proposal_started", "id": proposal_id,
                   "base": base, "project": PROJECT})
    schema = state / f"{proposal_id}.schema.json"
    output = state / f"{proposal_id}.response.json"
    schema.write_text(json.dumps({
        "type": "object", "additionalProperties": False,
        "required": ["summary", "path", "old", "new"],
        "properties": {key: {"type": "string"}
                       for key in ("summary", "path", "old", "new")},
    }), encoding="utf-8")
    prompt = ("Project devcore. Inspect this checkout read-only. Propose exactly "
              "one replacement in the named existing file. Do not modify files. "
              "Return JSON with summary, path, old (an exact unique snippet from "
              "the file) and new (its replacement). Preserve executable behavior "
              "unless the task explicitly requires a change. If no safe edit is "
              "possible, return an empty old string.\nTarget: " + target +
              "\n\nTask:\n" + task)
    command = [codex, "exec", "-C", str(repo), "--sandbox", "read-only",
               "--ephemeral", "--output-schema", str(schema),
               "--output-last-message", str(output), "-"]
    try:
        result = subprocess.run(command, input=prompt, capture_output=True,
                                text=True, timeout=900, check=False)
        if result.returncode:
            raise RuntimeError(f"Codex proposal failed with exit code {result.returncode}")
        if _repo(repo)[1] != base:
            raise RuntimeError("Repository changed while Codex was proposing")
        response = json.loads(output.read_text(encoding="utf-8"))
        if not isinstance(response, dict):
            raise ValueError("Invalid Codex proposal structure")
        patch = _proposal_patch(repo, response, target)
        paths = _patch_paths(patch)
        _apply_check(repo, patch)
        payload = {"project": PROJECT, "base": base, "task": task,
                   "summary": response["summary"], "patch": patch}
        digest = _digest(payload)
        proposal = {**payload, "id": proposal_id, "sha256": digest,
                    "paths": paths, "status": "waiting_approval"}
        (state / f"{proposal_id}.json").write_text(
            json.dumps(proposal, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        _audit(state, {"event": "proposal_ready", "id": proposal_id,
                       "sha256": digest, "base": base, "paths": paths})
        return {"id": proposal_id, "sha256": digest, "summary": response["summary"],
                "paths": paths, "status": "waiting_approval"}
    finally:
        schema.unlink(missing_ok=True)
        output.unlink(missing_ok=True)


def read_proposal(state: Path, proposal_id: str) -> dict:
    if not re.fullmatch(r"[0-9a-f]{32}", proposal_id):
        raise ValueError("Invalid proposal id")
    path = state / f"{proposal_id}.json"
    proposal = json.loads(path.read_text(encoding="utf-8"))
    if (proposal.get("id") != proposal_id or proposal.get("project") != PROJECT or
            proposal.get("sha256") != _digest(proposal)):
        raise ValueError("Proposal identity or hash mismatch")
    return proposal


def approve(repo: Path, state: Path, proposal_id: str, sha256: str,
            *, principal=None) -> dict:
    proposal = read_proposal(state, proposal_id)
    if proposal.get("status") != "waiting_approval" or proposal["sha256"] != sha256:
        raise ValueError("Proposal is not awaiting this exact approval")
    path = state / f"{proposal_id}.json"
    repo, base = _repo(repo)
    state = state.resolve(strict=True)
    if state.is_relative_to(repo):
        raise ValueError("Pilot state must be outside the repository")
    if base != proposal["base"]:
        raise ValueError("Pilot checkout changed since proposal")
    paths = _patch_paths(proposal["patch"])
    if paths != proposal["paths"]:
        raise ValueError("Proposal paths changed")
    if principal is None:
        if not sys.stdin.isatty():
            raise ValueError("Interactive human approval is required")
        print(f"Files: {', '.join(paths)}\nSummary: {proposal['summary']}")
        print(proposal["patch"])
        confirmation = input(f"Type APPLY {sha256} to approve this exact patch: ")
        if confirmation != f"APPLY {sha256}":
            raise ValueError("Approval phrase does not match proposal hash")
        actor = getpass.getuser()
        approval_source = "local_terminal"
    else:
        from devcore_engine.security.identity import Principal, WRITE
        if (not isinstance(principal, Principal) or principal.project_id != PROJECT
                or principal.action != WRITE or not principal.user_id.strip()):
            raise ValueError("Authenticated devcore write principal required")
        actor = principal.user_id
        approval_source = "authenticated_project_api"
    _apply_check(repo, proposal["patch"])
    _audit(state, {"event": "human_approved", "id": proposal_id,
                   "sha256": sha256, "actor": actor, "source": approval_source})
    subprocess.run(["git", "apply", "--index", "--ignore-whitespace", "-"], cwd=repo,
                   input=proposal["patch"], text=True, capture_output=True,
                   timeout=45, check=True)
    for relative in paths:
        target = repo / relative
        contents = target.read_bytes()
        if b"\r\n" in contents:
            target.write_bytes(contents.replace(b"\r\n", b"\n"))
        subprocess.run(["git", "add", "--", relative], cwd=repo,
                       capture_output=True, text=True, timeout=45, check=True)
    _verify_staged_patch(repo, paths, proposal["patch"])
    proposal["status"] = "applied"
    proposal["approved_by"] = actor
    proposal["approval_source"] = approval_source
    path.write_text(json.dumps(proposal, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
    _audit(state, {"event": "patch_applied", "id": proposal_id,
                   "sha256": sha256, "actor": actor, "source": approval_source})
    return {"id": proposal_id, "status": "applied", "approved_by": actor,
            "paths": paths}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=PILOT_REPO)
    parser.add_argument("--state", type=Path,
                        default=Path(os.environ.get("DEVCORE_LOCAL_ROOT", "")) / "AgentPilot")
    sub = parser.add_subparsers(dest="command", required=True)
    proposal = sub.add_parser("propose")
    proposal.add_argument("--file", required=True)
    proposal.add_argument("task")
    approval = sub.add_parser("approve")
    approval.add_argument("proposal_id")
    approval.add_argument("sha256")
    args = parser.parse_args()
    if not args.state.is_absolute() or not os.environ.get("DEVCORE_LOCAL_ROOT"):
        parser.error("Set an absolute DEVCORE_LOCAL_ROOT before using the pilot")
    try:
        result = (propose(args.repo, args.state, args.task, args.file) if args.command == "propose"
                  else approve(args.repo, args.state, args.proposal_id, args.sha256))
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        print(json.dumps({"status": "refused", "reason": str(exc)}))
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
