#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V-YTDownload - free YouTube downloader
Windows 98 / Windows Classic themed, MediaHuman-style interface.
One job: paste a link -> download to output/mp4 or output/mp3.

Usage:
    python app.py
Requirements:
    pip install -r requirements.txt  (yt-dlp, imageio-ffmpeg, pillow)
"""

import os
import re
import sys
import time
import queue
import shutil
import threading
import subprocess
import traceback
from dataclasses import dataclass, field

import tkinter as tk
from tkinter import messagebox

import vyt_core as core
from vyt_core import T

try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except Exception:
    HAS_PIL = False

# ----------------------------------------------------------------------------
# Theme-driven globals (refreshed by apply_theme()).
# Widgets read these at build time; theme switching = refresh + rebuild.
# ----------------------------------------------------------------------------
FACE = LIGHT = MIDLIGHT = DARK = DARKEST = NAVY = TITLE_GR2 = ""
SEL_BG = SEL_FG = BAR_BLUE = LIST_BG = GREEN_OK = ""
ROW_BG = PANEL_BG = ENTRY_BG = TEXT_FG = MUTED_FG = ACCENT = ""
BTN_HOVER = BTN_PRESS = ""
BAR_TOP = BAR_BOTTOM = BAR_BORDER = ""
FONT_UI = FONT_UI_B = FONT_TITLE = FONT_MONO = ("Tahoma", 8)
RELIEF_BTN = "raised"
HOVER_GLOW = False
CHUNKY_BAR = True
BANNER_MODE = "plain"
BANNER_FG = "#ffffff"
TITLE_C1 = "#000080"
TITLE_C2 = "#1084d0"


def apply_theme(name=None):
    """Push the active core theme into the module globals the UI reads."""
    global FACE, LIGHT, MIDLIGHT, DARK, DARKEST, NAVY, TITLE_GR2
    global SEL_BG, SEL_FG, BAR_BLUE, LIST_BG, GREEN_OK
    global ROW_BG, PANEL_BG, ENTRY_BG, TEXT_FG, MUTED_FG, ACCENT
    global BTN_HOVER, BTN_PRESS, BAR_TOP, BAR_BOTTOM, BAR_BORDER
    global FONT_UI, FONT_UI_B, FONT_TITLE, FONT_MONO
    global RELIEF_BTN, HOVER_GLOW, CHUNKY_BAR, BANNER_MODE, BANNER_FG
    global TITLE_C1, TITLE_C2
    if name:
        core.apply_theme(name)
    th = core.theme()
    FACE = th["bg"]
    PANEL_BG = th["panel"]
    ENTRY_BG = th["entry_bg"]
    LIST_BG = th["list_bg"]
    ROW_BG = th["row_bg"]
    LIGHT = "#ffffff"
    MIDLIGHT = "#dfdfdf" if core.theme_name() == "win98" else "#cfe2f4"
    DARK = "#808080" if core.theme_name() == "win98" else "#8aa5bd"
    DARKEST = "#0a0a0a"
    NAVY = th["accent"]
    TITLE_GR2 = th["title2"]
    SEL_BG = th["select_bg"]
    SEL_FG = th["select_fg"]
    BAR_BLUE = th["bar_bottom"]
    BAR_TOP = th["bar_top"]
    BAR_BOTTOM = th["bar_bottom"]
    BAR_BORDER = th["bar_border"]
    GREEN_OK = th["ok"]
    TEXT_FG = th["text"]
    MUTED_FG = th["muted"]
    ACCENT = th["accent"]
    BTN_HOVER = th["btn_hover"]
    BTN_PRESS = th["btn_press"]
    FONT_UI = th["font_ui"]
    FONT_UI_B = th["font_bold"]
    FONT_TITLE = th["font_title"]
    FONT_MONO = th["font_mono"]
    RELIEF_BTN = th["relief_btn"]
    HOVER_GLOW = th["hover_glow"]
    CHUNKY_BAR = th["chunky"]
    BANNER_MODE = th["banner_mode"]
    BANNER_FG = th["banner_fg"]
    # title gradient endpoints also follow the theme
    TITLE_C1 = th["title1"]
    TITLE_C2 = th["title2"]


APP_TITLE = "V-YTDownload"

# ----------------------------------------------------------------------------
# Dizin / ffmpeg cozumu
# ----------------------------------------------------------------------------
def base_dir():
    return core.program_dir()


BASE = base_dir()
OUT_MP4 = os.path.join(BASE, "output", "mp4")
OUT_MP3 = os.path.join(BASE, "output", "mp3")

for _d in (OUT_MP4, OUT_MP3):
    try:
        os.makedirs(_d, exist_ok=True)
    except Exception:
        pass


def background_path():
    for cand in (core.resource_path("assets", "background.png"),
                 os.path.join(BASE, "assets", "background.png"),
                 os.path.join(BASE, "background.png")):
        if cand and os.path.exists(cand):
            return cand
    return None


def icon_path():
    for cand in (core.resource_path("assets", "app.ico"),
                 os.path.join(BASE, "assets", "app.ico")):
        if cand and os.path.exists(cand):
            return cand
    return None


def find_ffmpeg():
    # 0) bundled next to / inside the packaged app (PyInstaller)
    cands = [core.resource_path("ffmpeg.exe"),
             core.resource_path("bin", "ffmpeg.exe"),
             os.path.join(BASE, "ffmpeg.exe"),
             os.path.join(BASE, "bin", "ffmpeg.exe")]
    import glob as _glob
    for _d in {core.resource_path(), BASE}:
        try:
            # versioned names, e.g. ffmpeg-win-x86_64-v7.1.exe
            cands += sorted(_glob.glob(os.path.join(_d, "ffmpeg*.exe")))
        except Exception:
            pass
    for cand in cands:
        if cand and os.path.exists(cand):
            return cand
    # 1) system ffmpeg
    w = shutil.which("ffmpeg")
    if w:
        return w
    # 2) imageio-ffmpeg bundled binary
    try:
        import imageio_ffmpeg
        p = imageio_ffmpeg.get_ffmpeg_exe()
        if p and os.path.exists(p):
            return p
    except Exception:
        pass
    return None


FFMPEG_EXE = find_ffmpeg()


def _has_curl_cffi():
    try:
        import curl_cffi  # noqa: F401
        return True
    except Exception:
        return False


HAS_CURL_CFFI = _has_curl_cffi()


def apply_net_opts(opts):
    """Harden downloads: Chrome TLS impersonation + saved login (cookies).

    - impersonate=chrome: real-Chrome TLS fingerprint, fewer resets/bot walls.
    - cookies: required for age-restricted videos ("sign in to confirm age").
    """
    if HAS_CURL_CFFI:
        try:
            # API path needs an ImpersonateTarget object, NOT a plain string
            # (a string raises a bare AssertionError deep inside yt-dlp).
            from yt_dlp.networking.impersonate import ImpersonateTarget
            opts.setdefault("impersonate", ImpersonateTarget(client="chrome"))
        except Exception:
            pass
    src = core.PREFS.get("cookies_source", "none")
    cf = core.PREFS.get("cookiefile", "")
    if src == "file" and cf and os.path.exists(cf):
        opts["cookiefile"] = cf
    elif src in core.COOKIE_BROWSERS:
        opts["cookiesfrombrowser"] = (src,)
    return opts


def count_youtube_cookies(jar):
    try:
        return sum(1 for c in jar if "youtube" in (getattr(c, "domain", "") or ""))
    except Exception:
        return 0


def verify_browser_cookies(browser):
    """Read a browser's cookie jar locally (no network). Returns (ok, yt_count, err)."""
    try:
        from yt_dlp.cookies import extract_cookies_from_browser
        jar = extract_cookies_from_browser(browser)
        return True, count_youtube_cookies(jar), ""
    except Exception as ex:
        return False, 0, str(ex)[:120]


def verify_cookiefile(path):
    """Parse a Netscape cookies.txt locally. Returns (ok, yt_count)."""
    try:
        from http.cookiejar import MozillaCookieJar
        jar = MozillaCookieJar(path)
        jar.load(ignore_discard=True, ignore_expires=True)
        return True, count_youtube_cookies(jar)
    except Exception:
        return False, 0

YOUTUBE_RE = re.compile(
    r"(https?://)?(www\.|m\.|music\.)?(youtube\.com/(watch|shorts|embed|live|playlist)|youtu\.be/)[^\s<>\"']+",
    re.IGNORECASE,
)


def extract_urls(text):
    if not text:
        return []
    return [m.group(0) for m in YOUTUBE_RE.finditer(text)]


def fmt_bytes(n):
    if not n:
        return "--"
    try:
        n = float(n)
    except Exception:
        return "--"
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {u}"
        n /= 1024
    return f"{n:.1f} TB"


def fmt_speed(bps):
    if not bps:
        return "--"
    return fmt_bytes(bps) + "/s"


def fmt_eta(s):
    if s is None:
        return "--"
    try:
        s = int(s)
    except Exception:
        return "--"
    m, sec = divmod(s, 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}:{m:02d}:{sec:02d}"
    return f"{m:02d}:{sec:02d}"


def safe_filename(name, maxlen=120):
    bad = '<>:"/\\|?*\x00\x01\x02\x03\x04\x05\x06\x07\x08\x0b\x0c\x0e\x0f'
    for ch in bad:
        name = name.replace(ch, "_")
    name = re.sub(r"\s+", " ", name).strip().strip(".")
    if len(name) > maxlen:
        name = name[:maxlen].rstrip()
    return name or "video"


# ----------------------------------------------------------------------------
# Win98 yardimcilari
# ----------------------------------------------------------------------------

def w98_raised(parent, **kw):
    aero = core.theme_name() == "aero"
    kw.setdefault("bg", FACE)
    kw.setdefault("relief", "flat" if aero else "raised")
    kw.setdefault("bd", 1 if aero else 2)
    f = tk.Frame(parent, **kw)
    return f


def w98_sunken(parent, **kw):
    aero = core.theme_name() == "aero"
    kw.setdefault("bg", FACE)
    kw.setdefault("relief", "flat" if aero else "sunken")
    kw.setdefault("bd", 1 if aero else 2)
    f = tk.Frame(parent, **kw)
    return f


