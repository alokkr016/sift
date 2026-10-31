import unittest

from AppKit import (
    NSApplication,
    NSBackingStoreBuffered,
    NSClosableWindowMask,
    NSFullSizeContentViewWindowMask,
    NSMakeRect,
    NSMiniaturizableWindowMask,
    NSResizableWindowMask,
    NSTitlebarSeparatorStyleNone,
    NSTitledWindowMask,
    NSWindow,
    NSWindowCloseButton,
    NSWindowMiniaturizeButton,
    NSWindowTitleHidden,
    NSWindowZoomButton,
)

from sift.desktop import apply_borderless_chrome, arrow_direction, background_hex, interface_style_is_dark
from sift.review import PAGE


class BorderlessWindowTest(unittest.TestCase):
    def test_chrome_hides_the_title_and_keeps_the_buttons(self):
        NSApplication.sharedApplication()
        mask = (
            NSTitledWindowMask
            | NSClosableWindowMask
            | NSMiniaturizableWindowMask
            | NSResizableWindowMask
        )
        window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(0, 0, 480, 320), mask, NSBackingStoreBuffered, False
        )
        window.setTitle_("Sift")
        apply_borderless_chrome(window)
        try:
            self.assertTrue(window.titlebarAppearsTransparent())
            self.assertEqual(window.titleVisibility(), NSWindowTitleHidden)
            self.assertEqual(window.titlebarSeparatorStyle(), NSTitlebarSeparatorStyleNone)
            self.assertTrue(window.styleMask() & NSFullSizeContentViewWindowMask)
            self.assertTrue(window.styleMask() & NSTitledWindowMask)
            self.assertTrue(window.styleMask() & NSClosableWindowMask)
            self.assertTrue(window.isMovableByWindowBackground())
            for kind in (NSWindowCloseButton, NSWindowMiniaturizeButton, NSWindowZoomButton):
                button = window.standardWindowButton_(kind)
                if button is not None:
                    self.assertFalse(button.isHidden())
        finally:
            window.close()

    def test_light_and_dark_backgrounds_match_the_page(self):
        self.assertEqual(background_hex(False), "#f6eee9")
        self.assertEqual(background_hex(True), "#161210")
        self.assertIn("--bg: #f6eee9", PAGE)
        self.assertIn("--bg: #161210", PAGE)
        self.assertIn("prefers-color-scheme: dark", PAGE)
        self.assertIn('id="prev"', PAGE)
        self.assertIn('id="next"', PAGE)
        self.assertIn("ArrowLeft", PAGE)
        self.assertIn("ArrowRight", PAGE)
        self.assertIn("function siftArrow", PAGE)
        self.assertEqual(arrow_direction(123), -1)
        self.assertEqual(arrow_direction(124), 1)
        self.assertIsNone(arrow_direction(36))
        self.assertTrue(interface_style_is_dark("Dark"))
        self.assertFalse(interface_style_is_dark(None))
        self.assertFalse(interface_style_is_dark("Light"))


if __name__ == "__main__":
    unittest.main()
