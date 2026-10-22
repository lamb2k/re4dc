from pathlib import Path
import json,struct,hashlib,sys
L=Path(__file__).parent;D=Path(r'C:\Flycast-Evidence\re4-dreamcast\castle18-20261018\Test21\recovered-j-content-20261021');R=D.parent;n=int(sys.argv[1]);cap=D/f'route-walk-controlled-event{n:03d}';out=D/f'controlled-event{n:03d}-closed-proof.json';assert not out.exists();h={};exec((L/'audit-authoritative-life-extended-history-20261019.py').read_text().split('targets=[')[0],h);state=cap/'data/disc.state';raw=h['decode'](state);va,code=h['load_segments'](R/'builds/c21jmW/re4dc-game.elf');rb=raw.find(code[0x4000:0x4100])-(va+0x4000-0x8c000000)
for off in [0x100000,0x120000,0x140000]:assert raw[rb+va+off-0x8c000000:rb+va+off+256-0x8c000000]==code[off:off+256]
def read(a,n):assert 0x8c000000<=a and a+n<=0x8d000000;return raw[rb+a-0x8c000000:rb+a+n-0x8c000000]
u32=lambda a:struct.unpack('<I',read(a,4))[0];pg=u32(0x8c2e91dc);pl=u32(0x8c39d700);sub=u32(0x8c39d6fc);rd=0x8c3b9314;nr=struct.unpack('<H',read(rd+2,2))[0];sv=u32(rd+0x18);rsf={}
if 0<nr<256 and 0x8c000000<=sv and sv+nr*0xd8<=0x8d000000:
 tb=read(sv,nr*0xd8)
 for i in range(nr):
  q=tb[i*0xd8:(i+1)*0xd8]
  if q[:2]in[bytes([2,1]),bytes([2,8]),bytes([2,4])]:rsf[hex(q[0]*256+q[1])]=hex(struct.unpack_from('<I',q,4)[0])
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();start=json.loads((cap/'run-start.json').read_text());result=json.loads((cap/'run-result.json').read_text());guard=json.loads((cap/'owned-resource-guard.json').read_text());assert result['emulator_exited']and guard['process_exited'];screens=[]
for p in sorted((cap/'shots').glob('controlled-*/controlled-context.json')):
 c=json.loads(p.read_text());screens.append(dict(context=str(p),sha256=sha(p),source_interval=c['source_frame_interval'],pngs=c['pngs']))
record=dict(scope='CONTROLLED teleport/scripted-event TEST lineage; exact closed-state audit anchored by four frozenELF code segments. No authenticcombat/release/physicalDreamcastacceptance.',state=str(state),state_sha256=sha(state),source=u32(pg+0x51e4),room=hex(struct.unpack('<H',read(pg+0x4f9e,2))[0]),chapter=read(pg+0x4f8a,1)[0],phase=list(read(pg+0x20,2)),Stop=hex(u32(pg+0x170)),status1=hex(u32(pg+0x5010)),health=list(struct.unpack('<4H',read(pg+0x4fa4,8))),saved_RSF=rsf,player_pos=list(struct.unpack('<3f',read(pl+0x94,12)))if 0x8c000000<=pl<0x8cfff000 else None,partner_ptr=hex(sub),partner_pos=list(struct.unpack('<3f',read(sub+0x94,12)))if 0x8c000000<=sub<0x8cfff000 else None,run_start=start,run_result=result,resource_guard=guard,screenshots=screens,protected={})
for name,expected in [('route-walk127','ec9ed07928efec777400317762bb1730a0644def73d610a1631c20381ca40e16'),('route-walk294','cb7a314b8fd0383af0b7baf17c2e87a712705beb122a1d39c7705553dd795258')]:
 p=D/name/'data/disc.state';assert sha(p)==expected;record['protected'][name]=dict(state_sha256=expected,unchanged=True)
out.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps({k:record[k]for k in ['source','state_sha256','room','chapter','health','saved_RSF','phase','Stop']}));print(out)
