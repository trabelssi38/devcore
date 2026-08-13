# secret_scan.ps1 -- scan tracked text files for hardcoded secrets
param(
    [string]$Path = (Get-Location).Path,
    [switch]$Quiet
)

$ErrorActionPreference = "Stop"

$root = (Resolve-Path -LiteralPath $Path).Path
$gitRoot = $null
try {
    $res = (& git -C $root rev-parse --show-toplevel 2>&1)
    if ($LASTEXITCODE -eq 0 -and $res -and $res -notmatch "fatal:") {
        $gitRoot = $res.Trim()
    }
} catch {}

if ($gitRoot) {
    $root = $gitRoot
    $relativeFiles = @(& git -C $root ls-files)
} else {
    $relativeFiles = Get-ChildItem -LiteralPath $root -Recurse -File |
        ForEach-Object { [System.IO.Path]::GetRelativePath($root, $_.FullName) }
}

$skipExtensions = @(
    ".7z", ".dll", ".exe", ".gif", ".ico", ".jpg", ".jpeg", ".pdf", ".png",
    ".pyc", ".sqlite", ".zip"
)
$skipPrefixes = @(
    ".git/",
    ".repowise/",
    ".repowise-workspace/",
    "DEV_CORE_DATA/"
)
$allowFiles = @(
    ".env.example",
    "DEV_CORE/Config/gemini_api_key.txt",
    "DEV_CORE/Config/nvidia_api_key.txt",
    "DEV_CORE/Config/cerebras_api_key.txt"
)

$patterns = @(
    @{ Name = "OpenAI-style token"; Regex = [regex]"(?i)\bsk-[a-z0-9][a-z0-9_-]{19,}\b" },
    @{ Name = "Gemini AI Studio token"; Regex = [regex]"\bAQ\.[A-Za-z0-9_-]{30,}\b" },
    @{ Name = "Google API key"; Regex = [regex]"\bAIza[0-9A-Za-z_-]{20,}\b" }
)

$findings = @()

foreach ($rel in $relativeFiles) {
    if (-not $rel) { continue }
    $normalized = ($rel -replace "\\", "/")

    if ($allowFiles -contains $normalized) { continue }
    if ($skipPrefixes | Where-Object { $normalized.StartsWith($_) }) { continue }

    $extension = [System.IO.Path]::GetExtension($normalized).ToLowerInvariant()
    if ($skipExtensions -contains $extension) { continue }

    $fullPath = Join-Path $root $rel
    if (-not (Test-Path -LiteralPath $fullPath)) { continue }

    $item = Get-Item -LiteralPath $fullPath
    if ($item.Length -gt 1MB) { continue }

    try {
        $text = Get-Content -LiteralPath $fullPath -Raw -Encoding UTF8
    } catch {
        continue
    }
    if ($null -eq $text) { $text = "" }

    foreach ($pattern in $patterns) {
        foreach ($match in $pattern.Regex.Matches($text)) {
            $prefix = if ($match.Index -gt 0) { $text.Substring(0, $match.Index) } else { "" }
            $line = 1 + ([regex]::Matches($prefix, "`n")).Count
            $findings += [PSCustomObject]@{
                File = $normalized
                Line = $line
                Type = $pattern.Name
            }
        }
    }
}

if ($findings.Count -gt 0) {
    if (-not $Quiet) {
        Write-Host "  [FAIL] Secrets detectes dans des fichiers suivis:" -ForegroundColor Red
        foreach ($finding in $findings) {
            Write-Host "         $($finding.File):$($finding.Line) -- $($finding.Type)" -ForegroundColor Red
        }
    }
    exit 1
}

if (-not $Quiet) {
    Write-Host "  [OK]   Aucun secret hardcode detecte dans les fichiers suivis" -ForegroundColor Green
}
exit 0
