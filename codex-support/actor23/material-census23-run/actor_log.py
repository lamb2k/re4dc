"""Actual-source log grammar; workspace serials and game ticks stay separate."""
import re
class EvidenceFailure(ValueError):pass
class MissingTelemetry(EvidenceFailure):pass

def require(ok,message):
 if not ok:raise EvidenceFailure(message)

def clean(text):
 require(not re.search(r'Out of memory|\b(?:HALT|FAULT|MISSING)\b|LOG OVERRUN|log head decreased',text),'fault, missing, OOM or lost-log evidence')

# Exact10395 tick_log.cpp slots; arbitrary pairs are never assumed avg/max.
DURATION_FIELDS=frozenset(('total setup cpu end remain logic trans post wopq wxlu wshell wall '
 'CamCtrl.Check ScenarioMove EmMgr.move Player ObjMgr.move CameraMove EspMove LightMove '
 'TaskScheduler EspTrans ShadowTrans MirrorTrans ClothTrans objTrans SndWatcher').split())
VERTEX_FIELDS=frozenset(('vopq','vxlu','vshell'))
COUNTER_FIELDS={'rotcache':('window_delta_counts',('hits','misses')),'pwcdiag':('cumulative_counts',('checks','mismatches'))}

def timing_rows(text):
 rows=[]
 for raw in text.splitlines():
  if not raw.startswith('PT '):continue
  match=re.fullmatch(r'PT f=(\d+)-(\d+) n=(\d+)(?: (.*))?',raw);require(match is not None,'malformed PT header')
  first,last,n=map(int,match.groups()[:3]);require(n>0 and last>=first,'invalid PT game-tick range')
  fields={};counters={};unclassified=[];seen=set()
  for token in(match.group(4)or'').split():
   name,separator,value=token.partition('=')
   if name not in DURATION_FIELDS|VERTEX_FIELDS|COUNTER_FIELDS.keys():
    unclassified.append(dict(name=name if separator else None,raw_value=value if separator else None,raw=token));continue
   require(name not in seen,'duplicate known PT field');seen.add(name)
   if name in COUNTER_FIELDS:
    require(re.fullmatch(r'\d+/\d+',value)is not None,'malformed known PT counter pair')
    values=list(map(int,value.split('/')));require(all(v<=0xffffffff for v in values),'PT counter outside source unsigned range')
    kind,labels=COUNTER_FIELDS[name];counters[name]=dict(kind=kind,values=dict(zip(labels,values)),raw=token)
   else:
    require(re.fullmatch(r'\d+/\d+(?:/\d+)?',value)is not None,'malformed known PT statistics')
    values=list(map(int,value.split('/')));avg,maximum=values[:2];samples=values[2]if len(values)==3 else n
    require(all(v<=0xffffffff for v in values)and maximum>=avg and samples>0,'invalid known PT mean/max/sample count')
    fields[name]=dict(kind='duration_statistics'if name in DURATION_FIELDS else'vertex_count_statistics',unit='us'if name in DURATION_FIELDS else'vertices',avg=avg,max=maximum,samples=samples,samples_explicit=len(values)==3,raw=token)
  rows.append(dict(game_tick_first=first,game_tick_last=last,n=n,fields=fields,counters=counters,unclassified_fields=unclassified,raw=raw))
 return rows

def observe(result,text):
 clean(text)
 require(result.get('status')=='RUN_COMPLETE'and result.get('emu')=='console'and result.get('seconds')==54 and not result.get('errors'),'stock observer not a clean exact54 console run')
 require('stopped'not in result and type(result.get('reader_exit'))is int and result['reader_exit']==0 and 'early_emulator_exit'not in result and not result.get('checkpoint_close_timeout'),'exact stock natural reader_exit0 required; no goal or emulator early exit')
 require(54<=result.get('elapsed_s',0)<=59.5,'observer reader elapsed outside original bound')
 ends=re.findall(r'^\[end: head=(\d+) stage=(None|\d+) overruns=(\d+)\]$',text,re.M);stops=re.findall(r'^\[capture stop reason=([^ ]+) elapsed=([0-9]+\.[0-9]{3})\]$',text,re.M)
 require(len(ends)==len(stops)==1 and ends[0][2]=='0'and stops[0][0]=='deadline'and 54<=float(stops[0][1])<=59.5,'exact full reader deadline/zero overrun markers required')
 require(re.findall(r'^warp: room enter ([0-9a-f]{3}) \(#\d+\)',text,re.M)==['119'],'cold r119 entry not established')
 require(not re.search(r'^AV23(?: |WORK |WINDOW )',text,re.M),'mode0 observer must not activate a late window')
 rows=timing_rows(text)
 if not any(r['fields'].get('vopq',{}).get('max',0)>0 for r in rows):raise MissingTelemetry('no positive actual WORLD_METER world contribution sample')
 return dict(status='MODE0_OBSERVATION_RECORDED',observation_only=True,active_window_gate=False,actor_hiding_gate=False,actual_camera_qualified=False,actual_late_global_tick=None,actual_goto_room_PAD_tick=None,pre_skin_savings_claim=False,pixel_parity_gate=False,whole_frame_timing_claim=False,PT_game_tick_samples=rows,alive_rows=re.findall(r'^warp: (?:alive|alivelist)[^\n]*$',text,re.M),scope='Raw whole-iteration/tick costs are retained. Flycast console mode is not physical-console timing; no active-window cost alignment or whole-frame gain is inferred.')

