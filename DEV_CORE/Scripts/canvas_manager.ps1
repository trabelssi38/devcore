# canvas_manager.ps1 -- DEV_CORE v9.0
# Gere le canvas symbolique (Mermaid) et le dechargement de contexte (Refs)
# Usage : & "canvas_manager.ps1" -Action Update
#         & "canvas_manager.ps1" -Action Offload -Content "..." -TaskId "T-02" -Type "log"
#         & "canvas_manager.ps1" -Action Fetch -NodeId "T02_log_a1b2"

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("Update", "Offload", "Fetch", "Test")]
    [string]$Action,
    
    [string]$Content,
    [string]$TaskId,
    [string]$Type = "log", # "log", "code", "test", "spec"
    [string]$NodeId
)

$DEV_CORE      = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\devcore\DEV_CORE" }
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT)     { $env:DEVCORE_DATA_ROOT }     else { "C:\devcore\DEV_CORE_DATA" }
$TODAY         = Get-Date -Format "yyyy-MM-dd"

# 1. Resoudre le projet actif
$projName = & "$DEV_CORE\Scripts\Get-ActiveProject.ps1"
if (-not $projName) {
    Write-Error "Impossible de recuperer le projet actif."
    exit 1
}

$refsDir = "$DEV_CORE_DATA\Refs\$projName"
if (-not (Test-Path $refsDir)) {
    New-Item -ItemType Directory -Path $refsDir -Force | Out-Null
}

