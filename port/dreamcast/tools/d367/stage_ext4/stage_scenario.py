#!/usr/bin/env python3
"""stage_scenario.py: ext4 + disc-cache staging for the playability harness (lane stage-ext4, 2026-10-14).

Same command line as the harness's stage-scenario.py (scenario, --arm, --programs, --overlay, --fixture,
--capture-reserve-mib) and the same outputs in <harness>/scenarios/<scenario>/: disc/disc.bin, disc/disc.cue,
stage.json (status STAGED_PAYLOAD_IDENTITY_PASS, disc_sha256, ...; plus an "ext4" key), payload-manifest.json.

  RE4DC_STAGE_EXT4=0  -> execs the old script unchanged (<harness>/stage-scenario-copy.py, else stage-scenario.py).
  default             -> 1. inputs on 9p (/mnt/c: overlay payloads, harness programs, programs json, MEDIA.json, helper
                           scripts, 9p fixture sources) come from an ext4 content cache $RE4DC_STAGE_ROOT/cas, keyed by
                           (path, size, mtime_ns): one 9p read per changed source;
                        2. the input key (base sha, every payload's destination + sha256 in staging order, removals,
                           the derived script sha, the pycdlib version) names the image. Same inputs as an earlier
                           staging whose image is still in the disc cache -> reuse that image (no build, no copy);
                        3. otherwise the image is built, re-read in both ISO namespaces, read by the independent raw
                           reader and hashed on ext4 with the same pycdlib operations as stage-scenario.py, then copied
                           once into the disc cache on C: (disccache.py, $RE4DC_DISCCACHE/<sha256>/disc.bin);
                        4. scenarios/<scenario>/disc/disc.bin is an NTFS hard link to the cached image
                           (RE4DC_DISCCACHE=0: a private copy instead). run-emulator*.py re-hashes it against
                           stage.json natively before boot and hard-links it into the capture, as before.
  The ext4 path runs only while the old script is the version it was derived from (DERIVED_SHA); otherwise it warns
  and runs the old script, so a harness edit never silently diverges.

Env: RE4DC_HARNESS, RE4DC_STAGE_ROOT (/root/stage), RE4DC_STAGE_CAS_VERIFY=1 (re-hash cached 9p sources),
RE4DC_STAGE_REUSE=0 (always build), RE4DC_STAGE_KEEP=1 (keep the ext4 image), RE4DC_DISCCACHE(_CAP_GB) (disccache.py),
RE4DC_STAGE_FREEZE_TIME=<epoch> (proof runs only: pycdlib stamps the wall clock into the image).
"""
import os, sys
HARNESS = os.environ.get('RE4DC_HARNESS', '/mnt/c/Game Dev/Emulators/re4-assets-private/world-agent-20260926/'
                         'continuation-20260927/playability-r11-r1')
ORIG = os.path.join(HARNESS, 'stage-scenario-copy.py')
if not os.path.exists(ORIG):
    ORIG = os.path.join(HARNESS, 'stage-scenario.py')
DERIVED_SHA = '5c3d19e1e6cc3b5d627335a3f8212a791271bd5a32cc489cc734f87d292d1d7b'

def run_original():
    os.execv(sys.executable, [sys.executable, ORIG] + sys.argv[1:])

if os.environ.get('RE4DC_STAGE_EXT4', '1') == '0':
    run_original()

import hashlib
with open(ORIG, 'rb') as f:
    if hashlib.sha256(f.read()).hexdigest() != DERIVED_SHA:
        print('stage_scenario.py: WARNING %s changed since the ext4 path was derived from it; '
              'running it unchanged (re-derive stage_ext4/stage_scenario.py)' % ORIG, file=sys.stderr)
        run_original()

if os.environ.get('RE4DC_STAGE_FREEZE_TIME'):
    import time as _t
    _frozen = float(os.environ['RE4DC_STAGE_FREEZE_TIME']); _t.time = lambda: _frozen

