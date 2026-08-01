# event_bus.ps1 -- DEV_CORE v10 -- append-only Event Bus
param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("Publish", "Read", "Tail", "Health")]
    [string]$Action,
    [string]$Id = "",
    [string]$Source = "devcore",
    [string]$EventType = "",
    [string]$Project = "",
    [string]$TaskId = "",
    [string]$CorrelationId = "",
    [string]$PayloadJson = "{}",
    [string]$Date = "",
    [int]$Limit = 50,
    [switch]$Json
)

$ErrorActionPreference = "Stop"

$SOURCE_WAS_SPECIFIED = $PSBoundParameters.ContainsKey("Source")
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT) { $env:DEVCORE_DATA_ROOT } else { (Join-Path (Split-Path -Parent $PSScriptRoot) "DEV_CORE_DATA") }
$TODAY = if ($Date) { $Date } else { Get-Date -Format "yyyy-MM-dd" }
$EVENTS_DIR = Join-Path $DEV_CORE_DATA "Bus\events"
$EVENTS_FILE = Join-Path $EVENTS_DIR "events-$TODAY.jsonl"

function Ensure-EventsDir {
    New-Item -ItemType Directory -Path $EVENTS_DIR -Force | Out-Null
    return $EVENTS_DIR
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

function New-BusEvent {
    if ([string]::IsNullOrWhiteSpace($EventType)) {
        Write-Error "EventType is required for Publish."
        exit 64
    }

    $projectName = Get-ActiveProjectName
    $eventId = if ($Id) { $Id } else { [guid]::NewGuid().ToString("n") }
    [pscustomobject][ordered]@{
        schema_version = 1
        id = $eventId
        timestamp = (Get-Date).ToString("o")
        source = $Source
        event_type = $EventType
        project = $projectName
        task_id = Get-ActiveTaskId -ProjectName $projectName
        correlation_id = if ($CorrelationId) { $CorrelationId } else { $eventId }
        payload = Read-PayloadJson
    }
}

function Read-EventFile {
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

function Test-DuplicateEvent {
    param($Candidate, $ExistingEvents)

    foreach ($event in @($ExistingEvents)) {
        if ($event.id -and $event.id -eq $Candidate.id) { return $true }
        if ($Candidate.correlation_id -and $event.correlation_id -eq $Candidate.correlation_id -and
            $event.event_type -eq $Candidate.event_type -and $event.source -eq $Candidate.source -and
            $event.task_id -eq $Candidate.task_id) {
            return $true
        }
    }
    return $false
}

function Select-Events {
    param($Events)

    $selected = @($Events)
    if ($EventType) { $selected = @($selected | Where-Object { $_.event_type -eq $EventType }) }
    if ($Project) { $selected = @($selected | Where-Object { $_.project -eq $Project }) }
    if ($TaskId) { $selected = @($selected | Where-Object { $_.task_id -eq $TaskId }) }
    if ($Source -and $SOURCE_WAS_SPECIFIED) { $selected = @($selected | Where-Object { $_.source -eq $Source }) }
    return $selected
}

function New-ReadResult {
    param([switch]$TailOnly)

    Ensure-EventsDir | Out-Null
    $read = Read-EventFile -Path $EVENTS_FILE
    $events = @(Select-Events -Events $read.events)
    if ($TailOnly) {
        $events = @($events | Select-Object -Last ([math]::Max(1, $Limit)))
    } elseif ($Limit -gt 0) {
        $events = @($events | Select-Object -First $Limit)
    }

    [pscustomobject][ordered]@{
        schema_version = 1
        date = $TODAY
        store_path = $EVENTS_FILE
        events_count = @($events).Count
        errors_count = $read.errors
        events = $events
    }
}

function New-Health {
    Ensure-EventsDir | Out-Null
    $canWrite = $false
    try {
        $probe = Join-Path $EVENTS_DIR ".health"
        "ok" | Set-Content -LiteralPath $probe -Encoding UTF8
        Remove-Item -LiteralPath $probe -Force -ErrorAction SilentlyContinue
        $canWrite = $true
    } catch {
        $canWrite = $false
    }

    [pscustomobject][ordered]@{
        schema_version = 1
        ok = $canWrite
        events_dir = $EVENTS_DIR
        store_path = $EVENTS_FILE
        writable = $canWrite
    }
}

switch ($Action) {
    "Publish" {
        Ensure-EventsDir | Out-Null
        $event = New-BusEvent
        $duplicate = $false
        if (Test-Path -LiteralPath $EVENTS_FILE) {
            $escId = [regex]::Escape($event.id)
            $duplicate = Select-String -Path $EVENTS_FILE -Pattern "`"id`"\s*:\s*`"$escId`"" -Quiet
            if (-not $duplicate -and $event.correlation_id) {
                $escCorrelation = [regex]::Escape($event.correlation_id)
                $escType = [regex]::Escape($event.event_type)
                $escTask = [regex]::Escape($event.task_id)
                $escSrc = [regex]::Escape($event.source)
                $lines = Select-String -Path $EVENTS_FILE -Pattern "`"correlation_id`"\s*:\s*`"$escCorrelation`""
                foreach ($l in $lines) {
                    $lineStr = $l.Line
                    if ($lineStr -match "`"event_type`"\s*:\s*`"$escType`"" -and
                        $lineStr -match "`"task_id`"\s*:\s*`"$escTask`"" -and
                        $lineStr -match "`"source`"\s*:\s*`"$escSrc`"") {
                        $duplicate = $true
                        break
                    }
                }
            }
        }
        if (-not $duplicate) {
            ($event | ConvertTo-Json -Depth 30 -Compress) | Add-Content -LiteralPath $EVENTS_FILE -Encoding UTF8
        }
        $result = [pscustomobject][ordered]@{
            schema_version = 1
            duplicate = $duplicate
            event = $event
            store_path = $EVENTS_FILE
        }
        if ($Json) { $result | ConvertTo-Json -Depth 30 }
        else {
            $state = if ($duplicate) { "duplicate" } else { "published" }
            Write-Host "[EVENT_BUS] $state -- $($event.event_type) $($event.id)"
        }
        exit 0
    }
    "Read" {
        $result = New-ReadResult
        if ($Json) { $result | ConvertTo-Json -Depth 30 }
        else { Write-Host "[EVENT_BUS] read OK -- $($result.events_count) event(s)" }
        exit 0
    }
    "Tail" {
        $result = New-ReadResult -TailOnly
        if ($Json) { $result | ConvertTo-Json -Depth 30 }
        else { Write-Host "[EVENT_BUS] tail OK -- $($result.events_count) event(s)" }
        exit 0
    }
    "Health" {
        $health = New-Health
        if ($Json) { $health | ConvertTo-Json -Depth 10 }
        else { Write-Host "[EVENT_BUS] health OK -- writable=$($health.writable)" }
        if ($health.ok) { exit 0 } else { exit 1 }
    }
}