def _hex_mix(c1, c2, t):
    c1 = c1.lstrip("#"); c2 = c2.lstrip("#")
    r = int(int(c1[0:2], 16) + (int(c2[0:2], 16) - int(c1[0:2], 16)) * t)
    g = int(int(c1[2:4], 16) + (int(c2[2:4], 16) - int(c1[2:4], 16)) * t)
    b = int(int(c1[4:6], 16) + (int(c2[4:6], 16) - int(c1[4:6], 16)) * t)
    return f"#{r:02x}{g:02x}{b:02x}"


def attach_tip(widget, text):
    """Lightweight themed tooltip (no extra dependency)."""
    tip = {"win": None, "after": None}

    def show(_e=None):
        hide()
        try:
            x = widget.winfo_rootx() + 12
            y = widget.winfo_rooty() + widget.winfo_height() + 4
            w = tk.Toplevel(widget)
            w.wm_overrideredirect(True)
            w.wm_geometry(f"+{x}+{y}")
            th = core.theme()
            bg = "#ffffff" if core.theme_name() == "aero" else "#ffffe1"
            bd = th["btn_border"] if core.theme_name() == "aero" else "#000000"
            lbl = tk.Label(w, text=text, bg=bg, fg=th["text"], font=FONT_UI,
                           relief="solid", bd=1, padx=6, pady=3)
            lbl.configure(highlightbackground=bd)
            lbl.pack()
            tip["win"] = w
        except Exception:
            pass

    def hide(_e=None):
        if tip["after"]:
            try:
                widget.after_cancel(tip["after"])
            except Exception:
                pass
            tip["after"] = None
        if tip["win"] is not None:
            try:
                tip["win"].destroy()
            except Exception:
                pass
            tip["win"] = None

    def schedule(_e=None):
        hide()
        try:
            tip["after"] = widget.after(600, show)
        except Exception:
            pass

    widget.bind("<Enter>", schedule, add="+")
    widget.bind("<Leave>", hide, add="+")
    widget.bind("<ButtonPress>", hide, add="+")


def w98_button(parent, text, command=None, width=None, state="normal", tip=None, **kw):
    kw.setdefault("bg", core.theme()["btn_bg"] if core.theme_name() == "aero" else FACE)
    kw.setdefault("fg", TEXT_FG)
    kw.setdefault("activebackground", BTN_HOVER)
    kw.setdefault("activeforeground", TEXT_FG)
    kw.setdefault("relief", RELIEF_BTN)
    kw.setdefault("bd", 1 if core.theme_name() == "aero" else 2)
    kw.setdefault("font", FONT_UI)
    kw.setdefault("cursor", "hand2" if state == "normal" else "arrow")
    if core.theme_name() == "aero":
        kw.setdefault("highlightthickness", 1)
        kw.setdefault("highlightbackground", core.theme()["btn_border"])
        kw.setdefault("highlightcolor", core.theme()["btn_border"])
        kw.setdefault("padx", 6)
        kw.setdefault("pady", 3)
    b = tk.Button(parent, text=text, command=command, width=width, state=state, **kw)
    if HOVER_GLOW and state == "normal":
        base = kw["bg"]

        def on_enter(_e, bb=b):
            try:
                if str(bb["state"]) == "normal":
                    bb.configure(bg=BTN_HOVER, relief="raised", bd=1)
            except Exception:
                pass

        def on_leave(_e, bb=b):
            try:
                bb.configure(bg=base, relief="flat", bd=1)
            except Exception:
                pass

        def on_press(_e, bb=b):
            try:
                bb.configure(bg=BTN_PRESS, relief="sunken", bd=1)
            except Exception:
                pass

        b.bind("<Enter>", on_enter, add="+")
        b.bind("<Leave>", on_leave, add="+")
        b.bind("<ButtonPress-1>", on_press, add="+")
        b.bind("<ButtonRelease-1>", on_enter, add="+")
    else:
        b.bind("<FocusIn>", lambda e: b.configure(relief="raised"))
    if tip:
        attach_tip(b, tip)
    return b


def w98_label(parent, text, bold=False, **kw):
    kw.setdefault("bg", FACE)
    kw.setdefault("fg", TEXT_FG)
    kw.setdefault("font", FONT_UI_B if bold else FONT_UI)
    return tk.Label(parent, text=text, **kw)


def w98_entry(parent, **kw):
    kw.setdefault("relief", core.theme()["relief_entry"])
    kw.setdefault("bd", 1 if core.theme_name() == "aero" else 2)
    kw.setdefault("bg", ENTRY_BG)
    kw.setdefault("fg", TEXT_FG)
    kw.setdefault("font", FONT_UI)
    kw.setdefault("insertbackground", TEXT_FG)
    if core.theme_name() == "aero":
        kw.setdefault("highlightthickness", 1)
        kw.setdefault("highlightbackground", core.theme()["btn_border"])
        kw.setdefault("highlightcolor", core.theme()["btn_border"])
    return tk.Entry(parent, **kw)


def _hex_to_rgb(h):
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def draw_title_gradient(canvas, w, active=True):
    canvas.delete("grad")
    steps = 64
    if active:
        r1, g1, b1 = _hex_to_rgb(TITLE_C1)
        r2, g2, b2 = _hex_to_rgb(TITLE_C2)
    else:
        r1, g1, b1 = 0x80, 0x80, 0x80
        r2, g2, b2 = 0xB5, 0xB5, 0xB5
    for i in range(steps):
        t = i / max(1, steps - 1)
        r = int(r1 + (r2 - r1) * t)
        g = int(g1 + (g2 - g1) * t)
        b = int(b1 + (b2 - b1) * t)
        color = f"#{r:02x}{g:02x}{b:02x}"
        x0 = int(w * i / steps)
        x1 = int(w * (i + 1) / steps) + 1
        canvas.create_rectangle(x0, 0, x1, 30, fill=color, outline=color, tags="grad")


class ChunkBar(tk.Canvas):
    """Themed progress bar: Win98 chunky blocks / Aero glossy gradient."""

    def __init__(self, parent, width=220, height=16, **kw):
        aero = core.theme_name() == "aero"
        super().__init__(parent, width=width, height=height,
                         bg="#ffffff", relief="flat" if aero else "sunken",
                         bd=1 if aero else 2,
                         highlightthickness=1 if aero else 0,
                         highlightbackground=BAR_BORDER if aero else "#ffffff",
                         **kw)
        self._bw = width
        self._bh = height
        self._frac = 0.0
        self._indet = False
        self._tick = 0
        self.bind("<Configure>", self._on_conf)
        self.after_idle(self._draw)

    def _on_conf(self, ev):
        self._bw = max(10, ev.width)
        self._draw()

    def set(self, frac, indet=False):
        try:
            frac = max(0.0, min(1.0, float(frac)))
        except Exception:
            frac = 0.0
        self._frac = frac
        self._indet = indet
        self._draw()

    def _draw(self):
        try:
            self.delete("b")
        except Exception:
            return
        try:
            w = self.winfo_width()
        except Exception:
            w = 0
        if not w or w <= 1:
            w = getattr(self, "_bw", 220)
        h = 18 if core.theme_name() == "aero" else 16
        x0, y0, x1, y1 = 2, 2, w - 2, h - 2
        if core.theme_name() == "aero":
            self._draw_aero(x0, y0, x1, y1)
            return
        if self._indet:
            # sliding block animation (advances on data events only)
            self._tick = (self._tick + 1) % 20
            bw = 34
            start = 2 + (self._tick * 9) % max(1, (w - bw - 4))
            self.create_rectangle(start, y0 + 1, start + bw, y1 - 1,
                                  fill=BAR_BLUE, outline=BAR_BLUE, tags="b")
            return
        nblocks = max(1, (w - 6) // 12)
        lit = int(round(self._frac * nblocks))
        for i in range(nblocks):
            bx0 = 3 + i * 12
            bx1 = bx0 + 10
            if bx1 > w - 3:
                break
            fill = BAR_BLUE if i < lit else "white"
            self.create_rectangle(bx0, y0 + 1, bx1, y1 - 1,
                                  fill=fill, outline=fill, tags="b")

    def _draw_aero(self, x0, y0, x1, y1):
        # track
        self.create_rectangle(x0, y0, x1, y1, fill="#ffffff",
                              outline=BAR_BORDER, tags="b")
        inner_w = max(0, x1 - x0 - 2)
        if self._indet:
            self._tick = (self._tick + 1) % 30
            bw = max(30, inner_w // 4)
            start = x0 + 1 + (self._tick * 11) % max(1, (inner_w - bw))
            segs = 10
            for i in range(segs):
                t = i / max(1, segs - 1)
                c = _hex_mix(BAR_TOP, BAR_BOTTOM, t)
                sx0 = start + bw * i / segs
                sx1 = start + bw * (i + 1) / segs
                self.create_rectangle(sx0, y0 + 1, sx1, y1 - 1, fill=c,
                                      outline=c, tags="b")
            self.create_rectangle(start, y0 + 1, start + bw, y0 + 4,
                                  fill="#ffffff", outline="", tags="b",
                                  stipple="gray25")
            return
        # glossy vertical gradient fill
        fw = int(round(inner_w * self._frac))
        steps = 12
        for j in range(steps):
            t = j / max(1, steps - 1)
            c = _hex_mix(BAR_TOP, BAR_BOTTOM, t)
            ry0 = y0 + 1 + (y1 - y0 - 2) * j / steps
            ry1 = y0 + 1 + (y1 - y0 - 2) * (j + 1) / steps
            self.create_rectangle(x0 + 1, ry0, x0 + 1 + fw, ry1, fill=c,
                                  outline=c, tags="b")
        if fw > 0:
            # glass highlight band
            self.create_rectangle(x0 + 1, y0 + 1, x0 + 1 + fw, y0 + 5,
                                  fill="#e8f4fe", outline="", tags="b",
                                  stipple="gray25")


# ----------------------------------------------------------------------------
# Veri modeli
# ----------------------------------------------------------------------------
@dataclass
class QueueItem:
    url: str
    fmt: str = "mp4"          # "mp4" | "mp3"
    quality: str = "720p"     # mp4: 360p/480p/720p/1080p/Best ; mp3: 128k/192k/320k
    title: str = "Fetching link..."
    duration: str = ""
    status: str = "Waiting"  # Waiting | Fetching info | Downloading | Converting | Completed | Error | Stopped
    progress: float = 0.0
    indet: bool = False
    size: str = "--"
    speed: str = "--"
    eta: str = "--"
    filename: str = ""
    error: str = ""
    retry_a: int = 0  # current attempt number (for the "Retrying" line)
    retry_t: int = 0  # total attempts
    retry_why: str = ""  # current attempt label, e.g. "ipv4"
    tls_fails: int = 0  # attempts that died inside the TLS handshake
    row: object = field(default=None, repr=False)


LOG_FILE = os.path.join(BASE, "output", "download.log")


def log_line(text):
    """Append a timestamped line to output/download.log (self-diagnostics)."""
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + text + "\n")
    except Exception:
        pass


TLS_MARKERS = ("invalid_session_id", "decode_error", "tls connect error",
               "ssl routines", "connection was reset", "recv failure",
               "failed to perform, curl: (35", "eof occurred",
               "unexpected eof", "tlsv1 alert", "certificate verify failed")


def is_tls_error(msg):
    try:
        ml = (msg or "").lower()
    except Exception:
        return False
    return any(m in ml for m in TLS_MARKERS)


# processes known to mangle TLS handshakes (DPI circumvention tools)
TRAFFIC_TOOLS = ("goodbyedpi", "zapret", "powertunnel", "byedpi",
                 "greenhub", "spoofdpi")
TOOL_DISPLAY = {"goodbyedpi": "GoodbyeDPI", "zapret": "Zapret",
                "powertunnel": "PowerTunnel", "byedpi": "ByeDPI",
                "greenhub": "GreenHub", "spoofdpi": "SpoofDPI"}


def detect_traffic_tools():
    """Names of running DPI-bypass tools, if any (best effort)."""
    found = []
    try:
        import psutil
        for p in psutil.process_iter(["name", "exe", "cmdline"]):
            try:
                blob = " ".join([
                    str(p.info.get("name") or ""),
                    str(p.info.get("exe") or ""),
                    " ".join(p.info.get("cmdline") or []),
                ]).lower()
            except Exception:
                continue
            for tool in TRAFFIC_TOOLS:
                if tool in blob and tool not in found:
                    found.append(tool)
    except Exception:
        pass
    return found


# ----------------------------------------------------------------------------
# yt-dlp mantigi (arayuzden bagimsiz)
# ----------------------------------------------------------------------------

def build_ydl_opts(item: QueueItem, ffmpeg_exe, hooks):
    if item.fmt == "mp3":
        outdir = OUT_MP3
        bitrate = {"128k": "128", "192k": "192", "320k": "320"}.get(item.quality, "192")
        opts = {
            "format": "bestaudio/best",
            "outtmpl": os.path.join(outdir, "%(title)s.%(ext)s"),
            "restrictfilenames": False,
            "windowsfilenames": True,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "progress_hooks": hooks,
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": bitrate,
            }],
            "postprocessor_hooks": hooks,
            "prefer_ffmpeg": True,
        }
    else:
        outdir = OUT_MP4
        cap = {"360p": 360, "480p": 480, "720p": 720, "1080p": 1080}.get(item.quality, 720)
        if item.quality in ("Best", "En iyi"):
            fmt = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best[ext=mp4]/best"
        else:
            fmt = (f"bestvideo[ext=mp4][height<={cap}]+bestaudio[ext=m4a]/"
                   f"bestvideo[height<={cap}]+bestaudio/"
                   f"best[ext=mp4][height<={cap}]/best[height<={cap}]/best")
        opts = {
            "format": fmt,
            "outtmpl": os.path.join(outdir, "%(title)s.%(ext)s"),
            "restrictfilenames": False,
            "windowsfilenames": True,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "merge_output_format": "mp4",
            "progress_hooks": hooks,
            "postprocessor_hooks": hooks,
            "prefer_ffmpeg": True,
        }
    if ffmpeg_exe and os.path.exists(ffmpeg_exe):
        # yt-dlp accepts the executable file itself (versioned names OK)
        opts["ffmpeg_location"] = ffmpeg_exe
    # Node kuruluysa JS challenge'lar icin kullan (format kaybi olmasin)
    if shutil.which("node"):
        opts["js_runtimes"] = {"node": {}}
    apply_net_opts(opts)
    return opts


