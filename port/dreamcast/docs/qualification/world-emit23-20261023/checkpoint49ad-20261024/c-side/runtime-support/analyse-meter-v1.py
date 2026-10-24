"""Frozen qualification capture verifier; complete common PT windows, modelled only."""
import argparse,hashlib,json,pathlib,re,sys,statistics
FROZEN='7a3af776ff8c14070f96272cd48074e5895d0490'
ARM_FLAGS={'R':(0,0),'L':(1,0),'E':(0,1),'B':(1,1)}
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def inspect(root,arm,scene):
 tag='q2' if scene=='b1' and arm in 'RL' else 'q1'
 cap=root/'runtime-support'/f'{arm}-m-{scene}-{tag}'
 text=(cap/'run-output.txt').read_text(errors='replace')
 launch=json.loads((cap/'bounded-launch.json').read_text()); result=json.loads((cap/'run-result.json').read_text())
 assert not launch['deadline_fired'] and launch['guest_exited'] and launch['guest_observed_elapsed_s']<=55,launch
 assert result['status']=='RUN_COMPLETE' and not result['errors'],result
 assert result['reader_exit']==0 and result['seconds']==40 and result['emu']=='console',result
 fixture=(cap/'fixture-warp.txt').read_bytes().replace(bytes([13]),b'')
 assert hashlib.sha256(fixture).hexdigest()==result['fixtures']['warp']['sha256']
 assert launch['expected_executable_sha256']==sha(cap/'flycast.exe')
 assert not re.search(r'WEC23 ',text),'census in timing capture'
 bad_events=[(k,int(v)) for k,v in re.findall(r'\b(fallback|aborts|refusals|refused)=(\d+)',text) if int(v)]
 assert not bad_events,('nonzero reported fallback/abort/refusal',bad_events)
 room='101' if scene=='b1' else '100'
 assert f'warp: start room={room} next_room={room} ' in text,'wrong/missing warp room'
 assert 'quality: titleExit mode=standard source=default features=00000001 lod_px=5' in text,'runtime quality'
 knobs=dict(x.split('=',1) for x in (root/'identities'/f'{arm}-m-resolved-knobs.txt').read_text().splitlines() if '=' in x)
 expected={'SCENERY_SELECT_LEAN2':str(ARM_FLAGS[arm][0]),'SCENERY_EMIT_PREFETCH':str(ARM_FLAGS[arm][1]),'SCENERY_EMIT_CENSUS':'0','WORLD_METER':'1','GAME_TICK_LOG':'60','PHASE_METER':'1','PC_SAMPLER':'0','PS2_PVS':'0','SCENERY_SUBMIT_BATCH':'1','SCENERY_SELECT_ONLY':'1','SCENERY_REPLAY_LEAN':'1','SCENERY_UV_SNAPSHOT':'0','SCENERY_DEDUP':'0','SCENERY_FAR_LOD':'4','QUALITY_LOD_PX':'5','R101_ALIVE_CAP':'4','ACTOR_SETUP_LEAN':'0','CPU_BACKFACE':'0','ACTOR_BACKFACE':'0'}
 for k,v in expected.items():assert knobs.get(k)==v,(arm,k,knobs.get(k),v)
 assert (root/'identities'/f'{arm}-m-stack.txt').read_text().splitlines()[0]==FROZEN
 windows={}
 for line in text.splitlines():
  match=re.match(r'PT f=(\d+)-(\d+) n=(\d+)(.*)$',line)
  if not match:continue
  first,last,n=map(int,match.group(1,2,3)); key=(first,last,n)
  fields=windows.setdefault(key,{})
  for token in match.group(4).split():
   k,v=token.split('=',1)
   assert k not in fields,('duplicate PT field',key,k)
   fields[k]=list(map(int,v.split('/')))
 valid={}
 for key,fields in windows.items():
  first,last,n=key
  if first<300 or last>=1140:continue
  assert n==60 and last-first+1==n,(key,'noncomplete tick range')
  assert all(k in fields for k in ('wopq','wxlu','wshell','wall','total','setup','cpu','logic','trans','post','rotcache')),(key,'partial PT log record')
  assert all(len(fields[k])==2 for k in ('wopq','wxlu','wshell','wall','total','setup','cpu','logic','trans','post')),('subset slot',key)
  valid[key]=fields
 assert valid,'no complete PT windows'
 alives=[int(x) for x in re.findall(r'warp: alive (\d+) room '+room+r' frame \d+',text)]
 if scene=='b1':assert alives and max(alives)<=4,('cap4 violation',alives)
 return {'cap':str(cap),'log_sha256':sha(cap/'run-output.txt'),'result':result,'launch':launch,'runtime_lod_px':5,'far_lod_multiplier':4,'effective_scenery_tolerance':20,'alive_samples':alives,'windows':valid}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('root');a=ap.parse_args();root=pathlib.Path(a.root)
 out={'source':FROZEN,'claim':'MODELLED Flycast console-mode PT readings only; no physical-console speed or image gate','window_rule':'whole common 60-tick PT windows entirely inside [300,1140); all wrapped PT fields present','scenes':{}}
 for scene in ('b1','s2'):
  captures={arm:inspect(root,arm,scene) for arm in ARM_FLAGS}
  keys=sorted(set.intersection(*(set(v['windows']) for v in captures.values())))
  assert keys,('no common complete PT windows',scene)
  assert all(b[0]==a[1]+1 for a,b in zip(keys,keys[1:])),('noncontiguous common windows',keys)
  ticks=sum(k[2] for k in keys); rows={}
  for arm,c in captures.items():
   fields={k:sum(c['windows'][w][k][0]*w[2] for w in keys)/ticks/1000 for k in ('wopq','wxlu','wshell','wall','total','setup','cpu','logic','trans','post')}
   fields['world']=fields['wopq']+fields['wxlu']+fields['wshell']
   samples=[sum(c['windows'][w][k][0] for k in ('wopq','wxlu','wshell'))/1000 for w in keys]
   rows[arm]={'means_ms_per_tick':fields,'world_window_means_ms':samples,'world_window_stdev_ms':statistics.stdev(samples) if len(samples)>1 else 0,**{k:v for k,v in c.items() if k!='windows'}}
  r,l,e,b=(rows[x]['means_ms_per_tick']['world'] for x in 'RLEB')
  out['scenes'][scene]={'windows':[list(w) for w in keys],'ticks':ticks,'rows':rows,'world_delta_ms':{'L-R':l-r,'E-R':e-r,'B-R':b-r,'B-L-E+R':b-l-e+r}}
 launches=sorted((v['launch']['guest_started_monotonic'],v['launch']['guest_started_monotonic']+v['launch']['guest_observed_elapsed_s'],arm,scene) for scene in out['scenes'] for arm,v in out['scenes'][scene]['rows'].items())
 assert all(b[0]>=a[1] for a,b in zip(launches,launches[1:])),('owned guest overlap',launches)
 out['owned_meter_guests_disjoint']=True
 dest=root/'runtime-support'/'meter-summary.json';dest.write_text(json.dumps(out,indent=2)+'\n');print(dest)
 for scene,s in out['scenes'].items():print(scene,s['ticks'],{a:round(v['means_ms_per_tick']['world'],6) for a,v in s['rows'].items()},s['world_delta_ms'])
if __name__=='__main__':main()