# task_service.ps1 -- DEV_CORE v10 -- Task Service adapter
param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("Path", "Read", "Add", "Next", "Complete", "Step", "Edit", "Pause", "Skip", "Sync")]
    [string]$Action,
    [string]$Id = "",
    [string]$Title = "",
    [ValidateSet("reasoning", "coding", "bulk")]
    [string]$Mode = "coding",
    [string]$DependsOn = "",
    [string]$Reason = "",
    [string]$InputPath = "",
    [int]$Steps = 0,
    [int]$StepNumber = 0,
    [switch]$Force,
    [switch]$Json
)

$ErrorActionPreference = "Stop"
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT) { $env:DEVCORE_DATA_ROOT } else { (Join-Path (Split-Path -Parent $PSScriptRoot) "DEV_CORE_DATA") }
$EVENT_BUS = Join-Path $PSScriptRoot "event_bus.ps1"

function Get-TaskServiceProject {
    $currentPath = (Get-Location).Path
    if ($env:DEVCORE_ACTIVE_PROJECT_NAME -and $env:DEVCORE_ACTIVE_PROJECT_PWD -eq $currentPath) {
        return $env:DEVCORE_ACTIVE_PROJECT_NAME
    }

    $projectScript = Join-Path $PSScriptRoot "Get-ActiveProject.ps1"
    if (Test-Path -LiteralPath $projectScript) {
        return ((& $projectScript) | Select-Object -First 1).Trim()
    }
    return "devcore"
}

function Get-TaskBoardPath {
    $project = Get-TaskServiceProject
    return (Join-Path $DEV_CORE_DATA "Memory\$project\tasks.json")
}

