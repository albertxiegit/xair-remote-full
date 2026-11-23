#!/usr/bin/env python3
"""Click CH01..CH08 and make a montage showing which strip actually gets selected."""

import ctypes
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pyautogui
from PIL import Image, ImageDraw

from lib.xairedit_focus import XAirEditFocus

focus = XAirEditFocus()
win = focus.window()
ctypes.windll.user32.SetForegroundWindow(win._hWnd)
time.sleep(0.3)
tiles = []
for i in range(1, 9):
    group = 'CH %02d' % i
    focus.select_group(group)
    time.sleep(0.25)
    shot = pyautogui.screenshot().crop((100, 60, 820, 470))
    tile = Image.new('RGB', (720, 430), 'white')
    tile.paste(shot, (0, 0))
    ImageDraw.Draw(tile).text((10, 405), group, fill=(255, 0, 0))
    tiles.append(tile)
montage = Image.new('RGB', (1440, 1720), 'white')
for idx, tile in enumerate(tiles):
    montage.paste(tile, ((idx % 2) * 720, (idx // 2) * 430))
montage.save('focus_scan.png')
print('saved focus_scan.png')
