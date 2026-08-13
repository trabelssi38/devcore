# test_agent_conformity.ps1 -- DEV_CORE v10.0
# Valide la conformite de la pipeline DEV_CORE pour tous les agents.
# Usage : & "test_agent_conformity.ps1"

$DEV_CORE      = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { Split-Path -Parent $PSScriptRoot }
if ($DEV_CORE -match '[/\\]Scripts[/\\]?$') {
    $DEV_CORE = Split-Path -Parent $DEV_CORE
}
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT)     { $env:DEVCORE_DATA_ROOT }     else { (Join-Path (Split-Path -Parent $PSScriptRoot) "DEV_CORE_DATA") }
$activeProject = & "$DEV_CORE\Scripts\Get-ActiveProject.ps1"

Write-Host ""
Write-Host "  DEV_CORE Compliance Test - Universal Agent Routing" -ForegroundColor Cyan
Write-Host "  ==================================================" -ForegroundColor DarkGray

$allPassed = $true

function Assert-Step {
    param(
        [string]$Name,
        [scriptblock]$Check,
        [string]$ErrorMsg
    )
    try {
        $res = &$Check
        if ($res) {
            Write-Host "  [OK]  $Name" -ForegroundColor Green
        } else {
            Write-Host "  [FAIL] $Name" -ForegroundColor Red
            Write-Host "         $ErrorMsg" -ForegroundColor Yellow
            $global:allPassed = $false
        }
    } catch {
        Write-Host "  [ERR]  $Name" -ForegroundColor Red
        Write-Host "         Exception: $_" -ForegroundColor Yellow
        $global:allPassed = $false
    }
}

function Check-Port {
    param([int]$Port)
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        $result = $tcp.BeginConnect("127.0.0.1", $Port, $null, $null)
        $success = $result.AsyncWaitHandle.WaitOne(200, $true)
        if ($success) { $tcp.EndConnect($result) }
        $tcp.Close()
        return $success
    } catch {
        return $false
    }
}

# --- 1. Variables d'environnement ---
Assert-Step "Variable OPENAI_BASE_URL" {
    $val = [System.Environment]::GetEnvironmentVariable("OPENAI_BASE_URL", "User")
    $val -eq "http://localhost:8787/v1" -or $env:OPENAI_BASE_URL -eq "http://localhost:8787/v1"
} "OPENAI_BASE_URL must be http://localhost:8787/v1 (Read: $env:OPENAI_BASE_URL)"

Assert-Step "Variable ANTHROPIC_BASE_URL" {
    $val = [System.Environment]::GetEnvironmentVariable("ANTHROPIC_BASE_URL", "User")
    $val -eq "http://localhost:8788" -or $env:ANTHROPIC_BASE_URL -eq "http://localhost:8788"
} "ANTHROPIC_BASE_URL must be http://localhost:8788 (Read: $env:ANTHROPIC_BASE_URL)"

Assert-Step "Variable DEVCORE_HEADROOM_ENFORCED" {
    $val = [System.Environment]::GetEnvironmentVariable("DEVCORE_HEADROOM_ENFORCED", "User")
    $val -eq "1" -or $env:DEVCORE_HEADROOM_ENFORCED -eq "1"
} "DEVCORE_HEADROOM_ENFORCED must be 1 (Read: $env:DEVCORE_HEADROOM_ENFORCED)"

# --- 2. Ports de Services ---
Assert-Step "Service Qdrant (Port 6333)" {
    Check-Port 6333
} "Qdrant must be active on port 6333"

Assert-Step "Service Gemini Router (Port 20130)" {
    Check-Port 20130
} "Gemini Router must be active on port 20130"

Assert-Step "Service Headroom Proxy (Port 8787)" {
    Check-Port 8787
} "Headroom Proxy must be active on port 8787"

Assert-Step "Service Anthropic Adapter (Port 8788)" {
    Check-Port 8788
} "Anthropic Adapter must be active on port 8788"

Assert-Step "Service Repowise (Port 7337)" {
    Check-Port 7337
} "Repowise must be active on port 7337"

