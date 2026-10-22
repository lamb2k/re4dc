"""Prepare one current staged C/ASM profile; no guest, native query or allocation.

Without a separately supplied root review, the written profile is deliberately
unlaunchable. Existing profiles/output paths are always preserved.
"""
from pathlib import Path,PurePosixPath
import argparse,datetime,hashlib,importlib,json,os,re,sys
from contain import P,HELPER,API,COUNTER,sha

BASE=Path(r'C:\Flycast-Evidence\re4-dreamcast\backface-sh4zam')
TEMPLATE=Path(r'C:\Flycast-Evidence\re4-dreamcast\d367-harness-par')
TRACKS={'track01.bin','track02.raw','track03.bin','track03.iso'}

def native_path(value):
 if value.startswith('/mnt/c/'):return Path('C:/'+value[7:])
 if value.startswith('/root/'):return Path(r'\\wsl.localhost\Ubuntu-24.04')/Path(value[1:])
 p=Path(value)
 if not p.is_absolute():raise ValueError('absolute pinned path required: '+value)
 return p

def checked_json(path,pin,inputs):
 path=native_path(str(path))
 data=path.read_bytes()
 if hashlib.sha256(data).hexdigest()!=pin:raise ValueError('receipt pin differs: '+str(path))
 inputs[str(path)]=pin;return json.loads(data)

def pin(path,inputs,expected=None):
 path=native_path(str(path))
 if not path.is_file() or path.is_symlink():raise ValueError('ordinary input file required: '+str(path))
 digest=sha(path)
 if expected and digest!=expected:raise ValueError('input hash differs: '+str(path))
 inputs[str(path)]=digest;return path

def runtime_inputs(inputs):
 # These imports perform no emulator/process/window queries. Pin the modules
 # used by stock runner/reader/PIL plus the CPython DLL and extension modules.
 for name in ('argparse','ast','copy','csv','ctypes','ctypes.wintypes','datetime','hashlib',
              'importlib.util','json','locale','os','pathlib','re','shutil','socket',
              'struct','subprocess','threading','time','encodings.cp1252','encodings.utf_16'):
  importlib.import_module(name)
 from PIL import Image
 Image.init()
 pin(Path(sys.executable),inputs)
 for module in list(sys.modules.values()):
  value=getattr(module,'__file__',None)
  if value:
   path=Path(value)
   if path.is_file() and path.suffix.lower() in ('.py','.pyd','.dll','.zip'):pin(path,inputs)
 for folder in (Path(sys.base_prefix),Path(sys.base_prefix)/'DLLs'):
  for pattern in ('*.dll','*.pyd','python*.zip'):
   for path in folder.glob(pattern):pin(path,inputs)
 # Include lazily used PIL plugins without executing their image operations.
 import PIL
 for path in Path(PIL.__file__).parent.rglob('*'):
  if path.is_file() and path.suffix.lower() in ('.py','.pyd','.dll'):pin(path,inputs)

