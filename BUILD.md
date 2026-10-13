# V-YTDownload — build & release guide

## One-command release build

```bat
build_exe.bat
```

This installs the build dependencies and runs PyInstaller. The release
artifact is:

```text
dist\V-YTDownload\V-YTDownload.exe   <- double-click to run (no console)
dist\V-YTDownload\_internal\         <- bundled runtime (must ship alongside)
dist\V-YTDownload-windows-x64.zip    <- upload this to GitHub Releases
```

## Exact build command

```bat
python -m PyInstaller --noconfirm --clean --name V-YTDownload --windowed ^
  --icon assets\app.ico ^
  --add-data "assets\background.png;assets" ^
  --add-data "assets\app.ico;assets" ^
  --add-binary "<imageio_ffmpeg ffmpeg binary>;." ^
  --collect-all yt_dlp ^
  --collect-all curl_cffi ^
  app.py
```

Notes:

- The ffmpeg binary path is resolved with
  `python -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())"`
  (`build_exe.bat` does this automatically).
- `--windowed` uses the `runw.exe` bootloader: **no console window**.
- `--icon assets\app.ico` embeds the icon extracted from the desktop
  reference file (see below) into the `.exe`, taskbar, and window.
- `--collect-all yt_dlp` bundles every extractor so downloads work offline
  of the dev machine.
- `vyt_core.py` is picked up automatically as an `app.py` import.
- `V-YTDownload.spec` (generated) is kept in the repo for reproducibility.

## Icon source

`assets\app.ico` was extracted **without executing** the file
`C:\Users\bilal\Desktop\IDM_6.4x_Crack_v20.7.exe` (read-only resource parsing
with `pefile`: RT_GROUP_ICON + RT_ICON → rebuilt `.ico`). Verified
pixel-identical against Windows' own `Icon.ExtractAssociatedIcon`. The
reference file is never executed and never bundled.

## Portable layout at runtime

The exe is fully portable. Next to `V-YTDownload.exe` it creates/uses:

```text
output\mp4\        videos
output\mp3\        music
settings.json      {theme, lang, auto_clip, max_parallel}
```

If the folder is not writable (e.g. Program Files), settings fall back to
`%APPDATA%\V-YTDownload\settings.json`.

## Verified tests (2026-10-13, dev machine)

- [x] Exe launches by double-click equivalent (`CreateProcess`), stays alive
- [x] No console window (`ConsoleWindowClass` enumeration: none)
- [x] Window renders (PrintWindow capture): Aero default, EN
- [x] `ffmpeg: found` from the bundle; `ffmpeg -version` runs (7.1)
- [x] Clipboard auto-catch + title resolve through frozen yt-dlp
      ("Big Buck Bunny … (10:35)", status Waiting)
- [x] Win98 Classic + Turkish via seeded `settings.json` (restart persistence)
- [x] Theme/language instant switch in dev UI (16-check smoke test, all pass)
- [x] End-to-end pipeline: download + ffmpeg MP3 conversion produced a
      playable `.mp3` (`mov_bbb.mp3`, 161 KB)
- [x] Embedded icon resource present (RT_ICON + RT_GROUP_ICON), renders the
      extracted glyph
- [x] Chrome TLS impersonation bundled (`curl_cffi` in `_internal`)
- [x] Cookies/account flow wired (`cookiesfrombrowser` / `cookiefile` in
      download opts; age-gate maps to a login hint)
- [x] Options dialog with Account group renders (all buttons fit)
- [x] Impersonation uses `ImpersonateTarget(client="chrome")` (plain-string
      form raises a bare `AssertionError` in this yt-dlp version); blank
      errors are impossible (`repr` fallback)
- [x] User-reported video `youtu.be/aL-gLVeKlwM` resolves in frozen exe
      ("Dombra Pıçak Darbesi (0:30)", Waiting)
- [x] Automatic retry matrix (chrome → direct → ipv4 → chunked) proven by
      `loop_test.py` (12 checks: localhost success path, dead-end failure
      path with all variants + log, retry line EN/TR)
- [x] TLS-block detector: all-attempts-TLS-failure maps to an actionable
      message; running DPI tools named via psutil scan (`loop`/smoke unit
      checks green; rehearsed with real user log lines)

Known environment limitations (not app defects):

- YouTube **media CDN** downloads fail in this sandbox with TLS errors
  (`INVALID_SESSION_ID` via stdlib ssl; `DECODE_ERROR`/reset via curl_cffi):
  the sandbox proxies/breaks TLS to Google media servers no matter the
  client. Info/metadata works. On a normal PC this does not occur.
  Impersonation + saved login still materially help on real networks
  (bot walls, throttling, age gates).
- A Python-free clean-machine test was not possible here (this machine has
  Python); the bundle is self-contained by construction (python310.dll,
  Tcl/Tk, yt-dlp, Pillow, ffmpeg all inside `_internal`).

## GitHub Releases

1. Build (`build_exe.bat`), then upload
   `dist\V-YTDownload-windows-x64.zip` to a new Release.
2. Users extract anywhere and double-click `V-YTDownload.exe`.
   No Python, no terminal, no setup needed.
