# task_spec_parser.ps1 -- DEV_CORE v6 Auto layer
# Parser les fichiers de spec pour extraire des taches candidates

$DEV_CORE      = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\devcore\DEV_CORE" }
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT)     { $env:DEVCORE_DATA_ROOT }     else { "C:\devcore\DEV_CORE_DATA" }
$TODAY         = Get-Date -Format "yyyy-MM-dd"
$LOG           = "$DEV_CORE_DATA\Logs\scripts\task_spec_parser_$TODAY.log"
$projName      = & "$PSScriptRoot\..\Get-ActiveProject.ps1"
$QUEUE         = "$DEV_CORE_DATA\Memory\$projName\task_spec_queue.jsonl"

function Log { param($msg,$color="Gray")
    $l = "[$(Get-Date -f HH:mm:ss)] $msg"
    Add-Content $LOG $l -ErrorAction SilentlyContinue
    Write-Host "    $l" -ForegroundColor $color
}

function Get-ModeFromContent { param($text)
    $lower = $text.ToLower()
    if ($lower -match "architecture|spec|design|decision|plan|review|refactor") { return "reasoning" }
    if ($lower -match "implement|code|tdd|api|route|endpoint|controller") { return "coding" }
    if ($lower -match "test|doc|document|readme|bulk|deploy|ci") { return "bulk" }
    return "coding"
}

Log "task_spec_parser -- analyse fichiers spec" "Cyan"

$specDir = "$DEV_CORE_DATA\Vault\docs\superpowers\specs"
if (-not (Test-Path $specDir)) {
    Log "Dossier spec introuvable : $specDir" "Yellow"
    return
}

$specFiles = Get-ChildItem $specDir -Filter "*.md" -ErrorAction SilentlyContinue
if (-not $specFiles) {
    Log "Aucun fichier spec trouve" "Gray"
    return
}

$candidates = @()

foreach ($file in $specFiles) {
    Log "Parsing : $($file.Name)" "Cyan"
    $content = Get-Content $file.FullName -Raw -Encoding UTF8

    # 1. Extraire le titre (H1)
    $title = ""
    if ($content -match '^# (.+)$') {
        $title = $Matches[1].Trim()
    } else {
        $title = $file.BaseName -replace '^\d{4}-\d{2}-\d{2}-', '' -replace '-', ' '
    }

    # 2. Parser les sections (H2, H3) comme sous-taches
    $sections = [regex]::Matches($content, '^## (.+)$', [System.Text.RegularExpressions.RegexOptions]::Multiline)
    if ($sections.Count -eq 0) {
        $sections = [regex]::Matches($content, '^### (.+)$', [System.Text.RegularExpressions.RegexOptions]::Multiline)
    }

    foreach ($section in $sections) {
        $sectionTitle = $section.Groups[1].Value.Trim()
        $mode = Get-ModeFromContent $sectionTitle
        $candidates += @{
            title = "$title - $sectionTitle"
            mode = $mode
            source = $file.Name
            source_type = "spec_header"
            detected = $TODAY
        }
        Log "  [SECTION] $sectionTitle [$mode]" "Gray"
    }

    # 3. Extraire les TODOs et CHECKLISTs
    $todoPattern = '- \[ \] (.+)'
    $todos = [regex]::Matches($content, $todoPattern)
    foreach ($todo in $todos) {
        $todoTitle = $todo.Groups[1].Value.Trim()
        $mode = Get-ModeFromContent $todoTitle
        $candidates += @{
            title = "$title - $todoTitle"
            mode = $mode
            source = $file.Name
            source_type = "todo"
            detected = $TODAY
        }
        Log "  [TODO] $todoTitle [$mode]" "Gray"
    }

    # 4. Parser frontmatter si present
    if ($content -match '^---\s*\n([\s\S]*?)\n---') {
        $fm = $Matches[1]
        if ($fm -match 'tags:\s*\[(.*?)\]') {
            $tags = $Matches[1] -split ',' | ForEach-Object { $_.Trim() }
            Log "  [TAGS] $($tags -join ', ')" "Gray"
        }
    }
}

# Sauvegarder les candidats dans la queue
if ($candidates.Count -gt 0) {
    $candidates | ForEach-Object {
        Add-Content $QUEUE ($_ | ConvertTo-Json -Compress)
    }
    Log "$($candidates.Count) candidats trouves dans les specs" "Green"
} else {
    Log "Aucun candidat trouve" "Gray"
}

