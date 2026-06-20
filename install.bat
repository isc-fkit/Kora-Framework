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
REM Skill chi-duy-tri (maintainer-only) - khong cai cho nguoi dung thuong.
del /q "%DEST_CMD%\kora-release.md" 2>nul

echo Cai workflows ho tro ...
for %%d in (workflows scripts templates config tools) do (
  if exist "%SRC%\%%d" (
    rmdir /s /q "%DEST_CORE%\%%d" 2>nul
    robocopy "%SRC%\%%d" "%DEST_CORE%\%%d" /E >nul
  )
)
REM Workflow chi-duy-tri - go khoi ban cai nguoi dung.
del /q "%DEST_CORE%\workflows\12-release.md" 2>nul
del /q "%DEST_CORE%\workflows\13-evolve-system.md" 2>nul
if exist "%SRC%\CLAUDE.md" copy /y "%SRC%\CLAUDE.md" "%DEST_CORE%\" >nul

REM --- Resolve thu muc Downloads dong (ho tro Downloads da doi vi tri qua registry) ---
set "DLBASE=%USERPROFILE%\Downloads"
for /f "tokens=2,*" %%a in ('reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders" /v "{374DE290-123F-4565-9164-39C4925E467B}" 2^>nul ^| find "REG_"') do set "DLRAW=%%b"
if defined DLRAW call set "DLBASE=%DLRAW%"
if not exist "%DLBASE%" set "DLBASE=%USERPROFILE%\Downloads"
if not exist "%DLBASE%" set "DLBASE=%USERPROFILE%"

REM --- Dung ROOT Knowledge-Base trong Downloads + KHOI TAO project NGAY (folder skill BEN TRONG) ---
set "ROOT=%DLBASE%\Knowledge-Base"
if defined KORA_PROJECT set "ROOT=%KORA_PROJECT%"
set "SKILL_DIR=%ROOT%\Skill"
if not exist "%SKILL_DIR%" mkdir "%SKILL_DIR%"
del /q "%SKILL_DIR%\kora-*.md" 2>nul
copy /y "%DEST_CMD%\kora-*.md" "%SKILL_DIR%\" >nul 2>nul

REM Khoi tao cau truc project GON ngay trong ROOT (chi khi CHUA phai project Kora -> tranh de tri thuc)
if not exist "%ROOT%\config\factory-config.yaml" if not exist "%ROOT%\config\domain-presets" (
  for %%d in (01-domain 02-product 03-features 04-design 05-architecture 06-decisions 07-research 08-glossary) do mkdir "%ROOT%\docs\%%d" 2>nul
  mkdir "%ROOT%\inbox" 2>nul
  mkdir "%ROOT%\.kb" 2>nul
  mkdir "%ROOT%\config" 2>nul
  mkdir "%ROOT%\Kora_Brain\00_Index" 2>nul
  if exist "%DEST_CORE%\config\factory-config.example.yaml" copy /y "%DEST_CORE%\config\factory-config.example.yaml" "%ROOT%\config\factory-config.yaml" >nul
  if exist "%DEST_CORE%\config\domain-presets" xcopy /e /i /y "%DEST_CORE%\config\domain-presets" "%ROOT%\config\domain-presets" >nul
  >"%ROOT%\CLAUDE.md" echo @~/.claude/kora-framework/CLAUDE.md
  >"%ROOT%\Kora_Brain\00_Index\Knowledge-Base.md" echo # Knowledge Base
)

REM Don folder Kora-Skills kieu cu neu con sot tu ban truoc
rmdir /s /q "%DLBASE%\Kora-Skills" 2>nul
del /q "%DLBASE%\Kora-Skills.zip" 2>nul

rmdir /s /q "%TMP%" 2>nul
echo.
echo [OK] Da cai skills Kora + domain preset (gom Healthcare/Y te, Retail, Manufacturing...) vao ~/.claude.
echo      Project da khoi tao san: %ROOT%
echo      Folder skill (upload vao Cowork): %SKILL_DIR%
echo      Claude Code (CLI): mo  %ROOT%  -^> go  /kora-init (dat domain/ten) roi /kora-scan.
echo      Claude Cowork (App): upload kora-*.md trong  %SKILL_DIR%  vao Skills -^> mo  %ROOT%  -^> go /kora-init.
echo      Cap nhat: chay lai file nay (skill moi tu keo ve, tri thuc giu nguyen).  Go: chay uninstall.bat.
:end
echo.
pause
endlocal