from pathlib import Path
import argparse, ast, fcntl, io, json, shutil, struct, time
import pycdlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import disccache

T0 = time.monotonic()
HERE = Path(HARNESS); ROOT = HERE.parent
SROOT = Path(os.environ.get('RE4DC_STAGE_ROOT', '/root/stage'))
CAS = SROOT / 'cas'; CAS.mkdir(parents=True, exist_ok=True)
VERIFY = os.environ.get('RE4DC_STAGE_CAS_VERIFY', '0') == '1'
IO = dict(p9_read=0, p9_write=0, cas_hits=0, cas_misses=0)

def _ninep_mounts():
    out = []
    with open('/proc/mounts') as f:
        for line in f:
            dev, mnt, fs = line.split()[:3]
            if fs in ('9p', 'drvfs', 'v9fs'):
                out.append(mnt.replace('\\040', ' ').rstrip('/') + '/')
    return out
NINEP = _ninep_mounts()

def on_9p(p):
    return any(str(p).startswith(m) for m in NINEP)

def _hash_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()

def cas(src):
    """ext4 path with the content of src. 9p sources go through the cache; ext4 sources are used in place."""
    src = Path(src)
    if not on_9p(src):
        return src
    st = os.stat(src)
    # pycdlib copies the source's permission bits into the Rock Ridge PX record: the cached object keeps them
    mode = st.st_mode & 0o7777
    key = hashlib.sha256(('%s\0%d\0%d' % (os.path.realpath(src), st.st_size, st.st_mtime_ns)).encode()).hexdigest()
    ref = CAS / 'keys' / key[:2] / key
    if ref.exists():
        sha = ref.read_text().strip()
        obj = CAS / 'obj' / sha[:2] / ('%s-%o' % (sha, mode))
        if obj.exists() and obj.stat().st_size == st.st_size and (not VERIFY or _hash_file(obj) == sha):
            IO['cas_hits'] += 1
            os.utime(ref)
            return obj
    tmpdir = CAS / 'tmp'; tmpdir.mkdir(exist_ok=True)
    tmp = tmpdir / ('%d.%s' % (os.getpid(), key[:16]))
    h = hashlib.sha256(); n = 0
    with open(src, 'rb') as fi, open(tmp, 'wb') as fo:
        for b in iter(lambda: fi.read(1 << 22), b''):
            h.update(b); fo.write(b); n += len(b)
    if n != st.st_size or os.stat(src).st_mtime_ns != st.st_mtime_ns:
        tmp.unlink(); raise SystemExit('stage_scenario.py: %s changed while it was cached' % src)
    sha = h.hexdigest()
    obj = CAS / 'obj' / sha[:2] / ('%s-%o' % (sha, mode)); obj.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(tmp, mode); os.replace(tmp, obj)
    ref.parent.mkdir(parents=True, exist_ok=True)
    rt = ref.with_name(ref.name + '.%d' % os.getpid()); rt.write_text(sha + '\n'); os.replace(rt, ref)
    IO['cas_misses'] += 1; IO['p9_read'] += n
    return obj

def cas_text(src):
    return cas(src).read_text()

# ---- stage-scenario.py (DERIVED_SHA), inputs through cas(), image on ext4 ----
BASE = Path('/root/probe/d367-resume-20260927/integration-01/disc-ig27rc1-kite7/disc.bin')
BASE_SHA = 'c2237d1a08e14c5a9dc67d178f631f5b905b50b9f4744012326ea97db40dca56'
utility = ROOT / 'renderer/inventory-uiorder-r1/stage-iso.py'; text = cas_text(utility)
assert hashlib.sha256(text.encode()).hexdigest() == 'f95bfad4b2d1a1be0dfbb3bf99331841ddaeaa739435f3f89df614a10d50d9d6'
ns = dict(Path=Path, hashlib=hashlib, io=io, pycdlib=pycdlib)
defs = ast.parse(text)
exec(compile(ast.Module(body=[n for n in defs.body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name in
                              {'sha', 'HashSink', 'manifest', 'primary_path', 'replace'}], type_ignores=[]), str(utility), 'exec'), ns)
