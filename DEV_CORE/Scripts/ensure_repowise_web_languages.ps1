# ensure_repowise_web_languages.ps1 -- add web/source passthrough languages to local Repowise
param(
    [string]$Python = "python",
    [switch]$Quiet
)

$ErrorActionPreference = "Stop"

function Get-RepowisePackageRoot {
    $code = @"
import os, repowise
for path in getattr(repowise, '__path__', []):
    models = os.path.join(path, 'core', 'ingestion', 'models.py')
    if os.path.exists(models):
        print(path)
        break
"@
    $root = & $Python -c $code
    if ($LASTEXITCODE -ne 0 -or -not $root) {
        if (-not $Quiet) { Write-Host "[DEV_CORE] Repowise Python package not installed; skipping patch." }
        exit 0
    }
    return [string]$root.Trim()
}

function Write-Utf8NoBom {
    param(
        [Parameter(Mandatory=$true)][string]$Path,
        [Parameter(Mandatory=$true)][string]$Content
    )
    $enc = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $Content, $enc)
}

function Ensure-LineAfter {
    param(
        [Parameter(Mandatory=$true)][string]$Text,
        [Parameter(Mandatory=$true)][string]$Anchor,
        [Parameter(Mandatory=$true)][string[]]$Lines
    )
    foreach ($line in $Lines) {
        if ($Text -notmatch [regex]::Escape($line)) {
            $Text = $Text -replace [regex]::Escape($Anchor), ($Anchor + "`n" + $line)
            $Anchor = $line
        }
    }
    return $Text
}

function Ensure-TupleEntriesAfter {
    param(
        [Parameter(Mandatory=$true)][string]$Text,
        [Parameter(Mandatory=$true)][string]$Anchor,
        [Parameter(Mandatory=$true)][string[]]$Entries
    )
    foreach ($entry in $Entries) {
        if ($Text -notmatch [regex]::Escape($entry)) {
            $Text = $Text -replace [regex]::Escape($Anchor), ($Anchor + "`n    " + $entry)
            $Anchor = "    " + $entry
        }
    }
    return $Text
}

$pkgRoot = Get-RepowisePackageRoot
$specDir = Join-Path $pkgRoot "core\ingestion\languages\specs"
$modelsPath = Join-Path $pkgRoot "core\ingestion\models.py"
$specInitPath = Join-Path $specDir "__init__.py"

if (-not (Test-Path $specDir) -or -not (Test-Path $modelsPath) -or -not (Test-Path $specInitPath)) {
    if (-not $Quiet) { Write-Host "[DEV_CORE] Repowise package layout non-standard; skipping web language patch." }
    exit 0
}

$specs = @{
    "html.py" = @'
"""LanguageSpec for HTML markup source files."""

from ..spec import LanguageSpec

SPEC = LanguageSpec(
    tag="html",
    display_name="HTML / Web Markup",
    extensions=frozenset({".html", ".htm", ".vue", ".svelte", ".astro"}),
    is_code=True,
    is_passthrough=True,
    entry_stems=("index", "app", "main"),
    color_hex="#E34C26",
)
'@
    "css.py" = @'
"""LanguageSpec for CSS and stylesheet source files."""

from ..spec import LanguageSpec

SPEC = LanguageSpec(
    tag="css",
    display_name="CSS / Stylesheets",
    extensions=frozenset({".css", ".scss", ".sass", ".less", ".pcss", ".postcss"}),
    is_code=True,
    is_passthrough=True,
    color_hex="#563D7C",
)
'@
    "powershell.py" = @'
"""LanguageSpec for PowerShell source files."""

from ..spec import LanguageSpec

SPEC = LanguageSpec(
    tag="powershell",
    display_name="PowerShell",
    extensions=frozenset({".ps1", ".psm1", ".psd1"}),
    is_code=True,
    is_infra=True,
    is_passthrough=True,
    shebang_tokens=("pwsh", "powershell"),
    color_hex="#012456",
)
'@
}

try {
    foreach ($name in $specs.Keys) {
        Write-Utf8NoBom -Path (Join-Path $specDir $name) -Content $specs[$name]
    }

    $specInit = Get-Content $specInitPath -Raw -Encoding UTF8
    $specInit = Ensure-LineAfter -Text $specInit -Anchor "from .graphql import SPEC as _GRAPHQL" -Lines @(
        "from .html import SPEC as _HTML",
        "from .css import SPEC as _CSS"
    )
    $specInit = Ensure-LineAfter -Text $specInit -Anchor "from .openapi import SPEC as _OPENAPI" -Lines @(
        "from .powershell import SPEC as _POWERSHELL"
    )
    $specInit = Ensure-TupleEntriesAfter -Text $specInit -Anchor "    _OPENAPI," -Entries @(
        "_HTML,",
        "_CSS,",
        "_POWERSHELL,"
    )
    Write-Utf8NoBom -Path $specInitPath -Content $specInit

    $models = Get-Content $modelsPath -Raw -Encoding UTF8
    $models = Ensure-TupleEntriesAfter -Text $models -Anchor '    "r",' -Entries @(
        '"html",',
        '"css",',
        '"powershell",'
    )
    Write-Utf8NoBom -Path $modelsPath -Content $models

    $verify = @"
from repowise.core.ingestion.languages.registry import REGISTRY
from repowise.core.ingestion.models import EXTENSION_TO_LANGUAGE
required = {
    '.html': 'html',
    '.vue': 'html',
    '.svelte': 'html',
    '.astro': 'html',
    '.css': 'css',
    '.scss': 'css',
    '.less': 'css',
    '.ps1': 'powershell',
}
for ext, tag in required.items():
    assert REGISTRY.all_extensions().get(ext) == tag, (ext, REGISTRY.all_extensions().get(ext))
    assert EXTENSION_TO_LANGUAGE.get(ext) == tag, (ext, EXTENSION_TO_LANGUAGE.get(ext))
print('Repowise web languages OK')
"@
    if ($Quiet) {
        & $Python -c $verify 2>$null | Out-Null
    } else {
        & $Python -c $verify
    }
} catch {
    if (-not $Quiet) { Write-Host "[DEV_CORE] Non-admin access or existing Repowise configuration; skipping web language patch." }
    exit 0
}
