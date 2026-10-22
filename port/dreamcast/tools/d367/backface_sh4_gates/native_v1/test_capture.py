import ast,json,pathlib,tempfile,unittest
from stock_child import instrument,CaptureHook
P=pathlib.Path(__file__).parent
STOCK=pathlib.Path(r'\\wsl.localhost\Ubuntu-24.04\root\probe\codex-backface-sh4zam-gates\port\dreamcast\tools\d367\fullplay\fp_run.py')
class Tests(unittest.TestCase):
 def prepare(self,cap):
  (cap/'run-output.txt').write_text('warp: frozen at tick 330')
  (cap/'boot.log').write_text('fb=a5000000,a5000008\n',encoding='utf-16')
  return {'pid':7,'start_filetime':12,'path':'owned.exe','private_job_members':[1,7]}
 def capture(self,evidence,output):
  output.mkdir();(output/'fb0.png').write_bytes(b'fake host image0');(output/'fb1.png').write_bytes(b'fake host image1');return [0,4]
 def test_actual_stock_unique_capture_only(self):self.assertIsInstance(instrument(STOCK.read_text()),ast.Module)
 def test_missing_capture_refuses(self):
  with self.assertRaises(ValueError):instrument('print(1)')
 def test_two_capture_calls_refuse(self):
  with self.assertRaises(ValueError):instrument('mod.capture(a,b)\nmod.capture(c,d)')
 def test_no_freeze_no_native_read(self):
  with tempfile.TemporaryDirectory() as tmp:
   cap=pathlib.Path(tmp);(cap/'run-output.txt').write_text('not frozen');hook=CaptureHook({'capture':tmp,'freeze_tick':330},proof=lambda:(_ for _ in ()).throw(AssertionError('native touched')));self.assertEqual(hook(lambda *a:None,cap,cap/'frames'),[])
 def test_frozen_read_before_after_identity_and_clock(self):
  with tempfile.TemporaryDirectory() as tmp:
   cap=pathlib.Path(tmp);pin=self.prepare(cap);clock=iter([11,12]);calls=[];hook=CaptureHook({'capture':tmp,'freeze_tick':330},clock=lambda:next(clock),schedule=lambda:18,proof=lambda:(calls.append('identity') or pin));self.assertEqual(hook(self.capture,cap,cap/'frames'),[0,4]);self.assertEqual(calls,['identity','identity']);self.assertTrue(hook.events[0]['qualified'])
 def test_late_capture_refuses(self):
  with tempfile.TemporaryDirectory() as tmp:
   cap=pathlib.Path(tmp);pin=self.prepare(cap);clock=iter([11,41]);hook=CaptureHook({'capture':tmp,'freeze_tick':330},clock=lambda:next(clock),schedule=lambda:18,proof=lambda:pin)
   with self.assertRaises(ValueError):hook(self.capture,cap,cap/'frames')
 def test_identity_change_refuses(self):
  with tempfile.TemporaryDirectory() as tmp:
   cap=pathlib.Path(tmp);pin=self.prepare(cap);ident=iter([pin,{**pin,'pid':8}]);hook=CaptureHook({'capture':tmp,'freeze_tick':330},clock=lambda:11,schedule=lambda:18,proof=lambda:next(ident))
   with self.assertRaises(ValueError):hook(self.capture,cap,cap/'frames')
 def test_tick3300_is_not_tick330(self):
  with tempfile.TemporaryDirectory() as tmp:
   cap=pathlib.Path(tmp);self.prepare(cap);(cap/'run-output.txt').write_text('warp: frozen at tick 3300');hook=CaptureHook({'capture':tmp,'freeze_tick':330},proof=lambda:(_ for _ in ()).throw(AssertionError('native touched')));self.assertEqual(hook(self.capture,cap,cap/'frames'),[])
 def test_actual_caller_stop_local(self):
  with tempfile.TemporaryDirectory() as tmp:
   cap=pathlib.Path(tmp);pin=self.prepare(cap);clock=iter([11,12]);hook=CaptureHook({'capture':tmp,'freeze_tick':330},clock=lambda:next(clock),proof=lambda:pin)
   stop_at=18
   self.assertEqual(hook(self.capture,cap,cap/'frames'),[0,4]);self.assertEqual(hook.events[0]['freeze_observed_monotonic'],10)
 def test_missing_stop_local_refuses(self):
  with tempfile.TemporaryDirectory() as tmp:
   cap=pathlib.Path(tmp);pin=self.prepare(cap);hook=CaptureHook({'capture':tmp,'freeze_tick':330},proof=lambda:pin)
   with self.assertRaises(ValueError):hook(self.capture,cap,cap/'frames')
 def test_capture_start_outside_stock_grace_refuses(self):
  with tempfile.TemporaryDirectory() as tmp:
   cap=pathlib.Path(tmp);pin=self.prepare(cap);hook=CaptureHook({'capture':tmp,'freeze_tick':330},clock=lambda:19,schedule=lambda:18,proof=lambda:pin)
   with self.assertRaises(ValueError):hook(self.capture,cap,cap/'frames')
if __name__=='__main__':unittest.main()