switch ($Action) {
    "Update" {
        # 1. Lire les taches actives
        $tFile = "$DEV_CORE_DATA\Memory\$projName\tasks.json"
        if (-not (Test-Path $tFile)) {
            Write-Host "tasks.json absent pour le projet $projName"
            exit 0
        }
        
        try {
            $board = Get-Content $tFile -Raw -Encoding UTF8 | ConvertFrom-Json
            $activeTask = $board.tasks | Where-Object { $_.status -eq "active" }
            
            if (-not $activeTask) {
                # Pas de tache active, canvas vide ou minimal
                $minimalCanvas = '```mermaid' + "`n" + 'graph TD' + "`n" + '    Start[Pas de tache active]' + "`n" + '```'
                $minimalCanvas | Set-Content "$refsDir\canvas.md" -Encoding UTF8
                exit 0
            }
            
            $tid = $activeTask.id
            $title = $activeTask.title
            $mode = $activeTask.mode
            
            $mermaid = '```mermaid' + "`n" + 'graph TD' + "`n"
            $format = '    {0}["{0}: {1} ({2})"]' + "`n"
            $mermaid += $format -f $tid, $title, $mode
            
            # Ajouter les etapes
            if ($activeTask.PSObject.Properties["steps"]) {
                $idx = 1
                foreach ($s in $activeTask.steps) {
                    $sId = "{0}_S{1}" -f $tid, $idx
                    $sTitle = $s.title
                    $sDone = if ($s.done) { " [v]" } else { "" }
                    
                    $stepFormat = '    {0}("{1}. {2}{3}")' + "`n"
                    $mermaid += $stepFormat -f $sId, $idx, $sTitle, $sDone
                    
                    $linkFormat = '    {0} --> {1}' + "`n"
                    $mermaid += $linkFormat -f $tid, $sId
                    
                    $idx++
                }
            }
            
            # Ajouter les references de fichiers decharges s'il y en a pour cette tache
            $taskRefsDir = "{0}\{1}" -f $refsDir, $tid
            if (Test-Path $taskRefsDir) {
                $files = Get-ChildItem -Path $taskRefsDir -Filter "*.md" -File
                foreach ($f in $files) {
                    $nId = $f.BaseName
                    # nId format ex: T02_log_a1b2
                    $nParts = $nId -split "_"
                    $nType = if ($nParts.Count -gt 1) { $nParts[1] } else { "ref" }
                    
                    $lines = (Get-Content $f.FullName).Count
                    
                    $fileFormat = '    {0}{{"{0} ({1}, {2} lines)"}}' + "`n"
                    $mermaid += $fileFormat -f $nId, $nType, $lines
                    
                    $dotFormat = '    {0} -.-> {1}' + "`n"
                    $mermaid += $dotFormat -f $tid, $nId
                }
            }
            
            $mermaid += '```'
            
            # Enregistrer le canvas
            $mermaid | Set-Content "$refsDir\canvas.md" -Encoding UTF8
            Write-Host "Canvas Mermaid mis a jour avec succes."
        } catch {
            Write-Error "Echec de la mise a jour du canvas: $_"
        }
    }
    
    "Offload" {
        if (-not $Content -or -not $TaskId) {
            Write-Error "Arguments manquants pour Offload: Content et TaskId requis."
            exit 1
        }
        
        $taskRefsDir = "{0}\{1}" -f $refsDir, $TaskId
        if (-not (Test-Path $taskRefsDir)) {
            New-Item -ItemType Directory -Path $taskRefsDir -Force | Out-Null
        }
        
        # Generer un node_id unique deterministe
        # On calcule un hash MD5 du contenu pour eviter de creer des doublons
        $utf8Bytes = [System.Text.Encoding]::UTF8.GetBytes($Content)
        $md5 = [System.Security.Cryptography.MD5]::Create()
        $hashBytes = $md5.ComputeHash($utf8Bytes)
        $hashStr = ""
        foreach ($b in $hashBytes) { $hashStr += $b.ToString("x2") }
        $shortHash = $hashStr.Substring(0, 4)
        
        # ID ex: T02_log_e4c3
        # On remplace les tirets dans TaskId pour l'ID Mermaid (Mermaid n'aime pas les tirets dans les IDs de noeuds)
        $cleanTaskId = $TaskId -replace "-", ""
        $generatedNodeId = "{0}_{1}_{2}" -f $cleanTaskId, $Type, $shortHash
        
        $refFile = "{0}\{1}.md" -f $taskRefsDir, $generatedNodeId
        
        # Enregistrer le fichier
        $header = "---`nnode_id: {0}`ntask_id: {1}`ntype: {2}`ndate: {3}`n---`n`n" -f $generatedNodeId, $TaskId, $Type, (Get-Date -Format 'o')
        $finalContent = $header + $Content
        $finalContent | Set-Content $refFile -Encoding UTF8
        
        # Mettre a jour le canvas
        & $MyInvocation.MyCommand.Path -Action Update
        
        # Retourner l'ID pour l'agent
        Write-Output "OFFLOAD_SUCCESS: $generatedNodeId (decharge dans refs/)"
    }
    
    "Fetch" {
        if (-not $NodeId) {
            Write-Error "Argument NodeId manquant pour Fetch."
            exit 1
        }
        
        # Extraire le task_id a partir de NodeId (ex: T02_log_a1b2 -> task_id T-02)
        # T02_log_a1b2 -> cleanTaskId T02
        $parts = $NodeId -split "_"
        if ($parts.Count -lt 1) {
            Write-Error "Format de NodeId incorrect : $NodeId"
            exit 1
        }
        
        $cleanTaskId = $parts[0]
        # Re-former le TaskId avec tiret (ex: T02 -> T-02)
        $taskId = if ($cleanTaskId -match '^T(\d+)$') { "T-" + $Matches[1] } else { $cleanTaskId }
        
        $refFile = "{0}\{1}\{2}.md" -f $refsDir, $taskId, $NodeId
        if (-not (Test-Path $refFile)) {
            Write-Error "Reference $NodeId introuvable dans $refFile"
            exit 1
        }
        
        # Lire le fichier, passer les metadonnees yaml en en-tete
        $lines = Get-Content $refFile
        $inYaml = $false
        $contentLines = @()
        foreach ($l in $lines) {
            if ($l -eq "---") {
                $inYaml = -not $inYaml
                continue
            }
            if (-not $inYaml) {
                $contentLines += $l
            }
        }
        
        $contentLines -join "`n"
    }
    
    "Test" {
        Write-Host "Test de canvas_manager.ps1..."
        # 1. Creer une ref de test
        $testContent = "Ceci est un log de test tres volumineux pour valider le dechargement de contexte."
        $res = & $MyInvocation.MyCommand.Path -Action Offload -Content $testContent -TaskId "T-99" -Type "log"
        Write-Host "Offload Result: $res"
        
        if ($res -match "OFFLOAD_SUCCESS: (T99_log_\w+)") {
            $node = $Matches[1]
            Write-Host "Node genere : $node"
            
            # 2. Recuperer la ref de test
            $fetched = & $MyInvocation.MyCommand.Path -Action Fetch -NodeId $node
            Write-Host "Fetched Content: $fetched"
            
            if ($fetched.Trim() -eq $testContent) {
                Write-Host "Verification MATCH : OK !" -ForegroundColor Green
            } else {
                Write-Error "Verification MISMATCH !"
            }
            
            # Nettoyer
            Remove-Item "$refsDir\T-99" -Recurse -Force -ErrorAction SilentlyContinue
            Remove-Item "$refsDir\canvas.md" -Force -ErrorAction SilentlyContinue
        } else {
            Write-Error "Echec de l'offload de test."
        }
    }
}
