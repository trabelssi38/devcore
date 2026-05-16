# Dashboard Multi-Project Implementation

## Goal
Update the DEV_CORE HTML dashboard to dynamically display the status of all active projects simultaneously, replacing the current static mockup.

## Tasks
- [x] Task 1: Create `gen_dashboard.ps1` in `Scripts\` that iterates through `C:\devcore\DEV_CORE_DATA\Memory\*` to detect all active projects.
  - **Verify**: Run `.\gen_dashboard.ps1`, it should output the list of detected project folders.
- [x] Task 2: Implement JSON parsing in `gen_dashboard.ps1` to extract task data from each project's `tasks.json` (Project Name, Active Task ID, Active Client, Completion percentage).
  - **Verify**: The script successfully builds a PowerShell array/object representing the state of all projects.
- [x] Task 3: Refactor the current `index.html` into a template file (`Dashboard\template.html`), replacing hardcoded HTML blocks with injection tokens (e.g., `{{PROJECT_CARDS}}` and `{{TASKS_PIPELINE}}`).
  - **Verify**: `template.html` exists and no longer contains hardcoded task data.
- [x] Task 4: Update `gen_dashboard.ps1` to generate HTML blocks from the parsed JSON data, inject them into `template.html`, and output the final `index.html`.
  - **Verify**: Running the script generates a valid `index.html` that visually displays accurate real-time data for all local projects.
- [x] Task 5: Add a hook to call `gen_dashboard.ps1` at the end of key scripts (`task_add.ps1`, `task_next.ps1`, `task_done.ps1`, `task_step_done.ps1`) to ensure the dashboard is always up-to-date.
  - **Verify**: Completing a step via `dc task step done` automatically updates the `index.html` file on disk.

## Done When
- [x] `index.html` is dynamically generated.
- [x] Multiple projects are displayed on the dashboard if they exist in the `Memory` directory.
- [x] The dashboard updates automatically when task states change via the `dc` CLI.
