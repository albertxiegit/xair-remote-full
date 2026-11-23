"""Move X-Air Edit's selected-channel frame with arrow keys via PostMessage.

Position is read from the cyan selection frame by XAirSelection, so resizing or
moving the window does not break focus tracking.  Left/Right arrows are used
for the actual move because they select every strip without stealing focus.
"""

import ctypes
import time

try:
    import pygetwindow as gw
except ImportError:
    gw = None

CHANNEL_INDEX = {}
for i in range(1, 17):
    CHANNEL_INDEX['CH %02d' % i] = i - 1
CHANNEL_INDEX['AUX'] = 16
for i in range(1, 5):
    CHANNEL_INDEX['FX SEND %d' % i] = 16 + i

MAX_FOCUS_INDEX = 20  # FX SEND 4; never step into BUS / MAIN LR

VK_LEFT = 0x25
VK_RIGHT = 0x27
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101


class XAirEditFocus:
    def __init__(self, enabled=True):
        self.enabled = enabled and gw is not None
        self.last_group = None
        self.selected_index = None
        self.detector = None

    def window(self):
        if not self.enabled:
            return None
        for win in gw.getAllWindows():
            if win.title.startswith('X AIR Edit'):
                return win
        return None

    def _key(self, hwnd, vk):
        user32 = ctypes.windll.user32
        user32.PostMessageW(hwnd, WM_KEYDOWN, vk, 0)
        time.sleep(0.03)
        user32.PostMessageW(hwnd, WM_KEYUP, vk, 0)
        time.sleep(0.05)

    def _detected_index(self):
        if self.detector is None:
            return None
        try:
            return self.detector.current_index()
        except Exception:
            return None

    def _walk(self, hwnd, delta):
        if not delta:
            return
        key = VK_RIGHT if delta > 0 else VK_LEFT
        for _ in range(abs(delta)):
            self._key(hwnd, key)

    def enforce_limit(self):
        """Pull the frame back if it drifted past FX SEND 4."""
        if not self.enabled:
            return
        win = self.window()
        if win is None:
            return
        try:
            current = self._detected_index()
            if current is None:
                current = self.selected_index
            if current is not None and current > MAX_FOCUS_INDEX:
                self._walk(win._hWnd, MAX_FOCUS_INDEX - current)
                self.selected_index = MAX_FOCUS_INDEX
        except Exception as exc:
            print('Focus limit failed: %s' % exc)

    def select_group(self, group):
        if not self.enabled or group not in CHANNEL_INDEX:
            return False
        win = self.window()
        if win is None:
            print('X-Air Edit window not found')
            return False
        try:
            hwnd = win._hWnd
            current = self._detected_index()
            if current is None:
                current = self.selected_index
            if current is None:
                print('Focus: cannot detect current strip')
                return False
            target = min(CHANNEL_INDEX[group], MAX_FOCUS_INDEX)
            delta = target - current
            self._walk(hwnd, delta)
            self.selected_index = target
        except Exception as exc:
            print('Focus move failed: %s' % exc)
            return False
        self.last_group = group
        print('X-Air Edit focus -> %s (index %d, was %d)' % (
            group, target, current))
        return True
