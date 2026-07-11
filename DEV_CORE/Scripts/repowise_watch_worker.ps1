# repowise_watch_worker.ps1 -- long-running Repowise watcher for one repo
param(
    [Parameter(Mandatory=$true)][string]$ProjectName,
    [Parameter(Mandatory=$true)][string]$ProjectPath,
    [Parameter(Mandatory=$true)][string]$RepowisePath,
    [Parameter(Mandatory=$true)][string]$LogDir
)

$ErrorActionPreference = "Continue"
$env:PYTHONIOENCODING = if ($env:PYTHONIOENCODING) { $env:PYTHONIOENCODING } else { "utf-8" }
$DEV_CORE = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\devcore\DEV_CORE" }

New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
$safeName = $ProjectName -replace '[\\/:*?"<>| ]', '_'
$logPath = Join-Path $LogDir "$safeName.log"
$docsStatePath = Join-Path $LogDir "$safeName.docs.json"
$docsRefreshMinutes = if ($env:REPOWISE_DOCS_REFRESH_MINUTES) { [int]$env:REPOWISE_DOCS_REFRESH_MINUTES } else { 60 }

function Log {
    param([string]$Message)
    $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Message"
    Add-Content -Path $logPath -Value $line -Encoding UTF8 -ErrorAction SilentlyContinue
}

function Read-JsonSafe {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) { return $null }
    try {
        $raw = Get-Content -LiteralPath $Path -Raw -Encoding UTF8
        if (-not $raw -or -not $raw.Trim()) { return $null }
        return ($raw | ConvertFrom-Json)
    } catch {
        return $null
    }
}

function Get-RepoHead {
    param([string]$Path)
    try {
        $head = (& git -C $Path rev-parse HEAD 2>$null | Select-Object -First 1)
        if ($head) { return $head.Trim() }
    } catch {}
    return $null
}

function Test-DocsRefreshRequired {
    param(
        [string]$ProjectPath,
        [string]$DocsStatePath,
        [int]$RefreshMinutes
    )

    $head = Get-RepoHead -Path $ProjectPath
    if (-not $head) {
        return [pscustomobject]@{ required = $false; head = $null; reason = "no_git_head" }
    }

    $repowiseState = Read-JsonSafe -Path (Join-Path $ProjectPath ".repowise\state.json")
    if ($repowiseState) {
        $docsEnabled = $false
        if ($repowiseState.PSObject.Properties["docs_enabled"]) {
            $docsEnabled = [bool]$repowiseState.docs_enabled
        }
        $totalPages = 0
        if ($repowiseState.PSObject.Properties["total_pages"]) {
            try { $totalPages = [int]$repowiseState.total_pages } catch { $totalPages = 0 }
        }
        if (-not $docsEnabled -or $totalPages -le 0) {
            return [pscustomobject]@{ required = $true; head = $head; reason = "docs_disabled_or_empty" }
        }
    }

    $state = Read-JsonSafe -Path $DocsStatePath
    if (-not $state -or -not $state.last_docs_commit) {
        return [pscustomobject]@{ required = $true; head = $head; reason = "missing_docs_state" }
    }

    if ([string]$state.last_docs_commit -ne $head) {
        return [pscustomobject]@{ required = $true; head = $head; reason = "new_commit" }
    }

    if ($state.refreshed_at -and $RefreshMinutes -gt 0) {
        try {
            $last = [datetimeoffset]::Parse([string]$state.refreshed_at)
            if (((Get-Date) - $last.LocalDateTime).TotalMinutes -ge $RefreshMinutes) {
                return [pscustomobject]@{ required = $true; head = $head; reason = "ttl_elapsed" }
            }
        } catch {}
    }

    return [pscustomobject]@{ required = $false; head = $head; reason = "current" }
}

function Save-DocsRefreshState {
    param(
        [string]$Path,
        [string]$Commit,
        [string]$Reason,
        [int]$ExitCode
    )

    [pscustomobject]@{
        refreshed_at = (Get-Date -Format "o")
        last_docs_commit = $Commit
        reason = $Reason
        exit_code = $ExitCode
    } | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $Path -Encoding UTF8
}

