#!/usr/bin/env python3
"""data17_unvq.py <tools dir> <derived tex.pak> <donor tex.pak> <out tex.pak> <key>...
Undo a tex_merge: take <derived>, put back the donor's package for each key, rebuild with texpack.build."""
import sys
sys.path.insert(0, sys.argv[1])
import tex_merge, texpack  # noqa: E402

derived, donor = tex_merge.read(sys.argv[2]), tex_merge.read(sys.argv[3])
for k in sys.argv[5:]:
    a, b = k.split('-'); key = (int(a, 16), int(b, 16))
    assert key in derived and key in donor, k
    print(k, len(derived[key]), '->', len(donor[key]))
    derived[key] = donor[key]
blob, n = texpack.build(derived)
open(sys.argv[4], 'wb').write(blob)
print('packages', n, 'bytes', len(blob))
