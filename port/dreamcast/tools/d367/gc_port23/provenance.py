#!/usr/bin/env python3
"""provenance.py CATALOG.json RECIPE.conf OUT_DIR : GC-ASSET provenance proofs from the data-set stores.

gc-catalog24b (coordinator 10-24, round 7 item 2): every catalog row gets ps2 / gc / authored ("derived": our
tools' output with no source) where the stores say so; the rest stays unknown and is listed.

Rules, in order, per row (source = disc path of the payload):
  1. dc/tex.pak members: the tex.pak chain of the data sets (t11-fix T17_DATA then recipe DATA, in order) is
     diffed key by key; a key takes the provenance of the last set that changed its bytes. Keys already in
     the oldest readable pack are unattributed (unknown). Loose dc/tex*/ keys: the last set staging that key.
  2. a disc path staged by a data set: the set's store. provenance.tsv (a converter's member table) decides
     by output sha256 (ps2 when the row names a PS2 member, else gc); otherwise the store RECIPE (or, with no
     RECIPE: PS2 sources -> ps2; a set with no RECIPE whose t11-fix comments name a PS2 source -> unknown
     (listed); otherwise authored, which is gc for a GameCube disc file or a GameCube picture key.
  3. a disc path no set stages: on the GameCube disc (debug disc 1 FST) -> gc (stager conversion of the GC
     file); a ps2-world.* file -> ps2; other dc/ outputs -> authored; else unknown.
Runtime-harvest rows (fonts, layout) stay unknown.
Motion rows (kind=motion, one per FCV/SEQ clip key; gc-catalog24b round 8): only the PS2 motion stores (data sets
named pm*: pmleon24b, pmgan24, pmwep24b) attribute motion, by their RECIPE; a key those stores' archives or dc/mot
keys carry is ps2 wherever it sits; any other clip in a GameCube disc file is gc. The motion stores never
attribute the other kinds staged in the same archive (models keep the previous set's provenance)."""
import collections, csv, hashlib, importlib.util, io, json, os, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / 'd367/gc_port23'))
from assetpipe.rooms import GcIso  # noqa: E402
import build_catalog  # noqa: E402

GC_ISO = '/root/work/re4-dreamcast/orig/G4BE08/re4_debug_disc1.iso'
PS2 = re.compile(r'\bPS2\b|ps2|PCSX2|BIO4DAT|SLUS')
sha = lambda b: hashlib.sha256(b).hexdigest()
MOTION_SET = re.compile(r'^pm')


def motion_keys(store):
    """Clip keys a motion store's outputs carry (archives as staged + dc/mot key files)."""
    keys = set()
    root = Path(store.src)
    root = root if root.is_dir() else root.parent
    for f in root.rglob('*'):
        if not f.is_file():
            continue
        if f.suffix == '.fcv' and re.fullmatch(r'[0-9a-f]{8}-[0-9a-f]{8}', f.stem):
            keys.add(f.stem); continue
        if f.suffix.lower() not in ('.drs', '.dar', '.das', '.dat'):
            continue
        b = f.read_bytes()
        bodies = [b] + ([b[build_catalog.DRS_TABLE:]] if f.suffix == '.drs' and len(b) > build_catalog.DRS_TABLE else [])
        bodies += [body for _at, body in build_catalog.record_bodies(b)]
        for body in bodies:
            keys.update(k for k, _ in build_catalog.motion_clips(body))
    return keys


