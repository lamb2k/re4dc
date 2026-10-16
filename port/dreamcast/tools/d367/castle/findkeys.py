#!/usr/bin/env python3
"""findkeys.py ISO OUTDIR KEY... -- scan castle-relevant GC archives for single source images by key and
build each as prepare_native_ui.prepare() does (one image, MaterialBinding('source',0,None))."""
import fnmatch, hashlib, json, sys
from pathlib import Path
T = Path('/root/probe/codex-ps2-assets-20261013/tree/port/dreamcast/tools')
sys.path.insert(0, str(T))
import prepare_native_ui as P
import le_mirror as mirror
from convert_tpl import parse_tpl, build_package, MaterialBinding, TPL_MAGIC
from assetpipe.rooms import GcIso
import struct

iso = GcIso(sys.argv[1]); out = Path(sys.argv[2]); keys = set(sys.argv[3:])
pats = ['st2/r206.das', 'evd/r206*', 'ss/*', 'ss/*/*', 'st2/*.das', 'etc/*', 'evd/r20*']
files = []
for p in pats:
    for f in sorted(iso.files):
        if fnmatch.fnmatch(f.lower(), p) and f not in files:
            files.append(f)
found = {}; origins = {}
cur = [None]
def observe(file, offset, data, context):
    if len(data) >= 12 and struct.unpack_from('>II', data) == (TPL_MAGIC, 0): return
    try: imgs = parse_tpl(data)
    except Exception: return
    for i, im in enumerate(imgs):
        k, payload = P.image_identity(im)
        if k in keys:
            found.setdefault(k, im)
            origins.setdefault(k, []).append(dict(file=file, context=context, tpl_offset=offset, image=i,
                                                  sha256=hashlib.sha256(payload).hexdigest()))
prev = mirror.TPL_OBSERVER; mirror.TPL_OBSERVER = observe
try:
    for f in files:
        if keys <= found.keys(): break
        data = iso.read(f)
        try:
            if f.lower().endswith('.das') and f.lower().startswith('st'): mirror.prepare_room_archive(f.lower(), data)
            else: mirror.convert_file(f.lower(), bytearray(data))
        except Exception as e:
            print('skip', f, type(e).__name__, str(e)[:80])
finally: mirror.TPL_OBSERVER = prev
out.mkdir(parents=True, exist_ok=True); rep = []
for k, im in found.items():
    blob, meta = build_package([im], [MaterialBinding('source', 0, None)], twiddle=True, pad_to_power_of_two=True,
                               source_intensity_alpha=True)
    (out / (k + '.re4tex')).write_bytes(blob)
    rep.append(dict(key=k, width=im.width, height=im.height, format=im.format, bytes=len(blob),
                    sha256=hashlib.sha256(blob).hexdigest(), sources=origins[k][:6]))
    print(k, im.width, im.height, len(blob), origins[k][0]['file'], origins[k][0]['context'])
(out / 'native-ui-keys.json').write_text(json.dumps(rep, indent=1) + '\n')
print('missing:', sorted(keys - found.keys()))