AV=r'AV23 frame=(\d+) mode=(\d+) n=(\d+) query=(\d+) sections=(\d+) wall=(\d+) hidden=(\d+) bound=(\d+) would=(\d+) skip=(\d+) tri=(\d+) xf=(\d+)'
WORK=r'AV23WORK frame=(\d+) groups=(\d+) hit=(\d+) miss=(\d+) scan=(\d+) material=(\d+) identity=(\d+) numeric=(\d+) capacity=(\d+) reset=(\d+) world_ok=(\d+) world_draw=(\d+) metadata_checks=(\d+) metadata_bytes=(\d+)'
WINDOW=r'AV23WINDOW event=(\d+) frame=(\d+) mode=(\d+) mask=([0-9a-f]+) left=(\d+) once=1 metadata_checks=(\d+) metadata_bytes=(\d+)'

def window(text,mode):
 clean(text);require(mode in(0,1,2),'exact source-supported mode required')
 lines=text.replace('\r\n','\n').splitlines();events=[];pairs=[];pending=None
 for line in lines:
  if line.startswith('AV23WINDOW '):
   m=re.fullmatch(WINDOW,line);require(m is not None,'malformed source window row');a=m.groups();events.append(dict(event=int(a[0]),frame=int(a[1]),mode=int(a[2]),mask=int(a[3],16),left=int(a[4]),metadata_checks=int(a[5]),metadata_bytes=int(a[6]),position=len(pairs)))
  elif line.startswith('AV23 '):
   require(pending is None,'missing paired AV23WORK row');m=re.fullmatch(AV,line);require(m is not None,'malformed AV23 row');pending=dict(zip(('frame','mode','n','query','sections','wall','hidden','bound','would','skip','tri','xf'),map(int,m.groups())))
  elif line.startswith('AV23WORK '):
   m=re.fullmatch(WORK,line);require(m is not None and pending is not None,'orphan/malformed actual work row');work=dict(zip(('frame','groups','hit','miss','scan','material','identity','numeric','capacity','reset','world_ok','world_draw','metadata_checks','metadata_bytes'),map(int,m.groups())));require(work['frame']==pending['frame'],'source/work serial mismatch');pairs.append(dict(actor=pending,work=work));pending=None
 require(pending is None and len(events)==2 and len(pairs)==600,'one complete600-bind window and paired work rows required')
 start,end=events;mask=[0,32,64][mode]
 require((start['event'],start['mode'],start['mask'],start['left'],start['position'])==(1,mode,mask,599,0),'wrong once-only actor window start')
 require((end['event'],end['mode'],end['mask'],end['left'],end['position'])==(3,0,mask,0,600),'complete mode0 restoration required; cancel/invalid is not completion')
 for index,pair in enumerate(pairs,1):
  a,w=pair['actor'],pair['work'];require(a['n']==index and a['mode']==mode,'wrong mode or skipped/duplicate bind count')
  require(index==1 and a['frame']==start['frame']or index>1 and a['frame']>pairs[index-2]['actor']['frame'],'workspace serial order invalid')
  if mode<2:require(a['skip']==a['tri']==0,'OFF/census must not skip preparation')
  if mode==0:require(all(a[key]==0 for key in ('query','sections','wall','hidden','bound','would','skip','tri')),'OFF must retain disabled actor-query behavior')
  if a['skip']or a['tri']:require(mode==2 and a['would']>=a['skip']and a['hidden']>0 and w['world_ok']>0,'actual preskin skip lacks same-bind contributing-world receipt')
 require(end['frame']>pairs[-1]['actor']['frame'],'completion boundary must follow finalbind')
 require(end['metadata_checks']>=start['metadata_checks']and end['metadata_bytes']>=start['metadata_bytes'],'metadata counters decreased/wrapped')
 totals={key:sum(p['actor'][key]for p in pairs)for key in ('query','sections','wall','hidden','bound','would','skip','tri','xf')};work_totals={key:sum(p['work'][key]for p in pairs)for key in pairs[0]['work']if key!='frame'}
 for event in events:event['workspace_serial']=event['frame']
 for pair in pairs:pair['workspace_serial']=pair['actor']['frame']
 return dict(status='SOURCE_WINDOW_LOG_CONTRACT_COMPLETE',workspace_binds=600,drawn_frames_claim=False,selected_mode=mode,restored_mode=0,actual_preskin_skip_records=totals['skip'],actor_totals=totals,work_totals=work_totals,window_events=events,raw_work_pairs=pairs,PT_game_tick_samples=timing_rows(text),clock_interpretation=dict(AV23_frame_raw='owner workspace-bind serial, including crowd Trans; explicit workspace_serial alias supplied',PT_f='game-tick serial range',late='explicit observed global game tick',goto='separate observed room PAD tick'),metadata_scope='Cumulative source counters retained; no blanket601/602 bound. Source synthetic case602checks/828352B is an example, not a cap on pre-admission refusals.',whole_frame_gain_gate=False,camera_and_guarded_scene_gates=False,scope='No numerical join between workspace serial and PT game tick. Partial/opening/movement/destruction/material and matched pixel gates require separate actual main-reviewed evidence.')