sha, manifest, primary_path, replace = (ns[k] for k in ('sha', 'manifest', 'primary_path', 'replace'))

def base_ok():
    # the 785 MB base is hashed once per (size, mtime, inode), not on every staging
    st = BASE.stat(); memo = SROOT / 'base-verified.json'; k = '%d:%d:%d' % (st.st_size, st.st_mtime_ns, st.st_ino)
    try:
        if json.loads(memo.read_text()).get(k) == BASE_SHA:
            return True
    except Exception:
        pass
    if sha(BASE) != BASE_SHA:
        return False
    t = memo.with_name('base-verified.%d' % os.getpid()); t.write_text(json.dumps({k: BASE_SHA})); os.replace(t, memo)
    return True

def iso_primary_name(name, directory=False):
    # lane ch2code16 2026-10-16 (Codex's stage-scenario-v2 ISO-name fix, cx_iso_names.py): an ISO9660 primary name keeps
    # only A-Z, 0-9 and _ and one extension, so a two-extension event file (evd/e113.evd.evq, r113 / r11c / r11f events)
    # stages; every name the old upper()/'-'->'_' rule accepted maps to the same primary name as before.
    def clean(part):
        return ''.join(c if ('A' <= c <= 'Z' or '0' <= c <= '9' or c == '_') else '_' for c in part.upper())
    if directory or '.' not in name:
        return clean(name)
    stem, ext = name.rsplit('.', 1)
    return clean(stem) + '.' + clean(ext)

def ensure_dir(iso, parent):
    done = ''
    for name in [p for p in parent.split('/') if p]:
        path = done + '/' + name
        try: iso.get_record(rr_path=path)
        except Exception:
            base = primary_path(iso.get_record(rr_path=done or '/')).rstrip('/')
            iso.add_directory(iso_path=base + '/' + iso_primary_name(name, directory=True), rr_name=name, joliet_path=path)
        done = path

def add(iso, files):
    streams = []
    for path, source in files.items():
        parent, name = path.rsplit('/', 1) if '/' in path else ('', path)
        ensure_dir(iso, parent)
        ip = primary_path(iso.get_record(rr_path='/' + parent)).rstrip('/') + '/' + iso_primary_name(name) + ';1'
        stream = source.open('rb'); streams.append(stream)
        iso.add_fp(stream, source.stat().st_size, iso_path=ip, rr_name=name, joliet_path='/' + path)
    return streams

def remove(iso, path):
    r = iso.get_record(joliet_path='/' + path)
    prim = [x for x, is_pvd in r.inode.linked_records if is_pvd]; assert len(prim) == 1
    iso.rm_file(iso_path=primary_path(prim[0]))

def diff(a, b): return dict(removed=sorted(a.keys() - b.keys()), added=sorted(b.keys() - a.keys()),
                            changed=sorted(k for k in a.keys() & b.keys() if a[k] != b[k]))

p = argparse.ArgumentParser(); p.add_argument('scenario'); p.add_argument('--arm', required=True)
p.add_argument('--programs', type=Path, default=HERE / 'programs.json')
p.add_argument('--overlay', type=Path, required=True); p.add_argument('--fixture', type=Path)
p.add_argument('--capture-reserve-mib', type=int, choices=(128, 256, 512), default=256)
a = p.parse_args()
out = HERE / 'scenarios' / a.scenario; assert not out.exists(), 'Preserve earlier scenario'
work = SROOT / 'scen' / a.scenario; assert not work.exists(), 'stale ext4 stage dir %s (clean.sh)' % work
assert base_ok()
media = json.loads(cas_text(ROOT / 'integration-source-r11/MEDIA.json'))['assets']
changes = {}; digests = {}
for entry in media:
    dest = entry['eventual_disc_destination']; src = cas(a.overlay / dest)
    assert src.is_file() and sha(src) == entry['sha256'] and src.stat().st_size == entry['bytes'], dest
    assert dest not in changes; changes[dest] = src; digests[dest] = entry['sha256']
