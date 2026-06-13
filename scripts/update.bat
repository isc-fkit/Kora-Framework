@echo off
REM ============================================================================
REM update.bat - CAP NHAT app "Adaptive Knowledge Base" ma GIU NGUYEN tri thuc.
REM - Neu cai bang git: chay `git pull` (tri thuc da gitignore nen khong bi dung).
REM - Neu tai zip: tu tai ban moi va chi ghi de phan CHUONG TRINH (CORE).
REM Chay duoc tu bat ky dau - script tu ve thu muc goc repo.
REM ============================================================================
setlocal EnableDelayedExpansion

REM --- Tu ve repo root (cha cua thu muc scripts\) ---
set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%.." || (echo [LOI] Khong vao duoc thu muc repo. & goto :end)
set "REPO_ROOT=%CD%"

set "ZIP_URL=https://github.com/luugiakhanh689/adaptive_knowledge_base/archive/refs/heads/release.zip"

echo ================================================================
echo   CAP NHAT Adaptive Knowledge Base
echo   Thu muc: %REPO_ROOT%
echo ================================================================
echo.

REM --- Doc version cu tu version.json ---
set "OLD_VER=0.0.0"
if exist "%REPO_ROOT%\version.json" (
  for /f "tokens=2 delims=:," %%A in ('findstr /i "\"version\"" "%REPO_ROOT%\version.json"') do (
    set "OLD_VER=%%~A"
  )
)
set "OLD_VER=%OLD_VER: =%"
set "OLD_VER=%OLD_VER:"=%"
echo Phien ban hien tai: v%OLD_VER%
echo.

REM --- Truong hop 1: co .git -> git pull ---
if exist "%REPO_ROOT%\.git" (
  where git >nul 2>nul || (echo [LOI] Ban cai bang git nhung may chua co 'git'. Hay cai git roi chay lai. & goto :end)
  echo Dang cap nhat bang git (tri thuc cua ban duoc giu nguyen)...
  echo.
  git pull --ff-only
  if errorlevel 1 (
    echo.
    echo [CHU Y] Khong the cap nhat tu dong - thuong do ban co thay doi cuc bo trong CORE.
    echo   Cach xu ly:
    echo     1^) Xem thay doi:        git -C "%REPO_ROOT%" status
    echo     2^) Tam cat roi cap nhat: git -C "%REPO_ROOT%" stash ^&^& git -C "%REPO_ROOT%" pull --ff-only ^&^& git -C "%REPO_ROOT%" stash pop
    echo     3^) Bo thay doi CORE:     git -C "%REPO_ROOT%" reset --hard origin/release
    echo   Tri thuc cua ban KHONG bi anh huong du chon cach nao.
    goto :end
  )
  echo.
  echo [OK] Cap nhat git thanh cong.
  goto :version
)

REM --- Truong hop 2: khong co .git -> tai zip + chi cap nhat CORE ---
echo Khong thay thu muc .git -^> ban dang dung ban tai zip.
echo Se tai ban moi nhat va chi ghi de phan CHUONG TRINH.
echo.
where curl       >nul 2>nul || (echo [LOI] Thieu lenh 'curl'. & goto :end)
where tar        >nul 2>nul || (echo [LOI] Thieu lenh 'tar' (de giai nen zip). & goto :end)
where robocopy   >nul 2>nul || (echo [LOI] Thieu lenh 'robocopy'. & goto :end)

set "TMP_DIR=%TEMP%\akb-update-%RANDOM%%RANDOM%"
mkdir "%TMP_DIR%" 2>nul
set "ZIP_FILE=%TMP_DIR%\release.zip"

echo Dang tai ban moi nhat...
curl -fL "%ZIP_URL%" -o "%ZIP_FILE%" || (echo [LOI] Tai ban moi that bai. Kiem tra mang roi thu lai. & goto :end)

echo Dang giai nen...
tar -xf "%ZIP_FILE%" -C "%TMP_DIR%" || (echo [LOI] Giai nen that bai. & goto :end)

REM Tim thu muc *-release vua giai nen
set "SRC_DIR="
for /d %%D in ("%TMP_DIR%\*-release") do set "SRC_DIR=%%D"
if not defined SRC_DIR (echo [LOI] Khong tim thay thu muc nguon sau khi giai nen. & goto :end)

echo Dang ghi de PHAN CHUONG TRINH (giu nguyen tri thuc cua ban)...

REM --- Doc ten vault tu config (KHONG hardcode - moi project mot ten khac) ---
set "VAULT_DIR=Project_Name_Brain"
if exist "%REPO_ROOT%\config\factory-config.yaml" (
  for /f "tokens=2 delims=:" %%A in ('findstr /i /c:"vault_path:" "%REPO_ROOT%\config\factory-config.yaml"') do set "VAULT_DIR=%%A"
)
set "VAULT_DIR=%VAULT_DIR: =%"

REM robocopy /MIR loai tru cac thu muc/file DATA. /XD = exclude dir, /XF = exclude file.
REM KHONG dung /MIR (tranh xoa file ngoai danh sach); dung /E de copy de quy + ghi de.
robocopy "%SRC_DIR%" "%REPO_ROOT%" /E ^
  /XD ".git" "docs\01-domain" "docs\02-product" "docs\03-features" "docs\04-design" "docs\05-architecture" "docs\06-decisions" "docs\08-glossary" "inbox" "%VAULT_DIR%" "*_Brain" ^
  /XF "index.json" "relation-graph.json" "source-registry.json" "health-report.md" "changelog.md" "lessons.md" "factory-config.yaml" "domain-rules.md" ".env.local" ".env.*" >nul
REM robocopy tra ve >=8 la loi that su; 0-7 la binh thuong.
if errorlevel 8 (echo [LOI] Ghi de phan chuong trinh that bai. & goto :end)

REM Don temp
rmdir /s /q "%TMP_DIR%" 2>nul
echo.
echo [OK] Cap nhat chuong trinh thanh cong (tri thuc cua ban duoc giu nguyen).

:version
set "NEW_VER=0.0.0"
if exist "%REPO_ROOT%\version.json" (
  for /f "tokens=2 delims=:," %%A in ('findstr /i "\"version\"" "%REPO_ROOT%\version.json"') do (
    set "NEW_VER=%%~A"
  )
)
set "NEW_VER=%NEW_VER: =%"
set "NEW_VER=%NEW_VER:"=%"
echo.
echo Phien ban moi: v%NEW_VER%
echo.
echo [GOI Y] Neu phan dung index (kb-indexer) co thay doi, hay chay lai:
echo     python3 tools\kb-indexer\build_index.py --root .

:end
echo.
popd 2>nul
pause
endlocal
