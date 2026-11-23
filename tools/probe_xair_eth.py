#!/usr/bin/env python3
"""Broadcast /xinfo on a specific local interface (e.g. direct Ethernet)."""

import socket
import sys

LOCAL_IP = sys.argv[1] if len(sys.argv) > 1 else '169.254.91.188'
BROADCAST = sys.argv[2] if len(sys.argv) > 2 else '169.254.255.255'

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, True)
sock.bind((LOCAL_IP, 0))
sock.settimeout(4)
sock.sendto(b'/xinfo\0\0', (BROADCAST, 10024))
print('Broadcast /xinfo from %s to %s' % (LOCAL_IP, BROADCAST))
try:
    while True:
        data, addr = sock.recvfrom(512)
        print('Reply from %s:%d -> %r' % (addr[0], addr[1], data[:160]))
except socket.timeout:
    print('No X-Air reply within 4s')
finally:
    sock.close()
