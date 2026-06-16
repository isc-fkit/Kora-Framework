@echo off
REM ============================================================================
REM import-kb.bat - NHAP tri thuc (DATA) tren mot may moi da cai ban app sach.
REM Cach dung:  scripts\import-kb.bat [duong-dan-file.zip]
REM   - Khong truyen: tu lay file genesis1-kb-*.zip MOI NHAT o goc repo.
REM Viec lam: giai nen -> doc manifest.json -> copy DATA ve dung cho ->
REM   cap nhat vault_path trong config -> dung lai index bang kb-indexer.
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

where tar >nul 2>nul || (echo [LOI] Thieu lenh 'tar' (de giai nen zip). & goto :end)

echo ================================================================
echo   NHAP tri thuc - Adaptive Knowledge Base (Genesis-1)
echo   Thu muc: %REPO_ROOT%
echo ================================================================
echo.

REM --- Xac dinh file zip ---
set "ZIP_IN=%~1"
if "%ZIP_IN%"=="" (
  REM Lay genesis1-kb-*.zip moi nhat (sap theo thoi gian, moi nhat truoc)
  for /f "delims=" %%F in ('dir /b /a-d /o-d "%REPO_ROOT%\genesis1-kb-*.zip" 2^>nul') do (
    set "ZIP_IN=%REPO_ROOT%\%%F"
    goto :gotzip
  )
)
:gotzip
if "%ZIP_IN%"=="" (echo [LOI] Khong tim thay file genesis1-kb-*.zip. Hay truyen duong dan file zip lam tham so. & goto :end)
if not exist "%ZIP_IN%" (echo [LOI] Khong thay file zip: %ZIP_IN% & goto :end)
echo Dung goi: %ZIP_IN%
echo.

REM --- Giai nen ra temp ---
set "TMP_DIR=%TEMP%\akb-import-%RANDOM%%RANDOM%"
mkdir "%TMP_DIR%" 2>nul
echo Dang giai nen...
tar -xf "%ZIP_IN%" -C "%TMP_DIR%" || (echo [LOI] Giai nen that bai (file co the hong). & goto :clean)

set "MANIFEST=%TMP_DIR%\manifest.json"
if not exist "%MANIFEST%" (echo [LOI] Goi khong hop le: thieu manifest.json. & goto :clean)

REM --- Doc vault_path tu manifest ---
set "MANIFEST_VAULT="
for /f "tokens=2 delims=:," %%A in ('findstr /i "vault_path" "%MANIFEST%"') do (
  set "MANIFEST_VAULT=%%~A"
)
set "MANIFEST_VAULT=%MANIFEST_VAULT: =%"
set "MANIFEST_VAULT=%MANIFEST_VAULT:"=%"
if "%MANIFEST_VAULT%"=="" set "MANIFEST_VAULT=Project_Name_Brain"
echo Vault trong goi: %MANIFEST_VAULT%
echo.

REM --- Canh bao neu ghi de vault dang co ---
if exist "%REPO_ROOT%\%MANIFEST_VAULT%\" (
  echo [CHU Y] Thu muc vault "%MANIFEST_VAULT%" DA ton tai va se bi GHI DE.
  set /p "ANS=    Tiep tuc? (y/N) "
  if /i not "!ANS!"=="y" (echo Da huy. Khong co gi bi thay doi. & goto :clean)
  REM User dong y -> xoa sach vault cu de THAY moi (tranh file thua).
  rmdir /s /q "%REPO_ROOT%\%MANIFEST_VAULT%" 2>nul
)

echo.
echo Dang nhap du lieu ve dung cho...

REM --- Copy moi thu trong temp (tru manifest.json) ve repo root ---
set "COUNT=0"
for /d %%D in ("%TMP_DIR%\*") do (
  robocopy "%%D" "%REPO_ROOT%\%%~nxD" /E >nul
)
for %%F in ("%TMP_DIR%\*") do (
  if /i not "%%~nxF"=="manifest.json" copy /y "%%F" "%REPO_ROOT%\%%~nxF" >nul
)
REM Dem so file da nhap
for /f %%N in ('dir /b /s /a-d "%TMP_DIR%" 2^>nul ^| find /c /v ""') do set "COUNT=%%N"
REM Bot 1 cho manifest.json
set /a COUNT=COUNT-1
if %COUNT% LSS 0 set "COUNT=0"

REM --- Cap nhat vault_path trong config cho khop manifest ---
if exist "%CFG%" (
  powershell -NoProfile -Command ^
    "$c=Get-Content -LiteralPath '%CFG%'; $c = $c -replace '^(\s*)vault_path:.*$', ('${1}vault_path: %MANIFEST_VAULT%'); Set-Content -LiteralPath '%CFG%' -Value $c" 2>nul
  echo Da cap nhat vault_path trong config: %MANIFEST_VAULT%
)

REM --- Dung lai index ---
echo.
echo Dang dung lai index (kb-indexer)...
where python3 >nul 2>nul
if not errorlevel 1 (
  python3 "%REPO_ROOT%\tools\kb-indexer\build_index.py" --root .
) else (
  where python >nul 2>nul
  if not errorlevel 1 (
    python "%REPO_ROOT%\tools\kb-indexer\build_index.py" --root .
  ) else (
    echo [CHU Y] Khong thay python - bo qua. Sau khi cai python, chay:
    echo     python tools\kb-indexer\build_index.py --root .
  )
)

echo.
echo [OK] Da nhap xong, %COUNT% file.

:clean
rmdir /s /q "%TMP_DIR%" 2>nul

:end
echo.
popd 2>nul
pause
endlocal
