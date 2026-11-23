#!/usr/bin/env python3
"""Test real and synthetic arrow keys in X-Air Edit, step by step."""

import ctypes
import ctypes.wintypes
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pyautogui
import pygetwindow as gw
from PIL import Image, ImageDraw

user32 = ctypes.windll.user32
win = next(w for w in gw.getAllWindows() if w.title.startswith('X AIR Edit'))
hwnd = win._hWnd
shots = []


def shot(label):
    time.sleep(0.3)
    img = pyautogui.screenshot().crop((100, 55, 820, 470))
    tile = Image.new('RGB', (720, 435), 'white')
    tile.paste(img, (0, 0))
    ImageDraw.Draw(tile).text((10, 410), label, fill=(255, 0, 0))
    shots.append(tile)


user32.SetForegroundWindow(hwnd)
time.sleep(0.4)
pyautogui.click(win.left + 28, win.top + 428)
shot('click CH01')
pyautogui.press('right')
shot('real RIGHT x1')
pyautogui.press('right')
shot('real RIGHT x2')

# Leave foreground, then try PostMessage key.
codebuddy = next(w for w in gw.getAllWindows() if 'CodeBuddy' in w.title)
user32.SetForegroundWindow(codebuddy._hWnd)
time.sleep(0.3)
user32.PostMessageW(hwnd, 0x0100, 0x27, 0)
time.sleep(0.03)
user32.PostMessageW(hwnd, 0x0101, 0x27, 0)
time.sleep(0.3)
user32.SetForegroundWindow(hwnd)
shot('PostMessage RIGHT')

montage = Image.new('RGB', (1440, 870), 'white')
for i, tile in enumerate(shots):
    montage.paste(tile, ((i % 2) * 720, (i // 2) * 435))
montage.save('keys_test.png')
print('saved')
