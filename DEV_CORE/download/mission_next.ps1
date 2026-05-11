# mission_next.ps1 -- DEV_CORE v6 -- ASCII safe
$DEV_CORE      = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\DEV_CORE" }
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT)     { $env:DEVCORE_DATA_ROOT }     else { "C:\DEV_CORE_DATA" }
$mFile = "$DEV_CORE_DATA\Memory\missions.json"

if (-not (Test-Path $mFile)) {
    Write-Host "  Aucun missions.json -- dc new mission 'titre'" -ForegroundColor Yellow
    exit 0
}

$board = Get-Content $mFile -Raw | ConvertFrom-Json

$current = $board.missions | Where-Object { $_.status -eq "active" } | Select-Object -First 1

if (-not $current) {
    $done_ids = ($board.missions | Where-Object { $_.status -eq "done" }).id
    $current  = $board.missions | Where-Object {
        $_.status -eq "todo" -and (
            -not $_.depends_on -or
            $done_ids -contains $_.depends_on
        )
    } | Select-Object -First 1
}

if (-not $current) {
    $done  = ($board.missions | Where-Object { $_.status -eq "done" }).Count
    $total = $board.missions.Count
    if ($done -eq $total -and $total -gt 0) {
        Write-Host "  Toutes les missions accomplies !" -ForegroundColor Green
    } else {
        Write-Host "  Aucune mission disponible -- verifier les dependances (dc ms)" -ForegroundColor Yellow
    }
    exit 0
}

# Activer la mission si todo
if ($current.status -eq "todo") {
    $current.status = "active"
    $current | Add-Member -NotePropertyName "started_at" -NotePropertyValue (Get-Date -Format "o") -Force
    $board.current_mission = $current.id
}

# Adapter le client
$client = $current.agent
if ($client -eq "antigravity") { $client = "gemini" }
$board.active_client = $client
$board | ConvertTo-Json -Depth 10 | Set-Content $mFile -Encoding UTF8

# Adapter le client DEV_CORE
& "$DEV_CORE\Scripts\adapt_client.ps1" -Client $client | Out-Null

# Mission suivante
$next = $board.missions | Where-Object {
    $_.status -eq "todo" -and $_.id -ne $current.id
} | Select-Object -First 1

# Affichage
Write-Host ""
Write-Host "  +------------------------------------------+" -ForegroundColor Cyan
Write-Host "  |  MISSION $($current.id.PadRight(32))  |" -ForegroundColor Cyan
Write-Host "  +------------------------------------------+" -ForegroundColor Cyan
Write-Host "  |  $($current.title.PadRight(40))  |" -ForegroundColor White
Write-Host "  +------------------------------------------+" -ForegroundColor Cyan
Write-Host "  |  Agent  : $($current.agent.PadRight(31))|" -ForegroundColor Gray
Write-Host "  |  Steps  : $("$($current.steps_done)/$($current.steps_total)".PadRight(31))|" -ForegroundColor Gray
if ($next) {
    Write-Host "  |  Suivant: $("$($next.id) -> $($next.agent)".PadRight(31))|" -ForegroundColor DarkGray
}
Write-Host "  +------------------------------------------+" -ForegroundColor Cyan
Write-Host ""

# Prompt d'ouverture selon l'agent
Write-Host "  Prompt d'ouverture :" -ForegroundColor DarkGray
Write-Host "  +------------------------------------------+" -ForegroundColor DarkGray

if ($current.agent -eq "claude") {
    $p = "Lis session_context.txt et last_handoff.md. Charge dev-methodology skill. Mission $($current.id) : brainstorm si nouvelle spec, attends validation."
} elseif ($current.agent -eq "codex") {
    $p = "Lis session_context.txt et last_handoff.md. TDD. Commit tag [$($current.id)] apres chaque etape. dc mv quand done."
} elseif ($current.agent -eq "antigravity" -or $current.agent -eq "gemini") {
    $p = "Lis session_context.txt et last_handoff.md. Mode bulk -- genere tout sans validation intermediaire. Fabric-patterns pour la structure."
} else {
    $p = "Lis session_context.txt et last_handoff.md. Execute la mission $($current.id)."
}

Write-Host "  |  $($p.Substring(0, [Math]::Min($p.Length, 40)).PadRight(40))  |" -ForegroundColor White
if ($p.Length -gt 40) {
    $p2 = $p.Substring(40)
    Write-Host "  |  $($p2.Substring(0, [Math]::Min($p2.Length, 40)).PadRight(40))  |" -ForegroundColor White
    if ($p2.Length -gt 40) {
        $p3 = $p2.Substring(40)
        Write-Host "  |  $($p3.PadRight(40))  |" -ForegroundColor White
    }
}
Write-Host "  +------------------------------------------+" -ForegroundColor DarkGray
Write-Host ""

# Ecrire le contexte pour les hooks
$ctx = @"
[DEV_CORE] Mission active : $($current.id)
[DEV_CORE] Titre  : $($current.title)
[DEV_CORE] Agent  : $($current.agent)
[DEV_CORE] Steps  : $($current.steps_done)/$($current.steps_total)
[DEV_CORE] Client : $client
[DEV_CORE] Tag git: [$($current.id)]
"@
$ctx | Set-Content "$DEV_CORE_DATA\Logs\scripts\session_context.txt" -Encoding UTF8
