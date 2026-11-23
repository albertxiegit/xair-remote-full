#!/usr/bin/env python3
"""Try every documented way to force X-Touch Mini into MC mode."""

import time

import mido

name_in = None
name_out = None
for name in mido.get_input_names():
    if 'x-touch mini' in name.lower():
        name_in = name
for name in mido.get_output_names():
    if 'x-touch mini' in name.lower():
        name_out = name
print('input :', name_in)
print('output:', name_out)

inp = mido.open_input(name_in)
out = mido.open_output(name_out)

print('Sending CC127=1 on channels 0..15')
for channel in range(16):
    out.send(mido.Message('control_change', channel=channel, control=127, value=1))
    time.sleep(0.05)

time.sleep(1)
print('Sending CC127=1 on channel 0 again')
out.send(mido.Message('control_change', channel=0, control=127, value=1))

print('Listening 3s for replies (press MC manually now if you like):')
end = time.time() + 3
while time.time() < end:
    for msg in inp.iter_pending():
        print('  <<', msg)
    time.sleep(0.05)

inp.close()
out.close()
