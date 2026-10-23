"""One exact census, only after main's explicit --execute and fresh admission."""
from pathlib import Path
import argparse,hashlib,json,os,shutil,subprocess,sys
import runner_contracts as c
TREE='/root/probe/codex-actor-visibility23-eligibility-witness-integration'
STOCK_SHA='646bd4eb42ff2063d4e07dc3754ab0c0d61e3b75348b934a48e7f63a25a07747'
TRACE_SHA='e5d301a1e5888b5256feee01ab7e90b7c21633d36450691a9e9df1836e913688'

def source_clean():
 script="import pathlib,subprocess,json;t="+repr(TREE)+";p=pathlib.Path(t+'/port/dreamcast/game/obj');g=lambda a:subprocess.check_output(['git','-C',t]+a,text=True);print(json.dumps(dict(head=g(['rev-parse','HEAD']).strip(),status=g(['status','--porcelain']),marker_exists=p.exists(),marker_symlink=p.is_symlink())))"
 live=json.loads(subprocess.check_output(['wsl.exe','-d','Ubuntu-24.04','-u','root','--','python3','-c',script],text=True,timeout=15))
 if live!=dict(head=c.SOURCE,status='',marker_exists=False,marker_symlink=False):raise ValueError('literal clean exact source and absent marker required')
 return live
def held_trace():
 root=Path(r'\\wsl.localhost\Ubuntu-24.04\root\probe');found=[]
 for path in root.glob('.trace.holder*'):
  text=path.read_text(errors='strict')
  if 'actor23-root-material-census23-r1' in text and 'root-native-census-bea2.py' in text:found.append(path)
 if len(found)!=1:raise ValueError('exact single census trace holder required')
 suffix=found[0].name.removeprefix('.trace.holder')
 if suffix not in ('',*(f'.{i}'for i in range(1,16))):raise ValueError('trace slot outside global16')
 lock='/root/probe/.trace.lock'+suffix
 result=subprocess.run(['wsl.exe','-d','Ubuntu-24.04','-u','root','--','flock','-n',lock,'true'],timeout=15)
 if result.returncode!=1:raise ValueError('trace holder must still have an actually locked slot')
 return str(found[0])
def review_record(stage,programme,stage_pin,processes,paths,resources_path,resources_pin):
 r=dict(source=c.SOURCE,integration=stage['integration'],case=c.CASE,stage_receipt_sha256=stage_pin,programme_receipt_sha256=stage['programme_receipt_sha256'],fixture_sha256=stage['fixture_pins'][c.CASE]['sha256'],pad_sha256='073552789fad65c4057fa83303f10ac18ff9bc00ae48f195762be982c3222ff9',normalization_seal_sha256=c.normalization_pin())
 for field in ('elf','raw','resolved','source_seal','private_inputs'):r[field+'_sha256']=programme[field]['sha256']
 for field in ('module_roster','kos_receipt','ownership_audit','assets_manifest','disc_manifest'):r[field+'_sha256']=stage[field]['sha256']
 for key in ('final_EXEC_ELF_reviewed','all14_modules_reviewed','actual_KOS_and_inline_memory_owners_reviewed','compile_preprocess_objects_link_reviewed','private_certificate_SDK_and_room_metadata_reviewed','programme_assets_ISO_readback_reviewed','native_controller_reviewed','source_literal_clean','trace_lock_held','census_mode1_only_acknowledged','census600_completion_and_flush_required','actual_cuts_pixels_and_hardware_pending'):r[key]=True
 r.update(lane_live_guests=processes['lane_live_guests'],global_live_guests=processes['global_live_guests'],capacity_reviewed_utc=processes['utc'],process_receipt=dict(path=str(paths['processes']),sha256=c.sha(paths['processes'])),resource_receipt=dict(path=str(resources_path),sha256=resources_pin))
 return r
