"""Read-only current-candidate DATA/IP and exact QA media plan. Never stages."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,os,resource,time
HERE=Path(__file__).resolve().parent
QA=Path('/dev/shm/gc-motion24-qa-memory-v2-dbqczoc8')
CAND=Path('/mnt/c/Game Dev/Emulators/RE4DC-RR/cand-fb254e82')
FIXTURE=Path('/root/work/lanes/dedup-offline23-main/stage-on/pkgtree')
TOOLS=QA/'off/source/port/dreamcast/tools/d367'
FINAL=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/gc-motion24-20261024/qa-memory-media-aab-v1')
WORK=Path('/root/probe/gc-motion24-qa-media-v1')

def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def row(p):return dict(size=Path(p).stat().st_size,sha256=sha(p))
def fresh(p,v):
 with Path(p).open('x') as f:json.dump(v,f,indent=2);f.write('\n')
def load():
 spec=importlib.util.spec_from_file_location('official_fp_iso',TOOLS/'fullplay/fp_iso.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def stream_manifest(track,iso):
 tr=iso.Track(track,45000);got={};extents={}
 try:
  for name,extent,size in iso.files(tr):
   key=name.lstrip('/');assert key not in got and not Path(key).is_absolute() and '..' not in Path(key).parts,key
   h=hashlib.sha256();remain=size;lba=extent
   while remain:
    n=min(remain,1<<20);blob=tr.read_bytes(lba,n);assert len(blob)==n;h.update(blob);remain-=n;lba+=n//2048
   got[key]=dict(size=size,sha256=h.hexdigest());extents[key]=dict(lba=extent,size=size)
  ip=tr.read(45000,16)
 finally:tr.f.close()
 return got,extents,ip

def programme_manifest(arm,original,receipt):
 m=dict(original);m['1ST_READ.BIN']=dict(size=receipt['arms'][arm]['files']['program.bin']['bytes'],sha256=receipt['arms'][arm]['files']['program.bin']['sha256'])
 for name,meta in receipt['arms'][arm]['files'].items():
  if name.endswith('.ovl'):m['dc/'+name]=dict(size=meta['bytes'],sha256=meta['sha256'])
 for name in ('warp','padscript','w11'):m['dc/'+name+'.txt']=dict(size=8192,sha256=hashlib.sha256(bytes(8192)).hexdigest())
 return m

def main():
 resource.setrlimit(resource.RLIMIT_AS,(268435456,268435456));start=time.monotonic()
 assert not (HERE/'MEDIA-PLAN.json').exists() and not FINAL.exists() and not WORK.exists()
 qa=json.loads((QA/'qa-receipt.json').read_text());check=json.loads((HERE/'QA-READBACK.json').read_text());assert qa['complete'] is True and check['QA_receipt_sha256']==sha(QA/'qa-receipt.json')
 identity=json.loads((CAND/'IDENTITY.json').read_text());assert identity['source']=='fb254e82ee6f9a3d9e34d53d1d442348a46b9cf2'
 iso=load();manifest,extents,ip=stream_manifest(CAND/'gdemu/track03.bin',iso)
 assert manifest['1ST_READ.BIN']['sha256']==identity['programme']['raw_main']
 for name,meta in identity['programme']['overlays'].items():assert manifest['dc/'+name]==meta
 assert len([n for n in manifest if n.startswith('dc/') and n.endswith('.ovl')])==14
 assert not any('dc/'+n+'.txt' in manifest for n in ('warp','padscript','w11'))
 allowed={'1ST_READ.BIN'}|{'dc/'+n for n in qa['arms']['off']['files'] if n.endswith('.ovl')}|{'dc/warp.txt','dc/padscript.txt','dc/w11.txt'};assert len(allowed)==18
 # Read-only fixture can provide common assets ONLY after exact current-disc
 # comparison. Ignore its known extra alternate files; never copy them.
 fixture=[]
 for key,pin in manifest.items():
  if key in allowed:continue
  path=FIXTURE/key;assert path.is_file() and not path.is_symlink() and row(path)==pin,key
  fixture.append(key)
 fresh(HERE/'CURRENT-CANDIDATE-MANIFEST.json',manifest);fresh(HERE/'CURRENT-CANDIDATE-EXTENTS.json',extents)
 with (HERE/'SOURCE-IP.BIN').open('xb') as f:f.write(ip)
 expected={}
 for arm in ('off','on'):
  m=programme_manifest(arm,manifest,qa);delta={k for k in set(m)|set(manifest) if m.get(k)!=manifest.get(k)};assert delta==allowed,delta
  fresh(HERE/(arm.upper()+'-EXPECTED-MANIFEST.json'),m);expected[arm]=dict(path=str(HERE/(arm.upper()+'-EXPECTED-MANIFEST.json')),identity=row(HERE/(arm.upper()+'-EXPECTED-MANIFEST.json')))
 # All cross-arm differences must be the15 fresh programmes, never fixtures/assets.
 off=programme_manifest('off',manifest,qa);on=programme_manifest('on',manifest,qa);cross={k for k in off if off[k]!=on[k]};assert cross==allowed-{'dc/warp.txt','dc/padscript.txt','dc/w11.txt'}
 tracks={p.name:row(p) for p in (CAND/'gdemu').iterdir() if p.is_file()}
 obj=dict(status='PREPARED_NOT_RUN_PROFILE_PIN_CLOSURE_PENDING_ROOT_REVIEW',source=qa['source'],QA_root=str(QA),QA_receipt=row(QA/'qa-receipt.json'),QA_readback=row(HERE/'QA-READBACK.json'),candidate=str(CAND),candidate_identity=row(CAND/'IDENTITY.json'),candidate_tracks=tracks,sourceIP=row(HERE/'SOURCE-IP.BIN'),original_manifest=row(HERE/'CURRENT-CANDIDATE-MANIFEST.json'),assets=dict(files=len(fixture),logical_bytes=sum(manifest[n]['size'] for n in fixture),read_only_fixture=str(FIXTURE),fixture_extra_files_excluded=True,tex_pak=manifest['dc/tex.pak']),allowed_differences=sorted(allowed),expected_manifests=expected,cross_arm_differences=sorted(cross),base_paths={a:str(FINAL/('base-'+a)) for a in ('off','on')},work_paths={a:str(WORK/a) for a in ('off','on')},capacity=dict(owned_cap_bytes=4*1024**3,C_admission_bytes=26*1024**3,C_floor_bytes=24*1024**3,absolute_C_floor_bytes=20*1024**3,stage_ext4=0,cache='NONE; fresh own outputs only',PRUNE_AUTO=0,logical_estimate_bytes=2*sum(x['size'] for x in off.values())+2*sum(x['size'] for x in manifest.values())+64*1024**2,model='Conservative counts two linked roots and two ISO bases; no shared cache; actual cap monitored before/between phases'),fixtures=dict(warp_lba=400,pad_lba=420,w11_lba=440,fixture_bytes=8192,track1_sectors=606,track2_sectors=302,track3_lba=45000),official_tools={n:row(TOOLS/n) for n in ('fullplay/fp_iso.py','fullplay/fp_master.sh','fullplay/fp_run.py','trace_lock.sh')},genisoimage=row('/usr/bin/genisoimage'),helper=row(__file__),no_stage=True,no_SDK=True,no_guest=True,root_grant_required=True,seconds=time.monotonic()-start)
 assert obj['capacity']['logical_estimate_bytes']<obj['capacity']['owned_cap_bytes']
 fresh(HERE/'MEDIA-PLAN.json',obj);print(json.dumps(dict(files=len(manifest),assets=len(fixture),tex_pak=manifest['dc/tex.pak'],allowed=len(allowed),logical_estimate=obj['capacity']['logical_estimate_bytes'],plan_sha256=sha(HERE/'MEDIA-PLAN.json'))))
if __name__=='__main__':main()
