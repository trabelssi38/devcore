# learning_service.ps1 -- DEV_CORE v11.1 -- measured recommendations engine
param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("Analyze", "Status", "Health")]
    [string]$Action,
    [string]$Date = "",
    [switch]$Json
)

$ErrorActionPreference = "Stop"

$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT) { $env:DEVCORE_DATA_ROOT } else { (Join-Path (Split-Path -Parent $PSScriptRoot) "DEV_CORE_DATA") }
$TODAY = if ($Date) { $Date } else { Get-Date -Format "yyyy-MM-dd" }
$LEARNING_DIR = Join-Path $DEV_CORE_DATA "Learning"
$REPORT_FILE = Join-Path $LEARNING_DIR "learning-report-$TODAY.json"
$METRICS_FILE = Join-Path $DEV_CORE_DATA "Logs\metrics\metrics-$TODAY.jsonl"
$EVENTS_FILE = Join-Path $DEV_CORE_DATA "Bus\events\events-$TODAY.jsonl"
$EVENT_BUS = Join-Path $PSScriptRoot "event_bus.ps1"

function Ensure-LearningDir {
    New-Item -ItemType Directory -Path $LEARNING_DIR -Force | Out-Null
    return $LEARNING_DIR
}

function Read-JsonLines {
    param([string]$Path)

    $items = @()
    $errors = 0
    if (-not (Test-Path -LiteralPath $Path)) {
        return [pscustomobject]@{ items = @(); errors = 0 }
    }

    foreach ($line in Get-Content -LiteralPath $Path -Encoding UTF8) {
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        try {
            $items += ($line | ConvertFrom-Json)
        } catch {
            $errors++
        }
    }

    return [pscustomobject]@{ items = $items; errors = $errors }
}

function Get-PayloadValue {
    param($Item, [string]$Name, [string]$Default = "unknown")

    if ($Item -and $Item.PSObject.Properties["payload"] -and $Item.payload) {
        $payload = $Item.payload
        if ($payload.PSObject.Properties[$Name] -and -not [string]::IsNullOrWhiteSpace([string]$payload.$Name)) {
            return [string]$payload.$Name
        }
    }
    return $Default
}

function Add-Stat {
    param([hashtable]$Table, [string]$Key, [double]$Value)

    if ([string]::IsNullOrWhiteSpace($Key)) { $Key = "unknown" }
    if (-not $Table.ContainsKey($Key)) {
        $Table[$Key] = [ordered]@{ count = 0; sum = 0.0; average = 0.0; latest = 0.0 }
    }
    $Table[$Key].count++
    $Table[$Key].sum = [math]::Round(([double]$Table[$Key].sum + $Value), 6)
    $Table[$Key].latest = [math]::Round($Value, 6)
    $Table[$Key].average = [math]::Round(([double]$Table[$Key].sum / [double]$Table[$Key].count), 6)
}

function Add-Count {
    param([hashtable]$Table, [string]$Key)

    if ([string]::IsNullOrWhiteSpace($Key)) { $Key = "unknown" }
    if (-not $Table.ContainsKey($Key)) {
        $Table[$Key] = [ordered]@{ count = 0 }
    }
    $Table[$Key].count++
}

function Get-GlobalAverage {
    param([hashtable]$Table)

    $sum = 0.0
    $count = 0
    foreach ($key in $Table.Keys) {
        $sum += [double]$Table[$key].sum
        $count += [int]$Table[$key].count
    }
    if ($count -eq 0) { return 0.0 }
    return [math]::Round(($sum / $count), 6)
}

function New-Recommendation {
    param(
        [string]$Type,
        [string]$Title,
        [string]$Recommendation,
        [double]$Confidence,
        [object[]]$Evidence
    )

    [pscustomobject][ordered]@{
        type = $Type
        title = $Title
        recommendation = $Recommendation
        confidence = [math]::Round([math]::Min(0.95, [math]::Max(0.1, $Confidence)), 2)
        evidence = @($Evidence)
    }
}

