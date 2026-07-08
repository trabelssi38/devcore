# ensure_repowise_watch.ps1 -- continuously scan DEV_CORE declared projects with Repowise
param(
    [string]$RepoRoot = "C:\devcore",
    [string]$RepowisePath = "",
    [switch]$StatusOnly,
    [switch]$Stop
)

$ErrorActionPreference = "Stop"

$DEV_CORE = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\devcore\DEV_CORE" }
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT) { $env:DEVCORE_DATA_ROOT } else { "C:\devcore\DEV_CORE_DATA" }
$HomeDir = [Environment]::GetFolderPath("UserProfile")
$MemoryDir = Join-Path $DEV_CORE_DATA "Memory"
$LogDir = Join-Path $DEV_CORE_DATA "Logs\scripts\repowise_watch"
$StatePath = Join-Path $DEV_CORE_DATA "Logs\scripts\repowise_watch_state.json"
$WorkerPath = Join-Path $DEV_CORE "Scripts\repowise_watch_worker.ps1"
$ProjectRegistryPath = Join-Path $DEV_CORE "Config\projects.json"

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

    return $null
}

function Read-JsonSafe {
    param([string]$Path)
    if (-not (Test-Path $Path)) { return $null }
    $raw = Get-Content $Path -Raw -Encoding UTF8 -ErrorAction SilentlyContinue
    if (-not $raw -or -not $raw.Trim()) { return $null }
    return ($raw | ConvertFrom-Json)
}

function Get-DeclaredProjectNames {
    if (-not (Test-Path $MemoryDir)) { return @() }

    $projects = @()
    Get-ChildItem $MemoryDir -Directory | ForEach-Object {
        $tasksPath = Join-Path $_.FullName "tasks.json"
        if (Test-Path $tasksPath) {
            $board = Read-JsonSafe $tasksPath
            $name = if ($board -and $board.project) { [string]$board.project } else { $_.Name }
            if ($name -and $name -notin @("default", "archive", "Patterns", "Scenarios", "Scores")) {
                $projects += $name
            }
        }
    }

    return ($projects | Sort-Object -Unique)
}

function Get-CandidateRoots {
    $roots = @($RepoRoot, "C:\src")
    if ($env:DEVCORE_PROJECT_ROOTS) {
        $roots += ($env:DEVCORE_PROJECT_ROOTS -split ';')
    }
    return $roots | Where-Object { $_ -and (Test-Path $_) } | ForEach-Object { (Resolve-Path $_).Path } | Sort-Object -Unique
}

function Get-RegisteredProjectPath {
    param([string]$ProjectName)

    $registry = Read-JsonSafe $ProjectRegistryPath
    if (-not $registry -or -not $registry.projects) { return $null }

    foreach ($project in $registry.projects) {
        if ($project.name -eq $ProjectName -and $project.path -and (Test-Path $project.path)) {
            return (Resolve-Path $project.path).Path
        }
    }

    return $null
}

function Resolve-ProjectPath {
    param([string]$ProjectName)

    $registeredPath = Get-RegisteredProjectPath -ProjectName $ProjectName
    if ($registeredPath) {
        return $registeredPath
    }

    if ($ProjectName -eq "devcore" -and (Test-Path $RepoRoot)) {
        return (Resolve-Path $RepoRoot).Path
    }

    foreach ($root in (Get-CandidateRoots)) {
        $direct = Join-Path $root $ProjectName
        if (Test-Path $direct) {
            return (Resolve-Path $direct).Path
        }
    }

    foreach ($root in (Get-CandidateRoots)) {
        foreach ($candidate in (Get-ChildItem $root -Directory -ErrorAction SilentlyContinue)) {
            $projectFile = Join-Path $candidate.FullName ".devcore\project.json"
            if (Test-Path $projectFile) {
                $project = Read-JsonSafe $projectFile
                if ($project -and $project.name -eq $ProjectName) {
                    return $candidate.FullName
                }
            }
        }
    }

    return $null
}

