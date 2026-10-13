#!/usr/bin/env python3
"""Retarget a route fixture's REL overlays (dc/*.ovl) to the arm under test.

Usage: fixture_arm.py <in.json> <out.json> <arm-label> [--warp <warp.txt>]
                      [--programs-dir <programs> | --candidate-dir <candidate>]

Overlays are relocated against the game ELF they were built with. A fixture that pins
dc/em2f.ovl (or pl0f/em22/em2b/pl11) from another arm's programs/candidate-route<X>/ links
that module against the wrong symbol table: the room boots, and the first call into the
module jumps to a stale address (lakerig 2026-10-13: st-lake FAULT in the em2f thread at
pc=00121e40 and in EspTrans after pl0f; texchk N-lake / L-lake / L-lake2). Rooms that never
load those modules (h2, square, r103) hide the mismatch.

Every dc/*.ovl entry is rewritten to programs/candidate-route<arm>/<name>.ovl; the script
refuses if that file does not exist. --warp replaces dc/warp.txt.
"""
import argparse, json, os, re, sys

HW = ('/mnt/c/Game Dev/Emulators/re4-assets-private/world-agent-20260926/'
      'continuation-20260927/playability-r11-r1/programs')


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('src')
    parser.add_argument('dst')
    parser.add_argument('arm')
    parser.add_argument('--warp')
    paths = parser.add_mutually_exclusive_group()
    paths.add_argument('--programs-dir', default=HW)
    paths.add_argument('--candidate-dir')
    args = parser.parse_args(argv[1:])
    src, dst, arm, warp = args.src, args.dst, args.arm, args.warp
    d = json.load(open(src))
    rep = d['replace']
    cand = args.candidate_dir or os.path.join(args.programs_dir, 'candidate-route' + arm)
    n = 0
    for k in sorted(rep):
        if re.fullmatch(r'dc/[a-z0-9_]+\.ovl', k):
            new = os.path.join(cand, os.path.basename(k))
            if not os.path.isfile(new):
                print('fixture_arm: missing %s' % new); return 1
            if rep[k] != new:
                print('fixture_arm: %s %s -> %s' % (k, rep[k], new)); n += 1
            rep[k] = new
    if warp:
        rep['dc/warp.txt'] = warp
    d.setdefault('provenance', {})['fixture_arm'] = {'src': src, 'arm': arm, 'ovl_retargeted': n,
                                                  'candidate_dir': cand}
    json.dump(d, open(dst, 'w'), indent=1)
    print('fixture_arm: %s retargeted=%d' % (dst, n))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
