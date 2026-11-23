#!/usr/bin/env python3
"""Test moving X-Air Edit channel selection with arrow keys via PostMessage."""

import ctypes
import ctypes.wintypes
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pyautogui

from lib.xairedit_focus import XAirEditFocus

focus = XAirEditFocus()
win = focus.window()
focus.select_group('CH 01')
time.sleep(0.3)
hwnd = win._hWnd
user32 = ctypes.windll.user32
VK_RIGHT = 0x27
user32.PostMessageW(hwnd, 0x0100, VK_RIGHT, 0)
time.sleep(0.03)
user32.PostMessageW(hwnd, 0x0101, VK_RIGHT, 0)
time.sleep(0.4)
ctypes.windll.user32.SetForegroundWindow(hwnd)
time.sleep(0.3)
pyautogui.screenshot().crop((100, 60, 820, 470)).save('arrow_test.png')
print('saved')
