from pathlib import Path
import json,hashlib,struct,datetime,shutil,re
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18');R=Path(r'C:\Flycast-Evidence\re4-dreamcast\castle18-20261018\Test21');D=R/'recovered-j-content-20261021';C=D/'route-walk-controlled-ch32-drain015';H=Path(r'\\wsl.localhost\Ubuntu-24.04\root\probe\codex-castle18\port\dreamcast\tools\d367\castle18\controlled-script-events-20261021')
def sha(p):
 with p.open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
g=json.loads((C/'owned-resource-guard.json').read_text());o=json.loads((C/'controlled-drain015-observer-summary.json').read_text());run=json.loads((C/'run-result.json').read_text());assert g['owner']['pid']==58264 and g['process_exited']and g['closed_identity']['retained_handle_signaled']and g['closed_identity']['exit_code']==0 and g['exit_age']<47.5 and not g['actions']and run['emulator_exited']and not run['errors']
state=C/'data/disc.state';s=sha(state);h={};exec((L/'audit-authoritative-life-extended-history-20261019.py').read_text().split('targets=[')[0],h);raw=h['decode'](state);va,code=h['load_segments'](R/'builds/c21jmW/re4dc-game.elf');rb=raw.find(code[0x4000:0x4100])-(va+0x4000-0x8c000000)
for off in [0x4000,0x100000,0x120000,0x140000]:assert raw[rb+va+off-0x8c000000:rb+va+off+256-0x8c000000]==code[off:off+256]
def read(a,n):assert 0x8c000000<=a and a+n<=0x8d000000;return raw[rb+a-0x8c000000:rb+a+n-0x8c000000]
u32=lambda a:struct.unpack('<I',read(a,4))[0];pg=u32(0x8c2e91dc);rd=0x8c3b9314;nr=struct.unpack('<H',read(rd+2,2))[0];sv=u32(rd+24);tb=read(sv,nr*0xd8);rsf=next(struct.unpack_from('<I',tb,i*0xd8+4)[0]for i in range(nr)if tb[i*0xd8:i*0xd8+2]==b'\x02\x05')
fields=dict(frame=u32(pg+0x51e4),room=hex(struct.unpack('<H',read(pg+0x4f9e,2))[0]),phase=list(read(pg+0x20,2)),chapter=read(pg+0x4f8a,1)[0],Stop=hex(u32(pg+0x170)),status1=hex(u32(pg+0x5010)),health=list(struct.unpack('<4H',read(pg+0x4fa4,8))),RSF205=hex(rsf),Key_on=hex(u32(0x8c3a948c+16)),Key_trg=hex(u32(0x8c3a948c+24)))
areas={}
for n,v in o['last']['areas'].items():p=v['ptr'];areas[n]=dict(enabled=bool(read(p+0x34,1)[0]&1),func=hex(u32(p+0x40)))
actors=[];p=u32(0x8c39d3b8+20);seen=set()
while p and p not in seen and len(seen)<128:
 seen.add(p);b=read(p,0x3c8);fl=struct.unpack_from('<I',b,4)[0];st=struct.unpack_from('<I',b,0x3c4)[0];actors.append(dict(ptr=hex(p),id=b[0x100],type=b[0x101],source_list=hex(b[0x398]),HP=struct.unpack_from('<h',b,0x320)[0],be_flag=hex(fl),native_status=hex(st),source_active=(fl&0x201==1 and bool(st&0x20))));p=struct.unpack_from('<I',b,8)[0]
assert not p;assert fields['Stop']=='0x0'and rsf&0xc0000000==0xc0000000 and not(u32(pg+0x5010)&0x10000000)
assert all(not areas[x]['enabled']for x in['0x7','0x8','0x15'])and areas['0x11']['enabled']and areas['0x1b']['func']!='0x0'
pulses=[];rechecks=[];ends=[]
for e in o['events']:
 if 'ordinary_owned_UI_pulse'in e:pulses.append(e)
 if 'immediate_input_recheck'in e:
  v=e['row'];rechecks.append(dict(kind=e['immediate_input_recheck'],fields={k:v.get(k)for k in ['frame','process_age','Stop','saved_RSF205','message0','message0_source_identity','live_native_code_anchors_verified']}))
 if 'original_drain_end_observed'in e:
  v=e['original_drain_end_observed'];ends.append({k:v.get(k)for k in ['frame','process_age','Stop','status1','saved_RSF205','source68_active_observed']})
