#!/usr/bin/env python3
"""Verify that the selection detector follows arrow-key moves."""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.xair_selection import XAirSelection
from lib.xairedit_focus import XAirEditFocus

detector = XAirSelection()
print('initial index:', detector.current_index())
focus = XAirEditFocus()
focus.select_group('CH 05')
time.sleep(0.5)
print('after CH05:', detector.current_index())
focus.select_group('CH 09')
time.sleep(0.5)
print('after CH09:', detector.current_index())
