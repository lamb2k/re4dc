from pathlib import Path
import json,struct,hashlib,sys
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18');R=Path(r'C:\Flycast-Evidence\re4-dreamcast\castle18-20261018\Test21');D=R/'recovered-j-content-20261021';n=int(sys.argv[1]);assert 1<=n<=999;cap=D/f'route-walk{n:02d}';out=D/f'route-walk{n:02d}-checkpoint-proof.json';assert not out.exists()
start=json.loads((cap/'run-start.json').read_text());assert start['disc_sha256']=='b67ac21eff8d819ef9ca5f0997b4c16401cb98a3d304feb65aa4b90f7affbeb6';assert start['elf_sha256']=='4d823b496b9a402baadabe7f679c089fa0fd55c7ffd175ec634915745a11487f';run=json.loads((cap/'run-result.json').read_text());assert run['emulator_exited']
h={};exec((L/'audit-authoritative-life-extended-history-20261019.py').read_text().split('targets=[')[0],h);state=cap/'data/disc.state';raw=h['decode'](state);va,code=h['load_segments'](R/'builds/c21jmW/re4dc-game.elf');rb=raw.find(code[0x4000:0x4100])-(va+0x4000-0x8c000000)
for off in [0x100000,0x120000,0x140000]:assert raw[rb+va+off-0x8c000000:rb+va+off+256-0x8c000000]==code[off:off+256]
def read(a,n):assert 0x8c000000<=a and a+n<=0x8d000000;return raw[rb+a-0x8c000000:rb+a+n-0x8c000000]
u32=lambda a:struct.unpack('<I',read(a,4))[0];pg=u32(0x8c2e91dc);phase=list(read(pg+0x20,2));ss=read(0x8c3de064+0x28,1)[0];stop=u32(pg+0x170);held=u32(pg+0x5010)&0x10000000
proof=dict(scope='Read-only immutable checkpoint audit of recovered-J NEW cold lineage only. No original J state retarget or game writes.',run=cap.name,state_sha256=hashlib.sha256(state.read_bytes()).hexdigest(),source_frame=u32(pg+0x51e4),room=hex(struct.unpack('<H',read(pg+0x4f9e,2))[0]),chapter=read(pg+0x4f8a,1)[0],phase=phase,Stop=hex(stop),SSLoop=ss,held_world=hex(held),health=list(struct.unpack('<4H',read(pg+0x4fa4,8))),start=start,result=run,ELF_anchors=4)
if phase==[3,0]and not(ss or stop or held):
 pl=u32(0x8c39d700);sub=u32(0x8c39d6fc);assert read(pl+0x100,1)==b'\0'and read(sub+0x100,1)==b'\3';proof.update(player_pos=list(struct.unpack('<3f',read(pl+0x94,12))),partner_pos=list(struct.unpack('<3f',read(sub+0x94,12))),partner_subflags=hex(struct.unpack('<H',read(sub+0x400,2))[0]))
control=json.loads((cap/'owned-window-current-stair-walk.json').read_text());proof['events']=[e for e in control['events']if not any(k in e for k in ('key','private_same_method_fast_framebuffer_decoder_preloaded'))];proof['last_sample']=control['samples'][-1]if control['samples']else None;proof['screenshot_contexts']=[json.loads(p.read_text())for p in (cap/'shots').glob('checkpoint-*/checkpoint-context.json')]
mp=cap/'readonly-motion-cache.jsonl'
if mp.exists():
 rows=[json.loads(s)for s in mp.read_text().splitlines()];active=[r for r in rows if'loads'in r]
 if active:proof['motion_first_sample']=active[0];proof['motion_last_sample']=active[-1]
out.write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({k:proof.get(k)for k in ['run','source_frame','state_sha256','room','health','player_pos','partner_pos','partner_subflags']}))