#!/usr/bin/env python3
"""admit_dir.py <set dir with manifest.tsv>: admit_check.py for a loose-file set (dcform_dir.py output)."""
import os, struct, subprocess, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import admit_check as a  # noqa: E402


def main():
    d = pathlib.Path(sys.argv[1])
    rels = [l.split('\t')[0] for l in open(d / 'manifest.tsv') if l.strip()]
    blobs = [(r, (d / r).read_bytes()) for r in rels]
    a.host.Ps2TextureCrcTests.setUpClass()
    try:
        root = a.host.Ps2TextureCrcTests.root; scene = a.host.ROOT / 'room'
        (root / 'r.cpp').write_text('#include <cstring>\n' + a.host.READER)
        subprocess.run(['g++', '-std=c++17'] + ['-DRE4DC_%s=1' % k for k in a.KNOBS] +
                       ['-DRE4DC_STORAGE_BOUNCE_BYTES=16384', '-I' + str(root), '-I' + str(scene), str(root / 'r.cpp'),
                        str(scene / 'texture_package.cpp'), str(scene / 'room_storage.cpp'), '-o', str(root / 'r')], check=True)
        pal = [(r, b) for r, b in blobs if struct.unpack_from('<I', b, 120)[0] in (3, 4, 5)]
        palk = {r for r, _ in pal}
        bad = a.pal4_admit(pal) if pal else []
        for r, b in blobs:
            if r in palk:
                continue
            (root / 'n').write_bytes(b)
            o = subprocess.run([str(root / 'r'), str(root / 'n')], capture_output=True, text=True)
            out = (o.stdout + o.stderr).strip()
            if o.returncode or out.splitlines()[-1:] != ['ok|ok']:
                bad.append((r, out.splitlines()[-1] if out else 'rc'))
        print('ADMIT %s %d/%d (%d PAL4)' % ('PASS' if not bad else 'FAIL', len(blobs) - len(bad), len(blobs), len(pal)))
        for r, w in bad[:20]:
            print('  refused', r, w)
    finally:
        a.host.Ps2TextureCrcTests.tearDownClass()


if __name__ == '__main__':
    main()
