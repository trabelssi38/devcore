# task_prompt_analyzer.ps1 -- DEV_CORE v6 Auto layer
# Analyse les sessions recentes pour suggerer des taches

$DEV_CORE      = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\devcore\DEV_CORE" }
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT)     { $env:DEVCORE_DATA_ROOT }     else { "C:\devcore\DEV_CORE_DATA" }
$TODAY         = Get-Date -Format "yyyy-MM-dd"
$LOG           = "$DEV_CORE_DATA\Logs\scripts\task_prompt_analyzer_$TODAY.log"
$QUEUE         = "$DEV_CORE_DATA\Memory\task_prompt_queue.jsonl"

function Log { param($msg,$color="Gray")
    $l = "[$(Get-Date -f HH:mm:ss)] $msg"
    Add-Content $LOG $l -ErrorAction SilentlyContinue
    Write-Host "    $l" -ForegroundColor $color
}

function Get-ModeFromVerb { param($verb)
    $r = @("architecture","design","spec","decision","plan","review","reorg","organize","cleanup","refactor")
    $c = @("implement","code","build","api","route","endpoint","controller","add","create","write","developpe","corrige","migrate")
    $b = @("test","doc","document","readme","bulk","deploy","ci","optimize","profiling","lighthouse")

    if ($verb -in $r) { return "reasoning" }
    if ($verb -in $c) { return "coding" }
    if ($verb -in $b) { return "bulk" }
    return "coding"
}

Log "task_prompt_analyzer -- analyse prompts sessions" "Cyan"

$sessionDir = "$DEV_CORE_DATA\Sessions"
if (-not (Test-Path $sessionDir)) {
    Log "Dossier sessions introuvable : $sessionDir" "Yellow"
    return
}

$sessionFiles = Get-ChildItem $sessionDir -Filter "*.md" -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending | Select-Object -First 10

if (-not $sessionFiles) {
    Log "Aucune session trouvee" "Gray"
    return
}

$candidates = @()

foreach ($file in $sessionFiles) {
    Log "Analyse session : $($file.Name)" "Cyan"
    $content = Get-Content $file.FullName -Raw -Encoding UTF8 -ErrorAction SilentlyContinue

    # 1. Patterns de detection
    $patterns = @{
        "coding" = @(
            "(?i)\b(?:impl[ée]menter|coder|d[eé]velopper|ajouter|cr[ée]er|corriger|fixer|migrer)\s+[^.?!]+"
            "(?i)j[e'\s]+ai\s+(?:impl[ée]ment[ée]|cod[ée]|d[eé]velopp[ée]|ajout[ée]|cr[ée][ée]|corrig[ée]|fix[ée])\s+[^.?!]+"
        )
        "reasoning" = @(
            "(?i)\b(?:architectur|design|spec|d[ée]cision|plan|review|refactor[ée]r|r[ée]organiser)\s+[^.?!]+"
            "(?i)j[e'\s]+ai\s+(?:d[ée]cid[ée]|design[ée]|planifi[ée]|review[ée]|refactor[ée])\s+[^.?!]+"
        )
        "bulk" = @(
            "(?i)\b(?:test|doc|documentation|readme|bulk|d[ée]ploy|ci|optimisation|profiling|lighthouse)\s+[^.?!]+"
            "(?i)j[e'\s]+ai\s+(?:test[ée]|document[ée]|optimis[ée]|d[ée]ploy[ée])\s+[^.?!]+"
        )
    }

    $detected = @()
    foreach ($mode in $patterns.Keys) {
        foreach ($pattern in $($patterns[$mode])) {
            $matches = [regex]::Matches($content, $pattern)
            foreach ($match in $matches) {
                $phrase = $match.Value.Trim()
                if ($phrase.Length -gt 10 -and $phrase.Length -lt 200) {
                    $detected += @{ mode=$mode; phrase=$phrase }
                }
            }
        }
    }

    $detected | Select-Object -First 5 | ForEach-Object {
        Log "  [PATTERN] [$($_.mode)] $($_.phrase)" "Gray"
        $candidates += @{
            title = $_.phrase.Substring(0, [Math]::Min(120, $_.phrase.Length))
            mode = $_.mode
            source = $file.Name
            source_type = "prompt_analyzer"
            detected = $TODAY
        }
    }

    # 2. Mots-cles speciaux
    $keywords = @("TODO", "FIXME", "NEXT", "ENSUITE", "A FAIRE")
    foreach ($kw in $keywords) {
        $kwMatches = [regex]::Matches($content, "(?im)^.*$kw:?\s*(.+)")
        foreach ($kwMatch in $kwMatches) {
            $kTitle = $kwMatch.Groups[1].Value.Trim()
            if ($kTitle.Length -gt 5 -and $kTitle.Length -lt 150) {
                $mode = Get-ModeFromVerb ($kTitle.Split(' ')[0])
                $candidates += @{
                    title = "TODO: $kTitle"
                    mode = $mode
                    source = $file.Name
                    source_type = "keyword_$kw"
                    detected = $TODAY
                }
                Log "  [$kw] $kTitle [$mode]" "Gray"
            }
        }
    }
}

# Sauvegarder les candidats dans la queue
if ($candidates.Count -gt 0) {
    $unique = $candidates | Group-Object title | ForEach-Object { $_.Group[0] }
    $unique | ForEach-Object {
        Add-Content $QUEUE ($_ | ConvertTo-Json -Compress)
    }
    Log "$($unique.Count) candidats uniques trouves dans les sessions" "Green"
} else {
    Log "Aucun candidat trouve" "Gray"
}