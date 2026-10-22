"""Read-only adapter; caller supplies exact-bound symbols/layout and read_bytes.
No process attach, input, save-state load, write or launch API exists here.
Samples are non-atomic; coherence and source frames must be retained.
"""
import struct,importlib.util,pathlib
_spec=importlib.util.spec_from_file_location('layout_contract',pathlib.Path(__file__).with_name('layout-contract.py'))
_contract=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(_contract)

REQUIRED = ('_pG','_pPL','_EmMgr','_ItemMgr','_pSys','_Key','_Joy',
            '__ZL8Pad_data','_SceSys','_SubScreenWk')
OPTIONAL_QA = ('__ZN12_GLOBAL__N_1L9qa_framesE','__ZN12_GLOBAL__N_1L7g_flagsE')

def resolve_symbol_groups(groups):
 return {n:items[0]['address'] for n,items in groups.items() if len({(v['address'],v['bytes'],v['type']) for v in items})==1}

def select_symbols(symbols):
 missing=[n for n in REQUIRED if n not in symbols]
 if missing: raise ValueError('missing generic symbols: '+','.join(missing))
 return {n:symbols.get(n) for n in REQUIRED+OPTIONAL_QA+('_pSUB',)}

class RAMRangeError(ValueError):
 """Only an invalid SH4 address/extent; unrelated reader/ABI errors stay fatal."""
 def __init__(self,address,fmt):
  self.address=address;self.format=fmt;self.bytes=struct.calcsize('<'+fmt);self.field_context=None
  super().__init__('outside SH4 RAM: '+repr(address)+' format='+fmt+' bytes='+str(self.bytes))
 def as_dict(self):
  return {'kind':'RAMRangeError','address':hex(self.address) if isinstance(self.address,int) else repr(self.address),'format':self.format,'bytes':self.bytes,'allowed_start':'0x8c000000','allowed_end_exclusive':'0x8d000000','field_context':self.field_context}

