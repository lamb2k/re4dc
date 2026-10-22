"""Tiny synthetic file-contract controls, never target/image/guest acceptance."""
import argparse,copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import prepare_profile as m
from contain import sha

class Tests(unittest.TestCase):
 def fixture(self,base,name='f1'):
  work=base/'work';work.mkdir();out=base/'objects';out.mkdir();disc=base/'disc';disc.mkdir();template=base/'template';template.mkdir();(template/'data').mkdir()
  def write(path,data):path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data);return str(path)
  def obj(path,value):write(path,(json.dumps(value)+'\n').encode());return sha(path)
  elf=write(out/'program.elf',b'fake ELF identity, source control only');raw=write(work/'program.raw',b'fake raw')
  overlays={}
  for index in range(14):
   f=out/(str(index)+'.ovl');write(f,bytes([index]));overlays[f.name]=sha(f)
  resolved=out/'resolved-knobs.txt';write(resolved,b'CPU_BACKFACE=2\nACTOR_BACKFACE=1\nVRAM_ROOM_ARENA=0\nGAME_SH4ZAM=1\nTA_HASH=1\nBACKFACE_CENSUS=1\n')
  assets=work/'assets.json';obj(assets,{'dc/model.dat':{'size':3,'sha256':'a'*64}})
  identity=dict(elf=elf,elf_sha256=sha(elf),raw=raw,raw_sha256=sha(raw),overlays=overlays,resolved_sha256=sha(resolved),assets_file=str(assets),assets_sha256=sha(assets),syms='0x10 0x20 0x30')
  programs=work/'PROGRAMS-RECEIPT.json';obj(programs,dict(status='PROGRAMS_AND_PKGTREES_READY',source='1'*40,qa_source='2'*40,run_id='pair02',arms={'ASM':identity}))
  expected={}
  for name2 in ('disc.gdi','track01.bin','track02.raw','track03.bin'):
   f=disc/name2;write(f,b'synthetic track contract only');expected[name2]=dict(size=f.stat().st_size,sha256=sha(f))
  write(disc.parent/'syms.txt',b'0x10 0x20 0x30\n')
  tick=330 if name=='f1' else 420;fixture=base/'fixture.txt';write(fixture,('freeze '+str(tick)+'\n').encode())
  manifest=work/'fixtures'/name/'ASM/disc-manifest.json';obj(manifest,{'dc/model.dat':{'size':3,'sha256':'a'*64},'1ST_READ.BIN':{'sha256':sha(raw)},'dc/warp.txt':{'sha256':sha(fixture)}})
  stage=base/'stage.json';obj(stage,dict(status='PAIRED_FIXTURE_STAGED_NO_GUEST',source='1'*40,qa_source='2'*40,run_id='pair02',fixture=name,work=str(work),programme_receipt_sha256=sha(programs),fixture_pins={name:dict(path=str(fixture),sha256=sha(fixture))},cases={'ASM':dict(programme=identity,c_gdemu=str(disc),expected=expected,fixture_sha256=sha(fixture))}))
  sdk=base/'sdk.json';write(sdk,b'fake SDK receipt, not source clearance')
  stock=base/'stock.py';write(stock,b"mod.capture(shot, shot / 'frames')\n")
  console=base/'console.exe';write(console,b'fake console source control only')
  for dep in ('emu.cfg','read_log.py','capture_ui_vram.py'):write(template/dep,b'rend.EmulateFramebuffer = yes\n')
  env=base/'environment.json';obj(env,dict(RE4DC_EMU='console',RE4DC_MAX_FLYCASTS='16',RE4DC_CONSOLE_EXE=str(console)))
  a=argparse.Namespace(stage=str(stage),stage_sha256=sha(stage),source='1'*40,qa_source='2'*40,pair='pair02',fixture=name,arm='ASM',sdk_evidence=str(sdk),sdk_sha256=sha(sdk),stock=str(stock),stock_sha256=sha(stock),console=str(console),console_sha256=sha(console),environment=str(env),profile=str(base/'profile.json'),root_review=None,root_review_sha256=None)
  return a,template
 def run_fixture(self,a,template):
  with patch.object(m,'BASE',Path(a.profile).parent/'runs'),patch.object(m,'TEMPLATE',template),patch.object(m,'runtime_inputs',lambda inputs:None):return m.prepare(a)
 def test_draft_stays_unallocated_and_unreviewed(self):
  with tempfile.TemporaryDirectory()as tmp:
   a,t=self.fixture(Path(tmp));p=self.run_fixture(a,t);self.assertFalse(p['current_programme_closure_verified']);self.assertFalse(p['fresh_root_capacity_review']);self.assertIsNone(p['lane_live_guests']);self.assertFalse(Path(a.profile).exists());self.assertFalse(Path(p['output']).exists())
 def test_close_fixture420(self):
  with tempfile.TemporaryDirectory()as tmp:
   a,t=self.fixture(Path(tmp),'close-ganado');p=self.run_fixture(a,t);self.assertEqual(p['freeze_tick'],420);self.assertIn('^warp: frozen at tick 420$',p['stock_argv'])
 def test_old_pair_refused(self):
  with tempfile.TemporaryDirectory()as tmp:
   a,t=self.fixture(Path(tmp));a.pair='pair01'
   with self.assertRaises(ValueError):self.run_fixture(a,t)
 def test_track_change_refused(self):
  with tempfile.TemporaryDirectory()as tmp:
   a,t=self.fixture(Path(tmp));(Path(tmp)/'disc/track03.bin').write_bytes(b'changed')
   with self.assertRaises(ValueError):self.run_fixture(a,t)
 def test_overlay_change_refused(self):
  with tempfile.TemporaryDirectory()as tmp:
   a,t=self.fixture(Path(tmp));(Path(tmp)/'objects/5.ovl').write_bytes(b'changed')
   with self.assertRaises(ValueError):self.run_fixture(a,t)
 def test_fixture_change_refused(self):
  with tempfile.TemporaryDirectory()as tmp:
   a,t=self.fixture(Path(tmp));(Path(tmp)/'fixture.txt').write_bytes(b'freeze 420\n')
   with self.assertRaises(ValueError):self.run_fixture(a,t)
if __name__=='__main__':unittest.main()
