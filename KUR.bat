@echo off
REM V-YTDownload first-time setup - installs dependencies
cd /d "%~dp0"
python -m pip install --user -r requirements.txt
echo.
echo Done. Now run BASLAT.bat to start V-YTDownload.
pause
