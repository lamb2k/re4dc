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

Every overlay the candidate holds (dc/<name>.ovl) is also added when the fixture lacks it (ch3found16
2026-10-16): a STAGE_OVL image needs st1_0..st2_3, a ROUTE_* image its enemy overlays, and a fixture written
for an older image halted at boot with "route overlay missing on the disc" (cast16 Zealot runs).

A pinned 1ST_READ.BIN is retargeted to <candidate>/1ST_READ.BIN too; without that file the script refuses (exit 3).

--data <fixture.json> (the recipe's data set, e.g. a T15_DATA package fixture) checks every prepared archive
(em/*.drs) against it: a fixture that pins another lane's prepared archive fails here, loudly, instead of
halting at boot ("invalid prepared enemy motion archive": k6's pl11.drs from an older motion contract).
--allow em/<x>.drs accepts a reviewed difference (repeatable).
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
    parser.add_argument('--data', help='recipe data-set fixture: every em/*.drs must match it')
    parser.add_argument('--allow', action='append', default=[], help='em/<x>.drs allowed to differ from --data')
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
    # A fixture that pins 1ST_READ.BIN (castle r207j) would boot another arm's program with this arm's overlays
    # ("MISSING route overlay built for another program"): retarget it, or refuse when the arm has none.
    if '1ST_READ.BIN' in rep:
        new = os.path.join(cand, '1ST_READ.BIN')
        if not os.path.isfile(new):
            print('fixture_arm: refused: fixture pins 1ST_READ.BIN %s but the arm has no %s' % (rep['1ST_READ.BIN'], new))
            return 3
        if rep['1ST_READ.BIN'] != new:
            print('fixture_arm: 1ST_READ.BIN %s -> %s' % (rep['1ST_READ.BIN'], new)); n += 1
        rep['1ST_READ.BIN'] = new
    added = 0
    if os.path.isdir(cand):
        for f in sorted(os.listdir(cand)):
            if f.endswith('.ovl') and 'dc/' + f not in rep:
                rep['dc/' + f] = os.path.join(cand, f); added += 1
        if added:
            print('fixture_arm: added %d candidate overlays' % added)
        d['remove'] = sorted(set(d.get('remove', [])) - set(rep))
    if args.data:
        base = json.load(open(args.data))['replace']
        bad = [k for k in sorted(rep) if re.fullmatch(r'em/[a-z0-9_]+\.drs', k) and k in base
               and rep[k] != base[k] and k not in args.allow]
        for k in bad:
            print('fixture_arm: PREPARED MISMATCH %s: fixture %s, data set %s' % (k, rep[k], base[k]))
        if bad:
            print('fixture_arm: refused (%d prepared archives differ from %s; --allow to accept)' % (len(bad), args.data))
            return 2
    if warp:
        rep['dc/warp.txt'] = warp
    d.setdefault('provenance', {})['fixture_arm'] = {'src': src, 'arm': arm, 'ovl_retargeted': n, 'ovl_added': added, 'data': args.data,
                                                  'candidate_dir': cand}
    json.dump(d, open(dst, 'w'), indent=1)
    print('fixture_arm: %s retargeted=%d' % (dst, n))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
