#!/usr/bin/env python3
"""Native read-only concrete1618 JSON/hash/schema review. Never imports writer/controller."""
import argparse,hashlib,json,pathlib
P=pathlib.Path
W='0b97fd7afdf5c1811bc8d3530bb6ba7ed1145f27faa027a154fa3c44d6bed4d0';C='e5d738e4094c161f7040a1abeeb6a7a504ee7075f9cc6e44394a815b81a6a5a9'
PLAN='6f80df864bea4577b5d40d79cf81e61780a2542a35a018fa9aedbc2d132b6111';OUTER='0dd8021ecced51d49e827061952518cac76540a29bec0f18efcc6980efb4b119';OA='39904b018030f9c360b65f315d4fedb2621c110fab3e0f4bf59fa35f09786bff'
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root-lane',required=True);ap.add_argument('--writer-plan',required=True);ap.add_argument('--out',required=True);a=ap.parse_args();lane=P(a.root_lane);out=P(a.out);out.mkdir(parents=True,exist_ok=False)
 def sha(p):return hashlib.sha256(P(p).read_bytes()).hexdigest()
 files={key:lane/('APPEND1618-'+name+'.json')for key,name in [('child','CHILD-ALLOCATION'),('outer','OUTER-PLAN'),('allocation','OUTER-ALLOCATION'),('preparation','ROOT-PREPARATION')]};docs={k:json.loads(p.read_text())for k,p in files.items()};wp=P(a.writer_plan);w=json.loads(wp.read_text());child=docs['child'];o=docs['outer'];allocation=docs['allocation'];prep=docs['preparation'];checks=[]
 def ck(name,value):assert value,name;checks.append(dict(name=name,result='PASS',kind='read-only JSON/source SHA/path check, no operational qualification'))
 ck('root outer plan allocation exact SHA',sha(files['outer'])==OUTER and sha(files['allocation'])==OA and sha(wp)==PLAN)
 ck('child allocation raw writer/controller/plan',child['allocated'] is True and child['writer_source_sha256']==W and child['controller_sha256']==C and child['writer_plan_sha256']==PLAN)
 ck('child cap baseline peer inner',child['aggregate_cap_bytes']==332902400 and child['runtime_floor_bytes']==19394461696 and child['peer_reserved_bytes']==67108864 and child['inner_seconds']==51 and child['compression_credits'] is False)
 ck('same exact new3roots across all plans',all(d['approved_output_root']==w['metadata_root'] and d['approved_payload_roots']==w['payload_roots']for d in [child,o,allocation]))
 ck('outer allocation SHA links child and outerplan',allocation['allocated'] is True and allocation['plan_sha256']==OUTER and allocation['child_allocation_sha256']==sha(files['child'])==o['child_allocation_sha256'])
 ck('outer allocation cap floor source seal',allocation['max_output_bytes']==332902400 and allocation['runtime_floor_bytes']==19461570560 and allocation['writer_source_sha256']==W and allocation['controller_sha256']==C and allocation['parent_input_seal_sha256']==w['parent_input_seal_sha256'])
 ck('outer frozen130 cap8MiB log peer',o['absolute_seconds']==130 and o['max_output_bytes']==332902400 and o['peer_reserved_bytes']==67108864 and o['log_limit_bytes']==8388608)
 argv=o['argv'];ck('native interpreter direct script no shell',P(argv[0]).name=='python.exe' and P(argv[1]).name=='immutable_append1618_writer.py' and len(argv)==11 and argv[-1]=='--execute')
 for flag,expected in [('--plan',str(wp)),('--plan-sha256',PLAN),('--allocation-receipt',str(files['child'])),('--allocation-sha256',sha(files['child']))]:ck('exact once child argv '+flag,argv.count(flag)==1 and argv[argv.index(flag)+1]==expected)
 ck('actual raw writer from argv pinned',sha(argv[1])==W and o['input_sha256'][argv[1]]==W)
 input_proofs=[]
 for p,h in o['input_sha256'].items():actual=sha(p);ck('pinned input '+P(p).name,actual==h);input_proofs.append(dict(path=p,sha256=actual,bytes=P(p).stat().st_size))
 ck('child file explicitly pinned',o['child_allocation_path']==str(files['child']) and o['input_sha256'][str(files['child'])]==sha(files['child']))
 ck('controller native absolute cwd',P(o['cwd']).resolve()==P(r'C:\Game Dev\Emulators'))
 roots=[P(w['metadata_root']),*[P(p)for p in w['payload_roots']]]
 ck('root metadata prepared empty',roots[0].is_dir() and not list(roots[0].iterdir()))
 ck('both payload roots absent canonical',all(not p.exists() and p.resolve()==p for p in roots[1:]))
 ck('all3roots canonical',all(p.resolve()==p for p in roots))
 ck('explicit new roots and no duplicated outputs',all(str(p)in o['new_outputs']for p in roots[1:]) and len(o['new_outputs'])==len(set(o['new_outputs'])))
 ck('outputs within exact roots absent',all(any(P(p).is_relative_to(r)for r in roots)and not P(p).exists() for p in o['new_outputs']))
 ck('controller receiptlog absent under metadata',all(P(o[k]).is_relative_to(roots[0])and P(o[k]).parent.is_dir()and not P(o[k]).exists()for k in ['receipt','log']))
 expected=roots[0]/'pycache';ck('prepared exact BOTH env schema matches frozen plan',prep['environment']==w['required_environment']=={'PYTHONDONTWRITEBYTECODE':'1','PYTHONPYCACHEPREFIX':str(expected)} and not expected.exists() and expected.resolve()==expected)
 ck('root prep exact outer hashchain',prep['plan_sha256']==OUTER and prep['allocation_sha256']==OA and prep['controller_sha256']==C and prep['prepared_only'] is True)
 ck('new full admission bytes peer once',19461570560+332902400==19794472960)
 proofs=[]
 for key,p in files.items():raw=p.read_bytes();(out/p.name).write_bytes(raw);proofs.append(dict(role=key,path=str(p),sha256=sha(p),bytes=len(raw)))
 r=dict(scope='read-only concrete schema/hash/current-empty-path proof only; no executable imports/job/payload allocation by reviewer',files=proofs,checks=checks,inputs=input_proofs,required_root_remaining=['Set BOTH inherited environment values before controller Python startup, preserve absent prefix, use-B for root controller startup. ROOT-PREPARATION is recorded intent, not live environment proof.','Run exact controller default validation then fresh resource floor+aggregate19794472960/global64MiB peer admission before execute.','Retained process/job/final resource proof and actual child/fullpack/mirror readback remain future gates.'])
 (out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(result='PASS',checks=len(checks),input_SHA_count=len(input_proofs),fresh_bytes=sum(p.stat().st_size for p in out.iterdir()if p.is_file()))))
if __name__=='__main__':main()