"""Open Sift in its own Mac window."""

import threading
from pathlib import Path

from sift.review import make_handler

ICON = Path(__file__).resolve().parent.parent / "assets" / "AppIcon.png"
_last_mouse_down = {"event": None}
_drag_monitor = False
_arrow_monitor = False
_text_entry = {"on": False}
_theme_observer = None
_LEFT_ARROW = 123
_RIGHT_ARROW = 124

# Match the page background in sift/review.py.
_LIGHT_BG = (246 / 255, 238 / 255, 233 / 255, 1.0)
_DARK_BG = (22 / 255, 18 / 255, 16 / 255, 1.0)


def interface_style_is_dark(style: str | None) -> bool:
    return style == "Dark"


def background_hex(dark: bool) -> str:
    return "#161210" if dark else "#f6eee9"


def background_rgba(dark: bool) -> tuple[float, float, float, float]:
    return _DARK_BG if dark else _LIGHT_BG


def arrow_direction(key_code: int) -> int | None:
    """Mac key codes for Left and Right. None means the key does not change photos."""
    if key_code == _LEFT_ARROW:
        return -1
    if key_code == _RIGHT_ARROW:
        return 1
    return None


def current_interface_is_dark() -> bool:
    from Foundation import NSUserDefaults

    style = NSUserDefaults.standardUserDefaults().stringForKey_("AppleInterfaceStyle")
    return interface_style_is_dark(style)


class DesktopApi:
    def choose_folder(self) -> str:
        import webview

        window = webview.windows[0] if webview.windows else None
        if window is None:
            return ""
        choice = window.create_file_dialog(webview.FileDialog.FOLDER)
        if not choice:
            return ""
        return str(choice[0])

    def begin_drag(self) -> None:
        """Drag the window from a click on the page background."""
        from PyObjCTools import AppHelper

        AppHelper.callAfter(_drag_from_last_mouse_down)

    def set_typing(self, on: bool) -> None:
        """Keep arrow keys in a text field instead of changing photos."""
        _text_entry["on"] = bool(on)


def open_window(db_path, port: int = 8765) -> None:
    import webview
    from http.server import ThreadingHTTPServer

    try:
        server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(db_path))
    except OSError:
        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(db_path))
        port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{port}"
    print(f"Sift window at {url}", flush=True)
    window = webview.create_window(
        "Sift",
        url,
        width=1180,
        height=800,
        min_size=(860, 560),
        js_api=DesktopApi(),
        background_color=background_hex(current_interface_is_dark()),
    )
    window.events.shown += _schedule_chrome
    window.events.loaded += _schedule_chrome
    try:
        webview.start(gui="cocoa", func=_apply_icon)
    finally:
        server.shutdown()
        server.server_close()


def _schedule_chrome() -> None:
    from PyObjCTools import AppHelper

    AppHelper.callAfter(_apply_live_chrome)


def _apply_live_chrome() -> None:
    import webview

    if not webview.windows:
        return
    native = webview.windows[0].native
    if native is None:
        return
    apply_borderless_chrome(native)
    _apply_system_appearance(native)
    _extend_page_under_titlebar(native)
    _install_background_drag(native)
    _install_arrow_keys(native)
    _watch_appearance()
    _apply_icon()


def apply_borderless_chrome(window) -> None:
    """Hide the title bar like Arc, and leave the traffic-light buttons visible.

    pywebview's frameless flag hides those buttons, so this stays a titled window.
    """
    from AppKit import (
        NSClosableWindowMask,
        NSColor,
        NSFullSizeContentViewWindowMask,
        NSMiniaturizableWindowMask,
        NSTitlebarSeparatorStyleNone,
        NSTitledWindowMask,
        NSWindowCloseButton,
        NSWindowMiniaturizeButton,
        NSWindowTitleHidden,
        NSWindowZoomButton,
    )

    window.setStyleMask_(
        window.styleMask()
        | NSTitledWindowMask
        | NSClosableWindowMask
        | NSMiniaturizableWindowMask
        | NSFullSizeContentViewWindowMask
    )
    window.setTitleVisibility_(NSWindowTitleHidden)
    window.setTitlebarAppearsTransparent_(True)
    window.setTitlebarSeparatorStyle_(NSTitlebarSeparatorStyleNone)
    window.setMovableByWindowBackground_(True)
    _paint_window_background(window)
    content = window.contentView()
    theme = content.superview() if content is not None else None
    if theme is not None:
        for view in theme.subviews():
            name = view.className() if view.respondsToSelector_("className") else ""
            if "Titlebar" in str(name) and view.respondsToSelector_("setBackgroundColor:"):
                view.setBackgroundColor_(NSColor.clearColor())
    for kind in (NSWindowCloseButton, NSWindowMiniaturizeButton, NSWindowZoomButton):
        button = window.standardWindowButton_(kind)
        if button is not None:
            button.setHidden_(False)


