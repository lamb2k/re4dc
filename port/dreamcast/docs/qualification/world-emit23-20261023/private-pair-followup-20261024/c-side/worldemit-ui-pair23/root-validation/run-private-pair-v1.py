"""Root-private matched trace pair. Uses unchanged strict gates, records failure.
One added PS2 texture is the sole data delta; production unchanged.
"""
from pathlib import Path
import importlib.util,json,os,subprocess,fcntl,copy,hashlib
HERE=Path(__file__).resolve().parent
GATE=HERE.parent.parent/'world-emit23/current-gates/current_gates_root_v1.py'
spec=importlib.util.spec_from_file_location('current',GATE);g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
E=g.E;RESULT=E/'private-ps2-hair-v1-stage.json'
def main():
 stage=g.jsonread(RESULT);assert stage['stage_success'] and stage['sole_asset_change']=='dc/tex/7/7d4e1e92-052bdc2e.re4tex'
 assert stage['root_helper']['sha256']==g.sha(HERE/'stage-private-v1.py')
 assert g.sha(GATE)=='1861ed9e055c6d6c2a356360257775a51b22800e22a1562d36d4f5c5c93515ae'
 done=[]
 with (E/'root-worker.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX)
  for arm in ['control','candidate']:
   g.floor();u=g.inspect('B','t');assert u==stage['unit']
   cmd,cap,fix=g.command('B','mendez','B-mendez-ps2hair-'+arm+'-r1',u);assert not cap.exists()
   base=E/'_discs'/('B-t' if arm=='control' else 'B-t-ps2hair-v1')
   if arm=='control':media=g.check_base(base,u)
   else:
    assert g.sha(base/'track03.iso')==stage['track03']['sha256']
    assert g.sha(base/'base-manifest.json')==stage['staged_manifest']['sha256']
    media={'base':str(base),'track03_sha256':stage['track03']['sha256'],'base_manifest_sha256':stage['staged_manifest']['sha256'],'sole_asset_addition':stage['sole_asset_change']}
   cmd[cmd.index('--base')+1]=g.win(base);cmd[cmd.index('--period')+1]='1';fix['period']=1
   receipt={'unit':u,'staged':media,'private_data_option':'MENDEZ_PS2_PAIR23_PRIVATE','enabled':arm=='candidate','gate':'mendez','arm':arm,'fixtures':fix,'command':cmd,'script_sha256':g.sha(Path(__file__)),'stage_receipt_sha256':g.sha(RESULT),'look_approved':False,'guard_order':['root-worker','stat3','trace16','exact-child55']}
   g.fresh_json(E/'launches'/('private-hair-'+arm+'-r1.json'),receipt)
   env=dict(os.environ,RE4DC_EMU='console',RE4DC_MAX_FLYCASTS='16',FP_NOLIMIT='1',TRACE_SLOTS='16',TRACE_LOCK_OWNER='root-private-mendez-'+arm,RE4DC_CONSOLE_EXE=r'C:\Flycast-Evidence\re4-dreamcast\flycast-console-bin\flycast-console.exe')
   for k in ['RE4DC_GD_PROFILE','RE4DC_GD_JITTER','RE4DC_GD_SEED']:env.pop(k,None)
   env['WSLENV']=':'.join(filter(None,[env.get('WSLENV',''),'RE4DC_EMU','RE4DC_MAX_FLYCASTS','FP_NOLIMIT','RE4DC_CONSOLE_EXE']))
   with (E/'launches'/('private-hair-'+arm+'-r1.log')).open('x') as log:p=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT)
   assert cap.exists(),'No capture; preserve launcherlog'
   g.fresh_json(cap/'current-gate-launch.json',receipt)
   reference=(E/'captures/B-mendez-ps2hair-control-r1') if arm=='candidate' else None
   result=g.judge(cap,'mendez','B',reference,p.returncode)
   run=g.jsonread(cap/'run-result.json');assert g.recorded_track_matches(run,g.win(base),media['track03_sha256'])
   assert run['fixtures']['warp']['sha256']==fix['warp']['sha256'] and run['fixtures']['pad']['sha256']==fix['pad']['sha256']
   assert result['exact_console_image_verified'] and result['exact_harness_verified']
   done.append({'arm':arm,'capture':str(cap),'result':result,'elapsed_s':run.get('elapsed_s'),'actual_media_verified':True})
   print(json.dumps({'arm':arm,'strict_pass':result['pass'],'critical':result['critical'],'observed':result['observed']}),flush=True)
 g.fresh_json(E/'private-ps2-hair-matched-trace-r1.json',{'source':g.SOURCE,'programme':stage['unit']['programme'],'arms':done,'scope':'Private one-file PS2 material candidate. Strict route checks, bounded console emulator only; snapshots not yet matched or reviewed. No hardware, production or look acceptance.'})
if __name__=='__main__':main()