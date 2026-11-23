"""State cache, page navigation and OSC/MIDI bridge logic."""

import os
import threading
import time

from .params import FOCUS_KNOB, TRACK_GROUPS, build_pages, push_toggle_addr


class MixerState:
    def __init__(self):
        self.pages, self.groups = build_pages()
        self.layer = 0
        self.group_index = {0: 0, 1: 0}
        self.page_index = {0: 0, 1: 0}
        self.shared_track = 0
        self.favorites = {}
        self.values = {}
        self.shift = False
        self.midi = None
        self.xair = None
        self.focus_clicker = None
        self.selection_detector = None
        self._page_params = {}
        self._toggle_addrs = {}
        self._last_tap = 0
        self._tap_times = []
        self._focus_accum = 0
        self._focus_timer = None

    # ------------------------------------------------------------------ pages
    def group_pages(self, layer=None, group=None):
        layer = self.layer if layer is None else layer
        group = self.current_group() if group is None else group
        return [p for p in self.pages if p.layer == layer and p.group == group]

    def current_group(self):
        groups = self.groups[self.layer]
        return groups[self.group_index[self.layer] % len(groups)]

    def current_page(self):
        pages = self.group_pages()
        return pages[self.page_index[self.layer] % len(pages)]

    def _bind_page(self):
        self._page_params = {}
        for i, param in enumerate(self.current_page().params):
            if param is not None:
                for addr in (param.addrs or (param.addr,)):
                    self._page_params[addr] = i
        self._toggle_addrs = {}
        group = self.current_track_group()
        for knob in range(7):
            addr = push_toggle_addr(knob, group)
            if addr is not None:
                self._toggle_addrs[addr] = knob

    def refresh_controls(self):
        self._bind_page()
        if self.midi is not None:
            self.midi.refresh_controls()
        self.query_current_page()

    def goto_page(self, delta=0, absolute=None):
        pages = self.group_pages()
        if absolute is None:
            self.page_index[self.layer] = (self.page_index[self.layer] + delta) % len(pages)
        else:
            self.page_index[self.layer] = absolute % len(pages)
        self.refresh_controls()
        self.print_status()

    def current_track_index(self):
        return self.shared_track if 0 <= self.shared_track < len(TRACK_GROUPS) else None

    def current_track_group(self):
        index = self.current_track_index()
        return TRACK_GROUPS[index] if index is not None else None

    def _sync_track_groups(self):
        group = self.current_track_group()
        if group is None:
            return
        for layer in (0, 1):
            if group in self.groups[layer]:
                self.group_index[layer] = self.groups[layer].index(group)

    def goto_group(self, delta):
        if os.environ.get('DEBUG_NAV'):
            print('NAV group=%s delta=%d track=%s' % (
                self.current_group(), delta, self.current_track_index()), flush=True)
        current = self.current_track_index()
        if current is None:
            current = 0
        if current == len(TRACK_GROUPS) - 1 and delta > 0:
            if self.focus_clicker is not None:
                self.focus_clicker.enforce_limit()
            return
        if current == 0 and delta < 0:
            return
        target = current + delta
        if target < 0 or target >= len(TRACK_GROUPS):
            return
        self.shared_track = target
        self._sync_track_groups()
        self.page_index[self.layer] = 0
        self.refresh_controls()
        self.print_status()
        if self.focus_clicker is not None:
            self.focus_clicker.select_group(self.current_track_group())

    def goto_track(self, index):
        if index < 0 or index >= len(TRACK_GROUPS):
            return
        self.shared_track = index
        self._sync_track_groups()
        self.page_index[self.layer] = 0
        self.refresh_controls()
        self.print_status()
        if self.focus_clicker is not None:
            self.focus_clicker.select_group(TRACK_GROUPS[index])

    def set_layer(self, layer):
        if layer not in (0, 1):
            return
        self.favorites[self.layer] = (self.current_group(), self.page_index[self.layer])
        self.layer = layer
        self._sync_track_groups()
        self.page_index[layer] = 0
        if self.midi is not None:
            self.midi.set_layer_leds(layer)
        self.refresh_controls()
        self.print_status()
        if self.focus_clicker is not None:
            self.focus_clicker.select_group(self.current_track_group())

    def goto_home(self):
        self.shared_track = 0
        self._sync_track_groups()
        self.page_index[self.layer] = 0
        self.refresh_controls()
        self.print_status()

    def goto_favorite(self):
        key = self.layer + 10
        saved = self.favorites.get(key)
        if saved is None:
            print('No favourite page stored (long-press a button to store).')
            return
        group, page = saved
        if group in self.groups[self.layer]:
            self.group_index[self.layer] = self.groups[self.layer].index(group)
            self.page_index[self.layer] = page
            self.refresh_controls()
            self.print_status()

    def store_favorite(self):
        self.favorites[self.layer + 10] = (self.current_group(), self.page_index[self.layer])
        print('Favourite stored: %s' % self.current_page().label())

    def print_status(self):
        page = self.current_page()
        print('[L%d] %s (%d/%d in group)' % (
            self.layer + 1, page.label(),
            self.page_index[self.layer] + 1, len(self.group_pages())))

    def start_selection_watcher(self):
        """Follow channel selection made by mouse/keyboard in X-Air Edit."""
        def loop():
            while True:
                if self.selection_detector is not None:
                    idx = self.selection_detector.current_index()
                    if (idx is not None and idx < len(TRACK_GROUPS) and
                            self.layer == 0 and
                            self.current_group() in TRACK_GROUPS):
                        group = 'CH %02d' % (idx + 1)
                        if group != self.current_group():
                            self.group_index[self.layer] = self.groups[self.layer].index(group)
                            self.page_index[self.layer] = 0
                            if self.focus_clicker is not None:
                                self.focus_clicker.selected_index = idx
                            self.refresh_controls()
                            self.print_status()
                time.sleep(0.4)
        threading.Thread(target=loop, daemon=True).start()

    # -------------------------------------------------------------- OSC side
    def send(self, addr, value=None):
        if self.xair is not None:
            self.xair.send(addr, value)

    def query_current_page(self):
        for param in self.current_page().params:
            if param is not None:
                self.send(param.addr)
                time.sleep(0.002)
        for addr in self._toggle_addrs:
            self.send(addr)
            time.sleep(0.002)
        for addr in ('/lr/mix/fader', '/config/mute', '/config/dim', '/config/mono'):
            self.send(addr)
            time.sleep(0.006)

    def received_osc(self, addr, value):
        self.values[addr] = value
        if self.midi is None:
            return
        knob = self._page_params.get(addr)
        if knob is None:
            if addr in self._toggle_addrs:
                self.midi.update_indicators()
            return
        param = self.current_page().params[knob]
        self.midi.set_ring(knob, self.normalise(param, value))
        if param.toggle == addr or addr in self._toggle_addrs:
            self.midi.update_indicators()

    @staticmethod
    def normalise(param, value=None):
        if param.kind == 'int':
            span = param.hi - param.lo
            if span <= 0:
                return float(value or 0)
            return max(0.0, min(1.0, float(value if value is not None else param.lo) / span))
        return max(0.0, min(1.0, float(value if value is not None else 0.0)))

    def value_of(self, param):
        if param.addr in self.values:
            return self.values[param.addr]
        if param.addr.endswith('/pan'):
            return 0.5
        return param.lo

    # ----------------------------------------------------------- MIDI actions
    def _flush_focus(self):
        if self._focus_accum == 0:
            return
        direction = 1 if self._focus_accum > 0 else -1
        self._focus_accum = 0
        self.goto_group(direction)

    def change_param(self, knob, delta):
        if knob == FOCUS_KNOB:
            self._focus_accum += delta
            if self._focus_timer is not None:
                self._focus_timer.cancel()
            self._focus_timer = threading.Timer(0.05, self._flush_focus)
            self._focus_timer.daemon = True
            self._focus_timer.start()
            return
        page = self.current_page()
        param = page.params[knob]
        if param is None:
            return
        if param.toggle is not None or (param.kind == 'float' and param.step >= 1.0):
            self.toggle_addr(param.toggle or param.addr, knob)
            return
        current = self.value_of(param)
        multiplier = 5 if self.shift else 1
        if param.kind == 'int':
            step = max(1, param.step) * multiplier
            value = int(current) + (step if delta > 0 else -step)
            value = max(param.lo, min(param.hi, value))
        else:
            value = float(current) + (delta / 200.0) * param.step * 100 * multiplier
            value = max(param.lo, min(param.hi, value))
            value = round(value, 4)
        for addr in (param.addrs or (param.addr,)):
            self.values[addr] = value
            self.send(addr, value)
        if self.midi is not None:
            self.midi.set_ring(knob, self.normalise(param, value))

    def push_knob(self, knob):
        if knob == FOCUS_KNOB:
            self.store_favorite()
            return
        addr = push_toggle_addr(knob, self.current_track_group())
        if addr is not None:
            self.toggle_addr(addr, knob)
            return
        page = self.current_page()
        param = page.params[knob]
        if param is not None and param.toggle is not None:
            self.toggle_addr(param.toggle, knob)

    def press_button(self, button):
        if button < 16:
            self.goto_track(button)

    def toggle_addr(self, addr, knob=None):
        current = self.values.get(addr, 0)
        value = 0 if current else 1
        self.values[addr] = value
        self.send(addr, value)
        if self.midi is not None:
            self.midi.refresh_controls()

    def set_lr_fader(self, value):
        value = max(0.0, min(1.0, value))
        self.values['/lr/mix/fader'] = value
        self.send('/lr/mix/fader', round(value, 4))

    def tap(self):
        now = time.time()
        if now - self._last_tap > 3:
            self._tap_times = []
        self._tap_times.append(now)
        self._last_tap = now
        if len(self._tap_times) < 2:
            return
        intervals = [b - a for a, b in zip(self._tap_times, self._tap_times[1:])]
        tempo = sum(intervals) / len(intervals)
        if tempo <= 0:
            return
        print('Tap tempo: %.1f BPM' % (60.0 / tempo))
        for slot in range(1, 5):
            fx_type = self.values.get('/fx/%d/type' % slot)
            if fx_type in (10, 11, 12, 21, 24, 25, 26):
                param = '02' if fx_type == 10 else '01'
                self.send('/fx/%d/par/%s' % (slot, param), round(tempo / 3, 4))

    def read_initial_state(self):
        self.query_current_page()
        for slot in range(1, 5):
            self.send('/fx/%d/type' % slot)
        self._bind_page()
