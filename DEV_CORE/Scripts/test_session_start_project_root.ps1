$ErrorActionPreference = "Stop"
$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("devcore-session-root-" + [guid]::NewGuid().ToString("N"))
$savedLocation = (Get-Location).Path
$saved = @{}
foreach ($name in @("DEVCORE_PLATFORM_ROOT", "DEVCORE_LOCAL_ROOT", "DEVCORE_DATA_ROOT", "DCC_INIT_RECORD")) {
    $saved[$name] = [System.Environment]::GetEnvironmentVariable($name, "Process")
}

try {
    $platform = Join-Path $tempRoot "platform"
    $scripts = Join-Path $platform "Scripts"
    $local = Join-Path $tempRoot "local"
    $shared = Join-Path $tempRoot "shared"
    $project = Join-Path $tempRoot "project"
    $nested = Join-Path $project "src\module"
    New-Item -ItemType Directory -Path $scripts, $local, $shared, $nested -Force | Out-Null
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot "session_start.ps1") -Destination $scripts
    Set-Content -LiteralPath (Join-Path $scripts "platform_version.ps1") -Value "# isolated stub"
    Set-Content -LiteralPath (Join-Path $scripts "Get-ActiveProject.ps1") -Value "'alpha'"
    @'
param([string]$Name, [string]$Stack, [string]$Path)
Set-Content -LiteralPath $env:DCC_INIT_RECORD -Value "$Name|$Path"
'@ | Set-Content -LiteralPath (Join-Path $scripts "new_project.ps1")
    $env:DEVCORE_PLATFORM_ROOT = $platform
    $env:DEVCORE_LOCAL_ROOT = $local
    $env:DEVCORE_DATA_ROOT = $shared
    $env:DCC_INIT_RECORD = Join-Path $tempRoot "init.txt"

    $sha = [System.Security.Cryptography.SHA256]::Create()
    $key = [System.BitConverter]::ToString($sha.ComputeHash([System.Text.Encoding]::UTF8.GetBytes("alpha"))).Replace('-', '').Substring(0, 16)
    $sha.Dispose()
    $userKey = ($env:USERNAME -replace '[^A-Za-z0-9_-]', '_')
    $flagDir = Join-Path $local ("Logs\scripts\" + $key)
    New-Item -ItemType Directory -Path $flagDir -Force | Out-Null
    $flag = Join-Path $flagDir ("session_started_" + (Get-Date -Format "yyyy-MM-dd") + "_${userKey}.flag")
    Set-Content -LiteralPath $flag -Value "already started"

    New-Item -ItemType Directory -Path (Join-Path $project ".devcore") -Force | Out-Null
    Set-Content -LiteralPath (Join-Path $project ".devcore\project.json") -Value '{"name":"alpha"}'
    Push-Location $nested
    try {
        & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File (Join-Path $scripts "session_start.ps1") | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "Nested metadata scenario failed" }
    } finally { Pop-Location }
    if (Test-Path -LiteralPath $env:DCC_INIT_RECORD) { throw "Nested directory was registered as a project" }

    Remove-Item -LiteralPath (Join-Path $project ".devcore\project.json")
    New-Item -ItemType Directory -Path (Join-Path $project ".git") -Force | Out-Null
    Push-Location $nested
    try {
        & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File (Join-Path $scripts "session_start.ps1") | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "Git root scenario failed" }
    } finally { Pop-Location }
    $record = Get-Content -LiteralPath $env:DCC_INIT_RECORD -Raw
    if ($record.Trim() -ne "alpha|$project") { throw "Project initialized outside Git root: $record" }
    if (Test-Path -LiteralPath (Join-Path $shared "Memory\alpha\tasks.json")) { throw "Shared board was written" }
    Write-Host "[OK] Session initialization resolves the project root" -ForegroundColor Green
} finally {
    Set-Location $savedLocation
    foreach ($name in $saved.Keys) {
        if ($null -eq $saved[$name]) { Remove-Item -Path ("Env:" + $name) -ErrorAction SilentlyContinue }
        else { Set-Item -Path ("Env:" + $name) -Value $saved[$name] }
    }
    if (Test-Path -LiteralPath $tempRoot) { Remove-Item -LiteralPath $tempRoot -Recurse -Force }
}
