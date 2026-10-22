"""Integrate the sealed nine-row delta into the owned mipmap worktree."""
from pathlib import Path
import hashlib, json, shutil, subprocess

TREE = Path('/root/probe/codex-mipmap21-integration')
RECT = TREE/'port/dreamcast/tools/d367/texture_rect21'
DELTA = Path('/root/re4data/private/texture-world-next21-r101-scoped9-v2-20261021')
MIRROR = Path('/mnt/c/Game Dev/Emulators/re4-assets-private/texture-world-next21-r101-scoped9-v2-20261021')
EVIDENCE = Path('/mnt/c/Flycast-Evidence/re4-dreamcast/texture-world-next21-r101-20261021')
OUT = Path('/root/probe/mipmap21-integration-world26-20261021')
assert not OUT.exists()
assert subprocess.check_output(['git','-C',str(TREE),'rev-parse','HEAD'],text=True).strip() == 'b9201d0452e9090c05781f489be2e47f4650ef97'
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
assert sha(EVIDENCE/'SHA256SUMS-FINAL.txt') == '0d71d3ff1c7f2192ec00b38fa6a7e03c727ac1c7e4e035bcb60027359ceee92f'
for line in (EVIDENCE/'SHA256SUMS-FINAL.txt').read_text().splitlines():
 digest,relative = line.split('  ',1)
 assert sha(EVIDENCE/relative) == digest, relative
for root in (DELTA,MIRROR):
 for line in (root/'SHA256SUMS').read_text().splitlines():
  digest,relative = line.split('  ',1)
  assert sha(root/relative) == digest, str(root/relative)
assert sha(DELTA/'receipt.json') == 'f078139b74ff1f1050992f1c3dc6420d3be53d6a77a11e6a04a7905c94b5c35f'
paths = ['scoped_representations.inc','provenance_certificates.inc','world_rect_provenance.h','world_rect_bind.h']
before = {name:sha(RECT/name) for name in paths}
for name in paths:
 assert (RECT/name).read_bytes() == (EVIDENCE/('actual-input-'+name)).read_bytes(), name
OUT.mkdir()
for name in paths: shutil.copyfile(RECT/name,OUT/('before-'+name))
for name,addition in [('scoped_representations.inc','proposed_representations.inc'),('provenance_certificates.inc','proposed_provenance_certificate.inc')]:
 original = (RECT/name).read_bytes()
 extra = (DELTA/addition).read_bytes().replace(b'// PROPOSED r101 nine. Not installed in the active guarded table.', b'// Integrated r101 nine; the enclosing WORLD_RECT21 guard defaults to zero.')
 (RECT/name).write_bytes(original + b'\n' + extra)
p = RECT/'world_rect_provenance.h'
text = p.read_text()
needle = 'static_assert(sizeof(certificates)/sizeof(certificates[0])==2U);'
assert text.count(needle) == 1
text = text.replace(needle,needle.replace('==2U','==3U'))
text = text.replace('// Scoped17 policy/source provenance, never physical file integrity.', '// Scoped26 policy/source provenance, never physical file integrity.')
text = text.replace('// CRC/record validation. The two immutable full-file certificates come from', '// CRC/record validation. The three immutable full-file certificates come from')
text = text.replace('// 78 key-only remaps (74 OP,4 VA); all geometry/placements/pass/cull remain', '// 90 key-only remaps (86 OP,4 VA); all geometry/placements/pass/cull remain')
text = text.replace('// exact and the 17 RGB565 replacements have opaque alpha at every mip level.', '// exact and the 26 RGB565 replacements have opaque alpha at every mip level.')
p.write_text(text)
# This probe now includes the actual integrated headers, rather than host copies.
shutil.copyfile(EVIDENCE/'probe.cpp',OUT/'probe.cpp')
command = ['g++','-std=c++17','-O1','-g0','-fsanitize=undefined','-fno-sanitize-recover=all','-I'+str(RECT),str(OUT/'probe.cpp'),'-o',str(OUT/'probe')]
build = subprocess.run(command,capture_output=True,text=True)
(OUT/'compile.txt').write_text(build.stdout+build.stderr)
assert build.returncode == 0, build.stderr
current = Path('/root/re4data/private/texture-rect21-current948-scoped17-20261021')
worlds = [current/'dc/native/r100/ps2-world.r4pw',current/'dc/native/r103/ps2-world.r4pw',DELTA/'dc/native/r101/ps2-world.r4pw']
run = subprocess.run([str(OUT/'probe'),*map(str,worlds)],capture_output=True,text=True)
assert run.returncode == 0 and run.stdout.strip() == '402', run.stderr
after = {name:sha(RECT/name) for name in paths}
assert before['world_rect_bind.h'] == after['world_rect_bind.h']
receipt = dict(state='INTEGRATED_SOURCE_HOST_ONLY',base_commit='b9201d0452e9090c05781f489be2e47f4650ef97',delta_commit='1c34b593c9cc328bc2c9e09f2ff33c8b3f407c08',delta_receipt_sha256=sha(DELTA/'receipt.json'),delta_seal_sha256=sha(DELTA/'SHA256SUMS'),before=before,after=after,representation_rows=26,certificate_rows=3,changed_world_bindings=90,host_checks=402,host_command=command,probe_source_sha256=sha(OUT/'probe.cpp'),probe_sha256=sha(OUT/'probe'),worlds={str(p):sha(p) for p in worlds},original_two_room_audit_json_unchanged=True,experimental_default_zero=True,limits=['No new SH4 object or linked programme','No materialized combined pack or image','No new Flycast mipmap qualification or look/performance/release/hardware acceptance'])
(OUT/'integration.json').write_text(json.dumps(receipt,indent=2)+'\n')
(RECT/'integration_world26.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(dict(state=receipt['state'],host_checks=402,representations=26,certificates=3)))
