# test_qdrant_vector_contract.ps1 -- live Qdrant/vector contract test
$ErrorActionPreference = "Stop"

. "$PSScriptRoot\embedding_contract.ps1"

$contract = Get-DevCoreEmbeddingContract
$qdrantUrl = if ($env:QDRANT_URL) { $env:QDRANT_URL } else { "http://localhost:6333" }

function Assert-True {
    param(
        [bool]$Condition,
        [string]$Message
    )
    if (-not $Condition) { throw $Message }
}

function Invoke-QdrantJson {
    param(
        [Parameter(Mandatory=$true)][string]$Method,
        [Parameter(Mandatory=$true)][string]$Path,
        [object]$Body = $null
    )

    $uri = "$qdrantUrl$Path"
    if ($null -eq $Body) {
        return Invoke-RestMethod -Uri $uri -Method $Method -TimeoutSec 15
    }

    $json = $Body | ConvertTo-Json -Depth 20
    return Invoke-RestMethod -Uri $uri -Method $Method -Body ([Text.Encoding]::UTF8.GetBytes($json)) -ContentType "application/json; charset=utf-8" -TimeoutSec 15
}

$health = Invoke-QdrantJson -Method Get -Path "/collections"
Assert-True ($health.status -eq "ok") "Qdrant should list collections"

foreach ($collection in $contract.qdrant_collections) {
    $info = Invoke-QdrantJson -Method Get -Path "/collections/$collection"
    Assert-True ([int]$info.result.config.params.vectors.size -eq $contract.dimensions) "$collection should use $($contract.dimensions)d vectors"
}

$body = New-DevCoreEmbeddingRequestBody -Text "DEV_CORE Qdrant vector contract smoke test"
$headers = @{}
if ($env:NINEROUTER_API_KEY) { $headers["Authorization"] = "Bearer $env:NINEROUTER_API_KEY" }
$embeddingResponse = Invoke-RestMethod -Uri $contract.endpoint -Method Post -Body ([Text.Encoding]::UTF8.GetBytes(($body | ConvertTo-Json -Depth 8))) -ContentType "application/json; charset=utf-8" -Headers $headers -TimeoutSec 30
$vector = $embeddingResponse.data[0].embedding
Assert-DevCoreEmbeddingVector -Vector $vector -Context "live embedding"

$tempCollection = "devcore_contract_$([guid]::NewGuid().ToString('N').Substring(0, 12))"
try {
    Invoke-QdrantJson -Method Put -Path "/collections/$tempCollection" -Body @{
        vectors = @{
            size = $contract.dimensions
            distance = "Cosine"
        }
    } | Out-Null

    Invoke-QdrantJson -Method Put -Path "/collections/$tempCollection/points" -Body @{
        points = @(
            @{
                id = "00000000-0000-0000-0000-000000000001"
                vector = $vector
                payload = @{
                    title = "contract"
                    type = "test"
                }
            }
        )
    } | Out-Null

    $search = Invoke-QdrantJson -Method Post -Path "/collections/$tempCollection/points/search" -Body @{
        vector = $vector
        limit = 1
        with_payload = $true
    }
    Assert-True ($search.result.Count -ge 1) "Qdrant should return the upserted point"
    Assert-True ($search.result[0].payload.title -eq "contract") "Qdrant payload should round-trip"
} finally {
    try { Invoke-QdrantJson -Method Delete -Path "/collections/$tempCollection" | Out-Null } catch {}
}

Write-Host "[OK] Qdrant vector contract passed" -ForegroundColor Green
