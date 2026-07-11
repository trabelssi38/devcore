# auto_skills_detector.ps1 -- DEV_CORE v9.0 Auto layer
$DEV_CORE      = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\devcore\DEV_CORE" }
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT)     { $env:DEVCORE_DATA_ROOT }     else { "C:\devcore\DEV_CORE_DATA" }
$TODAY         = Get-Date -Format "yyyy-MM-dd"
$LOG           = "$DEV_CORE_DATA\Logs\scripts\auto_skills_detector_$TODAY.log"
function Log { param($msg,$color="Gray"); $l="[$(Get-Date -f HH:mm:ss)] $msg"; Add-Content $LOG $l -ErrorAction SilentlyContinue; Write-Host "    $l" -ForegroundColor $color }
Log "auto_skills_detector -- scan patterns" "Cyan"
$regPath = "$DEV_CORE\Skills\skills_registry.json"
$runtimeDir = "$DEV_CORE_DATA\Skills"
$runtimePath = "$runtimeDir\skills_runtime.json"
if (-not (Test-Path $regPath)) { Log "skills_registry.json absent" "Yellow"; exit 0 }
$reg = Get-Content $regPath -Raw -Encoding UTF8 | ConvertFrom-Json

New-Item -ItemType Directory -Path $runtimeDir -Force | Out-Null
$now = Get-Date -Format "o"
$existing = @{}
if (Test-Path $runtimePath) {
    try {
        $runtime = Get-Content $runtimePath -Raw -Encoding UTF8 | ConvertFrom-Json
        foreach ($skill in @($runtime.skills)) {
            if ($skill.id) { $existing[[string]$skill.id] = $skill }
        }
    } catch {}
}

$runtimeSkills = @()
foreach ($skill in @($reg.skills)) {
    $id = [string]$skill.id
    if ([string]::IsNullOrWhiteSpace($id)) { continue }
    $previous = if ($existing.ContainsKey($id)) { $existing[$id] } else { $null }
    $runtimeSkills += [pscustomobject][ordered]@{
        id = $id
        last_checked = $now
        last_used = if ($previous -and $previous.PSObject.Properties["last_used"]) { $previous.last_used } elseif ($skill.PSObject.Properties["last_used"]) { $skill.last_used } else { $null }
        usage_count = if ($previous -and $previous.PSObject.Properties["usage_count"]) { [int]$previous.usage_count } elseif ($skill.PSObject.Properties["usage_count"]) { [int]$skill.usage_count } else { 0 }
    }
}

[pscustomobject][ordered]@{
    schema_version = 1
    generated_at = $now
    source_registry = $regPath
    skills_count = @($runtimeSkills).Count
    skills = $runtimeSkills
} | ConvertTo-Json -Depth 10 | Set-Content $runtimePath -Encoding UTF8

Log "Registry lu -- $($reg.skills.Count) skills actifs; runtime mis a jour : $runtimePath" "Green"
