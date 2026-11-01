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
attribute the other kinds staged in the same archive (models keep the previous set's provenance).
Byte-following (wep19-26, coordinator 10-26): a set staging a whole file is credited only with the members whose bytes
it changed. A member already present, byte for byte, in the previous set's copy of that file (motion sets included) is
not that set's work: the row walks back to the set that first carried those bytes, and to the stager base rules
(rule 3) when no set changed it. The first set staging a file has no earlier copy to compare and still gets the whole
file; provenance-report.json lists those cases (whole_file_credit). A copy that does not carry the row's bytes at all
(a store kept in a form the stager converts further) proves nothing: that set keeps the credit, as before.
Opt-in (PROVENANCE_FOLLOW_BYTES=1): on the 10-26 recipe it moves 126 model / 28 sound rows from ps2 to gc and ~110
rows to unknown in other lanes' rooms (em11-em17 Ganado archives, st1 objects), so turning it on is a gate decision."""
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


def graft_digests(dar, members):
    """sha256 of each named ETM sub-file body (past its 0x40 record header) in a native room archive, plus the body
    without its zero tail."""
    import struct as _st
    sys.path[:0] = [str(Path(__file__).resolve().parent.parent.parent)]
    import room_smd as _rs
    import ps2_objects as _po
    b = Path(dar).read_bytes()
    _k, size, _d, off = _st.unpack_from('<4I', b, 0x20)
    pay = b[off:off + size]
    etm = next(pay[a:z] for t, a, z in _rs.tagged_entries(pay, '<') if t.rstrip(b'\0') == b'ETM')
    out = set()
    for n, a, z in _po.etm_entries(etm, '<'):
        if n in members:
            body = etm[a + 0x40:z]
            out |= {hashlib.sha256(body).hexdigest(), hashlib.sha256(body.rstrip(b'\0')).hexdigest()}
    # whole tagged entries ("0x20 BIN", lane props-ps2-26: room-archive models grafted as entries)
    for i, (t, a, z) in enumerate(_rs.tagged_entries(pay, '<')):
        if '%#04x %s' % (i + 4, t.rstrip(b'\0').decode('latin1')) in members:
            body = pay[a:z]
            out |= {hashlib.sha256(body).hexdigest(), hashlib.sha256(body.rstrip(b'\0')).hexdigest()}
    return out


GC_MODEL_CACHE = Path(os.environ.get('GC_MODEL_DIGESTS', '/root/rr/state/gc-model-digests.json'))


def gc_model_digests(gc):
    """Blind-spot fix (lane props-ps2-26 10-26): sha256 of every GameCube room model in its native form (le_mirror of
    each room-archive BIN entry and each ETM etc model, with and without its zero tail and 32-byte padding), over every
    room of the GameCube disc. A model row whose bytes are one of these is GameCube data whoever owns the archive: a
    set that stages a whole archive (and says PS2 in its RECIPE) no longer hides the GC models it carries unchanged.
    Cached by ISO size + mtime."""
    import struct as _st
    sys.path[:0] = [str(Path(__file__).resolve().parent.parent.parent)]
    import room_smd as _rs
    import ps2_objects as _po
    st = os.stat(GC_ISO)
    key = '%s:%d:%d:%s' % (GC_ISO, st.st_size, int(st.st_mtime), sha(Path(_po.__file__).read_bytes())[:16])
    try:
        c = json.loads(GC_MODEL_CACHE.read_text())
        if c.get('key') == key:
            return {k: v for k, v in c['digests'].items()}
    except Exception:
        pass
    out = {}

    def add(le, label):
        for v in (le, le.rstrip(b'\0'), le + bytes(_po.al(len(le)) - len(le))):
            out.setdefault(sha(v), label)
    for room, k in gc.rooms():
        try:
            gd = gc.read(k)
            if gd[:32] == _rs.CONTAINER_MAGIC:
                gd = _rs.decode_das(gd)
            ents = _rs.tagged_entries(gd, '>')
        except Exception:
            continue
        for i, (t, a, z) in enumerate(ents):
            t = t.rstrip(b'\0')
            try:
                if t == b'BIN':
                    add(_po.to_le(gd[a:z], hex(i + 4)), '%s %#04x BIN' % (room, i + 4))
                elif t == b'ETM':
                    eb = gd[a:z]
                    for n, s, e in _po.etm_entries(eb, '>'):
                        if n.lower().endswith('.bin'):
                            add(_po.to_le(eb[s + 0x40:e], n), '%s ETM/%s' % (room, n))
            except Exception:
                continue
    try:
        GC_MODEL_CACHE.parent.mkdir(parents=True, exist_ok=True)
        GC_MODEL_CACHE.write_text(json.dumps(dict(key=key, digests=out)))
    except OSError:
        pass
    return out


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


FOLLOW_BYTES = os.environ.get('PROVENANCE_FOLLOW_BYTES') == '1'
_DIGESTS = {}


def file_digests(src, path):
    """sha256 of every catalog member of one staged copy (build_catalog.member_rows; dc/native files whole), or None
    when the copy is not a readable file."""
    key = (str(src), path)
    if key not in _DIGESTS:
        f = Path(src)
        if not f.is_file():
            _DIGESTS[key] = None
        else:
            b = f.read_bytes()
            out = {sha(b)} if path.startswith('dc/native/') else set()
            out |= {sha(data) for _k, _i, data, _s in build_catalog.member_rows(path, b)}
            _DIGESTS[key] = out
    return _DIGESTS[key]


def follow_bytes(sets, path, digest):
    """The non-motion set that produced this member's bytes (wep19-26 byte-following), or None when no set changed
    them (stager base). Returns (store, whole_file) where whole_file says the set is the file's first copy, so its
    credit could not be checked against an earlier copy."""
    for i in range(len(sets) - 1, -1, -1):
        st = sets[i]
        if MOTION_SET.match(st.name):
            continue
        if digest in st.tsv:
            return st, False
        own = file_digests(st.src, path)
        if own is None or digest not in own:
            return st, False  # this copy is not in the staged form: no proof either way, the set keeps the credit
        prev = file_digests(sets[i - 1].src, path) if i else None
        if prev is not None and digest in prev:
            continue          # unchanged by this set: an earlier copy already carried these bytes
        return st, i == 0 or prev is None
    return None, False


REVIEWED = Path(__file__).resolve().parent / 'provenance-reviewed.tsv'


def load_reviewed(path=REVIEWED):
    """Reviewed exact-bytes provenance (lane gc-audit25 10-25): payloads no data-set store attributes (stager base
    files, the oldest readable tex.pak, runtime harvests, sets with no RECIPE) whose bytes were traced to a PS2
    source. A row maps (kind, output_sha256) -> ps2; it never matches other bytes, so a changed payload falls back
    to the rules below. Columns: kind, id, output_sha256, ps2_sha256 (the PS2 source member's bytes), ps2_source,
    evidence (tab separated, '#' comment lines)."""
    out = {}
    if not path.is_file():
        return out
    lines = [l for l in path.read_text().splitlines() if l.strip() and not l.startswith('#')]
    for r in csv.DictReader(lines, delimiter='\t'):
        o, p = (r.get('output_sha256') or '').strip(), (r.get('ps2_sha256') or '').strip()
        if not re.fullmatch(r'[0-9a-f]{64}', o) or not re.fullmatch(r'[0-9a-f]{64}', p):
            raise ValueError('provenance-reviewed.tsv: bad sha row %r' % r)
        out[(r['kind'], o)] = ('ps2', 'reviewed exact bytes: %s (%s)' % (r['ps2_source'], r['evidence']))
    return out


def main(catalog, recipe_conf, out_dir):
    mod, lines = load_t11()
    conf = Path(recipe_conf).read_text()
    # Every DATA= line in order, with "$DATA" expanded (a recipe appends sets: DATA="$DATA,pmgan24,...").
    data = ''
    for m in re.finditer(r'^DATA="([^"]*)"', conf, re.M):
        data = m.group(1).replace('${DATA}', data).replace('$DATA', data)
    names = [n for n in (mod.T17_DATA + ',' + data).split(',') if n]
    stores, overlay, tex_loose, packs, missing_sets = {}, {}, {}, [], []
    grafted = {}
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
            if k == 'graft':
                # member-level graft (t11-fix.py graft_all): the set owns only the grafted members, never the archive
                # (the archive's other members keep their own sets' provenance). A grafted ETM member's catalog row is
                # its body (sub-file past the 0x40 record header); those rows are attributed to the graft set as GC
                # unless its store's provenance.tsv says otherwise.
                for gdest, (gsrc, members) in srcs.items():
                    st = stores.setdefault((n, gsrc), Store(n, gsrc, lines))
                    for dg in graft_digests(gsrc, members):
                        grafted[dg] = st
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
    reviewed = load_reviewed()
    gc_models = gc_model_digests(gc)
    proofs, unknown, counts = [], [], collections.Counter()
    whole_file = collections.Counter()
    for r in rows:
        src = r['source']
        path = src.split('#')[0].lower()
        prov, ev = 'unknown', ''
        rv = reviewed.get((r['kind'], r['sha256']))
        if rv:
            prov, ev = rv
        elif r['kind'] == 'model' and r['sha256'] in gc_models:
            # member bytes, not archive ownership (lane props-ps2-26 10-26): the row IS a GameCube room model
            prov, ev = 'gc', 'member bytes = le_mirror(GameCube %s)' % gc_models[r['sha256']]
        elif r['sha256'] in grafted:
            st = grafted[r['sha256']]
            prov, ev = st.tsv.get(r['sha256'], 'gc'), 'grafted member of set %s (%s)' % (st.name, st.src)
        elif src.startswith('runtime-harvest:'):
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
        elif FOLLOW_BYTES and follow_bytes(overlay.get(path, []), path, r['sha256'])[0] is not None:
            st, whole = follow_bytes(overlay[path], path, r['sha256'])
            prov, ev = st.prov(r['sha256'], gc_file(path))
            if whole and r['sha256'] not in st.tsv:
                whole_file[(st.name, path, prov)] += 1
                ev += ' (first copy of the file: whole-file credit)'
        elif not FOLLOW_BYTES and [st for st in overlay.get(path, []) if not MOTION_SET.match(st.name)]:
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
               counts={'%s/%s' % k: v for k, v in sorted(counts.items())},
               whole_file_credit=['%s %s %s rows=%d' % (k + (v,)) for k, v in sorted(whole_file.items())])
    (out / 'provenance-report.json').write_text(json.dumps(rep, indent=1) + '\n')
    print(json.dumps(rep['counts'], indent=0))
    print('packs', rep['packs'], 'missing sets', missing_sets)


if __name__ == '__main__':
    main(*sys.argv[1:4])
