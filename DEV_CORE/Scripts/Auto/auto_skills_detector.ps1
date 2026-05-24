# auto_skills_detector.ps1 -- DEV_CORE v7.3 Auto layer
$DEV_CORE      = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\devcore\DEV_CORE" }
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT)     { $env:DEVCORE_DATA_ROOT }     else { "C:\devcore\DEV_CORE_DATA" }
$TODAY         = Get-Date -Format "yyyy-MM-dd"
$LOG           = "$DEV_CORE_DATA\Logs\scripts\auto_skills_detector_$TODAY.log"
function Log { param($msg,$color="Gray"); $l="[$(Get-Date -f HH:mm:ss)] $msg"; Add-Content $LOG $l -ErrorAction SilentlyContinue; Write-Host "    $l" -ForegroundColor $color }
Log "auto_skills_detector -- scan patterns" "Cyan"
$regPath = "$DEV_CORE\Skills\skills_registry.json"
if (-not (Test-Path $regPath)) { Log "skills_registry.json absent" "Yellow"; exit 0 }
$reg = Get-Content $regPath | ConvertFrom-Json
# Mettre a jour last_checked
$reg | Add-Member -NotePropertyName "last_checked" -NotePropertyValue (Get-Date -Format "o") -Force
$reg | ConvertTo-Json -Depth 10 | Set-Content $regPath -Encoding UTF8
Log "Registry mis a jour -- $($reg.skills.Count) skills actifs" "Green"
