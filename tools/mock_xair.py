#!/usr/bin/env python3
"""Minimal local XR18 simulator for testing the bridge without the mixer.

Listens on UDP 10024, answers /xinfo, stores parameter values and replays
queries.  Run `python tools/mock_xair.py` in one terminal, then
`python xair-remote.py 127.0.0.1` in another.
"""

import queue
import socket
import sys
import threading

from pythonosc.osc_message import OscMessage
from pythonosc.osc_message_builder import OscMessageBuilder


class MockXAir:
    def __init__(self, host='127.0.0.1', port=10024):
        self.host = host
        self.port = port
        self.values = {}
        self.clients = set()
        self.inbox = queue.Queue()
        self._running = False
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.sock.bind((host, port))
        self.sock.settimeout(0.2)
        self.thread = threading.Thread(target=self._loop, daemon=True)

    def start(self):
        self._running = True
        self.thread.start()

    def stop(self):
        self._running = False
        self.sock.close()

    def _send(self, addr, value, target):
        builder = OscMessageBuilder(address=addr)
        values = value if isinstance(value, list) else [value]
        for item in values:
            builder.add_arg(item)
        try:
            self.sock.sendto(builder.build().dgram, target)
        except OSError:
            pass

    def _broadcast(self, addr, value, exclude=None):
        for client in list(self.clients):
            if client != exclude:
                self._send(addr, value, client)

    def _loop(self):
        while self._running:
            try:
                data, client = self.sock.recvfrom(4096)
            except socket.timeout:
                continue
            except OSError:
                break
            self.clients.add(client)
            try:
                msg = OscMessage(data)
            except Exception:
                continue
            if msg.address == '/xinfo':
                self._send('/xinfo', [self.host, self.port, 'XR18', '1.17'], client)
                continue
            if msg.address in ('/xremote', '/xremotenfb'):
                continue
            if not msg.params:
                value = self.values.get(msg.address, 0.0)
                self._send(msg.address, value, client)
            else:
                self.values[msg.address] = msg.params[0]
                self._broadcast(msg.address, msg.params[0], exclude=client)

    def inject(self, addr, value):
        """Simulate a change made on the mixer itself."""
        self.values[addr] = value
        self._broadcast(addr, value)


def main():
    mock = MockXAir()
    mock.start()
    print('Mock XR18 listening on udp %s:%d' % (mock.host, mock.port))
    print('Now run: python xair-remote.py 127.0.0.1')
    print('Type "ADDRESS VALUE" to simulate a mixer-side change, e.g. /ch/01/mix/fader 0.7')
    print('Type "quit" to exit.')
    try:
        while True:
            line = sys.stdin.readline()
            if not line or line.strip() == 'quit':
                break
            parts = line.split()
            if len(parts) != 2:
                continue
            addr, raw = parts
            try:
                value = float(raw)
                if value.is_integer() and '.' not in raw:
                    value = int(value)
            except ValueError:
                value = raw
            mock.inject(addr, value)
            print('Injected %s = %s' % (addr, value))
    except KeyboardInterrupt:
        pass
    finally:
        mock.stop()


if __name__ == '__main__':
    main()
