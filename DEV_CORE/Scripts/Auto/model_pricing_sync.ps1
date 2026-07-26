# model_pricing_sync.ps1 - DEV_CORE model pricing synchronization
param(
    [switch]$Apply,
    [switch]$FailOnChange,
    [switch]$AllowMediumConfidence,
    [string]$Source
)

$DEV_CORE = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { (Split-Path -Parent $PSScriptRoot) }
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT) { $env:DEVCORE_DATA_ROOT } else { (Join-Path (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)) "DEV_CORE_DATA") }
$registry = "$DEV_CORE\Config\model_pricing.json"
$report = "$DEV_CORE_DATA\Logs\pricing\model_pricing_sync_report.json"

$argsList = @(
    "$DEV_CORE\Scripts\Auto\model_pricing_sync.py",
    "--registry", $registry,
    "--report-out", $report
)

if ($Apply) { $argsList += "--apply" }
if ($FailOnChange) { $argsList += "--fail-on-change" }
if ($AllowMediumConfidence) { $argsList += "--allow-medium-confidence" }
if ($Source) { $argsList += @("--source", $Source) }

& python @argsList
exit $LASTEXITCODE
