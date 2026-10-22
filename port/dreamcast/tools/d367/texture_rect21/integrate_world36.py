"""Integrate the next sealed ten-row source cohort; preserve the frozen 994 build."""
from pathlib import Path
import hashlib, json, shutil, subprocess
T = Path('/root/probe/codex-mipmap21-integration')
R = T/'port/dreamcast/tools/d367/texture_rect21'
D = Path('/root/re4data/private/texture-world-next21-r103-scoped10-20261021')
M = Path('/mnt/c/Game Dev/Emulators/re4-assets-private')/D.name
E = Path('/mnt/c/Flycast-Evidence/re4-dreamcast/texture-world-next21-r103-20261021/sealed-v2')
O = Path('/root/probe/mipmap21-integration-world36-20261021')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
assert not O.exists()
assert subprocess.check_output(['git','-C',str(T),'rev-parse','HEAD'],text=True).strip() == '845abb1f4ad3a2721d17f64899b6dc59d4bce66c'
assert sha(E/'SHA256SUMS-FINAL.txt') == '9668625b1d61147e0dd7c1289248976cffa0aa2e70ec367fe1ab4ff03af79b7c'
for root,seal in [(E,'SHA256SUMS-FINAL.txt'),(D,'SHA256SUMS'),(M,'SHA256SUMS')]:
 for line in (root/seal).read_text().splitlines():
  digest,name = line.split('  ',1)
  assert sha(root/name) == digest, str(root/name)
assert sha(D/'receipt.json') == 'ad19a67f24081ecfcf85cd2ccab7e4d3a4cb37989c445a1da30bcb9583797e62'
names = ['world_rect_bind.h','world_rect_provenance.h','scoped_representations.inc','provenance_certificates.inc']
before = {n:sha(R/n) for n in names}
for n in names: assert (R/n).read_bytes() == (E/('actual-parent-'+n)).read_bytes(), n
O.mkdir()
for n in names: shutil.copyfile(R/n,O/('before-'+n))
for name,add in [('scoped_representations.inc','proposed_representations.inc'),('provenance_certificates.inc','proposed_provenance_certificate.inc')]:
 extra = (D/add).read_text()
 extra = extra.replace('PROPOSED','Next cohort, integrated experimentally:')
 (R/name).write_bytes((R/name).read_bytes()+b'\n'+extra.encode())
p = R/'world_rect_provenance.h'
s = p.read_text()
for a,b in [('==3U);','==4U);'),('Scoped26','Scoped36'),('The three immutable','The four immutable'),('90 key-only remaps (86 OP,4 VA)','164 key-only remaps (160 OP,4 VA)'),('the 26 RGB565','the 36 RGB565')]:
 assert s.count(a)==1, a
 s=s.replace(a,b)
p.write_text(s)
shutil.copyfile(E/'probe.cpp',O/'probe.cpp')
command = ['g++','-std=c++17','-O1','-g0','-fsanitize=undefined','-fno-sanitize-recover=all','-I'+str(R),str(O/'probe.cpp'),'-o',str(O/'probe')]
b = subprocess.run(command,capture_output=True,text=True)
(O/'compile.txt').write_text(b.stdout+b.stderr)
assert b.returncode==0,b.stderr
P = Path('/root/re4data/private/texture-rect21-current948-scoped17-20261021')
worlds = [P/'dc/native/r100/ps2-world.r4pw',P/'dc/native/r103/ps2-world.r4pw',Path('/root/re4data/private/texture-world-next21-r101-scoped9-v2-20261021/dc/native/r101/ps2-world.r4pw'),D/'dc/native/r103/ps2-world.r4pw']
run = subprocess.run([str(O/'probe'),*map(str,worlds)],capture_output=True,text=True)
assert run.returncode==0 and run.stdout.strip()=='556',run.stderr
after = {n:sha(R/n) for n in names}
assert before['world_rect_bind.h']==after['world_rect_bind.h']
receipt = dict(state='NEXT_1004_SOURCE_HOST_ONLY',parent='845abb1f4ad3a2721d17f64899b6dc59d4bce66c',delta_source='61717e5cf0c299d48fb3fbf71b7f1ef76253434f',before=before,after=after,representations=36,physical_certificates=4,source_rooms=3,prior_r103_certificate_retained=True,host_checks=556,host_command=command,probe_source_sha256=sha(O/'probe.cpp'),probe_sha256=sha(O/'probe'),worlds={str(w):sha(w) for w in worlds},delta_receipt_sha256=sha(D/'receipt.json'),delta_seal_sha256=sha(D/'SHA256SUMS'),frozen_994_program_source='845abb1f4ad3a2721d17f64899b6dc59d4bce66c',frozen_994_program='4ef617a1888ec2fb48c45aae789b8cb21c2c6086f36b1a5d2efe56ceebadb4f9',virtual_1004_pack='9e5a069e6978e00eb61325c935dfd952f01f97036407041063d685da82fdf9c7',limits=['No1004pack or programme written','Frozen994pack/programme preserved','Look/resources/performance/Flycast/release/hardware unaccepted'])
for p in (O/'integration.json',R/'integration_world36.json'): p.write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(dict(state=receipt['state'],checks=556,representations=36,certificates=4)))
