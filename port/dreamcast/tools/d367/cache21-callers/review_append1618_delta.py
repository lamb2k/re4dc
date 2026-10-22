#!/usr/bin/env python3
"""Source-only 1618 delta review. No writer import/process/payload resolution."""
import argparse,ast,hashlib,json,pathlib,shutil,subprocess
ROOT=pathlib.Path('/mnt/c/Flycast-Evidence/re4-dreamcast/texture21-benchmark-20261021')
LANE=pathlib.Path('/mnt/c/Game Dev/Emulators/codex-lanes/castle-controls21')
W='0b97fd7afdf5c1811bc8d3530bb6ba7ed1145f27faa027a154fa3c44d6bed4d0';P='6f80df864bea4577b5d40d79cf81e61780a2542a35a018fa9aedbc2d132b6111';C='e5d738e4094c161f7040a1abeeb6a7a504ee7075f9cc6e44394a815b81a6a5a9'
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);a=ap.parse_args();out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=False)
 paths={'writer1618':ROOT/'append1618-writer-adapter-01/source/immutable_append1618_writer.py','writer1600':ROOT/'append1600-writer-adapter-01/source/immutable_append1600_writer.py','plan1618':ROOT/'append1618-writer-adapter-01/writer-plan.json','controller1618':LANE/'owned-windows-1618-pack-job.py','controller1600':LANE/'owned-windows-1600-pack-job.py','doc':LANE/'PACK1618-JOB-CONTROLLER.md'}
 manifest=[];texts={};trees={}
 for key,p in paths.items():
  raw=p.read_bytes();texts[key]=raw.decode();(out/key).write_bytes(raw);manifest.append(dict(role=key,path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),crlf=raw.count(b'\r\n'),lf=raw.count(b'\n')))
  if p.suffix=='.py':trees[key]=ast.parse(texts[key])
 checks=[]
 def ck(name,value):assert value,name;checks.append(dict(name=name,result='PASS',kind='static source or byte identity only'))
 def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
 ck('exact raw source plan controller SHA',sha(paths['writer1618'])==W and sha(paths['plan1618'])==P and sha(paths['controller1618'])==C)
 plan=json.loads(texts['plan1618']);w=texts['writer1618'];c=texts['controller1618']
 ck('family7151 members d43d bytes',plan['expected']['members']==7151 and plan['expected']['bytes']==160159744 and plan['expected']['sha256']=='d43d1c81ba2e70ab0177c6c97867fd39c95d68a114b727601b3eadd14e6aaf08')
 ck('new parent seal0eb5233f',plan['parent_input_seal_sha256']=='0eb5233f21ed050d1cf1dc8aef0a6f8277292d60409122e074b525d4636d43ac')
 ck('two packs plus12MiB fixed cap',2*160159744+12582912==plan['aggregate_cap_bytes']==332902400)
 ck('floor peer once plus new admission',plan['runtime_floor_bytes']+plan['peer_reserved_bytes']==19461570560 and 19461570560+332902400==19794472960)
 ck('new fixed root names',all('append1618-' in x for x in [plan['metadata_root'],*plan['payload_roots']]) and 'PACK_CAP=332902400' in c and 'append1618-materialization-01' in c)
 ck('four exact source dependencies raw bytes',len(plan['source_sha256'])==4 and all(sha(paths['writer1618'].parent/n)==h for n,h in plan['source_sha256'].items()))
 def defs(tree):return {n.name:n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
 def dump(n):return ast.dump(n,include_attributes=False)
 identical=[];wa,wb=defs(trees['writer1600']),defs(trees['writer1618'])
 for name in ['Budget','sha','json_new','sealed','source_stream','inspect_pack','write_one','copy_blocks','allocation','re_hash']:
  ck('unchanged writer helper '+name,dump(wa[name])==dump(wb[name]));identical.append(dict(kind='writer',name=name,start=wb[name].lineno,end=wb[name].end_lineno))
 ca,cb=defs(trees['controller1600']),defs(trees['controller1618'])
 for name in ['native','sha','canonical','within','main']:
  ck('unchanged controller helper '+name,dump(ca[name])==dump(cb[name]));identical.append(dict(kind='controller',name=name,start=cb[name].lineno,end=cb[name].end_lineno))
 na,nb=defs(ca['run']),defs(cb['run'])
 for name in ['checked','fail','terminate','times','live_pin','size_tree','resources','log_reader','hard_guard']:
  ck('unchanged native lifecycle helper '+name,dump(na[name])==dump(nb[name]));identical.append(dict(kind='controller.run',name=name,start=nb[name].lineno,end=nb[name].end_lineno))
 ck('child query accepts only known codes otherwise raises','if error in(1,50,120):return logical' in w and "raise OSError(error,'native allocation query failed closed')" in w)
 ck('child query success charges max round native','return max(logical,low+(high<<32))' in w)
 ck('new Budget default binds new local strict query function',wb['file_charge'].lineno<wb['Budget'].lineno and 'charge=file_charge' in ast.get_source_segment(w,wb['Budget']))
 ck('dontwrite gate precedes all local imports',w.index('if not sys.dont_write_bytecode:')<w.index('from file_charge import'))
 ck('full writer env validation before resolver and known loader',w.index('plan=json.loads(a.plan.read_text());environment(plan)')<w.index('head,index,rows=resolve(plan)')<w.index('spec.loader.exec_module(known)'))
 ck('full env does NOT precede local imports',w.index('from file_charge import')<w.index('def environment(plan):'))
 ck('controller production checks inherited cache before child creation','if not test:require_cache_environment(root)' in c and c.index('def require_cache_environment')<c.index('k.CreateProcessW(str(exe)'))
 ck('effective and explicit env plus fresh exact prefix checked',all(t in c for t in ["os.environ.get('PYTHONDONTWRITEBYTECODE')!='1'",'canonical(raw)!=expected','canonical(effective)!=expected','if expected.exists():']))
 ck('child request inherits checked env without mutation','None,str(cwd),C.byref(startup)' in c and 'os.environ[' not in c)
 ck('new resolve inherits1600 exact resolver and seals','from immutable_append1600_writer import resolve as resolve1600' in w and "sealed(root,APPEND1618_SEAL)" in w and "d['frozen1600']['writer_sha256']" in w)
 ck('old general child fallback helper never imported as Budget charge','from immutable_append1600_writer import resolve as resolve1600' in w and 'charge=file_charge' in w)
 authoritative=pathlib.Path('/root/probe/codex-texture21-benchmark/port/dreamcast/tools/d367/texture21_benchmark/immutable_append1618_writer.py');raw=authoritative.read_bytes();ck('live authoritative writer raw equals frozen C bytes',raw==paths['writer1618'].read_bytes())
 gitraw=subprocess.check_output(['git','-C','/root/probe/codex-texture21-benchmark','show','HEAD:port/dreamcast/tools/d367/texture21_benchmark/immutable_append1618_writer.py']);lfsha=hashlib.sha256(gitraw).hexdigest();ck('raw CRLF versus Git LF explicit',raw.count(b'\r\n')==212 and raw.replace(b'\r\n',b'\n')==gitraw and lfsha!=W)
 receipt=dict(scope='SOURCE_ONLY delta review; no frozen imports/job/materialization',manifest=manifest,checks=checks,unchanged_AST_helpers=identical,git_lf=dict(bytes=len(gitraw),sha256=lfsha,executable_raw_sha256=W,raw_bytes=len(raw)),limits=['Full writer prefix/env validation is after local imports; accepted coupled controller launch prevalidates and inherits correct env. Do not claim standalone full preimport guard.','Child known error fallback is code-restricted but not UNC-path-restricted. Outer retains UNC+code restriction.','51s starts postresolve/cooperative;130s guard begins post pin/assignment. No OS API preemption claim.'])
 (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(dict(result='PASS',static_checks=len(checks),unchanged_helpers=len(identical),fresh_bytes=sum(p.stat().st_size for p in out.iterdir()if p.is_file()))))
if __name__=='__main__':main()