@echo off
REM ============================================================================
REM import-kb.bat - NHAP tri thuc (DATA) tren may da cai ban app sach (Windows).
REM   Ho tro 2 loai goi (NGANG voi import-kb.command tren macOS/Linux):
REM     - SAO LUU (export-kb): kora-kb-*.zip / genesis1-kb-*.zip - DATA phang + manifest.json.
REM     - ARCHIVE ban giao (archive-kb): kora-archive-*.zip - co thu muc 'kora-archive\'
REM       gom data\, manifest.json (package_type/permission), .env.local (key READ),
REM       notify-smtp.env (cred bao loi), markers\.
REM Cach dung:  scripts\import-kb.bat [duong-dan-file.zip]
REM   - Khong truyen: tu lay file MOI NHAT (kora-archive-* > kora-kb-* > genesis1-kb-*) o goc repo.
REM ============================================================================
setlocal EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%.." || (echo [LOI] Khong vao duoc thu muc repo. & goto :end)
set "REPO_ROOT=%CD%"
set "CFG=%REPO_ROOT%\config\factory-config.yaml"

REM --- Go "Mark of the Web" cho cac script con lai ---
powershell -NoProfile -Command "Get-ChildItem -LiteralPath '%REPO_ROOT%\scripts' -Recurse -File -ErrorAction SilentlyContinue | Unblock-File -ErrorAction SilentlyContinue" >nul 2>nul
echo [OK] Da go nhan canh bao cho cac script - lan sau double-click chay thang.
echo.

where tar >nul 2>nul || (echo [LOI] Thieu lenh 'tar' (de giai nen zip). & goto :end)

echo ================================================================
echo   NHAP tri thuc - Kora-Framework
echo   Thu muc: %REPO_ROOT%
echo ================================================================
echo.

REM --- Xac dinh file zip (uu tien kora-archive- > kora-kb- > genesis1-kb-) ---
set "ZIP_IN=%~1"
if "%ZIP_IN%"=="" (
  for /f "delims=" %%F in ('dir /b /a-d /o-d "%REPO_ROOT%\kora-archive-*.zip" 2^>nul') do ( set "ZIP_IN=%REPO_ROOT%\%%F" & goto :gotzip )
  for /f "delims=" %%F in ('dir /b /a-d /o-d "%REPO_ROOT%\*-kb-*.zip" 2^>nul') do ( set "ZIP_IN=%REPO_ROOT%\%%F" & goto :gotzip )
)
:gotzip
if "%ZIP_IN%"=="" (echo [LOI] Khong tim thay goi (kora-archive-*.zip / kora-kb-*.zip). Hay truyen duong dan file zip. & goto :end)
if not exist "%ZIP_IN%" (echo [LOI] Khong thay file zip: %ZIP_IN% & goto :end)
echo Dung goi: %ZIP_IN%
echo.

REM --- Giai nen ra temp ---
set "TMP_DIR=%TEMP%\akb-import-%RANDOM%%RANDOM%"
mkdir "%TMP_DIR%" 2>nul
echo Dang giai nen...
tar -xf "%ZIP_IN%" -C "%TMP_DIR%" || (echo [LOI] Giai nen that bai (file co the hong). & goto :clean)

REM --- Nhan dien loai goi: ARCHIVE (co kora-archive\) hay SAO LUU phang ---
set "ARCHIVE_MODE=0"
set "PKG_ROOT=%TMP_DIR%"
set "DATA_SRC=%TMP_DIR%"
if exist "%TMP_DIR%\kora-archive\manifest.json" (
  set "ARCHIVE_MODE=1"
  set "PKG_ROOT=%TMP_DIR%\kora-archive"
  set "DATA_SRC=%TMP_DIR%\kora-archive\data"
)
set "MANIFEST=%PKG_ROOT%\manifest.json"
if not exist "%MANIFEST%" (echo [LOI] Goi khong hop le: thieu manifest.json. & goto :clean)

REM --- Doc vault_path + package_type tu manifest ---
set "MANIFEST_VAULT="
for /f "tokens=2 delims=:," %%A in ('findstr /i "vault_path" "%MANIFEST%"') do set "MANIFEST_VAULT=%%~A"
set "MANIFEST_VAULT=%MANIFEST_VAULT: =%"
set "MANIFEST_VAULT=%MANIFEST_VAULT:"=%"
if "%MANIFEST_VAULT%"=="" set "MANIFEST_VAULT=Project_Name_Brain"
set "PKG_TYPE="
for /f "tokens=2 delims=:," %%A in ('findstr /i "package_type" "%MANIFEST%"') do set "PKG_TYPE=%%~A"
set "PKG_TYPE=%PKG_TYPE: =%"
set "PKG_TYPE=%PKG_TYPE:"=%"
if "%PKG_TYPE%"=="" set "PKG_TYPE=host"
echo Vault trong goi : %MANIFEST_VAULT%
echo Loai goi        : %PKG_TYPE%
echo.

