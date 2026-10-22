#!/usr/bin/env python3
"""PS2 world coverage registry (WSL): which rooms have a loadable native PS2 world package, from validated packages.

For every room on the configured sources (GC debug disc 1 St1/St2/St4 rooms, the PS2 disc's AFS rooms) it picks the
room's package, in this order: a --package override; the first current play fixture that stages the room's world
(PLAY_FIXTURES: title-c14-pak, then title-c13-pw), exactly as that fixture stages it; a guarded rebuild
<--package-root>/<room>-ps2-uvg; the package most route fixtures stage; else the converter output in a corpus (<corpus>/out/<room>-ps2, the ps2rooms lane's `ps2_room_r4im.py
--color-light ps2` rule). Every other fixture staging of the room with other mesh / sidecar bytes is listed under
package.conflicts (never counted as evidence for the selected package). It validates the package and writes:

  <out>/world-coverage.json   machine-readable manifest (schema re4dc-world-coverage/1): per room the sources and
                              their hashes, the package and its validation, staging, runtime registration, runtime
                              evidence (route runs whose staged disc carried this exact package) and blockers
  <out>/world-coverage.md     the same as a table
  --inc PATH                  the runtime room bitmap for PS2_WORLD_REGISTRY=1 (game/platform/include/
                              ps2_world_rooms.inc): every room whose package passed validation

Validation (a package is loadable only if all pass):
  runtime open   ps2_world_check (built from this directory's .cpp with the runtime's own MeshPackage::adopt and
                 ps2_open's R4PW checks): the same accept/reject and reason the game logs ("PS2MESH open failed: ...")
  textures       every part's texture loads the way the game loads it (tex_package_error: open_streamed + validate()
                 rules, payload CRC, and textures()[0] exactly the part's size); each file's sha256 is recorded. The
                 bytes: for a fixture-selected package, what that fixture's disc holds (Fixture.texture: the staged
                 dc/tex.pak member for a TEX_PACK=1 image, else the loose dc/tex file: fixture, media overlay or base
                 disc, unless the fixture removes it); otherwise the package's tex/
  identity       the room's own PS2 route graph points (aux/<room>/*.RTP) and every GC door arrival into the room
                 (stage_route.py scan of the GC disc) lie inside the package's placed world box (+2 m)
  provenance     fail closed (check_provenance): the converter report ps2-world.json names these package hashes, its
                 input directory exists, an extraction manifest record lists the inputs and matches the PS2 disc's
                 AFS member, and every listed input has the listed sha256. LEGACY waives this only for the exact
                 (re4mesh, r4pw) pair it names.
Runtime evidence: scenarios that opened the room's package; a run proves the package only if its payload-manifest.json
staged the same mesh and sidecar sha256 and the game read the same bytes for every part texture: resolved with the
tested image's knobs (its route-build resolved-knobs.txt, bound by the ELF sha256) and native_ui.cpp's precedence
(select_texture: Standard texlow key, else the dc/tex.pak member when TEX_PACK=1 and the staged pack is valid and
holds the key, else the loose file), the pack's bytes recovered from the fixture source or base disc and checked
against the staged sha256 and the run's "tex pack:" log line. Anything that cannot be established leaves the run
unverified with the reason. Recorded: arm, ELF, knobs, pack, texture sources, fixture, warp start / placement and
sampled poses, PS2MESH open / frame / fallback / abort lines, HALT and MISSING. A clean run proves submission for the
views it saw, not every placement or pose.
States (rec['states'], each against the selected package's re4mesh + r4pw + texture-set sha256): registered (passes
validation; in_inc: listed in the runtime .inc given with --inc-check), staged (fixtures whose disc holds exactly these
bytes), entered (runs that staged them and opened the package), drawn (clean runs), reviewed (--reviews records
naming the same three hashes; a review of other bytes is listed as stale, not counted).

usage: world_registry.py [--out DIR] [--inc PATH] [--corpus DIR ...] [--evidence-glob 'route-*' ...]
                         [--package ROOM=DIR ...] [--play-fixture JSON ...] [--reviews JSON] [--inc-check PATH]
Re-running with the same inputs gives the same manifest except 'generated'.
"""
import argparse, collections, glob, hashlib, json, os, re, struct, subprocess, sys, time, zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parents[1]                       # port/dreamcast/tools
REPO_DC = HERE.parents[2]                     # port/dreamcast
sys.path[:0] = [str(TOOLS), str(TOOLS / 'd367'), str(REPO_DC.parents[1] / 'tools')]
PRIV = Path('/mnt/c/Game Dev/Emulators/re4-assets-private')
HARNESS = PRIV / 'world-agent-20260926/continuation-20260927/playability-r11-r1'
CORPORA = [PRIV / 'ps2rooms-20260930',
           PRIV / 'architect-review-20261003/tools/supervisor-20261003/world-coverage/ps2rooms-st24']
BASE_MANIFEST = Path('/root/probe/d367-resume-20260927/integration-01/disc-ig27rc1-kite7/payload-manifest.json')
GC_ISO = Path('/root/work/re4-dreamcast/orig/G4BE08/re4_debug_disc1.iso')
PS2_ISO = Path('/mnt/c/Game Dev/Emulators/re4_helpers/Resident Evil 4 (USA)/Resident Evil 4 (USA).iso')
NATIVE_STATIC = REPO_DC / 'game/platform/native_static.cpp'
CACHE = Path(os.environ.get('WORLD_REGISTRY_CACHE', '/root/probe/sup-world-coverage-20261003/cache'))
TOUR = HARNESS / 'tour'
ROUTE_FIXTURES = TOOLS / 'd367/route/fixtures'  # repo copies of tour/ route fixtures (paths relative to tour/)
# The current play discs' fixtures in precedence order (docs/D367_PLAY_BUILD_CHECKLIST.md "Texture pack"): title-c14-pak
# is title-c13-pw packed (TEX_PACK=1; packed loose files removed); both stage the --lod-uv-guard worlds.
PLAY_FIXTURES = [TOUR / 'play/title-c14-pak.json', TOUR / 'play/title-c13-pw.json']
OVERLAY = Path('/mnt/c/Flycast-Evidence/re4-dreamcast/r11-media-overlay-r1/payloads')  # stage-scenario.py --overlay
BASE_DISC = BASE_MANIFEST.parent / 'disc.bin'
MARGIN = 2000.0                               # mm around the placed world box for the identity checks
MAX_TEX = 1024


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def checker():
    """Build ps2_world_check (host g++) when the .cpp or the runtime header changed."""
    src = HERE / 'ps2_world_check.cpp'
    deps = [src, REPO_DC / 'room/instanced_mesh.hpp', REPO_DC / 'room/room_package.hpp']
    tag = hashlib.sha256(b''.join(p.read_bytes() for p in deps)).hexdigest()[:16]
    exe = CACHE / f'ps2_world_check-{tag}'
    if not exe.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        subprocess.run(['g++', '-std=c++17', '-O1', '-DRE4DC_TREE_IMPOSTOR=1', '-DRE4DC_MESH_TEXTURES=1',
                        '-I', str(HERE / 'hostinc'), '-I', str(REPO_DC / 'room'), str(src), '-o', str(exe)], check=True)
    return exe, sha(src)


def run_check(exe, mesh, side):
    p = subprocess.run([str(exe), str(mesh), str(side)], capture_output=True, text=True)
    return json.loads(p.stdout)


def hand_list():
    text = NATIVE_STATIC.read_text()
    m = re.search(r'extern "C" int re4dc_ps2_world_room\(unsigned room\)\{\s*return (room==0x[^;]+);', text)
    return sorted('r%03x' % int(x, 16) for x in re.findall(r'room==0x([0-9a-f]+)', m.group(1)))


# The door-arrival parser: stage_route.scan and what it reads with. The gc-doors cache is keyed by these files' hashes
# plus the disc's sha256, so other media or a changed parser never reuse another scan.
ARRIVAL_PARSER = [TOOLS / 'd367/stage_route.py', TOOLS / 'room_smd.py', TOOLS / 'assetpipe/rooms.py']


def gc_rooms_and_arrivals(iso_path=None, cache_dir=None):
    """GC disc 1: the St1/St2/St4 rooms and every door arrival position (stage_route.scan), cached under
    gc-doors-<disc sha256[:16]>-<parser sha256[:16]>.json (the disc is hashed on every run)."""
    iso_path, cache_dir = Path(iso_path or GC_ISO), Path(cache_dir or CACHE)
    iso_sha = sha(iso_path)
    parser = {str(p.relative_to(TOOLS)): sha(p) for p in ARRIVAL_PARSER}
    parser_sha = hashlib.sha256(json.dumps(parser, sort_keys=True).encode()).hexdigest()
    cache = cache_dir / f'gc-doors-{iso_sha[:16]}-{parser_sha[:16]}.json'
    if cache.exists():
        d = json.loads(cache.read_text())
        if d.get('iso_sha256') == iso_sha and d.get('parser_sha256') == parser_sha:
            return d
    import stage_route
    from assetpipe.rooms import GcIso
    iso = GcIso(str(iso_path))
    rooms = sorted(r for r, _ in iso.rooms())
    arrivals = collections.defaultdict(list)
    for stage in sorted({int(r[1], 16) for r in rooms}):
        for src, rec in stage_route.scan(iso, stage).items():
            for d in rec['doors']:
                arrivals[d['dst']].append(dict(src=src, door=d['no'], pos=d['pos']))
    out = dict(iso=str(iso_path), iso_sha256=iso_sha, iso_bytes=iso_path.stat().st_size, parser=parser,
               parser_sha256=parser_sha, rooms=rooms, arrivals=arrivals)
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(out, indent=1))
    return out


