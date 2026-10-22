#!/usr/bin/env python3
"""Tiny independent actual-source stream/consumer gap controls; no pack job."""
import argparse,ast,contextlib,hashlib,json,os,pathlib,stat,struct,unittest,zlib
P=pathlib.Path
HELPER=P('/mnt/c/Game Dev/Emulators/codex-lanes/cache21/root_pack_stream21.py')
FROZEN=P('/mnt/c/Flycast-Evidence/re4-dreamcast/texture21-benchmark-20261021/append1618-writer-adapter-01/source/immutable_append1618_writer.py')
CHARGE=FROZEN.with_name('file_charge.py')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(HELPER)=='3e6c20648b641421c2dce8ed7948a9a550483da2b463cf19ab0b7a9deaccbbfc'
assert sha(FROZEN)=='0b97fd7afdf5c1811bc8d3530bb6ba7ed1145f27faa027a154fa3c44d6bed4d0'
helper={};exec(compile(HELPER.read_text(),str(HELPER),'exec'),helper)
ns=dict(Path=P,os=os,stat=stat,WOF=0x80000017,hashlib=hashlib,zlib=zlib,struct=struct,CHUNK=1048576)
charge_node=next(n for n in ast.parse(CHARGE.read_text()).body if isinstance(n,ast.FunctionDef)and n.name=='safe_path')
exec(compile(ast.Module(body=[charge_node],type_ignores=[]),'<actual-safe-path>','exec'),ns)
for name in ['source_stream','write_one']:
 node=next(n for n in ast.parse(FROZEN.read_text()).body if isinstance(n,ast.FunctionDef)and n.name==name)
 exec(compile(ast.Module(body=[node],type_ignores=[]),'<actual-v1-'+name+'>','exec'),ns)
class Refusal(RuntimeError):pass
class Guard:
 def claim(self,p):return p
 def check(self,*args,**kwargs):pass
 def commit(self,*args):pass
 def published(self,*args):raise AssertionError('publication forbidden in failure control')
