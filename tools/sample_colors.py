#!/usr/bin/env python3
"""Print header colors of every channel strip in X-Air Edit."""

import ctypes
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygetwindow as gw
from PIL import Image

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
win = next(w for w in gw.getAllWindows() if w.title.startswith('X AIR Edit'))
hwnd = win._hWnd
w, h = win.width, win.height
hdc = user32.GetWindowDC(hwnd)
memdc = gdi32.CreateCompatibleDC(hdc)
bmp = gdi32.CreateCompatibleBitmap(hdc, w, h)
gdi32.SelectObject(memdc, bmp)
user32.PrintWindow(hwnd, memdc, 2)


class BIH(ctypes.Structure):
    _fields_ = [('biSize', ctypes.c_ulong), ('biWidth', ctypes.c_long),
                ('biHeight', ctypes.c_long), ('biPlanes', ctypes.c_ushort),
                ('biBitCount', ctypes.c_ushort), ('biCompression', ctypes.c_ulong),
                ('biSizeImage', ctypes.c_ulong), ('biXPelsPerMeter', ctypes.c_long),
                ('biYPelsPerMeter', ctypes.c_long), ('biClrUsed', ctypes.c_ulong),
                ('biClrImportant', ctypes.c_ulong)]


bi = BIH()
bi.biSize = ctypes.sizeof(BIH)
bi.biWidth = w
bi.biHeight = -h
bi.biPlanes = 1
bi.biBitCount = 24
buf = ctypes.create_string_buffer(w * h * 3)
gdi32.GetDIBits(memdc, bmp, 0, h, buf, ctypes.byref(bi), 0)
img = Image.frombuffer('RGB', (w, h), buf.raw, 'raw', 'BGR', 0, 1)
for i in range(12):
    x = 28 + i * 62
    y = 428 + 15
    print(i + 1, img.getpixel((x, y)), 'top', img.getpixel((x, y - 12)))
gdi32.DeleteObject(bmp)
gdi32.DeleteObject(memdc)
user32.ReleaseDC(hwnd, hdc)
