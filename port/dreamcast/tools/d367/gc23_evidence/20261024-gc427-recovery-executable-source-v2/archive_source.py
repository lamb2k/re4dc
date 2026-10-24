"""Exact append-only source/evidence snapshot; no source/media/build mutations."""
from pathlib import Path
import datetime,hashlib,io,json,subprocess,tarfile
LANE=Path('/mnt/c/Game Dev/Emulators/codex-lanes/gc-motion24')
SRC=LANE/'kos-budget-retest-guest-exec-v2'
TREE=Path('/root/work/lanes/gc23-evidence-tools')
REL='port/dreamcast/tools/d367/gc23_evidence/20261024-gc427-recovery-executable-source-v2'
PARENT='bd1c1826ffb878e7264e6d0f454722dd5aa19416'
def git(*args):return subprocess.check_output(['git','-C',str(TREE),*args])
def row(raw):return dict(size=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def encoded(j):return (json.dumps(j,indent=1)+'\n').encode()
def fresh(path,raw):
 with path.open('xb') as f:f.write(raw)
if __name__=='__main__':
 assert git('status','--porcelain')==b''
 assert git('rev-parse','HEAD').decode().strip()==PARENT,'Moved archive HEAD; do not reset'
 assert git('branch','--show-current').decode().strip()=='wip/gc23-evidence-tools-20261024'
 seal=(SRC/'SOURCE-REVIEW-SEAL.json').read_bytes()
 assert row(seal)==dict(size=4112,sha256='533ef84d9edf445047fbc9bac6ebebba8ce93e937787a3360176499eaf2512f4')
 pins=json.loads(seal)['members'];selected={p.name:p.read_bytes() for p in SRC.iterdir() if p.is_file()}
 assert set(selected)==set(pins)|{'SOURCE-REVIEW-SEAL.json','SOURCE-READBACK.json'}
 assert all(not p.is_symlink() and p.is_file() for p in SRC.iterdir())
 for name,pin in pins.items():assert row(selected[name])==pin
 assert not any(n in selected for n in ['CURRENT-BASELINE.json','RECOVERY-BINDING.json','TOOLCHAIN-SEAL.json'])
 dest=TREE/REL;assert not dest.exists();dest.mkdir(parents=True)
 manifest={}
 for name,raw in selected.items():fresh(dest/name,raw);manifest[name]=dict(path=str(SRC/name),**row(raw))
 own=Path(__file__);raw=own.read_bytes();fresh(dest/'archive_source.py',raw);manifest['archive_source.py']=dict(path=str(own),**row(raw))
 fresh(dest/'.gitattributes',b'* -text\n')
 fresh(dest/'SOURCE-MANIFEST.json',encoded(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),parent=PARENT,source_members=manifest,bytes=sum(v['size'] for v in manifest.values()),line_endings='Exact originals; Git text normalization disabled')))
 fresh(dest/'DISCLOSURE.md',b'# Executable GC recovery source review snapshot\n\n79 source/public host controls pass; three actual current media/resource checks remain pending. Six original controller/postslot/entry/owner/judge files are byte-identical to7b512. New recovery context/binder/finalizer is reviewable source and refuses absent real OFF/current baseline. V5 sourcec3dd/seal9377 is the expected actual media producer; OFF programme provenance remains8ce, compared with427 payload. Root has not supplied actual fresh media; no current baseline/final guest seal/grant exists. I001 plan retains3ff/1f6/catalog0/Motion/raw/terminal gaps and original4000/4016 failure. All old2301/4dd/7b512/HOLD contracts remain immutable. No SDK/stage/guest/runtime change, programme/ELF/assets/IP/images/capture data included.\n')
 expected={p.relative_to(TREE).as_posix():p.read_bytes() for p in dest.iterdir()}
 git('add','--',REL)
 assert {p.decode() for p in git('diff','--cached','--name-only','-z').split(b'\0') if p}==set(expected)
 for name,raw in expected.items():assert git('show',':'+name)==raw
 git('commit','-m','Preserve executable GC recovery source and pending actual-media binding')
 commit=git('rev-parse','HEAD').decode().strip()
 for name,raw in expected.items():assert git('show',commit+':'+name)==raw
 with tarfile.open(fileobj=io.BytesIO(git('archive','--format=tar',commit,REL)),mode='r:') as archive:
  exported={m.name:archive.extractfile(m).read() for m in archive.getmembers() if m.isfile()}
 assert exported==expected
 git('push','origin','HEAD:refs/heads/wip/gc23-evidence-tools-20261024')
 remote=git('ls-remote','origin','refs/heads/wip/gc23-evidence-tools-20261024').decode().split()[0];assert remote==commit
 assert git('status','--porcelain')==b''
 receipt=dict(status='EXACT_SOURCE_GIT_OBJECT_ARCHIVE_EXPORT_REMOTE_PASS_NO_ACTUAL_BASELINE_OR_GUEST',commit=commit,remote=remote,parent=PARENT,path=REL,files=len(expected),bytes=sum(map(len,expected.values())),source_review_seal=row(seal),source_manifest=row(expected[REL+'/SOURCE-MANIFEST.json']),normalization='none',SDK=0,stage=0,guest=0,runtime_changes=0)
 fresh(LANE/'kos-budget-retest-guest-exec-v2-ARCHIVE.json',encoded(receipt));print(json.dumps(receipt))
