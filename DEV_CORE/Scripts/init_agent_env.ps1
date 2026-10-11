# Show or launch an application with its own routing environment. Never User/Machine.
param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("openai", "claude", "auxiliary")][string]$Application,
    [string]$Command,
    [string[]]$Arguments = @()
)
$ErrorActionPreference = "Stop"
$routing = switch ($Application) {
    'openai' { @{ OPENAI_BASE_URL = 'http://127.0.0.1:8787/v1'; OPENAI_API_BASE = 'http://127.0.0.1:8787/v1' } }
    'claude' { @{ ANTHROPIC_BASE_URL = 'http://127.0.0.1:8787' } }
    'auxiliary' { @{ OPENAI_BASE_URL = 'http://127.0.0.1:8789/v1'; OPENAI_API_BASE = 'http://127.0.0.1:8789/v1' } }
}
if (-not $Command) {
    $routing | ConvertTo-Json
    return
}
$info = [System.Diagnostics.ProcessStartInfo]::new()
$info.FileName = $Command
$info.UseShellExecute = $false
foreach ($argument in $Arguments) { $info.ArgumentList.Add($argument) }
foreach ($key in @('OPENAI_BASE_URL', 'OPENAI_API_BASE', 'ANTHROPIC_BASE_URL', 'DEVCORE_HEADROOM_ENFORCED')) {
    $info.Environment.Remove($key) | Out-Null
}
foreach ($key in $routing.Keys) { $info.Environment[$key] = $routing[$key] }
$child = [System.Diagnostics.Process]::Start($info)
$child.WaitForExit()
exit $child.ExitCode