class Tests(unittest.TestCase):
 def setUp(self):
  self.root=OUT/self._testMethodName;self.root.mkdir();self.opened=[];self.validations=[];self.peak=0
  self.base=self.root/'base.bin';self.base.write_bytes(bytes(range(256))*2)
  data=bytearray(144)+bytearray(range(64));data[:8]=b'RE4DCTX\0';struct.pack_into('<I',data,36,zlib.crc32(data[48:]));self.asset=self.root/'asset.bin';self.asset.write_bytes(data)
  self.rows=[self.row(self.base,100,180),self.row(self.asset,0,len(data),True),self.row(self.base,0,211)]
 def row(self,p,off,n,descriptor=False):
  b=p.read_bytes()[off:off+n];r=dict(path=p,source_root=self.root,source_offset=off,bytes=n,sha256=hashlib.sha256(b).hexdigest())
  if descriptor:r.update(descriptor_hex=b[48:144].hex(),body_crc32=struct.unpack_from('<I',b,36)[0])
  return r
 def safe(self,p,r):self.validations.append(p);return ns['safe_path'](p,r)
 def opener(self,p):
  f=p.open('rb');self.opened.append(f);self.peak=max(self.peak,sum(not x.closed for x in self.opened));return f
 def stream(self,rows=None,guard=None,**kw):return helper['source_stream'](b'HEAD',b'INDEX',self.rows if rows is None else rows,guard or Guard(),safe_path=self.safe,opener=self.opener,**kw)
 def tearDown(self):
  for f in self.opened:f.close()
 def test_exact_old_order_nonadjacent_shared_padding_and_multichunk_crc(self):
  old=b''.join(ns['source_stream'](b'HEAD',b'INDEX',self.rows,Guard()))
  blocks=list(helper['coalesce'](self.stream(chunk=144),chunk=257));self.assertEqual(b''.join(blocks),old);self.assertTrue(all(len(b)==257 for b in blocks[:-1]));self.assertLessEqual(len(blocks[-1]),257)
  self.assertEqual(self.validations.count(self.base),1);self.assertEqual(len(self.opened),2);self.assertTrue(all(f.closed for f in self.opened));self.assertEqual(old[:9],b'HEADINDEX');self.assertEqual(len(old),9+3*2048)
 def test_independent_body_crc_rejects_when_descriptor_and_sha_match(self):
  data=bytearray(self.asset.read_bytes());data[-1]^=1;self.asset.write_bytes(data);r=dict(self.rows[1],sha256=hashlib.sha256(data).hexdigest())
  self.assertEqual(data[48:144].hex(),r['descriptor_hex']);self.assertEqual(struct.unpack_from('<I',data,36)[0],r['body_crc32'])
  with self.assertRaisesRegex(ValueError,'SHA/bodyCRC'):list(helper['coalesce'](self.stream([r],chunk=144)))
  self.assertTrue(all(f.closed for f in self.opened))
 def test_downstream_v1_failure_retains_handle_until_explicit_consumer_close(self):
  class FailWrite(Guard):
   def check(self,*args,**kw):
    if args:raise Refusal('downstream writer guard refusal')
  error=None
  try:ns['write_one'](self.root/'pack',helper['coalesce'](self.stream(guard=FailWrite()),chunk=16),10000,'0'*64,lambda p:None,FailWrite())
  except Refusal as e:error=e
  self.assertIsNotNone(error);self.assertEqual((self.root/'pack.part').stat().st_size,0);self.assertTrue(self.opened and any(not f.closed for f in self.opened))
  tb=error.__traceback__;blocks=None
  while tb:
   if tb.tb_frame.f_code.co_name=='write_one':blocks=tb.tb_frame.f_locals['blocks'];break
   tb=tb.tb_next
  self.assertIsNotNone(blocks);blocks.close();self.assertTrue(all(f.closed for f in self.opened))
  OBS['downstream_v1_gap']='CONFIRMED: retained actual write_one traceback owns suspended coalescer/sharedFD; explicit consumer close retires handle;0B partial preserved'
 def test_explicit_closing_contract_handles_same_downstream_refusal(self):
  class FailWrite(Guard):
   def check(self,*args,**kw):
    if args:raise Refusal('downstream writer guard refusal')
  error=None
  try:
   with contextlib.closing(helper['coalesce'](self.stream(guard=FailWrite()),chunk=16))as blocks:ns['write_one'](self.root/'pack',blocks,10000,'0'*64,lambda p:None,FailWrite())
  except Refusal as e:error=e
  self.assertIsNotNone(error);self.assertTrue(self.opened and all(f.closed for f in self.opened));self.assertTrue((self.root/'pack.part').exists())
 def test_shared_fd_pins_original_object_across_posix_path_replacement(self):
  old=b''.join(ns['source_stream'](b'HEAD',b'INDEX',self.rows,Guard()));g=self.stream();pieces=[next(g),next(g),next(g)];self.base.rename(self.root/'base-retained.bin');self.base.write_bytes(b'X'*512);pieces.extend(g)
  self.assertEqual(b''.join(pieces),old);self.assertEqual(self.validations.count(self.base),1);self.assertTrue(all(f.closed for f in self.opened))
  with self.assertRaisesRegex(ValueError,'SHA/bodyCRC'):b''.join(ns['source_stream'](b'HEAD',b'INDEX',self.rows,Guard()))
  OBS['path_replacement']='POSIX source fixture: helper uses original retained object and validates path once; frozen v1 reopens replacement and rejects changed bytes. No Windows/UNC sharing assertion.'
 def test_bound_is_eight_shared_plus_one_transient_and_nine_shared_refused(self):
  sources=[]
  for i in range(9):p=self.root/('tiny'+str(i));p.write_bytes(b'abc');sources.append(self.row(p,0,3))
  rows=sources[:8]+[sources[8]]+sources[:8];list(self.stream(rows));self.assertEqual(self.peak,9);self.assertTrue(all(f.closed for f in self.opened))
  before=len(self.opened)
  with self.assertRaisesRegex(ValueError,'too many repeated'):list(self.stream(sources+sources))
  self.assertEqual(len(self.opened),before);OBS['handle_bound']='8 retained shared descriptors PLUS1 transient single-use descriptor; default actual pack topology expected1 shared'
 def test_single_use_validation_refusal_closes_prior_shared_reader(self):
  actual=self.safe
  def safe(p,r):
   if p==self.asset:raise Refusal('source namespace refusal')
   return actual(p,r)
  with self.assertRaises(Refusal):list(helper['source_stream'](b'',b'',self.rows,Guard(),safe_path=safe,opener=self.opener))
  self.assertTrue(self.opened and all(f.closed for f in self.opened))
 def test_descriptor_chunk_parameter_has_minimum_header_precondition(self):
  with self.assertRaisesRegex(ValueError,'descriptor/header'):list(self.stream([self.rows[1]],chunk=143))
  self.assertTrue(all(f.closed for f in self.opened));OBS['chunk_precondition']='For descriptor rows first read must be>=144B; configurable positive chunks1..143 refuse valid descriptors. Default1MiB unaffected.'
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args();OUT=P(a.out);OUT.mkdir(parents=True,exist_ok=False);OBS={}
 suite=unittest.defaultTestLoader.loadTestsFromTestCase(Tests);result=unittest.TextTestRunner(verbosity=2).run(suite)
 receipt=dict(tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),helper_sha256=sha(HELPER),frozen_v1_sha256=sha(FROZEN),safe_path_sha256=sha(CHARGE),observations=OBS,scope='Tiny source-extracted Python/Linux host controls only, no large pack write/controller/guest or throughput claim')
 (OUT/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt));raise SystemExit(not result.wasSuccessful())