program = json.loads(cas_text(a.programs))[a.arm]
for dest, name in [('1ST_READ.BIN', '1ST_READ.BIN'), ('dc/sscrn.ovl', 'sscrn.ovl')]:
    src = cas(HERE / 'programs' / a.arm / name); assert sha(src) == program['files'][name]['sha256']; changes[dest] = src
    digests[dest] = program['files'][name]['sha256']
fixture = json.loads(cas_text(a.fixture)) if a.fixture else {}
for dest, source in fixture.get('replace', {}).items():
    # a replaced MEDIA / program destination must not keep its old digest: drop it so file_sha() hashes the new
    # source (castle lane 2026-10-15: 14 replaced MEDIA textures failed 'Payload/namespace mismatch')
    changes[dest] = cas((a.fixture.parent / source).resolve()); digests.pop(dest, None)
removals = fixture.get('remove', []); assert not (set(removals) & set(changes))
def file_sha(src):
    # ext4 fixture sources (tex.pak etc.) are hashed once per (path, size, mtime, inode)
    st = os.stat(src)
    k = hashlib.sha256(('%s\0%d\0%d\0%d' % (os.path.realpath(src), st.st_size, st.st_mtime_ns, st.st_ino)).encode()).hexdigest()
    ref = CAS / 'dkeys' / k[:2] / k
    if ref.exists():
        return ref.read_text().strip()
    h = sha(src)
    ref.parent.mkdir(parents=True, exist_ok=True)
    rt = ref.with_name(k + '.%d' % os.getpid()); rt.write_text(h + '\n'); os.replace(rt, ref)
    return h
for dest, src in changes.items():
    if dest not in digests: digests[dest] = file_sha(src)
# Route overlays (lane r118fault, 2026-10-15). A dc/<m>.ovl (pl0f, em2f, em22, em2b, pl11, ...) is linked against ONE
# game image: routeOverlayLoad (platform/modules.cpp) relocates only the overlay's own code and data, so its calls and
# stores into the image (EmInitFunc, Em10SetFunc, ...) keep the addresses of the build it came from. t11-fix.py keeps the
# program label a fixture was made for: mx-r118.json (made for t14drW) staged t14drW's pl11.ovl with t14idrW / t14hdrW /
# t14rcrW, pl11's _prolog stored Pl11Init at t14drW's EmInitFunc address, Ashley was built with the stale Em17Init and
# the r118 entry faulted (FAULT 780 in a KOS vblank node / FAULT 180; t14gdrW passed by luck of layout). A staged overlay
# must be the arm's own build whenever the arm has one; retarget a fixture with texchk/fixture_arm.py.
# RE4DC_STAGE_OVL_ANY=1 skips the check (never for a gate).
own_ovl = {'dc/' + n: f['sha256'] for n, f in program['files'].items() if n.endswith('.ovl')}
foreign = sorted(d for d in own_ovl if d in changes and digests[d] != own_ovl[d])
if foreign and os.environ.get('RE4DC_STAGE_OVL_ANY') != '1':
    sys.exit('STAGE REFUSED: the fixture %s stages %s built for another program than arm %s (a route overlay is linked '
             'against one game image); retarget it: port/dreamcast/tools/d367/texchk/fixture_arm.py <fixture> <out> <label>'
             % (a.fixture, ', '.join(foreign), a.arm))
