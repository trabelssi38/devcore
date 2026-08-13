# gateway.ps1 -- DEV_CORE v10 -- typed command gateway
param(
    [string]$Command = "",
    [switch]$List,
    [switch]$Json
)

$DEV_CORE = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { Split-Path -Parent $PSScriptRoot }
if ($DEV_CORE -match '[/\\]Scripts[/\\]?$') {
    $DEV_CORE = Split-Path -Parent $DEV_CORE
}
$SCRIPTS = Join-Path $DEV_CORE "Scripts"

$commandMap = [ordered]@{
    "check" = @{
        script = "diagnose.ps1"
        parameters = @{}
        description = "Diagnostic complet"
    }
    "check --fix" = @{
        script = "diagnose.ps1"
        parameters = @{ Fix = $true }
        description = "Diagnostic avec reparations"
    }
    "check --gate" = @{
        script = "diagnose.ps1"
        parameters = @{ Gate = $true }
        description = "Diagnostic release gate"
    }
    "check --fix --gate" = @{
        script = "diagnose.ps1"
        parameters = @{ Fix = $true; Gate = $true }
        description = "Diagnostic avec reparations et release gate"
    }
    "check --fix --dry-run" = @{
        script = "diagnose.ps1"
        parameters = @{ Fix = $true; DryRun = $true }
        description = "Simulation des reparations diagnostic"
    }
    "check --fix --gate --dry-run" = @{
        script = "diagnose.ps1"
        parameters = @{ Fix = $true; Gate = $true; DryRun = $true }
        description = "Simulation des reparations avec release gate"
    }
    "health" = @{
        script = "health_report.ps1"
        parameters = @{}
        description = "Rapport health court"
    }
    "health --json" = @{
        script = "health_report.ps1"
        parameters = @{ Json = $true }
        description = "Rapport health JSON"
    }
    "verify --ci" = @{
        script = "verify.ps1"
        parameters = @{ Ci = $true }
        description = "Gate CI deterministe"
    }
    "verify --ci --json" = @{
        script = "verify.ps1"
        parameters = @{ Ci = $true; Json = $true }
        description = "Gate CI deterministe JSON"
    }
    "guide onboarding" = @{
        script = "guided_recovery.ps1"
        parameters = @{ Flow = "onboarding" }
        description = "Guide premier lancement"
    }
    "guide onboarding --json" = @{
        script = "guided_recovery.ps1"
        parameters = @{ Flow = "onboarding"; Json = $true }
        description = "Guide premier lancement JSON"
    }
    "guide diagnostic" = @{
        script = "guided_recovery.ps1"
        parameters = @{ Flow = "diagnostic" }
        description = "Guide diagnostic runtime"
    }
    "guide diagnostic --json" = @{
        script = "guided_recovery.ps1"
        parameters = @{ Flow = "diagnostic"; Json = $true }
        description = "Guide diagnostic runtime JSON"
    }
    "guide recovery" = @{
        script = "guided_recovery.ps1"
        parameters = @{ Flow = "recovery" }
        description = "Guide recovery non destructif"
    }
    "guide recovery --json" = @{
        script = "guided_recovery.ps1"
        parameters = @{ Flow = "recovery"; Json = $true }
        description = "Guide recovery non destructif JSON"
    }
    "guide list" = @{
        script = "guided_recovery.ps1"
        parameters = @{ List = $true }
        description = "Liste les guides disponibles"
    }
    "guide list --json" = @{
        script = "guided_recovery.ps1"
        parameters = @{ List = $true; Json = $true }
        description = "Liste les guides disponibles JSON"
    }
}

$aliases = @{
    "check --gate --fix" = "check --fix --gate"
    "check --dry-run --fix" = "check --fix --dry-run"
    "check --fix --dry-run --gate" = "check --fix --gate --dry-run"
    "check --gate --fix --dry-run" = "check --fix --gate --dry-run"
    "check --gate --dry-run --fix" = "check --fix --gate --dry-run"
    "check --dry-run --fix --gate" = "check --fix --gate --dry-run"
    "check --dry-run --gate --fix" = "check --fix --gate --dry-run"
    "verify --json --ci" = "verify --ci --json"
    "guide --json" = "guide list --json"
    "guide" = "guide list"
    "guide --list" = "guide list"
    "guide --list --json" = "guide list --json"
    "guide --json --list" = "guide list --json"
}

function Normalize-Command {
    param([string]$Value)
    return (($Value -replace "\s+", " ").ToLowerInvariant()).Trim()
}

function Get-CommandRecords {
    $records = @()
    foreach ($name in $commandMap.Keys) {
        $entry = $commandMap[$name]
        $records += [pscustomobject]@{
            command = $name
            script = $entry["script"]
            args = @($entry["parameters"].Keys | ForEach-Object { "-$_" })
            description = $entry["description"]
        }
    }
    return $records
}

if ($List) {
    $records = Get-CommandRecords
    if ($Json) {
        [pscustomobject]@{ commands = $records } | ConvertTo-Json -Depth 6
    } else {
        foreach ($record in $records) {
            Write-Host ("  {0,-30} {1}" -f $record.command, $record.description)
        }
    }
    exit 0
}

$normalized = Normalize-Command -Value $Command
if ($aliases.ContainsKey($normalized)) {
    $normalized = $aliases[$normalized]
}

if (-not $commandMap.Contains($normalized)) {
    Write-Host "  Gateway: commande invalide '$Command'" -ForegroundColor Red
    Write-Host "  Utiliser: gateway.ps1 -List" -ForegroundColor DarkGray
    exit 64
}

$selected = $commandMap[$normalized]
$target = Join-Path $SCRIPTS $selected["script"]
if (-not (Test-Path -LiteralPath $target)) {
    Write-Host "  Gateway: script introuvable $target" -ForegroundColor Red
    exit 66
}

$targetParameters = $selected["parameters"]
& $target @targetParameters
$targetExitCode = $LASTEXITCODE
if ($null -eq $targetExitCode) { $targetExitCode = 0 }
exit $targetExitCode
