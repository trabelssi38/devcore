 param(
    [string]$Python = 'E:/DevCoreRuntime/releases/devcore-py31316-20261011-l9-runfix/Scripts/python.exe'
 )

 $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
 $principal = [Security.Principal.WindowsPrincipal]::new($identity)
 $admin = [Security.Principal.WindowsBuiltInRole]::Administrator
 if (-not $principal.IsInRole($admin)) {
     Write-Error 'Run PowerShell as Administrator before launching this script.'
     exit 740
 }
 if (-not (Test-Path -LiteralPath $Python)) {
     Write-Error "Python de recette absent : $Python"
     exit 2
 }
 $repo = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
 Set-Location $repo
 & $Python 'DEV_CORE/Scripts/run_windows_pytest.py' -q `
     'DEV_CORE/tests/test_individual_candidate_launcher.py::test_isolated_preflight_forces_individual_and_keeps_private_store_unchanged' `
     'DEV_CORE/tests/test_individual_candidate_launcher.py::test_launched_snapshot_authenticates_projects_and_records_actor'
 exit $LASTEXITCODE
