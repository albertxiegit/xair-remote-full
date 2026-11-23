#!/usr/bin/env python3
"""Full-parameter X-Touch Mini -> X-Air (XR18) OSC bridge.

Fork of peterdikant/xair-remote with a config-driven page engine.
"""

import argparse
import threading
import time

from lib.midicontroller import MidiController
from lib.mixerstate import MixerState
from lib.xair import XAirClient, find_mixer
from lib.xairedit_focus import XAirEditFocus
from lib.xair_selection import XAirSelection
from lib.params import describe_pushes


def main():
    parser = argparse.ArgumentParser(description='Full OSC control of X-Air with X-Touch Mini')
    parser.add_argument('xair_address', nargs='?', help='mixer IP (auto-discovered if omitted)')
    parser.add_argument('-m', '--monitor', action='store_true',
                        help='exit if the X-Touch Mini is unplugged')
    args = parser.parse_args()

    address = args.xair_address or find_mixer()
    if not address:
        raise SystemExit('No mixer found. Pass its IP address explicitly.')

    state = MixerState()
    state.selection_detector = XAirSelection()
    state.focus_clicker = XAirEditFocus()
    state.focus_clicker.detector = state.selection_detector
    midi = MidiController(state)
    state.midi = midi
    xair = XAirClient(address, state)
    state.xair = xair
    xair.validate_connection()

    state.refresh_controls()
    state.print_status()
    print('\nLights: CH01-16 -> B1-B16 single ON | AUX -> B1 blink | FX1-4 -> B2-B5 blink')
    print('Buttons: B1-B16 -> CH01-16 direct select | Knob 8 steps CH/AUX/FX')
    print('Layer A: CH quick | Layer B: GATE/COMP THR + FX SEND1-4(mix7-10) + AUX SEND1+2')
    print('Knob press 1-7 (track %s):' % state.current_track_group())
    print(describe_pushes(state.current_track_group()))
    print('Same on Layer A/B. Ring: OFF -> 1 flash @150bpm/5s | ON -> steady value\n')

    threading.Thread(target=xair.refresh_connection, daemon=True).start()

    if args.monitor:
        def monitor():
            while True:
                if midi.inport.name not in get_names_safe():
                    print('X-Touch disconnected - exiting')
                    raise SystemExit(1)
                time.sleep(1)
        threading.Thread(target=monitor, daemon=True).start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print('Bye')


def get_names_safe():
    from mido import get_input_names
    return get_input_names()


if __name__ == '__main__':
    main()
