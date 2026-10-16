param(
    [string]$LanAddress = '172.16.210.32',
    [string]$RemoteSubnet = '172.16.210.0/24',
    [int]$Port = 20129,
    [switch]$Apply
)

$ErrorActionPreference = 'Stop'
if ($PSVersionTable.PSVersion.Major -lt 7) { throw 'Run this script with PowerShell 7 (pwsh).' }
$ruleName = 'DevCore Individual TLS pilot'
$address = [System.Net.IPAddress]::Parse($LanAddress)
if ($address.AddressFamily -ne [System.Net.Sockets.AddressFamily]::InterNetwork -or
    $LanAddress -eq '0.0.0.0' -or $Port -ne 20129) {
    throw 'An exact IPv4 LAN address and DevCore port 20129 are required.'
}
$network = [System.Net.IPNetwork]::Parse($RemoteSubnet)
if ($network.BaseAddress.AddressFamily -ne [System.Net.Sockets.AddressFamily]::InterNetwork -or
    -not $network.Contains($address)) {
    throw 'The allowed client subnet must contain the selected LAN address.'
}
$interfaceAddress = Get-NetIPAddress -AddressFamily IPv4 -IPAddress $LanAddress -ErrorAction Stop |
    Select-Object -First 1
$profile = Get-NetConnectionProfile -InterfaceIndex $interfaceAddress.InterfaceIndex -ErrorAction Stop
if ($profile.NetworkCategory -ne 'Private') {
    throw 'The selected LAN interface must have the Private network profile.'
}
$existing = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
if ($existing) { throw 'A DevCore pilot firewall rule already exists; inspect it before changing it.' }
$private = Get-NetFirewallProfile -Name Private -ErrorAction Stop
$report = [ordered]@{
    address = $LanAddress
    remote_subnet = $RemoteSubnet
    port = $Port
    interface = $profile.InterfaceAlias
    private_firewall_enabled_before = [bool]$private.Enabled
    action = if ($Apply) { 'apply' } else { 'preflight_only' }
}
if (-not $Apply) {
    [pscustomobject]$report | ConvertTo-Json
    return
}
$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Run the firewall change in elevated PowerShell.'
}
$created = $false
try {
    New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Action Allow -Enabled True `
        -Profile Private -Protocol TCP -LocalAddress $LanAddress -LocalPort $Port `
        -RemoteAddress $RemoteSubnet -Description 'DevCore TLS pilot, private LAN only' | Out-Null
    $created = $true
    Set-NetFirewallProfile -Name Private -Enabled True
    $rule = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction Stop
    $filter = $rule | Get-NetFirewallPortFilter
    $addresses = $rule | Get-NetFirewallAddressFilter
    $observed = [ordered]@{
        private_enabled = [string](Get-NetFirewallProfile -Name Private).Enabled
        rule_enabled = [string]$rule.Enabled
        action = [string]$rule.Action
        profile = [string]$rule.Profile
        protocol = [string]$filter.Protocol
        local_port = [string]$filter.LocalPort
        local_address = [string]$addresses.LocalAddress
        remote_address = [string]$addresses.RemoteAddress
    }
    # NetSecurity reports CIDR ranges with a dotted-decimal mask on this host.
    $maskOctets = for ($i = 0; $i -lt 4; $i++) {
        $bits = [Math]::Min(8, [Math]::Max(0, [int]$network.PrefixLength - 8 * $i))
        [int](256 - [Math]::Pow(2, 8 - $bits))
    }
    $acceptedRemoteAddresses = @(
        [string]$network,
        "$($network.BaseAddress)/$($maskOctets -join '.')"
    )
    if ($observed.private_enabled -ne 'True' -or
        $observed.rule_enabled -ne 'True' -or $observed.action -ne 'Allow' -or
        $observed.profile -ne 'Private' -or
        $observed.local_port -ne [string]$Port -or $observed.protocol -notin @('TCP', '6') -or
        $observed.local_address -ne $LanAddress -or
        $observed.remote_address -notin $acceptedRemoteAddresses) {
        throw "Firewall verification failed: $($observed | ConvertTo-Json -Compress)"
    }
    $report.action = 'private_firewall_and_scoped_rule_verified'
    [pscustomobject]$report | ConvertTo-Json
}
catch {
    $failure = $_.Exception.Message
    $rollback = @()
    if ($created) {
        try {
            Remove-NetFirewallRule -DisplayName $ruleName -ErrorAction Stop
            $rollback += 'rule_removed'
        }
        catch { $rollback += "rule_removal_failed: $($_.Exception.Message)" }
    }
    try {
        Set-NetFirewallProfile -Name Private -Enabled $private.Enabled -ErrorAction Stop
        $rollback += 'private_profile_restored'
    }
    catch { $rollback += "private_profile_restore_failed: $($_.Exception.Message)" }
    throw "DevCore firewall change failed: $failure; rollback: $($rollback -join ', ')"
}
