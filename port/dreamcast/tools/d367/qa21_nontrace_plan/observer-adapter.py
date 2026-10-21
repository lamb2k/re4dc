"""Read-only adapter; caller supplies exact-bound symbols/layout and read_bytes.
No process attach, input, save-state load, write or launch API exists here.
Samples are non-atomic; coherence and source frames must be retained.
"""
import struct

REQUIRED = ('_pG','_pPL','_EmMgr','_ItemMgr','_pSys','_Key','_Joy',
            '__ZL8Pad_data','_SceSys','_SubScreenWk')
OPTIONAL_QA = ('__ZN12_GLOBAL__N_1L9qa_framesE','__ZN12_GLOBAL__N_1L7g_flagsE')

def select_symbols(symbols):
 missing=[n for n in REQUIRED if n not in symbols]
 if missing: raise ValueError('missing generic symbols: '+','.join(missing))
 return {n:symbols.get(n) for n in REQUIRED+OPTIONAL_QA+('_pSUB',)}

class Reader:
 def __init__(self, read_bytes, symbols, layout, expected_elf):
  if layout['elf_sha256'] != expected_elf:raise ValueError('layout ELF mismatch')
  self.raw=read_bytes;self.sy=select_symbols(symbols);self.types=layout['found']
 def read(self, addr, fmt):
  size=struct.calcsize('<'+fmt)
  if not isinstance(addr,int) or not 0x8c000000<=addr<=0x8d000000-size:raise ValueError('outside SH4 RAM')
  data=self.raw(addr,size)
  if len(data)!=size:raise ValueError('short RAM read')
  values=struct.unpack('<'+fmt,data)
  return values[0] if len(values)==1 else list(values)
 def off(self, typ, name):
  m=[v for v in self.types[typ]['members'] if v['name']==name or v['name'].endswith('.'+name)]
  if len(m)!=1:raise ValueError('missing/ambiguous member '+typ+'.'+name)
  return m[0]['offset']
 def field(self,base,typ,name,fmt):return self.read(base+self.off(typ,name),fmt)
 def snapshot(self):
  sy=self.sy;g=self.read(sy['_pG'],'I');pl=self.read(sy['_pPL'],'I')
  if not g or not pl:return {'valid':False,'reason':'initial global/player pointer unavailable','qa_frames':None,'qa_flags':None}
  gf=lambda n,f:self.field(g,'GlobalWork',n,f)
  pf=lambda n,f:self.field(pl,'cPlayer',n,f)
  frame=gf('Frame_cnt','I');status=gf('Status_flg','4I')
  row={'global':{'frame':frame,'room':gf('room_id','H'),'player_life':gf('pl_life','H'),
      'rno':gf('Rno0','4B'),'stop':gf('Stop_flg','I'),'status':status},
      'player':{'ptr':pl,'pos':pf('pos','3f'),'rno':pf('r_no_0','4B'),
      'alive':pf('be_flag','I'),'serial':pf('serial','I'),'dmgType':pf('dmgType','I')},
      'event_start_cnt':self.field(sy['_SceSys'],'cSceSys','event_start_cnt','B'),
      'subscreen_type':self.field(sy['_SubScreenWk'],'SUB_SCREEN','type','I'),
      'ssloop':self.field(sy['_SubScreenWk'],'SUB_SCREEN','Loop','B'),
      'qa_frames':self.read(sy[OPTIONAL_QA[0]],'I') if sy[OPTIONAL_QA[0]] is not None else None,
      'qa_flags':self.read(sy[OPTIONAL_QA[1]],'I') if sy[OPTIONAL_QA[1]] is not None else None,
      'keys':{n:self.field(sy['_Key'],'KeyWork',n,'Q') for n in ('on','trg','rel')},
      'counters':{n:gf(n,'I') for n in ('g_shot_cnt','c_shot_cnt','g_hit_cnt','c_hit_cnt','g_kill_cnt','c_kill_cnt')},
      'debug_flags':gf('Debug_flg','4I'),'weapon_no':gf('weapon_no','B'),'pl_type':gf('pl_type','B')}
  arm=self.field(sy['_ItemMgr'],'cItemMgr','pArm','I')
  row['weapon']={'slot':arm,'id':self.field(arm,'ItemWork','id','H') if arm else None,
   'equipped_id':self.field(sy['_ItemMgr'],'cItemMgr','m_wep_id','H'),
   'weapon_no':row['weapon_no'],'loaded_rounds':self.field(arm,'ItemWork','bullet','H')&0x1fff if arm else None}
  motion=pf('pMotion','I');body=pf('Body','I');system=self.read(sy['_pSys'],'I')
  row['motion']={n:self.field(motion,'MotionWork',n,f) for n,f in [('pMot','I'),('Mot_frame','f'),('Seq_frame','f'),('Seq_frame_num','H')]} if motion else None
  row['body']={n:self.field(body,'cPlBody',n,'I') for n in ('pHeadData','pShape','pHair','pEye')} if body else None
  row['system']={n:self.field(system,'SystemWork',n,f) for n,f in [('region','B'),('key_type','B'),('flags','I')]} if system else None
  cam=g+self.off('GlobalWork','Cam')+self.off('Camera','param')
  row['camera']={n:self.field(cam,'CameraParam',n,f) for n,f in [('pos','3f'),('at','3f'),('roll','f'),('fovy','f')]}
  row['end_frame']=gf('Frame_cnt','I');row['coherent']=row['end_frame']==frame
  row['valid']=True
  return row

 def actor(self,ptr,authenticated_em10=False):
  """Actor identity is ptr+serial+id/type; caller must validate active-list membership.
  Optional Em10 work requires source-authenticated class, never inferred from ptr alone.
  """
  cf=lambda n,f:self.field(ptr,'cEm',n,f)
  out={'ptr':ptr,'serial':cf('serial','I'),'id':cf('id','B'),'type':cf('type','B'),
       'rno':cf('r_no_0','4B'),'hp':cf('hp','H'),'dmgType':cf('dmgType','i'),
       'pos':cf('pos','3f'),'frame':cf('frame','f')}
  if authenticated_em10:
   wk=ptr+self.off('cEm','x3E0')
   if self.off('cEm','x3E0')+self.types['Em10Work']['bytes']>self.types['cEm10']['bytes']:raise ValueError('Em10Work extent invalid')
   out['em10']={n:self.field(wk,'Em10Work',n,f) for n,f in [('Timer','i'),('Timer2','i'),('Wep_type','B'),('Fire_timer','i'),('pWep','I')]}
  return out
