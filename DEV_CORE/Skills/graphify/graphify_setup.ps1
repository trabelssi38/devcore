# graphify_setup.ps1 -- DEV_CORE v9.0
# Installe graphify + integre dans DEV_CORE
# Usage : powershell -ExecutionPolicy Bypass -File C:\DEV_CORE\Skills\graphify\graphify_setup.ps1

$DEV_CORE      = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\DEV_CORE" }
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT)     { $env:DEVCORE_DATA_ROOT }     else { "C:\DEV_CORE_DATA" }

Write-Host ""
Write-Host "  DEV_CORE v9.0 -- Graphify Setup" -ForegroundColor Cyan
Write-Host "  -------------------------------------" -ForegroundColor DarkGray
Write-Host ""

# 1. Installer graphify
Write-Host "  1/5 Installation graphify..." -ForegroundColor Cyan
$pipOk = $false
try {
    pip install graphifyy --quiet 2>$null
    $pipOk = $true
    Write-Host "  [OK] graphifyy installe via pip" -ForegroundColor Green
} catch {
    Write-Host "  [WARN] pip indisponible -- essayer : uv tool install graphifyy" -ForegroundColor Yellow
}

# 2. Creer le dossier skill et copier SKILL.md
Write-Host "  2/5 Installation du skill..." -ForegroundColor Cyan
$skillDir = "$DEV_CORE\Skills\graphify"
New-Item -ItemType Directory -Path $skillDir -Force | Out-Null

$scriptDir = Split-Path $MyInvocation.MyCommand.Path
$skillSrc  = Join-Path $scriptDir "SKILL.md"
if (Test-Path $skillSrc) {
    Copy-Item $skillSrc "$skillDir\SKILL.md" -Force
    Write-Host "  [OK] SKILL.md installe dans $skillDir" -ForegroundColor Green
} else {
    Write-Host "  [WARN] SKILL.md non trouve a cote de ce script" -ForegroundColor Yellow
}

# 3. Creer le dossier output dans DEV_CORE_DATA
Write-Host "  3/5 Dossier output graphify..." -ForegroundColor Cyan
$graphDir = "$DEV_CORE_DATA\Vault\docs\graphify"
New-Item -ItemType Directory -Path "$graphDir\devcore-platform" -Force | Out-Null
Write-Host "  [OK] $graphDir" -ForegroundColor Green

# 4. Creer .graphifyignore a la racine DEV_CORE
Write-Host "  4/5 .graphifyignore..." -ForegroundColor Cyan
$ignoreContent = @"
# DEV_CORE -- graphifyignore
Cache/
__pycache__/
*.pyc
*.pyo
*.tmp
*.log
*.csv
*.html
Logs/
token_reports/
Backups/
qdrant_storage/
Sessions/
.git/
node_modules/
Bus/archive/
Bus/receipts/
.obsidian/
.DS_Store
Thumbs.db
"@
$ignoreContent | Set-Content "$DEV_CORE\.graphifyignore" -Encoding UTF8
Write-Host "  [OK] .graphifyignore cree" -ForegroundColor Green

# 5. Hooks clients + mise a jour registry + BOOT.md
Write-Host "  5/5 Registry + BOOT.md + hooks..." -ForegroundColor Cyan

# Hook Claude Code
try {
    graphify install 2>$null
    Write-Host "  [OK] Hooks Claude Code installes" -ForegroundColor Green
} catch {
    Write-Host "  [INFO] graphify install -- a lancer manuellement apres pip" -ForegroundColor DarkGray
}

# Mettre a jour skills_registry.json
$regPath = "$DEV_CORE\Skills\skills_registry.json"
if (Test-Path $regPath) {
    $reg    = Get-Content $regPath -Raw | ConvertFrom-Json
    $exists = $reg.skills | Where-Object { $_.id -eq "graphify" }
    if (-not $exists) {
        $newSkill = [PSCustomObject]@{
            id             = "graphify"
            name           = "Graphify Knowledge Graph"
            description    = "Knowledge graph structurel depuis code, SQL, docs, images. Complementaire a Qdrant."
            skill_path     = "$DEV_CORE\Skills\graphify\SKILL.md"
            source         = "safishamsi/graphify"
            created        = (Get-Date -Format "yyyy-MM-dd")
            last_used      = (Get-Date -Format "yyyy-MM-dd")
            usage_count    = 0
            auto_generated = $false
            token_cost_avg = 0
            tags           = @("graphify","knowledge-graph","architecture","codebase","analysis","dependencies")
            triggers       = @("/graphify","graphify","knowledge graph","architecture review","dependances","impact refactoring","codebase inconnu")
        }
        $reg.skills += $newSkill
        $reg | Add-Member -NotePropertyName "last_updated" -NotePropertyValue (Get-Date -Format "yyyy-MM-dd") -Force
        $reg | ConvertTo-Json -Depth 10 | Set-Content $regPath -Encoding UTF8
        Write-Host "  [OK] skills_registry.json mis a jour (graphify ajoute)" -ForegroundColor Green
    } else {
        Write-Host "  Graphify deja present dans le registry" -ForegroundColor Gray
    }
} else {
    Write-Host "  [WARN] skills_registry.json introuvable : $regPath" -ForegroundColor Yellow
}

# Mettre a jour BOOT.md
$bootPath = "$DEV_CORE\Config\BOOT.md"
if (Test-Path $bootPath) {
    $bootContent = Get-Content $bootPath -Raw
    if ($bootContent -notmatch "graphify") {
        $graphifyBlock = @"

## Skills -- graphify (knowledge graph)
@when task_type=architecture
@priority 88
@load Skills/graphify/SKILL.md

@when task_type=review
@priority 85
@load Skills/graphify/SKILL.md

@when task_type=onboarding
@priority 95
@load Skills/graphify/SKILL.md
"@
        ($bootContent + $graphifyBlock) | Set-Content $bootPath -Encoding UTF8
        Write-Host "  [OK] BOOT.md mis a jour" -ForegroundColor Green
    } else {
        Write-Host "  BOOT.md deja a jour" -ForegroundColor Gray
    }
} else {
    Write-Host "  [WARN] BOOT.md introuvable : $bootPath" -ForegroundColor Yellow
}

# Resume final
Write-Host ""
Write-Host "  ============================================" -ForegroundColor Green
Write-Host "  [OK] Graphify installe dans DEV_CORE v9.0  " -ForegroundColor Green
Write-Host "  ============================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Skill  : $DEV_CORE\Skills\graphify\" -ForegroundColor White
Write-Host "  Output : $graphDir\" -ForegroundColor White
Write-Host ""
Write-Host "  Premier usage :" -ForegroundColor DarkGray
Write-Host "    cd C:\DEV_CORE" -ForegroundColor White
Write-Host "    /graphify Tools\devcore     (Claude Code)" -ForegroundColor White
Write-Host "    `$graphify Tools\devcore     (Codex)" -ForegroundColor White
Write-Host ""
Write-Host "  Codex -- activer multi-agent dans ~/.codex/config.toml :" -ForegroundColor DarkGray
Write-Host "    [features]" -ForegroundColor Gray
Write-Host "    multi_agent = true" -ForegroundColor Gray
Write-Host ""