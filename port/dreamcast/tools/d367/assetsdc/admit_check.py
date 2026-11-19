#!/usr/bin/env python3
"""admit_check.py <pak-derived.json> <tex.pak> : offline admission of every changed package by the actual native
Package reader (room/texture_package.cpp), host-compiled with the release recipe's texture knobs (ADMIT_KNOBS,
default CAST_MIPMAP TEX_TWIDDLED_MIPMAP TEX_PAL4_ALPHA TEX_PAL4_MIPMAP TEX_PAL8_ALPHA TEX_PAL8_MIPMAP TEX_RESIDENT).
Reuses the host harness of tests/test_mipmap_runtime.py. Prints ADMIT PASS n/n or the refused keys (exit 1).
(lane assets-dc, 2026-11-02). Not a frame-time or look check.
"""
import json, os, subprocess, sys, pathlib
HERE = pathlib.Path(__file__).resolve().parent
TESTS = HERE.parents[2] / 'tests'
sys.path[:0] = [str(TESTS), str(HERE.parents[1]), str(HERE.parent), str(HERE.parent / 'vram')]
import test_ps2_room_r4im_texcrc as host  # noqa: E402
from vq_pak import read_pak               # noqa: E402

KNOBS = os.environ.get('ADMIT_KNOBS', 'CAST_MIPMAP TEX_TWIDDLED_MIPMAP TEX_RESIDENT').split()


def pal4_admit(blobs):
    """PAL4 packages through tests/test_mipmap_pal4.py's palette harness (PVR stubs; TEX_PAL4_ALPHA + CAST_MIPMAP +
    TEX_PAL4_MIPMAP=1, the release values). Returns refused keys."""
    import tempfile
    import test_mipmap_pal4 as t
    bad = []
    with tempfile.TemporaryDirectory() as dd:
        d = pathlib.Path(dd); t.stubs(d)
        prefix = t.FIXTURE[:t.FIXTURE.index('int main(')].replace(
            'assert(!(tcw&0x80000000U));', 'assert(bool(tcw&0x80000000U)==bool(t.flags&kMipmap));')
        (d / 'reader.cpp').write_text(prefix + t.PALETTE_MAIN)
        exe = d / 'reader'
        subprocess.run(['g++', '-std=c++17', '-DRE4DC_STORAGE_BOUNCE_BYTES=16384', '-DRE4DC_PVR_PIPELINE=1',
                        '-DRE4DC_TEX_PAL4_ALPHA=1', '-DRE4DC_CAST_MIPMAP=1', '-DRE4DC_TEX_PAL4_MIPMAP=1', '-DRE4DC_UI_VRAM=1',
                        '-I' + str(d), '-I' + str(t.ROOT / 'room'), str(d / 'reader.cpp'),
                        str(t.ROOT / 'room/texture_package.cpp'), str(t.ROOT / 'room/room_storage.cpp'), '-o', str(exe)],
                       capture_output=True, check=True)
        for k, b in blobs:
            (d / 'x').write_bytes(b)
            if subprocess.run([str(exe), str(d / 'x'), '1'], capture_output=True).returncode:
                bad.append((k, 'pal4 harness refused'))
    return bad


def main():
    changed = json.load(open(sys.argv[1]))['changed']
    pkgs = read_pak(open(sys.argv[2], 'rb').read())
    host.Ps2TextureCrcTests.setUpClass()
    try:
        root = host.Ps2TextureCrcTests.root
        scene = host.ROOT / 'room'
        (root / 'reader-adm.cpp').write_text('#include <cstring>\n' + host.READER)
        exe = root / 'reader-adm'
        b = subprocess.run(['g++', '-std=c++17'] + ['-DRE4DC_%s=1' % k for k in KNOBS] +
                           ['-DRE4DC_STORAGE_BOUNCE_BYTES=16384', '-I' + str(root), '-I' + str(scene),
                            str(root / 'reader-adm.cpp'), str(scene / 'texture_package.cpp'),
                            str(scene / 'room_storage.cpp'), '-o', str(exe)], capture_output=True, text=True)
        if b.returncode:
            sys.exit('host build failed (%s):\n%s' % (' '.join(KNOBS), b.stderr[-3000:]))
        import struct as _st
        pal = [(k, pkgs[tuple(int(x, 16) for x in k.split('-'))]) for k in changed]
        pal = [(k, b) for k, b in pal if _st.unpack_from('<I', b, 48 + 72)[0] in (3, 4, 5)]
        palk = {k for k, _ in pal}
        bad = pal4_admit(pal) if pal else []
        for k in changed:
            if k in palk:
                continue
            kt = tuple(int(x, 16) for x in k.split('-'))
            p = root / 'adm.re4tex'; p.write_bytes(pkgs[kt])
            r = subprocess.run([str(exe), str(p)], capture_output=True, text=True)
            out = (r.stdout + r.stderr).strip()
            # the host READER prints "<strict>|<streamed>" verdicts: "ok|ok" when both admit the package
            if r.returncode != 0 or out.splitlines()[-1:] != ['ok|ok']:
                bad.append((k, out.splitlines()[-1] if out else 'rc %d' % r.returncode))
        print('ADMIT %s %d/%d (%s; %d PAL4 via the palette harness)' % ('PASS' if not bad else 'FAIL', len(changed) - len(bad), len(changed), ' '.join(KNOBS), len(pal)))
        for k, why in bad[:40]:
            print('  refused', k, why)
        sys.exit(1 if bad else 0)
    finally:
        host.Ps2TextureCrcTests.tearDownClass()


if __name__ == '__main__':
    main()
