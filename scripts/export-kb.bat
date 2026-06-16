@echo off
REM ============================================================================
REM export-kb.bat - XUAT toan bo tri thuc (DATA) ra 1 file .zip de doi may.
REM Goi gom: vault (*_Brain), du lieu .kb, cac thu muc docs nghiep vu, inbox,
REM config (factory-config.yaml + domain-rules.md) va cac file .env (TRU .env.example).
REM Kem manifest.json ghi phien ban + duong dan vault.
REM Chay duoc tu bat ky dau - script tu ve thu muc goc repo.
REM ============================================================================
setlocal EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%.." || (echo [LOI] Khong vao duoc thu muc repo. & goto :end)
set "REPO_ROOT=%CD%"
set "CFG=%REPO_ROOT%\config\factory-config.yaml"

REM --- Go "Mark of the Web" cho cac script con lai -> lan sau double-click khong bi SmartScreen hoi ---
powershell -NoProfile -Command "Get-ChildItem -LiteralPath '%REPO_ROOT%\scripts' -Recurse -File -ErrorAction SilentlyContinue | Unblock-File -ErrorAction SilentlyContinue" >nul 2>nul
echo [OK] Da go nhan canh bao cho cac script - lan sau double-click chay thang, khong bi hoi lai.
echo.

where tar >nul 2>nul || (echo [LOI] Thieu lenh 'tar' (de tao zip). & goto :end)

REM --- Ngay gio: tu bien NGAY hoac tu sinh (YYYYMMDD-HHMM) ---
if not defined NGAY (
  for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd-HHmm"') do set "NGAY=%%I"
)

REM --- Doc vault_path va project_name tu config ---
set "VAULT=Project_Name_Brain"
set "PROJECT=project"
if exist "%CFG%" (
  for /f "tokens=1,* delims=:" %%A in ('findstr /b /i /c:"  vault_path:" /c:"vault_path:" "%CFG%"') do (
    set "VAULT=%%B"
  )
  for /f "tokens=1,* delims=:" %%A in ('findstr /b /i /c:"project_name:" "%CFG%"') do (
    set "PROJECT=%%B"
  )
)
REM Cat khoang trang dau/cuoi + comment
for /f "tokens=* delims= " %%V in ("!VAULT!") do set "VAULT=%%V"
for /f "tokens=* delims= " %%V in ("!PROJECT!") do set "PROJECT=%%V"
for /f "tokens=1 delims=#" %%V in ("!VAULT!") do set "VAULT=%%V"
set "VAULT=!VAULT: =!"

REM --- Doc version tu version.json ---
set "VERSION=0.0.0"
if exist "%REPO_ROOT%\version.json" (
  for /f "tokens=2 delims=:," %%A in ('findstr /i "\"version\"" "%REPO_ROOT%\version.json"') do set "VERSION=%%~A"
)
set "VERSION=%VERSION: =%"
set "VERSION=%VERSION:"=%"

REM --- Ten project an toan cho ten file ---
set "SAFE_PROJECT=%PROJECT: =-%"
set "SAFE_PROJECT=%SAFE_PROJECT:\=-%"
set "SAFE_PROJECT=%SAFE_PROJECT:/=-%"
set "SAFE_PROJECT=%SAFE_PROJECT::=-%"
if "%SAFE_PROJECT%"=="" set "SAFE_PROJECT=project"

set "ZIP_NAME=genesis1-kb-%SAFE_PROJECT%-%NGAY%.zip"
set "ZIP_PATH=%REPO_ROOT%\%ZIP_NAME%"

echo ================================================================
echo   XUAT tri thuc - Adaptive Knowledge Base (Genesis-1)
echo   Project : %PROJECT%
echo   Vault   : %VAULT%
echo   Phien ban: v%VERSION%
echo ================================================================
echo.

REM --- Thu muc tam de gom DATA + manifest ---
set "STAGE=%TEMP%\akb-export-%RANDOM%%RANDOM%"
mkdir "%STAGE%" 2>nul

REM Ham phu: copy 1 path neu ton tai (dir hoac file), giu cau truc tuong doi.
call :stage_dir  "%VAULT%"
call :stage_file ".kb\index.json"
call :stage_file ".kb\relation-graph.json"
call :stage_file ".kb\source-registry.json"
call :stage_file ".kb\health-report.md"
call :stage_file ".kb\changelog.md"
call :stage_file ".kb\lessons.md"
call :stage_dir  "docs\01-domain"
call :stage_dir  "docs\02-product"
call :stage_dir  "docs\03-features"
call :stage_dir  "docs\04-design"
call :stage_dir  "docs\05-architecture"
call :stage_dir  "docs\06-decisions"
call :stage_dir  "docs\08-glossary"
call :stage_dir  "inbox"
call :stage_file "config\factory-config.yaml"
call :stage_file "config\domain-rules.md"

REM Cac file .env* trong tools\jira-to-obsidian TRU .env.example
for %%F in ("%REPO_ROOT%\tools\jira-to-obsidian\.env*") do (
  if /i not "%%~nxF"==".env.example" call :stage_file "tools\jira-to-obsidian\%%~nxF"
)

REM --- Tao manifest.json ---
for /f %%T in ('powershell -NoProfile -Command "(Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')"') do set "EXPORTED_AT=%%T"
(
  echo {
  echo   "version": "%VERSION%",
  echo   "exported_at": "%EXPORTED_AT%",
  echo   "vault_path": "%VAULT%",
  echo   "project_name": "%PROJECT%"
  echo }
) > "%STAGE%\manifest.json"

echo Dang dong goi...
if exist "%ZIP_PATH%" del /q "%ZIP_PATH%"
pushd "%STAGE%"
tar -a -c -f "%ZIP_PATH%" * || (popd & echo [LOI] Dong goi that bai. & goto :clean)
popd

for %%S in ("%ZIP_PATH%") do set "SIZE=%%~zS"
echo.
echo [OK] Da tao goi tri thuc:
echo      %ZIP_PATH%
echo      Kich thuoc: %SIZE% bytes
echo.
echo [GOI Y] Chep file nay sang may moi (da cai ban app sach) roi chay import-kb.bat

:clean
rmdir /s /q "%STAGE%" 2>nul
goto :end

REM ---------- Ham phu ----------
:stage_dir
if exist "%REPO_ROOT%\%~1\" (
  robocopy "%REPO_ROOT%\%~1" "%STAGE%\%~1" /E >nul
)
exit /b 0

:stage_file
if exist "%REPO_ROOT%\%~1" (
  for %%P in ("%STAGE%\%~1") do if not exist "%%~dpP" mkdir "%%~dpP" 2>nul
  copy /y "%REPO_ROOT%\%~1" "%STAGE%\%~1" >nul
)
exit /b 0

:end
echo.
popd 2>nul
pause
endlocal
