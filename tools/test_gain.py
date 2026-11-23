#!/usr/bin/env python3
"""Verify that /headamp/01/gain can be set and sticks on the XR18."""

import socket
import time

from pythonosc.osc_message import OscMessage
from pythonosc.osc_message_builder import OscMessageBuilder

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('', 0))
sock.settimeout(1.5)
MIXER = ('169.254.53.169', 10024)


def send(addr, value=None):
    builder = OscMessageBuilder(address=addr)
    if value is not None:
        builder.add_arg(value)
    sock.sendto(builder.build().dgram, MIXER)


def query(addr):
    send(addr)
    try:
        msg = OscMessage(sock.recv(512))
        return msg.params[0] if msg.params else None
    except socket.timeout:
        return 'TIMEOUT'


before = query('/headamp/01/gain')
print('before:', before)
if isinstance(before, float):
    trial = min(1.0, before + 0.1)
    send('/headamp/01/gain', trial)
    time.sleep(0.3)
    after = query('/headamp/01/gain')
    print('set to:', trial, 'read back:', after)
    send('/headamp/01/gain', before)
    print('restored to:', before)
else:
    print('cannot read gain, skip write test')
sock.close()
