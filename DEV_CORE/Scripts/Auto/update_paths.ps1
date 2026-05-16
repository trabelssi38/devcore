# update_paths.ps1
$scriptsDir = "C:\devcore\DEV_CORE\Scripts"

$files = Get-ChildItem -Path $scriptsDir -Filter "*.ps1" -Recurse

$old1 = '"$DEV_CORE_DATA\Memory\tasks.json"'
$new1 = '"$DEV_CORE_DATA\Memory\$(& ''C:\devcore\DEV_CORE\Scripts\Get-ActiveProject.ps1'')\tasks.json"'

$old2 = '"$DATA\Memory\tasks.json"'
$new2 = '"$DATA\Memory\$(& ''C:\devcore\DEV_CORE\Scripts\Get-ActiveProject.ps1'')\tasks.json"'

foreach ($f in $files) {
    if ($f.Name -eq "Get-ActiveProject.ps1" -or $f.Name -eq "update_paths.ps1" -or $f.Name -eq "migrate_multiproject.ps1") { continue }
    
    $content = Get-Content $f.FullName -Raw
    $updated = $false
    
    if ($content -match [regex]::Escape($old1)) {
        $content = $content.Replace($old1, $new1)
        $updated = $true
    }
    if ($content -match [regex]::Escape($old2)) {
        $content = $content.Replace($old2, $new2)
        $updated = $true
    }
    
    if ($updated) {
        Set-Content -Path $f.FullName -Value $content -NoNewline
        Write-Host "Updated $($f.Name)" -ForegroundColor Green
    }
}

# Update post-commit.hook
$hookPath = "$scriptsDir\post-commit.hook"
if (Test-Path $hookPath) {
    $hookContent = Get-Content $hookPath -Raw
    $hookOld = 'TASKS="C:/devcore/DEV_CORE_DATA/Memory/tasks.json"'
    $hookNew = 'PROJ_NAME=$(basename $(git rev-parse --show-toplevel))' + "`n" + 'TASKS="C:/devcore/DEV_CORE_DATA/Memory/$PROJ_NAME/tasks.json"'
    
    if ($hookContent -match [regex]::Escape($hookOld)) {
        $hookContent = $hookContent.Replace($hookOld, $hookNew)
        Set-Content -Path $hookPath -Value $hookContent -NoNewline
        Write-Host "Updated post-commit.hook" -ForegroundColor Green
    }
}
