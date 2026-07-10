# metrics_service.ps1 -- DEV_CORE v10 -- append-only Metrics Service
param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("Record", "Aggregate", "Status", "Health")]
    [string]$Action,
    [string]$Source = "devcore",
    [string]$Project = "",
    [string]$TaskId = "",
    [string]$MetricType = "",
    [double]$Value = 0,
    [string]$Unit = "count",
    [string]$PayloadJson = "{}",
    [string]$Date = "",
    [switch]$Json
)

$ErrorActionPreference = "Stop"

$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT) { $env:DEVCORE_DATA_ROOT } else { "C:\devcore\DEV_CORE_DATA" }
$TODAY = if ($Date) { $Date } else { Get-Date -Format "yyyy-MM-dd" }
$METRICS_DIR = Join-Path $DEV_CORE_DATA "Logs\metrics"
$METRICS_FILE = Join-Path $METRICS_DIR "metrics-$TODAY.jsonl"

function Ensure-MetricsDir {
    New-Item -ItemType Directory -Path $METRICS_DIR -Force | Out-Null
    return $METRICS_DIR
}

function Get-ActiveProjectName {
    if ($Project) { return $Project }
    $projectScript = Join-Path $PSScriptRoot "Get-ActiveProject.ps1"
    if (Test-Path -LiteralPath $projectScript) {
        try { return ((& $projectScript) | Select-Object -First 1).Trim() } catch {}
    }
    return "devcore"
}

function Get-ActiveTaskId {
    param([string]$ProjectName)
    if ($TaskId) { return $TaskId }
    $taskFile = Join-Path $DEV_CORE_DATA "Memory\$ProjectName\tasks.json"
    if (Test-Path -LiteralPath $taskFile) {
        try {
            $board = Get-Content -LiteralPath $taskFile -Raw -Encoding UTF8 | ConvertFrom-Json
            if ($board.current_task) { return [string]$board.current_task }
        } catch {}
    }
    return $null
}

function ConvertTo-SafePayload {
    param($Value)

    if ($null -eq $Value) { return $null }

    if ($Value -is [System.Array]) {
        $items = @()
        foreach ($item in $Value) { $items += ConvertTo-SafePayload -Value $item }
        return $items
    }

    if ($Value -is [System.Management.Automation.PSCustomObject]) {
        $safe = [ordered]@{}
        foreach ($prop in $Value.PSObject.Properties) {
            $name = [string]$prop.Name
            if ($name -match "(?i)(api[_-]?key|token|secret|password|credential)") {
                $safe[$name] = "[REDACTED]"
            } elseif ($name -match "(?i)^(prompt|content|message|input|output)$") {
                $safe[$name] = "[REDACTED_CONTEXT]"
            } else {
                $safe[$name] = ConvertTo-SafePayload -Value $prop.Value
            }
        }
        return [pscustomobject]$safe
    }

    if ($Value -is [System.Collections.IDictionary]) {
        $safe = [ordered]@{}
        foreach ($key in $Value.Keys) {
            $name = [string]$key
            if ($name -match "(?i)(api[_-]?key|token|secret|password|credential)") {
                $safe[$name] = "[REDACTED]"
            } elseif ($name -match "(?i)^(prompt|content|message|input|output)$") {
                $safe[$name] = "[REDACTED_CONTEXT]"
            } else {
                $safe[$name] = ConvertTo-SafePayload -Value $Value[$key]
            }
        }
        return [pscustomobject]$safe
    }

    if ($Value -is [string]) {
        return ($Value -replace "(?i)(api[_-]?key|token|secret|password)=([^;\s]+)", '$1=[REDACTED]')
    }

    return $Value
}

function Read-PayloadJson {
    if ([string]::IsNullOrWhiteSpace($PayloadJson)) { return [pscustomobject]@{} }
    try {
        return ConvertTo-SafePayload -Value ($PayloadJson | ConvertFrom-Json)
    } catch {
        $trimmed = $PayloadJson.Trim()
        if ($trimmed.StartsWith("{") -and $trimmed.EndsWith("}")) {
            $loose = [ordered]@{}
            $body = $trimmed.Substring(1, $trimmed.Length - 2)
            foreach ($part in ($body -split ",")) {
                $pieces = $part -split ":", 2
                if ($pieces.Count -eq 2) {
                    $key = $pieces[0].Trim().Trim('"', "'")
                    $value = $pieces[1].Trim().Trim('"', "'")
                    if (-not [string]::IsNullOrWhiteSpace($key)) {
                        $loose[$key] = $value
                    }
                }
            }
            if ($loose.Count -gt 0) {
                return ConvertTo-SafePayload -Value $loose
            }
        }
        return [pscustomobject]@{ raw = "[INVALID_JSON]" }
    }
}

function New-MetricEvent {
    $projectName = Get-ActiveProjectName
    [pscustomobject][ordered]@{
        schema_version = 1
        id = [guid]::NewGuid().ToString("n")
        event_type = "MetricRecorded"
        timestamp = (Get-Date).ToString("o")
        source = $Source
        project = $projectName
        task_id = Get-ActiveTaskId -ProjectName $projectName
        metric_type = $MetricType
        value = $Value
        unit = $Unit
        payload = Read-PayloadJson
    }
}

