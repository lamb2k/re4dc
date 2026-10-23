"""Validate one main-staged mode1 census; never allocate or launch."""
from pathlib import Path
import argparse,hashlib,json,re,sys
from contain import P,HELPER,API,COUNTER,sha
from binding_helpers import native_path,checked_json,pin,runtime_inputs
from policy import FINAL_SOURCE,INTEGRATION,STOP,STOCK_SHA,READER_SHA,CAPTURE_SHA,FIXTURE_SHA,PAD_SHA,OUTPUT_NAME,fixed_stock_contract,root_review_contract
from bindings import verify_bound,NORMALIZATION_SHA
from validate_bindings import current_programme,ownership_contract
TEMPLATE=Path(r'C:\Flycast-Evidence\re4-dreamcast\d367-harness-par')
OUTPUT=Path(r'C:\Flycast-Evidence\re4-dreamcast\pvs23-20261022')
def validate_fixture_bytes(row,raw):
 basis=native_path(row['basis_path']).read_bytes()
 if hashlib.sha256(basis).hexdigest()!='9bb15f9878843c6fdad1783afa0aef297ce63a4a3be0710302c110a63376c76c' or raw!=basis+b'goto 300 112950 2298.247 19750 3.14159265\r\nlate 0x20 539 0x119\r\n' or row['sha256']!=FIXTURE_SHA or hashlib.sha256(raw).hexdigest()!=FIXTURE_SHA:raise ValueError('exact g8 prefix plus reviewed candidate-A goto and no-hold census late required')

def profile_destinations(profile):
 profile=Path(profile).absolute();output=OUTPUT/OUTPUT_NAME
 if output.exists()or profile.exists():raise FileExistsError('preserve prior one-attempt output/profile; no automatic retry')
 return profile,output,output/'capture'

def validate_stage_bindings(stage,binding):
 if(stage.get('status'),stage.get('source'),stage.get('integration'))!=('ACTOR23_TWIN_STAGED_NO_GUEST',FINAL_SOURCE,INTEGRATION):raise ValueError('exact fresh main-staged actor twin required')
 if stage.get('programme_receipt_sha256')!=binding['programme']['sha256']:raise ValueError('stage current programme differs')
 for key in ('ownership_audit','kos_receipt','module_roster'):
  expected=binding[key];actual=stage.get(key,{})
  from material_identity import require_bound_receipt
  require_bound_receipt(actual,expected,native_path)
 if 'fixture_rebind'in stage:raise ValueError('fresh image stage required, not old fixture-only derivative')
 return stage

