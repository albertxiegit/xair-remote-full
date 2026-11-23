"""OSC parameter model and page generator for Behringer X-Air mixers.

Parameter addresses and ranges follow the X-AIR Remote Control Protocol
(firmware 1.14 and later).  Values exposed by the mixer are normalised:
float parameters use 0.0..1.0, integer parameters use their native range.
"""

from collections import namedtuple

Param = namedtuple('Param', 'addr label kind lo hi step toggle addrs')
Param.__new__.__defaults__ = ((),)

FOCUS_KNOB = 7

TRACK_GROUPS = (['CH %02d' % n for n in range(1, 17)] +
                ['AUX'] +
                ['FX SEND %d' % n for n in range(1, 5)])


def fparam(addr, label, step=0.01, toggle=None):
    return Param(addr, label, 'float', 0.0, 1.0, step, toggle)


def iparam(addr, label, hi, step=1, toggle=None):
    return Param(addr, label, 'int', 0, hi, step, toggle)


def mparam(addrs, label, step=0.01):
    return Param(addrs[0], label, 'float', 0.0, 1.0, step, None, tuple(addrs))


def track_base(group):
    if group.startswith('CH '):
        return _ch(int(group[3:]))
    if group == 'AUX':
        return '/rtn/aux'
    if group.startswith('FX SEND '):
        return _fxsend(int(group[8:]))
    return None


def push_toggle_addr(knob, group):
    """Layer A/B shared knob-press functions for the current track."""
    base = track_base(group)
    if base is None:
        return None
    if knob == 0:
        return base + '/mix/on'
    if knob == 1:
        if group.startswith('CH '):
            return '/-stat/solosw/%02d' % int(group[3:])
        return base + '/mix/solo'
    if knob == 2:
        return base + '/preamp/invert'
    if knob == 3:
        return base + '/gate/on'
    if knob == 4:
        return base + '/eq/on'
    if knob == 5:
        return base + '/dyn/on'
    if knob == 6:
        if group.startswith('CH '):
            return '/headamp/%02d/phantom' % int(group[3:])
        return None
    return None


PUSH_LABELS = ('MUTE', 'SOLO', 'POLARITY', 'GATE', 'EQ', 'COMP', '48V')


def describe_pushes(group):
    """Return knob-press function descriptions for the current track."""
    lines = []
    for knob, label in enumerate(PUSH_LABELS):
        addr = push_toggle_addr(knob, group)
        lines.append('  K%d %-8s %s' % (knob + 1, label, addr or 'n/a'))
    return '\n'.join(lines)


def none():
    return None


class Page:
    def __init__(self, layer, group, name, params, buttons=None):
        self.layer = layer
        self.group = group
        self.name = name
        self.params = list(params)[:8] + [none()] * (8 - len(list(params)[:8]))
        self.params[FOCUS_KNOB] = None
        self.buttons = dict(buttons or {})

    def label(self):
        return '%s / %s' % (self.group, self.name)


def _ch(n):
    return '/ch/%02d' % n


def _rtn(n):
    return '/rtn/aux' if n == 0 else '/rtn/%d' % n


def _bus(n):
    return '/bus/%d' % n


def _fxsend(n):
    return '/fxsend/%d' % n


def _dca(n):
    return '/dca/%d' % n


def _mute(n):
    return '/config/mute/%d' % n


def _mix_page(layer, group, base, title, has_pan=True, has_send=False):
    params = [fparam(base + '/fader', 'FADER', 0.01)]
    if has_pan:
        params.append(fparam(base + '/pan', 'PAN', 0.01))
    params.append(fparam(base + '/on', 'ON', 1.0, toggle=base + '/on'))
    params.append(iparam(base + '/lr', 'TO LR', 1, 1, toggle=base + '/lr'))
    params.append(fparam(base + '/grpon', 'GRP ON', 1.0, toggle=base + '/grpon'))
    params.append(iparam(base + '/tap', 'TAP', 5))
    if has_send:
        params.append(fparam(base + '/01/level', 'SEND 1'))
        params.append(fparam(base + '/02/level', 'SEND 2'))
    return Page(layer, group, title, params)