upper = BASE.stat().st_size + sum(f.stat().st_size for f in changes.values()) + 1024 ** 2
reserve = a.capture_reserve_mib * 1024 ** 2
key = hashlib.sha256(json.dumps(dict(base=BASE_SHA, derived=DERIVED_SHA, pycdlib=getattr(pycdlib, '__version__', '?'),
                                     changes=[[d, digests[d], changes[d].stat().st_size, changes[d].stat().st_mode & 0o7777]
                                              for d in changes],
                                     removals=removals)).encode()).hexdigest()
INDEX = SROOT / 'images'; INDEX.mkdir(exist_ok=True)
LOCKS = SROOT / 'locks'; LOCKS.mkdir(exist_ok=True)
t_in = time.monotonic()
use_cache = os.environ.get('RE4DC_DISCCACHE', '') != '0'
reused = False; copied = 0
# Disk hygiene rule (user, 2026-10-15): with less than 40 GB free on C: or D:, prune old build outputs first
# (prune_if_low.sh: evidence-root discs now, idle WSL objdirs/discs in the background), so the capacity check below
# does not refuse the run for space a rebuildable output holds. PRUNE_AUTO=0 skips it; PRUNE_LOW_GB sets the level.
if os.environ.get('PRUNE_AUTO', '1') != '0':
    # tools/d367/prune_if_low.sh in a tree; next to the installed copy in the harness (stage-ext4/install.sh)
    _here = Path(__file__).resolve().parent
    _prune = next((p for p in (_here.parent / 'prune_if_low.sh', _here / 'prune_if_low.sh') if p.exists()), None)
    if _prune:
        import subprocess
        subprocess.run(['bash', str(_prune)], stdout=sys.stderr, stderr=sys.stderr, check=False)
lk = open(LOCKS / (key + '.lock'), 'w'); fcntl.flock(lk, fcntl.LOCK_EX)  # one build per input key at a time
try:
    rec = None
    if use_cache and os.environ.get('RE4DC_STAGE_REUSE', '1') != '0' and (INDEX / (key + '.json')).exists():
        rec = json.loads((INDEX / (key + '.json')).read_text())
        cached = disccache.lookup(rec['disc_sha256'], 'disc.bin')
        if cached is None or cached.stat().st_size != rec['disc_bytes']:
            rec = None
    if rec is not None:
        reused = True
        before, after = rec['before'], rec['after']; disc_sha, disc_bytes = rec['disc_sha256'], rec['disc_bytes']
        stage_capacity = dict(free_before=shutil.disk_usage('/mnt/c').free, image_upper_bound=upper,
                              capture_reserve=reserve, floor=16 * 1024 ** 3)
        assert stage_capacity['free_before'] - reserve >= stage_capacity['floor']
        t_built = time.monotonic()
    else:
        # the image is built on ext4 (its vhdx is on C: too, until the ext4 copy is deleted) and then cached on C:
        if use_cache:
            with disccache.locked(): disccache.evict(need=2 * upper, reserve=reserve)
        stage_capacity = dict(free_before=shutil.disk_usage('/mnt/c').free,
                              image_upper_bound=upper, capture_reserve=reserve, floor=16 * 1024 ** 3)
        assert stage_capacity['free_before'] - upper - stage_capacity['capture_reserve'] >= stage_capacity['floor']
        iso = pycdlib.PyCdlib(); iso.open(str(BASE)); cache = {}
        before = manifest(iso, 'joliet', cache); before_rr = manifest(iso, 'rr', cache)
        assert before == json.loads((BASE.parent / 'payload-manifest.json').read_text())
        removed = [x for x in removals if x in before]
        for path in removed: remove(iso, path)
        replacements = {k: v for k, v in changes.items() if k in before}
        additions = {k: v for k, v in changes.items() if k not in before}
        streams, metadata = replace(iso, replacements); streams += add(iso, additions)
        expected = {k: v for k, v in before.items() if k not in removed}
        expected_rr = {k: v for k, v in before_rr.items() if k not in removed}
        for k, src in changes.items(): expected[k] = expected_rr[k] = dict(size=src.stat().st_size, sha256=digests[k])
        with BASE.open('rb') as f: boot = f.read(32768)
        assert boot.startswith(b'SEGA SEGAKATANA')
        work.mkdir(parents=True); (work / 'disc').mkdir(); disc = work / 'disc/disc.bin'
        with disc.open('x+b') as f: iso.write_fp(f); f.seek(0); f.write(boot)
        iso.close()
        for f in streams: f.close()
        iso = pycdlib.PyCdlib(); iso.open(str(disc)); cache = {}
        after = manifest(iso, 'joliet', cache); after_rr = manifest(iso, 'rr', cache); iso.close()
        assert after == expected and after_rr == expected_rr, 'Payload/namespace mismatch'
        reader = ROOT / 'gameplay/verify_cost_inputs.py'; rd = {'Path': Path, 'hashlib': hashlib, 'json': json, 'struct': struct}
        exec(compile(ast.Module(body=[n for n in ast.parse(cas_text(reader)).body if isinstance(n, ast.FunctionDef)],
                                type_ignores=[]), str(reader), 'exec'), rd)
        assert rd['disc_manifest'](disc) == after
        with disc.open('rb') as f: assert f.read(32768) == boot
        assert disc.stat().st_size <= upper
        disc_sha = sha(disc); disc_bytes = disc.stat().st_size
        t_built = time.monotonic()
    # ---- the crossing: link to the cached image (copied in once), or a private copy ----
    out.mkdir(parents=True); (out / 'disc').mkdir(); final = out / 'disc/disc.bin'
    if use_cache:
        if not reused:
            cached, copied = disccache.put(disc, disc_sha, 'disc.bin', reserve=reserve)
            t = INDEX / ('%s.json.%d' % (key, os.getpid()))
            t.write_text(json.dumps(dict(disc_sha256=disc_sha, disc_bytes=disc_bytes, before=before, after=after)))
            os.replace(t, INDEX / (key + '.json'))
        disccache.link(cached, final)
    else:
        with disc.open('rb') as fi, final.open('xb') as fo:
            for b in iter(lambda: fi.read(1 << 22), b''):
                fo.write(b); copied += len(b)
    IO['p9_write'] += copied
    assert final.stat().st_size == disc_bytes, 'staged image size mismatch'
    t_copied = time.monotonic()