def fetch_info(url, ffmpeg_exe):
    """Basligi coz (hizli). Playlist ise ilk N videoyu genislet."""
    import yt_dlp
    base = {"quiet": True, "no_warnings": True, "noplaylist": False,
            "extract_flat": "in_playlist", "socket_timeout": 30}
    if shutil.which("node"):
        base["js_runtimes"] = {"node": {}}
    if ffmpeg_exe and os.path.exists(ffmpeg_exe):
        base["ffmpeg_location"] = ffmpeg_exe
    apply_net_opts(base)
    with yt_dlp.YoutubeDL(base) as ydl:
        info = ydl.extract_info(url, download=False)
    # playlist mi?
    if info and info.get("_type") == "playlist":
        entries = [e for e in (info.get("entries") or []) if e][:25]
        out = []
        for e in entries:
            vid = e.get("url") or e.get("id")
            if not vid:
                continue
            full = vid if str(vid).startswith("http") else f"https://www.youtube.com/watch?v={vid}"
            out.append({"url": full, "title": e.get("title") or full,
                        "duration": e.get("duration")})
        return {"playlist": True, "playlist_title": info.get("title") or "Playlist",
                "entries": out}
    title = (info or {}).get("title") or url
    return {"playlist": False, "title": title, "duration": (info or {}).get("duration")}


