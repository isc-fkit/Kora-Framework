@echo off
REM schedule.bat — wrapper gọi tools\kora-scheduler\schedule.py (lịch Task Scheduler trên Windows).
REM Dùng: scripts\schedule.bat register --id daily --cron "0 8 * * 1-5" --scan jira:local --post confluence:KB
setlocal
set "DIR=%~dp0"
where py >nul 2>nul && (set "PY=py") || (set "PY=python")
"%PY%" "%DIR%..\tools\kora-scheduler\schedule.py" %*
endlocal
