# Read-only route admission checks. No generated tokens, active tasks or data touched.
$ErrorActionPreference = "Stop"
foreach ($route in @(@{Name='native'; Port=8787}, @{Name='auxiliary'; Port=8789})) {
    $state = Invoke-RestMethod "http://127.0.0.1:$($route.Port)/healthz" -TimeoutSec 3
    if ($state.service -ne 'headroom-devcore' -or $state.route -ne $route.Name -or $state.status -ne 'ready' -or $state.port -ne $route.Port) {
        throw "Unqualified route on $($route.Port)"
    }
    $expected = & C:/Python314/python.exe (Join-Path $PSScriptRoot 'headroom_routes.py') --route $route.Name --check | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) { throw 'Unable to load the route contract' }
    foreach ($property in $expected.PSObject.Properties) {
        $actual = $state.profile.PSObject.Properties[$property.Name]
        if (-not $actual -or ($actual.Value | ConvertTo-Json -Compress) -cne ($property.Value | ConvertTo-Json -Compress)) {
            throw "Route profile mismatch: $($route.Name)/$($property.Name)"
        }
    }
}
foreach ($port in @(8789, 20130)) {
    foreach ($model in @('gpt-4o', 'codex-mini', 'claude-test')) {
        $body = @{model=$model; messages=@()} | ConvertTo-Json -Compress
        $response = Invoke-WebRequest "http://127.0.0.1:$port/v1/chat/completions" -Method Post -ContentType 'application/json' -Body $body -TimeoutSec 3 -SkipHttpErrorCheck
        if ($response.StatusCode -ne 400) { throw "Native model $model not refused on $port" }
    }
}
Write-Output 'Admission qualified: native/auxiliary identities distinct, native aliases refused. Authenticated provider calls and savings are not qualified by this check.'
