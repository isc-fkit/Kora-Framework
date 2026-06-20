@echo off
REM ============================================================================
REM archive-kb.bat - DONG GOI KB co PHAN QUYEN + mat khau de ban giao cho user.
REM Goi = thu muc 'kora-archive\' { manifest.json, data\, .env.local (key READ), markers\ }.
REM Bien moi truong (Claude dieu phoi): KORA_ARCHIVE_PW, KORA_PKG_TYPE, KORA_PKG_PERMISSION,
REM   KORA_CLOUD_READ_BASE_URL, KORA_CLOUD_READ_USER, KORA_CLOUD_READ_TOKEN, KORA_CLOUD_SPACE.
REM ============================================================================
setlocal EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%.." || (echo [LOI] Khong vao duoc repo. & goto :end)
set "REPO_ROOT=%CD%"
set "CFG=%REPO_ROOT%\config\factory-config.yaml"
where py >nul 2>nul && (set "PY=py") || (set "PY=python")
where tar >nul 2>nul || (echo [LOI] Thieu 'tar'. & goto :end)

REM --- CONG MAT KHAU ---
echo [..] Kiem tra mat khau archive...
"%PY%" "%REPO_ROOT%\tools\archive-gate\verify_password.py" >nul || (echo [LOI] Sai mat khau - khong tao archive. & goto :end)
echo [OK] Mat khau hop le.

if not defined KORA_PKG_TYPE set "KORA_PKG_TYPE=user"
if not defined KORA_PKG_PERMISSION set "KORA_PKG_PERMISSION=read-only"

if not defined NGAY (
  for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd-HHmm"') do set "NGAY=%%I"
)

set "VAULT=Project_Name_Brain"
set "PROJECT=project"
if exist "%CFG%" (
  for /f "tokens=1,* delims=:" %%A in ('findstr /b /i /c:"  vault_path:" /c:"vault_path:" "%CFG%"') do set "VAULT=%%B"
  for /f "tokens=1,* delims=:" %%A in ('findstr /b /i /c:"project_name:" "%CFG%"') do set "PROJECT=%%B"
)
for /f "tokens=* delims= " %%V in ("!VAULT!") do set "VAULT=%%V"
for /f "tokens=* delims= " %%V in ("!PROJECT!") do set "PROJECT=%%V"
for /f "tokens=1 delims=#" %%V in ("!VAULT!") do set "VAULT=%%V"
set "VAULT=!VAULT: =!"

set "VERSION=0.0.0"
if exist "%REPO_ROOT%\version.json" (
  for /f "tokens=2 delims=:," %%A in ('findstr /i "\"version\"" "%REPO_ROOT%\version.json"') do set "VERSION=%%~A"
)
set "VERSION=%VERSION: =%"
set "VERSION=%VERSION:"=%"

set "SAFE_PROJECT=%PROJECT: =-%"
set "SAFE_PROJECT=%SAFE_PROJECT:\=-%"
set "SAFE_PROJECT=%SAFE_PROJECT:/=-%"
if "%SAFE_PROJECT%"=="" set "SAFE_PROJECT=project"
set "ZIP_PATH=%REPO_ROOT%\kora-archive-%SAFE_PROJECT%-%NGAY%.zip"

echo ================================================================
echo   ARCHIVE ban giao - Kora-Framework
echo   Project: %PROJECT% ^| Loai: %KORA_PKG_TYPE% (%KORA_PKG_PERMISSION%) ^| v%VERSION%
echo ================================================================

set "STAGEP=%TEMP%\akb-archive-%RANDOM%%RANDOM%"
set "STAGE=%STAGEP%\kora-archive"
mkdir "%STAGE%\data" 2>nul
mkdir "%STAGE%\markers" 2>nul

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
REM Goi USER: KHONG kem reports\ (chi HOST co bao cao)
if /i not "%KORA_PKG_TYPE%"=="user" call :stage_dir "reports"

REM AN TOAN: xoa MOI .env* lo trong data\ (gom .env.jira/.env.github/.env.cloud...), GIU .env.example.
for /r "%STAGE%\data" %%F in (.env .env.*) do if /i not "%%~nxF"==".env.example" del /q "%%F" 2>nul

REM Key READ-ONLY (neu co)
if defined KORA_CLOUD_READ_TOKEN (
  (
    echo # Key READ-ONLY cloud-KB chung ^(ship trong archive^) - chi GET.
    echo CONFLUENCE_BASE_URL=%KORA_CLOUD_READ_BASE_URL%
    echo CONFLUENCE_EMAIL=%KORA_CLOUD_READ_USER%
    echo CONFLUENCE_API_TOKEN=%KORA_CLOUD_READ_TOKEN%
    echo CONFLUENCE_AUTH=token
  ) > "%STAGE%\.env.local"
  echo [OK] Da ship key READ-ONLY.
) else (
  echo [..] Khong co KORA_CLOUD_READ_TOKEN - goi khong kem key doc.
)

for /f %%T in ('powershell -NoProfile -Command "(Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')"') do set "EXPORTED_AT=%%T"
(
  echo {
  echo   "version": "%VERSION%",
  echo   "exported_at": "%EXPORTED_AT%",
  echo   "vault_path": "%VAULT%",
  echo   "project_name": "%PROJECT%",
  echo   "package_type": "%KORA_PKG_TYPE%",
  echo   "permission": "%KORA_PKG_PERMISSION%",
  echo   "cloud_kb": { "base_url": "%KORA_CLOUD_READ_BASE_URL%", "space": "%KORA_CLOUD_SPACE%" }
  echo }
) > "%STAGE%\manifest.json"
echo %KORA_PKG_TYPE%> "%STAGE%\markers\package.type"

echo Dang dong goi...
if exist "%ZIP_PATH%" del /q "%ZIP_PATH%"
pushd "%STAGEP%"
tar -a -c -f "%ZIP_PATH%" kora-archive || (popd & echo [LOI] Dong goi that bai. & goto :clean)
popd

echo.
echo [OK] Da tao archive: %ZIP_PATH%
echo [GOI Y] Gui file cho user -^> ho chay import-kb.bat

:clean
rmdir /s /q "%STAGEP%" 2>nul
goto :end

:stage_dir
if exist "%REPO_ROOT%\%~1\" robocopy "%REPO_ROOT%\%~1" "%STAGE%\data\%~1" /E >nul
exit /b 0

:stage_file
if exist "%REPO_ROOT%\%~1" (
  for %%P in ("%STAGE%\data\%~1") do if not exist "%%~dpP" mkdir "%%~dpP" 2>nul
  copy /y "%REPO_ROOT%\%~1" "%STAGE%\data\%~1" >nul
)
exit /b 0

:end
echo.
popd 2>nul
pause
endlocal
