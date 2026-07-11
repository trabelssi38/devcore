# toonify.ps1 -- DEV_CORE
# DEPRECATED in v9.0 -- Remplacé par le proxy de compression Headroom SmartCrusher
# Conversion JSON <-> TOON avec stats et fallback
Write-Host "  [TOON] [DEPRECATED] Ce script est déprécié. Headroom SmartCrusher gère maintenant la compression JSON." -ForegroundColor Yellow

param(
    [Parameter(Mandatory=$true)]
    [string]$InputFile,
    [switch]$StatsSave,
    [switch]$Decode,
    [switch]$DryRun
)

$DEV_CORE = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\devcore\DEV_CORE" }
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT) { $env:DEVCORE_DATA_ROOT } else { "C:\devcore\DEV_CORE_DATA" }
. "$DEV_CORE\Scripts\platform_version.ps1"
$PLATFORM = Get-DevCorePlatformInfo
$KPI_FILE = "$DEV_CORE_DATA\Metrics\kpi.csv"
$TOON_CLI = "npx @toon-format/cli"

function Write-Log {
    param([string]$msg, [string]$color="Gray")
    Write-Host "  $msg" -ForegroundColor $color
}

Write-Host ""
Write-Host "  $($PLATFORM.title) -- TOONIFY" -ForegroundColor Cyan

if (-not (Test-Path $InputFile)) {
    Write-Log "ERREUR: $InputFile introuvable" "Red"
    exit 1
}

# Lire le fichier source
$sourceContent = Get-Content $InputFile -Raw
$sourceChars = $sourceContent.Length

if (-not $Decode) {
    # ENCODE: JSON -> TOON
    Write-Log "Encoding: $InputFile -> TOON" "Cyan"

    try {
        $tempJson = [System.IO.Path]::GetTempFileName() -replace '\.tmp$', '.json'
        # PS5.1 : Set-Content -Encoding UTF8 ajoute un BOM que npx toon rejette
        $Utf8NoBom = New-Object System.Text.UTF8Encoding $False
        [System.IO.File]::WriteAllText($tempJson, $sourceContent, $Utf8NoBom)

        # Syntaxe correcte : npx @toon-format/cli -e [INPUT] (pas 'encode --input')
        $toonOutput = & npx @toon-format/cli -e "$tempJson" 2>&1 |
            Where-Object { $_ -notmatch 'ExperimentalWarning' -and $_ -notmatch 'CommonJS module' -and $_ -notmatch 'require\(\)' -and $_ -notmatch '--trace-warnings' -and $_ -notmatch '^\(Use ' }
        $toonOutput = $toonOutput -join "`n"
        Remove-Item $tempJson -Force -ErrorAction SilentlyContinue

        if (-not $toonOutput -or $toonOutput.Length -lt 5) {
            throw "TOON encode produced empty output"
        }

        $toonChars = $toonOutput.Length
        $savings = if ($sourceChars -gt 0) { [math]::Round((($sourceChars - $toonChars) / $sourceChars) * 100, 1) } else { 0 }

        Write-Log "  JSON:   $sourceChars chars" "Gray"
        Write-Log "  TOON:   $toonChars chars" "Gray"
        Write-Log "  Gain:   $savings%" $(if ($savings -gt 25) { "Green" } else { "Yellow" })

        if ($savings -gt 25) {
            Write-Log "  RECOMMANDE: Activer TOON par defaut (gain > 25%)" "Green"
        }

        if ($StatsSave) {
            $metricsDir = Split-Path $KPI_FILE
            if (-not (Test-Path $metricsDir)) { New-Item -ItemType Directory -Path $metricsDir -Force | Out-Null }
            $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
            $filename = Split-Path $InputFile -Leaf
            $header = "timestamp,file,json_chars,toon_chars,savings_pct,recommended"
            $row = "$timestamp,$filename,$sourceChars,$toonChars,$savings,"
            if ($savings -gt 25) { $row += "YES" } else { $row += "NO" }
            if (-not (Test-Path $KPI_FILE)) { $header | Set-Content $KPI_FILE -Encoding UTF8 }
            $row | Add-Content $KPI_FILE -Encoding UTF8
            Write-Log "  Stats sauvegardees dans $KPI_FILE" "Green"
        }

        if (-not $DryRun) {
            $toonFile = [System.IO.Path]::ChangeExtension($InputFile, ".toon")
            $toonOutput | Set-Content $toonFile -Encoding UTF8
            Write-Log "  TOON ecrit dans $toonFile" "Green"
        }

        # Pas de return ici -- evite la pollution du pipeline quand appele depuis un autre script
        $script:ToonSavings    = $savings
        $script:ToonRecommended = ($savings -gt 25)

    } catch {
        Write-Log "ERREUR encoding TOON: $_ - Fallback JSON" "Red"
        return @{ error = $_.Exception.Message; fallback = "json" }
    }
} else {
    # DECODE: TOON -> JSON
    Write-Log "Decoding: $InputFile -> JSON" "Cyan"
    try {
        $tempToon = [System.IO.Path]::GetTempFileName() -replace '\.tmp$', '.toon'
        $sourceContent | Set-Content $tempToon -Encoding UTF8

        # Syntaxe correcte : npx @toon-format/cli -d [INPUT] (pas 'decode --input')
        $jsonOutput = & npx @toon-format/cli -d "$tempToon" 2>&1 |
            Where-Object { $_ -notmatch 'ExperimentalWarning' -and $_ -notmatch 'CommonJS module' -and $_ -notmatch 'require\(\)' -and $_ -notmatch '--trace-warnings' -and $_ -notmatch '^\(Use ' }
        $jsonOutput = $jsonOutput -join "`n"
        Remove-Item $tempToon -Force -ErrorAction SilentlyContinue

        if (-not $jsonOutput -or $jsonOutput.Length -lt 2) {
            throw "TOON decode produced empty output"
        }

        if (-not $DryRun) {
            $jsonFile = [System.IO.Path]::ChangeExtension($InputFile, ".json")
            $jsonOutput | Set-Content $jsonFile -Encoding UTF8
            Write-Log "  JSON ecrit dans $jsonFile" "Green"
        }

        return @{ success = $true }

    } catch {
        Write-Log "ERREUR decoding TOON: $_ - Fallback TOON" "Red"
        return @{ error = $_.Exception.Message; fallback = "toon" }
    }
}
