"""Smoke test: themes + languages + rebuild + prefs (no network)."""
import os
import sys
import tkinter as tk

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vyt_core as core
import app
from app import QueueItem

failures = []


def check(name, cond):
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        failures.append(name)


# 1) default prefs -> aero + en (start from a clean slate)
try:
    os.remove(core.prefs_path(app.BASE))
except Exception:
    pass
core.load_prefs(app.BASE)
check("default theme aero", core.theme_name() == "aero")
check("default lang en", core.lang() == "en")

# 2) string tables complete
for key, table in core.STRINGS.items():
    if "en" not in table or "tr" not in table:
        check(f"i18n {key}", False)
        break
else:
    check("i18n tables complete", True)

# 3) T() works both langs
core.set_language("tr")
check("T tr", app.T("tb_start") == "\u25bc  Ba\u015flat")
core.set_language("en")
check("T en", app.T("tb_start") == "\u25bc  Start")

# 4) App builds in aero
app.apply_theme()
r = tk.Tk()
a = app.App(r)
r.update_idletasks()
r.update()
bits = a._taskbar_icon_ok()
check("taskbar style bits", bits.get("appwindow") is True
      and bits.get("toolwindow") is False)
a.items.append(QueueItem(url="https://www.youtube.com/watch?v=x",
                         title="Test", status="Downloading", progress=0.5,
                         size="10 MB", speed="1 MB/s", eta="00:10"))
a._ui_add_row(0)
a._refresh_row(0)
r.update_idletasks()
check("aero build", getattr(a, "_banner_img", None) is not None)
check("aero progress mode", app.CHUNKY_BAR is False)

# 5) switch to win98 -> rebuild consistent
a.set_theme("win98")
r.update_idletasks()
r.update()
check("win98 applied", core.theme_name() == "win98")
check("win98 chunky", app.CHUNKY_BAR is True)
check("rows survive theme switch", len(a.items) == 1 and a.items[0].row is not None
      and a.items[0].row.winfo_exists())
check("toolbar english->still", "Start" in a.btn_start.cget("text"))

# 6) switch to turkish -> rebuild
a.set_language("tr")
r.update_idletasks()
check("tr toolbar", "Ba\u015flat" in a.btn_start.cget("text"))
a.items[0].row.refresh()
check("tr status", "ndiriliyor" in a.items[0].row.status_lbl.cget("text"))
a.set_language("en")

# 7) prefs persisted
check("settings.json written", os.path.exists(core.prefs_path(app.BASE)))
import json
saved = json.load(open(core.prefs_path(app.BASE), encoding="utf-8"))
check("prefs theme saved", saved.get("theme") == "win98")

# 8) back to aero default for the user
a.set_theme("aero")
core.set_language("en")
core.save_prefs(app.BASE)

# 9) network opts: impersonate + cookies wiring
o = app.build_ydl_opts(app.QueueItem(url="x", fmt="mp4"), None, [])
if app.HAS_CURL_CFFI:
    imp = o.get("impersonate")
    check("impersonate target", getattr(imp, "client", None) == "chrome")
else:
    check("impersonate skipped (no curl_cffi)", "impersonate" not in o)
core.PREFS["cookies_source"] = "chrome"
o2 = app.build_ydl_opts(app.QueueItem(url="x", fmt="mp4"), None, [])
check("cookiesfrombrowser set", o2.get("cookiesfrombrowser") == ("chrome",))
core.PREFS["cookies_source"] = "none"
core.save_prefs(app.BASE)

# 10) age-gate message mapping (no network)
core.set_language("tr")
ml = "Sign in to confirm your age. Use --cookies-from-browser".lower()
mapped = ("Yaş sınırlı" in app.T("err_age"))
check("tr age-gate string", mapped)
core.set_language("en")
check("en age-gate string", "Age-restricted" in app.T("err_age"))

# 11) TLS-block detector (offline unit checks)
check("tls marker ssl", app.is_tls_error("[SSL: INVALID_SESSION_ID] invalid session id"))
check("tls marker curl", app.is_tls_error("Failed to perform, curl: (35) TLS connect error: OPENSSL_internal:DECODE_ERROR"))
check("tls marker reset", app.is_tls_error("Recv failure: Connection was reset"))
check("tls negative", not app.is_tls_error("Video unavailable"))
check("tls empty safe", not app.is_tls_error(""))
tools = app.detect_traffic_tools()
check("tool scan runs", isinstance(tools, list))
check("tls strings", "GoodbyeDPI" in app.T("err_tls") and "TLS" in app.T("err_tls_tool", tool="X"))
r.destroy()

print("FAILURES:", failures if failures else "none")
sys.exit(1 if failures else 0)
