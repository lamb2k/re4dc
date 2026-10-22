#!/usr/bin/env python3
"""One new actual-source v2 consumer close control, no broad suite rerun."""
import argparse,ast,hashlib,json,pathlib,runpy
P=pathlib.Path
p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args();out=P(a.out);out.mkdir(parents=True,exist_ok=False)
tool=P(__file__).with_name('test_pack_stream_independent.py');env=runpy.run_path(str(tool));helper=env['helper'];Guard=env['Guard'];Refusal=env['Refusal'];ns=env['ns'].copy()
v2=P('/root/probe/codex-texture21-benchmark/port/dreamcast/tools/d367/texture21_benchmark/immutable_append1618_buffered_v2_writer.py');raw=v2.read_bytes();node=next(n for n in ast.parse(raw.decode()).body if isinstance(n,ast.FunctionDef)and n.name=='write_one');exec(compile(ast.Module(body=[node],type_ignores=[]),'<actual-v2-write-one>','exec'),ns)
base=out/'tiny-source';base.write_bytes(b'A'*200);row=dict(path=base,source_root=out,source_offset=0,bytes=100,sha256=hashlib.sha256(b'A'*100).hexdigest());opened=[]
def opener(p):f=p.open('rb');opened.append(f);return f
class Fail(Guard):
 def check(self,*args,**kw):
  if args:raise Refusal('downstream guard refusal')
error=None
try:ns['write_one'](out/'pack',helper['coalesce'](helper['source_stream'](b'',b'',[row,row],Fail(),safe_path=ns['safe_path'],opener=opener),chunk=16),1000,'0'*64,lambda p:None,Fail())
except Refusal as e:error=e
assert error is not None and opened and all(f.closed for f in opened)
assert (out/'pack.part').exists() and (out/'pack.part').stat().st_size==0
r=dict(test='actual newv2 write_one closes suspended coalescer on downstream guard failure while exception retained',result='PASS',v2_observed_sha256=hashlib.sha256(raw).hexdigest(),write_one_source_start=node.lineno,write_one_source_end=node.end_lineno,write_one_AST_sha256=hashlib.sha256(ast.dump(node,include_attributes=False).encode()).hexdigest(),closed_before_exception_release=True,partial_bytes=0,helper_sha256=env['sha'](env['HELPER']),scope='One tiny Linux/Python source control; observed v2 snapshot only, not final freeze/job/throughput proof')
(out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))