# test_embedding_contract.ps1 -- embedding contract unit tests
$ErrorActionPreference = "Stop"

. "$PSScriptRoot\embedding_contract.ps1"

function Assert-True {
    param(
        [bool]$Condition,
        [string]$Message
    )
    if (-not $Condition) { throw $Message }
}

$contract = Get-DevCoreEmbeddingContract
Assert-True ($contract.dimensions -eq 768) "embedding dimensions should be 768"
Assert-True ($contract.model -eq "gemini-embedding-001") "sync embedding model should be gemini-embedding-001"
Assert-True ($contract.query_model -eq "gemini-embedding-001") "query embedding model should be gemini-embedding-001"
Assert-True ($contract.qdrant_collections -contains "decisions") "contract should include decisions collection"

$syncBody = New-DevCoreEmbeddingRequestBody -Text "sync text"
Assert-True ($syncBody.model -eq $contract.model) "sync body should use configured model"
Assert-True ($syncBody.dimensions -eq 768) "sync body should request 768 dimensions"

$queryBody = New-DevCoreEmbeddingRequestBody -Text "query text" -Query
Assert-True ($queryBody.model -eq $contract.query_model) "query body should use configured query model"
Assert-True ($queryBody.dimensions -eq 768) "query body should request 768 dimensions"

Assert-DevCoreEmbeddingVector -Vector @(1..768) -Context "unit"

try {
    Assert-DevCoreEmbeddingVector -Vector @(1..3072) -Context "unit"
    throw "3072-dimensional vector should fail"
} catch {
    Assert-True ($_.Exception.Message -match "expected 768, got 3072") "dimension mismatch should report expected and actual size"
}

Write-Host "[OK] embedding contract unit tests passed" -ForegroundColor Green
