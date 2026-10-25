"""Opt-in DevCore agent pilot: read-only proposal, exact human-approved patch.

This entry point is deliberately not connected to task_sync or a schedule.
Only the dedicated pilot checkout may be used. The Codex subprocess has a
read-only sandbox; applying its proposal is a separate interactive operation.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
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
MAX_PROPOSALS_PER_DAY = 3
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


def _digest(payload: dict) -> str:
    source = {key: payload[key] for key in ("project", "base", "task", "summary", "patch")}
    encoded = json.dumps(source, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _apply_check(repo: Path, patch: str) -> None:
    result = subprocess.run(["git", "apply", "--check", "--index", "-"],
                            cwd=repo, input=patch, text=True, capture_output=True,
                            timeout=45, check=False)
    if result.returncode:
        raise ValueError("Patch does not apply: " + result.stderr.strip()[:500])


def _audit(state: Path, event: dict) -> None:
    state.mkdir(parents=True, exist_ok=True)
    record = {"at_utc": datetime.now(timezone.utc).isoformat(), **event}
    with (state / "audit.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def _enforce_daily_quota(state: Path) -> None:
    log = state / "audit.jsonl"
    if not log.exists():
        return
    today = datetime.now(timezone.utc).date().isoformat()
    attempts = 0
    for line in log.read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        if not isinstance(event, dict) or "at_utc" not in event:
            raise ValueError("Invalid pilot audit log")
        if event.get("event") == "proposal_started" and event["at_utc"].startswith(today):
            attempts += 1
    if attempts >= MAX_PROPOSALS_PER_DAY:
        raise ValueError("Daily pilot proposal quota exhausted")


def propose(repo: Path, state: Path, task: str, *, codex: str = "codex") -> dict:
    repo, base = _repo(repo)
    state = state.resolve()
    if state.is_relative_to(repo):
        raise ValueError("Pilot state must be outside the repository")
    if not task.strip() or len(task.encode("utf-8")) > MAX_TASK_BYTES:
        raise ValueError("Task missing or exceeds pilot quota")
    state.mkdir(parents=True, exist_ok=True)
    _enforce_daily_quota(state)
    proposal_id = uuid4().hex
    _audit(state, {"event": "proposal_started", "id": proposal_id,
                   "base": base, "project": PROJECT})
    schema = state / f"{proposal_id}.schema.json"
    output = state / f"{proposal_id}.response.json"
    schema.write_text(json.dumps({
        "type": "object", "additionalProperties": False,
        "required": ["summary", "patch"],
        "properties": {"summary": {"type": "string"}, "patch": {"type": "string"}},
    }), encoding="utf-8")
    prompt = ("Project devcore. Inspect this checkout read-only. Propose a minimal "
              "unified git diff editing existing text files under DEV_CORE only. "
              "Do not modify files. Return JSON with summary and patch. "
              "If no safe edit is possible, return an empty patch.\n\nTask:\n" + task)
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
        if not isinstance(response, dict) or set(response) != {"summary", "patch"}:
            raise ValueError("Invalid Codex proposal structure")
        if not all(isinstance(value, str) for value in response.values()):
            raise ValueError("Invalid Codex proposal values")
        paths = _patch_paths(response["patch"])
        for path in paths:
            if not (_git(repo, "ls-files", "--", path) == path):
                raise ValueError("Proposal touches an untracked file")
        _apply_check(repo, response["patch"])
        payload = {"project": PROJECT, "base": base, "task": task,
                   "summary": response["summary"], "patch": response["patch"]}
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


def approve(repo: Path, state: Path, proposal_id: str, sha256: str) -> dict:
    if not re.fullmatch(r"[0-9a-f]{32}", proposal_id):
        raise ValueError("Invalid proposal id")
    path = state / f"{proposal_id}.json"
    proposal = json.loads(path.read_text(encoding="utf-8"))
    if (proposal.get("id") != proposal_id or proposal.get("project") != PROJECT or
            proposal.get("status") != "waiting_approval" or
            proposal.get("sha256") != sha256 or _digest(proposal) != sha256):
        raise ValueError("Proposal identity or hash mismatch")
    repo, base = _repo(repo)
    state = state.resolve(strict=True)
    if state.is_relative_to(repo):
        raise ValueError("Pilot state must be outside the repository")
    if base != proposal["base"]:
        raise ValueError("Pilot checkout changed since proposal")
    paths = _patch_paths(proposal["patch"])
    if paths != proposal["paths"]:
        raise ValueError("Proposal paths changed")
    if not sys.stdin.isatty():
        raise ValueError("Interactive human approval is required")
    print(f"Files: {', '.join(paths)}\nSummary: {proposal['summary']}")
    print(proposal["patch"])
    confirmation = input(f"Type APPLY {sha256} to approve this exact patch: ")
    if confirmation != f"APPLY {sha256}":
        raise ValueError("Approval phrase does not match proposal hash")
    _apply_check(repo, proposal["patch"])
    actor = getpass.getuser()
    _audit(state, {"event": "human_approved", "id": proposal_id,
                   "sha256": sha256, "actor": actor})
    subprocess.run(["git", "apply", "--index", "-"], cwd=repo,
                   input=proposal["patch"], text=True, capture_output=True,
                   timeout=45, check=True)
    proposal["status"] = "applied"
    proposal["approved_by"] = actor
    path.write_text(json.dumps(proposal, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
    _audit(state, {"event": "patch_applied", "id": proposal_id,
                   "sha256": sha256, "actor": actor})
    return {"id": proposal_id, "status": "applied", "approved_by": actor,
            "paths": paths}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=PILOT_REPO)
    parser.add_argument("--state", type=Path,
                        default=Path(os.environ.get("DEVCORE_LOCAL_ROOT", "")) / "AgentPilot")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("propose").add_argument("task")
    approval = sub.add_parser("approve")
    approval.add_argument("proposal_id")
    approval.add_argument("sha256")
    args = parser.parse_args()
    if not args.state.is_absolute() or not os.environ.get("DEVCORE_LOCAL_ROOT"):
        parser.error("Set an absolute DEVCORE_LOCAL_ROOT before using the pilot")
    try:
        result = (propose(args.repo, args.state, args.task) if args.command == "propose"
                  else approve(args.repo, args.state, args.proposal_id, args.sha256))
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        print(json.dumps({"status": "refused", "reason": str(exc)}))
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