def ps2_rooms():
    import ps2_room_extract as px
    with px.ISO.open('rb') as f:
        index, index_sha = px.afs_index(f)
    return {n[:-4]: v for n, v in index.items() if re.fullmatch(r'r[0-9a-f]{3}\.dat', n)}, index_sha


def rtp_points(aux):
    pts = []
    for p in sorted(aux.glob('*.RTP')) if aux and aux.exists() else []:
        d = p.read_bytes()
        if d[:4] != b'PTR2':
            continue
        n = struct.unpack_from('<H', d, 6)[0]
        pts += [struct.unpack_from('<3f', d, 0x20 + 32 * i) for i in range(n)]
    return pts


def inside(pos, lo, hi):
    return all(lo[a] - MARGIN <= pos[a] <= hi[a] + MARGIN for a in (0, 2))   # x / z: the plan


_BASE_ISO = []
_SHA = {}


def sha_cached(path):
    path = Path(path)
    if path not in _SHA:
        _SHA[path] = sha(path) if path.is_file() else None
    return _SHA[path]


def base_disc_bytes(disc_path):
    """The base disc's file at `disc_path` (joliet), or None."""
    if not BASE_DISC.is_file():
        return None
    import io, pycdlib  # only with a base disc: hosts without pycdlib still run the tests
    if not _BASE_ISO:
        iso = pycdlib.PyCdlib()
        iso.open(str(BASE_DISC))
        _BASE_ISO.append(iso)
    buf = io.BytesIO()
    try:
        _BASE_ISO[0].get_file_from_iso_fp(buf, joliet_path='/' + disc_path)
    except Exception:
        return None
    return buf.getvalue()


def pack_index(blob):
    """key -> (offset, size) of a tex.pak's members, validated with texpack.verify; None if invalid."""
    import texpack
    try:
        count, _ = texpack.verify(blob)
    except SystemExit:
        return None
    return {'%08x-%08x' % struct.unpack_from('<2I', blob, 2048 + 16 * i):
            struct.unpack_from('<2I', blob, 2048 + 16 * i + 8) for i in range(count)}


class Fixture:
    """A stage-scenario.py fixture as a disc staged from it holds it: replace sources (relative to the fixture's own
    directory, as stage-scenario.py resolves them; the repo copies under tools/d367/route/fixtures are copies of tour/
    fixtures, so relative to tour/), then the fixture's removals, the media overlay and the base disc."""

    def __init__(self, path, play=False):
        self.path, self.name, self.play = Path(path), Path(path).name, play
        d = json.loads(self.path.read_text())
        base = TOUR if ROUTE_FIXTURES in self.path.parents else self.path.parent
        self.replace = {k: Path(os.path.normpath(v if v.startswith('/') else base / v))
                        for k, v in d.get('replace', {}).items()}
        self.remove = set(d.get('remove') or [])
        self._pack = None

    def read(self, disc_path):
        """(bytes or None, origin) of the disc's file at disc_path."""
        if disc_path in self.replace:
            src = self.replace[disc_path]
            return (src.read_bytes() if src.is_file() else None), 'fixture %s' % src
        if disc_path in self.remove:
            return None, 'removed by the fixture'
        if (OVERLAY / disc_path).is_file():
            return (OVERLAY / disc_path).read_bytes(), 'media overlay'
        b = base_disc_bytes(disc_path)
        return b, 'base disc' if b is not None else 'absent'

    def pack(self):
        """(blob, index, origin) of the staged dc/tex.pak, (None, None, reason) without a usable one."""
        if self._pack is None:
            blob, origin = self.read('dc/tex.pak')
            if blob is None:
                self._pack = (None, None, 'no dc/tex.pak (%s)' % origin)
            else:
                idx = pack_index(blob)
                self._pack = (blob, idx, origin) if idx is not None else (None, None, 'dc/tex.pak INVALID (%s)' % origin)
        return self._pack

    def texture(self, key):
        """(bytes or None, source) a TEX_PACK=1 play image reads for texture `key` (select_texture: the pack member
        when the staged pack holds the key, else the loose file). A TEX_PACK=0 image never stages a pack here."""
        blob, idx, origin = self.pack()
        if idx is not None and key in idx:
            off, size = idx[key]
            return blob[off:off + size], 'pack member (%s)' % origin
        return self.read(f'dc/tex/{key[0]}/{key}.re4tex')


def fixture_staging(play_fixtures=None, fixture_dirs=()):
    """(room -> [staging], room -> fixtures staging its room container, play Fixture list). A staging: one fixture's
    world for the room (its own re4mesh and r4pw entries and their sha256). Fixtures: the play fixtures, the tour/
    route fixtures, the repo copies (a name already read from tour/ is skipped), the play staging base
    tour/rel-r103-entry-pw.json and every *.json of `fixture_dirs` (a lane's own fixtures, --fixture-dir)."""
    plays = [Fixture(f, play=True) for f in (play_fixtures or PLAY_FIXTURES) if Path(f).is_file()]
    others, seen = [], {f.name for f in plays}
    extra = [f for d in fixture_dirs for f in sorted(Path(d).glob('*.json'))]
    for f in sorted(TOUR.glob('route-*.json')) + sorted(ROUTE_FIXTURES.glob('*.json')) + [TOUR / 'rel-r103-entry-pw.json'] + extra:
        if f.is_file() and f.name not in seen:
            seen.add(f.name)
            others.append(Fixture(f))
    pkg, rooms = collections.defaultdict(list), collections.defaultdict(list)
    for fx in plays + others:
        for k, src in fx.replace.items():
            m = re.fullmatch(r'dc/native/(r[0-9a-f]{3})/ps2-world\.re4mesh', k)
            if m:
                side = fx.replace.get(f'dc/native/{m.group(1)}/ps2-world.r4pw')
                pkg[m.group(1)].append(dict(fixture=fx, re4mesh=src, r4pw=side, re4mesh_sha256=sha_cached(src),
                                            r4pw_sha256=sha_cached(side) if side else None))
            m = re.fullmatch(r'st\d/(r[0-9a-f]{3})\.dar', k)
            if m:
                rooms[m.group(1)].append(fx.name)
    return pkg, rooms, plays


def tex_source(room_pkg_dir, key, replace):
    name = f'{key[0]}-{key[1]}.re4tex'
    p = room_pkg_dir / 'tex' / name
    if p.exists():
        return p
    v = replace.get(f'dc/tex/{name[0]}/{name}') if replace else None
    if v:
        q = Path(v) if v.startswith('/') else HARNESS / 'tour' / v
        return Path(os.path.normpath(q))
    return None


TEX_CRC_DATA_NOTE = ('payload_crc32 covers the texel data only (ps2_room_r4im.py emit), not every byte after the header '
                     '(texture_package.cpp, convert_tpl.py, stage.sh): loads in TEX_RESIDENT=1 images without '
                     'TEX_PAYLOAD_CRC (the runtime skips the CRC), refused by TEX_PAYLOAD_CRC=1 or non-resident images '
                     'and by stage.sh\'s staging check')


def _texture_feature_error(*, pal4_alpha=False, cast_mipmap=False,
                           twiddled_mipmap=False, pal4_mipmap=False,
                           pal8_alpha=False, pal8_mipmap=False):
    if ((twiddled_mipmap and not cast_mipmap) or
            (pal4_mipmap and not (pal4_alpha and cast_mipmap)) or
            (pal8_alpha and not pal4_alpha) or
            (pal8_mipmap and not (pal8_alpha and cast_mipmap))):
        return 'inconsistent native texture feature options'
    return None


