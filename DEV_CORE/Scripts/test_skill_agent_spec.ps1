# test_skill_agent_spec.ps1 -- Agent Skills spec compatibility checks
$ErrorActionPreference = "Stop"

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$skillLint = Join-Path $scriptRoot "skill_lint.ps1"
$failures = 0

function Assert-True {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) {
        Write-Host "[FAIL] $Message" -ForegroundColor Red
        $script:failures++
    }
}

$tmp = Join-Path $env:TEMP ("devcore-skill-spec-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $tmp -Force | Out-Null

try {
    $validDir = Join-Path $tmp "valid-skill"
    New-Item -ItemType Directory -Path $validDir -Force | Out-Null
@'
---
name: valid-skill
description: Use when validating Agent Skills compatible frontmatter and structure.
---

# Valid Skill

## Workflow

Follow a small deterministic workflow.
'@ | Set-Content -LiteralPath (Join-Path $validDir "SKILL.md") -Encoding UTF8

    $valid = & $skillLint -Path (Join-Path $validDir "SKILL.md") -StrictAgentSpec -Json | Out-String | ConvertFrom-Json
    Assert-True ($LASTEXITCODE -eq 0) "valid Agent Skill should pass strict spec"
    Assert-True ($valid.agent_spec_status -eq "PASS") "valid skill should have PASS agent_spec_status"

    $invalidDir = Join-Path $tmp "invalid_skill"
    New-Item -ItemType Directory -Path $invalidDir -Force | Out-Null
@'
---
name: invalid_skill
description: bad
---

# Invalid Skill
'@ | Set-Content -LiteralPath (Join-Path $invalidDir "SKILL.md") -Encoding UTF8

    & $skillLint -Path (Join-Path $invalidDir "SKILL.md") -StrictAgentSpec -Json | Out-String | ConvertFrom-Json | Out-Null
    Assert-True ($LASTEXITCODE -ne 0) "invalid Agent Skill should fail strict spec"

    $legacy = & $skillLint -Path (Join-Path $invalidDir "SKILL.md") -AgentSpec -Json | Out-String | ConvertFrom-Json
    Assert-True ($LASTEXITCODE -eq 0) "non-strict AgentSpec should not fail legacy skills"
    Assert-True ($legacy.status -eq "WARN") "legacy non-strict skill should warn without failing"
} finally {
    Remove-Item -LiteralPath $tmp -Recurse -Force -ErrorAction SilentlyContinue
}

if ($failures -gt 0) { exit 1 }
Write-Host "[OK] Agent Skills spec lint tests passed" -ForegroundColor Green
exit 0
