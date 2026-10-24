"""Actual source parser/member/bridge controls, synthetic source bytes only."""
from pathlib import Path
import subprocess,tempfile,unittest
from test_runtime_hooks import function
HERE=Path(__file__).resolve().parent
GAME=HERE.parents[2]/'game'
class OriginalGeometryTests(unittest.TestCase):
 def compile(self,text,mutant=False):
  with tempfile.TemporaryDirectory(prefix='gc-original-bridge-',dir='/dev/shm') as d:
   p=Path(d)/'source.cpp';p.write_text(text);exe=Path(d)/'check'
   subprocess.run(['g++','-std=c++17','-O1','-Wall','-Wextra','-Werror','-DRE4DC_GC_ASSET_GATE=1','-DRE4DC_NATIVE_ACTOR_FAST=1','-DRE4DC_GC_ASSET_TEST=1','-I',str(GAME/'platform/include'),str(p),str(GAME/'platform/gc_asset_members.cpp'),str(GAME/'platform/gc_asset_gate.cpp'),str(GAME/'platform/gc_asset_payloads.cpp'),'-o',str(exe)],check=True,capture_output=True,text=True)
   q=subprocess.run([str(exe)],capture_output=True,text=True)
   self.assertNotEqual(q.returncode,0,q.stderr) if mutant else self.assertEqual(q.returncode,0,q.stderr)
 def test_actual_parser_and_member_lifetime(self):self.compile((HERE/'test_original_geometry.cpp').read_text())
 def fixture(self):
  bridge=(GAME/'model_bridge.cpp').read_text()
  names=['bool gcasset_original_input(','extern "C" void re4dc_gcasset_pose_reset(','extern "C" void re4dc_gcasset_pose_publish(','extern "C" void re4dc_gcasset_shape_reset(','extern "C" void re4dc_gcasset_shape_source(','extern "C" unsigned re4dc_gcasset_weapon_consumer(','extern "C" re4dc_gcasset::SourceUse re4dc_gcasset_original_model_select(','extern "C" re4dc_gcasset::SourceUse re4dc_gcasset_original_actor_select(']
  fixture=(HERE/'test_original_bridge.cpp.in').read_text().replace('// BRIDGE_FUNCTIONS','\n'.join(function(bridge,n) for n in names))
  ui=(GAME/'platform/native_ui.cpp').read_text()
  fixture=fixture.replace('// UI_ACCEPT_FUNCTIONS',function(ui,'void gcasset_model_prepare(')+'\n'+function(ui,'void gcasset_model_accept('))
  model=(GAME/'platform/native_model.cpp').read_text();start=model.index('extern "C" void re4dc_model_submit(')
  gateway=model[start:model.index('#if RE4DC_NATIVE_ACTOR\n',start)]+'observe_selected(p);\n}\n'
  return fixture.replace('// MODEL_GATEWAY',gateway)
 def test_actual_raw_rigid_prepared_lazy_and_foreign_sources(self):self.compile(self.fixture())
 def test_semantic_mutants(self):
  source=self.fixture()
  for old,new in [('part->uv!=input.uv','false'),('!member_pose_current(info,member.serial,part->positions,part->normals,pG->Frame_cnt)','false'),('source->positions!=d->vtxOrig','false')]:
   with self.subTest(mutant=old):self.assertIn(old,source);self.compile(source.replace(old,new),True)
