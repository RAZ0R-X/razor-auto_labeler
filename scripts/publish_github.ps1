# GitHub'a v1.0.0 Yayınlama Scripti
# Kullanım: PowerShell'de bu dosyayı çalıştırın

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot ..

Write-Host "=== RAZOR Auto Labeler — GitHub Yayinlama ===" -ForegroundColor Cyan

# GitHub CLI giris kontrolu
$authStatus = gh auth status 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "GitHub'a giris yapmaniz gerekiyor." -ForegroundColor Yellow
    Write-Host "Asagidaki komutu calistirin ve tarayicidan onaylayin:" -ForegroundColor Yellow
    Write-Host "  gh auth login" -ForegroundColor Green
    Write-Host ""
    exit 1
}

Write-Host "GitHub hesabi dogrulandi." -ForegroundColor Green

# Repo olustur veya mevcut repoyu kullan
$username = gh api user -q .login
$repoExists = gh repo view "$username/razor-labeler" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "GitHub reposu olusturuluyor..." -ForegroundColor Cyan
    gh repo create razor-labeler `
        --public `
        --source=. `
        --remote=origin `
        --description "YOLO tabanli nesne tespiti ile otomatik goruntu etiketleme araci (PyQt6)" `
        --push
} else {
    Write-Host "Repo zaten mevcut, push ediliyor..." -ForegroundColor Cyan
    git push -u origin master 2>$null
    if ($LASTEXITCODE -ne 0) {
        git push -u origin main 2>$null
    }
    git push origin v1.0.0
}

# v1.0.0 release olustur
Write-Host "v1.0.0 release olusturuluyor..." -ForegroundColor Cyan
gh release create v1.0.0 `
    --title "RAZOR Auto Labeler v1.0.0" `
    --notes "## RAZOR Auto Labeler v1.0.0 — Ilk Kararli Surum

### Ozellikler
- YOLO tabanli otomatik goruntu etiketleme
- 20+ export formati (YOLOv8/v9/v11/v12, COCO, Pascal VOC, CSV...)
- YOLO-World open-vocabulary model destegi
- Toplu klasor/goruntu isleme
- Sinif yonetimi ve yeniden adlandirma
- PyQt6 modern arayuz

### Kurulum
\`\`\`bash
git clone https://github.com/RAZ0R-X/razor-labeler.git
cd razor-labeler
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
python main.py
\`\`\`

Detayli dokumantasyon icin README.md dosyasina bakin."

Write-Host ""
Write-Host "=== Tamamlandi! ===" -ForegroundColor Green
$repoUrl = gh repo view --json url -q .url
Write-Host "Repo: $repoUrl" -ForegroundColor Cyan
Write-Host "Release: $repoUrl/releases/tag/v1.0.0" -ForegroundColor Cyan
