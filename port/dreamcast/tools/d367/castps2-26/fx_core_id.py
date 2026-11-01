#!/usr/bin/env python3
"""fx_core_id.py: one GameCube etc/core.das effect id -> its PS2 Core.dat pictures, under the GC keys (lane cast-ps2-25, 10-26).

fx_ps2_pack.py lib converts only core.das EFF #1 (its 'common' job). The census of r106 / r109 found a picture of
core.das EFF #25 drawing GameCube pixels (ef2f7909-ea057c42: id 0x27 frame 4, the seven-segment digit '4'). This tool
runs fx_ps2_pack's own converter (gc_eff_tables, pair_effs, ps2_eff_textures, convert_set: PAL4 ARGB4444 under the
GameCube keys, cover flags) for the GameCube effect id holding a given key, then replaces those keys in a base tex.pak
(fx_ps2_pack pack semantics: base key bytes replaced, nothing else moves; texpack.build).

  python3 fx_core_id.py <GC etc/core.das> <PS2 Core.dat> <key> <base tex.pak> <out dir>
      -> <out dir>/dc/tex.pak, pak-derived.json, report.json, re4tex/<key>.re4tex
"""
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'test12fx'))
sys.path.insert(0, str(HERE.parent))
import fx_ps2_pack as F  # noqa: E402
import tex_merge  # noqa: E402
import texpack  # noqa: E402


def main():
    gc_core, ps2_core, want, base_path, out = sys.argv[1:6]
    gc_core, out = Path(gc_core), Path(out)
    gc_ids, gc_tpls = F.gc_eff_tables(gc_core.parent, [gc_core.name], 'etc/core.das')
    hits = []
    for ctx, ids in gc_ids.items():
        for n, tid in enumerate(ids):
            if want in [k for k, w, h in gc_tpls.get('%s/tpl%d' % (ctx, n), [])]:
                hits.append((ctx, tid, n))
    if len(hits) != 1:
        raise SystemExit('key %s: %d GameCube core.das effect ids hold it' % (want, len(hits)))
    ctx, tid, n = hits[0]
    blob = Path(ps2_core).read_bytes()
    ps2_effs = {}
    for k, (ty, s0, s1) in enumerate(F.dat_entries(blob)):
        if ty == 'EFF':
            try:
                ps2_effs[k] = F.ps2_eff_textures(blob[s0:s1])
            except (ValueError, IndexError) as ex:
                print('PS2 Core.dat entry %d skipped (%s)' % (k, ex))
    ent = dict(F.pair_effs({ctx: gc_ids[ctx]}, ps2_effs))[ctx]
    if ent is None or tid not in ps2_effs.get(ent, {}):
        raise SystemExit('%s id %#x: no PS2 counterpart' % (ctx, tid))
    texdir = out / 're4tex'
    rows = F.convert_set(ctx, [tid], {'%s/tpl0' % ctx: gc_tpls['%s/tpl%d' % (ctx, n)]}, ps2_effs[ent],
                         'Core.dat:%d' % ent, texdir, {})
    base = tex_merge.read(base_path)
    merged, changed, added = dict(base), [], []
    for f in sorted(texdir.glob('*.re4tex')):
        key = tuple(int(v, 16) for v in f.stem.split('-'))
        data = f.read_bytes()
        if base.get(key) != data:
            (changed if key in base else added).append(f.stem)
        merged[key] = data
    pak, count = texpack.build(merged)
    (out / 'dc').mkdir(parents=True, exist_ok=True)
    (out / 'dc' / 'tex.pak').write_bytes(pak)
    sha = lambda b: hashlib.sha256(b).hexdigest()
    side = dict(base=sha(Path(base_path).read_bytes()), out=sha(pak), count=count, added=added, changed=changed)
    (out / 'pak-derived.json').write_text(json.dumps(side, indent=1))
    (out / 'report.json').write_text(json.dumps(dict(gc=ctx, id=tid, gc_tpl=n, ps2='Core.dat entry %d' % ent,
                                                     rows=rows, keys=[f.stem for f in sorted(texdir.glob('*.re4tex'))]), indent=1))
    print('%s id %#x <- PS2 Core.dat EFF entry %d: %d keys replaced, %d added; out %s' % (ctx, tid, ent, len(changed), len(added), side['out'][:16]))


if __name__ == '__main__':
    main()
