param(
    [switch]$Apply,
    [switch]$Undo
)

$ErrorActionPreference = 'Stop'
if ($PSVersionTable.PSVersion.Major -lt 7) { throw 'Run this script with PowerShell 7 (pwsh).' }
if ($Apply -and $Undo) { throw 'Choose either -Apply or -Undo.' }
$principal = [Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Run this script with elevated PowerShell 7 (pwsh).'
}

$serverAddress = '172.16.210.32'
$clientAddress = '10.40.100.2'
$port = 20129
$baseRuleName = 'DevCore Individual TLS pilot'
$clientRuleName = 'DevCore Individual TLS pilot second host'
$clientForms = @($clientAddress, "$clientAddress/32", "$clientAddress/255.255.255.255")

$service = Get-CimInstance Win32_Service -Filter "Name='DevCoreIndividual'" -ErrorAction Stop
$binary = $service.PathName.Trim().Trim('"')
if ($service.State -ne 'Running' -or
    $binary -notlike '*\devcore-py31316-20261015-postgres-v253-lan\pythonservice.exe' -or
    -not (Get-NetTCPConnection -State Listen -LocalAddress $serverAddress -LocalPort $port -ErrorAction SilentlyContinue)) {
    throw 'The v253 LAN service must be running and listening on the exact pilot address.'
}

$baseRule = @(Get-NetFirewallRule -PolicyStore PersistentStore -DisplayName $baseRuleName -ErrorAction Stop)
$basePort = if ($baseRule.Count -eq 1) { $baseRule[0] | Get-NetFirewallPortFilter -ErrorAction Stop }
$baseAddress = if ($baseRule.Count -eq 1) { $baseRule[0] | Get-NetFirewallAddressFilter -ErrorAction Stop }
if ($baseRule.Count -ne 1 -or [string]$baseRule[0].Enabled -ne 'True' -or
    [string]$baseRule[0].Direction -ne 'Inbound' -or [string]$baseRule[0].Action -ne 'Allow' -or
    [string]$baseRule[0].Profile -ne 'Private' -or
    [string]$basePort.Protocol -notin @('TCP', '6') -or [string]$basePort.LocalPort -ne [string]$port -or
    [string]$baseAddress.LocalAddress -ne $serverAddress -or
    [string]$baseAddress.RemoteAddress -notin @('172.16.210.0/24', '172.16.210.0/255.255.255.0')) {
    throw 'The existing scoped v253 pilot rule is missing or has changed.'
}

function Assert-ClientRule($rule) {
    $portFilter = $rule | Get-NetFirewallPortFilter -ErrorAction Stop
    $addressFilter = $rule | Get-NetFirewallAddressFilter -ErrorAction Stop
    $remote = @($addressFilter.RemoteAddress | ForEach-Object { [string]$_ })
    if ([string]$rule.Enabled -ne 'True' -or [string]$rule.Direction -ne 'Inbound' -or
        [string]$rule.Action -ne 'Allow' -or [string]$rule.Profile -ne 'Private' -or
        [string]$portFilter.Protocol -notin @('TCP', '6') -or
        [string]$portFilter.LocalPort -ne [string]$port -or
        [string]$addressFilter.LocalAddress -ne $serverAddress -or
        $remote.Count -ne 1 -or $remote[0] -notin $clientForms) {
        throw "The second-host rule is not limited to $clientAddress on $($serverAddress):$($port)."
    }
    return $remote[0]
}

$existing = @(Get-NetFirewallRule -PolicyStore PersistentStore -DisplayName $clientRuleName -ErrorAction SilentlyContinue)
if ($existing.Count -gt 1) { throw 'More than one second-host rule exists.' }
if ($Undo) {
    if ($existing.Count -eq 0) {
        [pscustomobject]@{ status='already_absent'; rule=$clientRuleName } | ConvertTo-Json
        return
    }
    $remote = Assert-ClientRule $existing[0]
    Remove-NetFirewallRule -InputObject $existing[0] -ErrorAction Stop
    [pscustomobject]@{ status='second_host_rule_removed'; rule=$clientRuleName; remote_address=$remote } | ConvertTo-Json
    return
}
if ($existing.Count -eq 1) {
    $remote = Assert-ClientRule $existing[0]
    [pscustomobject]@{ status='second_host_rule_verified'; rule=$clientRuleName; remote_address=$remote } | ConvertTo-Json
    return
}
if (-not $Apply) {
    [pscustomobject]@{ status='preflight_only'; rule=$clientRuleName; local_address=$serverAddress;
        local_port=$port; remote_address="$clientAddress/32"; profile='Private' } | ConvertTo-Json
    return
}

$created = $false
try {
    New-NetFirewallRule -DisplayName $clientRuleName -Direction Inbound -Action Allow -Enabled True `
        -Profile Private -Protocol TCP -LocalAddress $serverAddress -LocalPort $port `
        -RemoteAddress "$clientAddress/32" -Description 'DevCore TLS pilot, exact second host only' | Out-Null
    $created = $true
    $rule = @(Get-NetFirewallRule -PolicyStore PersistentStore -DisplayName $clientRuleName -ErrorAction Stop)
    if ($rule.Count -ne 1) { throw 'Second-host firewall rule was not found after creation.' }
    $remote = Assert-ClientRule $rule[0]
    [pscustomobject]@{ status='second_host_rule_verified'; rule=$clientRuleName;
        local_address=$serverAddress; local_port=$port; remote_address=$remote } | ConvertTo-Json
}
catch {
    $failure = $_.Exception.Message
    $rollback = 'not_required'
    if ($created) {
        try {
            Remove-NetFirewallRule -DisplayName $clientRuleName -ErrorAction Stop
            $rollback = 'second_host_rule_removed'
        }
        catch { $rollback = "second_host_rule_removal_failed: $($_.Exception.Message)" }
    }
    throw "Second-host firewall rule failed: $failure; rollback: $rollback"
}
