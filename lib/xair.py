"""OSC transport for X-Air mixers (forked from peterdikant/xair-remote)."""

import socket
import threading
import time

from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_message import OscMessage
from pythonosc.osc_message_builder import OscMessageBuilder
from pythonosc.osc_server import BlockingOSCUDPServer


class OSCClientServer(BlockingOSCUDPServer):
    def __init__(self, address, dispatcher):
        super().__init__(('', 0), dispatcher, family=socket.AF_INET)
        self.xr_address = address

    def send_message(self, address, value=None):
        builder = OscMessageBuilder(address=address)
        if value is None:
            values = []
        elif isinstance(value, list):
            values = value
        else:
            values = [value]
        for val in values:
            builder.add_arg(val)
        self.socket.sendto(builder.build().dgram, self.xr_address)


class XAirClient:
    """Sends OSC commands to the mixer and forwards every state broadcast."""

    _CONNECT_TIMEOUT = 0.5
    _REFRESH_TIMEOUT = 5
    XAIR_PORT = 10024

    def __init__(self, address, state):
        self.state = state
        dispatcher = Dispatcher()
        dispatcher.set_default_handler(self.msg_handler)
        self.server = OSCClientServer((address, self.XAIR_PORT), dispatcher)
        self.info_response = []
        worker = threading.Thread(target=self.run_server, daemon=True)
        worker.start()

    def run_server(self):
        self.server.serve_forever()

    def msg_handler(self, addr, *data):
        if addr == '/xinfo':
            self.info_response = list(data)
            return
        if not data:
            return
        self.state.received_osc(addr, data[0])

    def validate_connection(self):
        self.send('/xinfo')
        time.sleep(self._CONNECT_TIMEOUT)
        if not self.info_response:
            raise RuntimeError('No OSC answer from mixer at %s' % (self.server.xr_address,))
        print('Connected to %s (firmware %s) at %s' % (
            self.info_response[2], self.info_response[3], self.info_response[0]))

    def refresh_connection(self):
        """Keep receiving parameter changes made by other controllers."""
        while True:
            self.send('/xremotenfb')
            time.sleep(self._REFRESH_TIMEOUT)

    def send(self, address, param=None):
        self.server.send_message(address, param)


def find_mixer():
    print('Searching for mixer...')
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, True)
    sock.settimeout(15)
    sock.sendto('/xinfo\0\0'.encode(), ('<broadcast>', XAirClient.XAIR_PORT))
    try:
        response = OscMessage(sock.recv(512))
    except socket.timeout:
        sock.close()
        return None
    sock.close()
    if response.address != '/xinfo' or len(response.params) < 4:
        return None
    print('Found %s with firmware %s on IP %s' % (
        response.params[2], response.params[3], response.params[0]))
    return response.params[0]
