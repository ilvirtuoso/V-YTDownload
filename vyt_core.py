#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""V-YTDownload core: themes, localization, preferences, frozen paths.

Stdlib only. app.py reads the active theme through module-level names
(FACE, FONT_UI, ...) that apply_theme() refreshes, so switching themes is
just: set values + rebuild the widgets.
"""
import json
import os
import sys

APP_NAME = "V-YTDownload"

# ----------------------------------------------------------------------------
# Themes
# ----------------------------------------------------------------------------
THEMES = {
    "aero": {
        "key": "aero",
        # surfaces
        "bg": "#d7e5f5",
        "panel": "#e9f1fa",
        "entry_bg": "#ffffff",
        "list_bg": "#eef4fb",
        "row_bg": "#ffffff",
        # buttons (glass blue)
        "btn_bg": "#e3eefb",
        "btn_hover": "#ffffff",
        "btn_press": "#bcd7f1",
        "btn_border": "#6ea3d4",
        # text
        "text": "#16222e",
        "muted": "#4c6274",
        "accent": "#175b9c",
        "ok": "#1a7a2e",
        "err": "#c00000",
        "select_bg": "#175b9c",
        "select_fg": "#ffffff",
        # title bar gradient (Frutiger aqua-blue)
        "title1": "#123f6e",
        "title2": "#8ec6ef",
        # progress bar
        "bar_top": "#bfe3fb",
        "bar_bottom": "#1c6fc4",
        "bar_border": "#4d8fcb",
        "bar_text": "#0e3a5c",
        "chunky": False,
        # banner
        "banner_mode": "image",
        "banner_fg": "#12365f",
        # fonts
        "font_ui": ("Segoe UI", 9),
        "font_bold": ("Segoe UI", 9, "bold"),
        "font_title": ("Segoe UI", 9, "bold"),
        "font_mono": ("Consolas", 9),
        # widget relief
        "relief_btn": "flat",
        "relief_panel": "flat",
        "relief_entry": "flat",
        "hover_glow": True,
        "dialog_accent": "#175b9c",
    },
    "win98": {
        "key": "win98",
        "bg": "#c0c0c0",
        "panel": "#c0c0c0",
        "entry_bg": "#ffffff",
        "list_bg": "#ffffff",
        "row_bg": "#ffffff",
        "btn_bg": "#c0c0c0",
        "btn_hover": "#c0c0c0",
        "btn_press": "#c0c0c0",
        "btn_border": "#808080",
        "text": "#000000",
        "muted": "#404040",
        "accent": "#000080",
        "ok": "#008000",
        "err": "#c00000",
        "select_bg": "#000080",
        "select_fg": "#ffffff",
        "title1": "#000080",
        "title2": "#1084d0",
        "bar_top": "#000080",
        "bar_bottom": "#000080",
        "bar_border": "#808080",
        "bar_text": "#000000",
        "chunky": True,
        "banner_mode": "plain",
        "banner_fg": "#ffffff",
        "font_ui": ("Tahoma", 8),
        "font_bold": ("Tahoma", 8, "bold"),
        "font_title": ("Tahoma", 8, "bold"),
        "font_mono": ("Courier New", 8),
        "relief_btn": "raised",
        "relief_panel": "raised",
        "relief_entry": "sunken",
        "hover_glow": False,
        "dialog_accent": "#000080",
    },
}

THEME_ORDER = ["aero", "win98"]
DEFAULT_THEME = "aero"
LANGS = ["en", "tr"]
DEFAULT_LANG = "en"

_active_theme = THEMES[DEFAULT_THEME]
_active_lang = DEFAULT_LANG


def theme():
    return _active_theme


def theme_name():
    return _active_theme.get("key", DEFAULT_THEME)


def lang():
    return _active_lang


# ----------------------------------------------------------------------------
# Strings (EN + TR). Every user-facing literal lives here.
# ----------------------------------------------------------------------------
STRINGS = {
    # --- toolbar ---
    "tb_add": {"en": "\u2795  Add URL", "tr": "\u2795  URL Ekle"},
    "tb_paste": {"en": "\U0001f4cb Paste", "tr": "\U0001f4cb Yap\u0131\u015ft\u0131r"},
    "tb_start": {"en": "\u25bc  Start", "tr": "\u25bc  Ba\u015flat"},
    "tb_stop": {"en": "\u25a0  Stop", "tr": "\u25a0  Durdur"},
    "tb_clear": {"en": "\u2716 Clear", "tr": "\u2716 Temizle"},
    "tb_themes": {"en": "Themes", "tr": "Temalar"},
    "tb_options": {"en": "Options", "tr": "Se\u00e7enekler"},
    "tip_add": {"en": "Add a YouTube link", "tr": "YouTube ba\u011flant\u0131s\u0131 ekle"},
    "tip_paste": {"en": "Paste link from clipboard", "tr": "Panodaki ba\u011flant\u0131y\u0131 yap\u0131\u015ft\u0131r"},
    "tip_start": {"en": "Start downloads", "tr": "\u0130ndirmeleri ba\u015flat"},
    "tip_stop": {"en": "Stop downloads", "tr": "\u0130ndirmeleri durdur"},
    "tip_clear": {"en": "Clear finished items", "tr": "Bitmi\u015f \u00f6\u011feleri temizle"},
    "tip_themes": {"en": "Themes and language", "tr": "Temalar ve dil"},
    "tip_options": {"en": "Options", "tr": "Se\u00e7enekler"},
    "tip_about": {"en": "About", "tr": "Hakk\u0131nda"},
    # --- format bar ---
    "fmt_label": {"en": "Format:", "tr": "Bi\u00e7im:"},
    "fmt_mp4": {"en": "MP4 Video", "tr": "MP4 Video"},
    "fmt_mp3": {"en": "MP3 Audio", "tr": "MP3 Ses"},
    "fmt_quality": {"en": "Quality:", "tr": "Kalite:"},
    "fmt_out": {"en": "Output: output/mp4  +  output/mp3",
                "tr": "\u00c7\u0131kt\u0131: output/mp4  +  output/mp3"},
    "fmt_hint": {"en": "MP4 -> output/mp4  |  MP3 -> output/mp3",
                 "tr": "MP4 -> output/mp4  |  MP3 -> output/mp3"},
    "q_best": {"en": "Best", "tr": "En iyi"},
    # --- list ---
    "list_head": {"en": " List - paste a link, press Start, that's it ",
                  "tr": " Liste - bir ba\u011flant\u0131 yap\u0131\u015ft\u0131r, Ba\u015flat'a bas, bu kadar "},
    "count": {"en": "{n} item(s)", "tr": "{n} \u00f6\u011fe"},
    "empty": {"en": ("\n\nNothing here yet.\n\nPress \"+ Add URL\" or just copy a YouTube link -\n"
                     "it is caught automatically.\nThen press \"Start\".\n\nFiles go to:\n"
                     "  MP4  ->  output\\mp4\\\n  MP3  ->  output\\mp3\\\n"),
              "tr": ("\n\nHen\u00fcz bir \u015fey yok.\n\n\"+ URL Ekle\"ye bas ya da bir YouTube ba\u011flant\u0131s\u0131n\u0131 kopyala -\n"
                     "otomatik yakalan\u0131r.\nArd\u0131ndan \"Ba\u015flat\"a bas.\n\nDosyalar:\n"
                     "  MP4  ->  output\\mp4\\\n  MP3  ->  output\\mp3\\\n")},
    # --- rows ---
    "row_open": {"en": "Open", "tr": "A\u00e7"},
    "st_waiting": {"en": "Waiting", "tr": "Bekliyor"},
    "st_fetching": {"en": "Fetching video info...", "tr": "Video bilgisi al\u0131n\u0131yor..."},
    "st_downloading": {"en": "Downloading... {pct}%  {speed}  {eta} left",
                       "tr": "\u0130ndiriliyor... %{pct}  {speed}  kalan {eta}"},
    "st_converting": {"en": "Converting / merging...",
                      "tr": "D\u00f6n\u00fc\u015ft\u00fcr\u00fcl\u00fcyor / birle\u015ftiriliyor..."},
    "st_done": {"en": "Completed -> {file}", "tr": "Tamamland\u0131 -> {file}"},
    "st_error": {"en": "Error: {err}", "tr": "Hata: {err}"},
    "st_stopped": {"en": "Stopped", "tr": "Durduruldu"},
    "st_retrying": {"en": "Retrying\u2026 {a}/{t} ({why})",
                    "tr": "Tekrar deneniyor\u2026 {a}/{t} ({why})"},
    # --- status bar ---
    "sb_ready": {"en": "Ready", "tr": "Haz\u0131r"},
    "sb_ready_hint": {"en": "Ready. Paste a YouTube link and press Start.",
                      "tr": "Haz\u0131r. Bir YouTube ba\u011flant\u0131s\u0131 yap\u0131\u015ft\u0131r ve Ba\u015flat'a bas."},
    "sb_ffmpeg_ok": {"en": "ffmpeg: found", "tr": "ffmpeg: var"},
    "sb_ffmpeg_missing": {"en": "ffmpeg: MISSING (mp3 will fail)",
                          "tr": "ffmpeg: YOK (mp3 \u00e7al\u0131\u015fmaz)"},
    # --- dialogs (generic) ---
    "dlg_ok": {"en": "  OK  ", "tr": "  Tamam  "},
    "dlg_cancel": {"en": "  Cancel  ", "tr": "  Vazge\u00e7  "},
    "dlg_warning": {"en": "Warning", "tr": "Uyar\u0131"},
    # --- add dialog ---
    "add_title": {"en": "Add URL", "tr": "URL Ekle"},
    "add_prompt": {"en": "Paste the YouTube link below:",
                   "tr": "YouTube ba\u011flant\u0131 adresini yap\u0131\u015ft\u0131r:"},
    "add_quality_note": {"en": "(...k for MP3, ...p for MP4)",
                         "tr": "(MP3 i\u00e7in ...k, MP4 i\u00e7in ...p)"},
    "add_empty": {"en": "Paste a link first.", "tr": "\u00d6nce bir ba\u011flant\u0131 yap\u0131\u015ft\u0131r."},
    "add_notube": {"en": "This doesn't look like a YouTube link.\nIt will still be added and tried.",
                   "tr": "Bu bir YouTube ba\u011flant\u0131s\u0131na benzemiyor.\nYine de eklenip denenecek."},
    # --- options dialog ---
    "opt_title": {"en": "Options", "tr": "Se\u00e7enekler"},
    "opt_folders": {"en": " Output folders ", "tr": " Kay\u0131t klas\u00f6rleri "},
    "opt_mp4": {"en": "MP4 folder:", "tr": "MP4 klas\u00f6r\u00fc:"},
    "opt_mp3": {"en": "MP3 folder:", "tr": "MP3 klas\u00f6r\u00fc:"},
    "opt_folders_note": {"en": "(Folders live under output/ next to the program.)",
                         "tr": "(Klas\u00f6rler program\u0131n yan\u0131ndaki output/ alt\u0131ndad\u0131r.)"},
    "opt_appearance": {"en": " Appearance ", "tr": " G\u00f6r\u00fcn\u00fcm "},
    "opt_theme": {"en": "Theme:", "tr": "Tema:"},
    "opt_lang": {"en": "Language:", "tr": "Dil:"},
    "opt_auto": {"en": "Auto-catch YouTube links from the clipboard (recommended)",
                 "tr": "Panodaki YouTube ba\u011flant\u0131lar\u0131n\u0131 otomatik yakala (\u00f6nerilir)"},
    "opt_parallel": {"en": "Simultaneous downloads:",
                     "tr": "Ayn\u0131 anda indirme say\u0131s\u0131:"},
    "msg_settings_saved": {"en": "Settings saved.", "tr": "Ayarlar kaydedildi."},
    # --- account / cookies (age-restricted videos) ---
    "opt_account": {"en": " YouTube login (age-restricted videos) ",
                    "tr": " YouTube giri\u015fi (ya\u015f s\u0131n\u0131rl\u0131 videolar) "},
    "opt_account_note": {"en": "Most videos need no login. Log in only if a download says "
                               "\"sign in to confirm your age\".",
                         "tr": "\u00c7o\u011fu video i\u00e7in giri\u015f gerekmez. Yaln\u0131zca indirme "
                               "\"ya\u015f\u0131n\u0131 do\u011frulamak i\u00e7in giri\u015f yap\" derse giri\u015f yap."},
    "acc_status_none": {"en": "Status: not logged in", "tr": "Durum: giri\u015f yap\u0131lmad\u0131"},
    "acc_status_browser": {"en": "Status: using {b} cookies ({n} YouTube)",
                           "tr": "Durum: {b} \u00e7erezleri kullan\u0131l\u0131yor ({n} YouTube)"},
    "acc_status_file": {"en": "Status: using cookies.txt ({n} YouTube)",
                        "tr": "Durum: cookies.txt kullan\u0131l\u0131yor ({n} YouTube)"},
    "acc_file": {"en": "cookies.txt\u2026", "tr": "cookies.txt\u2026"},
    "acc_clear": {"en": "Log out", "tr": "\u00c7\u0131k\u0131\u015f yap"},
    "acc_file_title": {"en": "Pick cookies.txt", "tr": "cookies.txt se\u00e7"},
    "msg_cookies_ok": {"en": "{B} cookies loaded ({n} YouTube). Try the download again.",
                       "tr": "{B} \u00e7erezleri y\u00fcklendi ({n} YouTube). \u0130ndirmeyi tekrar dene."},
    "msg_cookies_nologin": {"en": "{B} cookies readable, but no YouTube login found in them. "
                                  "Log into YouTube in {B} first, then retry.",
                            "tr": "{B} \u00e7erezleri okundu ama i\u00e7inde YouTube giri\u015fi yok. "
                                  "\u00d6nce {B} i\u00e7inde YouTube'a giri\u015f yap, sonra tekrar dene."},
    "msg_cookies_fail": {"en": "Could not read {B} cookies ({e}). Close {B} and retry, "
                               "or export a cookies.txt file instead.",
                         "tr": "{B} \u00e7erezleri okunamad\u0131 ({e}). {B} taray\u0131c\u0131s\u0131n\u0131 kapat\u0131p "
                               "tekrar dene ya da cookies.txt aktar."},
    "msg_cookiefile_ok": {"en": "cookies.txt loaded ({n} YouTube cookies). Try the download again.",
                          "tr": "cookies.txt y\u00fcklendi ({n} YouTube \u00e7erezi). \u0130ndirmeyi tekrar dene."},
    "msg_cookiefile_bad": {"en": "That file has no YouTube cookies. Export cookies while "
                                 "logged into YouTube (extensions like \"Get cookies.txt LOCALLY\" can do it).",
                           "tr": "Bu dosyada YouTube \u00e7erezi yok. YouTube'a giri\u015f yapm\u0131\u015fken aktar "
                                 "(\"Get cookies.txt LOCALLY\" gibi eklentiler yapabilir)."},
    "msg_logged_out": {"en": "Logged out. Saved login will no longer be used.",
                       "tr": "\u00c7\u0131k\u0131\u015f yap\u0131ld\u0131. Kay\u0131tl\u0131 giri\u015f art\u0131k kullan\u0131lmayacak."},
    "err_age": {"en": "Age-restricted. Open Options -> Account, log in, then retry.",
                "tr": "Ya\u015f s\u0131n\u0131rl\u0131. Se\u00e7enekler -> Hesap'tan giri\u015f yap\u0131p tekrar dene."},
    "err_tls": {"en": "TLS blocked: pause GoodbyeDPI / VPN / antivirus HTTPS scan, then retry.",
                "tr": "TLS engeli: GoodbyeDPI / VPN / antivir\u00fcs taramas\u0131n\u0131 duraklat\u0131p tekrar dene."},
    "err_tls_tool": {"en": "{tool} seems to alter TLS traffic. Quit it and retry the download.",
                     "tr": "{tool} TLS trafi\u011fini de\u011fi\u015ftiriyor gibi. Onu kapat\u0131p indirmeyi tekrar dene."},
    # --- about ---
    "about_title": {"en": "About", "tr": "Hakk\u0131nda"},
    "about_body": {"en": ("\n\nMediaHuman-style YouTube downloader.\n\n"
                          "MP4 -> output/mp4\nMP3 -> output/mp3\n\n"
                          "Powered by yt-dlp + ffmpeg."),
                   "tr": ("\n\nMediaHuman tarz\u0131 YouTube indirici.\n\n"
                          "MP4 -> output/mp4\nMP3 -> output/mp3\n\n"
                          "G\u00fc\u00e7: yt-dlp + ffmpeg.")},
    # --- paste / add ---
    "paste_title": {"en": "Paste", "tr": "Yap\u0131\u015ft\u0131r"},
    "paste_empty": {"en": "Clipboard is empty.", "tr": "Pano bo\u015f."},
    "paste_added": {"en": "{n} link(s) added. Press Start.",
                    "tr": "{n} ba\u011flant\u0131 eklendi. Ba\u015flat'a bas."},
    "paste_dup": {"en": "These links are already in the list.",
                  "tr": "Bu ba\u011flant\u0131lar zaten listede."},
    "paste_none": {"en": "No YouTube link found in the clipboard.\nCopied text:\n",
                   "tr": "Panoda YouTube ba\u011flant\u0131s\u0131 bulunamad\u0131.\nKopyalanan metin:\n"},
    "dup_title": {"en": "Already listed", "tr": "Zaten listede"},
    "dup_body": {"en": "This link is already in the list.",
                 "tr": "Bu ba\u011flant\u0131 zaten listede."},
    # --- resolve ---
    "pl_added": {"en": "Playlist added: {t} ({n} videos)",
                 "tr": "Liste eklendi: {t} ({n} video)"},
    "pl_empty": {"en": "Playlist is empty.", "tr": "Oynatma listesi bo\u015f."},
    "pl_name": {"en": "Playlist", "tr": "Oynatma listesi"},
    # --- start/stop/clear ---
    "msg_nothing": {"en": "Nothing to start. Add a URL first.",
                    "tr": "Ba\u015flat\u0131lacak bir \u015fey yok. \u00d6nce URL ekle."},
    "msg_running": {"en": "Already running...", "tr": "Zaten \u00e7al\u0131\u015f\u0131yor..."},
    "msg_downloading": {"en": "Downloading... ({n} parallel)",
                        "tr": "\u0130ndiriliyor... ({n} paralel)"},
    "msg_noactive": {"en": "No active download to stop.",
                     "tr": "Durdurulacak indirme yok."},
    "msg_stopping": {"en": "Stopping... (finishes the current step first)",
                     "tr": "Durduruluyor... (\u00f6nce mevcut ad\u0131m biter)"},
    "msg_cleared": {"en": "{n} finished item(s) cleared.",
                    "tr": "{n} bitmi\u015f \u00f6\u011fe temizlendi."},
    "msg_noclear": {"en": "No finished items to clear.",
                    "tr": "Temizlenecek bitmi\u015f \u00f6\u011fe yok."},
    # --- download results ---
    "msg_done": {"en": "Done: {t} -> {d}", "tr": "Bitti: {t} -> {d}"},
    "msg_failed": {"en": "Error: {t} - {e}", "tr": "Hata: {t} - {e}"},
    "err_ffmpeg": {"en": "ffmpeg not found.", "tr": "ffmpeg bulunamad\u0131."},
    "err_private": {"en": "Private video.", "tr": "\u00d6zel (gizli) video."},
    "err_unavail": {"en": "Video unavailable / removed.",
                    "tr": "Video yok / kald\u0131r\u0131lm\u0131\u015f."},
    "msg_caught": {"en": "Caught {n} link(s) from the clipboard. Press Start.",
                   "tr": "Panodan {n} ba\u011flant\u0131 yakaland\u0131. Ba\u015flat'a bas."},
    "msg_alldone": {"en": "All done. ({d}/{t}) Files are in output/.",
                    "tr": "T\u00fcm\u00fc bitti. ({d}/{t}) Dosyalar output/ klas\u00f6r\u00fcnde."},
    "err_open": {"en": "Cannot open", "tr": "A\u00e7\u0131lamad\u0131"},
    "busy_title": {"en": "Busy", "tr": "Me\u015fgul"},
    "busy_body": {"en": "Can't remove an item while it downloads. Press Stop first.",
                  "tr": "\u0130ndirme s\u00fcrerken \u00f6\u011fe silinemez. \u00d6nce Durdur'a bas."},
    "exit_title": {"en": "Exit", "tr": "\u00c7\u0131k\u0131\u015f"},
    "exit_body": {"en": "{n} download(s) running.\nExit anyway?",
                  "tr": "{n} indirme s\u00fcr\u00fcyor.\nYine de \u00e7\u0131k\u0131ls\u0131n m\u0131?"},
    "ff_title": {"en": "ffmpeg missing", "tr": "ffmpeg yok"},
    "ff_body": {"en": ("ffmpeg was not found.\nMP4 merging and MP3 conversion may fail.\n\n"
                       "It is bundled with the .exe normally; if you see this, reinstall."),
                "tr": ("ffmpeg bulunamad\u0131.\nMP4 birle\u015ftirme ve MP3 d\u00f6n\u00fc\u015ft\u00fcrme ba\u015far\u0131s\u0131z olabilir.\n\n"
                       "Normalde .exe ile birlikte gelir; bunu g\u00f6r\u00fcyorsan\u0131z yeniden kurun.")},
    "fatal": {"en": "Fatal error", "tr": "Kritik hata"},
    # --- banner ---
    "banner": {"en": "V-YTDownload\nfree YouTube to MP4 / MP3",
               "tr": "V-YTDownload\n\u00fccretsiz YouTube MP4 / MP3 indirici"},
    # --- themes dialog ---
    "th_title": {"en": "Themes", "tr": "Temalar"},
    "th_intro": {"en": "Choose the look of V-YTDownload. Applies instantly.",
                 "tr": "V-YTDownload g\u00f6r\u00fcn\u00fcm\u00fcn\u00fc se\u00e7. An\u0131nda uygulan\u0131r."},
    "th_aero": {"en": "Windows Vista Aero", "tr": "Windows Vista Aero"},
    "th_aero_d": {"en": "Glossy glass, blue highlights, soft glow. (Default)",
                  "tr": "Parlak cam, mavi vurgular, yumu\u015fak parlama. (Varsay\u0131lan)"},
    "th_win98": {"en": "Windows 98 Classic", "tr": "Windows 98 Classic"},
    "th_win98_d": {"en": "Gray panels, beveled borders, chunky bars. Retro.",
                   "tr": "Gri paneller, kabartma kenarlar, par\u00e7al\u0131 \u00e7ubuklar. Retro."},
    "th_lang": {"en": "Language:", "tr": "Dil:"},
    "lang_en": {"en": "English", "tr": "English"},
    "lang_tr": {"en": "T\u00fcrk\u00e7e", "tr": "T\u00fcrk\u00e7e"},
}


def T(key, **kw):
    table = STRINGS.get(key, {})
    s = table.get(_active_lang, table.get("en", key))
    if kw:
        try:
            s = s.format(**kw)
        except Exception:
            pass
    return s


def theme_label(name):
    return T("th_aero") if name == "aero" else T("th_win98")


# ----------------------------------------------------------------------------
# Preferences (portable: next to the program, fallback to %APPDATA%)
# ----------------------------------------------------------------------------
def _prefs_dir(exe_dir):
    try:
        probe = os.path.join(exe_dir, ".writetest")
        with open(probe, "w") as f:
            f.write("x")
        os.remove(probe)
        return exe_dir
    except Exception:
        appdata = os.environ.get("APPDATA") or os.path.expanduser("~")
        d = os.path.join(appdata, APP_NAME)
        try:
            os.makedirs(d, exist_ok=True)
        except Exception:
            pass
        return d


PREFS = {"theme": DEFAULT_THEME, "lang": DEFAULT_LANG,
         "auto_clip": True, "max_parallel": 2,
         "cookies_source": "none", "cookiefile": ""}

COOKIE_BROWSERS = ["chrome", "edge", "firefox", "brave"]


def prefs_path(exe_dir):
    return os.path.join(_prefs_dir(exe_dir), "settings.json")


def load_prefs(exe_dir):
    global _active_lang, _active_theme
    try:
        with open(prefs_path(exe_dir), "r", encoding="utf-8") as f:
            data = json.load(f)
        if data.get("theme") in THEMES:
            PREFS["theme"] = data["theme"]
        if data.get("lang") in LANGS:
            PREFS["lang"] = data["lang"]
        PREFS["auto_clip"] = bool(data.get("auto_clip", True))
        PREFS["max_parallel"] = max(1, min(3, int(data.get("max_parallel", 2))))
        if data.get("cookies_source") in (["none"] + COOKIE_BROWSERS + ["file"]):
            PREFS["cookies_source"] = data["cookies_source"]
        cf = data.get("cookiefile", "")
        if isinstance(cf, str) and (not cf or os.path.exists(cf)):
            PREFS["cookiefile"] = cf
    except Exception:
        pass
    _active_theme = THEMES[PREFS["theme"]]
    _active_lang = PREFS["lang"]
    return PREFS


def save_prefs(exe_dir):
    try:
        with open(prefs_path(exe_dir), "w", encoding="utf-8") as f:
            json.dump(PREFS, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def apply_theme(name):
    global _active_theme
    _active_theme = THEMES.get(name, THEMES[DEFAULT_THEME])
    PREFS["theme"] = _active_theme.get("key", DEFAULT_THEME)


def set_language(code):
    global _active_lang
    if code in LANGS:
        _active_lang = code
        PREFS["lang"] = code


# ----------------------------------------------------------------------------
# Frozen (PyInstaller) helpers
# ----------------------------------------------------------------------------
def is_frozen():
    return bool(getattr(sys, "frozen", False))


def resource_path(*parts):
    """Path to a bundled read-only resource (works frozen and in dev)."""
    if is_frozen():
        base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, *parts)


def program_dir():
    """Writable program folder: exe dir (frozen) or source dir (dev)."""
    if is_frozen():
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))