def _eq_pages(layer, group, base, title, bands, prefix='EQ'):
    pages = []
    pages.append(Page(layer, group, title + ' EQ ON', [
        fparam(base + '/eq/on', 'EQ ON', 1.0, toggle=base + '/eq/on'),
        iparam(base + '/eq/mode', 'MODE', 2),
        iparam(base + '/eq/1/type', 'B1 TYPE', 5),
        fparam(base + '/eq/1/f', 'B1 FREQ', 0.01),
        fparam(base + '/eq/1/g', 'B1 GAIN', 0.01),
        fparam(base + '/eq/1/q', 'B1 Q', 0.01),
        iparam(base + '/eq/2/type', 'B2 TYPE', 5),
        fparam(base + '/eq/2/f', 'B2 FREQ', 0.01),
    ]))
    idx = 1
    while idx <= bands:
        params = []
        for b in range(idx, min(idx + 2, bands + 1)):
            tag = 'B%d' % b
            params.extend([
                iparam(base + '/eq/%d/type' % b, tag + ' TYPE', 5),
                fparam(base + '/eq/%d/f' % b, tag + ' FREQ', 0.01),
                fparam(base + '/eq/%d/g' % b, tag + ' GAIN', 0.01),
                fparam(base + '/eq/%d/q' % b, tag + ' Q', 0.01),
            ])
        pages.append(Page(layer, group, '%s EQ %d-%d' % (title, idx, min(idx + 1, bands)), params))
        idx += 2
    return pages


def _dyn_pages(layer, group, base, title, with_keysrc):
    first = [
        fparam(base + '/dyn/on', 'DYN ON', 1.0, toggle=base + '/dyn/on'),
        iparam(base + '/dyn/mode', 'MODE', 1),
        iparam(base + '/dyn/det', 'DETECT', 1),
        iparam(base + '/dyn/env', 'ENV', 1),
        fparam(base + '/dyn/thr', 'THRESH', 0.01),
        iparam(base + '/dyn/ratio', 'RATIO', 11),
        fparam(base + '/dyn/knee', 'KNEE', 0.01),
        fparam(base + '/dyn/mgain', 'MAKEUP', 0.01),
    ]
    second = [
        fparam(base + '/dyn/attack', 'ATTACK', 0.01),
        fparam(base + '/dyn/hold', 'HOLD', 0.01),
        fparam(base + '/dyn/release', 'RELEASE', 0.01),
        fparam(base + '/dyn/mix', 'MIX', 0.01),
        fparam(base + '/dyn/auto', 'AUTO', 1.0, toggle=base + '/dyn/auto'),
        fparam(base + '/dyn/filter/on', 'FILT ON', 1.0, toggle=base + '/dyn/filter/on'),
        iparam(base + '/dyn/filter/type', 'FILT TYPE', 8),
        fparam(base + '/dyn/filter/f', 'FILT FREQ', 0.01),
    ]
    pages = [Page(layer, group, title + ' DYN 1', first),
             Page(layer, group, title + ' DYN 2', second)]
    if with_keysrc:
        pages.append(Page(layer, group, title + ' DYN KEY', [
            iparam(base + '/dyn/keysrc', 'KEY SRC', 22),
        ]))
    return pages


def _gate_pages(layer, group, base, title):
    first = [
        fparam(base + '/gate/on', 'GATE ON', 1.0, toggle=base + '/gate/on'),
        iparam(base + '/gate/mode', 'MODE', 4),
        fparam(base + '/gate/thr', 'THRESH', 0.01),
        fparam(base + '/gate/range', 'RANGE', 0.01),
        fparam(base + '/gate/attack', 'ATTACK', 0.01),
        fparam(base + '/gate/hold', 'HOLD', 0.01),
        fparam(base + '/gate/release', 'RELEASE', 0.01),
        iparam(base + '/gate/keysrc', 'KEY SRC', 22),
    ]
    second = [
        fparam(base + '/gate/filter/on', 'FILT ON', 1.0, toggle=base + '/gate/filter/on'),
        iparam(base + '/gate/filter/type', 'FILT TYPE', 8),
        fparam(base + '/gate/filter/f', 'FILT FREQ', 0.01),
    ]
    return [Page(layer, group, title + ' GATE 1', first),
            Page(layer, group, title + ' GATE 2', second)]


