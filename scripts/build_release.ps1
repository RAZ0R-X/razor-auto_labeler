$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$PyScripts = Join-Path $env:LOCALAPPDATA "Python\pythoncore-3.14-64\Scripts"
if (Test-Path $PyScripts) {
    $env:Path = "$PyScripts;$env:Path"
}

Write-Host "=== RAZOR Auto Labeler - Release Build ===" -ForegroundColor Cyan

Write-Host "[1/5] Generating icon..." -ForegroundColor Yellow
python scripts/build_logo_ico.py

Write-Host "[2/5] Building executable (PyInstaller)..." -ForegroundColor Yellow
if (Test-Path dist) { Remove-Item dist -Recurse -Force -ErrorAction SilentlyContinue }
if (Test-Path build/RAZOR-AutoLabeler) { Remove-Item build/RAZOR-AutoLabeler -Recurse -Force -ErrorAction SilentlyContinue }

$prevEap = $ErrorActionPreference
$ErrorActionPreference = "Continue"
& pyinstaller build/razor_labeler.spec --noconfirm --clean
$buildExit = $LASTEXITCODE
$ErrorActionPreference = $prevEap
if ($buildExit -ne 0) { throw "PyInstaller build failed" }

Write-Host "[3/5] Creating portable ZIP..." -ForegroundColor Yellow
$PortableZip = Join-Path $Root "dist\RAZOR-AutoLabeler-v1.0.0-portable.zip"
if (Test-Path $PortableZip) { Remove-Item $PortableZip -Force }
Compress-Archive -Path "dist\RAZOR-AutoLabeler\*" -DestinationPath $PortableZip -CompressionLevel Optimal

Write-Host "[4/5] Building Windows installer (Inno Setup)..." -ForegroundColor Yellow
$Iscc = @(
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1

if ($Iscc) {
    & $Iscc "installer\setup.iss"
    if ($LASTEXITCODE -ne 0) { throw "Inno Setup build failed" }
}
else {
    Write-Host "Inno Setup not found - skipping installer." -ForegroundColor Yellow
}

Write-Host "[5/5] Build complete!" -ForegroundColor Green
Write-Host ""
Get-ChildItem dist -File | ForEach-Object {
    $sizeMB = [math]::Round($_.Length / 1MB, 1)
    Write-Host "  $($_.Name) ($sizeMB MB)" -ForegroundColor Cyan
}
if (Test-Path "dist\RAZOR-AutoLabeler\RAZOR-AutoLabeler.exe") {
    Write-Host "  RAZOR-AutoLabeler\RAZOR-AutoLabeler.exe (portable)" -ForegroundColor Cyan
}
