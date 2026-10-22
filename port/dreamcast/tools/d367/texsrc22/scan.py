#!/usr/bin/env python3
"""scan.py (lane texsrc22): static key -> source map for every GC disc-1 texture image.

    scan.py ISO OUT.json [GLOB ...]

Walks every file of the GameCube disc (or the given fnmatch globs) through le_mirror's converters with a
TPL observer (as castle/findkeys.py does), and also brute-scans raw bytes for TPL headers, so images in
formats le_mirror does not dispatch are still found. Each image's key is prepare_native_ui.image_identity
(crc32-fnv1a over metadata + texels + palette), the same key dc/tex/<crc>-<fnv>.re4tex and tex.pak use.
Output: {key: [{file, context, offset, image, w, h, fmt}, ...]}.
"""
import fnmatch, json, struct, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import prepare_native_ui as P
import le_mirror as mirror
from convert_tpl import parse_tpl, TPL_MAGIC
from assetpipe.rooms import GcIso

iso = GcIso(sys.argv[1]); out = Path(sys.argv[2]); pats = sys.argv[3:] or ['*']
files = sorted(f for f in iso.files if any(fnmatch.fnmatch(f.lower(), p) for p in pats))
found = {}
seen = set()


def record(file, offset, data, context):
    try:
        imgs = parse_tpl(data)
    except Exception:
        return
    for i, im in enumerate(imgs):
        k, _ = P.image_identity(im)
        tag = (k, file, offset, i)
        if tag in seen:
            continue
        seen.add(tag)
        found.setdefault(k, []).append(dict(file=file, context=str(context)[:160], offset=offset, image=i,
                                            w=im.width, h=im.height, fmt=im.format))


def observe(file, offset, data, context):
    if len(data) >= 12 and struct.unpack_from('>II', data) == (TPL_MAGIC, 0):
        return
    record(file, offset, data, context)


def brute(f, data):
    magic = struct.pack('>I', TPL_MAGIC)
    pos = data.find(magic)
    while pos >= 0:
        if pos % 4 == 0 and pos + 12 <= len(data):
            n, toff = struct.unpack_from('>II', data, pos + 4)
            if 0 < n < 512 and toff == 12:
                record(f, pos, bytes(data[pos:]), 'brute')
        pos = data.find(magic, pos + 4)


mirror.TPL_OBSERVER = observe
for n, f in enumerate(files):
    try:
        data = iso.read(f)
    except Exception as e:
        print('read-fail', f, e, flush=True)
        continue
    low = f.lower()
    try:
        if low.endswith('.das') and low.startswith('st'):
            mirror.prepare_room_archive(low, data)
        else:
            mirror.convert_file(low, bytearray(data))
    except Exception as e:
        print('skip', f, type(e).__name__, str(e)[:80], flush=True)
    try:
        brute(low, data)
    except Exception as e:
        print('brute-fail', f, e, flush=True)
    if n % 200 == 0:
        print('progress %d/%d keys=%d' % (n, len(files), len(found)), flush=True)
out.write_text(json.dumps(found, sort_keys=True) + '\n')
print('done files=%d keys=%d' % (len(files), len(found)))