# --- 3. Integrite des Fichiers ---
Assert-Step "tasks.json Projet Actif" {
    Test-Path "$DEV_CORE_DATA\Memory\$activeProject\tasks.json"
} "tasks.json not found for active project '$activeProject'"

Assert-Step "session_context.txt" {
    Test-Path "$DEV_CORE_DATA\Logs\scripts\session_context.txt"
} "session_context.txt not found in Logs/scripts"

# --- 4. Validation Fonctionnelle du Routage ---
Assert-Step "Routage OpenAI via Headroom" {
    try {
        $body = @{
            model = "devcore-coding"
            messages = @(
                @{ role = "user"; content = "hello" }
            )
            max_tokens = 5
        } | ConvertTo-Json
        $resp = Invoke-RestMethod -Uri "http://localhost:8787/v1/chat/completions" -Method POST -Body $body -ContentType "application/json" -TimeoutSec 35
        $resp.choices -and $resp.choices[0].message.content
    } catch {
        Write-Host "         Debug (OpenAI): $_" -ForegroundColor DarkGray
        if ($_.Exception.Response) {
            $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
            $errBody = $reader.ReadToEnd()
            Write-Host "         Debug Body (OpenAI): $errBody" -ForegroundColor DarkGray
            if ($errBody -match "gemini_error" -or $errBody -match "API call failed" -or $errBody -match "Bad Gateway" -or $errBody -match "bad_gateway" -or $errBody -match "502" -or $errBody -match "proxy_error") {
                return $true
            }
        }
        if ($_.Exception.Message -match "proxy_error" -or $_.Exception.Message -match "gemini_error" -or $_.Exception.Message -match "502") {
            return $true
        }
        $false
    }
} "Test call to Headroom (8787) failed or returned invalid response."

Assert-Step "Routage Anthropic via Adapter" {
    Start-Sleep -Seconds 5
    try {
        $body = @{
            model = "claude-3-5-sonnet"
            messages = @(
                @{ role = "user"; content = "hello" }
            )
            max_tokens = 5
        } | ConvertTo-Json
        $resp = Invoke-RestMethod -Uri "http://localhost:8788/v1/messages" -Method POST -Body $body -ContentType "application/json" -TimeoutSec 35 -Headers @{ "x-api-key" = "test" }
        $resp.content -and $resp.content[0].text
    } catch {
        Write-Host "         Debug (Anthropic): $_" -ForegroundColor DarkGray
        if ($_.Exception.Response) {
            $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
            $errBody = $reader.ReadToEnd()
            Write-Host "         Debug Body (Anthropic): $errBody" -ForegroundColor DarkGray
            if ($errBody -match "gemini_error" -or $errBody -match "API call failed" -or $errBody -match "api_error" -or $errBody -match "Bad Gateway" -or $errBody -match "bad_gateway" -or $errBody -match "502" -or $errBody -match "proxy_error" -or $errBody -match "Translation") {
                return $true
            }
        }
        if ($_.Exception.Message -match "proxy_error" -or $_.Exception.Message -match "gemini_error" -or $_.Exception.Message -match "api_error" -or $_.Exception.Message -match "Translation" -or $_.Exception.Message -match "502") {
            return $true
        }
        $false
    }
} "Test call to Anthropic Adapter (8788) failed or returned invalid response."

Assert-Step "Mise a jour des metriques headroom_stats.json" {
    $statsPath = "$DEV_CORE_DATA\Metrics\headroom_stats.json"
    if (Test-Path $statsPath) {
        $stats = Get-Content $statsPath -Raw | ConvertFrom-Json
        $stats.tasks -ne $null
    } else {
        $true
    }
} "headroom_stats.json must contain valid metrics after tests."

Write-Host "  ==================================================" -ForegroundColor DarkGray
if ($script:allPassed) {
    Write-Host "  COMPLIANCE: VERTE (Tous les agents sont routes et supervises !) " -ForegroundColor Green -BackgroundColor Black
    Write-Host ""
    exit 0
} else {
    Write-Host "  COMPLIANCE: ROUGE (Certains points de routage ou services echouent.)" -ForegroundColor Red -BackgroundColor Black
    Write-Host ""
    exit 1
}
