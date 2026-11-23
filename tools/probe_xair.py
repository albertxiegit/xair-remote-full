#!/usr/bin/env python3
"""Broadcast /xinfo and print any X-Air mixer that answers."""

import socket
import sys

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, True)
sock.settimeout(4)
sock.sendto(b'/xinfo\0\0', ('<broadcast>', 10024))
print('Broadcast /xinfo sent')
try:
    while True:
        data, addr = sock.recvfrom(512)
        print('Reply from %s:%d -> %r' % (addr[0], addr[1], data[:120]))
except socket.timeout:
    print('No X-Air reply within 4s')
    sys.exit(1)
finally:
    sock.close()