class Reader:
 def __init__(self, read_bytes, symbols, layout, expected_elf, strict=True, source_contract=None, expected_source=None):
  if layout['elf_sha256'] != expected_elf:raise ValueError('layout ELF mismatch')
  self.raw=read_bytes;self.sy=select_symbols(symbols);self.types=layout['found'];self.layout=layout;self.strict=strict
  self.abi=_contract.validate_layout(layout) if strict else None
  if strict and (not source_contract or not expected_source or source_contract.get('source')!=expected_source):raise ValueError('pinned source cast/classification contract required')
  self.item_classes={i:1 for i in source_contract['ordinary_loaded_round_item_ids']} if source_contract else {}
  self.wep_info=source_contract.get('wep_info',[]) if source_contract else []
 def read(self, addr, fmt):
  size=struct.calcsize('<'+fmt)
  if not isinstance(addr,int) or not 0x8c000000<=addr<=0x8d000000-size:raise RAMRangeError(addr,fmt)
  data=self.raw(addr,size)
  if len(data)!=size:raise ValueError('short RAM read')
  values=struct.unpack('<'+fmt,data)
  return values[0] if len(values)==1 else list(values)
 def off(self, typ, name):
  m=[v for v in self.types[typ]['members'] if v['name']==name or v['name'].endswith('.'+name)]
  if len(m)!=1:raise ValueError('missing/ambiguous member '+typ+'.'+name)
  return m[0]['offset']
 def field(self,base,typ,name,fmt):
  if self.strict:_contract.validate_read(self.layout,typ,name,fmt)
  try:return self.read(base+self.off(typ,name),fmt)
  except RAMRangeError as error:
   error.field_context={'base':hex(base) if isinstance(base,int) else repr(base),'structure':typ,'member':name,'offset':self.off(typ,name)}
   raise
 def snapshot(self):
  sy=self.sy;g=self.read(sy['_pG'],'I');pl=self.read(sy['_pPL'],'I')
  if not (0x8c000000<=g<=0x8d000000-self.types['GlobalWork']['bytes'] and 0x8c000000<=pl<=0x8d000000-self.types['cPlayer']['bytes']):return {'valid':False,'reason':'initial global/player pointer unavailable','qa_frames':None,'qa_flags':None}
  gf=lambda n,f:self.field(g,'GlobalWork',n,f)
  pf=lambda n,f:self.field(pl,'cPlayer',n,f)
  frame=gf('Frame_cnt','I');status=gf('Status_flg','4I')
  row={'global':{'ptr':hex(g),'frame':frame,'room':gf('room_id','H'),'player_life':gf('pl_life','H'),
      'rno':gf('Rno0','4B'),'stop':gf('Stop_flg','I'),'status':status},
      'player':{'ptr':pl,'pos':pf('pos','3f'),'ang':pf('ang','3f'),'rno':pf('r_no_0','4B'),
      'alive':pf('be_flag','I'),'serial':pf('serial','I'),'dmgType':pf('dmgType','i')},
      'event_start_cnt':self.field(sy['_SceSys'],'cSceSys','event_start_cnt','B'),
      'subscreen_type':self.field(sy['_SubScreenWk'],'SUB_SCREEN','type','i'),
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
  items=self.field(sy['_ItemMgr'],'cItemMgr','pItems','I');count=self.field(sy['_ItemMgr'],'cItemMgr','nItems','i')
  row['weapon']['item_class']=self.item_classes.get(row['weapon']['id'])
  row['weapon']['attribute']=self.field(arm,'ItemWork','bullet','H')>>13 if arm else None
  row['weapon']['weapon_source_match']=any(w['id']==row['weapon']['id'] and w['attribute']==row['weapon']['attribute'] and w['weapon_no']==row['weapon_no'] for w in self.wep_info) if self.wep_info else None
  inrange=bool(items and arm and 0<count<=0x180 and items<=arm<items+count*self.types['ItemWork']['bytes'] and (arm-items)%self.types['ItemWork']['bytes']==0)
  owner=self.field(sy['_ItemMgr'],'cItemMgr','type','B')
  row['weapon']['valid_inventory_slot']=inrange and bool(self.field(arm,'ItemWork','flags','B')&1) and self.field(arm,'ItemWork','type','B')==owner
  motion=pl+self.off('cPlayer','Motion');body=pf('Body','I');system=self.read(sy['_pSys'],'I')
  row['motion']={n:self.field(motion,'MotionWork',n,f) for n,f in [('pMot','I'),('Mot_frame','f'),('Seq_frame','f'),('Seq_frame_num','H')]}
  row['body']={n:self.field(body,'cPlBody',n,'I') for n in ('pHeadData','pShape','pHair','pEye')} if body else None
  row['system']={n:self.field(system,'SystemWork',n,f) for n,f in [('region','B'),('key_type','B'),('flags','I')]} if system else None
  cam=g+self.off('GlobalWork','Cam')+self.off('Camera','param')
  row['camera']={n:self.field(cam,'CameraParam',n,f) for n,f in [('pos','3f'),('at','3f'),('roll','f'),('fovy','f')]}
  row['end_frame']=gf('Frame_cnt','I');row['coherent']=row['end_frame']==frame
  row['valid']=True
  row['non_atomic']=True
  row['player']['dmgType_bits']=row['player']['dmgType']&0xffffffff
  row['diagnostics']={'death_trace':None,'lethal_caller':None,'LifeDownSet2_before_after':None}
  row['unavailable']=['diagnostics.'+n for n in row['diagnostics']]
  if row['weapon']['item_class'] is None:row['unavailable'].append('weapon.item_class')
  return row

 def actor(self,ptr,authenticated_em10=False):
  """Actor identity is ptr+serial+id/type; caller must validate active-list membership.
  Optional Em10 work requires source-authenticated class, never inferred from ptr alone.
  """
  cf=lambda n,f:self.field(ptr,'cEm',n,f)
  out={'ptr':ptr,'serial':cf('serial','I'),'id':cf('id','B'),'type':cf('type','B'),
       'rno':cf('r_no_0','4B'),'hp':cf('hp','h'),'dmgType':cf('dmgType','i'),
       'pos':cf('pos','3f'),'ang':cf('ang','3f'),'alive':cf('be_flag','I'),'frame':cf('frame','f')}
  motion=ptr+self.off('cEm','Motion')
  out['motion']={n:self.field(motion,'MotionWork',n,f) for n,f in [('pMot','I'),('Mot_frame','f'),('Seq_frame','f'),('Seq_frame_num','H')]}
  out['em10']=None # private view stays unavailable without explicit source class authentication
  out['dmgType_bits']=out['dmgType']&0xffffffff
  if authenticated_em10:
   wk=ptr+self.off('cEm','x3E0')
   if self.off('cEm','x3E0')+self.types['Em10Work']['bytes']>self.types['cEm10']['bytes']:raise ValueError('Em10Work extent invalid')
   out['em10']={n:self.field(wk,'Em10Work',n,f) for n,f in [('Timer','i'),('Timer2','i'),('Wep_type','B'),('Fire_timer','i'),('pWep','I')]}
  return out

 def actor_chain(self):
  base=self.sy['_EmMgr'];array=self.field(base,'cEmMgr','pArray','I');count=self.field(base,'cEmMgr','nArray','I');stride=self.field(base,'cEmMgr','size','I');current=self.field(base,'cEmMgr','pAlive','I')
  if not array or not count or stride<self.types['cEm']['bytes'] or array+count*stride>0x8d000000 or array<0x8c000000:
   return {'actors':[],'manager_valid':False,'reason':'unavailable/invalid actor pool','manager_nodes_seen':0}
  seen=set();actors=[]
  while current:
   if current in seen or len(seen)>=64:return {'actors':actors,'manager_valid':False,'reason':'cycle/truncated actor list','manager_nodes_seen':len(seen)}
   if current<array or current>=array+count*stride or (current-array)%stride:return {'actors':actors,'manager_valid':False,'reason':'active node outside exact pool','manager_nodes_seen':len(seen)}
   seen.add(current);actor=self.actor(current);actor['active_list_member']=True
   if actor['id']==0 or 0x10<=actor['id']<=0x20:actors.append(actor)
   current=self.field(current,'cEm','pNext','I')
  return {'actors':actors,'manager_valid':True,'manager_nodes_seen':len(seen),'pool':{'array':array,'count':count,'stride':stride}}
