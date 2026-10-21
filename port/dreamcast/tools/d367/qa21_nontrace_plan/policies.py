"""Pure source-state gates: no process, input, memory-write or emulator API."""
def valid_sample(row):
 g=row.get('global') or {};p=row.get('player') or {}
 if row.get('valid') is False or row.get('coherent') is False:return False
 return isinstance(g.get('player_life'),int) and isinstance(g.get('frame'),int) and isinstance(g.get('room'),int) and bool(p.get('ptr')) and len(p.get('pos',[]))==3 and len(p.get('rno',[]))==4

def free_play(row):
 if not valid_sample(row):return False
 g=row['global'];p=row['player']
 return g['player_life']>0 and g.get('rno',[])[:2]==[3,0] and g.get('stop')==0 and not row.get('event_start_cnt',1) and row.get('subscreen_type',1)==0 and not row.get('ssloop',1) and bool(p.get('alive',0)&1)

def shooting_safe(row):
 if not free_play(row):return False
 g=row['global'];status=g.get('status',[])
 return len(status)==4 and not(status[0]&0x200000) and not(status[2]&0x80000000) and row['player']['rno'][0]==0

def qa_safe(row):
 frames=row.get('qa_frames')
 return isinstance(frames,int) and frames>=30 and free_play(row) and row.get('qa_flags') is not None

def discharge(before,after):
 """Strict ordinary gun-round evidence; caller separately records source/input windows."""
 try:
  for row in (before,after):
   if any(type(row[k]) is not int for k in ('room','frame')):raise ValueError()
   w=row['weapon'];c=row['counters']
   if not w['slot'] or any(type(w[k]) is not int for k in ('slot','id','equipped_id','weapon_no','loaded_rounds')) or not 0<=w['loaded_rounds']<=0x1fff:raise ValueError()
   if len(row['debug_flags'])<3 or any(type(c[k]) is not int for k in ('g_shot_cnt','c_shot_cnt','g_hit_cnt','g_kill_cnt')):raise ValueError()
 except (KeyError,TypeError,ValueError):
  return {'accepted':False,'rounds':0,'reasons':['incomplete ordinary-weapon sample']}
 a=before['weapon'];b=after['weapon'];ca=before['counters'];cb=after['counters'];reason=[]
 if before['room']!=after['room'] or not 0<after['frame']-before['frame']<=120:reason.append('room/frame discontinuity')
 if any(a[k]!=b[k] for k in ('slot','id','equipped_id','weapon_no')):reason.append('weapon/slot switch')
 if a['id'] in (0x52,0x6d) or before['debug_flags'][2]&0x00400000:reason.append('special/infinite ammunition')
 spent=a['loaded_rounds']-b['loaded_rounds'];shots=cb['g_shot_cnt']-ca['g_shot_cnt'];chapter=cb['c_shot_cnt']-ca['c_shot_cnt']
 if spent<=0 or shots!=spent or chapter!=spent:reason.append('ammo/counter discharge mismatch')
 return {'accepted':not reason,'rounds':spent if not reason else 0,'reasons':reason,'hit_count_delta':cb['g_hit_cnt']-ca['g_hit_cnt'],'kill_count_delta':cb['g_kill_cnt']-ca['g_kill_cnt']}
