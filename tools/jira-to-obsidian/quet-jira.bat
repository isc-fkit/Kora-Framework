@echo off
REM Double-click file nay de quet Jira -> vault (Windows).
cd /d "%~dp0"
echo === AI Product Factory - Quet Jira -^> Obsidian Vault ===
echo.
py import_jira.py --test
if errorlevel 1 ( echo. & pause & exit /b 1 )
echo.
echo Ket noi OK. Nhan phim bat ky de BAT DAU QUET...
pause >nul
py import_jira.py
echo.
echo Xong! Quay lai Cowork nhan "da quet xong".
pause
