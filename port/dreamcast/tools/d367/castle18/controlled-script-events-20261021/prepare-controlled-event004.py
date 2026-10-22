from pathlib import Path
import hashlib,re,datetime
L=Path(__file__).parent
p=L/'STATUS.md';s=p.read_text(encoding='utf-8')
s=s.replace('No guest is active. The first bounded cold DBG_WARP fixture awaits concrete fixture/main review and resource allocation.','No guest is active. Controlled001/002 completed;003 closed with Ashley death before exit and no secondary-wave/transition acceptance. Independent208 fixture004 is prepared for root allocation.')
s=re.sub(r'(?m)^Doing now:.*$', 'Doing now: No active PID. CONTROLLED003 closed source518, Leon912/1440 Ashley0/600, state4600bbfe...f1ad; primary cap blocked secondary actors and death interrupted exit. Preserve legitimate failure. Preparing independent004 original r208 crank-rise/debug-pressure bypass then teleport/native204 door; no outcome flags preset.',s)
s=re.sub(r'(?m)^Next:.*$', 'Next: Review/allocate ONE controlled004 cold unit; observe actual crank rise/event return/native204. Bridge/footings/pressure plates explicitly bypassed. No003b or ordinary combat.',s)
s=re.sub(r'(?m)^State:.*$', 'State: TELEPORT_EVENT_IMPLEMENTATION ACTIVE; no guest active,004 awaits internal root allocation. Branch codex/castle18; no shared game source claims.',s);p.write_text(s,encoding='utf-8')
src=(L/'observe-controlled-r201-event003.py').read_text()
src=src.replace("cap==D/'route-walk-controlled-event003'","cap==D/'route-walk-controlled-event004'")
src=src.replace("entered208=None","entered208=None;crank_full=None;entered204=None;baseline_crank=None")
a=src.index(' captured_before=False;out=')
b=src.index(' if k.WaitForSingleObject(h,0)==258 and not closed_sent:',a)
loop=''' out=cap/'controlled-events-observations.jsonl'
 with out.open('x')as f:
  while k.WaitForSingleObject(h,0)==258 and age()<39:
   check();pg=u32(0x8c2e91dc)
   if not 0x8c000000<=pg<0x8cffa000:time.sleep(.03);continue
   room=struct.unpack('<H',read(pg+0x4f9e,2))[0];phase=list(read(pg+0x20,2))
   if room not in [0x208,0x204]:time.sleep(.03);continue
   row=dict(pg=pg,process_age=age(),frame=u32(pg+0x51e4),room=hex(room),phase=phase,Stop=hex(u32(pg+0x170)),health=list(struct.unpack('<4H',read(pg+0x4fa4,8))),status1=hex(u32(pg+0x5010)),room_flags0=hex(u32(pg+0x174)))
   pl=u32(0x8c39d700)
   if 0x8c000000<=pl<0x8cfff000:row['player_pos']=list(struct.unpack('<3f',read(pl+0x94,12)))
   if room==0x208 and phase==[3,0]:
    rd=0x8c3b9314;nr=struct.unpack('<H',read(rd+2,2))[0];sv=u32(rd+0x18);rsf=None
    if 0<nr<256 and 0x8c000000<=sv and sv+nr*0xd8<=0x8d000000:
     tb=read(sv,nr*0xd8);rsf=next((struct.unpack_from('<I',tb,i*0xd8+4)[0]for i in range(nr)if tb[i*0xd8:i*0xd8+2]==b'\\x02\\x08'),None)
    row['saved_RSF']=hex(rsf)if rsf is not None else None
    if rsf is not None and not(rsf&0x04000000):baseline_clear=True
    st=u32(0x8c3bdd64);row['crank']={}
    if 0x8c000000<=st<0x8cfff000:
     for no in [0x4e,0x4f]:
      obj=u32(st+no*4)
      if 0x8c000000<=obj<0x8cfff000:row['crank'][hex(no)]=dict(ptr=hex(obj),y=struct.unpack('<f',read(obj+0x98,4))[0])
    if baseline_crank is None and row['crank']:baseline_crank=row['crank'];events.append(dict(initial_crank=baseline_crank,frame=row['frame']))
    row['areas']={};p=0x8c3b93cc+0x8c;seen=set()
    for _ in range(1024):
     v=u32(p)
     if v==0xffffffff:break
     p=v|0x80000000
     if not 0x8c000000<=p<0x8cffff00 or p in seen:break
     seen.add(p)
     if v&0x80000000:
      no=read(p+0x36,1)[0];row['areas'][hex(no)]=dict(enabled=bool(read(p+0x34,1)[0]&1),func=hex(u32(p+0x40)))
    if u32(pg+0x5010)&0x10000000:observed_held=True
    if crank_full is None and baseline_clear and observed_held and rsf is not None and rsf&0x04000000 and all(abs(row['crank'].get(hex(no),{}).get('y',-1)-target)<.01 for no,target in [(0x4e,4984),(0x4f,4000)]) and row['areas'].get('0x2',{}).get('enabled') and int(row['areas']['0x2']['func'],16)!=0 and not(u32(pg+0x5010)&0x10000000) and u32(pg+0x170)==0:
     crank_full=row['frame'];events.append(dict(original_crank_full_and_event_return=row))
   row.update(baseline_RSF5_clear_seen=baseline_clear,event_hold_seen=observed_held,crank_full_frame=crank_full);last=row;rows.append(row);f.write(json.dumps(row)+'\\n');f.flush()
   if room==0x204 and phase==[3,0]:
    if entered204 is None:entered204=row['frame'];events.append(dict(native_room204_entry=row))
    if row['frame']>=entered204+10 or age()>38:
     events.append(dict(native_r208_door_to_r204_observed=row));capture('native-room204-entry',row);close();break
   time.sleep(.025)
'''
src=src[:a]+loop+src[b:]
src=src.replace("scope='CONTROLLED SCRIPT EVENT COVERAGE, readonlyprocess observer plus exactowned WM_CLOSE only; no gameplay memory writes or combat inputs. Nativefixture carriesprior001/002RSF0+5SETUP; actualsecondaryAEV16andoriginaldoor201to208 progressionobservedseparately; authentic294/127 neverseeded/modified.'","scope='CONTROLLED scripted coverage. Cold208 chapter/partner and DebugTrg0 pressure bypass are SETUP. Observe original crank rise and native204 transition separately. Plates/bridge/footings not exercised. Authentic294/127 untouched.'")
src=src.replace('baseline_door_y=baseline_y,baseline_RSF5_clear_seen=baseline_clear','baseline_crank=baseline_crank,crank_full_frame=crank_full,baseline_RSF5_clear_seen=baseline_clear')
compile(src,'observe004','exec');(L/'observe-controlled-r208-event004.py').write_text(src)
src=(L/'run-controlled-event003.py').read_text().replace('event003','event004').replace('events003','events004').replace('r201-event004.py','r208-event004.py').replace('b9841f3facdb4a1e1c04c72dd85bf11716b126d55b3c392b66ec02c2db91dcde','12ad4b88c83efc6ae00ea138ef713ce9162e83e02cc531ce02211bd646370db0')
src=src.replace('Native fixture initialchapter/partner/position/priorRSF0+5 aredeclaredSETUP','Native fixture initialchapter/partner/position/DebugTrg0 pressure bypass are declared SETUP')
src=src.replace('Prior001/002RSF0+5areSETUPonly; initial0C then goto60secondary16, goto320 source07door thenordinaryA360; requireactualoriginalroom208transition, recordsecondaryactoradmission/orders withoutassumingcapqueuecompleted.','Cold208 DebugTrg0 at60 bypasses plates; require original crank rise4984/4000 and event return; goto240 original204 door and A280; require actual204 load. Plates/bridge/footings not exercised.')
src=src.replace("assets=json.loads((D/'master/base-manifest.json').read_text())['st2/r201.arc']","assets={n:json.loads((D/'master/base-manifest.json').read_text())[n]for n in ['st2/r208.arc','st2/r204.arc']}")
compile(src,'run004','exec');(L/'run-controlled-event004.py').write_text(src)
src=(L/'run-controlled-event003.sh').read_text().replace('event003','event004');(L/'run-controlled-event004.sh').write_bytes(src.replace('\r','').encode())
for n in ['controlled-event004-warp.txt','observe-controlled-r208-event004.py','run-controlled-event004.py','guard-resume-41inner-47absolute-resources-v4.py']:print(n,hashlib.sha256((L/n).read_bytes()).hexdigest())
