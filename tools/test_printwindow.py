#!/usr/bin/env python3
"""Capture the X-Air Edit window even when it is behind other windows."""

import ctypes
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygetwindow as gw
from PIL import Image

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
win = next(w for w in gw.getAllWindows() if w.title.startswith('X AIR Edit'))
hwnd = win._hWnd
left, top, w, h = win.left, win.top, win.width, win.height

hdc = user32.GetWindowDC(hwnd)
memdc = gdi32.CreateCompatibleDC(hdc)
bmp = gdi32.CreateCompatibleBitmap(hdc, w, h)
gdi32.SelectObject(memdc, bmp)
ok = user32.PrintWindow(hwnd, memdc, 2)
print('PrintWindow ok:', ok)

class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [('biSize', ctypes.c_ulong), ('biWidth', ctypes.c_long),
                ('biHeight', ctypes.c_long), ('biPlanes', ctypes.c_ushort),
                ('biBitCount', ctypes.c_ushort), ('biCompression', ctypes.c_ulong),
                ('biSizeImage', ctypes.c_ulong), ('biXPelsPerMeter', ctypes.c_long),
                ('biYPelsPerMeter', ctypes.c_long), ('biClrUsed', ctypes.c_ulong),
                ('biClrImportant', ctypes.c_ulong)]

bi = BITMAPINFOHEADER()
bi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
bi.biWidth = w
bi.biHeight = -h
bi.biPlanes = 1
bi.biBitCount = 24
bi.biCompression = 0
size = w * h * 3
buf = ctypes.create_string_buffer(size)
gdi32.GetDIBits(memdc, bmp, 0, h, buf, ctypes.byref(bi), 0)
img = Image.frombuffer('RGB', (w, h), buf.raw, 'raw', 'BGR', 0, 1)
img.save('printwindow_test.png')
print('saved', img.size)
for obj in (bmp, memdc):
    try:
        gdi32.DeleteObject(obj)
    except Exception:
        pass
user32.ReleaseDC(hwnd, hdc)
