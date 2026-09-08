# test_repowise_workspace_sync.ps1 -- Validate Repowise workspace auto-sync
param(
    [string]$WorkspaceYaml = ""
)

$ErrorActionPreference = "Stop"

if (-not $WorkspaceYaml -or -not (Test-Path $WorkspaceYaml)) {
    $defaultCandidate = (Resolve-Path "$PSScriptRoot\..\..\.repowise-workspace.yaml" -ErrorAction SilentlyContinue).Path
    if ($defaultCandidate -and (Test-Path $defaultCandidate)) {
        $WorkspaceYaml = $defaultCandidate
    } else {
        $WorkspaceYaml = "C:\devcore\.repowise-workspace.yaml"
    }
}

function Assert-True($condition, $message) {
    if (-not $condition) {
        throw "ASSERTION FAILED: $message"
    }
}

# 1. Run sync script
$syncScript = "$PSScriptRoot\sync_repowise_workspace.py"
Assert-True (Test-Path $syncScript) "sync_repowise_workspace.py script must exist"

$res = python $syncScript
Assert-True ($LASTEXITCODE -eq 0) "sync_repowise_workspace.py should exit with code 0"

# 2. Check workspace YAML content
Assert-True (Test-Path $WorkspaceYaml) "Repowise workspace YAML must exist after sync"
$content = Get-Content -LiteralPath $WorkspaceYaml -Raw

Assert-True ($content -match "path:\s*\.") "devcore primary repo must exist"
Assert-True ($content -match "alias:\s*devcore") "devcore alias must exist"
Assert-True ($content -match "last_commit_at_index:\s*[0-9a-fA-F]{7,40}") "last_commit_at_index must be synchronized from local repowise indices"

# 3. Simulate deleted folder and test pruning
$tempYaml = "$PSScriptRoot\temp_workspace.yaml"
@"
version: 1
default_repo: devcore
repos:
- path: .
  alias: devcore
  is_primary: true
- path: non_existent_deleted_project_folder_xyz
  alias: deleted_proj
"@ | Set-Content $tempYaml -Encoding UTF8

$env:DEVCORE_REPO_ROOT = "C:\devcore"
$pythonTest = @"
import sys
from pathlib import Path
sys.path.append(r'$PSScriptRoot')
import sync_repowise_workspace

sync_repowise_workspace.WORKSPACE_YAML = Path(r'$tempYaml')
sync_repowise_workspace.sync_workspace()
"@

python -c $pythonTest
Assert-True ($LASTEXITCODE -eq 0) "sync_workspace on temp yaml should exit with 0"

$prunedContent = Get-Content -LiteralPath $tempYaml -Raw
Remove-Item -LiteralPath $tempYaml -Force -ErrorAction SilentlyContinue

Assert-True ($prunedContent -notmatch "deleted_proj") "Obsolete deleted project must be pruned from workspace"

Write-Host "[OK] Repowise workspace auto-sync contract validated successfully"
