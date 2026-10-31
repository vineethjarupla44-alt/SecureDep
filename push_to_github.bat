@echo off
setlocal enabledelayedexpansion

echo ======================================================================
echo  SecureDep - Pushing Full-Stack Project to GitHub (Frontend + Backend)
echo  Target Repository: https://github.com/vineethjarupla44-alt/SecureDep.git
echo ======================================================================

cd /d "%~dp0"

echo.
echo [*] Step 1: Checking Git installation...
where git >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [!] ERROR: Git executable not found on system PATH.
    echo Please install Git from https://git-scm.com/ and rerun this script.
    pause
    exit /b 1
)
git --version

echo.
echo [*] Step 2: Preparing root Git repository...
rem Remove nested git repository if created inside backend or fdr-management-portal
if exist "backend\.git" (
    echo [*] Removing nested subfolder .git to ensure entire backend is committed...
    attrib -h -r -s "backend\.git\*.*" /s /d >nul 2>&1
    rd /s /q "backend\.git" >nul 2>&1
)
if exist "fdr-management-portal\.git" (
    echo [*] Removing nested subfolder .git to ensure entire backend is committed...
    attrib -h -r -s "fdr-management-portal\.git\*.*" /s /d >nul 2>&1
    rd /s /q "fdr-management-portal\.git" >nul 2>&1
)

if not exist .git (
    git init
)
git branch -M main

echo.
echo [*] Step 3: Configuring remote repository...
git remote remove origin >nul 2>&1
git remote add origin https://github.com/vineethjarupla44-alt/SecureDep.git
echo Remote origin configured:
git remote -v

echo.
echo [*] Step 4: Staging entire project (Frontend + Backend + Root Docs + Tests)...
git add .

echo.
echo [*] Step 5: Creating comprehensive full-stack commit...
git commit -m "feat(aicte-sih-26265): complete full-stack AICTE Security Deposit & FDR Management Portal (Frontend & Backend)"

echo.
echo [*] Step 6: Pushing complete project to GitHub (main branch)...
echo Note: If prompted, sign in via Git Credential Manager or enter your GitHub Personal Access Token (PAT).
echo.
git push -u origin main --force

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ======================================================================
    echo [SUCCESS] Full-stack project successfully pushed to GitHub!
    echo Verified: Both 'frontend' and 'backend' are now on GitHub.
    echo Visit: https://github.com/vineethjarupla44-alt/SecureDep
    echo ======================================================================
) else (
    echo.
    echo [!] Push encountered an error. Please check your GitHub credentials or internet connection.
)

echo.
pause
