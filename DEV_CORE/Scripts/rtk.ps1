[CmdletBinding()]
param(
    [Parameter(ValueFromPipeline=$true)]
    [string[]]$InputObject,
    
    [switch]$StatsSave
)

# DEPRECATED in v9.0 -- Remplace par le proxy de compression Headroom (port 8787)
Write-Host "  [RTK] [DEPRECATED] Ce script est deprecie. Headroom Proxy gere maintenant la compression automatiquement." -ForegroundColor Yellow

begin {
    $rawLines = @()
}

process {
    if ($InputObject) {
        $rawLines += $InputObject
    }
}

end {
    if ($rawLines.Count -eq 0) { return }
    $rawContent = $rawLines -join "`n"
    $originalSize = $rawContent.Length
    if ($originalSize -eq 0) { return }

    # 1. Enlever les lignes vides
    $compressedLines = $rawLines | Where-Object { $_ -and $_.Trim().Length -gt 0 }
    
    # 2. Trimmer chaque ligne et dedupliquer les espaces multiples
    $compressedLines = $compressedLines | ForEach-Object {
        $_.Trim() -replace '\s{2,}', ' '
    }

    # 3. Smart truncate si c'est enorme (> 500 lignes)
    if ($compressedLines.Count -gt 500) {
        $head = $compressedLines[0..199]
        $tail = $compressedLines[($compressedLines.Count - 200)..($compressedLines.Count - 1)]
        $compressedLines = $head + "`n... [RTK TRUNCATED $($compressedLines.Count - 400) LINES] ...`n" + $tail
    }

    $compressedContent = $compressedLines -join "`n"
    $newSize = $compressedContent.Length
    $savings = if ($originalSize -gt 0) { [math]::Round((($originalSize - $newSize) / $originalSize) * 100, 1) } else { 0 }

    # Output the compressed content
    Write-Output $compressedContent

    # Write stats to host (stderr/console, not pipeline)
    Write-Host "`n  [RTK] Output compresse : $originalSize chars -> $newSize chars (Gain: -$savings%)" -ForegroundColor Cyan

    if ($StatsSave) {
        $DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT) { $env:DEVCORE_DATA_ROOT } else { (Join-Path (Split-Path -Parent $PSScriptRoot) "DEV_CORE_DATA") }
        $KPI_FILE = "$DEV_CORE_DATA\Metrics\kpi.csv"
        $metricsDir = Split-Path $KPI_FILE
        if (-not (Test-Path $metricsDir)) { New-Item -ItemType Directory -Path $metricsDir -Force | Out-Null }
        
        $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        $header = "timestamp,file,json_chars,toon_chars,savings_pct,recommended"
        $row = "$timestamp,RTK_filter,$originalSize,$newSize,$savings,YES"
        
        if (-not (Test-Path $KPI_FILE)) { $header | Set-Content $KPI_FILE -Encoding UTF8 }
        $row | Add-Content $KPI_FILE -Encoding UTF8
    }
}
