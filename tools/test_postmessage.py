#!/usr/bin/env python3
"""Test clicking X-Air Edit without bringing it to the foreground."""

import ctypes
import time

import pyautogui
import pygetwindow as gw

user32 = ctypes.windll.user32
win = next(w for w in gw.getAllWindows() if w.title.startswith('X AIR Edit'))
hwnd = win._hWnd


def foreground_title():
    fg = user32.GetForegroundWindow()
    for w in gw.getAllWindows():
        if w._hWnd == fg:
            return w.title
    return hex(fg)


x_screen = win.left + 28 + 2 * 62
y_screen = win.top + 428
point = ctypes.wintypes.POINT(x_screen, y_screen) if hasattr(ctypes, 'wintypes') else None
if point is None:
    import ctypes.wintypes as wintypes
    point = wintypes.POINT(x_screen, y_screen)
user32.ScreenToClient(hwnd, ctypes.byref(point))
lparam = (point.y << 16) | (point.x & 0xFFFF)
print('before foreground:', foreground_title())
print('posting click at client', point.x, point.y)
user32.PostMessageW(hwnd, 0x0201, 1, lparam)
time.sleep(0.05)
user32.PostMessageW(hwnd, 0x0202, 0, lparam)
time.sleep(0.8)
print('after foreground:', foreground_title())
pyautogui.screenshot().save('postmessage_test.png')
