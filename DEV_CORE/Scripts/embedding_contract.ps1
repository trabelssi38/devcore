# embedding_contract.ps1 -- canonical embedding contract for DEV_CORE Qdrant

function Get-DevCoreEmbeddingContract {
    $platformRoot = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { Split-Path -Parent $PSScriptRoot }
    $configPath = Join-Path $platformRoot "Config\embedding.json"
    if (-not (Test-Path -LiteralPath $configPath)) {
        throw "Embedding config not found: $configPath"
    }

    $config = Get-Content -LiteralPath $configPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if (-not $config.dimensions -or [int]$config.dimensions -le 0) {
        throw "Embedding config missing positive dimensions"
    }
    if ([string]::IsNullOrWhiteSpace([string]$config.model)) {
        throw "Embedding config missing model"
    }
    if ([string]::IsNullOrWhiteSpace([string]$config.query_model)) {
        throw "Embedding config missing query_model"
    }
    if ([string]::IsNullOrWhiteSpace([string]$config.endpoint)) {
        throw "Embedding config missing endpoint"
    }

    [PSCustomObject]@{
        schema_version = [int]$config.schema_version
        provider = [string]$config.provider
        endpoint = [string]$config.endpoint
        model = [string]$config.model
        query_model = [string]$config.query_model
        dimensions = [int]$config.dimensions
        qdrant_collections = @($config.qdrant_collections)
    }
}

function New-DevCoreEmbeddingRequestBody {
    param(
        [Parameter(Mandatory=$true)][string]$Text,
        [switch]$Query
    )

    $contract = Get-DevCoreEmbeddingContract
    $model = if ($Query) { $contract.query_model } else { $contract.model }
    [PSCustomObject]@{
        model = $model
        input = $Text
        dimensions = $contract.dimensions
    }
}

function Assert-DevCoreEmbeddingVector {
    param(
        [Parameter(Mandatory=$true)][object]$Vector,
        [string]$Context = "embedding"
    )

    $contract = Get-DevCoreEmbeddingContract
    $count = @($Vector).Count
    if ($count -ne $contract.dimensions) {
        throw "$Context vector dimension mismatch: expected $($contract.dimensions), got $count"
    }
}
