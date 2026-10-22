"""Seal actual native cold-load010 partial title result and clean owned closure."""
from pathlib import Path
import json,hashlib,struct,shutil,datetime
L=Path(__file__).parent;R=Path(r'C:\Flycast-Evidence\re4-dreamcast\castle18-20261018\Test21');D=R/'recovered-j-content-20261021';cap=D/'route-walk-controlled-native-load011';HC=Path(r'\\wsl.localhost\Ubuntu-24.04\root\probe\codex-castle18\port\dreamcast\tools\d367\castle18\controlled-script-events-20261021');dest=HC/'controlled011';dest.mkdir(exist_ok=False)
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
g=json.loads((cap/'owned-resource-guard.json').read_text());r=json.loads((cap/'run-result.json').read_text());assert g['process_exited']and g['closed_identity']['retained_handle_signaled']and g['closed_identity']['exit_code']==0 and g['exit_age']<47.5 and r['emulator_exited']and r['early_emulator_exit']==0
assert sha(cap/'data/T0000_vmu_save_A1.bin')==sha(D/'route-walk-controlled-event009/data/T0000_vmu_save_A1.bin')=='425595f75b099a23789e09bbbd8fa4a3661072539644eae6051aa884943400b0'
protected={}
for name,expected in [('route-walk127','ec9ed07928efec777400317762bb1730a0644def73d610a1631c20381ca40e16'),('route-walk294','cb7a314b8fd0383af0b7baf17c2e87a712705beb122a1d39c7705553dd795258')]:assert sha(D/name/'data/disc.state')==expected;protected[name]=expected
h={};exec((L/'audit-authoritative-life-extended-history-20261019.py').read_text().split('targets=[')[0],h);state=cap/'data/disc.state';raw=h['decode'](state);va,code=h['load_segments'](R/'builds/c21jmW/re4dc-game.elf');rb=raw.find(code[0x4000:0x4100])-(va+0x4000-0x8c000000)
for off in [0x100000,0x120000,0x140000]:assert raw[rb+va+off-0x8c000000:rb+va+off+256-0x8c000000]==code[off:off+256]
def read(a,n):assert 0x8c000000<=a and a+n<=0x8d000000;return raw[rb+a-0x8c000000:rb+a+n-0x8c000000]
u32=lambda a:struct.unpack('<I',read(a,4))[0];pg=u32(0x8c2e91dc)
observed=dict(source_frame=u32(pg+0x51e4),phase=list(read(pg+0x20,2)),room=hex(struct.unpack('<H',read(pg+0x4f9e,2))[0]),chapter=read(pg+0x4f8a,1)[0],health_restored_from_save=list(struct.unpack('<4H',read(pg+0x4fa4,8))))
screens=[]
for p in(cap/'shots').glob('controlled-*/controlled-context.json'):
 ctx=json.loads(p.read_text());screens.append(dict(context_path=str(p),context_sha256=sha(p),context=ctx));shutil.copyfile(p,dest/(p.parent.name+'-context.json'))
