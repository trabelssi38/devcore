"""Project-scoped associations for the Cockpit's task interaction view."""

from collections import defaultdict
import json
import re


def task_identity(project, task_id):
    if not isinstance(project, str) or not project.strip():
        return None
    if not isinstance(task_id, str) or not task_id.strip():
        return None
    return project.strip(), task_id.strip().upper()


def index_task_events(rows):
    events = defaultdict(list)
    subjects = defaultdict(set)
    for row in rows:
        _, event_type, project, task_id, raw_payload, created_at = row
        try:
            payload = json.loads(raw_payload) if isinstance(raw_payload, str) else raw_payload
        except (ValueError, TypeError):
            payload = None
        if not task_id and isinstance(payload, dict):
            task_id = payload.get("task_id")
        identity = task_identity(project, task_id)
        # Historical events without an explicit project cannot be attributed.
        if identity is None:
            continue
        details = (
            payload.get("commit_msg") or payload.get("title") or event_type
        ) if isinstance(payload, dict) else str(payload if payload is not None else event_type)
        events[identity].append({
            "event_type": event_type, "created_at": created_at, "details": details
        })
        if isinstance(payload, dict):
            for field in ("commit_msg", "title"):
                subject = payload.get(field)
                if isinstance(subject, str) and subject.strip():
                    subjects[(identity[0], subject.strip().casefold())].add(identity)
    return dict(events), dict(subjects)


def repository_project(repo_root):
    """Read only a manifest at this root, never a global or parent preference."""
    try:
        name = json.loads((repo_root / ".devcore" / "project.json").read_text(encoding="utf-8-sig"))["name"]
    except (OSError, UnicodeError, ValueError, KeyError, TypeError):
        return None
    if not isinstance(name, str) or not name.strip():
        return None
    name = name.strip()
    if any(part in name for part in ("/", "\\", ":", "..")):
        return None
    return name


def index_git_files(log_text, project, projects, event_subjects):
    """Associate one repository's files only with unambiguous tasks of its project."""
    if not isinstance(project, str) or not project:
        return {}
    visible = set()
    subjects = defaultdict(set)
    for board in projects:
        if board["name"] != project:
            continue
        for task in board.get("tasks", []):
            identity = task_identity(project, task.get("id"))
            if identity is None:
                continue
            visible.add(identity)
            title = task.get("title")
            if isinstance(title, str) and title.strip():
                subjects[title.strip().casefold()].add(identity)
    for (subject_project, subject), identities in event_subjects.items():
        if subject_project == project:
            subjects[subject].update(identity for identity in identities if identity in visible)
    files = defaultdict(list)
    current = None
    for line in log_text.splitlines():
        line = line.strip()
        if not line:
            continue
        if re.match(r"^[0-9a-f]{7,40}\s", line):
            subject = line.split(" ", 1)[1]
            tags = set(re.findall(r"\bT-(?:\d+|GIT-[A-Za-z0-9]+)\b", subject, re.IGNORECASE))
            candidates = {task_identity(project, tag) for tag in tags} if tags else subjects.get(subject.casefold(), set())
            current = next(iter(candidates)) if len(candidates) == 1 else None
            if current not in visible:
                current = None
        elif current is not None and line not in files[current]:
            files[current].append(line)
    return dict(files)


def scoped_task_metrics(metrics, project, task_id):
    """Accept legacy numeric padding, but never a task-only metrics key."""
    if not isinstance(metrics, dict):
        return None
    candidates = [task_id]
    if re.fullmatch(r"T-\d+", task_id, re.IGNORECASE):
        number = int(task_id[2:])
        candidates.extend((f"T-{number}", f"T-{number:02d}"))
    for candidate in candidates:
        key = f"{project}_{candidate}"
        if key in metrics:
            return metrics[key]
        # Project identity stays exact; only the task id has case tolerance.
        for source_key, value in metrics.items():
            if isinstance(source_key, str) and source_key.startswith(project + "_") and source_key.casefold() == key.casefold():
                return value
    return None