function Import-GeminiKeyForDocsRefresh {
    if ($env:GEMINI_API_KEY -or $env:GOOGLE_API_KEY) {
        return "env"
    }

    $candidateFiles = @()
    if ($env:GEMINI_API_KEY_FILE) { $candidateFiles += $env:GEMINI_API_KEY_FILE }
    if ($env:GOOGLE_API_KEY_FILE) { $candidateFiles += $env:GOOGLE_API_KEY_FILE }
    $candidateFiles += Join-Path $DEV_CORE "Config\gemini_api_key.txt"

    foreach ($candidate in $candidateFiles) {
        if ($candidate -and (Test-Path -LiteralPath $candidate)) {
            try {
                $key = (Get-Content -LiteralPath $candidate -Raw -Encoding UTF8).Trim()
                if ($key) {
                    $env:GEMINI_API_KEY = $key
                    return "file"
                }
            } catch {}
        }
    }

    return $null
}

function Invoke-RepowiseDocsRefresh {
    param(
        [string]$RepowisePath,
        [string]$ProjectPath,
        [string]$DocsStatePath,
        [int]$RefreshMinutes
    )

    $check = Test-DocsRefreshRequired -ProjectPath $ProjectPath -DocsStatePath $DocsStatePath -RefreshMinutes $RefreshMinutes
    if (-not $check.required) {
        Log "DOCS refresh skip reason=$($check.reason) head=$($check.head)"
        return
    }

    $geminiKeySource = Import-GeminiKeyForDocsRefresh
    if ($geminiKeySource) {
        Log "DOCS provider key source=gemini_$geminiKeySource"
    }

    if (-not $env:REPOWISE_PROVIDER -and
        -not $env:ANTHROPIC_API_KEY -and
        -not $env:OPENAI_API_KEY -and
        -not $env:OPENROUTER_API_KEY -and
        -not $env:OLLAMA_BASE_URL -and
        -not $env:GEMINI_API_KEY -and
        -not $env:GOOGLE_API_KEY -and
        -not $env:DEEPSEEK_API_KEY -and
        -not $env:LITELLM_API_KEY) {
        Log "DOCS refresh skip reason=provider_missing hint=set REPOWISE_PROVIDER or an API key; index-only watch continues"
        Save-DocsRefreshState -Path $DocsStatePath -Commit $check.head -Reason "provider_missing" -ExitCode 78
        return
    }

    $docsArgs = @("update", "--docs", "--no-workspace")
    if ($check.reason -eq "docs_disabled_or_empty") {
        $docsArgs = @("update", "--full", "--docs", "--no-workspace")
    }
    Log "DOCS refresh start reason=$($check.reason) head=$($check.head) args=$($docsArgs -join ' ')"
    & $RepowisePath @docsArgs $ProjectPath *>> $logPath
    $exitCode = $LASTEXITCODE
    Log "DOCS refresh exit=$exitCode"
    if ($exitCode -eq 0) {
        Save-DocsRefreshState -Path $DocsStatePath -Commit $check.head -Reason $check.reason -ExitCode $exitCode
    }
}

try {
    $resolvedProjectPath = (Resolve-Path $ProjectPath).Path
    Log "START project=$ProjectName path=$resolvedProjectPath"

    if (-not (Test-Path $RepowisePath)) {
        Log "ERROR repowise not found: $RepowisePath"
        exit 1
    }

    $env:REPOWISE_EMBEDDER = if ($env:REPOWISE_EMBEDDER) { $env:REPOWISE_EMBEDDER } else { "mock" }

    $webLanguagesPatchPath = Join-Path $DEV_CORE "Scripts\ensure_repowise_web_languages.ps1"
    if (Test-Path $webLanguagesPatchPath) {
        Log "REGISTRY patch web languages"
        & $webLanguagesPatchPath -Quiet *>> $logPath
        Log "REGISTRY patch exit=$LASTEXITCODE"
    }

    $statePath = Join-Path $resolvedProjectPath ".repowise\state.json"
    if (-not (Test-Path $statePath)) {
        Log "INIT index-only fast"
        & $RepowisePath init --index-only --mode fast --no-workspace -y --no-claude-md --no-agents --no-codex $resolvedProjectPath *>> $logPath
        Log "INIT exit=$LASTEXITCODE"
    } else {
        Log "UPDATE index-only no-docs"
        & $RepowisePath update --index-only --no-docs --no-workspace $resolvedProjectPath *>> $logPath
        Log "UPDATE exit=$LASTEXITCODE"
    }

    Invoke-RepowiseDocsRefresh -RepowisePath $RepowisePath -ProjectPath $resolvedProjectPath -DocsStatePath $docsStatePath -RefreshMinutes $docsRefreshMinutes

    Log "WATCH starting"
    & $RepowisePath watch --no-workspace $resolvedProjectPath *>> $logPath
    Log "WATCH exited exit=$LASTEXITCODE"
    exit $LASTEXITCODE
} catch {
    Log "ERROR $($_.Exception.Message)"
    exit 1
}
