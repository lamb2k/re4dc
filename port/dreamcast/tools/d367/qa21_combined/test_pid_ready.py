from pathlib import Path
import importlib.util,tempfile,unittest
p=Path(__file__).with_name('run_observed_v3.py')
s=importlib.util.spec_from_file_location('qa21_observed_v2',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class PidRead(unittest.TestCase):
 def test_missing_and_empty_are_retryable(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'flycast.pid';self.assertIsNone(m.read_owned_pid(p));p.write_text('');self.assertIsNone(m.read_owned_pid(p));p.write_text('pending');self.assertIsNone(m.read_owned_pid(p))
 def test_complete_pid_is_read(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'flycast.pid';p.write_text('12345\n');self.assertEqual(m.read_owned_pid(p),12345)
if __name__=='__main__':unittest.main()