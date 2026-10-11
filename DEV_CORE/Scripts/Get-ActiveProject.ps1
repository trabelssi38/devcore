# Resolve the project for this invocation without shared mutable state.
# A local manifest is authoritative. A new ordinary Git repository may use its
# directory name until session_start.ps1 creates .devcore/project.json.
param([string]$Project)

$ErrorActionPreference = "Stop"

function Test-ProjectId {
    param([string]$Value)
    return (-not [string]::IsNullOrWhiteSpace($Value) -and
            $Value -notmatch '[\\/:]' -and $Value -notmatch '\.\.')
}

if ($PSBoundParameters.ContainsKey("Project")) {
    $candidate = $Project.Trim()
    if (-not (Test-ProjectId $candidate)) { Write-Error "Identifiant de projet invalide."; exit 1 }
    Write-Output $candidate
    exit 0
}

$cursor = Get-Item -LiteralPath (Get-Location).Path
while ($cursor) {
    $manifest = Join-Path $cursor.FullName ".devcore\project.json"
    if (Test-Path -LiteralPath $manifest -PathType Leaf) {
        try {
            $metadata = Get-Content -Raw -LiteralPath $manifest -Encoding UTF8 | ConvertFrom-Json
            $candidate = [string]$metadata.name
            if (-not (Test-ProjectId $candidate)) { throw "Identifiant de projet invalide." }
            Write-Output $candidate
            exit 0
        } catch {
            Write-Error "Manifeste de projet invalide : $manifest"
            exit 1
        }
    }
    $gitMarker = Join-Path $cursor.FullName ".git"
    if (Test-Path -LiteralPath $gitMarker -PathType Container) {
        $candidate = $cursor.Name
        if (-not (Test-ProjectId $candidate)) { Write-Error "Nom de depot invalide."; exit 1 }
        Write-Output $candidate
        exit 0
    }
    if (Test-Path -LiteralPath $gitMarker -PathType Leaf) {
        Write-Error "Worktree sans manifeste .devcore/project.json."
        exit 1
    }
    $cursor = $cursor.Parent
}

Write-Error "Projet introuvable : fournir -Project ou .devcore/project.json."
exit 1
