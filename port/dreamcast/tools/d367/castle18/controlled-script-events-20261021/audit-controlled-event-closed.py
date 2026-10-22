from pathlib import Path
import json,struct,hashlib,re,sys
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18');D=Path(r'C:\Flycast-Evidence\re4-dreamcast\castle18-20261018\Test21\recovered-j-content-20261021');R=D.parent;n=int(sys.argv[1]);assert 1<=n<=999;cap=D/f'route-walk-controlled-event{n:03d}';out=D/f'controlled-event{n:03d}-closed-proof.json';assert not out.exists();h={};exec((L/'audit-authoritative-life-extended-history-20261019.py').read_text().split('targets=[')[0],h);state=cap/'data/disc.state';raw=h['decode'](state);va,code=h['load_segments'](R/'builds/c21jmW/re4dc-game.elf');rb=raw.find(code[0x4000:0x4100])-(va+0x4000-0x8c000000)
for off in [0x100000,0x120000,0x140000]:assert raw[rb+va+off-0x8c000000:rb+va+off+256-0x8c000000]==code[off:off+256]
def read(a,n):assert 0x8c000000<=a and a+n<=0x8d000000;return raw[rb+a-0x8c000000:rb+a+n-0x8c000000]
u32=lambda a:struct.unpack('<I',read(a,4))[0];pg=u32(0x8c2e91dc);pl=u32(0x8c39d700);sub=u32(0x8c39d6fc);rd=0x8c3b9314;nr=struct.unpack('<H',read(rd+2,2))[0];sv=u32(rd+0x18);tb=read(sv,nr*0xd8);rsf=next(struct.unpack_from('<I',tb,i*0xd8+4)[0]for i in range(nr)if tb[i*0xd8:i*0xd8+2]==b'\x02\x01');door=u32(u32(0x8c3bdd64)+0x53*4);actors=[];p=u32(0x8c39d3b8+0x14);seen=set()
while p and p not in seen and len(seen)<128:
 seen.add(p);b=read(p,0x3a0);actors.append(dict(ptr=hex(p),id=b[0x100],type=b[0x101],source_list=b[0x398],hp=struct.unpack_from('<h',b,0x320)[0],vtable=hex(struct.unpack_from('<I',b,0)[0]),be_flag_native=hex(struct.unpack_from('<I',b,4)[0]),routines=list(b[0xfc:0x100]),pos=list(struct.unpack_from('<3f',b,0x94))));p=struct.unpack_from('<I',b,8)[0]
areas={};p=0x8c3b93cc+0x8c;seen=set()
for _ in range(1024):
 v=u32(p)
 if v==0xffffffff:break
 p=v|0x80000000
 if not 0x8c000000<=p<0x8cffff00 or p in seen:break
 seen.add(p)
 if v&0x80000000:areas[hex(read(p+0x36,1)[0])]=dict(ptr=hex(p),enabled=bool(read(p+0x34,1)[0]&1),func=hex(u32(p+0x40)))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();start=json.loads((cap/'run-start.json').read_text());result=json.loads((cap/'run-result.json').read_text());guard=json.loads((cap/'owned-resource-guard.json').read_text());assert result['emulator_exited']and guard['process_exited'];screens=[]
for p in sorted((cap/'shots').glob('controlled-*/controlled-context.json')):
 c=json.loads(p.read_text());screens.append(dict(context=str(p),sha256=sha(p),source_interval=c['source_frame_interval'],pngs=c['pngs']))
record=dict(scope='CONTROLLED teleport/scripted-event TEST lineage, exact closed-state audit anchored by four frozenELF code segments. Not authenticcombat, releasecheck orphysicalDreamcastacceptance.',state=str(state),state_sha256=sha(state),source=u32(pg+0x51e4),room=hex(struct.unpack('<H',read(pg+0x4f9e,2))[0]),chapter=read(pg+0x4f8a,1)[0],phase=list(read(pg+0x20,2)),Stop=hex(u32(pg+0x170)),status1=hex(u32(pg+0x5010)),room_flags0=hex(u32(pg+0x174)),door_flags=hex(u32(pg+0x51cc)),health=list(struct.unpack('<4H',read(pg+0x4fa4,8))),player_pos=list(struct.unpack('<3f',read(pl+0x94,12))),partner_pos=list(struct.unpack('<3f',read(sub+0x94,12)))if sub else None,saved_RSF=hex(rsf),door_Smd53=hex(door),door_y=struct.unpack('<f',read(door+0x98,4))[0],areas=areas,actors=actors,run_start=start,run_result=result,resource_guard=guard,screenshots=screens,observer_diagnostic_note='001observerfield namedbe_flag readvtable(offset0), notnativebe_flag(offset4); notusedforacceptance. Correctnativeflag recordedinthisclosedaudit; rawobserverunchanged. Before-debug screenshot isblackfade, notvisualNPCproof; baselineHP+typedlistfromread-onlyRAM/nativekilllogs. Secondinner-deadlinecapture001ispostgoalclosegrace,mislabeled, notactualdeadlinefailure.'if n==1 else None)
record['protected']={}
for name,expected in [('route-walk127','ec9ed07928efec777400317762bb1730a0644def73d610a1631c20381ca40e16'),('route-walk294','cb7a314b8fd0383af0b7baf17c2e87a712705beb122a1d39c7705553dd795258')]:
 p=D/name/'data/disc.state';assert sha(p)==expected;record['protected'][name]=dict(state_sha256=expected,unchanged=True)
out.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps({k:record[k]for k in ['source','state_sha256','health','saved_RSF','door_y','phase','Stop']}));print(out)
