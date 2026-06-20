@echo off
REM uninstall.bat - Go Kora-Framework skills khoi %USERPROFILE%\.claude. (Tri thuc/project KHONG bi dung.)
setlocal

set "DEST_CMD=%USERPROFILE%\.claude\commands"
set "DEST_CORE=%USERPROFILE%\.claude\kora-framework"

REM Resolve Downloads (dong bo voi installer) de don folder Skill
set "DLBASE=%USERPROFILE%\Downloads"
for /f "tokens=2,*" %%a in ('reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders" /v "{374DE290-123F-4565-9164-39C4925E467B}" 2^>nul ^| find "REG_"') do set "DLRAW=%%b"
if defined DLRAW call set "DLBASE=%DLRAW%"
if not exist "%DLBASE%" set "DLBASE=%USERPROFILE%\Downloads"
set "SKILL_DIR=%DLBASE%\Knowledge-Base\Skill"

echo ================================================================
echo   Go Kora-Framework skills khoi ~/.claude
echo ================================================================
echo Se xoa:
echo   - %DEST_CMD%\kora-*.md
echo   - %DEST_CORE%\
echo   - %SKILL_DIR%\  (chi skill - tri thuc trong Knowledge-Base duoc giu)
echo.
set "ANS="
set /p ANS="Go 'yes' de xac nhan: "
if /i not "%ANS%"=="yes" (echo Da huy. & pause & exit /b 0)

del /q "%DEST_CMD%\kora-*.md" 2>nul
rmdir /s /q "%DEST_CORE%" 2>nul
rmdir /s /q "%SKILL_DIR%" 2>nul
rmdir "%DLBASE%\Knowledge-Base" 2>nul
rmdir /s /q "%USERPROFILE%\Downloads\Kora-Skills" 2>nul
del /q "%USERPROFILE%\Downloads\Kora-Skills.zip" 2>nul
echo.
echo [OK] Da go skill Kora.
echo Neu ban tung dat token API, hay xoa tay cac dong KORA_ trong bien moi truong.
pause
endlocal