def prepare(a):
 inputs={};binding=verify_bound(inputs);stage=checked_json(a.stage,a.stage_sha256,inputs)
 validate_stage_bindings(stage,binding)
 programme,syms=current_programme(stage,FINAL_SOURCE,inputs)
 if programme['arm']!='on':raise ValueError('mode1 census uses exact enabled ON only')
 ownership_contract(stage,programme,FINAL_SOURCE,inputs)
 assets=checked_json(stage['assets_manifest']['path'],stage['assets_manifest']['sha256'],inputs);disc=checked_json(stage['disc_manifest']['path'],stage['disc_manifest']['sha256'],inputs)
 assets={k.lstrip('/'):v for k,v in assets.items()};disc={k.lstrip('/'):v for k,v in disc.items()}
 for row in programme['world_package_baseline']['files']:
  if assets.get(row['name'])!={'size':row['size'],'sha256':row['sha256']}:raise ValueError('original r119 certificate source package differs')
 expected=dict(assets);expected['1ST_READ.BIN']=dict(sha256=programme['raw']['sha256'],size=native_path(programme['raw']['path']).stat().st_size)
 for item in programme['overlays']:expected[item['package_path']]=dict(sha256=item['sha256'],size=native_path(item['path']).stat().st_size)
 expected['dc/native/r119/room.r4rc']=dict(sha256=programme['private_room_metadata']['sha256'],size=40080)
 if disc!=expected:raise ValueError('complete raw+14 overlays+only private room metadata inventory differs')
 extract=checked_json(stage['extraction_receipt']['path'],stage['extraction_receipt']['sha256'],inputs)
 if extract.get('extracted_from_iso')is not True or extract.get('iso_sha256')!=stage['members']['track03.iso']['sha256']or extract.get('manifest_sha256')!=stage['disc_manifest']['sha256']:raise ValueError('actual ISO extraction/readback closure absent')
 base=native_path(stage['base']);members=stage['members']
 if base.resolve()!=base.absolute()or base.drive.casefold()!='c:'or set(members)!={'base.json','track01-template.iso','track02.raw','track03.iso','track03.sha256'}:raise ValueError('canonical C twin members required')
 for name,item in members.items():
  path=pin(base/name,inputs,item['sha256'])
  if path.stat().st_size!=item['size']:raise ValueError('base member extent differs')
 if(base/'track03.sha256').read_text().strip()!=members['track03.iso']['sha256']:raise ValueError('stale ISO digest text')
 meta=json.loads((base/'base.json').read_text());layout=dict(kind='twin',warp_lba=400,pad_lba=420,w11_lba=440,fixture_bytes=8192,gdi='3\n1 0 4 2048 track01.iso 0\n2 756 0 2352 track02.raw 0\n3 45000 4 2048 track03.iso 0\n')
 if{k:meta.get(k)for k in layout}!=layout or members['track01-template.iso']['size']!=1241088:raise ValueError('fixed twin layout differs')
 rows=checked_json(stage['fixtures']['path'],stage['fixtures']['sha256'],inputs);local=json.loads((P/'fixtures.json').read_text())
 if rows!=local or stage.get('fixture_pins')!=local or set(rows)!={'r119-census'}:raise ValueError('only exact reviewed mode1 census fixture')
 fixture=rows['r119-census'];path=pin(fixture['path'],inputs,fixture['sha256']);pin(fixture['basis_path'],inputs,fixture['basis_sha256']);pin(P/'fixtures.json',inputs)
 validate_fixture_bytes(fixture,path.read_bytes())
 pad=pin(fixture['pad_path'],inputs,PAD_SHA);pin(fixture['pad_basis_path'],inputs,PAD_SHA)
 if pad.read_bytes()!=native_path(fixture['pad_basis_path']).read_bytes():raise ValueError('byte-exact retained ordinary movie input required')
 if a.stock_sha256!=STOCK_SHA:raise ValueError('exact reviewed fp_run required')
 stock=pin(a.stock,inputs,STOCK_SHA);console=pin(a.console,inputs,a.console_sha256)
 for path in (HELPER,API,COUNTER,*P.glob('*.py')):pin(path,inputs)
 for name in ('emu.cfg','read_log.py','capture_ui_vram.py'):pin(TEMPLATE/name,inputs)
 if inputs[str(TEMPLATE/'read_log.py')]!=READER_SHA or inputs[str(TEMPLATE/'capture_ui_vram.py')]!=CAPTURE_SHA:raise ValueError('actual reader/capture sources differ')
 cfg=(TEMPLATE/'emu.cfg').read_text()
 if not re.search(r'(?mi)^rend.EmulateFramebuffer\s*=\s*(yes|true|1)\s*$',cfg)or re.search(r'(?mi)^Auto(?:Load|Save)State\s*=\s*(yes|true|1)\s*$',cfg):raise ValueError('standard framebuffer/no auto-state settings required')
 for path in (TEMPLATE/'data').rglob('*'):
  if path.is_file():pin(path,inputs)
 runtime_inputs(inputs);env=checked_json(a.environment,a.environment_sha256,inputs)
 if env!=dict(RE4DC_EMU='console',RE4DC_MAX_FLYCASTS='16',RE4DC_CONSOLE_EXE=str(console),FP_NOLIMIT='1'):raise ValueError('literal console environment')
 profile_path,output,capture=profile_destinations(a.profile)
 refs={}
 for name in ('track02.raw','track03.iso'):
  src=base/name;st=src.stat();refs[str(capture/name)]=dict(source=str(src),bytes=st.st_size,inode=st.st_ino,device=st.st_dev,links_before=st.st_nlink,sha256=inputs[str(src)])
 args=['--base',str(base),'--cap',str(capture),'--syms',syms,'--warp',fixture['path'],'--pad',str(pad),'--seconds','54','--period','4','--stop',STOP,'--grace','2','--name','actor23-r119-census']
 p=dict(source=FINAL_SOURCE,integration=INTEGRATION,case='r119-census',arm='on',runtime_mode=1,observation_only=True,active_window_claim=True,output=str(output),capture=str(capture),base=str(base),syms=syms,fixture=fixture['path'],fixture_sha256=fixture['sha256'],controller_child_argv=[sys.executable,'-B',str(P/'stock_child.py'),str(profile_path)],stock_argv=args,stock_runner=str(stock),stock_sha256=inputs[str(stock)],console_source=str(console),console_sha256=inputs[str(console)],environment=env,inputs=inputs,hardlink_refs=refs,stage_receipt_sha256=a.stage_sha256,programme_receipt_sha256=stage['programme_receipt_sha256'],elf_sha256=programme['elf']['sha256'],raw_sha256=programme['raw']['sha256'],resolved_sha256=programme['resolved']['sha256'],source_seal_sha256=programme['source_seal']['sha256'],module_roster_sha256=stage['module_roster']['sha256'],kos_receipt_sha256=stage['kos_receipt']['sha256'],private_inputs_sha256=programme['private_inputs']['sha256'],ownership_audit_sha256=stage['ownership_audit']['sha256'],assets_manifest_sha256=stage['assets_manifest']['sha256'],disc_manifest_sha256=stage['disc_manifest']['sha256'],root_review=None)
 p.update(pad=str(pad),pad_sha256=PAD_SHA,normalization_seal_sha256=NORMALIZATION_SHA,passive_sampling=False,late_global_tick=539,census_workspace_binds=600,completion_flush_required=True,actual_culling_qualified=False)
 fixed_stock_contract(p)
 if a.root_review:p['root_review']=checked_json(a.root_review,a.root_review_sha256,inputs);root_review_contract(p)
 return p

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 for name in ('stage','stage-sha256','stock','stock-sha256','console','console-sha256','environment','environment-sha256','profile'):parser.add_argument('--'+name,required=True)
 parser.add_argument('--root-review');parser.add_argument('--root-review-sha256');parser.add_argument('--write',action='store_true');a=parser.parse_args();p=prepare(a);data=(json.dumps(p,indent=2)+'\n').encode()
 if len(data)>256*1024:raise ValueError('profile metadata256KiB cap')
 if a.write:
  if not a.root_review:raise ValueError('main exact review required before writing launchable census profile')
  with Path(a.profile).open('xb')as f:f.write(data)
 print(json.dumps(dict(profile=a.profile,sha256=hashlib.sha256(data).hexdigest(),written=a.write,allocated=False,observation_only=True)))
if __name__=='__main__':main()