def load_t11():
    path = HERE / 'd367/test11/t11-fix.py'
    spec = importlib.util.spec_from_file_location('t11fix', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod, path.read_text().splitlines()


def comment_for(lines, name):
    """The comment block above the set's definition plus every comment line naming the set."""
    pat = re.compile(r"DATA\[['\"]%s['\"]\]\s*=|['\"]%s['\"]\s*:\s*\{" % (re.escape(name), re.escape(name)))
    word = re.compile(r'(?<![\w-])%s(?![\w-])' % re.escape(name))
    out = [l for l in lines if l.lstrip().startswith('#') and word.search(l)]
    for i, line in enumerate(lines):
        if pat.search(line):
            j = i - 1
            while j >= 0 and lines[j].lstrip().startswith('#'):
                out.append(lines[j]); j -= 1
            out.append(line)
            break
    return '\n'.join(out)


def store_files(src):
    p = Path(src)
    for d in [p if p.is_dir() else p.parent] + list((p if p.is_dir() else p.parent).parents)[:4]:
        found = {}
        for n in ('provenance.tsv', 'RECIPE.txt', 'RECIPE.md', 'RECIPE'):
            if (d / n).is_file():
                found[n] = d / n
        if found:
            return d, found
    return None, {}


class Store:
    def __init__(self, name, src, lines):
        self.name, self.src = name, src
        self.root, files = store_files(src)
        self.tsv = {}
        if 'provenance.tsv' in files:
            for r in csv.DictReader(io.StringIO(files['provenance.tsv'].read_text(errors='replace')), delimiter='\t'):
                out = (r.get('output_sha256') or '').strip()
                if out:
                    self.tsv[out] = 'ps2' if (r.get('ps2_sha256') or '').strip() else 'gc'
        recipe = next((files[n] for n in ('RECIPE.txt', 'RECIPE.md', 'RECIPE') if n in files), None)
        if recipe:
            text, self.why = recipe.read_text(errors='replace'), 'recipe=%s' % recipe
        else:
            text, self.why = comment_for(lines, name), 't11-fix comment of %s' % name
        # Only a store RECIPE (or provenance.tsv) proves ps2: a comment that names a
        # PS2 source leaves the set unknown (listed), never ps2 (which hides rows).
        if PS2.search(text):
            self.level = 'ps2' if recipe else 'unknown'
        else:
            self.level = 'authored'

    def prov(self, digest, gc_file=None, texture=False):
        if digest in self.tsv:
            return self.tsv[digest], 'set=%s provenance.tsv=%s' % (self.name, self.root)
        if self.level == 'authored' and gc_file:
            return 'gc', 'set=%s (no PS2 source; %s) reprocesses GameCube file %s' % (self.name, self.why, gc_file)
        if self.level == 'authored' and texture:
            return 'gc', 'set=%s (no PS2 source; %s): GameCube picture key' % (self.name, self.why)
        return self.level, 'set=%s %s' % (self.name, self.why)


def main(catalog, recipe_conf, out_dir):
    mod, lines = load_t11()
    conf = Path(recipe_conf).read_text()
    # Every DATA= line in order, with "$DATA" expanded (a recipe appends sets: DATA="$DATA,pmgan24,...").
    data = ''
    for m in re.finditer(r'^DATA="([^"]*)"', conf, re.M):
        data = m.group(1).replace('${DATA}', data).replace('$DATA', data)
    names = [n for n in (mod.T17_DATA + ',' + data).split(',') if n]
    stores, overlay, tex_loose, packs, missing_sets = {}, {}, {}, [], []
    for n in names:
        if n not in mod.DATA:
            missing_sets.append(n); continue
        for k, srcs in mod.DATA[n].items():
            if k == 'tex':
                for src in ([srcs] if isinstance(srcs, str) else list(srcs)):
                    st = stores.setdefault((n, src), Store(n, src, lines))
                    if os.path.isdir(src):
                        for f in Path(src).rglob('*.re4tex'):
                            tex_loose[f.stem.lower()] = st
                continue
            src = srcs if isinstance(srcs, str) else list(srcs)[-1]
            st = stores.setdefault((n, src), Store(n, src, lines))
            overlay.setdefault(k.lower(), []).append(st)
            if k.lower() == 'dc/tex.pak' and os.path.isfile(src):
                packs.append(st)
    tex_owner, first_pack = {}, None
    prev = None
    for st in packs:
        cur = {i: sha(d) for i, d, _o, _s in build_catalog.texpak_members(Path(st.src).read_bytes())}
        if prev is None:
            first_pack = st.name
        else:
            for k, h in cur.items():
                if prev.get(k) != h:
                    tex_owner[k] = st
        prev = cur
    ps2_motion = {}
    for st in stores.values():
        if MOTION_SET.match(st.name) and st.level == 'ps2':
            for k in motion_keys(st):
                ps2_motion.setdefault(k, st)
    gc = GcIso(GC_ISO)

    def gc_file(path):
        hit = gc.find(path)
        if hit is None and path.endswith(('.arc', '.dar')):
            hit = gc.find(path[:-4] + '.das')
        return hit
    rows = json.loads(Path(catalog).read_text())['entries']
    proofs, unknown, counts = [], [], collections.Counter()
    for r in rows:
        src = r['source']
        path = src.split('#')[0].lower()
        prov, ev = 'unknown', ''
        if src.startswith('runtime-harvest:'):
            ev = 'runtime harvest'
        elif r['kind'] == 'texture' and path == 'dc/tex.pak':
            st = tex_owner.get(r['id'].lower())
            if st:
                prov, ev = st.prov(r['sha256'], texture=True)
                ev = 'tex.pak key changed by ' + ev
            else:
                ev = 'tex.pak key unchanged since the oldest readable pack (%s)' % first_pack
        elif r['kind'] == 'texture' and r['id'].lower() in tex_loose and path.startswith('dc/tex'):
            prov, ev = tex_loose[r['id'].lower()].prov(r['sha256'], texture=True)
        elif r['kind'] == 'motion':
            motion_sets = [st for st in overlay.get(path, []) if MOTION_SET.match(st.name)]
            if motion_sets:
                prov, ev = motion_sets[-1].prov(r['sha256'])
                ev = 'motion ' + ev
            elif r['id'] in ps2_motion:
                prov, ev = 'ps2', 'motion key carried by PS2 motion set %s (%s)' % (ps2_motion[r['id']].name, ps2_motion[r['id']].why)
            elif gc_file(path) is not None:
                prov, ev = 'gc', 'GameCube motion: clip of GameCube disc file %s, no PS2 motion set stages it' % gc_file(path)
            else:
                ev = 'motion clip: no PS2 motion set, not on the GameCube disc'
        elif [st for st in overlay.get(path, []) if not MOTION_SET.match(st.name)]:
            st = [st for st in overlay[path] if not MOTION_SET.match(st.name)][-1]
            prov, ev = st.prov(r['sha256'], gc_file(path))
        elif gc_file(path) is not None:
            prov, ev = 'gc', 'stager base: GameCube disc file %s' % gc_file(path)
        elif 'ps2-world.' in path:
            prov, ev = 'ps2', 'PS2 world package (stager base)'
        elif path.startswith('dc/') and not path.startswith('dc/movie/'):
            prov, ev = 'authored', 'our tools output (stager base), no data set'
        else:
            ev = 'no data set, not on the GameCube disc'
        counts[(r['kind'], prov)] += 1
        if prov == 'unknown':
            unknown.append((r['kind'], r['id'], r['sha256'], src, ev))
        else:
            proofs.append(dict(kind=r['kind'], id=r['id'], sha256=r['sha256'], provenance=prov, evidence=ev))
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    (out / 'proofs.json').write_text(json.dumps(dict(schema=1, entries=proofs), indent=1, sort_keys=True) + '\n')
    with open(out / 'unknown-rows.tsv', 'w') as f:
        f.write('kind\tid\tsha256\tsource\twhy\n')
        for u in unknown:
            f.write('\t'.join(u) + '\n')
    rep = dict(sets=names, sets_not_in_t11=missing_sets, packs=[s.name for s in packs], first_pack=first_pack,
               counts={'%s/%s' % k: v for k, v in sorted(counts.items())})
    (out / 'provenance-report.json').write_text(json.dumps(rep, indent=1) + '\n')
    print(json.dumps(rep['counts'], indent=0))
    print('packs', rep['packs'], 'missing sets', missing_sets)


if __name__ == '__main__':
    main(*sys.argv[1:4])
