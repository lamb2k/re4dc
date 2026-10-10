#!/usr/bin/env python3
"""Build the material-pair texture packages a run asked for and could not open.

    pairs_from_log.py --iso GC.iso --output DIR [--log run-output.txt ...] [--pair COLOR:MASK ...]
                      [--file st1/r101.das ...]

A model part with a separate mask image (material_flags & 4) draws from one package keyed by
prepare_native_ui.material_pair_identity(color, mask). Nothing built those packages for the
route rooms (r101: 9 of them, warp-r101-pbdoor4 "package rejected: open failed"). The runtime
now logs each failed pair once:
    native UI: pair missing <pair key> color=<key> mask=<key> <w>x<h>
This reads those lines (and --pair for pairs recovered from older logs), extracts the source
archives from the GC disc into a work directory, and calls prepare_model_pairs, which checks
every requested image exists, has equal dimensions and yields the logged key. Output: one
<key>.re4tex per pair plus material-pairs.json. Private inputs and outputs (derived game art).
"""
import argparse
import re
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))   # tools/: prepare_native_ui, assetpipe
import prepare_native_ui as P  # noqa: E402
from assetpipe.rooms import GcIso  # noqa: E402

LINE = re.compile(r"native UI: pair missing ([0-9a-f]{8}-[0-9a-f]{8}) color=([0-9a-f]{8}-[0-9a-f]{8}) "
                  r"mask=([0-9a-f]{8}-[0-9a-f]{8})")
# Archives whose TPLs hold the route's model images (rooms, enemies, Leon, weapon, core).
ROUTE_FILES = ["st1/r100.das", "st1/r101.das", "st1/r103.das", "em/em10.drs", "em/em12.drs", "em/em15.drs",
               "em/em21.drs", "em/em23.drs", "em/em26.drs", "em/em28.drs", "em/em2a.drs", "em/pl00.drs",
               "em/wep02.drs", "etc/core.das",
               # r103's two remaining pairs (warp-r101-pbdoor6): images in the sub-screen object
               # archive and in the route events
               "ss/cmn/ss_oc101.dat", "evd/r101s30.evd",
               # r10b boarding (lake-20261010): 18d0fd82-2c9a9309, st1/r10b.arc entry 27
               "st1/r10b.das"]


def pairs_from_logs(logs):
    """{pair key: (color, mask)} from the runtime's pair-missing lines."""
    out = {}
    for lg in logs:
        for line in Path(lg).read_text(errors="replace").splitlines():
            m = LINE.search(line)
            if m:
                key, color, mask = m.groups()
                if P.material_pair_identity(color, mask) != key:
                    raise SystemExit("%s: pair key %s does not match its color/mask" % (lg, key))
                out[key] = (color, mask)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--iso", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--log", type=Path, action="append", default=[])
    ap.add_argument("--pair", action="append", default=[], help="COLOR:MASK source image identities")
    ap.add_argument("--file", action="append", default=[], help="source archive (default: the route set)")
    a = ap.parse_args(argv)
    pairs = pairs_from_logs(a.log)
    for p in a.pair:
        color, mask = p.split(":")
        pairs[P.material_pair_identity(color, mask)] = (color, mask)
    if not pairs:
        raise SystemExit("no pairs (no 'pair missing' lines and no --pair)")
    iso = GcIso(str(a.iso))
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp)
        files = []
        for f in a.file or ROUTE_FILES:
            if iso.find(f) is None:
                continue
            (src / f).parent.mkdir(parents=True, exist_ok=True)
            (src / f).write_bytes(iso.read(f))
            files.append(f)
        if a.output.exists():
            shutil.rmtree(a.output)
        rep = P.prepare_model_pairs(src, files, [dict(color=c, mask=m) for c, m in pairs.values()], a.output)
    for r in rep:
        print("%s  color=%s mask=%s  %d B" % (r["key"], r["color"], r["mask"], r["bytes"]))
    print("%d pairs -> %s" % (len(rep), a.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
