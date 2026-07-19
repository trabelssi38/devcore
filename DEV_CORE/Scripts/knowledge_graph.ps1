# knowledge_graph.ps1 -- DEV_CORE v10 -- local regenerable knowledge graph
param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("Build", "ImpactAnalysis", "Status", "Health")]
    [string]$Action,
    [string]$RepoRoot = "",
    [string]$Target = "",
    [switch]$Json
)

$ErrorActionPreference = "Stop"

$DEV_CORE = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\devcore\DEV_CORE" }
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT) { $env:DEVCORE_DATA_ROOT } else { "C:\devcore\DEV_CORE_DATA" }
$REPO_ROOT = if ($RepoRoot) { (Resolve-Path -LiteralPath $RepoRoot).Path } else { (Resolve-Path -LiteralPath (Join-Path $DEV_CORE "..")).Path }
$KNOWLEDGE_DIR = Join-Path $DEV_CORE_DATA "Knowledge"
$GRAPH_FILE = Join-Path $KNOWLEDGE_DIR "graph.json"

function Ensure-KnowledgeDir {
    New-Item -ItemType Directory -Path $KNOWLEDGE_DIR -Force | Out-Null
}

function ConvertTo-NodeId {
    param([string]$Type, [string]$Name)
    $safe = ($Name -replace "\\", "/").Trim()
    return "$Type`:$safe"
}

function Add-GraphNode {
    param(
        [hashtable]$Nodes,
        [string]$Type,
        [string]$Id,
        [string]$Label,
        [hashtable]$Properties = @{}
    )

    if (-not $Nodes.ContainsKey($Id)) {
        $Nodes[$Id] = [ordered]@{
            id = $Id
            type = $Type
            label = $Label
            properties = [ordered]@{}
        }
    }

    foreach ($key in $Properties.Keys) {
        $Nodes[$Id].properties[$key] = $Properties[$key]
    }
}

function Add-GraphEdge {
    param(
        [hashtable]$Edges,
        [string]$From,
        [string]$To,
        [string]$Type,
        [hashtable]$Properties = @{} # Accepts 'confidence' and arbitrary fields
    )

    if ([string]::IsNullOrWhiteSpace($From) -or [string]::IsNullOrWhiteSpace($To)) { return }
    $id = "$From|$Type|$To"
    if (-not $Edges.ContainsKey($id)) {
        $Edges[$id] = [ordered]@{
            id = $id
            from = $From
            to = $To
            type = $Type
            properties = [ordered]@{}
        }
    }

    foreach ($key in $Properties.Keys) {
        $Edges[$id].properties[$key] = $Properties[$key]
    }
}

function Get-ServiceNameForPath {
    param([string]$Path)

    $normalized = ($Path -replace "\\", "/").Trim("/")
    if ($normalized -match "^DEV_CORE/([^/]+)/") { return $Matches[1] }
    if ($normalized -match "^docs/") { return "Docs" }
    if ($normalized -match "^README") { return "Docs" }
    if ($normalized -match "^AGENTS\.md$") { return "Config" }
    $parts = $normalized -split "/"
    if ($parts.Count -gt 1) { return $parts[0] }
    return "root"
}

function Read-JsonLines {
    param([string]$Directory, [string]$Pattern)

    $items = New-Object System.Collections.Generic.List[object]
    $errors = 0
    if (-not (Test-Path -LiteralPath $Directory)) {
        return [pscustomobject]@{ items = @(); errors = 0 }
    }

    foreach ($file in Get-ChildItem -LiteralPath $Directory -Filter $Pattern -File -ErrorAction SilentlyContinue) {
        foreach ($line in Get-Content -LiteralPath $file.FullName -Encoding UTF8) {
            if ([string]::IsNullOrWhiteSpace($line)) { continue }
            try {
                $obj = $line | ConvertFrom-Json
                if ($obj -is [System.Management.Automation.PSCustomObject]) {
                    $obj._source_file = $file.FullName
                } else {
                    $obj | Add-Member -NotePropertyName "_source_file" -NotePropertyValue $file.FullName -Force
                }
                $null = $items.Add($obj)
            } catch {
                $errors++
            }
        }
    }
    return [pscustomobject]@{ items = $items.ToArray(); errors = $errors }
}

