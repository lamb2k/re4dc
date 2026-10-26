#!/usr/bin/env python3
"""member_census.py: member-level disc diff gate (lane fix-r100-props26, 2026-10-26).

  member_census.py <ref tree> <cand tree> <claims.tsv> [--json OUT]

Compares two extracted disc trees (fullplay/fp_iso.py extract: the last published release and the candidate) and
judges every difference against a reviewed claims list, so a data set that silently undoes or drops another set's
work fails the gate instead of shipping:
  - every st1/*.dar, st2/*.dar room archive: member by member (tagged entries of the room payload; ETM sub-files
    by name), a changed member is "st1/r100.dar:ETM/et0000.bin", "st1/r100.dar:0x37 ESQ", ...;
  - dc/tex.pak: keys removed, keys whose picture size / format flags changed ("dc/tex.pak:-<key>", ":~<key>");
    added keys are reported only;
  - every other file: added / removed / changed by path.
claims.tsv: one row per claimed change, tab separated: <glob over the item names above> <set or commit> <reason>.
'#' lines are comments. A difference no row claims is UNCLAIMED and fails the gate (exit 1). Prints
"MEMBER-CENSUS PASS|FAIL: n differences, n claimed, n unclaimed" last.
"""
import fnmatch
import hashlib
import json
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent.parent), str(HERE.parent)]
import room_smd as rs  # noqa: E402
import ps2_objects as po  # noqa: E402
import tex_size_check as tsc  # noqa: E402


def payload(dar):
    kind, size, dest, off = struct.unpack_from('<4I', dar, 0x20)
    if kind != 0 or off + size > len(dar):
        return None
    return dar[off:off + size]


def dar_members(b):
    """{member name: sha1} of a room archive payload."""
    pay = payload(b)
    if pay is None:
        return {'(unparsed)': hashlib.sha1(b).hexdigest()}
    out = {}
    for i, (t, s, e) in enumerate(rs.tagged_entries(pay, '<')):
        tag = t.rstrip(b'\0').decode('latin1')
        body = pay[s:e]
        if tag == 'ETM':
            try:
                for n, a, c in po.etm_entries(body, '<'):
                    out['ETM/%s' % n] = hashlib.sha1(body[a:c]).hexdigest()
                continue
            except Exception:
                pass
        out['0x%02x %s' % (i + 4, tag)] = hashlib.sha1(body).hexdigest()
    return out


def diff_tree(ref, cand):
    items = []
    rf = {p.relative_to(ref).as_posix() for p in ref.rglob('*') if p.is_file()}
    cf = {p.relative_to(cand).as_posix() for p in cand.rglob('*') if p.is_file()}
    for f in sorted(rf - cf):
        items.append((f + ':removed', 'file removed'))
    for f in sorted(cf - rf):
        items.append((f + ':added', 'file added'))
    for f in sorted(rf & cf):
        a, b = (ref / f).read_bytes(), (cand / f).read_bytes()
        if a == b:
            continue
        if f.endswith('.dar'):
            ma, mb = dar_members(a), dar_members(b)
            for m in sorted(set(ma) | set(mb)):
                if ma.get(m) != mb.get(m):
                    what = 'added' if m not in ma else 'removed' if m not in mb else 'changed'
                    items.append(('%s:%s' % (f, m), 'member ' + what))
        elif f == 'dc/tex.pak':
            pa, pb_ = tsc.read_pak(ref / f), tsc.read_pak(cand / f)
            for k in sorted(set(pa) - set(pb_)):
                items.append(('%s:-%s' % (f, k), 'key removed'))
            for k in sorted(set(pa) & set(pb_)):
                if pa[k] != pb_[k]:
                    items.append(('%s:~%s' % (f, k), 'key size/format %s -> %s' % (pa[k], pb_[k])))
            print('info: %s keys added %d' % (f, len(set(pb_) - set(pa))))
        else:
            items.append((f + ':changed', 'file changed'))
    return items


def main():
    a = sys.argv[1:]
    js = None
    if '--json' in a:
        i = a.index('--json'); js = a[i + 1]; del a[i:i + 2]
    ref, cand, claims = Path(a[0]), Path(a[1]), Path(a[2])
    rows = []
    for ln in claims.read_text().splitlines():
        if ln.strip() and not ln.startswith('#'):
            p = ln.split('\t')
            rows.append((p[0], p[1] if len(p) > 1 else '?'))
    items = diff_tree(ref, cand)
    res, bad = [], 0
    for name, what in items:
        who = next((s for g, s in rows if fnmatch.fnmatchcase(name, g)), None)
        res.append(dict(item=name, what=what, claimed_by=who))
        if who is None:
            bad += 1
            print('UNCLAIMED %s (%s)' % (name, what))
    if js:
        Path(js).write_text(json.dumps(res, indent=1))
    print('MEMBER-CENSUS %s: %d differences, %d claimed, %d unclaimed'
          % ('PASS' if bad == 0 else 'FAIL', len(items), len(items) - bad, bad))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