function Get-RepowiseWatchProcess {
    param(
        [string]$ProjectName,
        [string]$ProjectPath
    )

    $escaped = [regex]::Escape($ProjectPath)
    $escapedName = [regex]::Escape($ProjectName)
    Get-CimInstance Win32_Process -Filter "Name = 'powershell.exe' OR Name = 'pwsh.exe'" -ErrorAction SilentlyContinue |
        Where-Object {
            $_.CommandLine -and
            $_.CommandLine -match "repowise_watch_worker\.ps1" -and
            $_.CommandLine -match "-ProjectName\s+$escapedName(\s|$)" -and
            $_.CommandLine -match $escaped
        } |
        Select-Object -First 1
}

function Load-State {
    $state = Read-JsonSafe $StatePath
    if ($state) { return $state }
    return [pscustomobject]@{ updated_at = $null; projects = @() }
}

function Save-State {
    param([array]$ProjectStates)
    New-Item -ItemType Directory -Path (Split-Path $StatePath) -Force | Out-Null
    [pscustomobject]@{
        updated_at = (Get-Date -Format "o")
        projects = $ProjectStates
    } | ConvertTo-Json -Depth 8 | Set-Content $StatePath -Encoding UTF8
}

New-Item -ItemType Directory -Path $LogDir -Force | Out-Null

$resolvedRepowise = Resolve-Repowise -RequestedPath $RepowisePath
if (-not $resolvedRepowise) {
    Write-Host "[DEV_CORE] Repowise watch ERROR -- repowise executable not found"
    exit 1
}

$projectStates = @()

foreach ($name in (Get-DeclaredProjectNames)) {
    $path = Resolve-ProjectPath -ProjectName $name
    if (-not $path) {
        $projectStates += [pscustomobject]@{ project = $name; path = $null; status = "unresolved"; pid = $null }
        Write-Host "[DEV_CORE] Repowise watch WARN -- $name path unresolved"
        continue
    }

    $proc = Get-RepowiseWatchProcess -ProjectName $name -ProjectPath $path

    if ($Stop) {
        if ($proc) {
            Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
            Write-Host "[DEV_CORE] Repowise watch STOP -- $name pid=$($proc.ProcessId)"
        }
        $projectStates += [pscustomobject]@{ project = $name; path = $path; status = "stopped"; pid = $null }
        continue
    }

    if ($proc) {
        $projectStates += [pscustomobject]@{ project = $name; path = $path; status = "running"; pid = $proc.ProcessId }
        Write-Host "[DEV_CORE] Repowise watch OK -- $name pid=$($proc.ProcessId)"
        continue
    }

    if ($StatusOnly) {
        $projectStates += [pscustomobject]@{ project = $name; path = $path; status = "stopped"; pid = $null }
        Write-Host "[DEV_CORE] Repowise watch OFF -- $name"
        continue
    }

    $argList = @(
        "-ExecutionPolicy", "Bypass",
        "-NonInteractive",
        "-File", $WorkerPath,
        "-ProjectName", $name,
        "-ProjectPath", $path,
        "-RepowisePath", $resolvedRepowise,
        "-LogDir", $LogDir
    )

    $started = Start-Process -FilePath "powershell" -ArgumentList $argList -WindowStyle Hidden -PassThru -ErrorAction SilentlyContinue
    if ($started) {
        $projectStates += [pscustomObject]@{ project = $name; path = $path; status = "started"; pid = $started.Id }
        Write-Host "[DEV_CORE] Repowise watch START -- $name pid=$($started.Id)"
    } else {
        $projectStates += [pscustomobject]@{ project = $name; path = $path; status = "failed"; pid = $null }
        Write-Host "[DEV_CORE] Repowise watch ERROR -- $name failed to start"
    }
}

Save-State -ProjectStates $projectStates
Write-Host "[DEV_CORE] Repowise watch READY -- $($projectStates.Count) project(s)"