def _send_pages(layer, group, base, title, count=10):
    pages = []
    offset = 1
    while offset <= count:
        params = []
        for s in range(offset, min(offset + 8, count + 1)):
            tag = '%02d' % s
            params.append(fparam(base + '/' + tag + '/level', 'SEND %d' % s))
        pages.append(Page(layer, group, '%s SEND %d-%d' % (title, offset, min(offset + 7, count)), params))
        offset += 8
    return pages


def _strip_pages(layer, group, base, title, kind):
    """kind: 'ch', 'rtn', 'bus', 'lr', 'fxsend', 'dca', 'mute'."""
    pages = []
    if kind in ('ch', 'rtn', 'bus', 'fxsend', 'lr'):
        pages.append(_mix_page(layer, group, base + '/mix', title,
                               has_pan=(kind != 'fxsend'),
                               has_send=(kind in ('ch', 'rtn'))))
    if kind in ('ch', 'rtn'):
        pages.extend(_send_pages(layer, group, base + '/mix', title))
    if kind == 'ch':
        pages.extend(_gate_pages(layer, group, base, title))
        pages.append(Page(layer, group, title + ' PREAMP', [
            fparam(base + '/preamp/rtntrim', 'RTN TRIM', 0.01),
            fparam(base + '/preamp/rtnsw', 'RTN SRC', 1.0, toggle=base + '/preamp/rtnsw'),
            fparam(base + '/preamp/invert', 'INVERT', 1.0, toggle=base + '/preamp/invert'),
            fparam(base + '/preamp/hpon', 'HPF ON', 1.0, toggle=base + '/preamp/hpon'),
            fparam(base + '/preamp/hpf', 'HPF FREQ', 0.01),
            iparam(base + '/config/insrc', 'IN SRC', 18),
            iparam(base + '/config/rtnsrc', 'USB RET', 17),
            iparam(base + '/config/color', 'COLOR', 15),
        ]))
    if kind == 'rtn':
        pages.append(Page(layer, group, title + ' PREAMP', [
            fparam(base + '/preamp/rtntrim', 'TRIM', 0.01),
            fparam(base + '/preamp/rtnsw', 'RTN SRC', 1.0, toggle=base + '/preamp/rtnsw'),
            iparam(base + '/config/rtnsrc', 'USB PAIR', 8),
            iparam(base + '/config/color', 'COLOR', 15),
        ]))
    if kind in ('ch', 'rtn', 'bus', 'lr'):
        bands = 6 if kind in ('bus', 'lr') else 4
        pages.extend(_eq_pages(layer, group, base, title, bands))
    if kind in ('ch', 'bus', 'lr'):
        pages.extend(_dyn_pages(layer, group, base, title, with_keysrc=(kind == 'ch')))
        pages.append(Page(layer, group, title + ' INSERT', [
            fparam(base + '/insert/on', 'INSERT ON', 1.0, toggle=base + '/insert/on'),
            iparam(base + '/insert/fxslot', 'FX SLOT', 8),
        ]))
    if kind == 'ch':
        pages.append(Page(layer, group, title + ' AUTOMIX', [
            iparam(base + '/automix/group', 'AMIX GRP', 2),
            fparam(base + '/automix/weight', 'WEIGHT', 0.01),
        ]))
    if kind == 'dca':
        pages.append(Page(layer, group, title, [
            fparam(base + '/on', 'ON', 1.0, toggle=base + '/on'),
            fparam(base + '/fader', 'FADER', 0.01),
        ]))
    if kind == 'mute':
        pages.append(Page(layer, group, title, [
            fparam(base, 'MUTE GRP', 1.0, toggle=base),
        ]))
    return pages


