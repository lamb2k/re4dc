"""One metadata mapping and fresh preprocessor proof, never compile/link/stage."""
from pathlib import Path
import argparse,fcntl,hashlib,json,os,signal,subprocess,time
P=Path(__file__).resolve().parent
R=Path('/root/probe/lanes/actor-visibility23-eligibility-witness-integration');O=R/'on2';T=Path('/root/probe/codex-actor-visibility23-eligibility-witness-integration');G=T/'port/dreamcast/game/obj'
HEAD='f2405bb06ebaff6e2a7681479d5308ec5d3b988a';LINK='5c1b860513958c1df82889c316731ff3d9ab6b246cdd89a847831012b9e20a43'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def info(p):return dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p))
def verify(row):assert Path(row['path']).stat().st_size==row['bytes']and sha(row['path'])==row['sha256'],row['path']
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--release-priority-clear',action='store_true',required=True);ap.add_argument('--execute',action='store_true');a=ap.parse_args()
 locks=[];proc=None
 try:
  for name in ('/root/probe/d367-build.lock','/root/probe/d367-build2.lock'):
   f=open(name,'a')
   try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(f);break
   except BlockingIOError:f.close()
  else:raise RuntimeError('NO_SHARED_SLOT; preserve and return, no waiting')
  f=open(R/'tree.lock','a');fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(f)
  assert subprocess.check_output(['git','-C',str(T),'rev-parse','HEAD'],text=True).strip()==HEAD
  assert subprocess.check_output(['git','-C',str(T),'status','--porcelain'],text=True)=='?? port/dreamcast/game/obj\n'
  assert G.is_symlink()and G.resolve()==O/'link-scratch'
  assert sha(O/'LINK-RECEIPT.json')==LINK
  old_result=info(O/'RUN-RESULT.json');assert json.loads((O/'RUN-RESULT.json').read_bytes())['exit_code']==1
  receipt=json.loads((O/'LINK-RECEIPT.json').read_bytes());assert receipt['source_head']==HEAD and len(receipt['overlays'])==14
  immutable=[receipt[k]for k in ('main','raw','scrambled','resolved','objects_manifest','source_manifest','modules_roster')]+receipt['overlays']+receipt['kos']
  for row in immutable:verify(row)
  roster=json.loads(Path(receipt['modules_roster']['path']).read_bytes());assert len(roster)==14
  for row in roster:
   f=O/'modules'/row['elf'];assert sha(f)==row['elf_sha256'];immutable.append(info(f))
  objects=json.loads((O/'OBJECTS.json').read_bytes());entries=[];copied=0;retained=0
  for row in objects:
   verify(row);q=Path(row['path'])
   if q.is_relative_to(G):
    rel=q.relative_to(G);physical=O/'link-scratch'/rel;assert physical.resolve().is_relative_to(O/'link-scratch');verify(dict(path=str(physical),bytes=row['bytes'],sha256=row['sha256']))
    duplicate=O/'link-inputs'/rel
    if duplicate.is_file():target=duplicate;kind='ACTUAL_COPIED_FILE';copied+=1
    else:target=physical;kind='ACTUAL_RETAINED_OWNED_LINK_SCRATCH';retained+=1
    verify(dict(path=str(target),bytes=row['bytes'],sha256=row['sha256']))
    entries.append(dict(original_path=row['path'],original_bytes=row['bytes'],original_sha256=row['sha256'],status='RETAINED_REHASHABLE',retention_kind=kind,retained_path=str(target),retained_bytes=target.stat().st_size,retained_sha256=sha(target)))
   else:assert q.is_relative_to(O/'obj'),str(q)
  assert len(entries)==73 and copied==12 and retained==61,(len(entries),copied,retained)
  mapping=O/'LINK-INPUT-MAPPING.json';proof=O/'source-compile-r2';log=R/'on2-proof-r1.log';result=O/'PROOF-REPAIR-R1.json'
  assert not mapping.exists()and not proof.exists()and not log.exists()and not result.exists(), 'Fresh one-attempt proof only'
  if not a.execute:print(json.dumps(dict(status='READ_ONLY_READY',linked_programme_unchanged=True,mapping_entries=73,copied_files=12,owned_retained_files=61,preprocess=False)));return
  mapping.write_text(json.dumps(dict(source=HEAD,arm='on',output_label='on2',original_manifest=info(O/'OBJECTS.json'),original_link_receipt_sha256=LINK,live_standard_object_root=str(O/'obj'),entries=entries,actual_copies=copied,actual_owned_retained=retained,objects_copied_or_modified_by_repair=False),indent=2)+'\n')
  env=dict(os.environ,D367_SLOT_HELD='1',ACTOR23_ARM_OUTPUT='on2',ACTOR23_PROOF=str(P),TMPDIR=str(O/'temp'))
  with log.open('xb')as output:
   proc=subprocess.Popen(['bash',str(P/'proof.sh')],stdout=output,stderr=subprocess.STDOUT,env=env,start_new_session=True)
   rc=proc.wait();assert rc==0,'Fresh proof failed; preserve all outputs'
  try:os.killpg(proc.pid,0)
  except ProcessLookupError:pass
  else:raise RuntimeError('Proof parent exited with remaining processes')
  for row in immutable+[old_result]:verify(row)
  for row in objects:verify(row)
  compile=proof/'compile.json';assert compile.is_file()
  result.write_text(json.dumps(dict(status='POSTLINK_PROOF_REPAIRED_PENDING_MAIN_REVIEW',source=HEAD,original_run_result=old_result,original_run_result_unchanged=True,programme_objects_and_all14_unchanged=True,mapping=info(mapping),compile_receipt=info(compile),proof_log=info(log),compiler_or_linker_objects_generated=False,target_preprocessing=True,runtime_admitted=False,stage=False,guest=False),indent=2)+'\n')
  print(json.dumps(dict(status='POSTLINK_PROOF_REPAIRED_PENDING_MAIN_REVIEW',compile_receipt=info(compile),result=info(result))))
 finally:
  if proc:
   try:os.killpg(proc.pid,signal.SIGTERM)
   except ProcessLookupError:pass
   try:proc.wait(timeout=10)
   except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
   while True:
    try:os.killpg(proc.pid,0);os.killpg(proc.pid,signal.SIGKILL)
    except ProcessLookupError:break
    time.sleep(.1)
  for f in reversed(locks):f.close()
if __name__=='__main__':main()
