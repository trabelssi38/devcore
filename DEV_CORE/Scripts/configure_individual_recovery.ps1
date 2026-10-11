param([switch]$CheckOnly)

$name = 'DevCoreIndividual'
$expectedHost = 'E:\DevCoreRuntime\qualification\service-profile-v249\runtime\releases\devcore-py31316-20261011-l9-autostart-clean-v249\pythonservice.exe'
$configuration = sc.exe qc $name | Out-String
if ($LASTEXITCODE -ne 0 -or $configuration -notmatch [regex]::Escape($expectedHost)) {
    Write-Error 'SCM host differs from the qualified v249 release.'
    exit 2
}
if (-not $CheckOnly) {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        Write-Error 'Run PowerShell as Administrator before changing SCM recovery.'
        exit 740
    }
    & sc.exe config $name start= delayed-auto | Out-Host
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & sc.exe failure $name reset= 86400 actions= restart/60000/restart/120000/none/0 | Out-Host
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & sc.exe failureflag $name 1 | Out-Host
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
$current = sc.exe qc $name | Out-String
$recovery = sc.exe qfailure $name | Out-String
$flag = sc.exe qfailureflag $name | Out-String
$settings = Get-ItemProperty -LiteralPath 'HKLM:\SYSTEM\CurrentControlSet\Services\DevCoreIndividual'
Write-Output $current
Write-Output $recovery
Write-Output $flag
if ($settings.Start -ne 2 -or $settings.DelayedAutoStart -ne 1 -or
    $recovery -notmatch 'RESTART|RED.MARRER' -or
    $flag -notmatch 'FAILURE_ACTIONS_ON_NONCRASH_FAILURES\s*:\s*(1|TRUE)') {
    Write-Error 'Delayed startup and recovery configuration not yet verified.'
    exit 1
}
Write-Output 'recovery_check=passed'