REM --- Canh bao neu ghi de vault dang co ---
if exist "%REPO_ROOT%\%MANIFEST_VAULT%\" (
  echo [CHU Y] Thu muc vault "%MANIFEST_VAULT%" DA ton tai va se bi GHI DE.
  set /p "ANS=    Tiep tuc? (y/N) "
  if /i not "!ANS!"=="y" (echo Da huy. Khong co gi bi thay doi. & goto :clean)
  rmdir /s /q "%REPO_ROOT%\%MANIFEST_VAULT%" 2>nul
)

echo.
echo Dang nhap du lieu ve dung cho...
REM Copy CA cay DATA_SRC vao repo root, tru manifest.json. (Archive: data\ khong co file dieu khien.)
robocopy "%DATA_SRC%" "%REPO_ROOT%" /E /XF manifest.json >nul
set "COUNT=0"
for /f %%N in ('dir /b /s /a-d "%DATA_SRC%" 2^>nul ^| find /c /v ""') do set "COUNT=%%N"

REM --- Cap nhat vault_path trong config cho khop manifest ---
if exist "%CFG%" (
  powershell -NoProfile -Command ^
    "$c=Get-Content -LiteralPath '%CFG%'; $c = $c -replace '^(\s*)vault_path:.*$', ('${1}vault_path: %MANIFEST_VAULT%'); Set-Content -LiteralPath '%CFG%' -Value $c" 2>nul
  echo Da cap nhat vault_path trong config: %MANIFEST_VAULT%
)

REM --- Goi USER: dat key READ + cred bao loi + danh dau .kora-user ---
if "%ARCHIVE_MODE%"=="1" if /i "%PKG_TYPE%"=="user" (
  if exist "%PKG_ROOT%\.env.local" (
    mkdir "%REPO_ROOT%\tools\confluence-sync" 2>nul
    copy /y "%PKG_ROOT%\.env.local" "%REPO_ROOT%\tools\confluence-sync\.env.local" >nul
    echo [OK] Da dat key READ cloud-KB vao tools\confluence-sync\.env.local (chi GET).
  )
  if exist "%PKG_ROOT%\github.env" (
    mkdir "%REPO_ROOT%\tools\github-sync" 2>nul
    copy /y "%PKG_ROOT%\github.env" "%REPO_ROOT%\tools\github-sync\.env.local" >nul
    echo [OK] Da dat token READ GitHub vao tools\github-sync\.env.local (chi PULL).
  )
  if exist "%PKG_ROOT%\notify-smtp.env" (
    mkdir "%REPO_ROOT%\tools\report-mailer" 2>nul
    copy /y "%PKG_ROOT%\notify-smtp.env" "%REPO_ROOT%\tools\report-mailer\.env.local" >nul
    echo [OK] Da dat cred SMTP no-reply bao loi vao tools\report-mailer\.env.local.
  )
  (
    echo package=user
    echo imported_at=%DATE% %TIME%
  ) > "%REPO_ROOT%\.kora-user"
  echo [OK] Da tao .kora-user - may nay la GOI NGUOI DUNG: TAT bao cao/gui mail; chi get^&post KB chung.
)

REM --- Dung lai index (py > python3 > python) ---
echo.
echo Dang dung lai index (kb-indexer)...
where py >nul 2>nul && (py "%REPO_ROOT%\tools\kb-indexer\build_index.py" --root . & goto :indexed)
where python3 >nul 2>nul && (python3 "%REPO_ROOT%\tools\kb-indexer\build_index.py" --root . & goto :indexed)
where python >nul 2>nul && (python "%REPO_ROOT%\tools\kb-indexer\build_index.py" --root . & goto :indexed)
echo [CHU Y] Khong thay py/python - bo qua. Sau khi cai Python, chay:
echo     py tools\kb-indexer\build_index.py --root .
:indexed

echo.
echo [OK] Da nhap xong, %COUNT% file.

:clean
rmdir /s /q "%TMP_DIR%" 2>nul

:end
echo.
popd 2>nul
pause
endlocal
