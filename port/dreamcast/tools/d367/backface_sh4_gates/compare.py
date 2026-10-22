"""Offline explicit-pair verifier. No launch, auto-latest selection or missing-row skip."""
import argparse,hashlib,json,pathlib,re
class Refusal(ValueError):pass
def require(v,why):
 if not v:raise Refusal(why)
def digest(path):return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()
def diff_rgb(a,b,size_a,size_b):
 require(size_a==size_b,'different framebuffer dimensions');require(len(a)==len(b)==size_a[0]*size_a[1]*3,'truncated RGB');return {'different_pixels':sum(a[i:i+3]!=b[i:i+3] for i in range(0,len(a),3)),'max_channel_delta':max((abs(x-y) for x,y in zip(a,b)),default=0)}
def ganado_burst(log,window):
 lo,hi=window;require(0<=lo<hi,'invalid explicit BFC capture interval')
 return any(lo<=int(m[1]) and int(m[2])<=hi and int(m[3])>0 for m in re.finditer(r'bfc: frame=(\d+)\.\.(\d+) .*?cls=4 v=(\d+)',log))
def memory_gate(row):
 require(row['squeeze_bytes']==49152 and row['minimum_KOS_headroom']>=4096,'KOS48KiB headroom fail')
 require(row['s30_frames']==340 and row['s30_expected']==340,'s30 incomplete')
 require(row['heap4_refusals']==0 and row['heap4_before']>0 and row['missing_symbols']==0,'heap4/symbol failure')
 return True
def evidence(arm):
 require(arm['emu']=='console','console mode required');require(arm['run_complete'] and not arm['errors'],'run not complete/clean');require(not arm['hang_or_fault'],'fault/hang witness');require(arm['capture_seconds_after_freeze']>=0 and arm['capture_seconds_after_freeze']<=30,'shot outside freeze window')
 for kind in ('resolved_knobs','preprocessed','objects','elf','program','disc_manifest','assets_manifest','fixture','log','framebuffer'):
  row=arm['artifacts'][kind];require(digest(row['path'])==row['sha256'],'artifact pin changed: '+kind)
 require('warp: frozen at tick '+str(arm['freeze_tick']) in pathlib.Path(arm['artifacts']['log']['path']).read_text(errors='replace'),'exact freeze witness missing')
 return arm
def compare(pair):
 from PIL import Image
 a,b=evidence(pair['C']),evidence(pair['ASM'])
 require(a['knobs']==dict(CPU_BACKFACE=1,ACTOR_BACKFACE=1,GAME_SH4ZAM=1),'wrong C definitions');require(b['knobs']==dict(CPU_BACKFACE=2,ACTOR_BACKFACE=1,GAME_SH4ZAM=1),'wrong ASM definitions')
 require(a['fixture']==b['fixture'] and a['freeze_tick']==b['freeze_tick'],'fixture/tick mismatch')
 for key in ('fixture','assets_manifest'):require(a['artifacts'][key]['sha256']==b['artifacts'][key]['sha256'],'unmatched '+key)
 # Declaration must be backed by main build's resolved/preprocessed/object chain; names alone never establish OFF.
 require(pair['build_chain_verified'] and pair['loaded_assets_verified'],'missing build/loaded-asset proof')
 if pair['fixture']=='close-ganado':
  for arm in (a,b):
   log=pathlib.Path(arm['artifacts']['log']['path']).read_text(errors='replace');require(re.search(r'warp: face near target m=[0-9a-f]+ placed 500 mm ahead',log),'real live Ganado placement absent');require(ganado_burst(log,arm['bfc_capture_window']),'actual Ganado burst missing in exact capture interval');require(arm['alive_class15_and_nmrs_verified'],'actual live/drawn class0x15 missing')
 x,y=(Image.open(arm['artifacts']['framebuffer']['path']).convert('RGB') for arm in (a,b));r=diff_rgb(x.tobytes(),y.tobytes(),x.size,y.size);r['passed']=r['different_pixels']==0;return r
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('pair');args=ap.parse_args();print(json.dumps(compare(json.loads(pathlib.Path(args.pair).read_text())),indent=2))