function Get-RelativePathCompat {
    param([string]$BasePath, [string]$FullPath)

    $base = (Resolve-Path -LiteralPath $BasePath).Path.TrimEnd("\", "/")
    $full = (Resolve-Path -LiteralPath $FullPath).Path
    if ($full.StartsWith($base, [System.StringComparison]::OrdinalIgnoreCase)) {
        return $full.Substring($base.Length).TrimStart("\", "/")
    }
    return Split-Path -Leaf $full
}

function Get-GitCommits {
    $commits = @()
    try {
        $records = git -C $REPO_ROOT log --name-only --pretty=format:"__COMMIT__%H|%h|%cI|%s" -n 250
    } catch {
        return @()
    }

    $current = $null
    foreach ($line in $records) {
        if ($line -like "__COMMIT__*") {
            if ($current) { $commits += $current }
            $raw = $line.Substring(10)
            $parts = $raw -split "\|", 4
            $subject = if ($parts.Count -ge 4) { $parts[3] } else { "" }
            $taskId = $null
            if ($subject -match "\[(T-\d+)\]") { $taskId = $Matches[1] }
            $current = [ordered]@{
                hash = $parts[0]
                short = $parts[1]
                committed_at = $parts[2]
                subject = $subject
                task_id = $taskId
                files = @()
            }
        } elseif ($current -and -not [string]::IsNullOrWhiteSpace($line)) {
            $current.files += ($line -replace "\\", "/")
        }
    }
    if ($current) { $commits += $current }
    return $commits
}

function Add-TasksToGraph {
    param([hashtable]$Nodes, [hashtable]$Edges)

    $memoryDir = Join-Path $DEV_CORE_DATA "Memory"
    if (-not (Test-Path -LiteralPath $memoryDir)) { return }

    foreach ($taskFile in Get-ChildItem -LiteralPath $memoryDir -Filter "tasks.json" -Recurse -File -ErrorAction SilentlyContinue) {
        try { $board = Get-Content -LiteralPath $taskFile.FullName -Raw -Encoding UTF8 | ConvertFrom-Json } catch { continue }
        $project = if ($board.project) { [string]$board.project } else { Split-Path -Leaf (Split-Path -Parent $taskFile.FullName) }
        $projectId = ConvertTo-NodeId -Type "project" -Name $project
        Add-GraphNode -Nodes $Nodes -Type "project" -Id $projectId -Label $project

        foreach ($task in @($board.tasks)) {
            if (-not $task.id) { continue }
            $taskId = ConvertTo-NodeId -Type "task" -Name "$project/$($task.id)"
            Add-GraphNode -Nodes $Nodes -Type "task" -Id $taskId -Label "$($task.id) $($task.title)" -Properties @{
                project = $project
                task_id = [string]$task.id
                title = [string]$task.title
                status = [string]$task.status
                mode = [string]$task.mode
            }
            Add-GraphEdge -Edges $Edges -From $projectId -To $taskId -Type "project_task"
        }
    }
}

function Add-CommitsToGraph {
    param([hashtable]$Nodes, [hashtable]$Edges)

    foreach ($commit in Get-GitCommits) {
        $commitId = ConvertTo-NodeId -Type "commit" -Name $commit.short
        Add-GraphNode -Nodes $Nodes -Type "commit" -Id $commitId -Label $commit.short -Properties @{
            hash = $commit.hash
            short = $commit.short
            subject = $commit.subject
            committed_at = $commit.committed_at
            task_id = $commit.task_id
        }

        if ($commit.task_id) {
            $taskMatches = @($Nodes.Values | Where-Object { $_.type -eq "task" -and $_.properties.task_id -eq $commit.task_id })
            foreach ($taskNode in $taskMatches) {
                Add-GraphEdge -Edges $Edges -From $taskNode.id -To $commitId -Type "task_commit"
            }
        }

        foreach ($file in @($commit.files)) {
            $fileId = ConvertTo-NodeId -Type "file" -Name $file
            $service = Get-ServiceNameForPath -Path $file
            $serviceId = ConvertTo-NodeId -Type "service" -Name $service
            Add-GraphNode -Nodes $Nodes -Type "file" -Id $fileId -Label $file -Properties @{ path = $file; service = $service }
            Add-GraphNode -Nodes $Nodes -Type "service" -Id $serviceId -Label $service
            Add-GraphEdge -Edges $Edges -From $commitId -To $fileId -Type "commit_file"
            Add-GraphEdge -Edges $Edges -From $fileId -To $serviceId -Type "file_service"
        }
    }
}

function Add-EventsToGraph {
    param([hashtable]$Nodes, [hashtable]$Edges)

    $taskLookup = @{}
    foreach ($node in $Nodes.Values) {
        if ($node.type -eq "task" -and $node.properties.task_id) {
            $tid = [string]$node.properties.task_id
            if (-not $taskLookup.ContainsKey($tid)) {
                $taskLookup[$tid] = @()
            }
            $taskLookup[$tid] += $node.id
        }
    }

    $read = Read-JsonLines -Directory (Join-Path $DEV_CORE_DATA "Bus\events") -Pattern "events-*.jsonl"
    foreach ($event in @($read.items)) {
        if (-not $event.id) { continue }
        $eventId = ConvertTo-NodeId -Type "event" -Name $event.id
        Add-GraphNode -Nodes $Nodes -Type "event" -Id $eventId -Label "$($event.event_type) $($event.id)" -Properties @{
            event_type = [string]$event.event_type
            source = [string]$event.source
            project = [string]$event.project
            task_id = [string]$event.task_id
            timestamp = [string]$event.timestamp
        }
        $tid = [string]$event.task_id
        if ($tid -and $taskLookup.ContainsKey($tid)) {
            foreach ($targetNodeId in $taskLookup[$tid]) {
                Add-GraphEdge -Edges $Edges -From $eventId -To $targetNodeId -Type "event_task"
            }
        }
    }
    return $read.errors
}

function Add-MetricsToGraph {
    param([hashtable]$Nodes, [hashtable]$Edges)

    $taskLookup = @{}
    foreach ($node in $Nodes.Values) {
        if ($node.type -eq "task" -and $node.properties.task_id) {
            $tid = [string]$node.properties.task_id
            if (-not $taskLookup.ContainsKey($tid)) {
                $taskLookup[$tid] = @()
            }
            $taskLookup[$tid] += $node.id
        }
    }

    $read = Read-JsonLines -Directory (Join-Path $DEV_CORE_DATA "Logs\metrics") -Pattern "metrics-*.jsonl"
    foreach ($metric in @($read.items)) {
        if (-not $metric.id) { continue }
        $metricId = ConvertTo-NodeId -Type "metric" -Name $metric.id
        Add-GraphNode -Nodes $Nodes -Type "metric" -Id $metricId -Label "$($metric.metric_type) $($metric.value) $($metric.unit)" -Properties @{
            metric_type = [string]$metric.metric_type
            value = $metric.value
            unit = [string]$metric.unit
            project = [string]$metric.project
            task_id = [string]$metric.task_id
            timestamp = [string]$metric.timestamp
        }
        $tid = [string]$metric.task_id
        if ($tid -and $taskLookup.ContainsKey($tid)) {
            foreach ($targetNodeId in $taskLookup[$tid]) {
                Add-GraphEdge -Edges $Edges -From $metricId -To $targetNodeId -Type "metric_task"
            }
        }
    }
    return $read.errors
}

function Add-DecisionsToGraph {
    param([hashtable]$Nodes, [hashtable]$Edges)

    $roots = @((Join-Path $DEV_CORE_DATA "Vault"), (Join-Path $DEV_CORE "docs")) | Where-Object { Test-Path -LiteralPath $_ }
    foreach ($root in $roots) {
        foreach ($file in Get-ChildItem -LiteralPath $root -Filter "*.md" -Recurse -File -ErrorAction SilentlyContinue | Select-Object -First 200) {
            try { $content = Get-Content -LiteralPath $file.FullName -Raw -Encoding UTF8 } catch { continue }
            if ($file.FullName -notmatch "(?i)decision" -and $content -notmatch "(?im)^##\s+Decisions?\b|^\s*-\s*Decision:") { continue }
            $relative = (Get-RelativePathCompat -BasePath $root -FullPath $file.FullName) -replace "\\", "/"
            $decisionId = ConvertTo-NodeId -Type "decision" -Name $relative
            Add-GraphNode -Nodes $Nodes -Type "decision" -Id $decisionId -Label $relative -Properties @{
                path = $file.FullName
                root = $root
            }

            foreach ($service in @("Scripts","Dashboard","MCP","Config","Skills","Docs")) {
                if ($content -match [regex]::Escape($service) -or $relative -match [regex]::Escape($service)) {
                    $serviceId = ConvertTo-NodeId -Type "service" -Name $service
                    Add-GraphNode -Nodes $Nodes -Type "service" -Id $serviceId -Label $service
                    Add-GraphEdge -Edges $Edges -From $decisionId -To $serviceId -Type "decision_service"
                }
            }
        }
    }
}

function Add-CRGToGraph {
    param([hashtable]$Nodes, [hashtable]$Edges)

    $crgScript = Join-Path $DEV_CORE "Tools\devcore\crg_sync.py"
    $crgJson = Join-Path $KNOWLEDGE_DIR "crg_graph.json"

            Write-Host "Running CRG sync script..."
            & python $crgScript
            Write-Host "CRG sync script finished with exit code: $LASTEXITCODE"

    if (-not (Test-Path -LiteralPath $crgJson)) {
        Write-Warning "CRG graph file not found at $crgJson. Skipping CRG integration."
        return
    }

    try {
        $crgData = Get-Content -LiteralPath $crgJson -Raw -Encoding UTF8 | ConvertFrom-Json
        
        if ($crgData.nodes) {
            foreach ($n in $crgData.nodes) {
                $props = @{}
                if ($n.properties) {
                    foreach ($p in $n.properties.psobject.properties) {
                        $props[$p.Name] = $p.Value
                    }
                }
                Add-GraphNode -Nodes $Nodes -Type $n.type -Id $n.id -Label $n.label -Properties $props
            }
        }
        
        if ($crgData.edges) {
            foreach ($e in $crgData.edges) {
                $props = @{}
                if ($e.properties) {
                    foreach ($p in $e.properties.psobject.properties) {
                        $props[$p.Name] = $p.Value
                    }
                }
                Add-GraphEdge -Edges $Edges -From $e.from -To $e.to -Type $e.type -Properties $props
            }
        }
    } catch {
        Write-Warning "Failed to parse CRG graph JSON: $_"
    }
}

function New-KnowledgeGraph {
    Ensure-KnowledgeDir
    $nodes = @{}
    $edges = @{}
    Add-TasksToGraph -Nodes $nodes -Edges $edges
    Add-CommitsToGraph -Nodes $nodes -Edges $edges
    $eventErrors = Add-EventsToGraph -Nodes $nodes -Edges $edges
    $metricErrors = Add-MetricsToGraph -Nodes $nodes -Edges $edges
    Add-DecisionsToGraph -Nodes $nodes -Edges $edges
    Add-CRGToGraph -Nodes $nodes -Edges $edges

    $nodeList = @($nodes.Values | Sort-Object type,label)
    $edgeList = @($edges.Values | Sort-Object type,from,to)
    $graph = [ordered]@{
        schema_version = 1
        generated_at = (Get-Date).ToString("o")
        repo_root = $REPO_ROOT
        graph_path = $GRAPH_FILE
        nodes_count = $nodeList.Count
        edges_count = $edgeList.Count
        errors_count = ($eventErrors + $metricErrors)
        nodes = $nodeList
        edges = $edgeList
    }
    $graph | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $GRAPH_FILE -Encoding UTF8
    return [pscustomobject]$graph
}

function Read-KnowledgeGraph {
    if (-not (Test-Path -LiteralPath $GRAPH_FILE)) {
        return New-KnowledgeGraph
    }
    return Get-Content -LiteralPath $GRAPH_FILE -Raw -Encoding UTF8 | ConvertFrom-Json
}

function New-ImpactAnalysis {
    if ([string]::IsNullOrWhiteSpace($Target)) {
        Write-Error "Target is required for ImpactAnalysis."
        exit 64
    }

    $graph = Read-KnowledgeGraph
    $normalized = ($Target -replace "\\", "/").Trim("/")
    $targetNode = @($graph.nodes | Where-Object {
        $_.id -eq $Target -or $_.label -eq $Target -or
        ($_.properties.path -and (($_.properties.path -replace "\\", "/") -eq $normalized)) -or
        ($_.type -eq "file" -and $_.label -eq $normalized) -or
        ($_.type -eq "service" -and $_.label -eq $Target)
    } | Select-Object -First 1)

    if (-not $targetNode) {
        $fileId = ConvertTo-NodeId -Type "file" -Name $normalized
        $targetNode = @($graph.nodes | Where-Object { $_.id -eq $fileId } | Select-Object -First 1)
    }

    if (-not $targetNode) {
        return [pscustomobject][ordered]@{
            schema_version = 1
            target = $Target
            found = $false
            related_tasks = @()
            commits = @()
            files = @()
            services = @()
            events = @()
            metrics = @()
            blast_radius = 0
        }
    }

    $adjacency = @{}
    foreach ($edge in @($graph.edges)) {
        $from = [string]$edge.from
        $to = [string]$edge.to
        if (-not $adjacency.ContainsKey($from)) { $adjacency[$from] = @() }
        if (-not $adjacency.ContainsKey($to)) { $adjacency[$to] = @() }
        $adjacency[$from] += $to
        $adjacency[$to] += $from
    }

    $visited = @{}
    $frontier = @([string]$targetNode.id)
    for ($depth = 0; $depth -lt 3; $depth++) {
        $next = @()
        foreach ($nodeId in $frontier) {
            if ($visited.ContainsKey($nodeId)) { continue }
            $visited[$nodeId] = $true
            if ($adjacency.ContainsKey($nodeId)) {
                $next += $adjacency[$nodeId]
            }
        }
        $frontier = @($next | Select-Object -Unique)
    }

    $relatedNodes = @($graph.nodes | Where-Object { $visited.ContainsKey([string]$_.id) })
    [pscustomobject][ordered]@{
        schema_version = 1
        target = $Target
        found = $true
        target_node = $targetNode
        related_tasks = @($relatedNodes | Where-Object { $_.type -eq "task" } | ForEach-Object { $_.properties.task_id } | Select-Object -Unique)
        commits = @($relatedNodes | Where-Object { $_.type -eq "commit" } | ForEach-Object { $_.properties.short } | Select-Object -Unique)
        files = @($relatedNodes | Where-Object { $_.type -eq "file" } | ForEach-Object { $_.properties.path } | Select-Object -Unique)
        services = @($relatedNodes | Where-Object { $_.type -eq "service" } | ForEach-Object { $_.label } | Select-Object -Unique)
        events = @($relatedNodes | Where-Object { $_.type -eq "event" } | ForEach-Object { $_.properties.event_type } | Select-Object -Unique)
        metrics = @($relatedNodes | Where-Object { $_.type -eq "metric" } | ForEach-Object { $_.properties.metric_type } | Select-Object -Unique)
        blast_radius = @($relatedNodes).Count
    }
}

function New-Status {
    if (-not (Test-Path -LiteralPath $GRAPH_FILE)) {
        return [pscustomobject][ordered]@{
            schema_version = 1
            exists = $false
            graph_path = $GRAPH_FILE
            nodes_count = 0
            edges_count = 0
        }
    }
    $graph = Get-Content -LiteralPath $GRAPH_FILE -Raw -Encoding UTF8 | ConvertFrom-Json
    return [pscustomobject][ordered]@{
        schema_version = 1
        exists = $true
        graph_path = $GRAPH_FILE
        generated_at = $graph.generated_at
        nodes_count = [int]$graph.nodes_count
        edges_count = [int]$graph.edges_count
        errors_count = [int]$graph.errors_count
    }
}

function New-Health {
    Ensure-KnowledgeDir
    $canWrite = $false
    try {
        $probe = Join-Path $KNOWLEDGE_DIR ".health"
        "ok" | Set-Content -LiteralPath $probe -Encoding UTF8
        Remove-Item -LiteralPath $probe -Force -ErrorAction SilentlyContinue
        $canWrite = $true
    } catch {
        $canWrite = $false
    }
    return [pscustomobject][ordered]@{
        schema_version = 1
        ok = $canWrite
        writable = $canWrite
        knowledge_dir = $KNOWLEDGE_DIR
        graph_path = $GRAPH_FILE
    }
}

switch ($Action) {
    "Build" {
        $result = New-KnowledgeGraph
        if ($Json) { $result | ConvertTo-Json -Depth 30 }
        else { Write-Host "[KNOWLEDGE] build OK -- $($result.nodes_count) node(s), $($result.edges_count) edge(s)" }
        exit 0
    }
    "ImpactAnalysis" {
        $result = New-ImpactAnalysis
        if ($Json) { $result | ConvertTo-Json -Depth 30 }
        else { Write-Host "[KNOWLEDGE] impact OK -- blast_radius=$($result.blast_radius)" }
        exit 0
    }
    "Status" {
        $result = New-Status
        if ($Json) { $result | ConvertTo-Json -Depth 10 }
        else { Write-Host "[KNOWLEDGE] status OK -- nodes=$($result.nodes_count), edges=$($result.edges_count)" }
        exit 0
    }
    "Health" {
        $result = New-Health
        if ($Json) { $result | ConvertTo-Json -Depth 10 }
        else { Write-Host "[KNOWLEDGE] health OK -- writable=$($result.writable)" }
        if ($result.ok) { exit 0 } else { exit 1 }
    }
}
