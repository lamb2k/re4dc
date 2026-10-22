"""Pure no-I/O controller engine. Every action requires a fresh exact-bound sample.
Caller alone owns native posts and releases; no game-memory-write API.
"""
import importlib.util,pathlib
_spec=importlib.util.spec_from_file_location('policies',pathlib.Path(__file__).with_name('policies.py'));policy=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(policy)

class Shooting:
 def __init__(self):self.stage='wait';self.held=set();self.until=0;self.baseline=None;self.shots=[];self.stable=set();self.last=None;self.done=False;self.started=False
 def release(self,reason):
  out=[{'up':k,'reason':reason} for k in sorted(self.held)];self.held.clear();return out
 def step(self,row,age,elapsed):
  out=[]
  if elapsed>=40.75:self.done=True;return self.release('41s input cutoff margin')
  fresh=0<=age<=.2 and policy.valid_sample(row)
  if not fresh:
   self.stage='withheld';self.done=self.started;return self.release('stale/missing/noncoherent sample')
  if row['global']['player_life']<=0:self.done=True;return self.release('authentic death; no rollback')
  safe=policy.ordinary_weapon_ready(row) and row['global']['room']==0x103 and row.get('qa_flags')==0
  if not safe:
   self.stable.clear();self.stage='withheld';self.done=self.started;return self.release('not ordinary early freeplay/ammo gate')
  if self.done:return []
  frame=row['global']['frame']
  if self.stage in ('wait','withheld'):
   self.stable.add(frame)
   if len(self.stable)<4:return []
   self.started=True;self.baseline=row;self.stage='aim';self.until=elapsed+.4;self.held.add('rtrig');return [{'down':'rtrig','source_frame':frame,**({'capture':'before-shot'} if not self.shots else {})}]
  if elapsed<self.until:return []
  if self.stage=='aim':
   self.stage='fire';self.until=elapsed+.15;self.held.add('a');return [{'down':'a','source_frame':frame}]
  if self.stage=='fire':
   self.held.discard('a');self.stage='settle';self.until=elapsed+.65;return [{'up':'a','source_frame':frame}]
  if self.stage=='settle':
   result=policy.discharge(self.baseline,row);self.shots.append(result);out=self.release('shot settled');out.append({'proof':result,'before':self.baseline,'after':row,'capture':'after-shot'})
   if not result['accepted'] or len(self.shots)>=2:self.done=True;self.stage='complete' if all(s['accepted'] for s in self.shots) else 'unqualified';return out
   self.stage='wait';self.stable.clear();return out
  return []

class Cinematic:
 def __init__(self):self.held=set();self.b_count=0;self.until=0;self.last_b=-100;self.seen=set();self.done=False
 def release(self,reason):
  out=[{'up':k,'reason':reason} for k in sorted(self.held)];self.held.clear();return out
 def step(self,row,age,elapsed,manual_log=False):
  if elapsed>=40.75:self.done=True;return self.release('41s input cutoff margin')
  if not 0<=age<=.2 or not policy.valid_sample(row):return self.release('stale/missing/noncoherent')
  out=[]
  if 'b' in self.held and elapsed>=self.until:out+=self.release('manual B released');self.last_b=elapsed
  g=row['global'];p=row['player']
  manual=manual_log and g['room']==0x101 and g['player_life']>0 and g['rno'][:2]==[3,0] and row.get('subscreen_type')==64 and row.get('ssloop')==1 and row.get('qa_flags')==0 and p['rno'][0]==0
  if not manual and self.held:out+=self.release('manual context ended; no further B')
  if manual and not self.held and self.b_count<2 and elapsed-self.last_b>=1:
   self.b_count+=1;self.held.add('b');self.until=elapsed+.15;out.append({'down':'b','source_frame':g['frame'],'reason':'original PlayingManual2 only'})
  # Capture intents are evidence requests, never gameplay input/skip/mash.
  if row.get('manager_valid'):
   for actor in row.get('actors',[]):
    reciprocal=actor.get('dmgType_bits')==p['ptr'] and p.get('dmgType_bits')==actor.get('ptr')
    if reciprocal and actor.get('id')==0x15 and actor.get('type')==4:
     key=('catch',actor['ptr'],actor['serial'],tuple(actor['rno']),tuple(p['rno']))
     if key not in self.seen and 'catch-screenshot' not in self.seen:self.seen.add(key);self.seen.add('catch-screenshot');out.append({'capture':'reciprocal-catch','state':row,'actor_identity':{k:actor[k] for k in ('ptr','serial','id','type')},'inference':'routine-state witness; motion number/pixels need review'})
  for label,condition in [('life-zero',g['player_life']==0),('demo-transition',g['rno'][0]==4),('continue-UI',row.get('continue_ui_observed') is True)]:
   if condition and label not in self.seen:self.seen.add(label);out.append({'capture':label,'state':row})
  return out

class Door:
 def __init__(self):self.held=set();self.until=0;self.attempts=0;self.done=False
 def release(self,reason):
  out=[{'up':k,'reason':reason} for k in sorted(self.held)];self.held.clear();return out
 def step(self,row,age,elapsed):
  import math
  if elapsed>=40.75:self.done=True;return self.release('41s input cutoff')
  if not 0<=age<=.2 or not policy.valid_sample(row):return self.release('missing/stale/coherence')
  g=row['global']
  if g['player_life']<=0:self.done=True;return self.release('authentic death')
  if g['room']!=0x103:self.done=True;return self.release('original room transition; no further navigation')
  if not policy.free_play(row) or row.get('qa_flags')!=0:return self.release('original event/UI; withhold navigation')
  if self.held:
   if elapsed<self.until:return []
   return self.release('bounded normal movement complete')
  if self.done:return []
  px,_,pz=row['player']['pos'];yaw=row['player']['ang'][1];dx=-49731-px;dz=7670-pz;err=(math.atan2(dx,dz)-yaw+math.pi)%(2*math.pi)-math.pi
  if abs(err)>.15:key='turnleft' if err>0 else 'turnright';hold=min(.65,abs(err)/2.25)
  elif px<-48300 and 5800<pz<9500:
   if self.attempts>=4:self.done=True;return [{'unqualified':'ordinary door needs review'}]
   key='a';hold=.2;self.attempts+=1
  else:key='fwd';hold=min(.5,math.hypot(dx,dz)/1900)
  self.held.add(key);self.until=elapsed+hold;return [{'down':key,'reason':'retained ordinary r103 door route','source_frame':g['frame']}]