finally:
    fcntl.flock(lk, fcntl.LOCK_UN); lk.close()
    if os.environ.get('RE4DC_STAGE_KEEP', '0') != '1':
        shutil.rmtree(work, ignore_errors=True)
report = dict(status='STAGED_PAYLOAD_IDENTITY_PASS', scenario=a.scenario, arm=a.arm, elf_sha256=program['elf_sha256'], capacity=stage_capacity,
              base=str(BASE), base_sha256=BASE_SHA, disc_sha256=disc_sha, disc_bytes=disc_bytes,
              both_namespaces_verified=True, independent_raw_reader_verified=True, boot_area_preserved=True,
              payload_delta=diff(before, after), fixture=fixture, media_records=len(media), free_c_after=shutil.disk_usage('/mnt/c').free)
docs = [(out / 'payload-manifest.json', json.dumps(after, indent=2) + '\n'),
        (out / 'disc/disc.cue', 'FILE "disc.bin" BINARY\n  TRACK 01 MODE1/2048\n    INDEX 01 00:00:00\n')]
for path, body in docs: IO['p9_write'] += len(body.encode())
report['ext4'] = dict(input_key=key, reused_image=reused, linked=use_cache, stage_dir=str(work),
                      inputs_s=round(t_in - T0, 2), build_verify_s=round(t_built - t_in, 2), cross_s=round(t_copied - t_built, 2),
                      wall_s=round(time.monotonic() - T0, 2), **IO)
(out / 'stage.json').write_text(json.dumps(report, indent=2) + '\n')
for path, body in docs: path.write_text(body)
print(json.dumps(report, indent=2))
