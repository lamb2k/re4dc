"""NEWv2 source fixtures only; failurev1 remains untouched, no pack output."""
import hashlib,json
from unittest.mock import patch
import unittest
import immutable_append1618_buffered_v2_writer as new
import test_immutable_append1600_writer as original
import test_immutable_append1618_writer as prior

class BufferedV2Tests(prior.Reused1618WriterTests):
 def setUp(self):
  original.WriterTests.setUp(self);self.p1=patch.object(original,'w',new);self.p2=patch.object(prior,'new',new);self.p1.start();self.p2.start()
 def tearDown(self):self.p2.stop();self.p1.stop();original.WriterTests.tearDown(self)
 def test_exact_child_allocation_refusals(self):
  plan=dict(controller_sha256='a'*64,metadata_root='synthetic-meta',payload_roots=['one','two'],prior_failed_controller_sha256='c'*64);pp=self.root/'plan.json';pp.write_text(json.dumps(plan));ps=new.sha(pp);ap=self.root/'allocation.json'
  a=dict(allocated=True,allocation_id='SYNTHETIC_NOT_EXECUTABLE',writer_plan_sha256=ps,writer_source_sha256=new.sha(new.__file__),controller_sha256=plan['controller_sha256'],aggregate_cap_bytes=new.CAP,runtime_floor_bytes=new.FLOOR,peer_reserved_bytes=new.PEER,inner_seconds=51,approved_output_root=plan['metadata_root'],approved_payload_roots=plan['payload_roots'],prior_failed_controller_sha256=plan['prior_failed_controller_sha256'])
  ap.write_text(json.dumps(a));self.assertEqual(new.allocation(pp,ps,ap,new.sha(ap),plan)['allocation_id'],a['allocation_id'])
  for field,value in[('allocated',False),('aggregate_cap_bytes',new.CAP+1),('runtime_floor_bytes',0),('peer_reserved_bytes',0),('controller_sha256','b'*64),('writer_source_sha256','0'*64),('approved_payload_roots',['elsewhere']),('compression_credits',[{}]),('prior_failed_controller_sha256','d'*64)]:
   ap.write_text(json.dumps({**a,field:value}))
   with self.subTest(field=field),self.assertRaises(ValueError):new.allocation(pp,ps,ap,new.sha(ap),plan)
  ap.write_text(json.dumps(a))
  with self.assertRaises(ValueError):new.allocation(pp,ps,ap,'0'*64,plan)
 def test_actual_newstream_coalesces_identical_bytes_shared_validation_once(self):
  h,i,rows,blob,k=self.fixture();rows=rows+[dict(rows[0],key='00000003-00000004')];g=self.guard();safe=new.safe_path;calls=[]
  def counted(p,r):calls.append(str(p));return safe(p,r)
  with patch.object(new,'safe_path',side_effect=counted):blocks=list(new.source_stream(h,i,rows,g))
  package=rows[0]['path'].read_bytes();expected=h+i+(package+bytes((-len(package))%2048))*2
  self.assertEqual(b''.join(blocks),expected);self.assertEqual(len(blocks),1);self.assertEqual(len(calls),1)
 def test_write_guard_failure_closes_buffered_upstream_immediately(self):
  events=[]
  def source():
   try:yield b'abcd'
   finally:events.append('UPSTREAM_CLOSED')
  g=self.guard();check=g.check
  def fail_output(path=None,*args,**kwargs):
   if path is not None:raise RuntimeError('SYNTHETIC_OUTPUT_GUARD')
   return check(path,*args,**kwargs)
  target=self.root/'guard-failure';blocks=new.coalesce(source(),chunk=2)
  with patch.object(g,'check',side_effect=fail_output),self.assertRaisesRegex(RuntimeError,'SYNTHETIC_OUTPUT_GUARD'):new.write_one(target,blocks,4,hashlib.sha256(b'abcd').hexdigest(),lambda _:None,g)
  self.assertEqual(events,['UPSTREAM_CLOSED']);self.assertEqual((self.root/'guard-failure.part').read_bytes(),b'');self.assertFalse(target.exists())
if __name__=='__main__':unittest.main(verbosity=2)
