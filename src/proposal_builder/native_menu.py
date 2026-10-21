"""Right-click menu in the native window (spelling suggestions, cut / copy / paste).

pywebview turns WebView2's built-in context menu on only in debug mode. install() wraps pywebview's
GUI initialization so that, once its Edge backend is loaded and before any window exists, each new
browser control switches the menu back on. Developer tools and browser shortcut keys stay off.
The page script in widgets.CONTEXT_MENU_JS hides the menu outside text fields.

install() must run in the window process: NiceGUI opens the window in a child process, which
imports this package's __main__ (or the frozen launcher) before it starts the window.
"""

from __future__ import annotations

import sys

_MARK = "_pb_context_menu"


def install() -> None:
    if sys.platform != "win32":
        return
    try:
        import webview
    except Exception:  # noqa: BLE001  pywebview missing: browser mode only
        return
    init = getattr(webview, "initialize", None)
    if init is None or getattr(init, _MARK, False):
        return

    def initialize(*args, **kwargs):
        gui = init(*args, **kwargs)
        try:
            _patch_edge()
        except Exception:  # noqa: BLE001  never stop the window from opening
            pass
        return gui

    setattr(initialize, _MARK, True)
    webview.initialize = initialize


def _patch_edge() -> None:
    mod = sys.modules.get("webview.platforms.edgechromium")
    if mod is None:
        return
    cls = mod.EdgeChrome
    ready = cls.on_webview_ready
    if getattr(ready, _MARK, False):
        return

    def on_webview_ready(self, sender, args):
        ready(self, sender, args)
        try:
            sender.CoreWebView2.Settings.AreDefaultContextMenusEnabled = True
        except Exception:  # noqa: BLE001  initialization failed; pywebview reports it
            pass

    setattr(on_webview_ready, _MARK, True)
    cls.on_webview_ready = on_webview_ready
