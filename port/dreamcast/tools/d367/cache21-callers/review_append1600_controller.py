#!/usr/bin/env python3
"""Read-only frozen1600 writer/controller binding and static-contract review."""
import argparse,ast,hashlib,json,pathlib
WRITER='53015865a712cc061cbb29206d316135a3e0d1f609788083b070b06440570b1a'
PLAN='a41346d1264771e2c0e59c6f08b9dba11bd93a10732d4dd01fe440ec7995749d'
CONTROL='dbfd602aef443ce6fc150565e4c98b098e6d3a942698a00dc1a0aba3906e9782'
def main():
 p=argparse.ArgumentParser();p.add_argument('--adapter',required=True);p.add_argument('--controller',required=True);p.add_argument('--out',required=True);a=p.parse_args();root=pathlib.Path(a.adapter);controller=pathlib.Path(a.controller);out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=False)
 def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
 paths=[root/'writer-plan.json',root/'source/immutable_append1600_writer.py',root/'source/file_charge.py',root/'source/mipmap_pair_plan.py',controller,controller.with_name('PACK1600-JOB-CONTROLLER.md')]
 assert sha(paths[0])==PLAN and sha(paths[1])==WRITER and sha(controller)==CONTROL
 plan=json.loads(paths[0].read_text());w=paths[1].read_text();c=controller.read_text();f=paths[2].read_text()
 manifest=[dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size)for p in paths];objects=[]
 for path in [paths[1],paths[2],controller]:
  text=path.read_text();lines=text.splitlines();tree=ast.parse(text)
  for n in ast.walk(tree):
   if isinstance(n,(ast.FunctionDef,ast.ClassDef)):
    objects.append(dict(path=str(path),name=n.name,start=n.lineno,end=n.end_lineno,sha256=hashlib.sha256('\n'.join(lines[n.lineno-1:n.end_lineno]).encode()).hexdigest()))
 checks=[]
 def ck(name,yes):assert yes,name;checks.append(dict(name=name,result='PASS',kind='static source condition only'))
 ck('frozen exact writer plan source controller binding',plan['controller_sha256']==CONTROL and plan['source_sha256']['immutable_append1600_writer.py']==WRITER)
 ck('expected7133 d7fed160122880 bytes',plan['expected']['members']==7133 and plan['expected']['bytes']==160122880 and plan['expected']['sha256']=='d7fed6373143961f232eb99df952afefd301010529ed8e62149a2023d0244b6e')
 ck('two logical packs plus12MiB aggregate',2*160122880+12*1024**2==plan['aggregate_cap_bytes']==332828672)
 ck('peer added exactly once to base floor',plan['runtime_floor_bytes']+plan['peer_reserved_bytes']==19461570560)
 ck('inner51 outer130 frozen',plan['inner_seconds']==51 and plan['outer_seconds']==130)
 ck('all three writer dependencies pinned',set(plan['source_sha256'])=={'immutable_append1600_writer.py','file_charge.py','mipmap_pair_plan.py'} and all(sha(root/'source'/n)==h for n,h in plan['source_sha256'].items()))
 ck('exact two payload roots distinct from metadata',len(set(plan['payload_roots']+[plan['metadata_root']]))==3)
 ck('exclusive partial creation','os.O_EXCL' in w and 'target.exists()or target.is_symlink()' in w)
 ck('exclusive publication Windows no replace flag','MoveFileExW(str(source),str(target),8)' in f)
 ck('child preserves partial on failures','preserve partial' in w and 'except BaseException as exc:' in w and "json_new(meta/'child-result.json',result)" in w)
 ck('writer full hash and allmember readback before publication',w.index('proof=readback(partial)')<w.index('publish_no_replace(partial,target)') and 'member readback SHA differs' in w and 'full expected SHA differs' in w)
 ck('explicit mirror byte comparison',"if left!=right:raise ValueError('mirror byte comparison differs')" in w)
 ck('native suspended assigned membership before resume',c.index('k.CreateProcessW(str(exe)')<c.index('k.AssignProcessToJobObject(job,pi.hProcess)')<c.index('k.IsProcessInJob(pi.hProcess,job')<c.index('k.ResumeThread(pi.hThread)'))
 ck('privatejob killclose and singleprocess limit','LimitFlags=0x2000|0x8' in c and 'ActiveProcessLimit=1' in c)
 ck('independent hardstop captures job and130-minus-margin','owned_job=job' in c and 'deadline-.2' in c and 'k.TerminateJobObject(owned_job,124)' in c)
 ck('retained identity duration and exit code','actual_process_seconds=duration' in c and "created!=pin['start_filetime']" in c and "code.value==259" in c)
 ck('wholejob empty before handles close',c.index("result['whole_job_empty']=job_empty")<c.index("result['handles_closed_after_empty']=True"))
 ck('final output floor and reserve checked','Post-exit runtime floor/output cap/final receipt reserve' in c)
 ck('outer known UNC errors only','error in (1,50,120)' in c and 'else:raise C.WinError(error)' in c)
 ck('inner charges roundedlogical without compression credits','return max(logical,low+(high.value<<32))' in w)
 ck('root allocation before child creates payload dirs',w.index('root_a=allocation(')<w.index('for root in payload:root.mkdir();'))
 ck('child deadline starts after composition resolution',w.index('head,index,rows=resolve(plan)')<w.index('guard=Budget(payload+[meta],CAP,FLOOR+PEER,51)'))
 ck('child imports permit cache writes unless environment fixed','sys.dont_write_bytecode' not in w and 'from file_charge import' in w and 'spec.loader.exec_module(known)' in w and 'None,str(cwd),C.byref(startup)' in c)
 ck('inner native allocation error fallback is broader than outer','if low==0xffffffff and ctypes.get_last_error():return logical' in w)
 receipt=dict(scope='SOURCE_ONLY no pack allocation/write/job execution',manifest=manifest,objects=objects,checks=checks,issues=[dict(id='PYCACHE',severity='execution prerequisite',finding='Unpinned existing pyc may be read; absent/stale pyc may be written outside three roots. Require inherited PYTHONDONTWRITEBYTECODE=1 plus canonical fresh absent PYTHONPYCACHEPREFIX under metadata, root-recorded and read back before launch.'),dict(id='INNER-QUERY-FALLBACK',severity='qualified limitation',finding='Child falls back to rounded logical on any native query error; outer restricts known UNC errors1/50/120 and independently fails closed. Do not describe child query as identical to outer.'),dict(id='DEADLINE-SCOPE',severity='qualified limitation',finding='51s cooperative begins after resolve/import; outer130 covers process. Hard guard thread starts only after suspended identity and job assignment; no API preemption claim for stalled creation/pinning/assignment.')])
 (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(dict(result='PASS',static_checks=len(checks),objects=len(objects),source_files=len(paths),fresh_bytes=(out/'receipt.json').stat().st_size)))
if __name__=='__main__':main()