def prepare(a):
 inputs={};stage_path=native_path(a.stage)
 stage=checked_json(stage_path,a.stage_sha256,inputs)
 if stage.get('status')!='PAIRED_FIXTURE_STAGED_NO_GUEST':raise ValueError('completed staged receipt required')
 if (stage['source'],stage['qa_source'],stage['run_id'],stage['fixture'])!=(a.source,a.qa_source,a.pair,a.fixture):raise ValueError('stage does not name exact current requested pair')
 if not re.fullmatch('[0-9a-f]{40}',a.source) or not re.fullmatch('[0-9a-f]{40}',a.qa_source):raise ValueError('full current source and QA identities required')
 if a.pair=='pair01':raise ValueError('obsolete pre-SDK pair01 is refused')
 # Main's actual SDK compilation receipt is pinned, but root must review its
 # semantics/current source; presence is never automatic source clearance.
 pin(a.sdk_evidence,inputs,a.sdk_sha256)
 work=native_path(stage['work']);programs=checked_json(work/'PROGRAMS-RECEIPT.json',stage['programme_receipt_sha256'],inputs)
 if programs['status']!='PROGRAMS_AND_PKGTREES_READY' or (programs['source'],programs['qa_source'],programs['run_id'])!=(a.source,a.qa_source,a.pair):raise ValueError('current programme receipt differs')
 identity=stage['cases'][a.arm]['programme']
 if identity!=programs['arms'][a.arm]:raise ValueError('stage programme differs from current programme receipt')
 elf=pin(identity['elf'],inputs,identity['elf_sha256']);raw=pin(identity['raw'],inputs,identity['raw_sha256'])
 overlays=[]
 if len(identity['overlays'])!=14:raise ValueError('all14 overlays required')
 for name,digest in identity['overlays'].items():overlays.append(str(pin(elf.parent/name,inputs,digest)))
 resolved=pin(elf.parent/'resolved-knobs.txt',inputs,identity['resolved_sha256'])
 knobs=dict(line.split('=',1)for line in resolved.read_text().splitlines()if'='in line)
 for key,value in dict(CPU_BACKFACE='1'if a.arm=='C'else'2',ACTOR_BACKFACE='1',VRAM_ROOM_ARENA='0',GAME_SH4ZAM='1',TA_HASH='1',BACKFACE_CENSUS='1').items():
  if knobs.get(key)!=value:raise ValueError('resolved knob differs: '+key)
 assets=checked_json(identity['assets_file'],identity['assets_sha256'],inputs)
 case=stage['cases'][a.arm];disc=native_path(case['c_gdemu'])
 if disc.resolve()!=disc.absolute():raise ValueError('staged C disc alias refused')
 expected=case['expected']
 if {p.name for p in disc.iterdir()}!=set(expected):raise ValueError('staged disc member set changed')
 for name,info in expected.items():
  path=pin(disc/name,inputs,info['sha256'])
  if path.stat().st_size!=info['size']:raise ValueError('staged track size changed')
 manifest_path=work/'fixtures'/a.fixture/a.arm/'disc-manifest.json';manifest_data=manifest_path.read_bytes();manifest=json.loads(manifest_data);inputs[str(manifest_path)]=hashlib.sha256(manifest_data).hexdigest()
 manifest={key.lstrip('/'):value for key,value in manifest.items()}
 for key,info in assets.items():
  if key.lower()=='1st_read.bin':continue
  if manifest[key]['sha256']!=info['sha256'] or manifest[key]['size']!=info['size']:raise ValueError('staged asset member differs: '+key)
 if manifest['1ST_READ.BIN']['sha256']!=identity['raw_sha256']:raise ValueError('boot programme member differs')
 fixture=stage['fixture_pins'][a.fixture];pin(fixture['path'],inputs,fixture['sha256'])
 tick={'f1':330,'close-ganado':420}[a.fixture]
 fixture_text=native_path(fixture['path']).read_text()
 if re.findall(r'(?m)^freeze\s+(\d+)\s*$',fixture_text)!=[str(tick)]:raise ValueError('fixture freeze differs')
 if manifest['dc/warp.txt']['sha256']!=fixture['sha256'] or case['fixture_sha256']!=fixture['sha256']:raise ValueError('staged fixture member differs')
 syms=pin(disc.parent/'syms.txt',inputs)
 if syms.read_text().strip()!=identity['syms'] or len(identity['syms'].split())!=3:raise ValueError('three current ELF symbols differ')
 stock=pin(a.stock,inputs,a.stock_sha256)
 if stock.read_text().count('mod.capture(shot, shot / \'frames\')')!=1:raise ValueError('fixed stock capture call differs')
 for path in (HELPER,API,COUNTER,*P.glob('*.py')):pin(path,inputs)
 console=pin(a.console,inputs,a.console_sha256)
 for name in ('emu.cfg','read_log.py','capture_ui_vram.py'):pin(TEMPLATE/name,inputs)
 config=(TEMPLATE/'emu.cfg').read_text()
 if not re.search(r'(?mi)^rend.EmulateFramebuffer\s*=\s*(yes|true|1)\s*$',config):raise ValueError('stock RGB565 capture disabled')
 if re.search(r'(?mi)^Auto(?:Load|Save)State\s*=\s*(yes|true|1)\s*$',config):raise ValueError('automatic save states refused')
 for path in (TEMPLATE/'data').rglob('*'):
  if path.is_file():pin(path,inputs)
 runtime_inputs(inputs)
 env=json.loads(Path(a.environment).read_text());pin(a.environment,inputs)
 if not isinstance(env,dict) or env.get('RE4DC_EMU')!='console' or env.get('RE4DC_MAX_FLYCASTS')!='16':raise ValueError('explicit console/global16 environment required')
 if not all(isinstance(k,str)and isinstance(v,str)and(k.startswith('RE4DC_')or k=='FP_NOLIMIT')for k,v in env.items()):raise ValueError('explicit runner environment only')
 if env.get('RE4DC_CONSOLE_EXE',str(console))!=str(console):raise ValueError('console environment selects another executable')
 profile_path=Path(a.profile).absolute();output=BASE/(a.source+'-'+a.fixture+'-'+a.arm.lower()+'-01');capture=output/'capture'
 if output.exists() or profile_path.exists():raise FileExistsError('fresh output and profile required')
 hardlinks={}
 for name in TRACKS&set(expected):
  path=disc/name;st=path.stat();hardlinks[str(capture/name)]=dict(source=str(path),bytes=st.st_size,inode=st.st_ino,device=st.st_dev,links_before=st.st_nlink,sha256=inputs[str(path)])
 stock_argv=['--disc',str(disc),'--cap',str(capture),'--syms',identity['syms'],'--seconds','40','--period','2','--stop','^warp: frozen at tick '+str(tick)+'$','--grace','8','--name','bfasm-'+a.source[:8]+'-'+a.fixture+'-'+a.arm.lower()]
 profile=dict(fixture_name=a.fixture,arm=a.arm,source=a.source,qa_source=a.qa_source,pair=a.pair,output=str(output),capture=str(capture),
  controller_child_argv=[sys.executable,'-B',str(P/'stock_child.py'),str(profile_path)],stock_runner=str(stock),stock_sha256=inputs[str(stock)],stock_argv=stock_argv,
  environment=env,inputs=inputs,hardlink_refs=hardlinks,overlays=overlays,console_source=str(console),console_sha256=inputs[str(console)],freeze_tick=tick,
  stage_receipt=str(stage_path),stage_receipt_sha256=a.stage_sha256,programme_receipt_sha256=stage['programme_receipt_sha256'],
  current_programme_closure_verified=False,lane_live_guests=None,fresh_root_capacity_review=False,root_review=None,
  preparation_scope='Source/file validation only; no guest, native query, run allocation or hardware acceptance.')
 if a.root_review:
  review=checked_json(a.root_review,a.root_review_sha256,inputs)
  expected_review=dict(stage_receipt_sha256=a.stage_sha256,source=a.source,qa_source=a.qa_source,pair=a.pair,fixture=a.fixture,arm=a.arm,
   programme_and_asset_disc_closure_reviewed=True,actual_sdk_source_reviewed=True)
  if any(review.get(k)!=v for k,v in expected_review.items()):raise ValueError('root has not reviewed exact current staged closure')
  if review.get('lane_live_guests')not in(0,1)or not isinstance(review.get('global_live_guests'),int)or not 0<=review['global_live_guests']<16:raise ValueError('fresh root capacity review required')
  age=(datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat(review['capacity_reviewed_utc'])).total_seconds()
  if not 0<=age<=60:raise ValueError('root capacity review is stale')
  profile.update(current_programme_closure_verified=True,lane_live_guests=review['lane_live_guests'],fresh_root_capacity_review=True,root_review=review)
 return profile

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for name in ('stage','stage-sha256','source','qa-source','pair','sdk-evidence','sdk-sha256','stock','stock-sha256','console','console-sha256','environment','profile'):p.add_argument('--'+name,required=True)
 p.add_argument('--fixture',choices=['f1','close-ganado'],required=True);p.add_argument('--arm',choices=['C','ASM'],required=True)
 p.add_argument('--root-review');p.add_argument('--root-review-sha256');p.add_argument('--write',action='store_true');a=p.parse_args()
 profile=prepare(a);data=json.dumps(profile,indent=2)+'\n'
 if len(data.encode())>256*1024:raise ValueError('profile exceeds metadata allocation')
 if a.write:
  with Path(a.profile).open('x',newline='\n')as f:f.write(data)
 print(json.dumps(dict(profile=a.profile,written=a.write,sha256=hashlib.sha256(data.encode()).hexdigest(),input_count=len(profile['inputs']),
                       closure_reviewed=profile['current_programme_closure_verified'],allocated=False)))
if __name__=='__main__':main()
