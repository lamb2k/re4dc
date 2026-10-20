#!/usr/bin/env python3
"""pack_add.py <base tex.pak> <out tex.pak> <out sidecar.json> <tex dir>...   (lane ch2rooms20, 2026-10-20)

Adds the texture packages of new rooms (prepare_native_ui.py room pictures, ps2_room_r4im.py world pictures) to the
release tex.pak: every key the base pack lacks is added; a key the base already holds keeps the base bytes (the pack
is looked up first at run time, so the base bytes are the ones drawn) and is listed in the sidecar ("kept_base",
with both sha256s when the bytes differ). Between input dirs the first dir listing a key wins ("input_clash"). No base key is changed or removed. Deterministic (texpack.build).
The sidecar records base / out sha256 and the added keys, for t11-fix.py PAK_DERIVED and the store manifest.
"""
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import tex_merge  # noqa: E402
import texpack  # noqa: E402


def main():
    base_path, out_path, side_path, *dirs = sys.argv[1:]
    assert dirs, __doc__
    base = tex_merge.read(base_path)
    merged = dict(base)
    added, kept, clash, same = [], [], [], 0
    for d in dirs:
        for key, data in sorted(texpack.from_dir(d).items()):
            k = '%08x-%08x' % key
            if key in base:
                if base[key] == data:
                    same += 1
                else:
                    kept.append(dict(key=k, base=hashlib.sha256(base[key]).hexdigest(), new=hashlib.sha256(data).hexdigest(), dir=d))
                continue
            if key in merged:
                if merged[key] != data:   # the earlier dir wins (callers list world dirs before room dirs)
                    clash.append(dict(key=k, kept=hashlib.sha256(merged[key]).hexdigest(), dropped=hashlib.sha256(data).hexdigest(), dir=d))
                continue
            else:
                added.append(k)
            merged[key] = data
    blob, count = texpack.build(merged)
    open(out_path, 'wb').write(blob)
    sha = lambda b: hashlib.sha256(b).hexdigest()
    side = dict(base=sha(open(base_path, 'rb').read()), out=sha(blob), count=count, added=sorted(set(added)),
                kept_base=kept, input_clash=clash, same_bytes=same, dirs=dirs)
    json.dump(side, open(side_path, 'w'), indent=1)
    print('pack_add: %d base + %d added = %d keys; %d already in base (same bytes), %d kept base bytes, '
          '%d input clashes (first dir kept); out %s'
          % (len(base), len(set(added)), count, same, len(kept), len(clash), side['out'][:16]))


if __name__ == '__main__':
    main()