function Initialize-TaskBoard {
    param([string]$Path)

    $parent = Split-Path -Parent $Path
    if (-not (Test-Path -LiteralPath $parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }

    if (-not (Test-Path -LiteralPath $Path)) {
        [pscustomobject]@{
            project = Get-TaskServiceProject
            current_task = $null
            tasks = @()
        } | ConvertTo-Json -Depth 5 | Set-Content $Path -Encoding UTF8
    }
}

function Read-TaskBoard {
    $path = Get-TaskBoardPath
    Initialize-TaskBoard -Path $path
    return Get-Content $path -Raw -Encoding UTF8 | ConvertFrom-Json
}

function Write-TaskBoard {
    param($Board)

    $path = Get-TaskBoardPath
    $Board | ConvertTo-Json -Depth 10 | Set-Content $path -Encoding UTF8
}

function Publish-TaskEvent {
    param(
        [Parameter(Mandatory=$true)][string]$EventType,
        [Parameter(Mandatory=$true)]$Task,
        [string]$EventId = "",
        [hashtable]$Payload = @{}
    )

    if (-not (Test-Path -LiteralPath $EVENT_BUS)) { return }
    try {
        $project = Get-TaskServiceProject
        $taskId = [string]$Task.id
        $id = if ($EventId) { $EventId } else { "$project-$taskId-$EventType" }
        $eventPayload = [ordered]@{
            id = $taskId
            title = [string]$Task.title
            mode = [string]$Task.mode
            status = [string]$Task.status
            steps_done = if ($Task.PSObject.Properties["steps_done"]) { [int]$Task.steps_done } else { 0 }
            steps_total = if ($Task.PSObject.Properties["steps_total"]) { [int]$Task.steps_total } else { 1 }
        }
        foreach ($key in $Payload.Keys) {
            $eventPayload[$key] = $Payload[$key]
        }
        $payloadJson = $eventPayload | ConvertTo-Json -Depth 10 -Compress
        & $EVENT_BUS -Action Publish -Id $id -Source "task_service" -Project $project -TaskId $taskId -EventType $EventType -CorrelationId $id -PayloadJson $payloadJson 6>$null | Out-Null
    } catch {}
}

function Add-Task {
    param(
        [Parameter(Mandatory=$true)][string]$TaskTitle,
        [Parameter(Mandatory=$true)][string]$TaskMode,
        [string]$TaskDependsOn = ""
    )

    if ([string]::IsNullOrWhiteSpace($TaskTitle)) {
        Write-Host "  Task Service: titre requis" -ForegroundColor Red
        exit 64
    }

    $requestedWorktree = $env:DEVCORE_ACTIVE_WORKTREE_NAME
    $board = Read-TaskBoard
    $nums = $board.tasks | Where-Object { $_.id -match "^T-(\d+)$" } |
        ForEach-Object { [int]($_.id -replace "T-", "") }
    $next = if ($nums) { [int](($nums | Measure-Object -Maximum).Maximum) + 1 } else { 1 }
    $id = "T-{0:D2}" -f $next

    $task = [pscustomobject]@{
        id = $id
        title = $TaskTitle
        mode = $TaskMode
        status = "todo"
        steps_total = 1
        steps_done = 0
        depends_on = if ($TaskDependsOn) { "T-$TaskDependsOn" } else { $null }
        worktree = if ($requestedWorktree) { $requestedWorktree } elseif ($env:DEVCORE_ACTIVE_WORKTREE_NAME) { $env:DEVCORE_ACTIVE_WORKTREE_NAME } else { "main" }
    }

    $board.tasks += $task
    Write-TaskBoard -Board $board
    Publish-TaskEvent -EventType "TaskCreated" -Task $task -Payload @{ depends_on = $task.depends_on; worktree = $task.worktree }
    return $task
}

function Get-NextTask {
    $board = Read-TaskBoard
    $current = $board.tasks | Where-Object { $_.status -eq "active" } | Select-Object -First 1

    if (-not $current) {
        $doneIds = ($board.tasks | Where-Object { $_.status -eq "done" }).id
        $current = $board.tasks | Where-Object {
            $_.status -eq "todo" -and (
                -not $_.depends_on -or $doneIds -contains $_.depends_on
            )
        } | Select-Object -First 1
    }

    if (-not $current) {
        return $null
    }

    if ($current.status -eq "todo") {
        $current.status = "active"
        $current | Add-Member -NotePropertyName "started_at" -NotePropertyValue (Get-Date -Format "o") -Force
        $board.current_task = $current.id
        Write-TaskBoard -Board $board
        Publish-TaskEvent -EventType "TaskStarted" -Task $current -Payload @{ started_at = $current.started_at }

        $ephPath = Join-Path $DEV_CORE_DATA "Runtime\ephemeral_session.json"
        if (Test-Path -LiteralPath $ephPath) {
            Remove-Item -LiteralPath $ephPath -Force -ErrorAction SilentlyContinue
        }
    }

    return $current
}

function Complete-Task {
    param([switch]$ForceComplete)

    $board = Read-TaskBoard
    $current = $board.tasks | Where-Object { $_.status -eq "active" } | Select-Object -First 1
    if (-not $current) {
        return $null
    }

    $stepsTotal = if ($current.PSObject.Properties["steps_total"]) { [int]$current.steps_total } else { 1 }
    $stepsDone = if ($current.PSObject.Properties["steps_done"]) { [int]$current.steps_done } else { 1 }
    if ($stepsDone -lt $stepsTotal -and -not $ForceComplete) {
        Write-Host "  Task Service: $stepsDone/$stepsTotal etapes completees" -ForegroundColor Yellow
        exit 65
    }

    if ($stepsDone -lt $stepsTotal) {
        $current.steps_done = $stepsTotal
    }

    $current.status = "done"
    $current | Add-Member -NotePropertyName "completed_at" -NotePropertyValue (Get-Date -Format "o") -Force

    $doneIds = ($board.tasks | Where-Object { $_.status -eq "done" }).id
    $nextTask = $board.tasks | Where-Object {
        $_.status -eq "todo" -and (
            -not $_.depends_on -or $doneIds -contains $_.depends_on
        )
    } | Select-Object -First 1

    Write-TaskBoard -Board $board
    Publish-TaskEvent -EventType "TaskCompleted" -Task $current -Payload @{ completed_at = $current.completed_at }

    return [pscustomobject]@{
        completed = $current
        next = $nextTask
    }
}

function Complete-Step {
    param([int]$TargetStep = 0)

    $board = Read-TaskBoard
    $current = $board.tasks | Where-Object { $_.status -eq "active" } | Select-Object -First 1
    if (-not $current) {
        return $null
    }

    $message = ""
    if (-not $current.steps -or $current.steps.Count -eq 0) {
        $current.steps_done = [math]::Min(([int]$current.steps_done) + 1, [int]$current.steps_total)
        $message = "Step $($current.steps_done)/$($current.steps_total) pour $($current.id)"
    } else {
        if ($TargetStep -eq 0) {
            $step = $current.steps | Where-Object { -not $_.done } | Select-Object -First 1
        } else {
            $step = $current.steps | Where-Object { $_.id -eq $TargetStep } | Select-Object -First 1
        }

        if (-not $step) {
            $message = "Toutes les steps sont deja terminees."
        } else {
            $step.done = $true
            $current.steps_done = @($current.steps | Where-Object { $_.done }).Count
            $message = "Step $($step.id) done : $($step.title)"
        }
    }

    Write-TaskBoard -Board $board
    Publish-TaskEvent -EventType "TaskStepCompleted" -Task $current -EventId "$(Get-TaskServiceProject)-$($current.id)-TaskStepCompleted-$($current.steps_done)" -Payload @{ message = $message; complete = ([int]$current.steps_done -ge [int]$current.steps_total) }

    return [pscustomobject]@{
        task = $current
        complete = ([int]$current.steps_done -ge [int]$current.steps_total)
        message = $message
    }
}

function Edit-Task {
    param(
        [Parameter(Mandatory=$true)][string]$TaskId,
        [string]$TaskTitle = "",
        [string]$TaskMode = "",
        [int]$TaskSteps = 0,
        [switch]$UpdateTitle,
        [switch]$UpdateMode,
        [switch]$UpdateSteps
    )

    if ([string]::IsNullOrWhiteSpace($TaskId)) {
        Write-Host "  Task Service: id requis" -ForegroundColor Red
        exit 64
    }

    $board = Read-TaskBoard
    $task = $board.tasks | Where-Object { $_.id -eq $TaskId } | Select-Object -First 1
    if (-not $task) {
        Write-Host "  Task Service: tache $TaskId non trouvee" -ForegroundColor Red
        exit 66
    }

    $changes = @()
    if ($UpdateTitle) {
        if ([string]::IsNullOrWhiteSpace($TaskTitle)) {
            Write-Host "  Task Service: titre vide" -ForegroundColor Red
            exit 64
        }
        $task.title = $TaskTitle
        $changes += "title"
    }

    if ($UpdateMode) {
        $task.mode = $TaskMode
        $changes += "mode"
    }

    if ($UpdateSteps) {
        if ($TaskSteps -lt 1) {
            Write-Host "  Task Service: steps_total doit etre >= 1" -ForegroundColor Red
            exit 64
        }
        $task.steps_total = $TaskSteps
        if ($task.PSObject.Properties["steps_done"] -and [int]$task.steps_done -gt $TaskSteps) {
            $task.steps_done = $TaskSteps
        }
        $changes += "steps_total"
    }

    if ($changes.Count -gt 0) {
        Write-TaskBoard -Board $board
    }

    return [pscustomobject]@{
        task = $task
        changed = ($changes.Count -gt 0)
        changes = $changes
    }
}

function Pause-Task {
    $board = Read-TaskBoard
    $current = $board.tasks | Where-Object { $_.status -eq "active" } | Select-Object -First 1
    if (-not $current) {
        return $null
    }

    $current.status = "paused"
    $current | Add-Member -NotePropertyName "paused_at" -NotePropertyValue (Get-Date -Format "o") -Force
    $board.current_task = $null
    Write-TaskBoard -Board $board

    return [pscustomobject]@{
        task = $current
    }
}

function Skip-Task {
    param([string]$SkipReason = "")

    $board = Read-TaskBoard
    $current = $board.tasks | Where-Object { $_.status -eq "active" } | Select-Object -First 1
    if (-not $current) {
        return $null
    }

    $current.status = "skipped"
    $current | Add-Member -NotePropertyName "skipped_at" -NotePropertyValue (Get-Date -Format "o") -Force
    if (-not [string]::IsNullOrWhiteSpace($SkipReason)) {
        $current | Add-Member -NotePropertyName "skipped_reason" -NotePropertyValue $SkipReason -Force
    }

    $board.current_task = $null
    Write-TaskBoard -Board $board

    return [pscustomobject]@{
        task = $current
    }
}

function Sync-Tasks {
    param([Parameter(Mandatory=$true)][string]$SuggestionsPath)

    if (-not (Test-Path -LiteralPath $SuggestionsPath)) {
        Write-Host "  Task Service: fichier de suggestions introuvable" -ForegroundColor Red
        exit 66
    }

    $parsedSuggestions = Get-Content $SuggestionsPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $suggestions = @($parsedSuggestions | ForEach-Object { $_ })
    $board = Read-TaskBoard
    $existingIds = @($board.tasks | ForEach-Object { $_.id })
    $existingTitles = @($board.tasks | ForEach-Object { $_.title })
    $nums = @($board.tasks | Where-Object { $_.id -match "^T-(\d+)$" } |
        ForEach-Object { [int]($_.id -replace "T-", "") })
    $nextNum = if ($nums.Count -gt 0) {
        [int](($nums | Measure-Object -Maximum).Maximum) + 1
    } else {
        1
    }
    $addedTasks = @()

    foreach ($suggestion in $suggestions) {
        $id = [string]$suggestion.id
        if ([string]::IsNullOrWhiteSpace($id)) {
            while (("T-{0:D2}" -f $nextNum) -in $existingIds) {
                $nextNum++
            }
            $id = "T-{0:D2}" -f $nextNum
        }

        $title = if ($suggestion.title) { [string]$suggestion.title } else { [string]$suggestion.reason }
        if ([string]::IsNullOrWhiteSpace($title) -or $id -in $existingIds -or $title -in $existingTitles) {
            continue
        }

        $status = if ($suggestion.status) { [string]$suggestion.status } else { "todo" }
        $task = [pscustomobject]@{
            id = $id
            title = $title
            mode = if ($suggestion.mode) { [string]$suggestion.mode } else { "coding" }
            status = $status
            steps_total = if ($null -ne $suggestion.steps_total) { [int]$suggestion.steps_total } else { 1 }
            steps_done = if ($null -ne $suggestion.steps_done) { [int]$suggestion.steps_done } else { 0 }
            depends_on = if ($suggestion.depends_on) { [string]$suggestion.depends_on } else { $null }
            source = $suggestion.source
            worktree = if ($suggestion.worktree) { [string]$suggestion.worktree } elseif ($env:DEVCORE_ACTIVE_WORKTREE_NAME) { $env:DEVCORE_ACTIVE_WORKTREE_NAME } else { "main" }
            details = $suggestion.details
            steps = $suggestion.steps
            started_at = if ($suggestion.started_at) { $suggestion.started_at } elseif ($status -eq "done") { [datetime]::Now.AddHours(-1).ToString("o") } elseif ($status -eq "active") { [datetime]::Now.ToString("o") } else { $null }
            completed_at = if ($suggestion.completed_at) { $suggestion.completed_at } elseif ($status -eq "done") { [datetime]::Now.ToString("o") } else { $null }
        }

        $board.tasks += $task
        $existingIds += $id
        $existingTitles += $title
        $addedTasks += $task
        $nextNum++
    }

    if ($addedTasks.Count -gt 0) {
        Write-TaskBoard -Board $board
    }

    return [pscustomobject]@{
        added = $addedTasks.Count
        tasks = $addedTasks
    }
}

switch ($Action) {
    "Path" {
        $boardPath = Get-TaskBoardPath
        Write-Output $boardPath
        exit 0
    }
    "Read" {
        $board = Read-TaskBoard
        if ($Json) { $board | ConvertTo-Json -Depth 10 }
        else { Write-Output $board }
        exit 0
    }
    "Add" {
        $task = Add-Task -TaskTitle $Title -TaskMode $Mode -TaskDependsOn $DependsOn
        if ($Json) {
            $task | ConvertTo-Json -Depth 5
        } else {
            Write-Host "  [OK] Tache ajoutee : $($task.id) [$Mode] -- $Title" -ForegroundColor Green
        }
        exit 0
    }
    "Next" {
        $task = Get-NextTask
        if ($Json) {
            if ($task) { $task | ConvertTo-Json -Depth 5 }
            else { "null" }
        } elseif ($task) {
            Write-Host "  [OK] Tache active : $($task.id) [$($task.mode)] -- $($task.title)" -ForegroundColor Green
        } else {
            Write-Host "  Aucune tache disponible." -ForegroundColor Yellow
        }
        exit 0
    }
    "Complete" {
        $result = Complete-Task -ForceComplete:$Force
        if ($Json) {
            if ($result) { $result | ConvertTo-Json -Depth 8 }
            else { "null" }
        } elseif ($result) {
            Write-Host "  [OK] Tache terminee : $($result.completed.id)" -ForegroundColor Green
        } else {
            Write-Host "  Aucune tache active -- dc next task" -ForegroundColor Yellow
        }
        exit 0
    }
    "Step" {
        $result = Complete-Step -TargetStep $StepNumber
        if ($Json) {
            if ($result) { $result | ConvertTo-Json -Depth 8 }
            else { "null" }
        } elseif ($result) {
            Write-Host "  [OK] $($result.message)" -ForegroundColor Green
            Write-Host "  Progress : $($result.task.steps_done)/$($result.task.steps_total)" -ForegroundColor Cyan
        } else {
            Write-Host "  Aucune tache active." -ForegroundColor Yellow
        }
        exit 0
    }
    "Edit" {
        $result = Edit-Task `
            -TaskId $Id `
            -TaskTitle $Title `
            -TaskMode $Mode `
            -TaskSteps $Steps `
            -UpdateTitle:$PSBoundParameters.ContainsKey("Title") `
            -UpdateMode:$PSBoundParameters.ContainsKey("Mode") `
            -UpdateSteps:$PSBoundParameters.ContainsKey("Steps")
        if ($Json) {
            $result | ConvertTo-Json -Depth 8
        } elseif ($result.changed) {
            Write-Host "  [OK] Tache $Id mise a jour." -ForegroundColor Green
        } else {
            Write-Host "  Aucune modification specifiee. Exemple: dc task edit T-05 -Mode bulk -Steps 5" -ForegroundColor Yellow
        }
        exit 0
    }
    "Pause" {
        $result = Pause-Task
        if ($Json) {
            if ($result) { $result | ConvertTo-Json -Depth 8 }
            else { "null" }
        } elseif ($result) {
            Write-Host "  [OK] Tache $($result.task.id) mise en pause -- dc next task pour reprendre" -ForegroundColor Green
        } else {
            Write-Host "  Aucune tache active a mettre en pause." -ForegroundColor Yellow
        }
        exit 0
    }
    "Skip" {
        $result = Skip-Task -SkipReason $Reason
        if ($Json) {
            if ($result) { $result | ConvertTo-Json -Depth 8 }
            else { "null" }
        } elseif ($result) {
            Write-Host "  [OK] Tache $($result.task.id) passee (skipped)." -ForegroundColor Green
        } else {
            Write-Host "  Aucune tache active a passer." -ForegroundColor Yellow
        }
        exit 0
    }
    "Sync" {
        if ([string]::IsNullOrWhiteSpace($InputPath)) {
            Write-Host "  Task Service: InputPath requis" -ForegroundColor Red
            exit 64
        }
        $result = Sync-Tasks -SuggestionsPath $InputPath
        if ($Json) {
            $result | ConvertTo-Json -Depth 10
        } else {
            Write-Host "  [OK] $($result.added) taches synchronisees." -ForegroundColor Green
        }
        exit 0
    }
}
