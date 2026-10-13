@echo off
REM V-YTDownload - free YouTube to MP4/MP3 downloader (Windows 98 theme)
cd /d "%~dp0"
title V-YTDownload
if not exist "output\mp4" mkdir "output\mp4"
if not exist "output\mp3" mkdir "output\mp3"
python app.py
if errorlevel 1 (
  echo.
  echo ERROR: the program exited. Is Python installed? Check with "python --version".
  echo For dependencies: pip install -r requirements.txt
  pause
)
