"""Offline read-only stalled-player evidence; never modifies emulator or state."""
import argparse,json,struct,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--case',required=True);p.add_argument('--arm',choices=['combined','qa-control'],required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
assert not a.out.exists()
R=a.evidence;sys.path.insert(0,str(R/'dependencies'));import checkpoint
cap=R/a.case;build=R/'builds'/a.arm;binding=R/('control-binding.json' if a.arm=='qa-control' else 'combined-binding.json');layout=build/'dwarf-layout.json';elf=build/'re4dc-game.elf';state=cap/'data/disc.state'
proof=checkpoint.audit(state,elf,binding,layout);raw=checkpoint.decode(state);base=proof['ram_serialization_offset'];shape=json.loads(layout.read_text());syms={k:int(v,0) for k,v in json.loads(binding.read_text())['symbols'].items()}
def read(addr,fmt):
 n=struct.calcsize('<'+fmt);assert 0x8c000000<=addr<=0x8d000000-n
 v=struct.unpack_from('<'+fmt,raw,base+addr-0x8c000000);return v[0] if len(v)==1 else list(v)
def offset(kind,name):
 members=[m for m in shape['found'][kind]['members'] if m['name'].split('.')[-1]==name];assert len(members)==1,(kind,name);return members[0]['offset']
def field(addr,kind,name,fmt):return read(addr+offset(kind,name),fmt)
def model(addr):
 return {'ptr':hex(addr),'id':field(addr,'cModel','id','B'),'type':field(addr,'cModel','type','B'),'be_flag':hex(field(addr,'cModel','be_flag','I')),'rno':field(addr,'cModel','r_no_0','4B'),'pos':field(addr,'cModel','pos','3f'),'hp':field(addr,'cEm','hp','h')}
pg=read(syms['pG'],'I');pl=read(syms['pPL'],'I');player=model(pl)
for name,fmt in [('dmgType','I'),('m_Work0','I'),('m_Work1','I'),('m_Work2','I'),('m_ConDmFlag','B'),('m_ConDmTimer','H')]:player[name]=field(pl,'cPlayer',name,fmt)
actors=[];node=field(syms['EmMgr'],'cEmMgr','pAlive','I');seen=set()
while 0x8c000000<=node<0x8d000000 and node not in seen and len(seen)<64:
 seen.add(node);row=model(node)
 if int(row['be_flag'],0)&1:actors.append(row)
 node=field(node,'cModel','pNext','I')
changes=[];prev=None
for line in (cap/'read-only-state.jsonl').read_text().splitlines():
 row=json.loads(line);g=row.get('global',{});plr=row.get('player',{});key=(g.get('player_life'),tuple(plr.get('rno',[])),row.get('subscreen_type'))
 if key!=prev:changes.append({'host_s':row['host_s'],'frame':g.get('frame'),'life':key[0],'player_rno':list(key[1]),'subscreen_type':key[2],'qa_frames':row.get('qa_frames'),'motion_ptr':plr.get('motion_ptr'),'motion_frame':plr.get('motion_frame')});prev=key
result={'scope':'Read-only offline saved-state audit, no gameplay edits; input/RNG/source-frame timing differs between lineages','case':a.case,'arm':a.arm,'immutable_state_proof':proof,'global':{'game_level':field(pg,'GlobalWork','Game_level','B'),'debug_flags':field(pg,'GlobalWork','Debug_flg','4I')},'player':player,'actors':actors,'observed_state_changes':changes,'checkpoint_receipt_sha256':checkpoint.sha(cap/'checkpoint.json'),'process_supervisor':json.loads((R/'invocations'/a.case/'process-supervisor.json').read_text())}
a.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'case':a.case,'final_life':proof['player_life'],'rno':proof['player_rno'],'actors':len(actors),'out':str(a.out)}))