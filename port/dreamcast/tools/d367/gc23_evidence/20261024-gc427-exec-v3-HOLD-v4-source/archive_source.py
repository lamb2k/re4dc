"""Append frozen failed V3/review and narrow V4 source; exact bytes only."""
from pathlib import Path
import datetime,hashlib,io,json,subprocess,tarfile
LANE=Path('/mnt/c/Game Dev/Emulators/codex-lanes/gc-motion24')
TREE=Path('/root/work/lanes/gc23-evidence-tools')
REL='port/dreamcast/tools/d367/gc23_evidence/20261024-gc427-exec-v3-HOLD-v4-source'
PARENT='ae52e91a5bfef7f17ceaec1a8f4dcc959cf62e63'
def git(*a):return subprocess.check_output(['git','-C',str(TREE),*a])
def row(raw):return dict(size=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def fresh(path,raw):
 path.parent.mkdir(parents=True,exist_ok=True)
 with path.open('xb') as f:f.write(raw)
def encoded(j):return (json.dumps(j,indent=1)+'\n').encode()
if __name__=='__main__':
 assert git('status','--porcelain')==b'' and git('rev-parse','HEAD').decode().strip()==PARENT
 assert git('branch','--show-current').decode().strip()=='wip/gc23-evidence-tools-20261024'
 dest=TREE/REL;assert not dest.exists();dest.mkdir(parents=True)
 sources={}
 for version,digest in [('v3','0296f5782e8c94ccc65a46cfcd5171fdf5d6c3348914b6af80190245961c4dbc'),('v4','71e2937661a3a47556a2cb375c70c4ad51ddfae18ef26aac1d233dc6963a8424')]:
  root=LANE/('kos-budget-retest-guest-exec-'+version);seal=(root/'SOURCE-REVIEW-SEAL.json').read_bytes();assert row(seal)['sha256']==digest
  pins=json.loads(seal)['members'];assert {p.name for p in root.iterdir()}==set(pins)|{'SOURCE-REVIEW-SEAL.json','SOURCE-READBACK.json'}
  for p in root.iterdir():
   assert p.is_file() and not p.is_symlink();raw=p.read_bytes()
   if p.name in pins:assert row(raw)==pins[p.name]
   target='frozen-'+version+'/'+p.name;fresh(dest/target,raw);sources[target]=dict(path=str(p),**row(raw))
 review=LANE/'review-kos-budget-retest-guest-exec-v3-worldmeter';raw=(review/'REVIEW-SEAL.json').read_bytes();assert row(raw)['sha256']=='9e27c773fecb47b37ba6472481f62f104b0ff6417bda1881647ee8353ecd8578'
 for name,pin in {**json.loads(raw)['members'],'REVIEW-SEAL.json':row(raw)}.items():
  p=review/name;assert p.is_file() and not p.is_symlink();data=p.read_bytes();assert row(data)==pin and len(data)<128*1024
  target='independent-v3-HOLD/'+name;fresh(dest/target,data);sources[target]=dict(path=str(p),**row(data))
 own=Path(__file__);raw=own.read_bytes();fresh(dest/'archive_source.py',raw);sources['archive_source.py']=dict(path=str(own),**row(raw))
 fresh(dest/'.gitattributes',b'* -text\n')
 fresh(dest/'SOURCE-MANIFEST.json',encoded(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),parent=PARENT,source_members=sources,bytes=sum(v['size'] for v in sources.values()),normalization='none; originals preserved including line endings')))
 fresh(dest/'DISCLOSURE.md',b'# Frozen V3 failure and V4 source successor\n\nPreserves exact0296 failed source, independent encoded-callable collision HOLD and actual statement reproduction. V4 fixes drift_bytes only, with successful real binder statement serialization and preservedV3 TypeError regression.89 source/host checks pass; preservedV3 metadata explicitly becomes17thretained root. No current baseline/binding/finalguestseal/grant exists. Actual media proof is referenced by metadata hashes; no track/programme/ELF/object/asset/IP/image/capture bytes copied. All controller/common source stays exact; no runtime/SDK/stage/guest changes. Fresh user H2 allowance is separately root-owned/unconsumed; this controller remains four45/55-second KOS cases/H2false. Root owns actualmedia binding and all acceptance.\n')
 expected={p.relative_to(TREE).as_posix():p.read_bytes() for p in dest.rglob('*') if p.is_file()}
 git('add','--',REL)
 assert {s.decode() for s in git('diff','--cached','--name-only','-z').split(b'\0') if s}==set(expected)
 for n,b in expected.items():assert git('show',':'+n)==b
 git('commit','-m','Preserve failed GC binder review and narrow serialized-binding source repair')
 commit=git('rev-parse','HEAD').decode().strip()
 for n,b in expected.items():assert git('show',commit+':'+n)==b
 with tarfile.open(fileobj=io.BytesIO(git('archive','--format=tar',commit,REL)),mode='r:') as t:exported={m.name:t.extractfile(m).read() for m in t.getmembers() if m.isfile()}
 assert exported==expected
 git('push','origin','HEAD:refs/heads/wip/gc23-evidence-tools-20261024')
 remote=git('ls-remote','origin','refs/heads/wip/gc23-evidence-tools-20261024').decode().split()[0];assert remote==commit and git('status','--porcelain')==b''
 receipt=dict(status='EXACT_GIT_BYTES_ARCHIVE_EXPORT_REMOTE_PASS_SOURCE_PENDING_BINDING',parent=PARENT,commit=commit,remote=remote,path=REL,files=len(expected),bytes=sum(map(len,expected.values())),manifest=row(expected[REL+'/SOURCE-MANIFEST.json']),V3_HOLD_seal='0296f5782e8c94ccc65a46cfcd5171fdf5d6c3348914b6af80190245961c4dbc',V4_source_seal='71e2937661a3a47556a2cb375c70c4ad51ddfae18ef26aac1d233dc6963a8424',SDK=0,stage=0,guest=0)
 fresh(LANE/'kos-budget-retest-exec-v3-v4-ARCHIVE.json',encoded(receipt));print(json.dumps(receipt))