def _paint_window_background(window) -> None:
    from AppKit import NSColor

    red, green, blue, alpha = background_rgba(current_interface_is_dark())
    window.setBackgroundColor_(NSColor.colorWithSRGBRed_green_blue_alpha_(red, green, blue, alpha))


def _apply_system_appearance(window) -> None:
    """Follow the Mac light or dark setting, including the page behind the buttons."""
    from AppKit import NSAppearance, NSAppearanceNameAqua, NSAppearanceNameDarkAqua

    name = NSAppearanceNameDarkAqua if current_interface_is_dark() else NSAppearanceNameAqua
    appearance = NSAppearance.appearanceNamed_(name)
    window.setAppearance_(appearance)
    view = window.contentView()
    if view is not None and view.respondsToSelector_("setAppearance:"):
        view.setAppearance_(appearance)
    _paint_window_background(window)


def _refresh_appearance() -> None:
    import webview

    if not webview.windows:
        return
    native = webview.windows[0].native
    if native is not None:
        _apply_system_appearance(native)


def _watch_appearance() -> None:
    global _theme_observer
    if _theme_observer is not None:
        return
    from Foundation import NSDistributedNotificationCenter, NSObject

    class ThemeObserver(NSObject):
        def themeChanged_(self, _notification) -> None:
            from PyObjCTools import AppHelper

            AppHelper.callAfter(_refresh_appearance)

    observer = ThemeObserver.alloc().init()
    NSDistributedNotificationCenter.defaultCenter().addObserver_selector_name_object_(
        observer,
        "themeChanged:",
        "AppleInterfaceThemeChangedNotification",
        None,
    )
    _theme_observer = observer


def _extend_page_under_titlebar(window) -> None:
    from AppKit import NSEdgeInsetsMake

    view = window.contentView()
    if view is None:
        return
    if view.respondsToSelector_("_setAutomaticallyAdjustsContentInsets:"):
        view._setAutomaticallyAdjustsContentInsets_(False)
    if view.respondsToSelector_("setObscuredContentInsets:"):
        view.setObscuredContentInsets_(NSEdgeInsetsMake(0, 0, 0, 0))
    if view.respondsToSelector_("_setTopContentInset:"):
        view._setTopContentInset_(0)


def _install_background_drag(window) -> None:
    global _drag_monitor
    if _drag_monitor:
        return
    from AppKit import NSEvent, NSLeftMouseDownMask

    def remember(event):
        try:
            if event.window() != window:
                return event
            _last_mouse_down["event"] = event
            point = event.locationInWindow()
            view = window.contentView()
            height = view.frame().size.height if view is not None else 0
            from_top = height - point.y
            # Traffic lights sit in the top-left. The rest of that band drags the window.
            if 0 <= from_top <= 36 and point.x > 78:
                window.performWindowDragWithEvent_(event)
                return None
        except Exception:
            return event
        return event

    NSEvent.addLocalMonitorForEventsMatchingMask_handler_(NSLeftMouseDownMask, remember)
    _drag_monitor = True


def _ignore_js(_result, _error) -> None:
    return None


def _run_arrow(direction: int) -> None:
    import webview

    if not webview.windows:
        return
    native = webview.windows[0].native
    view = native.contentView() if native is not None else None
    if view is None or not view.respondsToSelector_("evaluateJavaScript:completionHandler:"):
        return
    view.evaluateJavaScript_completionHandler_("siftArrow(%d);" % int(direction), _ignore_js)


def _install_arrow_keys(window) -> None:
    """Left and Right never reach the page; macOS uses them to move focus."""
    global _arrow_monitor
    if _arrow_monitor:
        return
    from AppKit import (
        NSAlternateKeyMask,
        NSCommandKeyMask,
        NSControlKeyMask,
        NSEvent,
        NSKeyDownMask,
    )
    from PyObjCTools import AppHelper

    command_keys = NSCommandKeyMask | NSControlKeyMask | NSAlternateKeyMask

    def on_key(event):
        try:
            if event.window() != window or _text_entry["on"]:
                return event
            if event.modifierFlags() & command_keys:
                return event
            direction = arrow_direction(event.keyCode())
            if direction is None:
                return event
            AppHelper.callAfter(_run_arrow, direction)
        except Exception:
            return event
        return None

    NSEvent.addLocalMonitorForEventsMatchingMask_handler_(NSKeyDownMask, on_key)
    _arrow_monitor = True


def _drag_from_last_mouse_down() -> None:
    event = _last_mouse_down.get("event")
    if event is None:
        return
    window = event.window()
    if window is not None and window.respondsToSelector_("performWindowDragWithEvent:"):
        window.performWindowDragWithEvent_(event)


def _apply_icon() -> None:
    if not ICON.is_file():
        return
    from AppKit import NSApplication, NSImage

    image = NSImage.alloc().initWithContentsOfFile_(str(ICON))
    if image is not None:
        NSApplication.sharedApplication().setApplicationIconImage_(image)


def main_app(db_path, port: int = 8765) -> None:
    open_window(db_path, port)
