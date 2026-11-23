#!/usr/bin/env python3
"""Select a channel and screenshot X-Air Edit to verify the frame position."""

import ctypes
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pyautogui
import pygetwindow as gw

from lib.xairedit_focus import XAirEditFocus

group = sys.argv[1] if len(sys.argv) > 1 else 'CH 05'
focus = XAirEditFocus()
print('select', group, focus.select_group(group))
time.sleep(0.3)
win = focus.window()
ctypes.windll.user32.SetForegroundWindow(win._hWnd)
time.sleep(0.4)
pyautogui.screenshot().save('focus_check.png')
print('saved')
