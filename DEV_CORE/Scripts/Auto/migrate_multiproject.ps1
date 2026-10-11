# Historical in-place JSON mover. Disabled because it inferred a project and
# moved active data without reconciliation or a recoverable import report.
[Console]::Error.WriteLine(
    "Legacy in-place migration disabled; use the explicit import workflow on a verified copy."
)
exit 2
