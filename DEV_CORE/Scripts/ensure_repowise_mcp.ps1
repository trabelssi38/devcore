# ensure_repowise_mcp.ps1 -- configure Repowise MCP for DEV_CORE clients
param(
    [string]$RepoRoot = "C:\devcore",
    [string]$RepowisePath = ""
)

$ErrorActionPreference = "Stop"

$HomeDir = [Environment]::GetFolderPath("UserProfile")
$Description = "repowise: codebase intelligence -- docs, graph, git signals, dead code, decisions"

function Write-Utf8NoBom {
    param(
        [string]$Path,
        [string]$Content
    )

    $encoding = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $Content, $encoding)
}

function Resolve-Repowise {
    param([string]$RequestedPath)

    $candidates = @()
    if ($RequestedPath) { $candidates += $RequestedPath }
    if ($env:REPOWISE_EXE) { $candidates += $env:REPOWISE_EXE }
    $candidates += Join-Path $HomeDir "AppData\Roaming\Python\Python313\Scripts\repowise.exe"
    $candidates += Join-Path $HomeDir "AppData\Roaming\Python\Python312\Scripts\repowise.exe"

    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path $candidate)) {
            return (Resolve-Path $candidate).Path
        }
    }

    $cmd = Get-Command "repowise" -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }

    return "repowise"
}

function New-RepowiseMcpServer {
    param([string]$CommandPath, [string]$Root)

    [ordered]@{
        command = $CommandPath
        args = @(
            "mcp",
            ($Root -replace "\\", "/"),
            "--transport",
            "stdio"
        )
        description = $Description
    }
}

function Read-JsonObject {
    param([string]$Path)

    if (-not (Test-Path $Path)) {
        New-Item -ItemType Directory -Path (Split-Path $Path) -Force | Out-Null
        return [pscustomobject]@{}
    }

    $raw = Get-Content $Path -Raw -Encoding UTF8 -ErrorAction SilentlyContinue
    if (-not $raw -or -not $raw.Trim()) {
        return [pscustomobject]@{}
    }

    return ($raw | ConvertFrom-Json)
}

function Set-ObjectProperty {
    param(
        [object]$Object,
        [string]$Name,
        [object]$Value
    )

    if ($Object.PSObject.Properties[$Name]) {
        $Object.PSObject.Properties.Remove($Name)
    }
    $Object | Add-Member -NotePropertyName $Name -NotePropertyValue $Value
}

function Set-JsonMcpServer {
    param(
        [string]$Path,
        [object]$ServerConfig
    )

    $json = Read-JsonObject $Path
    if (-not $json.PSObject.Properties["mcpServers"] -or $null -eq $json.mcpServers) {
        Set-ObjectProperty -Object $json -Name "mcpServers" -Value ([pscustomobject]@{})
    }

    Set-ObjectProperty -Object $json.mcpServers -Name "repowise" -Value ([pscustomobject]$ServerConfig)
    $json | ConvertTo-Json -Depth 20 | Set-Content $Path -Encoding UTF8
    Write-Host "[DEV_CORE] Repowise MCP JSON OK -- $Path"
}

function Set-OpenCodeMcpServer {
    param(
        [string]$Path,
        [string]$CommandPath,
        [string]$Root
    )

    $json = Read-JsonObject $Path
    if (-not $json.PSObject.Properties["mcp"] -or $null -eq $json.mcp) {
        Set-ObjectProperty -Object $json -Name "mcp" -Value ([pscustomobject]@{})
    }

    $server = [pscustomobject]@{
        type = "local"
        command = @(
            $CommandPath,
            "mcp",
            ($Root -replace "\\", "/"),
            "--transport",
            "stdio"
        )
        enabled = $true
    }

    Set-ObjectProperty -Object $json.mcp -Name "repowise" -Value $server
    $json | ConvertTo-Json -Depth 30 | Set-Content $Path -Encoding UTF8
    Write-Host "[DEV_CORE] Repowise MCP opencode OK -- $Path"
}

function Set-CodexTomlMcpServer {
    param(
        [string]$Path,
        [string]$CommandPath,
        [string]$Root
    )

    New-Item -ItemType Directory -Path (Split-Path $Path) -Force | Out-Null
    $content = ""
    if (Test-Path $Path) {
        $content = Get-Content $Path -Raw -Encoding UTF8
    }

    $block = @"

[mcp_servers.repowise]
command = '$($CommandPath.Replace("'", "''"))'
args = [
  'mcp',
  '$(($Root -replace "\\", "/").Replace("'", "''"))',
  '--transport',
  'stdio',
]
startup_timeout_sec = 120
"@

    $pattern = "(?ms)^\[mcp_servers\.repowise\]\s*.*?(?=^\[[^\r\n]+\]|\z)"
    if ($content -match $pattern) {
        $content = [regex]::Replace($content, $pattern, $block.TrimStart(), 1)
    } else {
        $content = $content.TrimEnd() + $block
    }

    Write-Utf8NoBom -Path $Path -Content ($content.TrimEnd() + [Environment]::NewLine)
    Write-Host "[DEV_CORE] Repowise MCP Codex OK -- $Path"
}

$resolvedRepo = (Resolve-Path $RepoRoot).Path
$resolvedRepowise = Resolve-Repowise -RequestedPath $RepowisePath
$serverConfig = New-RepowiseMcpServer -CommandPath $resolvedRepowise -Root $resolvedRepo

$jsonTargets = @(
    (Join-Path $resolvedRepo ".mcp.json"),
    (Join-Path $HomeDir ".claude\settings.json"),
    (Join-Path $HomeDir ".gemini\settings.json"),
    (Join-Path $HomeDir ".gemini\antigravity\settings.json"),
    (Join-Path $HomeDir ".gemini\antigravity\mcp_config.json")
)

foreach ($target in $jsonTargets) {
    Set-JsonMcpServer -Path $target -ServerConfig $serverConfig
}

Set-CodexTomlMcpServer -Path (Join-Path $HomeDir ".codex\config.toml") -CommandPath $resolvedRepowise -Root $resolvedRepo
Set-CodexTomlMcpServer -Path (Join-Path $resolvedRepo ".codex\config.toml") -CommandPath $resolvedRepowise -Root $resolvedRepo
Set-OpenCodeMcpServer -Path (Join-Path $HomeDir ".config\opencode\opencode.json") -CommandPath $resolvedRepowise -Root $resolvedRepo

if (-not (Test-Path $resolvedRepowise) -and $resolvedRepowise -eq "repowise") {
    Write-Host "[DEV_CORE] Repowise MCP WARN -- repowise not found by absolute path; clients must have repowise in PATH"
} else {
    Write-Host "[DEV_CORE] Repowise MCP READY -- $resolvedRepowise"
}
