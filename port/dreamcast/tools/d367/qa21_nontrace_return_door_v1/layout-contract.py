"""Exact ABI contract for every adapter field. No source or RAM mutation."""
import struct

def member(layout,typ,name):
 matches=[m for m in layout['found'][typ]['members'] if m['name']==name or m['name'].endswith('.'+name)]
 if len(matches)!=1:raise ValueError('missing/ambiguous member '+typ+'.'+name)
 return matches[0]

def leaf(meta,fmt):
 if meta['bytes']!=struct.calcsize('<'+fmt):raise ValueError('ABI byte size mismatch')
 if meta['tag']=='DW_TAG_pointer_type':
  if fmt!='I':raise ValueError('pointer format mismatch')
  return
 enc=meta.get('encoding')
 allowed={'B':{7,8},'H':{7,8},'I':{7,8},'Q':{7,8},'b':{5,6},'h':{5,6},'i':{5,6},'f':{4}}
 if enc not in allowed.get(fmt,set()):raise ValueError('ABI scalar encoding mismatch '+str((meta,fmt)))

def validate_read(layout,typ,name,fmt):
 m=member(layout,typ,name)
 if (typ,name,fmt) in [('GlobalWork','Rno0','4B'),('cPlayer','r_no_0','4B'),('cEm','r_no_0','4B')]:
  names=['Rno'+str(i) for i in range(4)] if typ=='GlobalWork' else ['r_no_'+str(i) for i in range(4)]
  for i,n in enumerate(names):
   nmeta=member(layout,typ,n);leaf(nmeta,'B')
   if nmeta['offset']!=m['offset']+i:raise ValueError('routine byte group not contiguous')
 elif fmt in ('4I',):
  if m['tag']!='DW_TAG_array_type' or m.get('dimensions')!=[4] or m['bytes']!=16:raise ValueError('flag array ABI mismatch')
  leaf(m['element'],'I')
 elif fmt=='3f':
  parts=m.get('aggregate_members',[])
  if m['bytes']!=12 or [(x['name'],x['offset']) for x in parts]!=[('x',0),('y',4),('z',8)]:raise ValueError('Vec ABI not proven')
  for v in parts:leaf(v,'f')
 else:leaf(m,fmt)
 if m['offset']<0 or m['offset']+struct.calcsize('<'+fmt)>layout['found'][typ]['bytes']:raise ValueError('member exceeds object')
 return dict(structure=typ,requested=name,path=m['name'],offset=m['offset'],format=fmt,type=m['type'],tag=m['tag'],bytes=m['bytes'],route=m.get('route'),pointee=m.get('pointee'))

CONTRACT=[]
def add(t,entries):
 CONTRACT.extend((t,n,f) for n,f in entries)
add('GlobalWork',[('Frame_cnt','I'),('room_id','H'),('pl_life','H'),('Rno0','4B'),('Stop_flg','I'),('Status_flg','4I'),('Debug_flg','4I'),('weapon_no','B'),('pl_type','B')]+[(n,'I') for n in ('g_shot_cnt','c_shot_cnt','g_hit_cnt','c_hit_cnt','g_kill_cnt','c_kill_cnt')])
add('cPlayer',[('ang','3f'),('pos','3f'),('r_no_0','4B'),('be_flag','I'),('serial','I'),('dmgType','i'),('pMotion','I'),('Body','I')])
add('cSceSys',[('event_start_cnt','B')]);add('SUB_SCREEN',[('type','i'),('Loop','B')])
add('KeyWork',[(n,'Q') for n in ('on','trg','rel')]);add('cItemMgr',[('pArm','I'),('m_wep_id','H'),('pItems','I'),('nItems','i'),('type','B')]);add('ItemWork',[('id','H'),('bullet','H'),('flags','B'),('type','B')])
add('MotionWork',[('pMot','I'),('Mot_frame','f'),('Seq_frame','f'),('Seq_frame_num','H')])
add('cPlBody',[(n,'I') for n in ('pHeadData','pShape','pHair','pEye')]);add('SystemWork',[('region','B'),('key_type','B'),('flags','I')])
add('CameraParam',[('pos','3f'),('at','3f'),('roll','f'),('fovy','f')])
add('cEm',[('be_flag','I'),('pNext','I'),('ang','3f'),('serial','I'),('id','B'),('type','B'),('r_no_0','4B'),('hp','h'),('dmgType','i'),('pos','3f'),('frame','f')])
add('Em10Work',[('Timer','i'),('Timer2','i'),('Wep_type','B'),('Fire_timer','i'),('pWep','I')])

add('cEmMgr',[(n,'I') for n in ('pArray','nArray','size','pAlive')])

def validate_layout(layout):
 if layout.get('schema')!=2:raise ValueError('rich exact ABI metadata required')
 rows=[validate_read(layout,*entry) for entry in CONTRACT]
 views=[]
 for typ,n,target in [('GlobalWork','Cam','Camera'),('Camera','param','CameraParam'),('cPlayer','Motion','MotionWork'),('cEm','Motion','MotionWork')]:
  m=member(layout,typ,n)
  if m['type']!=target or m['bytes']!=layout['found'][target]['bytes'] or m['offset']+m['bytes']>layout['found'][typ]['bytes']:raise ValueError('inline object mismatch')
  views.append(dict(structure=typ,path=m['name'],offset=m['offset'],target=target,bytes=m['bytes']))
 m=member(layout,'cEm','x3E0')
 if m['offset']+layout['found']['Em10Work']['bytes']>layout['found']['cEm10']['bytes']:raise ValueError('private work view exceeds class')
 views.append(dict(structure='cEm',path=m['name'],offset=m['offset'],target='Em10Work',source_cast_required=True))
 return {'fields':rows,'object_views':views,'field_count':len(rows),'missing_diagnostic_fields':['death_trace','lethal_caller','LifeDownSet2_before_after'],
 'motion_view':'MotionWork is inline cModel.Motion at+472/220B. pMotion aliases Motion.pMot data pointer and is NEVER dereferenced as work' }
