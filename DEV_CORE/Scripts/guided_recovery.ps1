# guided_recovery.ps1 -- guided onboarding / diagnostic / recovery playbook
param(
    [ValidateSet("onboarding", "diagnostic", "recovery")]
    [string]$Flow = "onboarding",
    [switch]$List,
    [switch]$Json
)

$ErrorActionPreference = "Stop"

$DEV_CORE = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { Split-Path -Parent $PSScriptRoot }
$PLAYBOOK_PATH = Join-Path $DEV_CORE "Config\guided_recovery.json"

function Read-Playbook {
    if (-not (Test-Path -LiteralPath $PLAYBOOK_PATH)) {
        throw "Guided recovery playbook not found: $PLAYBOOK_PATH"
    }
    return Get-Content -LiteralPath $PLAYBOOK_PATH -Raw -Encoding UTF8 | ConvertFrom-Json
}

function Select-Flow {
    param($Playbook, [string]$Type)
    return @($Playbook.flows | Where-Object { $_.type -eq $Type } | Select-Object -First 1)[0]
}

$playbook = Read-Playbook

if ($List) {
    $result = [pscustomobject][ordered]@{
        ok = $true
        schema_version = $playbook.schema_version
        playbook_version = $playbook.playbook_version
        flows = @($playbook.flows | Select-Object id,type,title,description)
    }
    if ($Json) {
        $result | ConvertTo-Json -Depth 20
    } else {
        Write-Host "  DEV_CORE guided flows" -ForegroundColor Cyan
        foreach ($flowItem in $result.flows) {
            Write-Host ("  {0,-12} {1,-18} {2}" -f $flowItem.type, $flowItem.id, $flowItem.title) -ForegroundColor Gray
        }
    }
    exit 0
}

$selected = Select-Flow -Playbook $playbook -Type $Flow
if (-not $selected) {
    Write-Host "  Aucun flow guide pour: $Flow" -ForegroundColor Red
    exit 66
}

$response = [pscustomobject][ordered]@{
    ok = $true
    schema_version = $playbook.schema_version
    playbook_version = $playbook.playbook_version
    flow = $selected
    next_command = if (@($selected.steps).Count -gt 0) { [string]$selected.steps[0].command } else { "" }
}

if ($Json) {
    $response | ConvertTo-Json -Depth 30
} else {
    Write-Host ""
    Write-Host "  DEV_CORE guided $Flow -- $($selected.title)" -ForegroundColor Cyan
    Write-Host "  $($selected.description)" -ForegroundColor DarkGray
    Write-Host ""
    foreach ($step in @($selected.steps)) {
        Write-Host "  [$($step.id)] $($step.title)" -ForegroundColor White
        Write-Host "       command : $($step.command)" -ForegroundColor Gray
        Write-Host "       recovery: $($step.recovery_hint)" -ForegroundColor DarkGray
    }
    Write-Host ""
    Write-Host "  Next: $($response.next_command)" -ForegroundColor Green
}

exit 0
