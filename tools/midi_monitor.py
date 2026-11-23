#!/usr/bin/env python3
"""Print every MIDI message coming from the X-Touch Mini.

Run this while pressing buttons/turning knobs to determine the active mode.
MC-mode notes are 32-45/84-95; standard-mode messages are different.
"""

import time

import mido

MC_NOTES = {32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45,
            84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95}
MC_CC = set(range(16, 24)) | set(range(48, 56))

for name in mido.get_input_names():
    if 'x-touch mini' not in name.lower():
        continue
    print('Listening to: %s' % name)
    with mido.open_input(name) as port:
        for msg in port:
            stamp = time.strftime('%H:%M:%S')
            note = getattr(msg, 'note', None)
            control = getattr(msg, 'control', None)
            if note is not None:
                hint = 'MC' if note in MC_NOTES else 'NOT-MC'
                print('%s %s note=%d vel=%d  [%s]' % (stamp, msg.type, note,
                                                     getattr(msg, 'velocity', 0), hint))
            elif control is not None:
                hint = 'MC' if control in MC_CC else 'NOT-MC'
                print('%s %s cc=%d val=%d  [%s]' % (stamp, msg.type, control,
                                                   msg.value, hint))
            else:
                print('%s %s' % (stamp, msg))
