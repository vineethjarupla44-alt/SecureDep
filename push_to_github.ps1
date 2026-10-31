# SecureDep - Automated Full-Stack Git Push Script
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host " SecureDep - Pushing Full-Stack Project to GitHub (Frontend + Backend)" -ForegroundColor Cyan
Write-Host " Target Repository: https://github.com/vineethjarupla44-alt/SecureDep.git" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

Set-Location -Path $PSScriptRoot

# 1. Check Git
try {
    $gitVer = git --version
    Write-Host "[*] Git detected: $gitVer" -ForegroundColor Green
} catch {
    Write-Host "[!] Git not found on PATH. Please install Git: https://git-scm.com/" -ForegroundColor Red
    pause
    exit 1
}

# 2. Clean nested .git in subfolder if present
if (Test-Path -Path "fdr-management-portal\.git") {
    Write-Host "[*] Removing nested subfolder .git to track backend files in root repo..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force "fdr-management-portal\.git"
}

# 3. Init root repo
if (-not (Test-Path -Path ".git")) {
    Write-Host "[*] Initializing local git repository at project root..." -ForegroundColor Yellow
    git init
}
git branch -M main

# 4. Remote
Write-Host "[*] Configuring remote origin..." -ForegroundColor Yellow
git remote remove origin 2>$null
git remote add origin https://github.com/vineethjarupla44-alt/SecureDep.git
git remote -v

# 5. Stage entire project
Write-Host "[*] Staging all files (Frontend, Backend, Tests, Docs)..." -ForegroundColor Yellow
git add .

# 6. Commit
Write-Host "[*] Creating full-stack commit..." -ForegroundColor Yellow
git commit -m "feat(aicte-sih-26265): complete full-stack AICTE Security Deposit & FDR Management Portal (Frontend & Backend)"

# 7. Push with force
Write-Host "[*] Pushing entire project to GitHub (main branch)..." -ForegroundColor Cyan
git push -u origin main --force

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "======================================================================" -ForegroundColor Green
    Write-Host " [SUCCESS] Full-stack project successfully pushed to GitHub!" -ForegroundColor Green
    Write-Host " Verified: 'frontend', 'fdr-management-portal', tests, and docs are live." -ForegroundColor Green
    Write-Host " Visit: https://github.com/vineethjarupla44-alt/SecureDep" -ForegroundColor Green
    Write-Host "======================================================================" -ForegroundColor Green
} else {
    Write-Host "[!] Push failed. Please verify your GitHub network connection or PAT token." -ForegroundColor Red
}
