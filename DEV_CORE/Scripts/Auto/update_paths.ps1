# Historical one-shot source rewriter. Disabled because it rewrites installed
# scripts through a hard-coded machine path and reintroduces implicit project
# selection. Use the current project-scoped adapters or an explicit import on a
# copy of legacy data.
[Console]::Error.WriteLine(
    "Legacy source rewriter disabled; use project-scoped adapters or an explicit import on a copy."
)
exit 2
