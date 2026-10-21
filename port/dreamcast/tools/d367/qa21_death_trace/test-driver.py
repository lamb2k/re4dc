#!/usr/bin/env python3
"""Source-only preservation and resource-bound tests; no KOS build/image/guest."""
import ast,hashlib,subprocess,tempfile,unittest
from pathlib import Path
SOURCE=Path(__file__).with_name('full-link.py')
FUNCTIONS=ast.parse(SOURCE.read_text())
class DriverSafety(unittest.TestCase):
 def test_source_view_shadows_writable_paths(self):
  with tempfile.TemporaryDirectory(prefix='qa21-trace-driver-') as td:
   root=Path(td);base=root/'frozen';view=root/'view';trace=root/'trace';out=root/'out';base.mkdir();trace.mkdir();out.mkdir();scratch=base/'port/dreamcast/game/obj';scratch.mkdir(parents=True);(scratch/'pass1.elf').write_bytes(b'preserve frozen ELF')
   gen=base/'port/dreamcast/game/platform/sdk/gen';gen.mkdir(parents=True);(gen/'old.c').write_text('preserve frozen generated source')
   src=base/'src/game';src.mkdir(parents=True);(src/'game.cpp').write_text('frozen source');(src/'untouched.cpp').write_text('untouched source');(trace/'game.cpp').write_text('trace source');(trace/'Makefile').write_text('trace Makefile')
   tools=base/'port/dreamcast/tools/d367';tools.mkdir(parents=True);(tools/'root.sh').write_text('ROOT=$(cd "$(dirname "$0")/../../../.." && pwd)\nprintf "%s" "$ROOT"\n')
   (base/'port/dreamcast/game/Makefile').write_text('frozen Makefile');own=out/'link-scratch';own.mkdir()
   overrides={'src/game/game.cpp':trace/'game.cpp','port/dreamcast/game/Makefile':trace/'Makefile','port/dreamcast/game/obj':own,'port/dreamcast/game/platform/sdk/gen':None}
   ns={'Path':Path,'BASE':base,'VIEW':view,'overrides':overrides};tree=ast.Module(body=[x for x in FUNCTIONS.body if isinstance(x,ast.FunctionDef) and x.name=='mirror'],type_ignores=[]);exec(compile(tree,str(SOURCE),'exec'),ns);ns['mirror']()
   self.assertEqual((view/'src/game/game.cpp').read_text(),'trace source');self.assertEqual((view/'src/game/untouched.cpp').read_text(),'untouched source')
   (view/'port/dreamcast/game/obj/pass1.elf').write_bytes(b'new owned scratch');(view/'port/dreamcast/game/platform/sdk/gen/new.c').write_text('new owned generated source')
   self.assertEqual((scratch/'pass1.elf').read_bytes(),b'preserve frozen ELF');self.assertEqual((gen/'old.c').read_text(),'preserve frozen generated source');self.assertFalse((gen/'new.c').exists());self.assertEqual((own/'pass1.elf').read_bytes(),b'new owned scratch')
   got=subprocess.check_output(['bash',str(view/'port/dreamcast/tools/d367/root.sh')],cwd=view,text=True);self.assertEqual(got,str(view))
 def test_resource_boundaries(self):
  floor=18*1024**3+64*1024**2;cap=320*1024**2;log=8_000_000;ns={'FLOOR':floor,'CAP':cap,'LOG_CAP':log};tree=ast.Module(body=[x for x in FUNCTIONS.body if isinstance(x,ast.FunctionDef) and x.name=='stop_build_reason'],type_ignores=[]);exec(compile(tree,str(SOURCE),'exec'),ns);f=ns['stop_build_reason']
  self.assertIsNone(f(floor,cap-1,log-1,599.9));self.assertIn('floor',f(floor-1,0,0,0));self.assertIn('320MiB',f(floor,cap,0,0));self.assertIn('8MB',f(floor,0,log,0));self.assertIn('600s',f(floor,0,0,600))
 def test_overlay_binding_rejects_old_program(self):
  from overlay_identity import elf_text,overlay_bytes
  r=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/qa21-combined-regression-20261021');combined=elf_text(r/'builds/combined/re4dc-game.elf');control=elf_text(r/'builds/qa-control/re4dc-game.elf');overlay=(r/'builds/combined/sscrn.ovl').read_bytes();row=overlay_bytes(overlay,combined);self.assertEqual(row['bytes'],len(overlay))
  with self.assertRaisesRegex(AssertionError,'binding differs'):overlay_bytes(overlay,control)
if __name__=='__main__':unittest.main()