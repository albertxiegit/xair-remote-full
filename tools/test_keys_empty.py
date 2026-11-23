#!/usr/bin/env python3
"""Verify arrow keys can select empty/unassigned channels."""

import ctypes
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pyautogui
import pygetwindow as gw

user32 = ctypes.windll.user32
win = next(w for w in gw.getAllWindows() if w.title.startswith('X AIR Edit'))
hwnd = win._hWnd
user32.SetForegroundWindow(hwnd)
time.sleep(0.3)
pyautogui.click(win.left + 28, win.top + 428)  # CH01
time.sleep(0.2)
for _ in range(4):
    user32.PostMessageW(hwnd, 0x0100, 0x27, 0)
    time.sleep(0.03)
    user32.PostMessageW(hwnd, 0x0101, 0x27, 0)
    time.sleep(0.08)
time.sleep(0.4)
pyautogui.screenshot().crop((100, 55, 820, 470)).save('keys_empty.png')
print('saved')
