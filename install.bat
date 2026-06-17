@echo off
REM install.bat - Cai Kora-Framework skills vao %USERPROFILE%\.claude (managed, khong de lai folder source).
REM Double-click de chay. Chay lai = cap nhat (tu keo ban moi, them skill moi).
setlocal EnableDelayedExpansion

set "REPO=isc-fkit/Kora-Framework"
set "REF=release"
set "DEST_CMD=%USERPROFILE%\.claude\commands"
set "DEST_CORE=%USERPROFILE%\.claude\kora-framework"

echo ================================================================
echo   Kora-Framework - cai skills vao ~/.claude
echo ================================================================
echo.

where curl >nul 2>nul || (echo [LOI] Thieu 'curl'. & pause & exit /b 1)
where tar  >nul 2>nul || (echo [LOI] Thieu 'tar'.  & pause & exit /b 1)

if not exist "%DEST_CMD%"  mkdir "%DEST_CMD%"
if not exist "%DEST_CORE%" mkdir "%DEST_CORE%"

set "TMP=%TEMP%\kora-install-%RANDOM%%RANDOM%"
mkdir "%TMP%" 2>nul

echo Dang tai ban moi nhat...
curl -fsSL "https://github.com/%REPO%/archive/refs/heads/%REF%.tar.gz" -o "%TMP%\src.tgz" || (echo [LOI] Tai that bai. & goto end)
echo Dang giai nen...
tar -xzf "%TMP%\src.tgz" -C "%TMP%" || (echo [LOI] Giai nen that bai. & goto end)

set "SRC="
for /d %%D in ("%TMP%\*-%REF%") do set "SRC=%%D"
if not defined SRC (echo [LOI] Khong thay thu muc nguon. & goto end)

echo Cai lenh /kora-* ...
del /q "%DEST_CMD%\kora-*.md" 2>nul
copy /y "%SRC%\.claude\commands\kora-*.md" "%DEST_CMD%\" >nul

echo Cai workflows ho tro ...
for %%d in (workflows scripts templates config tools) do (
  if exist "%SRC%\%%d" (
    rmdir /s /q "%DEST_CORE%\%%d" 2>nul
    robocopy "%SRC%\%%d" "%DEST_CORE%\%%d" /E >nul
  )
)
if exist "%SRC%\CLAUDE.md" copy /y "%SRC%\CLAUDE.md" "%DEST_CORE%\" >nul

rmdir /s /q "%TMP%" 2>nul
echo.
echo [OK] Da cai skills Kora vao ~/.claude.
echo      Tao project: trong Cowork mo/tao 1 folder trong -^> go  /kora-init (tu dung project).
echo      Cap nhat: chay lai file nay.  Go: chay uninstall.bat.
:end
echo.
pause
endlocal
