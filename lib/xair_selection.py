"""Detect X-Air Edit's selected channel by the cyan selection frame.

X-Air Edit does not broadcast channel selection over OSC, and its window can be
resized/moved, so fixed template coordinates are unreliable.  This detector
takes a screenshot of the window and finds the cyan vertical frame that
surrounds the selected channel strip.  The strip width is taken from the frame
itself, so it works at any zoom level.
"""

import ctypes
import time

from PIL import Image

try:
    import pyautogui
    import pygetwindow as gw
except ImportError:
    pyautogui = None
    gw = None


class XAirSelection:
    def __init__(self, enabled=True):
        self.enabled = enabled and gw is not None and pyautogui is not None
        self.win = None
        self.hwnd = None
        self.last_index = None
        self._activated = False
        if self.enabled:
            self._find_window()

    def _find_window(self):
        for win in gw.getAllWindows():
            if win.title.startswith('X AIR Edit'):
                self.win = win
                self.hwnd = win._hWnd
                return
        self.enabled = False

    def _capture(self):
        # Activate the window once at startup only; later screenshots are fast
        # and do not steal focus from whatever the user is doing.
        if not self._activated:
            user32 = ctypes.windll.user32
            user32.SetForegroundWindow(self.hwnd)
            time.sleep(0.15)
            self._activated = True
        x0 = max(0, self.win.left)
        y0 = max(0, self.win.top)
        return pyautogui.screenshot(region=(x0, y0, self.win.width, self.win.height))

    def current_index(self):
        """Return 0-based strip index from the cyan selection frame."""
        if not self.enabled or self.win is None:
            return None
        try:
            img = self._capture()
        except Exception:
            return None
        w, h = img.size

        # Sample only 6 scanlines in the strip area instead of ~600 rows.
        # That cuts the pixel work from ~1M to ~9k and removes the lag.
        ys = [int(h * f) for f in (0.45, 0.55, 0.65, 0.75, 0.85, 0.92)]
        px = img.load()
        counts = {}
        for y in ys:
            for x in range(w):
                r, g, b = px[x, y]
                if g > 120 and b > 120 and r < 90 and abs(g - b) < 70:
                    counts[x] = counts.get(x, 0) + 1
        if not counts:
            return None
        tall = [x for x, count in counts.items() if count >= 4]
        if len(tall) < 2:
            return None
        tall.sort()

        # Group adjacent columns into frame lines; pick the two strongest.
        lines = []
        group = [tall[0]]
        for x in tall[1:]:
            if x - group[-1] <= 3:
                group.append(x)
            else:
                lines.append(sum(group) / float(len(group)))
                group = [x]
        lines.append(sum(group) / float(len(group)))
        if len(lines) < 2:
            return None
        lines.sort(key=lambda x: -counts[int(x)])
        left, right = sorted(lines[:2])
        frame_width = right - left
        if frame_width < 10:
            return None
        centre = (left + right) / 2.0
        index = int(round(centre / frame_width)) - 1
        if index < 0:
            index = 0
        self.last_index = index
        return index
