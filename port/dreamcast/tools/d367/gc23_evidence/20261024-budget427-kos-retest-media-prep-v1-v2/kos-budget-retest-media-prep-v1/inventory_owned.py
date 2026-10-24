"""Full metadata inventory and read-only rebuildability inspection; no deletion."""
from pathlib import Path
import hashlib,json,sys,datetime
HERE=Path(__file__).resolve().parent
assert sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
scope={'__file__':str(HERE/'capacity.py'),'__name__':'read_only_capacity'};exec(compile((HERE/'capacity.py').read_bytes(),str(HERE/'capacity.py'),'exec',dont_inherit=True),scope)
seen={};rows=[]
for name in scope['ROOTS']:
 root=Path(name)
 for p in sorted(root.rglob('*')):
  assert not p.is_symlink()
  if not p.is_file():continue
  s=p.stat();key=(s.st_dev,s.st_ino);first=seen.setdefault(key,str(p))
  rows.append(dict(path=str(p),bytes=s.st_size,dev=s.st_dev,ino=s.st_ino,nlink=s.st_nlink,first_owned_path=first,first_owned_occurrence=first==str(p)))
ext4=[x for x in rows if x['path'].startswith('/root/probe/') and x['first_owned_occurrence']]
largest=sorted(ext4,key=lambda x:(-x['bytes'],x['path']))[:40]
for x in largest:
 with Path(x['path']).open('rb') as f:x['actual_readonly_sha256']=hashlib.file_digest(f,'sha256').hexdigest()
# Distinguish copies from hardlinks. A hardlink's source bytes are not a safe
# removal target merely because an owned pathname was built during staging.
work_non_cdroot=[x for x in rows if x['path'].startswith('/root/probe/') and '/cdroot/' not in x['path']]
track_candidates=[x for x in work_non_cdroot if x['bytes']>=100*1024**2]
report=dict(status='READ_ONLY_COMPLETE_OWNED_INODE_INVENTORY_NO_DELETE',timestamp_UTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),roots=scope['ROOTS'],members=rows,unique_bytes=sum(x['bytes'] for x in rows if x['first_owned_occurrence']),largest_unique_ext4=largest,work_files_outside_cdroot=work_non_cdroot,large_intermediate_work_track_candidates=track_candidates,observed='No large intermediate packed track in either ext4 work tree. Bulk ext4 bytes are asset hardlinks under cdroot, not standalone duplicate ISO intermediates. Four large NTFS track03.iso files are final preserved discs; no deletion recommendation. Programme copies/blank fixture files and small low-density/t1root build inputs are regenerable staging products but are insufficient to remove the existing overage, much less fund a new ON final track. Root must decide any further owned-link cleanup; source/private asset originals, final discs, captures and failures remain protected.',deletion=0,SDK=0,stage=0,guest=0)
with (HERE/'OWNED-FILE-INVENTORY.json').open('x') as f:json.dump(report,f,indent=1);f.write('\n')
p=HERE/'OWNED-FILE-INVENTORY.json';print(json.dumps(dict(path=str(p),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),members=len(rows),unique_bytes=report['unique_bytes'],large_work_intermediates=len(track_candidates),largest_ext4=largest[:6])))
