@echo off
REM uninstall.bat - Go Kora-Framework skills khoi %USERPROFILE%\.claude. (Tri thuc/project KHONG bi dung.)
setlocal

set "DEST_CMD=%USERPROFILE%\.claude\commands"
set "DEST_CORE=%USERPROFILE%\.claude\kora-framework"

echo ================================================================
echo   Go Kora-Framework skills khoi ~/.claude
echo ================================================================
echo Se xoa:
echo   - %DEST_CMD%\kora-*.md
echo   - %DEST_CORE%\
echo.
set "ANS="
set /p ANS="Go 'yes' de xac nhan: "
if /i not "%ANS%"=="yes" (echo Da huy. & pause & exit /b 0)

del /q "%DEST_CMD%\kora-*.md" 2>nul
rmdir /s /q "%DEST_CORE%" 2>nul
echo.
echo [OK] Da go skill Kora.
echo Neu ban tung dat token API, hay xoa tay cac dong KORA_ trong bien moi truong.
pause
endlocal
