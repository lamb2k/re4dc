"""Install the sealed CRC-correct world36 tables in the isolated integration tree."""
from pathlib import Path
import hashlib,json,shutil,subprocess
T=Path('/root/probe/codex-mipmap21-integration');R=T/'port/dreamcast/tools/d367/texture_rect21'
D=Path('/root/re4data/private/texture-world36-canonical-crc-20261021')
M=Path('/mnt/c/Game Dev/Emulators/re4-assets-private')/D.name
E=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/texture-world36-canonical-crc-20261021')
O=Path('/root/probe/mipmap21-canonical-integration-20261021');assert not O.exists()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(E/'SHA256SUMS-FINAL.txt')=='c9a68b224a109b0f1be33f8f1282b3e8c21c87c8d6dce5a793ef7ec74540a27c'
for root,seal in [(E,'SHA256SUMS-FINAL.txt'),(D,'SHA256SUMS'),(M,'SHA256SUMS')]:
 for line in (root/seal).read_text().splitlines():
  digest,name=line.split('  ',1);assert sha(root/name)==digest,str(root/name)
assert sha(D/'receipt.json')=='77700bf92d3585285b9d14fa8eaa067b90c39f23d9e455abf300fd4c8c6b0789'
O.mkdir();names=['scoped_representations.inc','provenance_certificates.inc','world_rect_provenance.h','world_rect_bind.h']
before={n:sha(R/n) for n in names}
for n in names:shutil.copyfile(R/n,O/('before-'+n))
(R/'scoped_representations.inc').write_bytes((D/'proposed_representations.inc').read_bytes())
(R/'provenance_certificates.inc').write_bytes((D/'proposed_provenance_certificates.inc').read_bytes())
p=R/'world_rect_provenance.h';s=p.read_text();assert s.count('==4U);')==1 and s.count('The four immutable')==1
p.write_text(s.replace('==4U);','==3U);').replace('The four immutable','The three immutable'))
shutil.copyfile(E/'helper-probe.cpp',O/'probe.cpp')
cmd=['g++','-std=c++17','-O1','-g0','-fsanitize=undefined','-fno-sanitize-recover=all','-I'+str(R),str(O/'probe.cpp'),'-o',str(O/'probe')]
build=subprocess.run(cmd,capture_output=True,text=True);assert build.returncode==0,build.stderr
worlds=[D/'dc/native'/room/'ps2-world.r4pw' for room in ('r100','r101','r103')]
run=subprocess.run([str(O/'probe'),*map(str,worlds)],capture_output=True,text=True);assert run.returncode==0 and run.stdout.strip()=='573',run.stderr
after={n:sha(R/n) for n in names};assert before['world_rect_bind.h']==after['world_rect_bind.h']
q=Path('/root/probe/mipmap21-emitter-crc-repair-20261021/tests/qualification.json');assert json.loads(q.read_text())['status']=='PASS'
receipt=dict(state='CANONICAL_1004_WORLD_SOURCE_INTEGRATED',before=before,after=after,canonical_delta_source='94a6d54076eb1e9ed05d61ae72c67b2eedad8d92',canonical_delta_receipt_sha256=sha(D/'receipt.json'),canonical_delta_seal_sha256=sha(D/'SHA256SUMS'),representations=36,certificates=3,header_only_world_repairs=21,legacy_world_ids_rejected=21,host_checks=573,host_command=cmd,probe_sha256=sha(O/'probe'),emitter_qualification_sha256=sha(q),actual_Package_strict_and_CRC_stream_emitter_cases=48,worlds={str(w):sha(w) for w in worlds},guard_default_zero=True,runtime_CRC_unchanged=True,limits=['New canonical programme/pack/image not built by this unit','Previous994packs/programmes preserved on CRC hold','No Flycast/performance/release/hardware acceptance'])
for p in (O/'integration.json',R/'integration_canonical_world36.json'):p.write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(dict(state=receipt['state'],host_checks=573,worlds=3,legacy_ids_rejected=21)))
