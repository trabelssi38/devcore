$ErrorActionPreference = "Stop"
$sourceRoot = Split-Path -Parent $PSScriptRoot
$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("devcore-new-project-" + [guid]::NewGuid().ToString("N"))
$saved = @{}
foreach ($name in @("DEVCORE_PLATFORM_ROOT", "DEVCORE_CONFIG_ROOT", "DEVCORE_DATA_ROOT")) {
    $saved[$name] = [System.Environment]::GetEnvironmentVariable($name, "Process")
}

try {
    $platform = Join-Path $tempRoot "platform"
    $scripts = Join-Path $platform "Scripts"
    $config = Join-Path $platform "Config"
    $data = Join-Path $tempRoot "shared"
    $project = Join-Path $tempRoot "project"
    New-Item -ItemType Directory -Path $scripts, $config, $data, $project -Force | Out-Null
    Copy-Item -LiteralPath (Join-Path $sourceRoot "Scripts\platform_version.ps1") -Destination $scripts
    Copy-Item -LiteralPath (Join-Path $sourceRoot "Scripts\new_project.ps1") -Destination $scripts
    Copy-Item -LiteralPath (Join-Path $sourceRoot "Config\platform.json") -Destination $config
    $env:DEVCORE_PLATFORM_ROOT = $platform
    $env:DEVCORE_CONFIG_ROOT = $config
    $env:DEVCORE_DATA_ROOT = $data

    & (Join-Path $scripts "new_project.ps1") -Name "alpha" -Path $project | Out-Null
    $boardPath = Join-Path $data "Memory\alpha\tasks.json"
    if (Test-Path -LiteralPath $boardPath) { throw "Default initialization wrote shared task board" }
    $metadata = Get-Content -LiteralPath (Join-Path $project ".devcore\project.json") -Raw | ConvertFrom-Json
    if ($metadata.name -ne "alpha") { throw "Wrong project metadata" }
    $registry = Get-Content -LiteralPath (Join-Path $config "projects.json") -Raw | ConvertFrom-Json
    if (@($registry.projects | Where-Object name -eq "alpha").Count -ne 1) { throw "Project not registered" }

    & (Join-Path $scripts "new_project.ps1") -Name "beta" -Path $project -InitializeLegacyTaskBoard | Out-Null
    $legacyPath = Join-Path $data "Memory\beta\tasks.json"
    if (-not (Test-Path -LiteralPath $legacyPath)) { throw "Explicit legacy board missing" }
    $legacy = Get-Content -LiteralPath $legacyPath -Raw
    & (Join-Path $scripts "new_project.ps1") -Name "beta" -Path $project -InitializeLegacyTaskBoard | Out-Null
    if ((Get-Content -LiteralPath $legacyPath -Raw) -ne $legacy) { throw "Existing legacy board changed" }

    Write-Host "[OK] New projects avoid shared task writes by default" -ForegroundColor Green
} finally {
    foreach ($name in $saved.Keys) {
        if ($null -eq $saved[$name]) { Remove-Item -Path ("Env:" + $name) -ErrorAction SilentlyContinue }
        else { Set-Item -Path ("Env:" + $name) -Value $saved[$name] }
    }
    if (Test-Path -LiteralPath $tempRoot) { Remove-Item -LiteralPath $tempRoot -Recurse -Force }
}
