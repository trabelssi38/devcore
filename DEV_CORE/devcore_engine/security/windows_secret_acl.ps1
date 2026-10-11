param(
    [Parameter(Mandatory = $true)][string]$LiteralPath,
    [Parameter(Mandatory = $true)]
    [ValidateSet('ProtectFile', 'CheckFile', 'ProtectDirectory', 'CheckDirectory', 'ValidateDirectory', 'CheckStore')][string]$Mode
)

# Bundled with the security package. ProtectFile is limited to an empty newly reserved file;
# ProtectDirectory to an empty directory. No recursive changes or repair of
# existing secrets. Arguments are literal paths, never evaluated as code.
$ErrorActionPreference = 'Stop'
try {
    Import-Module (Join-Path $PSHOME 'Modules/Microsoft.PowerShell.Security/Microsoft.PowerShell.Security.psd1') -ErrorAction Stop
    if ($LiteralPath -notmatch '^[a-zA-Z]:[\\/]') { throw 'Local absolute path required' }
    $fullPath = [System.IO.Path]::GetFullPath($LiteralPath)
    $drive = [System.IO.DriveInfo]::new([System.IO.Path]::GetPathRoot($fullPath))
    if ($drive.DriveFormat -ne 'NTFS' -or $drive.DriveType -ne 'Fixed') { throw 'Local NTFS volume required' }
    $item = Get-Item -LiteralPath $fullPath -Force
    $directory = $Mode.EndsWith('Directory')
    if ([bool]$item.PSIsContainer -ne $directory) { throw 'Unexpected target kind' }
    $cursor = $item
    while ($null -ne $cursor) {
        if (($cursor.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Reparse point forbidden' }
        if ($cursor -is [System.IO.DirectoryInfo]) { $cursor = $cursor.Parent } else { $cursor = $cursor.Directory }
    }
    if ($Mode -eq 'ValidateDirectory') {
        @{ valid = $true; kind = 'directory'; local_ntfs = $true; reparse = $false } | ConvertTo-Json -Compress
        return
    }
    $owner = [System.Security.Principal.WindowsIdentity]::GetCurrent().User
    $system = [System.Security.Principal.SecurityIdentifier]::new('S-1-5-18')
    $allowed = @($owner.Value, $system.Value) | Select-Object -Unique
    function Assert-PrivateAcl($target, [bool]$inheritedFile = $false) {
        if (($target.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Reparse point forbidden' }
        $actual = Get-Acl -LiteralPath $target.FullName
        $actualOwner = $actual.GetOwner([System.Security.Principal.SecurityIdentifier]).Value
        $inherited = $inheritedFile -and -not $actual.AreAccessRulesProtected
        # Elevated Windows processes can create inherited children owned by Administrators.
        # This does not grant that group a DACL entry; OS administrators remain trusted.
        $owners = if ($inherited) { @($owner.Value, 'S-1-5-32-544') } else { @($owner.Value) }
        if ($actualOwner -notin $owners -or (-not $inherited -and -not $actual.AreAccessRulesProtected)) {
            throw 'Owner or inheritance not protected'
        }
        $rules = @($actual.GetAccessRules($true, $true, [System.Security.Principal.SecurityIdentifier]))
        if ($rules.Count -ne $allowed.Count) { throw 'Unexpected access rules' }
        $seen = @()
        foreach ($rule in $rules) {
            if ([bool]$rule.IsInherited -ne $inherited -or $rule.AccessControlType -ne 'Allow' -or
                $rule.IdentityReference.Value -notin $allowed -or
                $rule.FileSystemRights -ne [System.Security.AccessControl.FileSystemRights]::FullControl -or
                $rule.PropagationFlags -ne [System.Security.AccessControl.PropagationFlags]::None) {
                throw 'Unqualified access rule'
            }
            $flags = if ($target -is [System.IO.DirectoryInfo]) { [System.Security.AccessControl.InheritanceFlags]'ContainerInherit,ObjectInherit' } else { [System.Security.AccessControl.InheritanceFlags]::None }
            if ($rule.InheritanceFlags -ne $flags) { throw 'Unexpected inheritance flags' }
            $seen += $rule.IdentityReference.Value
        }
        if (@($seen | Select-Object -Unique).Count -ne $allowed.Count) { throw 'Incomplete access rules' }
        return @{ owner_sid = $actualOwner; inheritance_protected = [bool]$actual.AreAccessRulesProtected }
    }
    if ($Mode -eq 'CheckStore') {
        [void](Assert-PrivateAcl $item.Directory)
        $metadata = Assert-PrivateAcl $item
        $sidecars = @()
        foreach ($suffix in @('-journal', '-wal', '-shm')) {
            $childPath = $fullPath + $suffix
            if (Test-Path -LiteralPath $childPath) {
                $child = Get-Item -LiteralPath $childPath -Force
                if ($child.PSIsContainer) { throw 'Unexpected sidecar kind' }
                $childMetadata = Assert-PrivateAcl $child $true
                $sidecars += @{ suffix = $suffix; owner_sid = $childMetadata.owner_sid; inheritance_protected = $childMetadata.inheritance_protected }
            }
        }
        @{ valid = $true; kind = 'store'; owner_sid = $metadata.owner_sid; allowed_sids = @($allowed); sidecars = @($sidecars); local_ntfs = $true } | ConvertTo-Json -Depth 4 -Compress
        return
    }
    if ($Mode.StartsWith('Protect')) {
        if ($directory) {
            if (@(Get-ChildItem -LiteralPath $fullPath -Force).Count -ne 0) { throw 'Directory must be empty' }
            $acl = [System.Security.AccessControl.DirectorySecurity]::new()
        } else {
            if ($item.Length -ne 0) { throw 'File must be empty' }
            $acl = [System.Security.AccessControl.FileSecurity]::new()
        }
        $acl.SetOwner($owner)
        $acl.SetAccessRuleProtection($true, $false)
        foreach ($sidValue in $allowed) {
            $sid = [System.Security.Principal.SecurityIdentifier]::new($sidValue)
            if ($directory) {
                $rule = [System.Security.AccessControl.FileSystemAccessRule]::new(
                    $sid, 'FullControl', 'ContainerInherit,ObjectInherit', 'None', 'Allow')
            } else {
                $rule = [System.Security.AccessControl.FileSystemAccessRule]::new($sid, 'FullControl', 'Allow')
            }
            [void]$acl.AddAccessRule($rule)
        }
        Set-Acl -LiteralPath $fullPath -AclObject $acl
    }
    [void](Assert-PrivateAcl $item)
    @{ valid = $true; owner_sid = $owner.Value; allowed_sids = @($allowed); inheritance_protected = $true; kind = $(if ($directory) { 'directory' } else { 'file' }) } | ConvertTo-Json -Compress
} catch {
    # No file contents, tokens or exception payloads in output.
    [Console]::Error.WriteLine('Windows secret protection failed')
    exit 2
}