def _ch_quick_page(n):
    """User-defined quick page: 1 fader, 2 gain, 3 EQ hi, 4 EQ mid,
    5 mid sweep, 6 EQ low, 7 pan, 8 focus."""
    base = _ch(n)
    label = 'CH %02d' % n
    return Page(0, label, label + ' QUICK', [
        fparam(base + '/mix/fader', 'FADER', 0.01),
        fparam('/headamp/%02d/gain' % n, 'GAIN', 0.04),
        fparam(base + '/eq/4/g', 'EQ HI', 0.01),
        fparam(base + '/eq/2/g', 'EQ MID', 0.01),
        fparam(base + '/eq/2/f', 'MID FREQ', 0.01),
        fparam(base + '/eq/1/g', 'EQ LOW', 0.01),
        fparam(base + '/mix/pan', 'PAN', 0.01),
    ])


def build_pages():
    """Return (pages, groups_by_layer) with every controllable OSC address."""
    pages = []

    def add(layer, group, group_pages):
        for page in group_pages:
            page.layer = layer
            page.group = group
        pages.extend(group_pages)

    # Layer A: input channels, returns, buses, master, DCAs, mute groups.
    for n in range(1, 17):
        group_pages = _strip_pages(0, 'CH %02d' % n, _ch(n), 'CH %02d' % n, 'ch')
        group_pages[0] = _ch_quick_page(n)
        add(0, 'CH %02d' % n, group_pages)
    for n, label in [(0, 'AUX'), (1, 'FXRTN 1'), (2, 'FXRTN 2'), (3, 'FXRTN 3'), (4, 'FXRTN 4')]:
        add(0, label, _strip_pages(0, label, _rtn(n), label, 'rtn'))
    for n in range(1, 7):
        add(0, 'BUS %d' % n, _strip_pages(0, 'BUS %d' % n, _bus(n), 'BUS %d' % n, 'bus'))
    add(0, 'MAIN LR', _strip_pages(0, 'MAIN LR', '/lr', 'MAIN LR', 'lr'))
    for n in range(1, 5):
        add(0, 'FX SEND %d' % n, _strip_pages(0, 'FX SEND %d' % n, _fxsend(n), 'FX SEND %d' % n, 'fxsend'))
    for n in range(1, 5):
        add(0, 'DCA %d' % n, _strip_pages(0, 'DCA %d' % n, _dca(n), 'DCA %d' % n, 'dca'))
    add(0, 'MUTE GRP', [p for n in range(1, 5)
                        for p in _strip_pages(0, 'MUTE GRP', _mute(n), 'MUTE %d' % n, 'mute')])

    # Layer B: track-following control page for the same selected track.
    for group in TRACK_GROUPS:
        base = track_base(group)
        add(1, group, [Page(1, group, 'TRACK CTRL', [
            fparam(base + '/gate/thr', 'GATE THR'),
            fparam(base + '/dyn/thr', 'COMP THR'),
            fparam(base + '/mix/07/level', 'FX SEND 1'),
            fparam(base + '/mix/08/level', 'FX SEND 2'),
            fparam(base + '/mix/09/level', 'FX SEND 3'),
            fparam(base + '/mix/10/level', 'FX SEND 4'),
            mparam((base + '/mix/01/level', base + '/mix/02/level'), 'AUX SEND 1+2'),
        ])])

    # Layer B: console globals, routing, headamps, FX, snapshots.
    add(1, 'MAIN / SOLO', [
        Page(1, 'MAIN / SOLO', 'MAIN', [
            fparam('/lr/mix/fader', 'LR FADER', 0.01),
            fparam('/lr/mix/pan', 'LR BAL', 0.01),
            fparam('/config/dim', 'DIM', 1.0, toggle='/config/dim'),
            fparam('/config/mono', 'MONO', 1.0, toggle='/config/mono'),
            fparam('/config/mute', 'MUTE', 1.0, toggle='/config/mute'),
            fparam('/config/dimatt', 'DIM ATT', 0.01),
            fparam('/config/solo/level', 'SOLO LEVEL', 0.01),
            iparam('/config/solo/source', 'SOLO SRC', 14),
        ]),
        Page(1, 'MAIN / SOLO', 'SOLO', [
            iparam('/config/solo/chmode', 'CH PFL/AFL', 1),
            iparam('/config/solo/busmode', 'BUS PFL/AFL', 1),
            fparam('/config/solo/dimpfl', 'DIM PFL', 1.0, toggle='/config/solo/dimpfl'),
            iparam('/solosw/01', 'SOLO SW 01', 53),
            iparam('/solosw/02', 'SOLO SW 02', 53),
            iparam('/solosw/03', 'SOLO SW 03', 53),
            iparam('/solosw/04', 'SOLO SW 04', 53),
            iparam('/config/rta/source', 'RTA SRC', 32),
        ]),
        Page(1, 'MAIN / SOLO', 'RTA', [
            fparam('/config/rta/det', 'RTA DET', 1.0),
            fparam('/config/rta/decay', 'RTA DECAY', 0.01),
            iparam('/config/amixenable/X', 'AMIX X EN', 1, 1, '/config/amixenable/X'),
            iparam('/config/amixenable/Y', 'AMIX Y EN', 1, 1, '/config/amixenable/Y'),
            iparam('/config/amixlock/X', 'AMIX X LOCK', 1, 1, '/config/amixlock/X'),
            iparam('/config/amixlock/Y', 'AMIX Y LOCK', 1, 1, '/config/amixlock/Y'),
            fparam('/config/hardmute', 'HARD MUTE', 1.0, toggle='/config/hardmute'),
            fparam('/config/dcamute', 'DCA MUTE', 1.0, toggle='/config/dcamute'),
        ]),
    ])

    add(1, 'CONSOLE', [
        Page(1, 'CONSOLE', 'PREFS', [
            iparam('/prefs/clockrate', 'CLOCK', 1),
            fparam('/prefs/ponmute', 'PON MUTE', 1.0, toggle='/prefs/ponmute'),
            iparam('/prefs/usbifcmode', 'USB MODE', 1),
            iparam('/prefs/midiconfig', 'MIDI CFG', 127),
            fparam('/prefs/playnext', 'PLAY NEXT', 1.0, toggle='/prefs/playnext'),
            iparam('/-stat/autosave', 'AUTOSAVE', 1),
            iparam('/-stat/netmode', 'NET MODE', 2),
            iparam('/-stat/keysolo', 'KEY SOLO', 39),
        ]),
        Page(1, 'CONSOLE', 'LINK', [
            fparam('/config/linkcfg/preamp', 'LINK PREAMP', 1.0, toggle='/config/linkcfg/preamp'),
            fparam('/config/linkcfg/eq', 'LINK EQ', 1.0, toggle='/config/linkcfg/eq'),
            fparam('/config/linkcfg/dyn', 'LINK DYN', 1.0, toggle='/config/linkcfg/dyn'),
            fparam('/config/linkcfg/fdrmute', 'LINK FDER/MUTE', 1.0, toggle='/config/linkcfg/fdrmute'),
        ] + [fparam('/config/chlink/%d-%d' % (n, n + 1), 'CH %d-%d' % (n, n + 1), 1.0)
             for n in (1, 3, 5, 7)]),
        Page(1, 'CONSOLE', 'LINK 2', [
            fparam('/config/chlink/%d-%d' % (n, n + 1), 'CH %d-%d' % (n, n + 1), 1.0)
            for n in (9, 11, 13, 15)
        ] + [
            fparam('/config/buslink/%d-%d' % (n, n + 1), 'BUS %d-%d' % (n, n + 1), 1.0)
            for n in (1, 3, 5)
        ]),
        Page(1, 'CONSOLE', 'ACTIONS', [
            iparam('/-action/updnet', 'UPDATE NET', 3),
            fparam('/-action/wlanscan', 'WLAN SCAN', 1.0),
            fparam('/-action/initall', 'INIT ALL', 1.0),
            fparam('/-action/savestate', 'SAVE STATE', 1.0),
            fparam('/-action/clearsolo', 'CLEAR SOLO', 1.0),
        ]),
    ])

    headamp_pages = []
    for start in (1, 9):
        params = []
        for n in range(start, start + 8):
            params.append(fparam('/headamp/%02d/gain' % n, 'HA %02d' % n, 0.01))
        headamp_pages.append(Page(1, 'HEADAMP', 'GAIN %02d-%02d' % (start, start + 7), params))
        params = []
        for n in range(start, start + 8):
            params.append(fparam('/headamp/%02d/phantom' % n, '48V %02d' % n, 1.0,
                                 toggle='/headamp/%02d/phantom' % n))
        headamp_pages.append(Page(1, 'HEADAMP', 'PHANTOM %02d-%02d' % (start, start + 7), params))
    add(1, 'HEADAMP', headamp_pages)

    routing_pages = []
    routing_pages.append(Page(1, 'ROUTING', 'MAIN / PHONES', [
        iparam('/routing/main/01/src', 'MAIN L SRC', 10),
        iparam('/routing/main/02/src', 'MAIN R SRC', 10),
        iparam('/routing/aux/01/src', 'PHONE 1 SRC', 10),
        iparam('/routing/aux/02/src', 'PHONE 2 SRC', 10),
    ]))
    for start in (1, 5, 9, 13):
        params = []
        for n in range(start, start + 4):
            params.extend([
                iparam('/routing/p16/%02d/src' % n, 'P16 %02d SRC' % n, 55),
                iparam('/routing/p16/%02d/pos' % n, 'P16 %02d POS' % n, 10),
            ])
        routing_pages.append(Page(1, 'ROUTING', 'P16 %02d-%02d' % (start, start + 3), params))
    for start in (1, 7, 13):
        params = []
        for n in range(start, min(start + 6, 19)):
            params.extend([
                iparam('/routing/usb/%02d/src' % n, 'USB %02d SRC' % n, 37),
                iparam('/routing/usb/%02d/pos' % n, 'USB %02d POS' % n, 10),
            ])
        routing_pages.append(Page(1, 'ROUTING', 'USB %02d-%02d' % (start, min(start + 5, 18)), params))
    add(1, 'ROUTING', routing_pages)

    add(1, 'FX SELECT', [
        Page(1, 'FX SELECT', 'SLOTS 1-4', [
            iparam('/fx/1/type', 'FX1 TYPE', 60),
            fparam('/fx/1/insert', 'FX1 INSERT', 1.0, toggle='/fx/1/insert'),
            iparam('/fx/2/type', 'FX2 TYPE', 60),
            fparam('/fx/2/insert', 'FX2 INSERT', 1.0, toggle='/fx/2/insert'),
            iparam('/fx/3/type', 'FX3 TYPE', 60),
            fparam('/fx/3/insert', 'FX3 INSERT', 1.0, toggle='/fx/3/insert'),
            iparam('/fx/4/type', 'FX4 TYPE', 60),
            fparam('/fx/4/insert', 'FX4 INSERT', 1.0, toggle='/fx/4/insert'),
        ]),
    ])

    fx_pages = []
    for slot in range(1, 5):
        for start in range(1, 65, 8):
            params = []
            for n in range(start, start + 8):
                params.append(fparam('/fx/%d/par/%02d' % (slot, n), 'PAR %02d' % n, 0.01))
            fx_pages.append(Page(1, 'FX %d PAR' % slot,
                                 'PAR %02d-%02d' % (start, start + 7), params))
    add(1, 'FX PARAMS', fx_pages)

    snap_pages = []
    for action in ('load', 'save', 'delete'):
        for start in range(1, 65, 8):
            params = [iparam('/snap/' + action, '%s %02d' % (action.upper(), n), 64)
                      for n in range(start, start + 8)]
            snap_pages.append(Page(1, 'SNAPSHOTS', '%s %02d-%02d' % (action.upper(), start, start + 7), params))
    add(1, 'SNAPSHOTS', snap_pages)

    groups_by_layer = {0: [], 1: []}
    for page in pages:
        if page.group not in groups_by_layer[page.layer]:
            groups_by_layer[page.layer].append(page.group)
    return pages, groups_by_layer