def execute(a,resources,stage):
 if os.name!='nt':raise ValueError('Windows native controller required')
 c.validate_native_stage(stage)
 sys.path.insert(0,str(c.ADAPTER));sys.path.insert(0,str(c.LANE.parent/'world-scratch23'))
 from contain import all_guest_count
 from binding_helpers import native_path
 from bindings import verify_bound
 from root_process_census import census
 from policy import root_review_contract
 inputs={};binding=verify_bound(inputs)
 for key in ('ownership_audit','kos_receipt','module_roster'):
  c.require_bound_receipt(stage[key],binding[key],native_path)
 held_trace();source_clean()
 if shutil.disk_usage('C:/').free<resources['floor']+resources['guest_peak']:raise ValueError('C floor plus one future guest absent')
 stock=Path(r'\\wsl.localhost\Ubuntu-24.04\root\probe\codex-pvs23-build-3dd7dfe4\port\dreamcast\tools\d367\fullplay\fp_run.py');console=Path(r'C:\Flycast-Evidence\re4-dreamcast\flycast-console-bin\flycast-console.exe')
 if c.sha(stock)!=STOCK_SHA or c.sha(console)!='4a2da3a8a4562f020ae8dcfcd753e91d50a102e6d117cb06aacb320219ae9e82':raise ValueError('reviewed stock/console changed')
 for rel,pin in [('port/dreamcast/tools/d367/fullplay/fp_run.py',STOCK_SHA),('port/dreamcast/tools/d367/trace_lock.sh',TRACE_SHA)]:
  blob=subprocess.check_output(['wsl.exe','-d','Ubuntu-24.04','-u','root','--','git','-C',TREE,'show',c.SOURCE+':'+rel],timeout=15)
  if hashlib.sha256(blob).hexdigest()!=pin:raise ValueError('stock/trace differs in exact source')
 programme=c.checked(native_path(stage['programme_receipt']),c.PROGRAMME_SHA)
 processes=c.require_no_guests(census(all_guest_count))
 run=Path(a.stage).absolute().parent/'root-runs/material-census23-r1';prefix=run/c.CASE
 paths={name:prefix.with_suffix('.'+name+'.json')for name in ('profile','allocation','review','environment','processes','final-admission')}
 if any(p.exists()for p in paths.values()):raise FileExistsError('preserve previous attempt; no retry')
 # All writes and native execution are behind explicit --execute, exact stage,
 # independent reviews, live source, actual held lease and fresh admissions.
 run.mkdir(parents=True,exist_ok=True)
 env=dict(RE4DC_EMU='console',RE4DC_MAX_FLYCASTS='16',RE4DC_CONSOLE_EXE=str(console),FP_NOLIMIT='1')
 for key in list(os.environ):
  if key.startswith('RE4DC_')or key=='FP_NOLIMIT':os.environ.pop(key)
 os.environ.update(env)
 def save(path,data):
  with path.open('x')as f:f.write(json.dumps(data,indent=2)+'\n')
 save(paths['environment'],env);save(paths['processes'],processes)
 review=review_record(stage,programme,a.stage_sha256,processes,paths,a.resources,a.resources_sha256);save(paths['review'],review)
 args=[sys.executable,'-B',str(c.ADAPTER/'prepare_profile.py'),'--stage',a.stage,'--stage-sha256',a.stage_sha256,'--stock',str(stock),'--stock-sha256',STOCK_SHA,'--console',str(console),'--console-sha256',c.sha(console),'--environment',str(paths['environment']),'--environment-sha256',c.sha(paths['environment']),'--profile',str(paths['profile']),'--root-review',str(paths['review']),'--root-review-sha256',c.sha(paths['review']),'--write']
 subprocess.run(args,check=True)
 root_review_contract(json.loads(paths['profile'].read_text()))
 c.validate_resources(c.checked(a.resources,a.resources_sha256));source_clean();held_trace()
 final=c.require_no_guests(census(all_guest_count));save(paths['final-admission'],final)
 if shutil.disk_usage('C:/').free<c.FLOOR+resources['guest_peak']:raise ValueError('C floor changed before one guest')
 c.validate_native_stage(stage)
 save(paths['allocation'],dict(allocated=True,profile_sha256=c.sha(paths['profile']),controller_sha256=c.sha(c.ADAPTER/'contain.py'),attempt_limit=1,guard_seconds=59,closure_seconds=59.5))
 subprocess.run([sys.executable,'-B',str(c.ADAPTER/'launch.py'),'--profile',str(paths['profile']),'--profile-sha256',c.sha(paths['profile']),'--allocation',str(paths['allocation']),'--allocation-sha256',c.sha(paths['allocation']),'--execute'],check=True)
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for key in ('stage','stage-sha256','resources','resources-sha256','wrapper-review','wrapper-review-sha256'):p.add_argument('--'+key,required=True)
 p.add_argument('--execute',action='store_true');a=p.parse_args()
 c.verify_source(a.wrapper_review,a.wrapper_review_sha256)
 stage=c.validate_stage(c.checked(a.stage,a.stage_sha256));resources=c.validate_resources(c.checked(a.resources,a.resources_sha256))
 if not a.execute:print(json.dumps(dict(execute=False,case=c.CASE,source=c.SOURCE,programme_sha256=c.PROGRAMME_SHA,stage_sha256=a.stage_sha256,profiles_created=0,guests=0)));return
 execute(a,resources,stage)
if __name__=='__main__':main()
