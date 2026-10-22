from pathlib import Path
import json,hashlib,shutil,sys,datetime,collections
R=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/castle18-20261018/Test21');T=Path('/root/probe/codex-castle18');L=Path('/mnt/c/Game Dev/Emulators/codex-lanes/castle18')
D=R/'recovered-j-content-20261021';O=Path('/root/probe/castle21-recovered-j-content-20261021');assert not D.exists()and not O.exists()
required_free=18*1024**3+4*1024**3
assert shutil.disk_usage('/mnt/c').free>=required_free,('C staging preflight',shutil.disk_usage('/mnt/c').free,required_free)
assert shutil.disk_usage('/root/probe').free>=4*1024**3
inv=json.loads((R/'J-exact-recovery-input-inventory.json').read_text());want=json.loads((R/'skin-player-j-base/base-manifest.json').read_text());assert len(want)==6765
fixture_names={'dc/warp.txt','dc/padscript.txt','dc/w11.txt'}
assert set(inv['matched_sources'])|set(inv['secondary_image_matches'])|fixture_names==set(want)
assert hashlib.sha256((R/'tools/fp_master_ram.sh').read_bytes()).hexdigest()=='8f9d715d4e80aa7a66fe3f0f803189ec4a9f4a7a623b654f94a9a3eb6c3e4382'
D.mkdir();O.mkdir();tree=O/'tree';tree.mkdir();sys.path.insert(0,str(T/'port/dreamcast/tools/d367/fullplay'));import fp_iso
secondary={}
for k in sorted(want):
 if k in fixture_names:continue
 assert shutil.disk_usage('/mnt/c').free>=18*1024**3+2*1024**3,'Live C construction guard'
 dst=tree/k;dst.parent.mkdir(parents=True,exist_ok=True)
 if k in inv['matched_sources']:shutil.copyfile(inv['matched_sources'][k],dst)
 else:
  row=inv['secondary_image_matches'][k];tr=secondary.setdefault(row['image'],fp_iso.Track(row['image'],45000));dst.write_bytes(tr.read_bytes(row['extent'],row['size']))
 assert dst.stat().st_size==want[k]['size'] and hashlib.file_digest(dst.open('rb'),'sha256').hexdigest()==want[k]['sha256'],k
for k in fixture_names:assert hashlib.sha256(bytes(want[k]['size'])).hexdigest()==want[k]['sha256']
manifest={k:v for k,v in want.items()if k not in fixture_names};(D/'tree-manifest.json').write_text(json.dumps(manifest,sort_keys=True,indent=0)+'\n')
shutil.copyfile(R/'disc1-IP.BIN',D/'IP.BIN');shutil.copyfile(R/'J-exact-recovery-input-inventory.json',D/'input-inventory.json')
s=(R/'tools/fp_master_ram.sh').read_text();old='WORK=$(mktemp -d /dev/shm/castle21-master.XXXXXX)';assert s.count(old)==1;s=s.replace(old,'WORK=$(mktemp -d /root/probe/castle21-recovered-j-content-20261021/master-work.XXXXXX)');(D/'fp_master_recovered.sh').write_text(s)
receipt={'scope':'New recovered-J-content cold-boot lineage only. Exact old6765 content hashes; original ISO metadata lost. Old J snapshots and VMU untouched; no old-state retarget allowed.','original_iso_sha256':'87ba0ee4f54b289a1c227328e58577e57f3d5d72df9c22f4e4de33c1fe6e016b','original_iso_bytes':1018789888,'content_files':len(want),'tree_files':len(manifest),'zero_fixture_files':{k:want[k]for k in sorted(fixture_names)},'source_inventory_sha256':hashlib.sha256((D/'input-inventory.json').read_bytes()).hexdigest(),'original_manifest_sha256':hashlib.sha256((R/'skin-player-j-base/base-manifest.json').read_bytes()).hexdigest(),'IP_sha256':hashlib.sha256((D/'IP.BIN').read_bytes()).hexdigest(),'private_helper_sha256':hashlib.sha256((D/'fp_master_recovered.sh').read_bytes()).hexdigest(),'helper_only_change':'Temporary work location uses owned persistent ext4 on same filesystem as reconstructed tree; genisoimage arguments and fixture redirections unchanged.','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'C_free_after_tree':shutil.disk_usage('/mnt/c').free,'tree':str(tree),'old_image_resumed':False}
(D/'reconstruction-input-proof.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))