function Publish-LearningEvent {
    param($Report)

    if (-not (Test-Path -LiteralPath $EVENT_BUS)) { return }
    try {
        $payload = [ordered]@{
            date = $Report.date
            recommendations_count = $Report.recommendations_count
            report_path = $Report.report_path
        }
        $payloadJson = $payload | ConvertTo-Json -Depth 10 -Compress
        & $EVENT_BUS -Action Publish -Source "learning_service" -Project "devcore" -TaskId $null -EventType "LearningReportGenerated" -CorrelationId "learning-$($Report.date)" -PayloadJson $payloadJson 6>$null | Out-Null
    } catch {}
}

function New-Analysis {
    Ensure-LearningDir | Out-Null

    $metricsRead = Read-JsonLines -Path $METRICS_FILE
    $eventsRead = Read-JsonLines -Path $EVENTS_FILE

    $costByMode = @{}
    $tokensByMode = @{}
    $correctionsByMode = @{}
    $correctionsByTaskType = @{}
    $healthFailuresBySource = @{}

    foreach ($metric in @($metricsRead.items)) {
        $metricType = if ($metric.metric_type) { [string]$metric.metric_type } else { "unknown" }
        $unit = if ($metric.unit) { [string]$metric.unit } else { "count" }
        $value = try { [double]$metric.value } catch { 0.0 }
        $mode = Get-PayloadValue -Item $metric -Name "mode"
        $taskType = Get-PayloadValue -Item $metric -Name "task_type"

        if ($metricType -eq "cost" -and $unit -eq "usd") {
            Add-Stat -Table $costByMode -Key $mode -Value $value
        } elseif ($metricType -eq "tokens") {
            Add-Stat -Table $tokensByMode -Key $mode -Value $value
        } elseif ($metricType -eq "corrections") {
            Add-Stat -Table $correctionsByMode -Key $mode -Value $value
            Add-Stat -Table $correctionsByTaskType -Key $taskType -Value $value
        }
    }

    foreach ($event in @($eventsRead.items)) {
        if ($event.event_type -eq "HealthCheckFailed") {
            $source = if ($event.source) { [string]$event.source } else { "unknown" }
            Add-Count -Table $healthFailuresBySource -Key $source
        }
    }

    $recommendations = @()
    $globalCostAverage = Get-GlobalAverage -Table $costByMode
    foreach ($mode in @($costByMode.Keys | Sort-Object)) {
        $stats = $costByMode[$mode]
        if ($globalCostAverage -gt 0 -and [double]$stats.average -gt $globalCostAverage) {
            $delta = [double]$stats.average - $globalCostAverage
            $confidence = 0.55 + ([math]::Min(0.35, $delta / [math]::Max([double]$stats.average, 1)))
            $recommendations += New-Recommendation `
                -Type "cost" `
                -Title "Mode $mode au-dessus de la baseline cout" `
                -Recommendation "Verifier le routage des taches $mode avant d'augmenter le budget; baseline globale $globalCostAverage usd, moyenne $mode $($stats.average) usd." `
                -Confidence $confidence `
                -Evidence @("mode=$mode", "average_usd=$($stats.average)", "global_average_usd=$globalCostAverage", "samples=$($stats.count)")
        }
    }

    $globalCorrectionsAverage = Get-GlobalAverage -Table $correctionsByMode
    foreach ($mode in @($correctionsByMode.Keys | Sort-Object)) {
        $stats = $correctionsByMode[$mode]
        if ([double]$stats.sum -gt 0 -and ([double]$stats.average -ge $globalCorrectionsAverage)) {
            $confidence = 0.6 + [math]::Min(0.25, [double]$stats.sum / 20.0)
            $recommendations += New-Recommendation `
                -Type "routing" `
                -Title "Corrections elevees en mode $mode" `
                -Recommendation "Mesurer le prochain lot $mode contre la baseline corrections avant de changer le mode par defaut." `
                -Confidence $confidence `
                -Evidence @("mode=$mode", "corrections=$($stats.sum)", "average=$($stats.average)", "baseline=$globalCorrectionsAverage")
        }
    }

    foreach ($source in @($healthFailuresBySource.Keys | Sort-Object)) {
        $stats = $healthFailuresBySource[$source]
        $confidence = 0.65 + [math]::Min(0.25, [double]$stats.count / 10.0)
        $recommendations += New-Recommendation `
            -Type "reliability" `
            -Title "HealthCheckFailed detecte pour $source" `
            -Recommendation "Traiter $source comme candidat prioritaire de stabilisation avant d'ajouter de nouvelles capacites." `
            -Confidence $confidence `
            -Evidence @("source=$source", "failures=$($stats.count)", "event_type=HealthCheckFailed")
    }

    $report = [pscustomobject][ordered]@{
        schema_version = 1
        date = $TODAY
        generated_at = (Get-Date).ToString("o")
        metrics_path = $METRICS_FILE
        events_path = $EVENTS_FILE
        report_path = $REPORT_FILE
        observations = [ordered]@{
            metrics_count = @($metricsRead.items).Count
            metrics_errors = $metricsRead.errors
            events_count = @($eventsRead.items).Count
            events_errors = $eventsRead.errors
        }
        baseline = [ordered]@{
            cost_by_mode = $costByMode
            tokens_by_mode = $tokensByMode
            corrections_by_mode = $correctionsByMode
            corrections_by_task_type = $correctionsByTaskType
            health_failures_by_source = $healthFailuresBySource
            global_cost_average_usd = $globalCostAverage
            global_corrections_average = $globalCorrectionsAverage
        }
        recommendations_count = @($recommendations).Count
        recommendations = @($recommendations)
    }

    $report | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $REPORT_FILE -Encoding UTF8
    Publish-LearningEvent -Report $report
    return $report
}

function New-Health {
    Ensure-LearningDir | Out-Null
    $canWrite = $false
    try {
        $probe = Join-Path $LEARNING_DIR ".health"
        "ok" | Set-Content -LiteralPath $probe -Encoding UTF8
        Remove-Item -LiteralPath $probe -Force -ErrorAction SilentlyContinue
        $canWrite = $true
    } catch {
        $canWrite = $false
    }

    [pscustomobject][ordered]@{
        schema_version = 1
        ok = $canWrite
        learning_dir = $LEARNING_DIR
        report_path = $REPORT_FILE
        writable = $canWrite
    }
}

function Get-LatestReport {
    Ensure-LearningDir | Out-Null
    $latest = Get-ChildItem -LiteralPath $LEARNING_DIR -Filter "learning-report-*.json" -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    if (-not $latest) { return $null }
    try {
        return Get-Content -LiteralPath $latest.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
    } catch {
        return [pscustomobject][ordered]@{
            schema_version = 1
            report_path = $latest.FullName
            recommendations_count = 0
            read_error = $true
        }
    }
}

switch ($Action) {
    "Analyze" {
        $analysis = New-Analysis
        if ($Json) { $analysis | ConvertTo-Json -Depth 30 }
        else { Write-Host "[LEARNING] analyze OK -- $($analysis.recommendations_count) recommendation(s)" }
        exit 0
    }
    "Status" {
        $status = [pscustomobject][ordered]@{
            schema_version = 1
            health = New-Health
            latest_report = Get-LatestReport
        }
        if ($Json) { $status | ConvertTo-Json -Depth 30 }
        else {
            $count = if ($status.latest_report) { $status.latest_report.recommendations_count } else { 0 }
            Write-Host "[LEARNING] status OK -- $count recommendation(s)"
        }
        exit 0
    }
    "Health" {
        $health = New-Health
        if ($Json) { $health | ConvertTo-Json -Depth 10 }
        else { Write-Host "[LEARNING] health OK -- writable=$($health.writable)" }
        if ($health.ok) { exit 0 } else { exit 1 }
    }
}
