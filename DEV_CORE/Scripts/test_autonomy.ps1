# test_autonomy.ps1 -- DEV_CORE -- Test d'integration autonomie
# Simule un cycle complet : projet -> tache -> steps -> done -> chainage
# Usage : powershell -File test_autonomy.ps1

$DEV_CORE      = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { Split-Path -Parent $PSScriptRoot }
if ($DEV_CORE -match '[/\\]Scripts[/\\]?$') {
    $DEV_CORE = Split-Path -Parent $DEV_CORE
}
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT)     { $env:DEVCORE_DATA_ROOT }     else { (Join-Path (Split-Path -Parent $PSScriptRoot) "DEV_CORE_DATA") }
. "$DEV_CORE\Scripts\platform_version.ps1"
$PLATFORM = Get-DevCorePlatformInfo
$tFile         = "$DEV_CORE_DATA\Memory\$(& "$PSScriptRoot\Get-ActiveProject.ps1")\tasks.json"
$passed = 0; $failed = 0

function Assert {
    param($label, $condition)
    if ($condition) {
        Write-Host "  [PASS] $label" -ForegroundColor Green; $script:passed++
    } else {
        Write-Host "  [FAIL] $label" -ForegroundColor Red; $script:failed++
    }
}

Write-Host ""
Write-Host "  $($PLATFORM.title) -- Test Autonomie" -ForegroundColor Cyan
Write-Host "  ================================" -ForegroundColor DarkGray
Write-Host ""

# Backup tasks.json original
$backup = $null
if (Test-Path $tFile) {
    $backup = Get-Content $tFile -Raw
}

try {
    # 1. Creer un board de test
    Write-Host "  --- Setup ---" -ForegroundColor DarkGray
    $testBoard = @{
        project = "test-autonomy"
        current_task = $null
        tasks = @(
            @{
                id = "T-TEST-01"
                title = "Test task 1"
                mode = "coding"
                status = "todo"
                steps_total = 2
                steps_done = 0
                depends_on = $null
                steps = @(
                    @{ id = 1; title = "Step 1"; done = $false },
                    @{ id = 2; title = "Step 2"; done = $false }
                )
            },
            @{
                id = "T-TEST-02"
                title = "Test task 2"
                mode = "reasoning"
                status = "todo"
                steps_total = 1
                steps_done = 0
                depends_on = "T-TEST-01"
                steps = @(
                    @{ id = 1; title = "Step 1"; done = $false }
                )
            }
        )
    }
    $testBoard | ConvertTo-Json -Depth 10 | Set-Content $tFile -Encoding UTF8

    # 2. Test task_next active la premiere tache
    Write-Host "  --- Test task_next ---" -ForegroundColor DarkGray
    & "$DEV_CORE\Scripts\task_next.ps1" 2>&1 | Out-Null
    $board = Get-Content $tFile -Raw | ConvertFrom-Json
    $t1 = $board.tasks | Where-Object { $_.id -eq "T-TEST-01" }
    Assert "task_next active T-TEST-01" ($t1.status -eq "active")
    Assert "current_task = T-TEST-01" ($board.current_task -eq "T-TEST-01")

    # 3. Test step done
    Write-Host "  --- Test step done ---" -ForegroundColor DarkGray
    & "$DEV_CORE\Scripts\task_step_done.ps1" -StepNumber 1 2>&1 | Out-Null
    $board = Get-Content $tFile -Raw | ConvertFrom-Json
    $t1 = $board.tasks | Where-Object { $_.id -eq "T-TEST-01" }
    Assert "Step 1 marquee done" ($t1.steps[0].done -eq $true)
    Assert "steps_done = 1" ($t1.steps_done -eq 1)
    Assert "Status toujours active" ($t1.status -eq "active")

    # 4. Test step done 2 -> auto-complete
    Write-Host "  --- Test auto-complete ---" -ForegroundColor DarkGray
    & "$DEV_CORE\Scripts\task_step_done.ps1" -StepNumber 2 2>&1 | Out-Null
    $board = Get-Content $tFile -Raw | ConvertFrom-Json
    $t1 = $board.tasks | Where-Object { $_.id -eq "T-TEST-01" }
    Assert "T-TEST-01 auto-done" ($t1.status -eq "done")
    Assert "steps_done = 2" ($t1.steps_done -eq 2)

    # 5. Test auto-chainage : T-TEST-02 devrait etre active
    $t2 = $board.tasks | Where-Object { $_.id -eq "T-TEST-02" }
    Assert "Auto-chainage : T-TEST-02 active" ($t2.status -eq "active")

    # 6. Test integrity check
    Write-Host "  --- Test integrity ---" -ForegroundColor DarkGray
    # Corrompre volontairement
    $t2.steps_done = 99
    $board | ConvertTo-Json -Depth 10 | Set-Content $tFile -Encoding UTF8
    & "$DEV_CORE\Scripts\diagnose.ps1" -Fix 2>&1 | Out-Null
    $board = Get-Content $tFile -Raw | ConvertFrom-Json
    $t2 = $board.tasks | Where-Object { $_.id -eq "T-TEST-02" }
    Assert "Integrity fix : steps_done corrige" ($t2.steps_done -le $t2.steps_total)

    # 7. Test backup existe
    Write-Host "  --- Test backup ---" -ForegroundColor DarkGray
    $bkps = Get-ChildItem "$DEV_CORE_DATA\Backups\auto\tasks_*.json" -ErrorAction SilentlyContinue
    Assert "Auto-backup tasks.json cree" ($bkps.Count -gt 0)

} finally {
    # Restaurer tasks.json original
    Write-Host "  --- Cleanup ---" -ForegroundColor DarkGray
    if ($backup) {
        $backup | Set-Content $tFile -Encoding UTF8
        Write-Host "  [OK] tasks.json restaure" -ForegroundColor Gray
    }
}

Write-Host ""
Write-Host "  ================================" -ForegroundColor DarkGray
Write-Host "  PASS: $passed  |  FAIL: $failed" -ForegroundColor White
Write-Host ""
if ($failed -eq 0) {
    Write-Host "  AUTONOMIE 100% VALIDEE" -ForegroundColor Green
} else {
    Write-Host "  $failed tests en echec -- corriger avant deploiement" -ForegroundColor Red
}
Write-Host ""

if ($failed -gt 0) { exit 1 }
exit 0
