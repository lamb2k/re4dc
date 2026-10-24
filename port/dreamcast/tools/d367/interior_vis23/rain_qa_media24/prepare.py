"""Read-only binding of completed QA programmes/assets/old route. Never stages."""
from pathlib import Path
import hashlib,json,shutil,sys
HERE=Path(__file__).resolve().parent
C=HERE.parent.parent
OLD=C/'gc-motion24/qa-memory-media-prep'
E=Path('/mnt/c/Flycast-Evidence/re4-dreamcast')
SOURCE='8ce5ee2d00027268c3e69c9c300b819c1b14c63f'
def row(p):
 p=Path(p)
 with p.open('rb') as f:h=hashlib.file_digest(f,'sha256').hexdigest()
 return {'size':p.stat().st_size,'sha256':h}
def read(p):return json.loads(Path(p).read_bytes())
def emit(p,x):
 with Path(p).open('x') as f:json.dump(x,f,indent=2);f.write('\n')
def main():
 assert not (HERE/'PLAN.json').exists()
 final=E/'rain-diag24-20261024/qa-media-8ce-v1';work=Path('/root/probe/rain-diag24-qa-media-v1')
 assert not final.exists() and not work.exists()
 B=C/'rain-diag24/qa-final-8ce-independent-readback-v1';binding=B/'CANARY-BINDING.json';assert row(binding)['sha256']=='20036ec10222b8112c9273ccb2fa99fcb0f7f066e66f604c264d6ee1f25b23bc'
 assert row(B/'SOURCE-SEAL.json')['sha256']=='47724a51342e7bf0bcc06d0bf0f6789677cd4720c59b951aab01130fc18d4cee'
 b=read(binding);assert b['source']==SOURCE
 original=read(HERE/'CURRENT-CANDIDATE-MANIFEST.json');assert row(HERE/'CURRENT-CANDIDATE-MANIFEST.json')['sha256']=='4d07e720300fcd72ae1081a00fe6a702331983ed2e8af4fdfadb0346691a726a'
 old=read(OLD/'MEDIA-PLAN.json');assert row(HERE/'SOURCE-IP.BIN')==old['sourceIP']
 roots={a:E/('rain-diag24-20261024/qa-off-8ce-v3-interrupted-on-v1' if a=='off' else 'rain-diag24-20261024/qa-on-8ce-continuation-v1')/a for a in ['off','on']}
 inputs={str(binding):row(binding),str(B/'SOURCE-SEAL.json'):row(B/'SOURCE-SEAL.json'),str(B/'READBACK.json'):row(B/'READBACK.json')}
 programmes={};expected={};syms={}
 for arm in ['off','on']:
  programmes[arm]={}
  for n,pin in b['arms'][arm]['programmes'].items():
   p=roots[arm]/n;r=row(p);assert r=={'size':pin['bytes'],'sha256':pin['sha256']};programmes[arm][n]=r;inputs[str(p)]=r
  assert len(programmes[arm])==16 and len([n for n in programmes[arm] if n.endswith('.ovl')])==14
  ss={x['name']:x['value'] for x in b['arms'][arm]['symbols']};syms[arm]=' '.join(hex(ss[n]-0x8c000000) for n in ['_re4dc_logbuf','_re4dc_log_head','_re4dc_stage'])
  exp=dict(original);exp['1ST_READ.BIN']=programmes[arm]['program.bin']
  exp.update({'dc/'+n:p for n,p in programmes[arm].items() if n.endswith('.ovl')})
  exp.update({'dc/'+n+'.txt':{'size':8192,'sha256':hashlib.sha256(bytes(8192)).hexdigest()} for n in ['warp','padscript','w11']})
  emit(HERE/(arm.upper()+'-EXPECTED-MANIFEST.json'),exp);expected[arm]=exp
 allowed=sorted({k for k in set(original)|set(expected['off']) if original.get(k)!=expected['off'].get(k)})
 assert len(allowed)==18
 assert {k for k in expected['off'] if expected['off'][k]!=expected['on'][k]}==set(allowed)-{'dc/warp.txt','dc/padscript.txt','dc/w11.txt'}
 fixture=Path(old['assets']['read_only_fixture']);assets={k:v for k,v in original.items() if k not in allowed};assert len(assets)==1697
 for k,pin in assets.items():
  assert not (fixture/k).is_symlink() and row(fixture/k)==pin,k
 hist=E/'water-rain24/rain-bca44-console55-20261024/captures'
 fixtures={}
 for typ in ['warp','pad']:
  f=hist/'off-r10c-view-v1'/('fixture-'+typ+'.txt');other=hist/'on-r10c-view-v1'/f.name
  assert f.read_bytes()==other.read_bytes()
  inputs[str(f)]=row(f);inputs[str(other)]=row(other);fixtures[typ]={'path':str(f),'identity':row(f)}
 T=Path('/dev/shm/gc-motion24-qa-memory-v2-dbqczoc8/off/source/port/dreamcast/tools/d367')
 paths={'python':Path('/mnt/c/Users/lambd/AppData/Local/Programs/Python/Python312/python.exe'),'bound':C/'stat-bytes23/census-bound-run.py','harness':T/'fullplay/fp_run.py','stat3':C/'stat-bytes23/stat-guest-slot.sh','trace16':T/'trace_lock.sh','console':E/'flycast-console-bin/flycast-console.exe'}
 tools={n:{'path':str(p),'identity':row(p)} for n,p in paths.items()}
 for p in paths.values():inputs[str(p)]=row(p)
 P=C/'gc-motion24/pillow-isolated-prep-v1';assert row(P/'SOURCE-SEAL.json')['sha256']=='3bcff1c5a4eb7f5823296be065c097a246251ffd3c3d3d42ecf11073eeb7add2'
 for n,pin in read(P/'SOURCE-SEAL.json')['members'].items():assert row(P/n)==pin
 inputs[str(P/'SOURCE-SEAL.json')]=row(P/'SOURCE-SEAL.json');inputs[str(P/'pillow_launcher.py')]=row(P/'pillow_launcher.py')
 for p in ['/usr/bin/genisoimage','/usr/bin/python3',T/'fullplay/fp_master.sh',T/'fullplay/fp_iso.py',E/'d367-harness-par/capture_ui_vram.py',E/'d367-harness-par/read_log.py',E/'d367-harness-par/emu.cfg']:inputs[str(p)]=row(p)
 for name in ['filter06.cpp','espgen44.cpp']:
  p=Path('/dev/shm/rain8ce-qa-on-cont-v1-eyihqhpk/on/source/src/game')/name;inputs[str(p)]=row(p)
 plan={'status':'PREPARED_ONLY_NO_STAGE_GUEST_SDK','source':SOURCE,'programme_roots':{a:str(p) for a,p in roots.items()},'programmes':programmes,'syms':syms,'input_pins':inputs,'official_tools':{n:row(HERE/n) for n in ['official_fp_iso.py','official_fp_master.sh']},'genisoimage':row('/usr/bin/genisoimage'),'host_python':row('/usr/bin/python3'),'sourceIP':row(HERE/'SOURCE-IP.BIN'),'assets':old['assets'],'allowed_differences':allowed,'base_paths':{a:str(final/('base-'+a)) for a in ['off','on']},'work_paths':{a:str(work/a) for a in ['off','on']},'capacity':{'C_admission_bytes':26*1024**3,'C_floor_bytes':24*1024**3,'absolute_C_floor_bytes':20*1024**3,'owned_cap_bytes':4*1024**3,'logical_estimate_bytes':2*sum(v['size'] for v in expected['on'].values())+2*sum(v['size'] for v in original.values())+64*1024**2},'tools':tools,'pillow_launcher':str(P/'pillow_launcher.py'),'pillow_seal':row(P/'SOURCE-SEAL.json'),'fixtures':fixtures,'observation':{'held':0,'fragment':0,'harness_seconds':45,'child_seconds':55,'period':25,'lane_guests':1,'root_slots':3,'global_slots':16,'FP_NOLIMIT':'1','RE4DC_EMU':'console','rain_record_ON_offset':0x36c740,'record_bytes':128,'sample_period_ms':100,'observation_byte_cap':4*1024**2,'physical_cache_proof':False},'separate_48KiB_gate':{'status':'NOT_ALLOCATED_NOT_IMPLEMENTED','held':49152,'frag':[0,1],'requires':'separate matched held fixture/profile, stage/guest allocation; held0 never proves held48K gate'},'no_H2':True,'PRUNE_AUTO':0,'stage_ext4':0}
 assert plan['capacity']['logical_estimate_bytes']<4*1024**3
 emit(HERE/'PLAN.json',plan)
 print(json.dumps({'assets':len(assets),'programmes_per_arm':16,'syms':syms,'estimate':plan['capacity']['logical_estimate_bytes'],'plan':row(HERE/'PLAN.json')},indent=2))
if __name__=='__main__':main()
