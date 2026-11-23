#!/usr/bin/env python3
"""Generate a printable HTML label sheet for the current page map."""

import html
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from lib.params import build_pages  # noqa: E402

pages, groups = build_pages()


def escape(value):
    return html.escape(str(value))


rows = []
current_layer = None
current_group = None
for page in pages:
    if page.layer != current_layer:
        current_layer = page.layer
        current_group = None
        rows.append('<tr class="layer"><td colspan="10">LAYER %s</td></tr>' % ('A' if page.layer == 0 else 'B'))
    if page.group != current_group:
        current_group = page.group
        rows.append('<tr class="group"><td colspan="10">%s</td></tr>' % escape(current_group))
    labels = [escape(p.label) if p else '-' for p in page.params]
    rows.append('<tr><td>%s</td>%s</tr>' % (
        escape(page.name), ''.join('<td>%s</td>' % label for label in labels)))

document = """<!doctype html>
<html lang="zh"><head><meta charset="utf-8">
<title>X-Touch Mini full OSC labels</title>
<style>
body { font-family: Consolas, monospace; font-size: 9px; }
table { border-collapse: collapse; width: 100%%; }
td { border: 1px solid #999; padding: 2px 4px; }
tr.layer td { background: #333; color: #fff; font-weight: bold; }
tr.group td { background: #ddd; font-weight: bold; }
@media print { body { font-size: 8px; } }
</style></head><body>
<h2>X-Touch Mini full OSC page map (%d pages)</h2>
<p>Knob 1-8 columns; button 1-8 toggles the matching parameter when available.
Button 9 tempo, 10 shift, 11/12 page, 13/14 group, 15 favourite, 16 home.</p>
<table>%s</table></body></html>
""" % (len(pages), '\n'.join(rows))

target = os.path.join(ROOT, 'labels.html')
with open(target, 'w', encoding='utf-8') as handle:
    handle.write(document)
print('Wrote %s (%d pages)' % (target, len(pages)))