function Read-MetricEvents {
    param([string]$Path)
    $events = @()
    $errors = 0
    if (-not (Test-Path -LiteralPath $Path)) {
        return [pscustomobject]@{ events = @(); errors = 0 }
    }
    foreach ($line in Get-Content -LiteralPath $Path -Encoding UTF8) {
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        try {
            $events += ($line | ConvertFrom-Json)
        } catch {
            $errors++
        }
    }
    return [pscustomobject]@{ events = $events; errors = $errors }
}

function Add-GroupedMetric {
    param(
        [hashtable]$Table,
        [string]$MetricType,
        [string]$MetricUnit,
        [double]$MetricValue
    )

    if (-not $Table.ContainsKey($MetricType)) { $Table[$MetricType] = @{} }
    if (-not $Table[$MetricType].ContainsKey($MetricUnit)) {
        $Table[$MetricType][$MetricUnit] = [ordered]@{ count = 0; sum = 0.0 }
    }
    $Table[$MetricType][$MetricUnit].count++
    $Table[$MetricType][$MetricUnit].sum = [math]::Round(([double]$Table[$MetricType][$MetricUnit].sum + $MetricValue), 6)
}

function New-Aggregate {
    Ensure-MetricsDir | Out-Null
    $read = Read-MetricEvents -Path $METRICS_FILE
    $totals = @{}
    $projects = @{}
    $tasks = @{}
    $sources = @{}

    foreach ($event in @($read.events)) {
        $metricTypeName = if ($event.metric_type) { [string]$event.metric_type } else { "unknown" }
        $metricUnitName = if ($event.unit) { [string]$event.unit } else { "count" }
        $metricValue = try { [double]$event.value } catch { 0.0 }
        Add-GroupedMetric -Table $totals -MetricType $metricTypeName -MetricUnit $metricUnitName -MetricValue $metricValue

        $projectName = if ($event.project) { [string]$event.project } else { "unknown" }
        if (-not $projects.ContainsKey($projectName)) { $projects[$projectName] = [ordered]@{ events_count = 0; totals = @{} } }
        $projects[$projectName].events_count++
        Add-GroupedMetric -Table $projects[$projectName].totals -MetricType $metricTypeName -MetricUnit $metricUnitName -MetricValue $metricValue

        $taskName = if ($event.task_id) { [string]$event.task_id } else { "none" }
        if (-not $tasks.ContainsKey($taskName)) { $tasks[$taskName] = [ordered]@{ events_count = 0; totals = @{} } }
        $tasks[$taskName].events_count++
        Add-GroupedMetric -Table $tasks[$taskName].totals -MetricType $metricTypeName -MetricUnit $metricUnitName -MetricValue $metricValue

        $sourceName = if ($event.source) { [string]$event.source } else { "unknown" }
        if (-not $sources.ContainsKey($sourceName)) { $sources[$sourceName] = [ordered]@{ events_count = 0 } }
        $sources[$sourceName].events_count++
    }

    [pscustomobject][ordered]@{
        schema_version = 1
        date = $TODAY
        store_path = $METRICS_FILE
        events_count = @($read.events).Count
        errors_count = $read.errors
        totals = $totals
        projects = $projects
        tasks = $tasks
        sources = $sources
    }
}

function New-Health {
    Ensure-MetricsDir | Out-Null
    $canWrite = $false
    try {
        $probe = Join-Path $METRICS_DIR ".health"
        "ok" | Set-Content -LiteralPath $probe -Encoding UTF8
        Remove-Item -LiteralPath $probe -Force -ErrorAction SilentlyContinue
        $canWrite = $true
    } catch {
        $canWrite = $false
    }
    [pscustomobject][ordered]@{
        schema_version = 1
        ok = $canWrite
        metrics_dir = $METRICS_DIR
        store_path = $METRICS_FILE
        writable = $canWrite
    }
}

switch ($Action) {
    "Record" {
        if ([string]::IsNullOrWhiteSpace($MetricType)) {
            Write-Error "MetricType is required for Record."
            exit 64
        }
        Ensure-MetricsDir | Out-Null
        $event = New-MetricEvent
        ($event | ConvertTo-Json -Depth 20 -Compress) | Add-Content -LiteralPath $METRICS_FILE -Encoding UTF8
        if ($Json) {
            $event | ConvertTo-Json -Depth 20
        } else {
            Write-Host "[METRICS] record OK -- $($event.metric_type)=$($event.value) $($event.unit)"
        }
        exit 0
    }
    "Aggregate" {
        $aggregate = New-Aggregate
        if ($Json) { $aggregate | ConvertTo-Json -Depth 30 } else { Write-Host "[METRICS] aggregate OK -- $($aggregate.events_count) event(s)" }
        exit 0
    }
    "Status" {
        $status = [pscustomobject][ordered]@{
            schema_version = 1
            health = New-Health
            aggregate = New-Aggregate
        }
        if ($Json) { $status | ConvertTo-Json -Depth 30 } else { Write-Host "[METRICS] status OK -- $($status.aggregate.events_count) event(s)" }
        exit 0
    }
    "Health" {
        $health = New-Health
        if ($Json) { $health | ConvertTo-Json -Depth 10 } else { Write-Host "[METRICS] health OK -- writable=$($health.writable)" }
        if ($health.ok) { exit 0 } else { exit 1 }
    }
}
