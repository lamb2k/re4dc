#!/usr/bin/env python3
"""room_census.py <fixture.json> <room hex> <run-output.txt>... [--tsv OUT] (lane resident16, 2026-10-16; read only)

Every texture a room's visits loaded (room-entry preload passes and play), with its package from the disc the fixture
stages (dc/tex.pak, or a loose dc/tex/<c>/<key>.re4tex the fixture replaces): size, 16-bit format, payload (linear /
twiddled / VQ / palettised), payload bytes, and how it was loaded (pre = inside a preload pass, play = after it; sub =
while the sub screen was open). Totals per payload kind, so a room whose working set does not fit the texture budget
shows which pictures to shrink first (VRAM rule: shrink before evicting; vram/vq_pak.py re-encodes 16-bit packages as
VQ). Loads are attributed to rooms as resident_keys.py does (the "vram room:" line after them, or the room entered
last)."""
import json, re, struct, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import convert_tpl as tpl  # noqa: E402

PAK_MAGIC = b'RE4PAK1' + bytes(1)
LOAD = re.compile(r'^native UI: load /cd/dc/tex/./([0-9a-f]{8}-[0-9a-f]{8})\.re4tex (\d+)x(\d+) fmt=(\d+)')
ROOM = re.compile(r'^vram room: r=([0-9a-f]+) ')
PRE = re.compile(r'^native texture preload: frame=\d+ picked=\d+ resident=\d+ loads=(\d+)')
SS_OPEN = re.compile(r'^subscreen backing: open ')
SS_CLOSE = re.compile(r'^subscreen backing: close ')
ENTER = re.compile(r'^room lifecycle: phase=enter room=([0-9a-f]+) ')


def loads(log, room):
    out, pending, sub, cur = [], [], False, None
    for ln in Path(log).read_text(errors='replace').splitlines():
        m = ENTER.match(ln)
        if m:
            cur = int(m.group(1), 16); continue
        if SS_OPEN.match(ln):
            sub = True; continue
        if SS_CLOSE.match(ln):
            sub = False; continue
        m = LOAD.match(ln)
        if m:
            pending.append([m.group(1), int(m.group(2)), int(m.group(3)), 'sub' if sub else 'play']); continue
        m = PRE.match(ln)
        if m:
            k = int(m.group(1))
            for p in pending[len(pending) - k:] if k else []:
                p[3] = 'pre'
            continue
        m = ROOM.match(ln)
        if m:
            if int(m.group(1), 16) == room:
                out += pending
            pending = []
    if cur == room:
        out += pending
    return out


def package(fix, key, cache={}):
    # pak first, as the runtime (and vq16c-texpak.sh) look textures up: a loose copy shadowed by the pak never loads.
    r = fix['replace']
    loose = r.get('dc/tex/%s/%s.re4tex' % (key[0], key))
    pak = r.get('dc/tex.pak')
    if not pak:
        return (Path(loose).read_bytes(), 'loose') if loose else (None, 'absent')
    if pak not in cache:
        blob = Path(pak).read_bytes()
        magic, ver, count, ioff, doff = struct.unpack_from('<8s4I', blob, 0)
        assert magic == PAK_MAGIC, magic
        idx = {}
        for i in range(count):
            c, f, o, n = struct.unpack_from('<4I', blob, ioff + 16 * i)
            idx['%08x-%08x' % (c, f)] = (o, n)
        cache[pak] = (blob, idx)
    blob, idx = cache[pak]
    if key not in idx:
        return (Path(loose).read_bytes(), 'loose') if loose else (None, 'absent')
    o, n = idx[key]
    return blob[o:o + n], 'pak'


def describe(b):
    hdr = tpl.HEADER.unpack_from(b)
    _, tw, th, fmt, doff, dsize, flags, payload, _ = tpl.TEXTURE.unpack_from(b, hdr[5])
    kind = {0: 'linear', 1: 'twiddled', 2: 'VQ'}.get(payload, 'p%d' % payload)
    return tw, th, fmt, kind, dsize, flags


def main(a):
    tsv = None
    if '--tsv' in a:
        i = a.index('--tsv'); tsv = a[i + 1]; del a[i:i + 2]
    fix = json.load(open(a[0]))
    room = int(a[1], 16)
    seen = {}
    for log in a[2:]:
        for k, w, h, how in loads(log, room):
            e = seen.setdefault(k, {'w': w, 'h': h, 'how': set(), 'n': 0})
            e['how'].add(how); e['n'] += 1
    tot = {}
    rows = []
    for k, e in sorted(seen.items()):
        b, src = package(fix, k)
        if b is None:
            rows.append((k, e['w'], e['h'], '-', 'absent', 0, 0, src, ','.join(sorted(e['how'])), e['n'])); continue
        tw, th, fmt, kind, dsize, flags = describe(b)
        rows.append((k, tw, th, fmt, kind, dsize, flags, src, ','.join(sorted(e['how'])), e['n']))
        t = tot.setdefault(kind, [0, 0]); t[0] += 1; t[1] += dsize
    rows.sort(key=lambda r: -r[5])
    out = ['key\tw\th\tfmt\tpayload\tbytes\tflags\tsrc\thow\tloads']
    out += ['%s\t%d\t%d\t%s\t%s\t%d\t%#x\t%s\t%s\t%d' % r for r in rows]
    if tsv:
        Path(tsv).write_text('\n'.join(out) + '\n')
    for ln in out[:40]:
        print(ln)
    print('room %03x: %d keys; %s' % (room, len(rows), ', '.join('%s %d keys %d B' % (k, v[0], v[1]) for k, v in sorted(tot.items()))))


if __name__ == '__main__':
    main(sys.argv[1:])
