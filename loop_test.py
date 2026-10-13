"""Self-test rig: proves the retry matrix without touching YouTube.

A: localhost mp4 download through the REAL _download_one loop -> file lands.
B: dead endpoint -> all variants tried, final error set, download.log written.
"""
import functools
import http.server
import os
import socket
import subprocess
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import app
from app import QueueItem

WORK = r"C:\Users\bilal\AppData\Local\Temp\opencode\looptest"
os.makedirs(WORK, exist_ok=True)
for f in os.listdir(WORK):
    try:
        os.remove(os.path.join(WORK, f))
    except OSError:
        pass

failures = []


def check(name, cond, extra=""):
    print(("PASS " if cond else "FAIL ") + name, extra)
    if not cond:
        failures.append(name)


# --- make a tiny mp4 with the bundled ffmpeg -------------------------------
SRVDIR = os.path.join(WORK, "srv")
os.makedirs(SRVDIR, exist_ok=True)
SRC = os.path.join(SRVDIR, "source.mp4")
ff = app.find_ffmpeg()
print("ffmpeg:", ff)
r = subprocess.run(
    [ff, "-y", "-v", "error", "-f", "lavfi",
     "-i", "testsrc=duration=2:size=320x240:rate=10",
     "-pix_fmt", "yuv420p", SRC],
    capture_output=True, text=True)
check("test mp4 generated", os.path.exists(SRC), r.stderr[:120])
app.OUT_MP4 = WORK
app.OUT_MP3 = WORK

# --- serve it on localhost --------------------------------------------------
class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass

srv = http.server.ThreadingHTTPServer(
    ("127.0.0.1", 0),
    functools.partial(Quiet, directory=SRVDIR))
port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
print("serving on", port)

import tkinter as tk
import vyt_core as core
core.load_prefs(app.BASE)
app.apply_theme("aero")
root = tk.Tk()
root.withdraw()
a = app.App(root)
a.auto_clip = False  # don't let clipboard interfere

# --- Test A: success path through the real loop -----------------------------
a.items.append(QueueItem(url=f"http://127.0.0.1:{port}/source.mp4",
                         fmt="mp4", quality="720p", title="looptest"))
a._ui_add_row(0)
t = threading.Thread(target=a._download_one, args=(0,), daemon=True)
t.start()
t.join(timeout=120)
check("A thread finished", not t.is_alive())
it = a.items[0]
check("A status Completed", it.status == "Completed", it.status)
got = [f for f in os.listdir(WORK) if f.endswith(".mp4")]
check("A file downloaded", got == ["source.mp4"], str(got))
log = open(app.LOG_FILE, encoding="utf-8").read() if os.path.exists(app.LOG_FILE) else ""
check("A START logged", "START mp4/720p" in log)

# --- Test B: failure path, all variants, fast -------------------------------
a.items.append(QueueItem(url="http://127.0.0.1:9/nope.mp4",
                         fmt="mp4", quality="720p", title="deadtest"))
a._ui_add_row(1)
fast = {"retries": 1, "socket_timeout": 2, "fragment_retries": 1,
        "retry_sleep_functions": {"http": lambda n: 0, "fragment": lambda n: 0}}
t0 = time.time()
t2 = threading.Thread(target=a._download_one, args=(1, fast), daemon=True)
t2.start()
t2.join(timeout=180)
dt = time.time() - t0
check("B thread finished", not t2.is_alive(), f"{dt:.0f}s")
it2 = a.items[1]
check("B status Error", it2.status == "Error", it2.status)
check("B error non-empty", bool(it2.error), repr(it2.error[:100]))
log2 = open(app.LOG_FILE, encoding="utf-8").read()
n_retry = log2.count("RETRY")
check("B all 4 variants tried (3 retries logged)", n_retry >= 3, f"retries={n_retry}")
check("B FAIL lines logged", "FAIL attempt" in log2)

# --- Test C: retry status line renders ---------------------------------------
it2.status = "Retrying"
it2.retry_a = 2
it2.retry_t = 4
it2.retry_why = "ipv4"
it2.row.refresh()
txt = it2.row.status_lbl.cget("text")
check("C retry line", "2/4" in txt and "ipv4" in txt, txt)
core_lang = __import__("vyt_core").lang()
__import__("vyt_core").set_language("tr")
it2.row.refresh()
txt_tr = it2.row.status_lbl.cget("text")
check("C retry line TR", "Tekrar" in txt_tr, txt_tr)
__import__("vyt_core").set_language(core_lang)

srv.shutdown()
root.destroy()
print("FAILURES:", failures if failures else "none")
sys.exit(1 if failures else 0)
