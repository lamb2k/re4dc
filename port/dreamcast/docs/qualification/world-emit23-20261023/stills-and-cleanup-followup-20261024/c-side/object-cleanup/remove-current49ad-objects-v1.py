"""Remove only frozen inventoried root-owned completed .o/.d rebuildables.
Full preflight and retained programme identities precede every deletion.
"""
from pathlib import Path
import hashlib,json,os,re,time,sys
ROOT=Path('/root/probe/lanes/route');D=Path('/mnt/c/Game Dev/Emulators/codex-lanes/world-emit23')
INV=D/'CURRENT-49AD-OBJECTS-INVENTORY-v1.json';J=D/'CURRENT-49AD-OBJECTS-CLEANUP-v1.jsonl';R=D/'CURRENT-49AD-OBJECTS-CLEANUP-RECEIPT-v1.json'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def verify_keep(inv):
 for u in inv['units']:
  p=Path(u['unit']);assert sha(p/'stack.txt')==u['stack']
  for n,row in u['keep'].items():assert (p/n).stat().st_size==row['size'] and sha(p/n)==row['sha256']
def verify_file(row):
 p=Path(row['path']);assert p.resolve()==p and p.suffix in ['.o','.d']
 assert p.is_relative_to(ROOT) and re.fullmatch(r'out-(?:fpwe23[RLBE]49ad(?:[gcmn]W|gP)|we23[RLBE]49adr[PT])',p.relative_to(ROOT).parts[0])
 assert 'obj'==p.relative_to(ROOT).parts[1]
 assert not any(x in p.name for x in ['native_static','native_actor','coarse_actor','bfc','backface','cache'])
 assert not any(x.is_symlink() for x in [p,*p.parents])
 st=p.stat();assert (st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_nlink)==(row['dev'],row['inode'],row['size'],row['mtime_ns'],1)
 return p
assert sys.argv[1:]==['--execute-owned-rebuildables']
assert not J.exists() and not R.exists(),'Preserve earlier transaction'
i=json.loads(INV.read_text());assert i['source']=='49ad20f9932d638ddb7becf5db6f86b92e0a76a2' and i['read_only'] and len(i['units'])==25
assert i['count']==len(i['files']) and len({x['path'] for x in i['files']})==i['count']
active=[]
for proc in Path('/proc').iterdir():
 if not proc.name.isdigit() or int(proc.name)==os.getpid():continue
 try:args=(proc/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
 except (OSError,ProcessLookupError):continue
 if re.search(r'out-(?:fp)?we23[RLBE]49ad',args):active.append({'pid':proc.name,'command':args})
assert not active,active
verify_keep(i)
for row in i['files']:assert sha(verify_file(row))==row['sha256']
free_before=os.statvfs('/mnt/c').f_bavail*os.statvfs('/mnt/c').f_frsize
removed=[]
with J.open('x') as journal:
 journal.write(json.dumps({'begin':True,'inventory_sha256':sha(INV),'full_hash_preflight':True,'active_matching_processes':active,'free_c_before':free_before})+'\n');journal.flush();os.fsync(journal.fileno())
 for k,row in enumerate(i['files']):
  p=verify_file(row);p.unlink();removed.append(row['path']);journal.write(json.dumps({'removed':row['path'],'sha256':row['sha256'],'bytes':row['size']})+'\n')
  if k%1024==0:journal.flush();os.fsync(journal.fileno())
 journal.flush();os.fsync(journal.fileno())
verify_keep(i)
assert all(not Path(p).exists() for p in removed)
free_after=os.statvfs('/mnt/c').f_bavail*os.statvfs('/mnt/c').f_frsize
receipt={'inventory_sha256':sha(INV),'script_sha256':sha(Path(__file__)),'journal_sha256':sha(J),'removed_files':len(removed),'old_single_link_allocations_bytes':sum(r['allocated'] for r in i['files']),'retained_programme_checks':True,'retained_renderer_actor_cache_objects':True,'source_assets_logs_overlays_elf_untouched':True,'C_free_before':free_before,'C_free_after':free_after,'C_delta_not_attributed_to_cleanup':free_after-free_before,'scope':'Only completed49ad .o/.d rebuildables. No current programme/source/evidence media or global SDK changes; VHD space release may lag.'}
with R.open('x') as f:json.dump(receipt,f,indent=2);f.write('\n')
print(json.dumps(receipt))