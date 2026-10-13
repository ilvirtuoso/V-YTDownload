@echo off
REM V-YTDownload release build - produces dist\V-YTDownload\V-YTDownload.exe
REM Requires: pip install pyinstaller yt-dlp imageio-ffmpeg pillow
cd /d "%~dp0"
python -m pip install --user pyinstaller yt-dlp imageio-ffmpeg pillow
for /f "delims=" %%F in ('python -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())"') do set FFMPEG=%%F
echo Using ffmpeg: %FFMPEG%
python -m PyInstaller --noconfirm --clean --name V-YTDownload --windowed ^
  --icon assets\app.ico ^
  --add-data "assets\background.png;assets" ^
  --add-data "assets\app.ico;assets" ^
  --add-binary "%FFMPEG%;." ^
  --collect-all yt_dlp ^
  --collect-all curl_cffi ^
  app.py
echo.
echo Build finished. See dist\V-YTDownload\V-YTDownload.exe
pause
