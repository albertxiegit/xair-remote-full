#!/usr/bin/env python3
"""Select CH05 with real click, then CH03 with PostMessage, and screenshot."""

import ctypes
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pyautogui
import pygetwindow as gw

from lib.xairedit_focus import XAirEditFocus

user32 = ctypes.windll.user32
import ctypes.wintypes as wintypes

win = next(w for w in gw.getAllWindows() if w.title.startswith('X AIR Edit'))
XAirEditFocus().select_group('CH 05')
time.sleep(0.4)
hwnd = win._hWnd
x_screen = win.left + 28 + 2 * 62
y_screen = win.top + 428
point = wintypes.POINT(x_screen, y_screen)
user32.ScreenToClient(hwnd, ctypes.byref(point))
lparam = (point.y << 16) | (point.x & 0xFFFF)
user32.PostMessageW(hwnd, 0x0201, 1, lparam)
time.sleep(0.05)
user32.PostMessageW(hwnd, 0x0202, 0, lparam)
time.sleep(0.8)
pyautogui.screenshot().save('postmessage_test2.png')
print('done')
