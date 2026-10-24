"""Exact-byte append-only evidence checkpoint; no game/media operations."""
from pathlib import Path
import datetime,hashlib,io,json,subprocess,tarfile
LANE=Path('/mnt/c/Game Dev/Emulators/codex-lanes/gc-motion24')
SRC=LANE/'kos-budget-retest-guest-prep-v2'
TREE=Path('/root/work/lanes/gc23-evidence-tools')
REL='port/dreamcast/tools/d367/gc23_evidence/20261024-budget427-kos-guest-recovery-plan-v2'
DEST=TREE/REL
def git(*args):return subprocess.check_output(['git','-C',str(TREE),*args])
def row(raw):return dict(size=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def fresh(path,raw):
 with path.open('xb') as f:f.write(raw)
def encoded(value):return (json.dumps(value,indent=1)+'\n').encode()
if __name__=='__main__':
 assert git('status','--porcelain')==b'','Evidence tree has other edits'
 parent=git('rev-parse','HEAD').decode().strip()
 assert parent=='8c9cf9d5621b067dc10073b832e6e387b60e4a30','Revalidate moved archive HEAD; no reset'
 assert git('branch','--show-current').decode().strip()=='wip/gc23-evidence-tools-20261024'
 seal=(SRC/'PLAN-SEAL.json').read_bytes();assert row(seal)==dict(size=1753,sha256='b6e24101a8e1889f278f48a1603384f87efa6a8445fe750f79b51860210e053b')
 pins=json.loads(seal)['members']
 selected={p.name:p.read_bytes() for p in SRC.iterdir() if p.is_file()}
 assert set(selected)==set(pins)|{'PLAN-SEAL.json','READBACK.json'}
 for name,pin in pins.items():assert row(selected[name])==pin
 assert all(not p.is_symlink() for p in SRC.iterdir())
 assert not DEST.exists();DEST.mkdir(parents=True)
 sources={}
 for name,raw in selected.items():fresh(DEST/name,raw);sources[name]=dict(path=str(SRC/name),**row(raw))
 own=Path(__file__);raw=own.read_bytes();fresh(DEST/'archive_source.py',raw);sources['archive_source.py']=dict(path=str(own),**row(raw))
 fresh(DEST/'.gitattributes',b'* -text\n')
 fresh(DEST/'SOURCE-MANIFEST.json',encoded(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),parent=parent,source_members=sources,bytes=sum(x['size'] for x in sources.values()),line_endings='Original bytes; Git text normalization disabled locally')))
 fresh(DEST/'DISCLOSURE.md',b'# Pending recovery plan snapshot\n\nSource/plan only, no current baseline, no SDK/stage/guest authority.39 synthetic/RAM controls pass. Protected Rain-produced OFF path/identity and fresh both-media readback remain pending. Prior2301/4dd/7b512 and missing-track HOLD remain immutable. Root-reported hourly compaction cause is explicitly coordination context, not new forensic proof. No programme/asset/image/track/capture bytes are included.\n')
 expected={p.relative_to(TREE).as_posix():p.read_bytes() for p in DEST.iterdir()}
 git('add','--',REL)
 staged=git('diff','--cached','--name-only','-z').split(b'\0');assert {x.decode() for x in staged if x}==set(expected)
 for name,raw in expected.items():assert git('show',':'+name)==raw,'Index bytes changed'
 git('commit','-m','Preserve pending GC KOS guest recovery plan and honest missing-media HOLD')
 commit=git('rev-parse','HEAD').decode().strip()
 for name,raw in expected.items():assert git('show',commit+':'+name)==raw,'Git object bytes changed'
 archive=git('archive','--format=tar',commit,REL)
 with tarfile.open(fileobj=io.BytesIO(archive),mode='r:') as t:
  actual={m.name:t.extractfile(m).read() for m in t.getmembers() if m.isfile()}
 assert actual==expected,'Git archive re-export differs'
 git('push','origin','HEAD:refs/heads/wip/gc23-evidence-tools-20261024')
 remote=git('ls-remote','origin','refs/heads/wip/gc23-evidence-tools-20261024').decode().split()[0];assert remote==commit
 assert git('status','--porcelain')==b''
 receipt=dict(status='EXACT_GIT_OBJECT_AND_ARCHIVE_EXPORT_REMOTE_PASS_PENDING_MEDIA_PLAN_ONLY',commit=commit,remote=remote,parent=parent,path=REL,files=len(expected),bytes=sum(map(len,expected.values())),plan_seal=row(seal),manifest=row(expected[REL+'/SOURCE-MANIFEST.json']),all_original_bytes=True,normalization='none',SDK=0,stage=0,guest=0)
 fresh(LANE/'kos-budget-retest-guest-recovery-v2-ARCHIVE.json',encoded(receipt));print(json.dumps(receipt))
