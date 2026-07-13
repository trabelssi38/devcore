# ensure_repowise_web_proxy.ps1 -- keep Repowise UI proxy IPv4-safe on Windows
param(
    [string]$WebRoot = "$env:USERPROFILE\.repowise\web",
    [string]$ApiUrl = "http://127.0.0.1:7337"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $WebRoot)) {
    Write-Host "[DEV_CORE] Repowise UI proxy SKIP -- web cache not found"
    exit 0
}

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$patched = 0
$bomFixed = 0

$files = Get-ChildItem -LiteralPath $WebRoot -Recurse -File -Include *.js,*.json,*.html,*.mjs -ErrorAction SilentlyContinue
foreach ($file in $files) {
    $path = $file.FullName
    $bytes = [System.IO.File]::ReadAllBytes($path)
    if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
        $text = [System.Text.Encoding]::UTF8.GetString($bytes, 3, $bytes.Length - 3)
        [System.IO.File]::WriteAllText($path, $text, $utf8NoBom)
        $bytes = [System.IO.File]::ReadAllBytes($path)
        $bomFixed++
    }

    $source = [System.Text.Encoding]::UTF8.GetString($bytes)
    if ($source -match "localhost:7337") {
        $source = $source.Replace("http://localhost:7337", $ApiUrl).Replace("localhost:7337", ($ApiUrl -replace "^https?://", ""))
        [System.IO.File]::WriteAllText($path, $source, $utf8NoBom)
        $patched++
    }
}

Write-Host "[DEV_CORE] Repowise UI proxy OK -- patched=$patched bom_fixed=$bomFixed"