def tex_package_error(b, width, height, *, pal4_alpha=False, cast_mipmap=False,
                      twiddled_mipmap=False, pal4_mipmap=False, pal8_alpha=False,
                      pal8_mipmap=False):
    """(None, crc rule) if the RE4DCTX bytes `b` load the way the game loads a PS2 part texture, else (reason, None).

    The game opens /cd/dc/tex/<c>/<crc>-<fnv>.re4tex with texture::Package::open_streamed (native_ui.cpp
    RE4DC_OPEN_PACKAGE), which needs: the streamed metadata layout (descriptor table right after the 48-byte header,
    at most 64 KiB, before the data), every descriptor in a native layout (twiddled or VQ, not linear), and
    validate()'s per-texture rules (power-of-two 8..1024 sides, payload <= VQ, reserved 0, exact size: VQ 2048 +
    w*h/4, PAL4 VQ 2048 + w*h/16 + 32 (TREE_IMPOSTOR=1, which every PS2_WORLD_DRAW image has), else w*h*2; format <=
    ARGB4444 or PAL4; inside the data range). Then re4dc_ps2_world_direct_begin draws the part only if textures()[0]
    is exactly the part's width x height. Integrity: payload_crc32 must equal the CRC32 of every byte after the header
    (the runtime rule, crc rule 'header') or, the PS2 converter's rule, of the data range when it ends the file
    (crc rule 'data', TEX_CRC_DATA_NOTE). Either catches a truncated or altered payload.
    Format4 requires explicit pal4_alpha=True, corresponding to TEX_PAL4_ALPHA=1;
    its base-level twiddled payload is w*h/2 index bytes plus 32 palette bytes.
    PAL8 and each mip family require the corresponding explicit runtime features;
    none is inferred from a filename or accepted merely because its CRC passes."""
    feature_error = _texture_feature_error(pal4_alpha=pal4_alpha, cast_mipmap=cast_mipmap,
        twiddled_mipmap=twiddled_mipmap, pal4_mipmap=pal4_mipmap,
        pal8_alpha=pal8_alpha, pal8_mipmap=pal8_mipmap)
    if feature_error:
        return feature_error, None
    if len(b) < 48:
        return 'shorter than the header', None
    magic, version, hsize, stride, count, toff, doff, dsize, pcrc, _nsrc, _flags = struct.unpack_from('<8s10I', b)
    if magic != b'RE4DCTX\0' or version != 2 or hsize != 48:
        return 'magic, version or header size', None
    prefix = toff + count * stride
    if stride != 96 or toff != 48 or not count or prefix > 64 * 1024 or prefix > len(b) or doff < prefix:
        return 'streamed metadata layout', None
    if doff < 48 or doff + dsize > len(b):
        return 'data range outside the file', None
    if zlib.crc32(b[48:]) == pcrc:
        rule = 'header'
    elif doff + dsize == len(b) and zlib.crc32(b[doff:]) == pcrc:
        rule = 'data'
    else:
        return 'payload CRC32 (neither rule)', None
    for i in range(count):
        tw, th, fmt, off, size, _fl, payload, reserved = struct.unpack_from('<8I', b, toff + 96 * i + 64)
        dims = 8 <= tw <= 1024 and 8 <= th <= 1024 and not tw & (tw - 1) and not th & (th - 1)
        mip = bool(_fl & 4)
        pal4 = fmt == 3 and payload == 2 and not mip
        alpha4 = pal4_alpha and fmt == 4 and payload == 1 and (not mip or pal4_mipmap)
        alpha8 = (pal8_alpha and fmt == 5 and payload == 1 and tw == th and
                  not (_fl & (1 << 30)) and (not mip or pal8_mipmap))
        if mip:
            supported = (fmt <= 2 and (payload == 2 or payload == 1 and twiddled_mipmap) or
                         alpha4 and pal4_mipmap or alpha8 and pal8_mipmap)
            if not (dims and tw == th and cast_mipmap and supported):
                return 'descriptor %d: unsupported native mip family' % i, None
        pixels = tw * th
        if alpha8:
            expected = (pixels * 4 // 3 + 3 if mip else pixels) + 512
        elif alpha4:
            expected = (pixels * 4 // 3 + 3) // 2 + 32 if mip else pixels // 2 + 32
        elif pal4:
            expected = 2048 + pixels // 16 + 32
        elif payload == 2:
            # Square full-codebook chain: one 1x1 index, then 2x2 blocks.
            expected = 2048 + (pixels + 2) // 3 if mip else 2048 + pixels // 4
        else:
            expected = (pixels * 4 // 3 + 3) * 2 if mip else pixels * 2
        if (not dims or payload > 2 or reserved or size != expected or (fmt > 2 and not pal4 and not alpha4 and not alpha8) or off < doff
                or off + size > doff + dsize or off < 48 or off + size > len(b)):
            return 'descriptor %d: dimensions, format, layout or payload size' % i, None
        if payload == 0:
            return 'descriptor %d: linear payload (open_streamed refuses it)' % i, None
    tw, th = struct.unpack_from('<2I', b, toff + 64)
    if (tw, th) != (width, height):
        return 'texture is %dx%d, the part samples %dx%d' % (tw, th, width, height), None
    return None, rule


def check_textures(pkg_dir, keys, replace, resolver=None, *, pal4_alpha=False,
                   cast_mipmap=False, twiddled_mipmap=False, pal4_mipmap=False,
                   pal8_alpha=False, pal8_mipmap=False):
    """Every part's texture (unique key + size): present, loadable (tex_package_error) and hashed. resolver(key) ->
    (bytes or None, source) replaces the package-dir lookup (a fixture-selected package: the staged bytes)."""
    uniq = sorted({(k[0], k[1], k[2], k[3]) for k in keys})
    missing, bad, files, total, rules = [], [], {}, 0, collections.Counter()
    for crc, fnv, w, h in uniq:
        key = f'{crc}-{fnv}'
        if resolver:
            b, p = resolver(key)
            if b is None:
                missing.append(key)
                continue
        else:
            p = tex_source(pkg_dir, (crc, fnv), replace)
            if p is None or not p.is_file():
                missing.append(key)
                continue
            b = p.read_bytes()
        why, rule = tex_package_error(b, w, h, pal4_alpha=pal4_alpha, cast_mipmap=cast_mipmap,
                twiddled_mipmap=twiddled_mipmap, pal4_mipmap=pal4_mipmap,
                pal8_alpha=pal8_alpha, pal8_mipmap=pal8_mipmap)
        if why:
            bad.append(dict(key=key, size=[w, h], why=why))
        else:
            rules[rule] += 1
        if key not in files:
            files[key] = dict(sha256=hashlib.sha256(b).hexdigest(), bytes=len(b), source=str(p))
            total += len(b)
    agg = hashlib.sha256(''.join('%s %s\n' % (k, v['sha256']) for k, v in sorted(files.items())).encode()).hexdigest()
    return dict(parts=len(keys), unique=len(uniq), missing=missing, bad=bad, crc_rules=dict(rules),
                crc_note=TEX_CRC_DATA_NOTE if rules['data'] else None, files=files, files_sha256=agg,
                package_bytes=total)


def win_path(p):
    """A converter report's Windows path (C:\\...) as this host sees it (/mnt/c/...)."""
    m = re.fullmatch(r'([A-Za-z]):[\\/](.*)', p or '')
    return Path('/mnt/%s/%s' % (m.group(1).lower(), m.group(2).replace('\\', '/'))) if m else \
        Path(p.replace('\\', '/')) if p else None


def check_provenance(room, pd, m_sha, s_sha, manifests, afs_member, iso=None):
    """Fail-closed source binding of a package: (record, failures). Required: the converter report ps2-world.json
    naming these exact package hashes; its input directory (args.src); an extraction manifest record for the room
    (ps2_room_extract.py) that lists input files and whose AFS member matches the disc's index in place and in bytes
    (the claimed member sha256 equals the sha256 of those bytes of the configured PS2 disc, `iso`); and every listed
    input present with the listed sha256. Any absent or empty record is a failure, never a pass."""
    rec, fail = dict(report=None, inputs=None, manifest=None), []
    rp = pd / 'ps2-world.json'
    rep = None
    if not rp.is_file():
        fail.append('provenance: no converter report (ps2-world.json)')
    else:
        rep = json.loads(rp.read_text())
        rec['report'] = dict(path=str(rp), sha256=sha(rp), re4mesh_sha256=rep.get('re4mesh_sha256'),
                             r4pw_sha256=rep.get('r4pw_sha256'), args=rep.get('args'))
        if rep.get('re4mesh_sha256') != m_sha or rep.get('r4pw_sha256') != s_sha:
            fail.append('provenance: the converter report names other package hashes')
    inputs = win_path((rep or {}).get('args', {}).get('src')) if rep else None
    if inputs is not None and not inputs.is_absolute():
        # a relative --src (ps2-rooms-20260929: 'inputs\r100') is relative to the corpus root, <root>/out/<room>
        inputs = pd.parent.parent / inputs
        rec['inputs_relative_to'] = str(pd.parent.parent)
    if rep and (inputs is None or not inputs.is_dir()):
        fail.append('provenance: converter inputs absent (%s)' % ((rep or {}).get('args', {}).get('src')))
        inputs = None
    cands = [(src, m['rooms'][room]) for src, m in manifests.items() if room in m.get('rooms', {})]
    if not cands:
        fail.append('provenance: no extraction manifest record for the room')
    elif inputs is not None:
        best = None
        for src, man in cands:
            files = man.get('files') or {}
            mism = sorted(k for k, v in files.items() if not (inputs / k).is_file() or sha(inputs / k) != v.get('sha256'))
            score = (bool(files), not mism)
            if best is None or score > best[0]:
                best = (score, src, man, files, mism)
        _, src, man, files, mism = best
        member = man.get('member') or {}
        rec['manifest'] = dict(path=src, files=len(files), member=member)
        rec['inputs'] = dict(dir=str(inputs), mismatched=mism[:20], mismatched_count=len(mism))
        lit = inputs / 'gc-lit-cut0.json'
        if lit.is_file():
            rec['inputs']['gc_lit'] = dict(sha256=sha(lit), tev_scale=json.loads(lit.read_text())['env'].get('tev_scale'))
        if not files:
            fail.append('provenance: the extraction manifest record lists no input files')
        elif mism:
            fail.append('provenance: %d converter input(s) absent or differ from the extraction manifest' % len(mism))
        if not member.get('sha256') or not afs_member or (member.get('size'), member.get('offset')) != (
                afs_member.get('size'), afs_member.get('offset')):
            fail.append('provenance: the manifest AFS member does not match the PS2 disc index')
        else:
            # the claimed member hash against the configured disc's actual member bytes (read every run, no cache)
            actual = member_sha(iso or PS2_ISO, afs_member['offset'], afs_member['size'])
            rec['manifest']['member_actual_sha256'] = actual
            if actual != member['sha256']:
                fail.append('provenance: the manifest AFS member sha256 differs from the configured disc\'s bytes')
    return rec, fail


def member_sha(iso, offset, size):
    """sha256 of [offset, offset+size) of the disc image; None if the image is absent or shorter."""
    iso = Path(iso)
    if not iso.is_file() or iso.stat().st_size < offset + size:
        return None
    h = hashlib.sha256()
    with open(iso, 'rb') as f:
        f.seek(offset)
        left = size
        while left:
            b = f.read(min(left, 1 << 20))
            if not b:
                return None
            h.update(b)
            left -= len(b)
    return h.hexdigest()


# Packages landed before the PS2 extraction path existed. Each entry binds one exact package (both files), its report
# and the source it was converted from (sha256 re-checked on every run); other bytes for the room get no waiver.
LEGACY = {
    # r101: world-mesh-r21 (2026-09-28), converted from the GC-route renderer wrapper (an .r4p), not from the PS2
    # AFS, so no extraction manifest can describe it. Every route image since has staged it (rel-r103-entry-pw.json
    # and the route fixtures); the r101 bell regression (sup-wc-t0/t1-bell) runs it.
    'r101': dict(re4mesh_sha256='4ccfd1d8ddac4435ddc619ed1a3729d477d4206cb306db495d84b126ad603afe',
                 r4pw_sha256='300a346f1742a97fbe3aa75f158223e93a2695178b7c21e01168fea65c25d96f',
                 report_sha256='fc91f1b66af37505a3b1e92bbca271084ca165cec320b19fb83949fce9616fc8',
                 source=str(PRIV / 'world-agent-20260926/continuation-20260927/renderer/full-wrapper-v5-HOST-ONLY.r4p'),
                 source_sha256='82445a65fe13ec741fe6ff2c24c181024ad7e21cf0edc6a663d5a8d95eebf72b',
                 reason='world-mesh-r21 package (GC-route .r4p source, pre-extraction); the hand-list r101 package'),
}


# Further exact pairs per room from the same legacy source. r101: world-mesh-r21/package-uvg, ps2_world_r4im.py
# --lod-uv-guard 0.002 over the same .r4p (its report names source_sha256 82445a65...), the package every current
# play fixture stages (title-c13-pw / title-c14-pak); same sidecar as LEGACY['r101'].
LEGACY_ALSO = {
    'r101': [dict(re4mesh_sha256='50d1d1e5623510bd3f9425be1e75e771c6c161fd019e17587e3e0729b845d149',
                  r4pw_sha256='300a346f1742a97fbe3aa75f158223e93a2695178b7c21e01168fea65c25d96f',
                  report_sha256='89d4a54eb9b6125571e5e886a80a52edc7f63f6451703fadfca3b598576c90cd',
                  source=LEGACY['r101']['source'], source_sha256=LEGACY['r101']['source_sha256'],
                  reason='world-mesh-r21 package-uvg (--lod-uv-guard 0.002, same .r4p source): the r101 package of the play fixtures')],
}


def legacy_entry(room, m_sha, s_sha, prov):
    """The LEGACY / LEGACY_ALSO entry naming exactly these package files, this report and an unchanged source."""
    for leg in ([LEGACY[room]] if room in LEGACY else []) + LEGACY_ALSO.get(room, []):
        if (leg['re4mesh_sha256'], leg['r4pw_sha256']) != (m_sha, s_sha):
            continue
        if (prov.get('report') or {}).get('sha256') != leg['report_sha256']:
            continue
        src = Path(leg['source'])
        if src.is_file() and sha(src) == leg['source_sha256']:
            return leg
    return None


def legacy_holds(room, m_sha, s_sha, prov):
    """True only if a LEGACY entry names exactly these package files, this report and an unchanged source."""
    return legacy_entry(room, m_sha, s_sha, prov) is not None


# Source health: the game's own failure logs, which HALT / MISSING do not catch (a failed enemy spawn or model init
# leaves the room running with entities missing). Categories after the source strings (src/: dvd.cpp, em_set,
# readEmData, cEm/cObj/cParts modelInit, createSat; port: work backing, native pipeline) and the root's
# h2-matrix/logic_trace_diff.py SOURCE_FAILURE union (any other match is 'other'). Optional native UI staging
# fallbacks (texture upload / pair misses) are render health, not source failures, and are not listed here.
SOURCE_HEALTH = [
    ('em_set_failed', re.compile(rb'Em set failed')),
    ('dvd_alloc_failed', re.compile(rb'DVD:?\s*Memory allocat\w* fail', re.I)),
    ('read_em_error', re.compile(rb'readEmData\(\): error')),
    ('model_init_failed', re.compile(rb'(?:[Mm]odelInit\b.*(?:failed|was failed)|Parts allocate was failed)')),
    ('create_sat_failed', re.compile(rb'createSat\(\) (?:memory alloc failed|INVALID PTR)')),
    ('backing_failed', re.compile(rb'work backing:.*(?:failures=[1-9]|allocation fail)')),
    ('pipeline_failures', re.compile(rb'native pipeline:.*failures=[1-9]')),
]
SOURCE_FAILURE_REF = re.compile(rb'(?:EmSetFromList2|ModelInit|modelInit|createSat|DVD:?\s*Memory|work backing:).*'
                                rb'(?:failed|allocation fail|allocate fail|failures=[1-9])', re.I)
ROOM_MARK = re.compile(rb'(?:warp: room enter |room lifecycle: phase=enter room=)([0-9a-f]{3})\b')


def source_health(raw):
    """{'counts': {category: n}, 'rooms': {rXXX: {category: n}}, 'first': [lines]} of a run log; a failure is
    attributed to the room last entered ('warp: room enter' / 'room lifecycle: phase=enter'), 'r???' before any."""
    counts, rooms, first, room = collections.Counter(), collections.defaultdict(collections.Counter), [], 'r???'
    for line in raw.split(b'\n'):
        m = ROOM_MARK.search(line)
        if m:
            room = 'r' + m.group(1).decode()
            continue
        cat = next((c for c, rx in SOURCE_HEALTH if rx.search(line)), None)
        if cat is None and SOURCE_FAILURE_REF.search(line):
            cat = 'other'
        if cat:
            counts[cat] += 1
            rooms[room][cat] += 1
            if len(first) < 6:
                first.append('%s %s' % (room, line.decode('utf-8', 'replace').strip()[:120]))
    return dict(counts=dict(counts), rooms={k: dict(v) for k, v in rooms.items()}, first=first)


EVIDENCE_LINE = re.compile(rb'PS2MESH|room enter|^HALT|HALT |RE4DC MISSING|^warp: (start|placed|frame)|^tex pack: |'
                           rb'^quality assets: /cd/dc/native/')
STAGED = re.compile(r'dc/native/r[0-9a-f]{3}/(ps2-world\.(re4mesh|r4pw)|low/index\.txt)|dc/tex\.pak|'
                    r'dc/tex(low)?/[0-9a-f]/[0-9a-f]{8}-[0-9a-f]{8}\.re4tex')
ROUTE_OUT = Path('/root/probe/lanes/route')    # route-build.sh out-<label>: the tested image's resolved-knobs.txt


def run_knobs(arm, elf_sha):
    """TEX_PACK / QUALITY_ASSETS of the image a run tested (route-build.sh out-<label>/resolved-knobs.txt), or None
    when that output is gone or was rebuilt since (its elf.sha256 no longer names the run's ELF)."""
    if not arm or not arm.startswith('candidate-route'):
        return None
    out = ROUTE_OUT / ('out-' + arm[len('candidate-route'):])
    try:
        if not elf_sha or (out / 'elf.sha256').read_text().split()[0] != elf_sha:
            return None
        knobs = {}
        for line in (out / 'resolved-knobs.txt').read_text().splitlines():
            k, _, v = line.partition('=')
            if k in ('TEX_PACK', 'QUALITY_ASSETS', 'TEX_RESIDENT'):
                knobs[k] = v.split()[0] if v.split() else ''
        return knobs
    except OSError:
        return None


# Knob-guarded string literals: present in a program only when the knob compiled the code that logs them
# (native_ui.cpp includes texpack_index.inc under #if RE4DC_TEX_PACK; native_static.cpp's Standard index summary is
# under #if RE4DC_QUALITY_ASSETS).
KNOB_LITERALS = {'TEX_PACK': b'tex pack: %s not on the disc, per-file loads',
                 'QUALITY_ASSETS': b'quality assets: %s mesh=%02x tex=%u'}


def binary_knobs(scenario_dir, arm):
    """TEX_PACK / QUALITY_ASSETS of the program a run staged, when route-build's output for it is gone: only if the
    harness program file programs/<arm>/1ST_READ.BIN is byte-identical to the run's staged 1ST_READ.BIN (payload
    manifest sha256); the knobs then follow from KNOB_LITERALS in those bytes. None otherwise."""
    try:
        staged = json.loads((scenario_dir / 'payload-manifest.json').read_text())['1ST_READ.BIN']['sha256']
        b = (HARNESS / 'programs' / arm / '1ST_READ.BIN').read_bytes()
    except (OSError, KeyError, TypeError, ValueError):
        return None
    if hashlib.sha256(b).hexdigest() != staged:
        return None
    return dict({k: '1' if lit in b else '0' for k, lit in KNOB_LITERALS.items()}, source='staged program strings')


def select_texture(key, tex_pack, pack, texlow, staged):
    """(source, sha256) of the bytes the game loads for texture `key` ('crc-fnv'), native_ui.cpp load(): a key the
    room's Standard index adds (QUALITY_ASSETS, `texlow`) opens dc/texlow/<c>/ and is never looked up in the pack; a
    TEX_PACK=1 image with a usable pack (`pack`: key -> member sha256, None if the disc has no pack or it is invalid)
    reads the member when the key is in it, even if a loose file exists; otherwise the loose dc/tex/<c>/ file. A sha256
    of None: no such file on the disc."""
    if key in texlow:
        return 'texlow', staged.get(f'dc/texlow/{key[0]}/{key}.re4tex')
    if tex_pack and pack is not None and key in pack:
        return 'pack', pack[key]
    return 'loose', staged.get(f'dc/tex/{key[0]}/{key}.re4tex')


def pack_members(blob):
    """key -> member sha256 of a tex.pak, validated with texpack.verify (the runtime's checks); None if invalid."""
    import texpack
    try:
        count, _ = texpack.verify(blob)
    except SystemExit:
        return None
    out = {}
    for i in range(count):
        k0, k1, off, size = struct.unpack_from('<4I', blob, 2048 + 16 * i)
        out['%08x-%08x' % (k0, k1)] = hashlib.sha256(blob[off:off + size]).hexdigest()
    return out


_ISO, _PACKS = {}, {}


def staged_bytes(e, path):
    """The bytes a run's disc held at `path` (payload-manifest sha256): the fixture's source when it replaced the
    path, else the base disc's file; None unless the recovered bytes hash to the staged sha256."""
    want = e['staged'].get(path)
    if not want:
        return None
    src = ((e.get('fixture') or {}).get('replace') or {}).get(path)
    if src:
        # stage.json keeps the fixture's text, not its path: a relative source is tried against the fixture
        # directories (tour/, tour/play/); only bytes hashing to the staged sha256 count
        b = None
        for q in ([Path(src)] if src.startswith('/') else [TOUR / src, TOUR / 'play' / src]):
            q = Path(os.path.normpath(q))
            if q.is_file() and sha_cached(q) == want:
                b = q.read_bytes()
                break
    elif e.get('base') and Path(e['base']).is_file():
        import io, pycdlib
        iso = _ISO.get(e['base'])
        if iso is None:
            iso = _ISO[e['base']] = pycdlib.PyCdlib()
            iso.open(e['base'])
        buf = io.BytesIO()
        try:
            iso.get_file_from_iso_fp(buf, joliet_path='/' + path)
            b = buf.getvalue()
        except Exception:
            b = None
    else:
        b = None
    return b if b is not None and hashlib.sha256(b).hexdigest() == want else None


def resolve_textures(e, room, keys):
    """({key: (source, sha256)}, None) for the texture keys a run's image loaded in `room`, or (None, reason) when the
    run's records cannot establish the bytes (the evidence then stays unverified)."""
    k = e.get('knobs')
    if k is None:
        return None, 'tested image knobs unknown (route-build output gone or rebuilt since the run)'
    tex_pack = k.get('TEX_PACK') == '1'
    logged = ' '.join(e.get('pack_log') or [])
    pack = None
    if tex_pack and 'dc/tex.pak' in e['staged']:
        sha_pak = e['staged']['dc/tex.pak']
        if sha_pak not in _PACKS:
            blob = staged_bytes(e, 'dc/tex.pak')
            _PACKS[sha_pak] = ('unrecoverable', None) if blob is None else ('ok', pack_members(blob))
        state, pack = _PACKS[sha_pak]
        if state != 'ok':
            return None, 'staged dc/tex.pak bytes not recoverable (sha256 %s)' % sha_pak[:16]
        if pack is None and 'INVALID' not in logged:
            return None, 'dc/tex.pak fails texpack.verify but the run did not log it invalid'
        if pack is not None and 'count=%d ' % len(pack) not in logged + ' ':
            return None, 'dc/tex.pak index (%d members) not confirmed by the run log (%s)' % (len(pack), logged[:60])
    elif tex_pack and 'not on the disc' not in logged:
        return None, 'no dc/tex.pak staged but the run log does not say so (%s)' % logged[:60]
    texlow = set()
    if k.get('QUALITY_ASSETS') == '1':
        q = (e['rooms'].get(room) or {}).get('quality') or []
        if any(x != 'off' and x != 'tex=0' for x in q):
            b = staged_bytes(e, f'dc/native/{room}/low/index.txt')
            if b is None:
                return None, 'Standard index active in %s but its staged bytes are not recoverable' % room
            for line in b.decode('ascii', 'replace').splitlines():
                t = line.split()
                if len(t) >= 2 and t[0] == 'tex':
                    texlow.add(t[1].lower())
    return {key: select_texture(key, tex_pack, pack, texlow, e['staged']) for key in keys}, None


def scan_evidence(globs):
    """scenario -> {staged package / texture sha256 per disc path, arm / ELF / fixture, the warp start / placement /
    sampled poses, per-room open / frame / fallback stats}."""
    out = {}
    scen = HARNESS / 'scenarios'
    dirs = sorted({d for g in globs for d in scen.glob(g) if (d / 'capture/run-output.txt').exists()})
    for d in dirs:
        log = d / 'capture/run-output.txt'
        raw = log.read_bytes()
        if b'PS2MESH room=' not in raw:
            continue
        pm = d / 'payload-manifest.json'
        staged = {}
        if pm.exists():
            staged = {k: v['sha256'] for k, v in json.loads(pm.read_text()).items() if STAGED.fullmatch(k)}
        st = json.loads((d / 'stage.json').read_text()) if (d / 'stage.json').exists() else {}
        rooms = collections.defaultdict(lambda: dict(opens=0, open_failed=0, open_bytes=[], frames=[], fallback=0,
                                                     aborts=0, frame_lines=0, fail_reasons=[], poses=[], quality=[]))
        pack_log = []
        cur = None
        halt = missing = 0
        pending = None
        warp = []
        for line in raw.split(b'\n'):
            if not EVIDENCE_LINE.search(line):
                continue
            s = line.decode('utf-8', 'replace').strip()
            if s.startswith('tex pack: '):
                pack_log.append(s[10:120])
                continue
            m = re.match(r'quality assets: /cd/dc/native/r([0-9a-f]{3})/low/index\.txt (.*)', s)
            if m:
                q = m.group(2)
                t = re.search(r'tex=(\d+)', q)
                rooms['r' + m.group(1)]['quality'].append(('tex=%s' % t.group(1)) if t and q.startswith('mesh=') else 'off')
                continue
            if s.startswith('warp: '):
                if s.startswith(('warp: start', 'warp: placed')):
                    warp.append(s[6:])
                m = re.match(r'warp: frame (\d+) room=([0-9a-f]+) pl=(\S+)', s)
                if m and len(rooms['r' + m.group(2)]['poses']) < 12:
                    rooms['r' + m.group(2)]['poses'].append('frame %s pl=%s' % (m.group(1), m.group(3)))
                continue
            if s.startswith('HALT') or ' HALT ' in s:
                halt += 1
            if 'RE4DC MISSING' in s:
                missing += 1
            m = re.search(r'PS2MESH room=([0-9a-f]+) open$', s)
            if m:
                cur = 'r' + m.group(1)
                pending = cur
                continue
            m = re.search(r'PS2MESH open bytes=(\d+)', s)
            if m and pending:
                rooms[pending]['opens'] += 1
                rooms[pending]['open_bytes'].append(int(m.group(1)))
                pending = None
                continue
            m = re.search(r'PS2MESH open failed: (.*)', s)
            if m and pending:
                rooms[pending]['open_failed'] += 1
                rooms[pending]['fail_reasons'].append(m.group(1)[:80])
                pending = None
                continue
            m = re.search(r'PS2MESH frame=(\d+) pass=\d .*fallback=(\d+) aborts=(\d+)', s)
            if m and cur:
                r = rooms[cur]
                r['frames'].append(int(m.group(1)))
                r['frame_lines'] += 1
                r['fallback'] += int(m.group(2))
                r['aborts'] += int(m.group(3))
        out[d.name] = dict(run_output=str(log), elf_sha256=st.get('elf_sha256'), arm=st.get('arm'),
                           source_health=source_health(raw),
                           disc_sha256=st.get('disc_sha256'), fixture=st.get('fixture'), base=st.get('base'),
                           knobs=run_knobs(st.get('arm'), st.get('elf_sha256')) or
                           (binary_knobs(d, st.get('arm')) if st.get('arm') else None), pack_log=pack_log[:4],
                           warp=warp[:4], staged=staged, halt=halt, missing=missing,
                           rooms={k: dict(v, frames=[min(v['frames']), max(v['frames'])] if v['frames'] else [],
                                          open_bytes=sorted(set(v['open_bytes'])), fail_reasons=sorted(set(v['fail_reasons'])))
                                  for k, v in rooms.items()})
    return out


def bitmap_inc(rooms, manifest_sha):
    bits = [[0] * 8 for _ in range(6)]
    for r in rooms:
        v = int(r[1:], 16)
        st, ix = v >> 8, v & 255
        bits[st][ix >> 5] |= 1 << (ix & 31)
    lines = ['// ps2_world_rooms.inc - generated by tools/d367/ps2world/world_registry.py; do not edit.',
             '// PS2_WORLD_REGISTRY=1: native_static.cpp re4dc_ps2_world_room, one bit per room (stage = room >> 8,',
             '// word = (room & 255) >> 5). The rooms whose PS2 world package passed validation:',
             '//   ' + ' '.join(rooms),
             f'// manifest rooms sha256 {manifest_sha}']
    for st in range(6):
        lines.append('{' + ','.join('0x%08xU' % w for w in bits[st]) + '},' + f' // stage {st}')
    return '\n'.join(lines) + '\n'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--inc', type=Path)
    ap.add_argument('--corpus', type=Path, action='append', help='converter output roots (default: the two corpora)')
    ap.add_argument('--evidence-glob', action='append', help="harness scenario globs (default 'route-*')")
    ap.add_argument('--package', action='append', default=[], metavar='ROOM=DIR',
                    help='a candidate converter output dir (ps2-world.{re4mesh,r4pw,json} + tex/) for ROOM in place of '
                         'the route-fixture / corpus selection (e.g. a --lod-uv-guard rebuild); recorded in the row')
    ap.add_argument('--package-root', action='append', type=Path, default=[],
                    help='dirs of guarded rebuilds <room>-ps2-uvg (uvgbatch.py), selected after the play fixtures')
    ap.add_argument('--play-fixture', action='append', type=Path, help='play fixtures, in precedence order '
                    '(default PLAY_FIXTURES: tour/play/title-c14-pak.json, title-c13-pw.json)')
    ap.add_argument('--fixture-dir', action='append', type=Path, default=[],
                    help="a lane's fixture dir: its *.json count as staging evidence (after the tour/ and repo fixtures)")
    ap.add_argument('--reviews', type=Path, help='appearance reviews JSON: {room: [{re4mesh_sha256, r4pw_sha256, '
                    'textures_sha256, verdict, capture, by, date}]}; counted only for the same three hashes')
    ap.add_argument('--inc-check', type=Path, help='the runtime room list to report registered rooms against '
                    '(default: game/platform/include/ps2_world_rooms.inc)')
    for feature in ('cast-mipmap', 'twiddled-mipmap', 'pal4-alpha', 'pal4-mipmap',
                    'pal8-alpha', 'pal8-mipmap'):
        ap.add_argument('--' + feature, action='store_true',
                        help='validate textures with the matching explicit runtime feature')
    a = ap.parse_args()
    texture_features = {key: getattr(a, key) for key in ('cast_mipmap', 'twiddled_mipmap',
        'pal4_alpha', 'pal4_mipmap', 'pal8_alpha', 'pal8_mipmap')}
    config_error = _texture_feature_error(**texture_features)
    if config_error:
        ap.error(config_error)
    corpora = a.corpus or CORPORA
    reviews = json.loads(a.reviews.read_text()) if a.reviews else {}
    inc_path = a.inc_check or (REPO_DC / 'game/platform/include/ps2_world_rooms.inc')
    inc_rooms = set()
    if inc_path.is_file():
        m = re.search(r'^//   (r[0-9a-f]{3}(?: r[0-9a-f]{3})*)$', inc_path.read_text(), re.M)
        inc_rooms = set(m.group(1).split()) if m else set()
    exe, check_sha = checker()
    gc = gc_rooms_and_arrivals()
    ps2, afs_sha = ps2_rooms()
    hand = hand_list()
    base = json.loads(BASE_MANIFEST.read_text())
    base_rooms = sorted({m.group(1) for k in base for m in [re.fullmatch(r'st\d/(r[0-9a-f]{3})\.dar', k)] if m})
    fix_pkg, fix_rooms, plays = fixture_staging(a.play_fixture, a.fixture_dir)
    evidence = scan_evidence(a.evidence_glob or ['route-*'])
    manifests = {}
    for c in corpora:
        p = c / 'extract-manifest.json'
        manifests[str(c)] = json.loads(p.read_text()) if p.exists() else {}
    all_rooms = sorted(set(gc['rooms']) | set(ps2))
    out_rooms = {}
    for room in all_rooms:
        stage = int(room[1], 16)
        rec = dict(room=room, id='0x%s' % room[1:], stage=stage, blockers=[])
        mem = ps2.get(room)
        # sources
        corpus = next((c for c in corpora if (c / 'out' / f'{room}-ps2').exists() or (c / 'inputs' / room).exists()), None)
        man = manifests.get(str(corpus), {}).get('rooms', {}).get(room) if corpus else None
        if man is None:
            man = next((m.get('rooms', {}).get(room) for m in manifests.values() if m.get('rooms', {}).get(room)), None)
        rec['sources'] = dict(gc_disc1=room in gc['rooms'],
                              ps2_afs=dict(member=mem['name'], bytes=mem['size'], offset=mem['offset'],
                                           sha256=(man or {}).get('member', {}).get('sha256')) if mem else None,
                              scenario_smd=(man or {}).get('scenario_smd') if man else None)
        # package selection: override > first play fixture > the route fixtures' majority > corpus
        stagings = fix_pkg.get(room, [])
        pair = lambda x: (x['re4mesh_sha256'], x['r4pw_sha256'])
        pkg = None
        override = dict(x.split('=', 1) for x in a.package).get(room)
        play_st = [x for x in stagings if x['fixture'].play]
        if override:
            d = Path(override)
            pkg = dict(selected_by='--package override', dir=str(d), re4mesh=d / 'ps2-world.re4mesh',
                       r4pw=d / 'ps2-world.r4pw', fixture=None)
        elif play_st:
            s0 = play_st[0]
            pkg = dict(selected_by='play fixture ' + s0['fixture'].name, dir=str(s0['re4mesh'].parent),
                       re4mesh=s0['re4mesh'], r4pw=s0['r4pw'] or s0['re4mesh'].with_suffix('.r4pw'), fixture=s0['fixture'])
        elif any((r / f'{room}-ps2-uvg' / 'ps2-world.re4mesh').is_file() for r in a.package_root):
            d = next(r / f'{room}-ps2-uvg' for r in a.package_root if (r / f'{room}-ps2-uvg' / 'ps2-world.re4mesh').is_file())
            pkg = dict(selected_by='guarded rebuild ' + str(d.parent), dir=str(d), re4mesh=d / 'ps2-world.re4mesh',
                       r4pw=d / 'ps2-world.r4pw', fixture=None)
        elif stagings:
            votes = collections.Counter(pair(x) for x in stagings)
            best = max(votes, key=lambda k: (votes[k], str(k)))
            s0 = next(x for x in stagings if pair(x) == best)
            pkg = dict(selected_by='route fixture', dir=str(s0['re4mesh'].parent), re4mesh=s0['re4mesh'],
                       r4pw=s0['r4pw'] or s0['re4mesh'].with_suffix('.r4pw'), fixture=s0['fixture'])
        elif corpus and (corpus / 'out' / f'{room}-ps2' / 'ps2-world.re4mesh').exists():
            d = corpus / 'out' / f'{room}-ps2'
            pkg = dict(selected_by='corpus out/<room>-ps2', dir=str(d), re4mesh=d / 'ps2-world.re4mesh',
                       r4pw=d / 'ps2-world.r4pw', fixture=None)
        val = dict(ok=False, failures=[])
        if pkg is None:
            if mem is None:
                rec['blockers'].append('no PS2 source room (not in the PS2 AFS)')
            elif man and not man.get('scenario_smd'):
                rec['blockers'].append('no scenario SMD in the PS2 room (cinematic room: no world geometry)')
            elif stage in (3, 5):
                rec['blockers'].append('not converted: the approved bake (--color-light ps2) needs the room TEV scale '
                                       'from the GC LIT (GC disc 2, St3/St5, not configured: sources.toml gc_iso2 empty)')
            else:
                rec['blockers'].append('not converted (run ps2_room_extract.py + gc_room_lit.py + ps2_room_r4im.py)')
        else:
            mesh, side = Path(pkg['re4mesh']), Path(pkg['r4pw'])
            pd = Path(pkg['dir'])
            rep = json.loads((pd / 'ps2-world.json').read_text()) if (pd / 'ps2-world.json').exists() else None
            ck = run_check(exe, mesh, side) if mesh.exists() and side.exists() else dict(ok=False, why='missing files')
            keys = ck.pop('part_keys', [])
            m_sha, s_sha = (sha(mesh) if mesh.exists() else None), (sha(side) if side.exists() else None)
            same = sorted({x['fixture'].name for x in stagings if pair(x) == (m_sha, s_sha)})
            conflicts = [dict(fixture=x['fixture'].name, play=x['fixture'].play, re4mesh=str(x['re4mesh']),
                              r4pw=str(x['r4pw']), re4mesh_sha256=x['re4mesh_sha256'], r4pw_sha256=x['r4pw_sha256'])
                         for x in stagings if pair(x) != (m_sha, s_sha)]
            rec['package'] = dict(selected_by=pkg['selected_by'], dir=str(pd), re4mesh=str(mesh), r4pw=str(side),
                                  re4mesh_sha256=m_sha, r4pw_sha256=s_sha, fixtures=same, conflicts=conflicts,
                                  converter=dict(color_light=rep.get('args', {}).get('color_light'),
                                                 lights=rep.get('args', {}).get('lights'),
                                                 vertex_alpha_below_one=rep.get('stats', {}).get('vertex_alpha_below_one'),
                                                 corners_clipped=rep.get('stats', {}).get('corners_clipped'),
                                                 source_triangles=rep.get('source_triangles'),
                                                 level0_triangles=rep.get('level0_triangles'),
                                                 texture_vram_bytes=rep.get('texture_vram_bytes')) if rep else None)
            if not ck.get('ok'):
                val['failures'].append('runtime open: %s' % ck.get('why'))
            prov, pfail = check_provenance(room, pd, m_sha, s_sha, manifests, mem)
            if pfail and legacy_holds(room, m_sha, s_sha, prov):
                prov['legacy'] = dict(legacy_entry(room, m_sha, s_sha, prov), waived=pfail)
                pfail = []
            val['failures'] += pfail
            fx = pkg.get('fixture')
            tex = check_textures(pd, keys, None, resolver=fx.texture if fx else None, **texture_features) if ck.get('ok') else None
            if tex and fx:
                tex['resolved_from'] = 'fixture %s (%s)' % (fx.name, fx.pack()[2] if fx.pack()[1] is not None
                                                             else 'loose files; ' + fx.pack()[2])
            if tex and (tex['missing'] or tex['bad']):
                val['failures'].append('textures: %d missing, %d not loadable (%s)' % (
                    len(tex['missing']), len(tex['bad']), '; '.join(sorted({b['why'] for b in tex['bad']}))[:120]))
            if ck.get('ok') and not keys:
                val['failures'].append('textures: the package lists no part textures')
            ident = None
            if ck.get('ok'):
                lo, hi = ck['world_min'], ck['world_max']
                aux = (corpus / 'aux' / room) if corpus else None
                pts = rtp_points(aux)
                # a door record whose destination is (0, 0, 0) carries no arrival (r10e doors 4/5 to itself)
                every = gc['arrivals'].get(room, [])
                arr = [x for x in every if any(x['pos'])]
                rin = sum(inside(p, lo, hi) for p in pts)
                ain = [x for x in arr if inside(x['pos'], lo, hi)]
                ident = dict(rtp_points=len(pts), rtp_inside=rin, door_arrivals=len(arr), arrivals_inside=len(ain),
                             arrivals_outside=[x for x in arr if not inside(x['pos'], lo, hi)][:8],
                             zero_arrivals_skipped=[x for x in every if not any(x['pos'])])
                if pts and rin < 0.95 * len(pts):
                    val['failures'].append('identity: %d of %d route points outside the world box' % (len(pts) - rin, len(pts)))
                if arr and len(ain) < len(arr):
                    val['failures'].append('identity: %d of %d door arrivals outside the world box' % (len(arr) - len(ain), len(arr)))
                if not pts and not arr:
                    val['failures'].append('identity: no route points or door arrivals to check')
            val.update(ok=not val['failures'], runtime_open=ck, provenance=prov, textures=tex, identity=ident)
        rec['validation'] = val
        # staging and registration
        container = dict(base_disc=room in base_rooms, fixtures=sorted(set(fix_rooms.get(room, []))))
        # staged: fixtures whose disc holds this exact mesh + sidecar + every part texture (the texture set compared
        # per fixture with Fixture.texture); a fixture with the same world but other texture bytes is listed apart
        staged_exact, staged_other_tex = [], []
        tex_files = ((val.get('textures') or {}).get('files') or {})
        if rec.get('package') and tex_files:
            for x in stagings:
                if pair(x) != (rec['package']['re4mesh_sha256'], rec['package']['r4pw_sha256']):
                    continue
                diff = [k for k, v in sorted(tex_files.items())
                        if (lambda b: hashlib.sha256(b).hexdigest() if b is not None else None)(x['fixture'].texture(k)[0])
                        != v['sha256']]
                (staged_other_tex if diff else staged_exact).append(
                    x['fixture'].name if not diff else dict(fixture=x['fixture'].name, textures_differ=diff[:8],
                                                            textures_differ_count=len(diff)))
        rec['staging'] = dict(package_fixtures=(rec.get('package') or {}).get('fixtures', []), room_container=container,
                              exact=sorted(set(staged_exact)), same_world_other_textures=staged_other_tex)
        rec['registration'] = dict(hand_list=room in hand, registry=bool(val['ok']))
        # runtime evidence: runs in this room; a run proves this package only if its disc carried the same mesh and
        # sidecar (payload-manifest.json sha256) and the game read the same bytes for every part texture, resolved with
        # the tested image's TEX_PACK / QUALITY_ASSETS precedence (resolve_textures: pack member, texlow or loose file)
        ev = []
        p = rec.get('package') or {}
        want = {}
        tex_want = {k: v['sha256'] for k, v in ((val.get('textures') or {}).get('files') or {}).items()}
        if p:
            want[f'dc/native/{room}/ps2-world.re4mesh'] = p['re4mesh_sha256']
            want[f'dc/native/{room}/ps2-world.r4pw'] = p['r4pw_sha256']
        for name, e in evidence.items():
            if room not in e['rooms'] or not (e['rooms'][room]['opens'] or e['rooms'][room]['open_failed']):
                continue
            r = e['rooms'][room]
            sh = e['source_health']
            # failures in this room, or before any room mark (not attributable: counted against every room of the run)
            room_fail = dict(collections.Counter(sh['rooms'].get(room, {})) + collections.Counter(sh['rooms'].get('r???', {})))
            differ = sorted(k for k, v in want.items() if e['staged'].get(k) != v)
            res, unresolved = resolve_textures(e, room, sorted(tex_want)) if want else (None, 'no package')
            sources = collections.Counter()
            if res is not None:
                for key, (src, got) in res.items():
                    sources[src] += 1
                    if got != tex_want[key]:
                        differ.append('%s %s (%s)' % (src, key, 'absent' if got is None else got[:12]))
            ev.append(dict(scenario=name, run_output=e['run_output'], arm=e['arm'], elf_sha256=e['elf_sha256'],
                           disc_sha256=e['disc_sha256'], fixture=e['fixture'], warp=e['warp'], poses=r['poses'],
                           knobs=e.get('knobs'), tex_pack=e['staged'].get('dc/tex.pak'), pack_log=e.get('pack_log'),
                           quality=r.get('quality'), texture_sources=dict(sources), unresolved=unresolved,
                           package_sha_match=bool(want) and not differ and unresolved is None,
                           staged_differ=differ[:8], staged_differ_count=len(differ),
                           opens=r['opens'], open_failed=r['open_failed'], fail_reasons=r['fail_reasons'],
                           open_bytes=r['open_bytes'], frames=r['frames'], frame_lines=r['frame_lines'],
                           fallback_parts=r['fallback'], abort_parts=r['aborts'], halt=e['halt'], missing=e['missing'],
                           source_failures_room=room_fail, source_failures_run=sh['counts'], source_failure_lines=sh['first']))
        rec['runtime_evidence'] = ev
        drawn = [x for x in ev if x['package_sha_match'] and x['opens'] and not x['open_failed'] and x['frame_lines']
                 and not x['fallback_parts'] and not x['abort_parts'] and not x['halt'] and not x['missing']]
        # clean coverage also needs source health: no soft source failure in the room (a failed spawn / model init /
        # DVD allocation leaves the encounter incomplete); such runs stay recorded as observed drawing only
        good = [x for x in drawn if not x['source_failures_room']]
        unhealthy = [x for x in drawn if x['source_failures_room']]
        if good and val['ok']:
            rec['result'] = 'native'
            rec['observed'] = dict(runs=len(good), frames=[min(x['frames'][0] for x in good), max(x['frames'][1] for x in good)],
                                   scope='submission with zero fallback/abort parts for the views these runs saw (warp '
                                         'placement + logged poses); not every placement, pose or camera in the room')
        elif val['ok'] and unhealthy:
            rec['result'] = 'observed'
            rec['observed'] = dict(runs=len(unhealthy), scope='scenery drawn with zero fallback/abort parts, but every such '
                                   'run logged source failures in the room (%s): not a complete encounter' %
                                   ', '.join(sorted({k for x in unhealthy for k in x['source_failures_room']})))
        elif val['ok']:
            rec['result'] = 'unverified'
        else:
            rec['result'] = 'fallback'
        if val['ok'] and not good:
            entered_any = [x for x in ev if x['opens'] or x['open_failed']]
            if not container['base_disc'] and not container['fixtures'] and not entered_any:
                rec['blockers'].append('room not enterable on any staged disc: no room container (le_mirror + '
                                       'compact-room + room_smd release), sound banks, modules or warp preset '
                                       '(route lane bring-up, docs/lanes/route.md recipe)')
            elif unhealthy:
                rec['blockers'].append('source health: %d drawn run(s), each with source failures in the room' % len(unhealthy))
            elif entered_any:
                rec['blockers'].append('no runtime run with this package staged yet (the room is enterable: %d run(s) '
                                       'entered it with other bytes)' % len(entered_any))
            else:
                rec['blockers'].append('no runtime run with this package staged yet')
        if rec.get('package') and val['failures']:
            rec['blockers'] += val['failures']
        rec['status'] = {'native': 'native (runtime-proven, source-healthy runs)',
                         'observed': 'drawn, but only in runs with source failures (incomplete encounter)',
                         'unverified': 'package valid, runtime unproven', 'fallback': 'fallback (own scenery)'}[rec['result']]
        pk = rec.get('package') or {}
        tex_sha = (val.get('textures') or {}).get('files_sha256')
        hashes = dict(re4mesh_sha256=pk.get('re4mesh_sha256'), r4pw_sha256=pk.get('r4pw_sha256'), textures_sha256=tex_sha)
        rv = reviews.get(room) or []
        match = lambda r: all(r.get(k) == v for k, v in hashes.items()) and all(hashes.values())
        rec['states'] = dict(hashes=hashes, registered=bool(val['ok']), in_inc=room in inc_rooms,
                             staged=rec['staging']['exact'],
                             entered=[x['scenario'] for x in ev if x['package_sha_match'] and x['opens']],
                             drawn=[x['scenario'] for x in good],
                             drawn_with_source_failures=[dict(scenario=x['scenario'], failures=x['source_failures_room'])
                                                         for x in unhealthy],
                             reviewed=[r for r in rv if match(r)], reviews_of_other_bytes=[r for r in rv if not match(r)],
                             # every run in the room, whatever package it staged: its source health is the room's
                             # (a failed spawn there is not the package's fault, but it bounds what that run proves)
                             room_runs=len(ev), room_runs_other_bytes=sum(1 for x in ev if not x['package_sha_match']),
                             room_runs_with_source_failures=[dict(scenario=x['scenario'], this_package=x['package_sha_match'],
                                                                  failures=x['source_failures_room'])
                                                             for x in ev if x['source_failures_room']])
        out_rooms[room] = rec
    registry = sorted(r for r, v in out_rooms.items() if v['registration']['registry'])
    room_sha = hashlib.sha256(json.dumps({r: (out_rooms[r]['package']['re4mesh_sha256'], out_rooms[r]['package']['r4pw_sha256'])
                                          for r in registry}, sort_keys=True).encode()).hexdigest()
    doc = dict(schema='re4dc-world-coverage/1', generated=time.strftime('%Y-%m-%dT%H:%M:%S%z'),
               tool=dict(path='port/dreamcast/tools/d367/ps2world/world_registry.py', sha256=sha(__file__)),
               check_tool=dict(path='port/dreamcast/tools/d367/ps2world/ps2_world_check.cpp', sha256=check_sha),
               sources=dict(gc_iso=str(GC_ISO), gc_iso2=None, ps2_iso=str(PS2_ISO), ps2_afs_index_sha256=afs_sha,
                            base_disc_manifest=str(BASE_MANIFEST), base_disc_rooms=base_rooms,
                            corpora=[str(c) for c in corpora]),
               admission_rule='registry = every room whose package passes runtime open + textures + identity + '
                              'provenance (fail closed; LEGACY exact-pair waivers listed); result native = additionally '
                              'a run staged this exact mesh + sidecar + every part texture, opened it, drew PS2MESH '
                              'frames with no fallback/abort parts, HALT 0, MISSING 0 and no source failure in the room '
                              '(SOURCE_HEALTH: failed spawns, DVD allocations, model inits, createSat, backing, pipeline); '
                              'observed = the same draw only in runs with source failures (scenery seen, encounter '
                              'incomplete). Neither is playability: props, actors and fallbacks are not judged here',
               legacy=LEGACY, legacy_also=LEGACY_ALSO, play_fixtures=[dict(path=str(f.path), sha256=sha(f.path), pack=f.pack()[2]) for f in plays],
               reviews=dict(path=str(a.reviews), sha256=sha(a.reviews)) if a.reviews else None,
               inc_checked=dict(path=str(inc_path), rooms=sorted(inc_rooms)),
               runtime=dict(hand_list=hand, registry_rooms=registry, registry_rooms_sha256=room_sha,
                            inc=str(a.inc) if a.inc else None),
               counts=collections.Counter(v['result'] for v in out_rooms.values()),
               rooms=out_rooms)
    if any(texture_features.values()):
        doc['native_texture_features'] = texture_features
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / 'world-coverage.json').write_text(json.dumps(doc, indent=1, default=str) + '\n')
    if a.inc:
        a.inc.write_text(bitmap_inc(registry, room_sha))
    md = ['# PS2 world coverage (generated by tools/d367/ps2world/world_registry.py)', '',
          f"Sources: GC disc 1 `{GC_ISO}` (disc 2 not configured: St3/St5 have no GC LIT); PS2 `{PS2_ISO.name}`. "
          f"Hand list: {' '.join(hand)}. Registry ({len(registry)}): {' '.join(registry)}.", '',
          '| room | result | package | open (heap B) | textures | identity rtp / doors | container | evidence | '
          'states reg/inc/staged/entered/drawn/reviewed | conflicts | blockers |',
          '|---|---|---|---:|---|---|---|---|---|---|---|']
    for r, v in out_rooms.items():
        p, val = v.get('package'), v['validation']
        ck = val.get('runtime_open') or {}
        tx = val.get('textures') or {}
        idn = val.get('identity') or {}
        c = v['staging']['room_container']
        stt = v['states']
        md.append('| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |' % (
            r, v['result'], (p['re4mesh_sha256'][:8] + ' ' + p['selected_by']) if p else '-',
            (('ok %d' % ck['heap_bytes']) if ck.get('ok') else ('FAIL ' + str(ck.get('why')))) if p else '-',
            ('%d/%d' % (tx['unique'] - len(tx['missing']) - len(tx['bad']), tx['unique'])) if tx else '-',
            ('%d/%d, %d/%d' % (idn['rtp_inside'], idn['rtp_points'], idn['arrivals_inside'], idn['door_arrivals'])) if idn else '-',
            'base' if c['base_disc'] else ('fixture' if c['fixtures'] else 'none'),
            (('%d run(s) %s' % (v['observed']['runs'], v['observed'].get('frames', 'source failures'))) if v.get('observed')
             else ('%d run(s), none clean' % len(v['runtime_evidence']) if v['runtime_evidence'] else '-')) +
            ('; room source failures in %d of %d run(s)' % (len(stt['room_runs_with_source_failures']), stt['room_runs'])
             if stt['room_runs_with_source_failures'] else ''),
            '%s/%s/%d/%d/%d(+%d failed)/%d' % ('y' if stt['registered'] else 'n', 'y' if stt['in_inc'] else 'n',
                                   len(stt['staged']), len(stt['entered']), len(stt['drawn']),
                                   len(stt['drawn_with_source_failures']), len(stt['reviewed'])),
            len((p or {}).get('conflicts') or []),
            '; '.join(v['blockers'])[:200]))
    (a.out / 'world-coverage.md').write_text('\n'.join(md) + '\n')
    print(json.dumps(dict(rooms=len(out_rooms), counts=doc['counts'], registry=registry, hand=hand)))


if __name__ == '__main__':
    main()