assert[p['ordinary_owned_UI_pulse']for p in pulses]==['advance-intro-A','confirm-Yes']and len(ends)==1
protected={}
old=json.loads((D/'controlled-ch32-drain014-closed-audit.json').read_text())
for n,v in old['protected_inputs'].items():assert sha(D/n)==v;protected[n]=v
for n,v in [('route-walk-controlled-ch32-drain014/data/disc.state','3713cb2a4442ec5ddbf3dc4aec8dff107aa66721913e75813858c326a820adc5')]:assert sha(D/n)==v;protected[n]=v
runtimeVMU=sha(C/'data/T0000_vmu_save_A1.bin');assert runtimeVMU=='425595f75b099a23789e09bbbd8fa4a3661072539644eae6051aa884943400b0'
photos=[]
for context in(C/'shots').glob('*/controlled-context.json'):photos.append(dict(path=str(context),sha256=sha(context),PNGs=[dict(path=str(q),sha256=sha(q))for q in(context.parent/'frames').glob('*.png')]))
identities={n:sha(L/n)for n in ['observe-controlled-ch32-drain015.py','run-controlled-ch32-drain015.py','run-controlled-ch32-drain015.sh','controlled-ch32-drain015-pins.json','DRAIN015-ROOT-ALLOCATION.json']}
logs={n:dict(path=str(C/n),sha256=sha(C/n),bytes=(C/n).stat().st_size)for n in ['controlled-drain015-observations.jsonl','run-output.txt','controlled-drain015-observer-summary.json','owned-resource-guard.json']}
audit=dict(scope='CLOSED015 read-only file/state audit; no live attach/input/reexecution/newguest. Controlled teleport/script lineage; inherited014intro notnewprogress.',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),functional_result='PASS original native page/Yes/drain-end and expected areas/Stop return. Actor0x68 active NOTobserved; reason unresolved, absence doesNOTprove held. Native upperdoor and nextroom NOTtested.',supervisor_result='PASS retained V5 handle signaled/exit0',guard={k:v for k,v in g.items()if k!='samples'},guard_minimum_free=min(x['free']for x in g['samples']),guard_maximum_cap=max(x['cap_logical_bytes']for x in g['samples']),harness=run,actual_rechecks=rechecks,actual_pulses=pulses,first_drain_end=ends,closed_state=dict(path=str(state),sha256=s,mainELF_anchor_matches=4,fields=fields,areas=areas,source68=[v for v in actors if v['source_list']=='0x68'],observed_active_source_lists=[v for v in actors if v['source_active']],actor68_census='No source-list0x68 actor in final full pAlive chain. Do not infer cause.'),save=dict(runtimeVMU_sha256=runtimeVMU,source009_unchanged=True,nativeCardSave_claim=False),programme=json.loads((D/'controlled014-source-programme-assets.json').read_text()),source_and_allocation_sha256=identities,raw_log_references=logs,screenshots=photos,protected_inputs_fresh=protected,next='No nextguest allocated. Root views PNG acceptance and decides next original route unit after this sealed result.',physical_or_release_acceptance=False)
P=D/'controlled-ch32-drain015-closed-audit.json';assert not P.exists();P.write_text(json.dumps(audit,indent=2)+'\n',encoding='utf-8');assert sha(state)==s
keep=C/'KEEP-CONTROLLED015.txt';assert not keep.exists();keep.write_text('Preserve actual015 original page/Yes/drain-end, actor68 observationgap, exact state'+s+' and all raw logs/PNGs. Audit'+sha(P)+'. No hardware/release claim.\n')
A=H/'controlled015-actual';assert not A.exists();A.mkdir();(A/'.gitattributes').write_bytes(b'* -text\n')
for n in ['owned-resource-guard.json','controlled-drain015-observer-summary.json','run-result.json','run-start.json','owned-process.json','KEEP-CONTROLLED015.txt']:shutil.copyfile(C/n,A/n)
shutil.copyfile(P,A/P.name);shutil.copyfile(L/'DRAIN015-ROOT-ALLOCATION.json',A/'DRAIN015-ROOT-ALLOCATION.json')
seal={p.name:dict(bytes=p.stat().st_size,sha256=sha(p))for p in A.iterdir()};(A/'SEAL.json').write_text(json.dumps(seal,indent=2)+'\n')
header='CURRENT: ACTUAL015 CLOSED. Original page-A -> native Yes -> drain-end/expected area changes/Stop0 passed in controlled Flycast lineage. V5 retained exit0 at39.676s; state'+s[:8]+'/source'+str(fields['frame'])+' preserved. Actor0x68 NOT observed active; reason unresolved, not proof of held. No next guest allocation. Authentic127/294, actual013/014 and009VMU unchanged; no new inputs/attach/reexecution.'
for n in ['STATUS.md','HANDBACK.md','INBOX.md']:
 p=L/n;t=p.read_text(encoding='utf-8');p.write_text(header+t[t.index('\n\n'):],encoding='utf-8')
print(json.dumps(dict(state_sha256=s,audit_sha256=sha(P),audit_bytes=P.stat().st_size,mirror_bytes=sum(p.stat().st_size for p in A.iterdir()),closed_fields=fields,areas=areas,first_end=ends,actor68=[]),indent=2))
