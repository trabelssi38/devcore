"""Render task mutations bound to the version in the displayed snapshot."""

import html
import json


def render_task_action_buttons(project, task_id, status, version):
    # JavaScript must represent the SQLite integer exactly before sending it back.
    available = type(version) is int and 1 <= version <= 2**53 - 1

    def button(action, label, icon):
        if available:
            invocation = (
                f"{action}({json.dumps(project)}, {json.dumps(task_id)}, event, {version})"
            )
            attributes = f"title='{label}' onclick='{html.escape(invocation, quote=True)}'"
        else:
            attributes = "disabled title='Version indisponible : action désactivée'"
        css = "btn-done" if action == "completeTask" else "btn-delete"
        return f"<button class='btn-action {css}' {attributes}>{icon}</button>"

    done = button("completeTask", "Clôturer", "&#10004;") if status != "done" else ""
    return done, button("deleteTask", "Supprimer", "&#128465;")
