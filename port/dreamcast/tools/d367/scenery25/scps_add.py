#!/usr/bin/env python3
"""scps_add.py <native dir> <out dir> [rooms...] (lane scenery-rewrite25): add the SCENERY_PIECE_STATE section 'SCPS' v1
(scenery21 layout: head 16 B = u32 mesh crc, u32 mesh bytes, u32 part count, 0; then u32[part count] zero, pad 16) to
each room's room.r4rc for the world package it ships with now (<native>/<room>/ps2-world.re4mesh, e.g. a release disc
tree's dc/native). Every other section is kept byte for byte (an old SCPS is replaced). Outputs <out>/<room>/room.r4rc,
MANIFEST-SCPS.tsv, SHA256SUMS. Deterministic."""
import hashlib, struct, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'scenery19'))
import scdd_compile  # noqa: E402


def scps(mesh):
    h = struct.unpack_from('<16I', mesh, 0)
    crc, npart = h[3], h[5]
    body = struct.pack('<4I', crc, len(mesh), npart, 0) + bytes(4 * npart)
    return body + bytes(-len(body) % 16), npart, crc


def main():
    nat, out = Path(sys.argv[1]), Path(sys.argv[2])
    rooms = sys.argv[3:] or sorted(d.name for d in nat.iterdir()
                                   if (d / 'ps2-world.re4mesh').is_file() and (d / 'room.r4rc').is_file())
    rows, sums = [], []
    for r in rooms:
        mesh = (nat / r / 'ps2-world.re4mesh').read_bytes()
        b = (nat / r / 'room.r4rc').read_bytes()
        body, npart, crc = scps(mesh)
        secs = [s for s in scdd_compile.read_rc(b) if s[0] != b'SCPS']
        secs.append([b'SCPS', 1, 0, body, npart, 4, 16])
        rc = scdd_compile.write_rc(b, secs)
        (out / r).mkdir(parents=True, exist_ok=True)
        (out / r / 'room.r4rc').write_bytes(rc)
        rows.append((r, '%08x' % crc, npart, len(b), len(rc)))
        sums.append('%s  %s/room.r4rc' % (hashlib.sha256(rc).hexdigest(), r))
    with open(out / 'MANIFEST-SCPS.tsv', 'w') as f:
        f.write('room\tmesh_crc\tparts\tin_bytes\tout_bytes\n')
        for x in rows:
            f.write('\t'.join(str(v) for v in x) + '\n')
    (out / 'SHA256SUMS').write_text('\n'.join(sums) + '\n')
    for x in rows:
        print('%s crc=%s parts=%d room.r4rc %d -> %d B' % x)


if __name__ == '__main__':
    main()
