# Synchronise les tâches terminées d'un seul projet vers sa note Obsidian.
param(
    [Parameter(Mandatory=$true)]
    [ValidatePattern('^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$')]
    [ValidateNotNullOrEmpty()]
    [string]$Project
)

$ErrorActionPreference = 'Stop'
if (-not $env:DEVCORE_DATA_ROOT -or -not [IO.Path]::IsPathRooted($env:DEVCORE_DATA_ROOT)) {
    throw 'DEVCORE_DATA_ROOT absolu requis pour les notes projet.'
}
$platformRoot = if ($env:DEVCORE_PLATFORM_ROOT -and
    (Test-Path -LiteralPath (Join-Path $env:DEVCORE_PLATFORM_ROOT 'devcore_engine\cli.py') -PathType Leaf)) {
    [IO.Path]::GetFullPath($env:DEVCORE_PLATFORM_ROOT)
} else {
    [IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
}
if (-not $env:PYTHONPATH -or $env:PYTHONPATH -notlike "*$platformRoot*") {
    $env:PYTHONPATH = if ($env:PYTHONPATH) { "$platformRoot;$env:PYTHONPATH" } else { $platformRoot }
}
$pythonExe = if ($env:DEVCORE_PYTHON -and (Test-Path -LiteralPath $env:DEVCORE_PYTHON -PathType Leaf)) {
    $env:DEVCORE_PYTHON
} else {
    $pythonCommand = Get-Command python -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($pythonCommand) { $pythonCommand.Source }
}
if (-not $pythonExe) { throw 'Runtime Python DevCore introuvable.' }

$boardJson = & $pythonExe -m devcore_engine.cli task board --project $Project --json
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$board = ($boardJson | Out-String) | ConvertFrom-Json
if ($board.project -ne $Project) { throw 'Le board retourné ne correspond pas au projet demandé.' }

$today = Get-Date -Format 'yyyy-MM-dd'
$noteDir = Join-Path (Join-Path $env:DEVCORE_DATA_ROOT 'Vault\Daily Notes') $Project
$notePath = Join-Path $noteDir "$today.md"
$doneTasks = @($board.tasks | Where-Object { $_.status -eq 'done' })
$startMarker = '<!-- devcore:tasks:start -->'
$endMarker = '<!-- devcore:tasks:end -->'
$lines = @('## Taches accomplies', $startMarker)
foreach ($task in $doneTasks) { $lines += "- [x] **$($task.id)**: $($task.title)" }
$lines += $endMarker
$section = $lines -join "`n"

if (Test-Path -LiteralPath $notePath -PathType Leaf) {
    $note = Get-Content -LiteralPath $notePath -Raw -Encoding UTF8
    $startIndex = $note.IndexOf($startMarker, [StringComparison]::Ordinal)
    $endIndex = $note.IndexOf($endMarker, [StringComparison]::Ordinal)
    if ($startIndex -ge 0 -and $endIndex -gt $startIndex) {
        $prefix = $note.Substring(0, $startIndex)
        $suffix = $note.Substring($endIndex + $endMarker.Length)
        $generated = (($lines | Select-Object -Skip 1) -join "`n")
        $note = $prefix + $generated + $suffix
    } else {
        $note = $note.TrimEnd() + "`n`n" + $section + "`n"
    }
} else {
    $note = "---`ntitle: Daily Note $today`ndate: $today`nproject: $Project`n---`n`n# $today`n`n" + $section + "`n"
}

New-Item -ItemType Directory -Path $noteDir -Force | Out-Null
$temporary = Join-Path $noteDir ('.' + $today + '.' + [guid]::NewGuid().ToString('N') + '.tmp')
try {
    [IO.File]::WriteAllText($temporary, $note, [Text.UTF8Encoding]::new($false))
    Move-Item -LiteralPath $temporary -Destination $notePath -Force
} finally {
    if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary -Force }
}
Write-Host "  [OK] Note $Project : $($doneTasks.Count) taches terminees" -ForegroundColor Green