lines=(cap/'run-output.txt').read_text(errors='replace').splitlines();selected=[dict(line=i+1,text=s)for i,s in enumerate(lines)if s.startswith(('fixture:','card-vmu:'))]
result=dict(scope='CONTROLLED native cold LOAD011 partial outcome, not loaded gameplay/release/hardware acceptance.',status='PASS_NATIVE_VMU_LOAD_GAME_HANDOFF_PENDING',visible_result='Inspected fb0 PNG shows original CardLoad UI during exit/fade. Native load file0 blocks12 ok1/rc0 and title5/7→5/3→7/3 occurred. Room entry/gameplay remains pending.',native_load_log_seen=any(s.startswith('card-vmu: load file=')for s in lines),state_sha256=sha(state),closed_native_fields=observed,VMU_source_and_runtime_sha256=sha(cap/'data/T0000_vmu_save_A1.bin'),source_009_unchanged=True,protected_authentic_states=protected,programme_binding_receipt_sha256=sha(D/'frozen-master-programme-binding-20261021.json'),ELF_sha256=sha(R/'builds/c21jmW/re4dc-game.elf'),master_image_sha256='b67ac21eff8d819ef9ca5f0997b4c16401cb98a3d304feb65aa4b90f7affbeb6',guard=dict(PASS_normal_owned_closure=True,owner=g['owner'],closed_identity=g['closed_identity'],exit_age=g['exit_age'],max_capture_logical_bytes=max(s['cap_logical_bytes']for s in g['samples']),minimum_runtime_free_bytes=min(s['free']for s in g['samples']),not_a_new_fail_closed_path_test=True),harness=dict(status=r['status'],elapsed_s=r['elapsed_s'],errors=r['errors']),screenshots=screens,fixture_and_card_log=selected,next='No retry or following guest allocated. Preserve exact010 state; review remaining native source-gated pad state before a bounded same-lineage continuation. Teleport/event progression waits until actualLoad context is established.')
assert result['native_load_log_seen']
gc=(D/'controlled009-private-VMU-readback/RE4DCS01A-reconstructed-GC.bin').read_bytes();digest=2166136261
for x in gc[0x2000:0xeaf8]:digest=((digest^x)*16777619)&0xffffffff
assert digest==0xa569c07d and any('card-vmu: load digest file=0 a569c07d'in x for x in lines)
result['exact_saved_payload_byte_FNV_matches_runtime_load']=hex(digest)
rd=0x8c3b9314;nr=struct.unpack('<H',read(rd+2,2))[0];sv=u32(rd+0x18);saved_RSF204=None
if 0<nr<256 and 0x8c000000<=sv and sv+nr*0xd8<=0x8d000000:
 table=read(sv,nr*0xd8);saved_RSF204=next((struct.unpack_from('<I',table,i*0xd8+4)[0]for i in range(nr)if table[i*0xd8:i*0xd8+2]==bytes([2,4])),None)
result['saved_RSF204']=hex(saved_RSF204)if saved_RSF204 is not None else None
result['next']='No guest allocated. Prepare read-only exact011state continuation to finish original TitleExit/GameTask and observe original R204Init/radio if savedRSF0set/7clear. No rearm, input or outcome edits.'
p=D/'controlled-native-load011-closed-handback.json';assert not p.exists();p.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');shutil.copyfile(p,dest/'HANDBACK.json')
for n in ['owned-resource-guard.json','owned-process.json','run-start.json','run-result.json','controlled-native-load-observer-summary.json']:shutil.copyfile(cap/n,dest/n)
shutil.copyfile(D/'frozen-master-programme-binding-20261021.json',dest/'exact-programme-binding.json');shutil.copyfile(L/'LOAD011-ROOT-ALLOCATION.json',dest/'ROOT-ALLOCATION.json');shutil.copyfile(L/'seal-controlled-native-load011.py',HC/'seal-controlled-native-load011.py')
(cap/'KEEP').write_text('Preserve native cold LOAD011 successful native VMU load, actual state b9a39fbf, unchanged009 VMU, screenshots and V5 cleanclosure receipts. Game handoff/room entry remains pending. No deletion/retarget.\n')
intro='CURRENT: LOAD011 closed cleanly under V5, exit0 at39.575 seconds. Original native VMU load passed (12 blocks, ok1, rc0, exact saved-byte digest). The title-to-game handoff is pending, so no room-entry/gameplay or radio acceptance yet. Actual009 VMU and authentic127/294 are unchanged. State b9a39fbf is preserved. No next guest is allocated.\n\n'
for n in ['STATUS.md','HANDBACK.md','INBOX.md']:
 q=L/n;s=q.read_text(encoding='utf-8');q.write_text(intro+s,encoding='utf-8')
print(json.dumps(dict(handback_sha256=sha(p),closed_native_fields=observed,state_sha256=sha(state),guard_exit_age=g['exit_age'],maximum_cap=max(s['cap_logical_bytes']for s in g['samples']))))
