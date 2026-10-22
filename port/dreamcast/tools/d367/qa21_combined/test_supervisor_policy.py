from pathlib import Path
import ast,unittest
source=Path(__file__).with_name('run-fixture.py').read_text()
node=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='stop_reason')
namespace={};exec(compile(ast.Module(body=[node],type_ignores=[]),'<actual stop policy>','exec'),namespace)
reason=namespace['stop_reason'];floor=18*1024**3+64*1024**2
class Boundaries(unittest.TestCase):
 def test_time_margin(self):
  self.assertIsNone(reason(47.499,floor));self.assertEqual(reason(47.5,floor),'absolute owned guest wall-time cap');self.assertEqual(reason(48.0,floor),'absolute owned guest wall-time cap')
 def test_disk_floor(self):
  self.assertIsNone(reason(0,floor));self.assertEqual(reason(0,floor-1),'C18GiB+64MiB runtime floor');self.assertIsNone(reason(0,floor+1))
if __name__=='__main__':unittest.main()