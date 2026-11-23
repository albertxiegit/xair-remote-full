"""X-Touch Mini MIDI handling (MC mode) for the generic OSC page engine."""

import math
import os
import threading
import time

from mido import Message, get_input_names, get_output_names, open_input, open_output

from .params import FOCUS_KNOB, TRACK_GROUPS, push_toggle_addr


class MidiController:
    """X-Touch Mini must be in MC mode (hold MC while connecting).

    Layer A/B : Note 84 / 85
    Encoders  : CC 16-23 (1-10 = right, 65-72 = left)
    Enc. push : Note 32-39
    Buttons   : Note 89, 90, 40, 41, 42, 43, 44, 45,
                87, 88, 91, 92, 86, 93, 94, 95
    Rings     : CC 48-55
    Master    : Pitch wheel
    """

    MC_CHANNEL = 0
    MIDI_BUTTONS = [89, 90, 40, 41, 42, 43, 44, 45, 87, 88, 91, 92, 86, 93, 94, 95]
    MIDI_PUSH = [32, 33, 34, 35, 36, 37, 38, 39]
    MIDI_ENCODER = [16, 17, 18, 19, 20, 21, 22, 23]
    MIDI_RING = [48, 49, 50, 51, 52, 53, 54, 55]
    MIDI_LAYER = [84, 85]
    LED_OFF = 0
    LED_DIM = 20
    LED_ON = 127
    RING_FLASH_BPM = 150.0

    def __init__(self, state):
        self.state = state
        self.inport = None
        self.outport = None
        for name in get_input_names():
            if 'x-touch mini' in name.lower():
                print('Using MIDI input: ' + name)
                self.inport = open_input(name)
                break
        for name in get_output_names():
            if 'x-touch mini' in name.lower():
                print('Using MIDI output: ' + name)
                self.outport = open_output(name)
                break
        if self.inport is None or self.outport is None:
            raise RuntimeError('X-Touch Mini not found. Connect it and enter MC mode.')
        # Force MC mode via the documented global CC127, regardless of any
        # previous MSFS / X-Touch Editor configuration stored in the device.
        for channel in range(16):
            self.outport.send(Message('control_change', channel=channel,
                                      control=127, value=1))
        time.sleep(0.2)
        self._led_lock = threading.RLock()
        self._blink_button = None
        self._blink_generation = 0
        self._steady_button = None
        self._ring_blink = set()
        self._ring_generation = 0
        self._ring_user_active = {}
        self.set_layer_leds(0)
        worker = threading.Thread(target=self.midi_listener, daemon=True)
        worker.start()
        threading.Thread(target=self.blink_worker, daemon=True).start()
        threading.Thread(target=self.ring_blink_worker, daemon=True).start()

    # ------------------------------------------------------------------ send
    def send_note(self, note, velocity):
        self.outport.send(Message('note_on', channel=self.MC_CHANNEL,
                                  note=note, velocity=velocity))

    def send_cc(self, control, value):
        self.outport.send(Message('control_change', channel=self.MC_CHANNEL,
                                  control=control, value=value))

    def set_layer_leds(self, layer):
        self.send_note(self.MIDI_LAYER[0], self.LED_ON if layer == 0 else self.LED_OFF)
        self.send_note(self.MIDI_LAYER[1], self.LED_ON if layer == 1 else self.LED_OFF)

    def _write_ring(self, knob, value):
        self.send_cc(self.MIDI_RING[knob], value)

    def mark_ring_user(self, knob):
        with self._led_lock:
            self._ring_user_active[knob] = time.time() + 0.4

    def ring_value(self, knob):
        """Current normalised value of a knob's page parameter."""
        param = self.state.current_page().params[knob]
        if param is None:
            return None
        return self.state.normalise(param, self.state.value_of(param))

    def set_ring(self, knob, value):
        with self._led_lock:
            self._write_ring(knob, self.ring_cc(knob, value))

    def ring_cc(self, knob, value):
        """Map a normalised value to the X-Touch ring CC for this knob."""
        if value is None or value < 0:
            return 0
        value = max(0.0, min(1.0, value))
        if knob == FOCUS_KNOB:
            return 1 + round(value * 11)
        param = self.state.current_page().params[knob]
        if param is not None:
            addr = param.addr
            if '/eq/' in addr and addr.endswith('/f'):
                # EQ frequency sweep: single-dot like focus knob.
                return 1 + round(value * 11)
            if addr.endswith('/mix/pan') or ('/eq/' in addr and addr.endswith('/g')):
                # Pan / EQ gain: centre-based, 0 dB sits in the middle.
                return 17 + round(value * 10)
        return 33 + round(value * 11)

    def ring_blink_worker(self):
        """Metronome-style continuous flash of OFF knobs at ~150 BPM."""
        beat = 60.0 / self.RING_FLASH_BPM
        half = beat / 2.0
        with self._led_lock:
            knobs = tuple(self._ring_blink)
            generation = self._ring_generation
        while True:
            if not knobs:
                time.sleep(0.05)
                with self._led_lock:
                    knobs = tuple(self._ring_blink)
                    generation = self._ring_generation
                continue
            values = {}
            for knob in knobs:
                value = self.ring_value(knob)
                if value is not None:
                    values[knob] = self.ring_cc(knob, value)
            if not values:
                time.sleep(0.05)
                continue
            with self._led_lock:
                if self._ring_generation != generation:
                    knobs = tuple(self._ring_blink)
                    generation = self._ring_generation
                    continue
                now = time.time()
                for knob, cc in values.items():
                    if now >= self._ring_user_active.get(knob, 0):
                        self._write_ring(knob, cc)
            time.sleep(half)
            with self._led_lock:
                if self._ring_generation != generation:
                    knobs = tuple(self._ring_blink)
                    generation = self._ring_generation
                    continue
                now = time.time()
                for knob in values:
                    if now >= self._ring_user_active.get(knob, 0):
                        self._write_ring(knob, 0)
            time.sleep(half)
            with self._led_lock:
                if self._ring_generation != generation:
                    knobs = tuple(self._ring_blink)
                    generation = self._ring_generation

    def _write_button(self, button, velocity):
        if os.environ.get('DEBUG_LEDS'):
            print('LED B%d -> %d' % (button + 1, velocity), flush=True)
        self.send_note(self.MIDI_BUTTONS[button], velocity)

    def set_button(self, button, on, dim=False):
        velocity = self.LED_DIM if dim else (self.LED_ON if on else self.LED_OFF)
        with self._led_lock:
            self._write_button(button, velocity)

    def blink_worker(self):
        while True:
            with self._led_lock:
                button = self._blink_button
                generation = self._blink_generation
            if button is None:
                time.sleep(0.05)
                continue
            for _ in range(10):
                with self._led_lock:
                    if self._blink_generation != generation:
                        break
                    self._write_button(button, self.LED_ON)
                time.sleep(0.05)
                with self._led_lock:
                    if self._blink_generation != generation:
                        break
                    self._write_button(button, self.LED_OFF)
                time.sleep(0.05)
            else:
                with self._led_lock:
                    if self._blink_generation == generation:
                        self._write_button(button, self.LED_OFF)
                time.sleep(1.0)

    def refresh_controls(self):
        self.update_indicators()

    def update_indicators(self):
        page = self.state.current_page()
        group = self.state.current_track_group()
        blink_knobs = set()
        for i, param in enumerate(page.params):
            if i == FOCUS_KNOB:
                continue
            addr = push_toggle_addr(i, group)
            if addr is None and param is not None and param.toggle is not None:
                addr = param.toggle
            if addr is not None and not bool(self.state.values.get(addr, 0)):
                blink_knobs.add(i)
        with self._led_lock:
            if blink_knobs != self._ring_blink:
                self._ring_blink = blink_knobs
                self._ring_generation += 1

        for i, param in enumerate(page.params):
            if i == FOCUS_KNOB:
                pos = (self.state.current_track_index() or 0) / float(len(TRACK_GROUPS))
                self.set_ring(i, pos)
                continue
            self.set_ring(i, self.state.normalise(param, self.state.value_of(param))
                          if param is not None else None)

        track = self.state.current_track_index()
        one_hot = track if track is not None and track < 16 else None
        blink = None
        if track == 16:
            blink = 0
        elif track is not None and 17 <= track <= 20:
            blink = 1 + track - 17
        with self._led_lock:
            if blink != self._blink_button:
                self._blink_button = blink
                self._blink_generation += 1
            self._steady_button = one_hot
            for button in range(16):
                if button == blink:
                    continue
                self._write_button(button, self.LED_ON if button == one_hot else self.LED_OFF)

    # ---------------------------------------------------------------- receive
    def midi_listener(self):
        try:
            for msg in self.inport:
                if os.environ.get('DEBUG_MIDI'):
                    print('MIDI << %s' % msg, flush=True)
                if msg.type == 'control_change' and msg.control in self.MIDI_ENCODER:
                    knob = self.MIDI_ENCODER.index(msg.control)
                    self.mark_ring_user(knob)
                    delta = msg.value
                    if delta > 64:
                        delta = (delta - 64) * -1
                    self.state.change_param(knob, delta)
                elif msg.type == 'note_on' and msg.velocity > 0:
                    if msg.note in self.MIDI_PUSH:
                        self.state.push_knob(self.MIDI_PUSH.index(msg.note))
                    elif msg.note in self.MIDI_BUTTONS:
                        self.state.press_button(self.MIDI_BUTTONS.index(msg.note))
                    elif msg.note in self.MIDI_LAYER:
                        self.state.set_layer(self.MIDI_LAYER.index(msg.note))
                elif msg.type == 'pitchwheel':
                    self.state.set_lr_fader((msg.pitch + 8192) / 16384.0)
        except KeyboardInterrupt:
            self.inport.close()
            self.outport.close()
