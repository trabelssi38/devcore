# dashboard_read_model.ps1 -- incremental Dashboard read model from Event Bus JSONL
param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("Rebuild", "Read", "Health")]
    [string]$Action,
    [switch]$Json
)

$ErrorActionPreference = "Stop"

$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT) { $env:DEVCORE_DATA_ROOT } else { "C:\devcore\DEV_CORE_DATA" }
$EVENTS_DIR = Join-Path $DEV_CORE_DATA "Bus\events"
$DASHBOARD_DIR = Join-Path $DEV_CORE_DATA "Dashboard"
$READ_MODEL_FILE = Join-Path $DASHBOARD_DIR "read_model.json"

function ConvertTo-JsonSafe {
    param($Value)
    return ($Value | ConvertTo-Json -Depth 12)
}

function Write-Result {
    param($Value)
    if ($Json) {
        ConvertTo-JsonSafe $Value
    } else {
        $Value
    }
}

function Read-EventFiles {
    if (-not (Test-Path -LiteralPath $EVENTS_DIR)) { return @() }

    $events = @()
    $files = @(Get-ChildItem -LiteralPath $EVENTS_DIR -Filter "events-*.jsonl" -File | Sort-Object Name)
    foreach ($file in $files) {
        $lineNumber = 0
        foreach ($line in Get-Content -LiteralPath $file.FullName -Encoding UTF8) {
            $lineNumber++
            if ([string]::IsNullOrWhiteSpace($line)) { continue }
            try {
                $event = $line | ConvertFrom-Json
                $event | Add-Member -NotePropertyName "_file" -NotePropertyValue $file.Name -Force
                $event | Add-Member -NotePropertyName "_line" -NotePropertyValue $lineNumber -Force
                $events += $event
            } catch {
                # Ignore malformed event lines in the read model; Event Bus read reports parse errors separately.
            }
        }
    }
    return @($events | Sort-Object timestamp, id)
}

function Increment-ObjectCount {
    param($Object, [string]$Key)
    if ([string]::IsNullOrWhiteSpace($Key)) { return }
    if (-not ($Object.PSObject.Properties.Name -contains $Key)) {
        $Object | Add-Member -NotePropertyName $Key -NotePropertyValue 0
    }
    $Object.$Key = [int]$Object.$Key + 1
}

function New-EmptyReadModel {
    [pscustomobject][ordered]@{
        schema_version = 1
        generated_at = (Get-Date).ToString("o")
        source = "event_bus"
        events = [pscustomobject][ordered]@{
            cursor = [pscustomobject][ordered]@{
                total_events = 0
                last_event_id = $null
                last_timestamp = $null
                last_file = $null
                last_line = 0
            }
            by_type = [pscustomobject][ordered]@{}
            by_source = [pscustomobject][ordered]@{}
            recent = @()
        }
        tasks = [pscustomobject][ordered]@{
            active = $null
            last_completed = $null
            recent = @()
        }
        metrics = [pscustomobject][ordered]@{
            latest = [pscustomobject][ordered]@{}
        }
        dashboard = [pscustomobject][ordered]@{
            last_refresh = $null
        }
    }
}

function Apply-EventToReadModel {
    param($Model, $Event)

    $Model.events.cursor.total_events = [int]$Model.events.cursor.total_events + 1
    $Model.events.cursor.last_event_id = $Event.id
    $Model.events.cursor.last_timestamp = $Event.timestamp
    $Model.events.cursor.last_file = $Event._file
    $Model.events.cursor.last_line = $Event._line

    Increment-ObjectCount -Object $Model.events.by_type -Key ([string]$Event.event_type)
    Increment-ObjectCount -Object $Model.events.by_source -Key ([string]$Event.source)

    $Model.events.recent = @(
        @($Model.events.recent) +
        [pscustomobject][ordered]@{
            id = $Event.id
            timestamp = $Event.timestamp
            source = $Event.source
            event_type = $Event.event_type
            project = $Event.project
            task_id = $Event.task_id
        }
    ) | Select-Object -Last 20

    if ($Event.event_type -in @("TaskCreated", "TaskStarted", "TaskStepCompleted")) {
        $Model.tasks.active = [pscustomobject][ordered]@{
            id = $Event.task_id
            project = $Event.project
            event_type = $Event.event_type
            timestamp = $Event.timestamp
            title = $Event.payload.title
        }
        $Model.tasks.recent = @(@($Model.tasks.recent) + $Model.tasks.active) | Select-Object -Last 20
    }

    if ($Event.event_type -eq "TaskCompleted") {
        $Model.tasks.last_completed = [pscustomobject][ordered]@{
            id = $Event.task_id
            project = $Event.project
            timestamp = $Event.timestamp
        }
        if ($Model.tasks.active -and $Model.tasks.active.id -eq $Event.task_id) {
            $Model.tasks.active = $null
        }
    }

    if ($Event.event_type -eq "MetricRecorded") {
        $metricType = [string]($Event.payload.metric_type)
        if (-not [string]::IsNullOrWhiteSpace($metricType)) {
            $Model.metrics.latest | Add-Member -NotePropertyName $metricType -NotePropertyValue ([pscustomobject][ordered]@{
                value = $Event.payload.value
                unit = $Event.payload.unit
                task_id = $Event.task_id
                timestamp = $Event.timestamp
            }) -Force
        }
    }

    if ($Event.event_type -eq "DashboardRefreshed") {
        $Model.dashboard.last_refresh = [pscustomobject][ordered]@{
            status = $Event.payload.status
            duration_seconds = $Event.payload.duration_seconds
            timestamp = $Event.timestamp
            event_id = $Event.id
        }
    }
}

function New-ReadModel {
    $model = New-EmptyReadModel
    foreach ($event in Read-EventFiles) {
        Apply-EventToReadModel -Model $model -Event $event
    }
    return $model
}

switch ($Action) {
    "Rebuild" {
        New-Item -ItemType Directory -Path $DASHBOARD_DIR -Force | Out-Null
        $model = New-ReadModel
        ConvertTo-JsonSafe $model | Set-Content -LiteralPath $READ_MODEL_FILE -Encoding UTF8
        Write-Result $model
    }
    "Read" {
        if (Test-Path -LiteralPath $READ_MODEL_FILE) {
            $model = Get-Content -LiteralPath $READ_MODEL_FILE -Raw -Encoding UTF8 | ConvertFrom-Json
        } else {
            $model = New-EmptyReadModel
        }
        Write-Result $model
    }
    "Health" {
        $health = [pscustomobject][ordered]@{
            schema_version = 1
            ok = $true
            events_dir = $EVENTS_DIR
            read_model_path = $READ_MODEL_FILE
            exists = (Test-Path -LiteralPath $READ_MODEL_FILE)
        }
        Write-Result $health
    }
}
