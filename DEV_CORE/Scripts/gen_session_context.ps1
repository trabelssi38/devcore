# gen_session_context.ps1 -- DEV_CORE v7.3
# Genere le fichier session_context.txt

$DEV_CORE = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\devcore\DEV_CORE" }
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT) { $env:DEVCORE_DATA_ROOT } else { "C:\devcore\DEV_CORE_DATA" }
$CONTEXT_FILE = "$DEV_CORE_DATA\Logs\scripts\session_context.txt"

$tFile = "$DEV_CORE_DATA\Memory\$(& "$PSScriptRoot\Get-ActiveProject.ps1")\tasks.json"
if (-not (Test-Path $tFile)) {
    Write-Host "tasks.json absent" -ForegroundColor Yellow
    exit 1
}

$board = Get-Content $tFile -Raw | ConvertFrom-Json
$active = $board.tasks | Where-Object { $_.status -eq "active" } | Select-Object -First 1

if (-not $active) {
    $done_ids = ($board.tasks | Where-Object { $_.status -eq "done" }).id
    $todo = $board.tasks | Where-Object {
        $_.status -eq "todo" -and (
            -not $_.depends_on -or $done_ids -contains $_.depends_on
        )
    } | Select-Object -First 1
    if ($todo) {
        $board.current_task = $todo.id
        $todo.status = "active"
        $board | ConvertTo-Json -Depth 10 | Set-Content $tFile -Encoding UTF8
        $active = $todo
        Write-Host "  [DEV_CORE] Activation auto: $($active.id)" -ForegroundColor Cyan
    }
}

if (-not $active) {
    Write-Host "  [DEV_CORE] Aucune tache active" -ForegroundColor Yellow
    @"
[DEV_CORE] Aucune tache active
[DEV_CORE] Commencer par: dc new task 'description' -mode reasoning|coding|bulk
"@ | Set-Content $CONTEXT_FILE -Encoding UTF8
    exit 0
}

$budget = switch ($active.mode) {
    "reasoning" { "32k" }
    "coding"    { "8k" }
    "bulk"      { "16k" }
    default     { "16k" }
}

# Ensure directory exists
$scriptDir = Split-Path -Parent $CONTEXT_FILE
if (-not (Test-Path $scriptDir)) {
    New-Item -ItemType Directory -Path $scriptDir -Force | Out-Null
}

$content = @"
[DEV_CORE] Task active : $($active.id)
[DEV_CORE] Titre  : $($active.title)
[DEV_CORE] Mode   : $($active.mode)
[DEV_CORE] Budget : $budget tokens
[DEV_CORE] Steps  : $($active.steps_done)/$($active.steps_total)
[DEV_CORE] Tag git: [$($active.id)]
"@

$content | Set-Content $CONTEXT_FILE -Encoding UTF8
Write-Host "  [DEV_CORE] Session context genere: $($active.id) - $($active.mode)" -ForegroundColor Green