def fmt_duration(sec):
    if not sec:
        return ""
    try:
        sec = int(sec)
    except Exception:
        return ""
    m, s = divmod(sec, 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


# ----------------------------------------------------------------------------
# Liste satiri (her indirme icin klasik gorunum)
# ----------------------------------------------------------------------------
class ItemRow(tk.Frame):
    def __init__(self, parent, item: QueueItem, on_open=None, on_remove=None):
        super().__init__(parent, bg=ROW_BG, bd=1, relief="solid",
                         highlightbackground=DARK, highlightthickness=0)
        self.item = item
        self.on_open = on_open
        self.on_remove = on_remove

        # ikon (klasik metin ikon)
        self.icon = tk.Label(self, text="[MP4]", width=7, bg=ROW_BG,
                             fg=NAVY, font=FONT_MONO)
        self.icon.pack(side="left", padx=(6, 2), pady=6)

        mid = tk.Frame(self, bg=ROW_BG)
        mid.pack(side="left", fill="both", expand=True, padx=2)

        top = tk.Frame(mid, bg=ROW_BG)
        top.pack(fill="x")
        self.title_lbl = tk.Label(top, text=item.title, bg=ROW_BG, fg=TEXT_FG,
                                  font=FONT_UI_B, anchor="w")
        self.title_lbl.pack(side="left", fill="x", expand=True)
        self.size_lbl = tk.Label(top, text="--", bg=ROW_BG, fg=TEXT_FG, font=FONT_MONO,
                                 width=12, anchor="e")
        self.size_lbl.pack(side="right")

        bot = tk.Frame(mid, bg=ROW_BG)
        bot.pack(fill="x", pady=(2, 0))
        self.bar = ChunkBar(bot, width=200, height=16)
        self.bar.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.status_lbl = tk.Label(bot, text=T("st_waiting"), bg=ROW_BG, fg=MUTED_FG,
                                   font=FONT_UI, width=30, anchor="w")
        self.status_lbl.pack(side="left")

        right = tk.Frame(self, bg=ROW_BG)
        right.pack(side="right", padx=6)
        self.open_btn = w98_button(right, text=T("row_open"),
                                   command=self._open, state="disabled", width=6)
        self.open_btn.pack(pady=(2, 1))
        self.del_btn = w98_button(right, text="X",
                                  command=self._remove, width=6)
        self.del_btn.pack(pady=(1, 2))

        for w in (self, mid, top, bot, self.title_lbl, self.status_lbl,
                  self.size_lbl, self.icon):
            w.bind("<Double-Button-1>", lambda e: self._open())
        self.refresh()

    def _open(self):
        if self.on_open:
            self.on_open(self.item)

    def _remove(self):
        if self.on_remove:
            self.on_remove(self.item)

    def refresh(self):
        it = self.item
        tag = "[MP3]" if it.fmt == "mp3" else "[MP4]"
        try:
            self.icon.configure(text=tag)
        except Exception:
            pass
        t = it.title
        if it.duration:
            t = f"{t}  ({it.duration})"
        if len(t) > 90:
            t = t[:89] + "\u2026"
        self.title_lbl.configure(text=t)
        # status line (localized display of the internal status code)
        if it.status == "Downloading":
            det = T("st_downloading", pct=int(it.progress * 100),
                    speed=it.speed, eta=it.eta)
        elif it.status == "Converting":
            det = T("st_converting")
        elif it.status == "Completed":
            det = T("st_done", file=it.filename or "")
        elif it.status == "Error":
            det = T("st_error", err=it.error[:80]) if it.error else T("st_error", err="")
        elif it.status == "Stopped":
            det = T("st_stopped")
        elif it.status == "Retrying":
            det = T("st_retrying", a=it.retry_a or "?", t=it.retry_t or "?",
                    why=it.retry_why)
        elif it.status == "Fetching info":
            det = T("st_fetching")
        else:
            det = T("st_waiting")
        self.status_lbl.configure(text=det,
                                  fg=GREEN_OK if it.status == "Completed"
                                  else (core.theme()["err"] if it.status == "Error" else MUTED_FG))
        self.size_lbl.configure(text=it.size)
        self.bar.set(it.progress, indet=it.indet)
        try:
            self.open_btn.configure(state="normal" if it.status == "Completed" else "disabled")
        except Exception:
            pass


# ----------------------------------------------------------------------------
# Dialoglar (Win98 tarzi Toplevel)
# ----------------------------------------------------------------------------
class W98Dialog(tk.Toplevel):
    def __init__(self, master, title, w=420, h=180):
        super().__init__(master)
        self.withdraw()
        self.configure(bg=FACE)
        self.title(title)
        self.resizable(False, False)
        self.transient(master)
        # ortala
        self.update_idletasks()
        try:
            mx = master.winfo_rootx() + master.winfo_width() // 2
            my = master.winfo_rooty() + master.winfo_height() // 2
        except Exception:
            mx, my = 400, 300
        self.geometry(f"{w}x{h}+{max(0, mx-w//2)}+{max(0, my-h//2)}")
        # sahte baslik cubugu (icerde ince lacivert serit)
        bar = tk.Canvas(self, height=20, bg=NAVY, highlightthickness=0)
        bar.pack(fill="x", padx=2, pady=2)
        bar.create_rectangle(0, 0, 4000, 20, fill=NAVY, outline=NAVY)
        bar.create_text(8, 10, text=" " + title, anchor="w", fill="white", font=FONT_TITLE)
        self.body = tk.Frame(self, bg=FACE)
        self.body.pack(fill="both", expand=True, padx=10, pady=6)
        self.grab_set()
        self.deiconify()
        self.focus_force()


class AddDialog(W98Dialog):
    def __init__(self, master, initial="", fmt="mp4", quality="720p"):
        super().__init__(master, T("add_title"), 480, 235)
        self.result = None
        w98_label(self.body, text=T("add_prompt")).pack(anchor="w")
        self.url_entry = w98_entry(self.body)
        self.url_entry.pack(fill="x", pady=(4, 8))
        self.url_entry.insert(0, initial or "")
        self.url_entry.focus()
        self.url_entry.select_range(0, "end")

        fr = tk.Frame(self.body, bg=FACE)
        fr.pack(fill="x")
        w98_label(fr, text=T("fmt_label")).pack(side="left")
        self.fmt_var = tk.StringVar(value=fmt)
        for val, key in (("mp4", "fmt_mp4"), ("mp3", "fmt_mp3")):
            tk.Radiobutton(fr, text=T(key), variable=self.fmt_var, value=val,
                           bg=FACE, activebackground=FACE, font=FONT_UI,
                           fg=TEXT_FG, selectcolor=ENTRY_BG).pack(side="left", padx=6)

        fr2 = tk.Frame(self.body, bg=FACE)
        fr2.pack(fill="x", pady=(6, 0))
        w98_label(fr2, text=T("fmt_quality")).pack(side="left")
        self.q_var = tk.StringVar(value=quality)
        self.q_combo = tk.OptionMenu(fr2, self.q_var, "360p", "480p", "720p", "1080p", T("q_best"),
                                     "128k", "192k", "320k")
        self.q_combo.configure(bg=ENTRY_BG, fg=TEXT_FG, font=FONT_UI,
                               relief=core.theme()["relief_entry"], bd=2,
                               highlightthickness=0, width=10)
        self.q_combo.pack(side="left", padx=6)
        w98_label(fr2, text=T("add_quality_note"),
                  ).pack(side="left", padx=4)

        btns = tk.Frame(self.body, bg=FACE)
        btns.pack(fill="x", pady=(12, 0))
        tk.Frame(btns, bg=FACE).pack(side="left", expand=True, fill="x")
        w98_button(btns, text=T("dlg_ok"), command=self._ok, width=10).pack(side="left", padx=4)
        w98_button(btns, text=T("dlg_cancel"), command=self.destroy, width=10).pack(side="left", padx=4)
        self.bind("<Return>", lambda e: self._ok())
        self.bind("<Escape>", lambda e: self.destroy())

    def _ok(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning(T("dlg_warning"), T("add_empty"), parent=self)
            return
        if not extract_urls(url) and "http" not in url:
            messagebox.showwarning(T("dlg_warning"), T("add_notube"),
                                   parent=self)
        q = self.q_var.get()
        f = self.fmt_var.get()
        # auto-fix consistency
        if f == "mp3" and q.endswith("p") or q in ("Best", "En iyi"):
            if f == "mp3":
                q = "192k"
        if f == "mp4" and q.endswith("k"):
            q = "720p"
        self.result = (url, f, q)
        self.destroy()


class SettingsDialog(W98Dialog):
    def __init__(self, master, mp4dir, mp3dir, auto_clip, max_parallel):
        super().__init__(master, T("opt_title"), 500, 520)
        self.result = None
        groove = "groove" if core.theme_name() == "win98" else "flat"
        g = tk.Frame(self.body, bg=FACE, relief=groove, bd=2)
        g.pack(fill="x", pady=2)
        w98_label(g, text=T("opt_folders"), bold=True).pack(anchor="w", padx=6, pady=(4, 0))
        for key, val in (("opt_mp4", mp4dir), ("opt_mp3", mp3dir)):
            r = tk.Frame(g, bg=FACE)
            r.pack(fill="x", padx=8, pady=2)
            w98_label(r, text=T(key), bold=True).pack(side="left")
            w98_label(r, text=val,).pack(side="left", padx=6)
        r = tk.Frame(g, bg=FACE)
        r.pack(fill="x", padx=8, pady=(2, 6))
        w98_label(r, text=T("opt_folders_note")).pack(anchor="w")

        ga = tk.Frame(self.body, bg=FACE, relief=groove, bd=2)
        ga.pack(fill="x", pady=6)
        w98_label(ga, text=T("opt_appearance"), bold=True).pack(anchor="w", padx=6, pady=(4, 0))
        r3 = tk.Frame(ga, bg=FACE)
        r3.pack(fill="x", padx=8, pady=2)
        w98_label(r3, text=T("opt_theme")).pack(side="left")
        self.th_var = tk.StringVar(value=core.theme_name())
        th_om = tk.OptionMenu(r3, self.th_var, *core.THEME_ORDER)
        th_om.configure(bg=ENTRY_BG, fg=TEXT_FG, font=FONT_UI,
                        relief=core.theme()["relief_entry"], bd=2,
                        highlightthickness=0, width=18)
        th_om.pack(side="left", padx=6)
        r4 = tk.Frame(ga, bg=FACE)
        r4.pack(fill="x", padx=8, pady=(0, 6))
        w98_label(r4, text=T("opt_lang")).pack(side="left")
        self.lg_var = tk.StringVar(value=core.lang())
        lg_om = tk.OptionMenu(r4, self.lg_var, *core.LANGS)
        lg_om.configure(bg=ENTRY_BG, fg=TEXT_FG, font=FONT_UI,
                        relief=core.theme()["relief_entry"], bd=2,
                        highlightthickness=0, width=18)
        lg_om.pack(side="left", padx=6)

        gc = tk.Frame(self.body, bg=FACE, relief=groove, bd=2)
        gc.pack(fill="x", pady=6)
        w98_label(gc, text=T("opt_account"), bold=True).pack(anchor="w", padx=6, pady=(4, 0))
        w98_label(gc, text=T("opt_account_note")).pack(anchor="w", padx=8)
        self.acc_status = w98_label(gc, text="", bold=True)
        self.acc_status.pack(anchor="w", padx=8, pady=(2, 4))
        br = tk.Frame(gc, bg=FACE)
        br.pack(fill="x", padx=8, pady=(0, 6))
        for b in core.COOKIE_BROWSERS:
            w98_button(br, text=b.capitalize(), width=8,
                       command=lambda bb=b: self._use_browser(bb)).pack(side="left", padx=2)
        w98_button(br, text=T("acc_file"), width=10,
                   command=self._use_file).pack(side="left", padx=2)
        w98_button(br, text=T("acc_clear"), width=8,
                   command=self._use_none).pack(side="left", padx=2)
        self._refresh_acc_status()

        g2 = tk.Frame(self.body, bg=FACE, relief=groove, bd=2)
        g2.pack(fill="x", pady=6)
        self.auto_var = tk.BooleanVar(value=auto_clip)
        tk.Checkbutton(g2, text=T("opt_auto"),
                       variable=self.auto_var, bg=FACE, activebackground=FACE,
                       fg=TEXT_FG, font=FONT_UI, selectcolor=ENTRY_BG).pack(anchor="w", padx=8, pady=4)
        r2 = tk.Frame(g2, bg=FACE)
        r2.pack(fill="x", padx=8, pady=(0, 6))
        w98_label(r2, text=T("opt_parallel")).pack(side="left")
        self.par_var = tk.StringVar(value=str(max_parallel))
        om = tk.OptionMenu(r2, self.par_var, "1", "2", "3")
        om.configure(bg=ENTRY_BG, fg=TEXT_FG, font=FONT_UI,
                     relief=core.theme()["relief_entry"], bd=2,
                     highlightthickness=0, width=4)
        om.pack(side="left", padx=6)

        btns = tk.Frame(self.body, bg=FACE)
        btns.pack(fill="x", pady=(4, 0))
        tk.Frame(btns, bg=FACE).pack(side="left", expand=True, fill="x")
        w98_button(btns, text=T("dlg_ok"), command=self._ok, width=10).pack(side="left", padx=4)
        w98_button(btns, text=T("dlg_cancel"), command=self.destroy, width=10).pack(side="left", padx=4)

    def _refresh_acc_status(self):
        src = core.PREFS.get("cookies_source", "none")
        if src in core.COOKIE_BROWSERS:
            ok, n, _e = verify_browser_cookies(src)
            if ok:
                self.acc_status.configure(
                    text=T("acc_status_browser", b=src.capitalize(), n=n))
            else:
                self.acc_status.configure(text=T("acc_status_none"))
        elif src == "file" and core.PREFS.get("cookiefile"):
            ok, n = verify_cookiefile(core.PREFS["cookiefile"])
            self.acc_status.configure(
                text=T("acc_status_file", n=n) if ok else T("acc_status_none"))
        else:
            self.acc_status.configure(text=T("acc_status_none"))

    def _use_browser(self, browser):
        ok, n, err = verify_browser_cookies(browser)
        B = browser.capitalize()
        if ok and n > 0:
            core.PREFS["cookies_source"] = browser
            core.PREFS["cookiefile"] = ""
            core.save_prefs(core.program_dir())
            messagebox.showinfo(T("opt_title"), T("msg_cookies_ok", B=B, n=n),
                                parent=self)
        elif ok:
            messagebox.showwarning(T("dlg_warning"),
                                   T("msg_cookies_nologin", B=B), parent=self)
        else:
            messagebox.showwarning(T("dlg_warning"),
                                   T("msg_cookies_fail", B=B, e=err), parent=self)
        self._refresh_acc_status()

    def _use_file(self):
        from tkinter import filedialog
        p = filedialog.askopenfilename(parent=self, title=T("acc_file_title"),
                                       filetypes=[("cookies.txt", "*.txt"),
                                                  ("All files", "*.*")])
        if not p:
            return
        ok, n = verify_cookiefile(p)
        if ok and n > 0:
            core.PREFS["cookies_source"] = "file"
            core.PREFS["cookiefile"] = p
            core.save_prefs(core.program_dir())
            messagebox.showinfo(T("opt_title"), T("msg_cookiefile_ok", n=n),
                                parent=self)
        else:
            messagebox.showwarning(T("dlg_warning"), T("msg_cookiefile_bad"),
                                   parent=self)
        self._refresh_acc_status()

    def _use_none(self):
        core.PREFS["cookies_source"] = "none"
        core.PREFS["cookiefile"] = ""
        core.save_prefs(core.program_dir())
        messagebox.showinfo(T("opt_title"), T("msg_logged_out"), parent=self)
        self._refresh_acc_status()

    def _ok(self):
        try:
            p = max(1, min(3, int(self.par_var.get())))
        except Exception:
            p = 2
        self.result = (self.auto_var.get(), p, self.th_var.get(), self.lg_var.get())
        self.destroy()


class ThemesDialog(W98Dialog):
    """Dedicated Themes tab: Vista Aero vs Win98 Classic + language."""

    def __init__(self, master):
        super().__init__(master, T("th_title"), 500, 330)
        self.result = None
        w98_label(self.body, text=T("th_intro")).pack(anchor="w", pady=(0, 8))
        self.th_var = tk.StringVar(value=core.theme_name())
        groove = "groove" if core.theme_name() == "win98" else "flat"
        for name, tkey, dkey in (("aero", "th_aero", "th_aero_d"),
                                 ("win98", "th_win98", "th_win98_d")):
            card = tk.Frame(self.body, bg=FACE, relief=groove, bd=2)
            card.pack(fill="x", pady=3)
            rb = tk.Radiobutton(card, variable=self.th_var, value=name,
                                bg=FACE, activebackground=FACE, fg=TEXT_FG,
                                font=FONT_UI, selectcolor=ENTRY_BG)
            rb.pack(side="left", padx=6, pady=8)
            txt = tk.Frame(card, bg=FACE)
            txt.pack(side="left", fill="x", expand=True, pady=6)
            w98_label(txt, text=T(tkey), bold=True).pack(anchor="w")
            w98_label(txt, text=T(dkey)).pack(anchor="w")
            for w in (card, txt):
                w.bind("<Button-1>", lambda e, n=name: self.th_var.set(n))

        lr = tk.Frame(self.body, bg=FACE)
        lr.pack(fill="x", pady=(10, 0))
        w98_label(lr, text=T("th_lang"), bold=True).pack(side="left")
        self.lg_var = tk.StringVar(value=core.lang())
        for code, key in (("en", "lang_en"), ("tr", "lang_tr")):
            tk.Radiobutton(lr, text=T(key), variable=self.lg_var, value=code,
                           bg=FACE, activebackground=FACE, fg=TEXT_FG,
                           font=FONT_UI, selectcolor=ENTRY_BG).pack(side="left", padx=8)

        btns = tk.Frame(self.body, bg=FACE)
        btns.pack(fill="x", pady=(14, 0))
        tk.Frame(btns, bg=FACE).pack(side="left", expand=True, fill="x")
        w98_button(btns, text=T("dlg_ok"), command=self._ok, width=10).pack(side="left", padx=4)
        w98_button(btns, text=T("dlg_cancel"), command=self.destroy, width=10).pack(side="left", padx=4)
        self.bind("<Return>", lambda e: self._ok())
        self.bind("<Escape>", lambda e: self.destroy())

    def _ok(self):
        self.result = (self.th_var.get(), self.lg_var.get())
        self.destroy()


# ----------------------------------------------------------------------------
# Ana uygulama
# ----------------------------------------------------------------------------
class App:
    def __init__(self, root):
        self.root = root
        self.items: list[QueueItem] = []
        self.rows: dict[int, ItemRow] = {}
        self.lock = threading.Lock()
        self.ui_queue: queue.Queue = queue.Queue()
        self.stop_flags: dict[int, bool] = {}
        self.downloading = 0
        self.auto_clip = core.PREFS.get("auto_clip", True)
        self.max_parallel = core.PREFS.get("max_parallel", 2)
        self.last_clip = ""
        self.default_fmt = tk.StringVar(value="mp4")
        self.default_q_mp4 = tk.StringVar(value="720p")
        self.default_q_mp3 = tk.StringVar(value="192k")

        self._build_fake_chrome()
        self.rebuild_ui()

        # global shortcuts: bound once (rebuild_ui must not re-bind)
        self.root.bind_all("<Control-v>", lambda e: self.cmd_paste())
        self.root.bind_all("<Control-V>", lambda e: self.cmd_paste())
        self.root.bind_all("<MouseWheel>", self._wheel)

        self.root.after(100, self._pump_ui)
        self.root.after(1000, self._clip_watch)
        self._set_status(T("sb_ready_hint"))

    def rebuild_ui(self):
        """Destroy and recreate the content area (theme/language switch)."""
        for child in self.content.winfo_children():
            child.destroy()
        self.rows = {}
        try:
            self.outer.configure(bg=FACE)
            self.content.configure(bg=FACE)
            self.root.configure(bg=FACE)
        except Exception:
            pass
        self._build_banner()
        self._build_toolbar()
        self._build_formatbar()
        self._build_list()
        self._build_statusbar()
        for idx, _it in enumerate(self.items):
            self._ui_add_row(idx)
        self._draw_titlebar()
        self._sync_counts()

    def set_theme(self, name):
        if name not in core.THEMES:
            return
        apply_theme(name)
        core.save_prefs(BASE)
        self.rebuild_ui()

    def set_language(self, code):
        core.set_language(code)
        core.save_prefs(BASE)
        self.rebuild_ui()

    def cmd_themes(self):
        d = ThemesDialog(self.root)
        self.root.wait_window(d)
        if d.result:
            th, lg = d.result
            changed = False
            if th != core.theme_name():
                apply_theme(th)
                changed = True
            if lg != core.lang():
                core.set_language(lg)
                changed = True
            core.save_prefs(BASE)
            if changed:
                self.rebuild_ui()
            else:
                self._set_status(T("msg_settings_saved"))

    # -- sahte Win98 pencere cercevesi -------------------------------------
    # NOTE: overrideredirect removes the taskbar button, so we restore it
    # via WS_EX_APPWINDOW (see _enable_taskbar_icon). Custom title bar kept.
    def _build_fake_chrome(self):
        r = self.root
        r.overrideredirect(True)
        r.configure(bg=FACE)
        try:
            r.title(APP_TITLE)
        except Exception:
            pass
        W, H = 760, 540
        sx = (r.winfo_screenwidth() - W) // 2
        sy = (r.winfo_screenheight() - H) // 2 - 20
        r.geometry(f"{W}x{H}+{sx}+{sy}")
        r.minsize(640, 420)
        r.update_idletasks()
        self._enable_taskbar_icon()

        # dis cerceve: yuksek kabartma
        aero = core.theme_name() == "aero"
        self.outer = tk.Frame(r, bg=FACE,
                              relief="flat" if aero else "raised",
                              bd=1 if aero else 3)
        self.outer.pack(fill="both", expand=True, padx=0, pady=0)

        # baslik cubugu
        self.titlebar = tk.Canvas(self.outer, height=24 if aero else 22,
                                  bg=TITLE_C1,
                                  highlightthickness=0)
        self.titlebar.pack(fill="x", padx=2, pady=(2, 0))
        self.titlebar.bind("<Button-1>", self._drag_start)
        self.titlebar.bind("<B1-Motion>", self._drag_move)
        self.titlebar.bind("<Double-Button-1>", self._toggle_max)

        self._draw_titlebar()
        self.titlebar.bind("<Configure>", lambda e: self._draw_titlebar())
        # redraw the caption when (re)mapped, e.g. restore from taskbar
        self.root.bind("<Map>", lambda e: self.root.after(50, self._draw_titlebar))

        # icerik alani
        self.content = tk.Frame(self.outer, bg=FACE)
        self.content.pack(fill="both", expand=True, padx=3, pady=(2, 2))

        # alt tutamac (yeniden boyutlandirma)
        grip = tk.Frame(self.outer, bg=FACE, cursor="sizing")
        grip.place(relx=1.0, rely=1.0, anchor="se", width=18, height=18)
        gl = tk.Label(grip, text="\u25e2", bg=FACE, fg=DARK, font=("Tahoma", 10))
        gl.pack()
        grip.bind("<Button-1>", self._rs_start)
        grip.bind("<B1-Motion>", self._rs_move)
        gl.bind("<Button-1>", self._rs_start)
        gl.bind("<B1-Motion>", self._rs_move)

        r.bind("<FocusIn>", lambda e: self._draw_titlebar(active=True))
        r.bind("<FocusOut>", lambda e: self._draw_titlebar(active=False))

    def _enable_taskbar_icon(self):
        """Force a taskbar button (+ Alt+Tab entry) for the frameless window.

        overrideredirect windows get WS_EX_TOOLWINDOW (no taskbar). Flipping
        to WS_EX_APPWINDOW brings the button back while the custom chrome
        stays. Returns True when the style bits stuck.
        """
        try:
            import ctypes
            user32 = ctypes.windll.user32
            hwnd = user32.GetParent(self.root.winfo_id())
            if not hwnd:
                return False
            self._hwnd = hwnd
            GWL_EXSTYLE = -20
            WS_EX_APPWINDOW = 0x00040000
            WS_EX_TOOLWINDOW = 0x00000080
            style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE,
                                  (style & ~WS_EX_TOOLWINDOW) | WS_EX_APPWINDOW)
            # taskbar refreshes the button list on hide/show
            self.root.withdraw()
            self.root.after(50, self.root.deiconify)
            back = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            return bool((back & WS_EX_APPWINDOW) and not (back & WS_EX_TOOLWINDOW))
        except Exception:
            return False

    def _taskbar_icon_ok(self):
        """Read back the extended style bits (for self-tests)."""
        try:
            import ctypes
            user32 = ctypes.windll.user32
            hwnd = getattr(self, "_hwnd", None) or user32.GetParent(self.root.winfo_id())
            style = user32.GetWindowLongW(hwnd, -20)
            return {"appwindow": bool(style & 0x00040000),
                    "toolwindow": bool(style & 0x00000080)}
        except Exception:
            return {}

    def _draw_titlebar(self, active=True):
        c = self.titlebar
        try:
            w = c.winfo_width() or 740
        except Exception:
            w = 740
        draw_title_gradient(c, w, active=active)
        c.delete("ui")
        # minik ikon (klasik pencere ikonu taklidi)
        c.create_rectangle(4, 4, 18, 18, fill=FACE, outline="white", tags="ui")
        c.create_rectangle(6, 6, 16, 9, fill=TITLE_C1, outline=TITLE_C1, tags="ui")
        c.create_text(24, 11, text=APP_TITLE, anchor="w", fill="white",
                      font=FONT_TITLE, tags="ui")
        # sag dugmeler: _ | [] | X
        for i, (txt, cmd) in enumerate([
            ("_", self._minimize), ("\u25a1", self._toggle_max), ("X", self._close),
        ]):
            # sagdan sola 3 dugme
            idx = 2 - i  # X en sagda
            x0 = w - 4 - (idx + 1) * 20
            tag = f"btn{i}"
            c.create_rectangle(x0, 3, x0 + 18, 19, fill=FACE, outline=LIGHT,
                               tags=("ui", tag))
            c.create_rectangle(x0, 3, x0 + 18, 19, fill="", outline=DARK,
                               tags=("ui", tag))
            c.create_text(x0 + 9, 11, text=txt, font=FONT_UI_B,
                          tags=("ui", tag))
            c.tag_bind(tag, "<Button-1>", lambda e, cm=cmd: (cm(), "break"))

    def _drag_start(self, ev):
        # dugme alaninda suruklemeyi baslatma
        if ev.x > self.titlebar.winfo_width() - 70:
            return
        self._dx, self._dy = ev.x_root, ev.y_root
        self._gx, self._gy = self.root.winfo_x(), self.root.winfo_y()

    def _drag_move(self, ev):
        try:
            nx = self._gx + (ev.x_root - self._dx)
            ny = self._gy + (ev.y_root - self._dy)
            self.root.geometry(f"+{nx}+{ny}")
        except Exception:
            pass

    def _rs_start(self, ev):
        self._rx, self._ry = ev.x_root, ev.y_root
        self._rw, self._rh = self.root.winfo_width(), self.root.winfo_height()

    def _rs_move(self, ev):
        try:
            nw = max(640, self._rw + (ev.x_root - self._rx))
            nh = max(420, self._rh + (ev.y_root - self._ry))
            x, y = self.root.winfo_x(), self.root.winfo_y()
            self.root.geometry(f"{nw}x{nh}+{x}+{y}")
            self._draw_titlebar()
        except Exception:
            pass

    def _minimize(self):
        # With WS_EX_APPWINDOW set, plain iconify() drops to the taskbar
        # and the taskbar button restores the window. No chrome toggling.
        try:
            self.root.iconify()
            return
        except Exception:
            pass
        try:
            self.root.overrideredirect(False)
            self.root.iconify()
        except Exception:
            return

        def _back():
            try:
                self.root.deiconify()
                self.root.overrideredirect(True)
                self.root.focus_force()
                self._draw_titlebar()
            except Exception:
                pass
        self.root.after(300, _back)

    def _toggle_max(self):
        try:
            if getattr(self, "_maxed", False):
                self.root.geometry(self._prev_geo)
                self._maxed = False
            else:
                self._prev_geo = self.root.geometry()
                sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
                self.root.geometry(f"{sw}x{sh-30}+0+0")
                self._maxed = True
            self._draw_titlebar()
        except Exception:
            pass

    def _close(self):
        if self.downloading:
            if not messagebox.askyesno(T("exit_title"),
                                       T("exit_body", n=self.downloading)):
                return
        self.root.destroy()

    # -- banner (space artwork in Aero, plain strip in Win98) ------------------
    def _build_banner(self):
        if BANNER_MODE != "image":
            return
        wrap = w98_sunken(self.content)
        wrap.pack(fill="x", padx=2, pady=(2, 0))
        self.banner_h = 96
        self._banner_w = 0
        self._banner_img = None
        self._bg_src = background_path()
        self.banner_lbl = tk.Label(wrap, bg=NAVY, fg="white", font=FONT_TITLE,
                                   text="V-YTDownload", anchor="center",
                                   compound="center")
        self.banner_lbl.pack(fill="x")
        self.banner_lbl.bind("<Configure>", lambda e: self._paint_banner())
        self._paint_banner()

    def _paint_banner(self):
        if BANNER_MODE != "image":
            return
        if not HAS_PIL or not self._bg_src:
            self.banner_lbl.configure(text=T("banner").replace("\n", "  -  "),
                                      bg=core.theme()["dialog_accent"],
                                      fg="white", image="")
            return
        try:
            w = self.banner_lbl.winfo_width()
        except Exception:
            w = 0
        if not w or w < 50:
            self.root.after(200, self._paint_banner)
            return
        if abs(w - self._banner_w) < 30 and self._banner_img is not None:
            # text may still need a language refresh
            try:
                self.banner_lbl.configure(text=T("banner"))
            except Exception:
                pass
            return
        self._banner_w = w
        try:
            im = Image.open(self._bg_src).convert("RGB")
            im = im.resize((w, self.banner_h), Image.LANCZOS)
            self._banner_img = ImageTk.PhotoImage(im)
            self.banner_lbl.configure(
                image=self._banner_img,
                text=T("banner"),
                compound="center", fg=BANNER_FG,
                font=("Segoe UI", 14, "bold") if core.theme_name() == "aero"
                else ("Tahoma", 14, "bold"))
        except Exception:
            pass

    # -- toolbar ---------------------------------------------------------------
    def _build_toolbar(self):
        bar = tk.Frame(self.content, bg=FACE)
        bar.pack(fill="x", padx=2, pady=(2, 0))

        self.btn_add = w98_button(bar, text=T("tb_add"), command=self.cmd_add,
                                  width=12, tip=T("tip_add"))
        self.btn_add.pack(side="left", padx=2, pady=2)
        self.btn_paste = w98_button(bar, text=T("tb_paste"), command=self.cmd_paste,
                                    width=12, tip=T("tip_paste"))
        self.btn_paste.pack(side="left", padx=2, pady=2)
        self.btn_start = w98_button(bar, text=T("tb_start"), command=self.cmd_start,
                                    width=10, tip=T("tip_start"))
        self.btn_start.pack(side="left", padx=2, pady=2)
        self.btn_stop = w98_button(bar, text=T("tb_stop"), command=self.cmd_stop,
                                   width=10, tip=T("tip_stop"))
        self.btn_stop.pack(side="left", padx=2, pady=2)
        self.btn_clear = w98_button(bar, text=T("tb_clear"), command=self.cmd_clear_done,
                                    width=10, tip=T("tip_clear"))
        self.btn_clear.pack(side="left", padx=2, pady=2)

        right = tk.Frame(bar, bg=FACE)
        right.pack(side="right")
        w98_button(right, text=T("tb_themes"), command=self.cmd_themes,
                   width=9, tip=T("tip_themes")).pack(side="left", padx=2, pady=2)
        w98_button(right, text=T("tb_options"), command=self.cmd_settings,
                   width=9, tip=T("tip_options")).pack(side="left", padx=2, pady=2)
        w98_button(right, text="?", command=self.cmd_about,
                   width=3, tip=T("tip_about")).pack(side="left", padx=2, pady=2)

    # -- format bar ------------------------------------------------------------
    def _build_formatbar(self):
        fr = w98_sunken(self.content)
        fr.pack(fill="x", padx=2, pady=4)
        inner = tk.Frame(fr, bg=FACE)
        inner.pack(fill="x", padx=8, pady=6)

        w98_label(inner, text=T("fmt_label"), bold=True).pack(side="left")
        tk.Radiobutton(inner, text=T("fmt_mp4"), variable=self.default_fmt, value="mp4",
                       bg=FACE, activebackground=FACE, font=FONT_UI, fg=TEXT_FG,
                       selectcolor=ENTRY_BG).pack(side="left", padx=6)
        tk.Radiobutton(inner, text=T("fmt_mp3"), variable=self.default_fmt, value="mp3",
                       bg=FACE, activebackground=FACE, font=FONT_UI, fg=TEXT_FG,
                       selectcolor=ENTRY_BG).pack(side="left", padx=2)

        w98_label(inner, text=T("fmt_quality"), bold=True).pack(side="left", padx=(14, 2))
        self.q_combo = tk.OptionMenu(inner, self.default_q_mp4, "360p", "480p", "720p", "1080p", T("q_best"))
        self.q_combo.configure(bg=ENTRY_BG, fg=TEXT_FG, font=FONT_UI,
                               relief=core.theme()["relief_entry"], bd=2,
                               highlightthickness=0, width=8)
        self.q_combo.pack(side="left", padx=2)
        self.mp3q = tk.OptionMenu(inner, self.default_q_mp3, "128k", "192k", "320k")
        self.mp3q.configure(bg=ENTRY_BG, fg=TEXT_FG, font=FONT_UI,
                            relief=core.theme()["relief_entry"], bd=2,
                            highlightthickness=0, width=6)

        def _sync_fmt(*a):
            if self.default_fmt.get() == "mp3":
                self.q_combo.pack_forget()
                self.mp3q.pack(side="left", padx=2, after=None)
                # OptionMenu sirasi karisabilir; en basa degil sona ekle, sorun degil
            else:
                try:
                    self.mp3q.pack_forget()
                except Exception:
                    pass
                self.q_combo.pack(side="left", padx=2)
            self._set_status(T("fmt_hint"))
        self.default_fmt.trace_add("write", _sync_fmt)

        w98_label(inner, text=T("fmt_out"),
                  ).pack(side="right", padx=4)
        # baslangicta mp4 combo gorunur
        try:
            self.mp3q.pack_forget()
        except Exception:
            pass

    # -- download list ---------------------------------------------------------
    def _build_list(self):
        wrap = w98_sunken(self.content)
        wrap.pack(fill="both", expand=True, padx=2, pady=0)

        head_relief = "raised" if core.theme_name() == "win98" else "flat"
        head = tk.Frame(wrap, bg=FACE, relief=head_relief, bd=1)
        head.pack(fill="x")
        tk.Label(head, text=T("list_head"), bg=FACE, fg=TEXT_FG,
                 font=FONT_UI, anchor="w").pack(side="left", fill="x", expand=True)
        self.count_lbl = tk.Label(head, text=T("count", n=0), bg=FACE, fg=TEXT_FG,
                                  font=FONT_UI)
        self.count_lbl.pack(side="right", padx=8)

        self.canvas = tk.Canvas(wrap, bg=LIST_BG, highlightthickness=0)
        self.vbar = tk.Scrollbar(wrap, orient="vertical", command=self.canvas.yview,
                                 bg=FACE, relief="raised", bd=2, width=16)
        self.canvas.configure(yscrollcommand=self.vbar.set)
        self.vbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.listframe = tk.Frame(self.canvas, bg=LIST_BG)
        self.win = self.canvas.create_window((0, 0), window=self.listframe, anchor="nw")
        self.listframe.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self.win, width=e.width))

        self.empty_lbl = tk.Label(self.listframe, bg=LIST_BG, fg=MUTED_FG, font=FONT_UI,
                                  text=T("empty"),
                                  justify="center")
        self.empty_lbl.pack(fill="x", pady=10)

    def _wheel(self, ev):
        try:
            if self.canvas.winfo_containing(ev.x_root, ev.y_root) == self.canvas or True:
                self.canvas.yview_scroll(int(-1 * (ev.delta / 120)), "units")
        except Exception:
            pass

    # -- status bar ------------------------------------------------------------
    def _build_statusbar(self):
        sb = tk.Frame(self.content, bg=FACE)
        sb.pack(fill="x", padx=2, pady=(4, 0))
        sb_relief = "sunken" if core.theme_name() == "win98" else "flat"
        sb_bd = 2 if core.theme_name() == "win98" else 1
        self.status_left = tk.Label(sb, text=T("sb_ready"), bg=FACE, fg=TEXT_FG,
                                    relief=sb_relief, bd=sb_bd,
                                    font=FONT_UI, anchor="w", padx=6)
        self.status_left.pack(side="left", fill="x", expand=True, padx=(0, 2))
        self.status_mid = tk.Label(sb, text="ffmpeg: ?", bg=FACE, fg=TEXT_FG,
                                   relief=sb_relief, bd=sb_bd,
                                   font=FONT_UI, anchor="w", width=24, padx=6)
        self.status_mid.pack(side="left", padx=2)
        self.status_right = tk.Label(sb, text="0%", bg=FACE, fg=TEXT_FG,
                                     relief=sb_relief, bd=sb_bd,
                                     font=FONT_UI, anchor="center", width=10)
        self.status_right.pack(side="left", padx=(2, 0))
        self.status_mid.configure(text=T("sb_ffmpeg_ok") if FFMPEG_EXE else T("sb_ffmpeg_missing"))

    def _set_status(self, txt):
        try:
            self.status_left.configure(text=txt)
        except Exception:
            pass

    # ====================================================================
    # Komutlar
    # ====================================================================
    def cmd_add(self):
        try:
            clip = self.root.clipboard_get().strip()
        except Exception:
            clip = ""
        urls = extract_urls(clip)
        initial = urls[0] if urls else (clip if clip.startswith("http") else "")
        # varsayilan bicim/kalite
        fmt = self.default_fmt.get()
        q = self.default_q_mp3.get() if fmt == "mp3" else self.default_q_mp4.get()
        d = AddDialog(self.root, initial=initial, fmt=fmt, quality=q)
        self.root.wait_window(d)
        if d.result:
            url, f, q = d.result
            # birden cok link yapistirildysa hepsini al
            found = extract_urls(url)
            targets = found if found else [url]
            for u in targets:
                self.add_url(u, f, q)

    def cmd_paste(self):
        try:
            clip = self.root.clipboard_get().strip()
        except Exception:
            messagebox.showinfo(T("paste_title"), T("paste_empty"))
            return
        urls = extract_urls(clip)
        if urls:
            fmt = self.default_fmt.get()
            q = self.default_q_mp3.get() if fmt == "mp3" else self.default_q_mp4.get()
            added = 0
            for u in urls:
                if self.add_url(u, fmt, q, silent=True):
                    added += 1
            self._set_status(T("paste_added", n=added))
            if added == 0:
                messagebox.showinfo(T("paste_title"), T("paste_dup"))
        else:
            # duz metin link de olabilir (kisa link vs.)
            if clip.startswith("http"):
                fmt = self.default_fmt.get()
                q = self.default_q_mp3.get() if fmt == "mp3" else self.default_q_mp4.get()
                self.add_url(clip, fmt, q)
            else:
                messagebox.showinfo(T("paste_title"), T("paste_none") + clip[:200])

    def cmd_settings(self):
        d = SettingsDialog(self.root, OUT_MP4, OUT_MP3, self.auto_clip, self.max_parallel)
        self.root.wait_window(d)
        if d.result:
            auto, par, th, lg = d.result
            self.auto_clip, self.max_parallel = auto, par
            changed = False
            if th != core.theme_name():
                apply_theme(th)
                changed = True
            if lg != core.lang():
                core.set_language(lg)
                changed = True
            core.save_prefs(BASE)
            if changed:
                self.rebuild_ui()
            self._set_status(T("msg_settings_saved"))

    def cmd_about(self):
        messagebox.showinfo(
            T("about_title"),
            APP_TITLE + T("about_body"),
        )

    def add_url(self, url, fmt="mp4", quality="720p", silent=False):
        url = (url or "").strip().strip("<>")
        if not url:
            return False
        with self.lock:
            for it in self.items:
                if it.url == url and it.fmt == fmt:
                    if not silent:
                        messagebox.showinfo(T("dup_title"), T("dup_body"))
                    return False
            item = QueueItem(url=url, fmt=fmt, quality=quality, status="Fetching info", indet=True)
            self.items.append(item)
            idx = len(self.items) - 1
        self._ui_add_row(idx)
        threading.Thread(target=self._resolve_info, args=(idx,), daemon=True).start()
        return True

    # -- bilgi cozme ------------------------------------------------------
    def _resolve_info(self, idx):
        try:
            item = self.items[idx]
        except Exception:
            return
        try:
            res = fetch_info(item.url, FFMPEG_EXE)
            if res.get("playlist"):
                # ilkini guncelle, kalanlari ekle
                entries = res["entries"]
                if not entries:
                    raise RuntimeError(T("pl_empty"))
                first = entries[0]
                item.title = first["title"]
                item.duration = fmt_duration(first.get("duration"))
                item.url = first["url"]
                item.status = "Waiting"
                item.indet = False
                self.ui_queue.put(("refresh", idx))
                for e in entries[1:]:
                    with self.lock:
                        ni = QueueItem(url=e["url"], fmt=item.fmt, quality=item.quality,
                                       title=e["title"], duration=fmt_duration(e.get("duration")),
                                       status="Waiting")
                        self.items.append(ni)
                        nidx = len(self.items) - 1
                    self.ui_queue.put(("addrow", nidx))
                self.ui_queue.put(("status", T("pl_added", t=res["playlist_title"],
                                                           n=len(entries))))
            else:
                item.title = safe_filename(res["title"], 100)
                item.duration = fmt_duration(res.get("duration"))
                item.status = "Waiting"
                item.indet = False
                self.ui_queue.put(("refresh", idx))
        except Exception as ex:
            # baslik alinamasa bile indirmeye izin ver (URL'yi baslik yap)
            item.title = item.url[:80]
            item.status = "Waiting"
            item.indet = False
            item.error = str(ex)[:120]
            self.ui_queue.put(("refresh", idx))

    # -- baslat / durdur ---------------------------------------------------
    def cmd_start(self):
        with self.lock:
            pending = [i for i, it in enumerate(self.items)
                       if it.status in ("Waiting", "Error", "Stopped")]
        if not pending:
            self._set_status(T("msg_nothing"))
            return
        # calisan sayisini asmayacak kadar baslat
        slots = self.max_parallel - self.downloading
        if slots <= 0:
            self._set_status(T("msg_running"))
            return
        for idx in pending[:slots]:
            self.stop_flags[idx] = False
            threading.Thread(target=self._download_one, args=(idx,), daemon=True).start()
        self._set_status(T("msg_downloading", n=min(len(pending), self.max_parallel)))

    def cmd_stop(self):
        with self.lock:
            actives = [i for i, it in enumerate(self.items) if it.status in ("Downloading", "Converting", "Retrying")]
        if not actives:
            self._set_status(T("msg_noactive"))
            return
        for i in actives:
            self.stop_flags[i] = True
        self._set_status(T("msg_stopping"))

    def cmd_clear_done(self):
        with self.lock:
            keep = [(it) for it in self.items if it.status not in ("Completed", "Error")]
            removed = len(self.items) - len(keep)
            self.items = keep
        # satirlari bastan kur
        for w in list(self.listframe.winfo_children()):
            if w is not self.empty_lbl:
                w.destroy()
        self.rows = {}
        for idx, it in enumerate(self.items):
            self._ui_add_row(idx, refresh_only=False)
        self._sync_empty()
        self._set_status(T("msg_cleared", n=removed) if removed else T("msg_noclear"))

    # -- indirme ------------------------------------------------------------
    def _hook_for(self, idx):
        def hook(d):
            try:
                item = self.items[idx]
            except Exception:
                return
            if self.stop_flags.get(idx):
                raise RuntimeError("Stopped by user.")
            st = d.get("status")
            if st == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate")
                done = d.get("downloaded_bytes", 0)
                item.status = "Downloading"
                item.indet = not total
                if total:
                    item.progress = done / total
                item.size = fmt_bytes(total) if total else fmt_bytes(done)
                item.speed = fmt_speed(d.get("speed"))
                item.eta = fmt_eta(d.get("eta"))
                fn = d.get("filename") or d.get("info_dict", {}).get("_filename") or ""
                if fn:
                    item.filename = os.path.basename(fn)
                self.ui_queue.put(("refresh", idx))
            elif st == "finished":
                item.status = "Converting"
                item.indet = True
                fn = d.get("filename") or ""
                if fn:
                    item.filename = os.path.basename(fn)
                self.ui_queue.put(("refresh", idx))
            elif st == "processing":
                item.status = "Converting"
                item.indet = True
                self.ui_queue.put(("refresh", idx))
        return hook

    def _download_variants(self, item, overrides=None):
        """(label, opts) attempts, strongest first.

        Networks fail in different ways (TLS fingerprint walls, broken IPv6
        routes, throttling), so a single configuration is never enough.
        """
        base = build_ydl_opts(item, FFMPEG_EXE, [])
        variants = []
        if base.get("impersonate") is not None:
            variants.append(("chrome", dict(base)))
        plain = dict(base)
        plain.pop("impersonate", None)
        variants.append(("direct", plain))
        v4 = dict(plain)
        v4["force_ipv4"] = True
        variants.append(("ipv4", v4))
        ch = dict(v4)
        ch["http_chunk_size"] = 10 * 1024 * 1024
        variants.append(("chunked", ch))
        if overrides:
            for _label, opts in variants:
                opts.update(overrides)
        return variants

    def _single_attempt(self, item, idx, label, opts):
        hook = self._hook_for(idx)
        opts["progress_hooks"] = [hook]
        opts["postprocessor_hooks"] = [hook]
        import yt_dlp
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([item.url])

    def _download_one(self, idx, _overrides=None):
        with self.lock:
            self.downloading += 1
        try:
            item = self.items[idx]
        except Exception:
            with self.lock:
                self.downloading -= 1
            return
        self.ui_queue.put(("refresh", idx))
        try:
            item.status = "Downloading"
            item.progress = 0.0
            item.retry_a = 0
            item.retry_t = 0
            item.retry_why = ""
            self.ui_queue.put(("refresh", idx))
            variants = self._download_variants(item, overrides=_overrides)
            item.retry_t = len(variants)
            log_line(f"START {item.fmt}/{item.quality} {item.url}")
            last_err = ""
            tls_fails = 0
            for ai, (label, opts) in enumerate(variants):
                if self.stop_flags.get(idx):
                    raise RuntimeError("Stopped by user.")
                if ai > 0:
                    item.status = "Retrying"
                    item.retry_a = ai + 1
                    item.retry_why = label
                    item.indet = True
                    self.ui_queue.put(("refresh", idx))
                    log_line(f"RETRY {ai + 1}/{len(variants)} ({label}) {item.url}")
                try:
                    self._single_attempt(item, idx, label, opts)
                    last_err = ""
                    break
                except Exception as ex2:
                    last_err = str(ex2) or repr(ex2)
                    if "Stopped by user" in last_err:
                        raise
                    if is_tls_error(last_err):
                        tls_fails += 1
                    log_line(f"FAIL attempt {ai + 1} ({label}): {last_err[:400]}")
                    continue
            item.tls_fails = tls_fails
            item.retry_t = len(variants)
            if last_err:
                raise RuntimeError(last_err)
            if self.stop_flags.get(idx):
                raise RuntimeError("Stopped by user.")
            # gercek cikti dosyasini bul (basliktan tahmin yerine klasordeki en yeni)
            item.status = "Completed"
            item.progress = 1.0
            item.indet = False
            item.speed = "--"
            item.eta = "00:00"
            # dosya adini netlestir
            outdir = OUT_MP3 if item.fmt == "mp3" else OUT_MP4
            try:
                cands = [os.path.join(outdir, f) for f in os.listdir(outdir)]
                cands = [c for c in cands if os.path.isfile(c)]
                if cands:
                    newest = max(cands, key=os.path.getmtime)
                    # son 10 dakikada degistiyse bu bizimki sayilir
                    if time.time() - os.path.getmtime(newest) < 600:
                        item.filename = os.path.basename(newest)
                        item.size = fmt_bytes(os.path.getsize(newest))
            except Exception:
                pass
            self.ui_queue.put(("refresh", idx))
            log_line(f"DONE {item.filename or item.title[:60]} -> {outdir}")
            self.ui_queue.put(("status", T("msg_done", t=item.title[:60], d=outdir)))
            # bitince siradakini otomatik baslat (kuyruk akisi)
            self.ui_queue.put(("pump", None))
        except Exception as ex:
            msg = str(ex) or repr(ex)  # never show a blank "Error:"
            if "Stopped by user" in msg:
                item.status = "Stopped"
                item.indet = False
            else:
                item.status = "Error"
                item.indet = False
                # yaygin hatalari Turkcelestir
                ml = msg.lower()
                if (getattr(item, "tls_fails", 0) >= 4 or
                        (getattr(item, "tls_fails", 0) > 0 and is_tls_error(msg)
                         and "sign in to confirm" not in ml)):
                    # every route died inside TLS: something on this PC
                    # (DPI bypass, VPN, antivirus scan) mangles handshakes
                    tools = detect_traffic_tools()
                    if tools:
                        nice = TOOL_DISPLAY.get(tools[0], tools[0].capitalize())
                        item.error = T("err_tls_tool", tool=nice)
                        log_line(f"TLS-BLOCKED, running tool suspected: {tools}")
                    else:
                        item.error = T("err_tls")
                        log_line("TLS-BLOCKED, no known tool process found")
                elif "sign in to confirm" in ml or ("age" in ml and ("restrict" in ml or "confirm" in ml)):
                    item.error = T("err_age")
                elif "ffmpeg" in ml and ("not found" in ml or "no such" in ml):
                    item.error = T("err_ffmpeg")
                elif "Private video" in msg:
                    item.error = T("err_private")
                elif "Video unavailable" in msg:
                    item.error = T("err_unavail")
                else:
                    item.error = msg[:160]
            self.ui_queue.put(("refresh", idx))
            self.ui_queue.put(("status", T("msg_failed", t=item.title[:50],
                                           e=getattr(item, "error", "")[:60])))
            self.ui_queue.put(("pump", None))
        finally:
            with self.lock:
                self.downloading -= 1
            self.ui_queue.put(("counts", None))

    # -- pano izleme ---------------------------------------------------------
    def _clip_watch(self):
        if self.auto_clip:
            try:
                cur = self.root.clipboard_get()
            except Exception:
                cur = ""
            if cur and cur != self.last_clip:
                self.last_clip = cur
                urls = extract_urls(cur)
                # sadece yeni ve kisa suredir kopyalanmissa? basit: her yeni pano icerigi 1 kez islenir
                new = []
                with self.lock:
                    known = {it.url for it in self.items}
                for u in urls:
                    if u not in known:
                        new.append(u)
                if new:
                    fmt = self.default_fmt.get()
                    q = self.default_q_mp3.get() if fmt == "mp3" else self.default_q_mp4.get()
                    for u in new[:5]:  # ani spam korumasi
                        self.add_url(u, fmt, q, silent=True)
                    self._set_status(T("msg_caught", n=len(new)))
        self.root.after(1200, self._clip_watch)

    # -- UI pompa (thread -> tkinter) -----------------------------------------
    def _pump_ui(self):
        try:
            while True:
                kind, payload = self.ui_queue.get_nowait()
                if kind == "refresh":
                    self._refresh_row(payload)
                elif kind == "addrow":
                    self._ui_add_row(payload)
                elif kind == "status":
                    self._set_status(payload)
                elif kind == "counts":
                    self._sync_counts()
                elif kind == "pump":
                    # biten slotu doldur: bekleyen varsa baslat
                    with self.lock:
                        pending = [i for i, it in enumerate(self.items) if it.status == "Waiting"]
                    if pending and self.downloading < self.max_parallel:
                        idx = pending[0]
                        self.stop_flags[idx] = False
                        threading.Thread(target=self._download_one, args=(idx,), daemon=True).start()
                    else:
                        self._sync_counts()
                        if self.downloading == 0:
                            with self.lock:
                                done = sum(1 for it in self.items if it.status == "Completed")
                                total = len(self.items)
                            if total and done == total:
                                self._set_status(T("msg_alldone", d=done, t=total))
                self._sync_counts()
        except queue.Empty:
            pass
        self.root.after(120, self._pump_ui)

    # -- satir yonetimi ---------------------------------------------------------
    def _ui_add_row(self, idx, refresh_only=True):
        try:
            item = self.items[idx]
        except Exception:
            return
        self.empty_lbl.pack_forget()
        row = ItemRow(self.listframe, item, on_open=self.open_file, on_remove=self.remove_item)
        row.pack(fill="x", padx=4, pady=3)
        item.row = row
        self.rows[idx] = row
        # rows dict index kaymasina karsi: silme sonrasi bastan kuruluyor, o yuzden su anlik yeterli
        self._sync_counts()
        self.canvas.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.canvas.yview_moveto(1.0)

    def _refresh_row(self, idx):
        try:
            item = self.items[idx]
            row = getattr(item, "row", None)
            if row is not None and row.winfo_exists():
                row.refresh()
        except Exception:
            pass
        # genel ilerleme
        try:
            with self.lock:
                act = [it for it in self.items if it.status in ("Downloading", "Converting", "Retrying")]
                if act:
                    avg = sum(it.progress for it in act) / len(act)
                    self.status_right.configure(text=f"%{int(avg*100)}")
                elif any(it.status == "Completed" for it in self.items):
                    self.status_right.configure(text="100%")
        except Exception:
            pass

    def _sync_counts(self):
        try:
            self.count_lbl.configure(text=T("count", n=len(self.items)))
        except Exception:
            pass
        self._sync_empty()

    def _sync_empty(self):
        try:
            if self.items:
                self.empty_lbl.pack_forget()
            else:
                self.empty_lbl.pack(fill="x", pady=10)
        except Exception:
            pass

    def open_file(self, item: QueueItem):
        outdir = OUT_MP3 if item.fmt == "mp3" else OUT_MP4
        target = os.path.join(outdir, item.filename) if item.filename else outdir
        try:
            if os.path.isfile(target):
                # dosyayi secili sekilde goster
                subprocess.Popen(["explorer", "/select,", os.path.abspath(target)])
            else:
                os.startfile(os.path.abspath(outdir))
        except Exception as ex:
            messagebox.showerror(T("err_open"), str(ex))

    def remove_item(self, item: QueueItem):
        # aktif indirme kaldirilamaz
        if item.status in ("Downloading", "Converting", "Retrying"):
            messagebox.showwarning(T("busy_title"), T("busy_body"))
            return
        with self.lock:
            if item in self.items:
                self.items.remove(item)
        try:
            if item.row is not None and item.row.winfo_exists():
                item.row.destroy()
        except Exception:
            pass
        # indexler kaydi -> satirlari bastan kur (en saglam yol)
        for w in list(self.listframe.winfo_children()):
            if w is not self.empty_lbl:
                w.destroy()
        for idx, it in enumerate(self.items):
            row = ItemRow(self.listframe, it, on_open=self.open_file, on_remove=self.remove_item)
            row.pack(fill="x", padx=4, pady=3)
            it.row = row
            self.rows[idx] = row
        self._sync_counts()


def main():
    core.load_prefs(core.program_dir())
    apply_theme()
    root = tk.Tk()
    root.configure(bg=FACE)
    root.option_add("*Background", FACE)
    root.option_add("*Foreground", TEXT_FG)
    root.option_add("*Font", FONT_UI)
    root.option_add("*Button.Background", FACE)
    root.option_add("*Entry.Background", ENTRY_BG)
    root.option_add("*Text.Background", ENTRY_BG)
    try:
        ip = icon_path()
        if ip:
            root.iconbitmap(ip)
    except Exception:
        pass
    app = App(root)
    try:
        if not FFMPEG_EXE:
            root.after(800, lambda: messagebox.showwarning(
                T("ff_title"),
                T("ff_body")))
    except Exception:
        pass
    root.mainloop()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        try:
            messagebox.showerror(T("fatal"), traceback.format_exc()[-1500:])
        except Exception:
            pass
