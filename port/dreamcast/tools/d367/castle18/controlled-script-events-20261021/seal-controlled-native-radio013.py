"""Seal actual native cold-load010 partial title result and clean owned closure."""
from pathlib import Path
import json,hashlib,struct,shutil,datetime
L=Path(__file__).parent;R=Path(r'C:\Flycast-Evidence\re4-dreamcast\castle18-20261018\Test21');D=R/'recovered-j-content-20261021';cap=D/'route-walk-controlled-native-radio013';HC=Path(r'\\wsl.localhost\Ubuntu-24.04\root\probe\codex-castle18\port\dreamcast\tools\d367\castle18\controlled-script-events-20261021');dest=HC/'controlled013';dest.mkdir(exist_ok=False)
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
result=dict(scope='CONTROLLED exact012 fullstate continuation, originalradio return and visiblegameplay verified. No authenticcombat, audio/sync, performance, release or hardwareacceptance.',status='PASS_ORIGINAL_RADIO_RETURN_AND_GAMEPLAY',visible_result='Originalradio streamstopped/closed; fresh backingclose hash15e45996 ok, Stopreturned0, postreturn sourceframesadvance. Inspectedafter-radio-close PNG showsLeon/gameworld/HUD in204. No input/skip added; audio/sync/hardware remainunassessed.',native_load_log_seen=any(s.startswith('card-vmu: load file=')for s in lines),state_sha256=sha(state),closed_native_fields=observed,VMU_source_and_runtime_sha256=sha(cap/'data/T0000_vmu_save_A1.bin'),source_009_unchanged=True,protected_authentic_states=protected,programme_binding_receipt_sha256=sha(D/'frozen-master-programme-binding-20261021.json'),ELF_sha256=sha(R/'builds/c21jmW/re4dc-game.elf'),master_image_sha256='b67ac21eff8d819ef9ca5f0997b4c16401cb98a3d304feb65aa4b90f7affbeb6',guard=dict(PASS_normal_owned_closure=True,owner=g['owner'],closed_identity=g['closed_identity'],exit_age=g['exit_age'],max_capture_logical_bytes=max(s['cap_logical_bytes']for s in g['samples']),minimum_runtime_free_bytes=min(s['free']for s in g['samples']),not_a_new_fail_closed_path_test=True),harness=dict(status=r['status'],elapsed_s=r['elapsed_s'],errors=r['errors']),screenshots=screens,fixture_and_card_log=selected,next='No retry or following guest allocated. Preserve exact010 state; review remaining native source-gated pad state before a bounded same-lineage continuation. Teleport/event progression waits until actualLoad context is established.')
import re
prior=(D/'route-walk-controlled-native-handoff012/run-output.txt').read_text(errors='replace');assert 'subscreen backing: close'not in prior
matches=[x for x in lines if re.search(r'subscreen backing: close area=.*hash=15e45996 ok\b',x)];assert len(matches)==1,matches
obs=json.loads((cap/'controlled-native-load-observer-summary.json').read_text());close=next(x for x in obs['events']if x.get('backing_close_log'));assert close['hash']=='15e45996'and close['result']=='ok'
rows=[json.loads(x)for x in(cap/'controlled-load-observations.jsonl').read_text().splitlines()]
post=[x for x in rows if x['process_age']>=close['process_age']and x['Stop']=='0x0'and x['phase'][0]==3 and x['room']=='0x204'];assert len(post)>2 and post[-1]['frame']>post[0]['frame']
assert sha(D/'route-walk-controlled-native-handoff012/data/disc.state')=='64a178245be5dd8b9dbb14ec1a4f4da0e8be08b3d5041e8c6b0388ab0b809436'
assert sha(D/'route-walk-controlled-native-load011/data/disc.state')=='b9a39fbffe221e840f50041eea820cbc75f4720a7b74560e34dc2b74be60339e'
result['protected_012_seed_state_sha256']=sha(D/'route-walk-controlled-native-handoff012/data/disc.state')
result['native_LOAD011_previous_success']='Originalcoldload file0/CRC/digesta569c07d at7bcfd6c2e; restoredlogrecords are not a secondcoldload.'
result['prior012_radio_execution']='Native204entry andoriginalSalazar/Leoncodec execution at31a3e7849, ongoingatitsdeadline.'
result['radio_return']=dict(new_backingclose=matches[0],close_event=close,Stop_returned_zero=True,postreturn_source_frame_interval=[post[0]['frame'],post[-1]['frame']],postreturn_rows=len(post),afterclose_gameworld_HUD_PNG_inspected=True,stream1_154_stopped=any('stream 1:154 stopped'in x for x in lines),stream1_154_closed=any('stream 1:154 closed'in x for x in lines),audible_quality_or_sync_assessed=False)
rd=0x8c3b9314;nr=struct.unpack('<H',read(rd+2,2))[0];sv=u32(rd+0x18);saved_RSF204=None
if 0<nr<256 and 0x8c000000<=sv and sv+nr*0xd8<=0x8d000000:
 table=read(sv,nr*0xd8);saved_RSF204=next((struct.unpack_from('<I',table,i*0xd8+4)[0]for i in range(nr)if table[i*0xd8:i*0xd8+2]==bytes([2,4])),None)
result['saved_RSF204']=hex(saved_RSF204)if saved_RSF204 is not None else None
result['next']='No followingguest allocated. Originalradio return iscomplete; preserveactual013 state andprepare nextchapter nativeevent route onlyunderrootcoordination.'
p=D/'controlled-native-radio013-closed-handback.json';assert not p.exists();p.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');shutil.copyfile(p,dest/'HANDBACK.json')
for n in ['owned-resource-guard.json','owned-process.json','run-start.json','run-result.json','controlled-native-load-observer-summary.json']:shutil.copyfile(cap/n,dest/n)
shutil.copyfile(D/'frozen-master-programme-binding-20261021.json',dest/'exact-programme-binding.json');shutil.copyfile(L/'RADIO013-ROOT-ALLOCATION.json',dest/'ROOT-ALLOCATION.json');shutil.copyfile(L/'seal-controlled-native-radio013.py',HC/'seal-controlled-native-radio013.py')
(cap/'KEEP').write_text('Preserve controlledRADIO013 originalradio return/gameplay, newbackinghash15e45996ok, actualstate/unchanged009VMU/prior011+012seeds, PNGcontexts and V5cleanclosure receipts. No audio/sync/hardware claim. No deletion/retarget.\n')
intro='CURRENT: RADIO013 closed cleanly under V5, exit0 at39.825 seconds. Originalradio return passed: new backingclose hash15e45996 ok, Stop0/postreturn sourceframe advance and inspectedLeon/gameworld/HUD capture. No input or skip was added. No followingguest isallocated. Actual013 stateis preserved; authentic127/294, actual009VMU andprior011/012seeds remainunchanged. Audio/sync/hardwareacceptance separate.\n\n'
for n in ['STATUS.md','HANDBACK.md','INBOX.md']:
 q=L/n;s=q.read_text(encoding='utf-8');q.write_text(intro+s,encoding='utf-8')
print(json.dumps(dict(handback_sha256=sha(p),closed_native_fields=observed,state_sha256=sha(state),guard_exit_age=g['exit_age'],maximum_cap=max(s['cap_logical_bytes']for s in g['samples']))))
