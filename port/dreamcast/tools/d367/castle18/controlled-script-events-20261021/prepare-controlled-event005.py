from pathlib import Path
import hashlib,re
L=Path(__file__).parent
src=(L/'observe-controlled-r208-event004.py').read_text().replace("cap==D/'route-walk-controlled-event004'","cap==D/'route-walk-controlled-event005'")
a=src.index(" out=cap/'controlled-events-observations.jsonl'");b=src.index(' if k.WaitForSingleObject(h,0)==258 and not closed_sent:',a)
loop=''' out=cap/'controlled-events-observations.jsonl';movie_shot=False;chapter_seen=False
 with out.open('x')as f:
  while k.WaitForSingleObject(h,0)==258 and age()<39:
   check();pg=u32(0x8c2e91dc)
   if not 0x8c000000<=pg<0x8cffa000:time.sleep(.03);continue
   room=struct.unpack('<H',read(pg+0x4f9e,2))[0]
   if room!=0x204:time.sleep(.03);continue
   row=dict(pg=pg,process_age=age(),frame=u32(pg+0x51e4),room=hex(room),phase=list(read(pg+0x20,2)),Stop=hex(u32(pg+0x170)),health=list(struct.unpack('<4H',read(pg+0x4fa4,8))),status1=hex(u32(pg+0x5010)),status3=hex(u32(pg+0x5018)),chapter=read(pg+0x4f8a,1)[0],partner_ptr=hex(u32(0x8c39d6fc)))
   pl=u32(0x8c39d700)
   if 0x8c000000<=pl<0x8cfff000:row['player_pos']=list(struct.unpack('<3f',read(pl+0x94,12)))
   rd=0x8c3b9314;nr=struct.unpack('<H',read(rd+2,2))[0];sv=u32(rd+0x18);rsf=None
   if 0<nr<256 and 0x8c000000<=sv and sv+nr*0xd8<=0x8d000000:
    tb=read(sv,nr*0xd8);rsf=next((struct.unpack_from('<I',tb,i*0xd8+4)[0]for i in range(nr)if tb[i*0xd8:i*0xd8+2]==b'\\x02\\x04'),None)
   row['saved_RSF']=hex(rsf)if rsf is not None else None
   if rsf is not None and not(rsf&0x80000000):baseline_clear=True
   if u32(pg+0x5010)&0x10000000:observed_held=True
   row.update(baseline_RSF0_clear_seen=baseline_clear,event_hold_seen=observed_held);last=row;rows.append(row);f.write(json.dumps(row)+'\\n');f.flush()
   if not movie_shot and rsf is not None and rsf&0x80000000 and age()<35:
    events.append(dict(original_event_RSF0_early=row));capture('original-r204-event-start',row);movie_shot=True
   if not chapter_seen and row['chapter']!=6:
    events.append(dict(chapter_task_early_transition=row));chapter_seen=True
   time.sleep(.025)
'''
src=src[:a]+loop+src[b:]
src=src.replace("scope='CONTROLLED scripted coverage. Cold208 chapter/partner and DebugTrg0 pressure bypass are SETUP. Observe original crank rise and native204 transition separately. Plates/bridge/footings not exercised. Authentic294/127 untouched.'","scope='CONTROLLED cold204 original scripted event coverage. Chapter6/partner/initialAEV2 are SETUP; no event outcome bits preset. Early RSF0/chapter7/RSF7 do not prove movieEOF/resultsUI/savewrite/radio. Authentic127/294 untouched.'")
compile(src,'observe005','exec');(L/'observe-controlled-r204-event005.py').write_text(src)
src=(L/'run-controlled-event004.py').read_text().replace('event004','event005').replace('r208-event005','r204-event005').replace('12ad4b88c83efc6ae00ea138ef713ce9162e83e02cc531ce02211bd646370db0','43c17e26bf7cbfbf027daeaa5e2c61c42029e5139cce93b295ea11bdee4400e1')
src=src.replace('castle21-CONTROLLED-r208-crank-exit004','castle21-CONTROLLED-r204-chapter-event005').replace('Native fixture initialchapter/partner/position/DebugTrg0 pressure bypass are declared SETUP','Native fixture initialchapter6/partner/position in originalAEV2 are declared SETUP')
src=src.replace('Cold208 DebugTrg0 at60 bypasses plates; require original crank rise4984/4000 and event return; goto240 original204 door and A280; require actual204 load. Plates/bridge/footings not exercised.','Cold204 originalAEV2 triggers r204EventExec/movie20400/chapter-end task. Early flags/chapter transitions are recorded separately from actualEOF/resultsUI/savewrite/radio. Preserve continuation if bounded stop midstage.')
src=src.replace("for n in ['st2/r208.arc','st2/r204.arc']","for n in ['st2/r204.arc']")
compile(src,'run005','exec');(L/'run-controlled-event005.py').write_text(src)
src=(L/'run-controlled-event004.sh').read_text().replace('event004','event005');(L/'run-controlled-event005.sh').write_bytes(src.replace('\r','').encode())
p=L/'STATUS.md';s=p.read_text(encoding='utf-8');s=re.sub(r'(?m)^Doing now:.*$', 'Doing now: No active PID. CONTROLLED004 closed source486 room204 phase2/loading, state9904d44d...ad36, health1440/600. Original208 crank full/end PASS at316; native door initiated204 load, phase3 arrival not yet accepted. Preparing005 cold204 actualAEV2→movie/chapter UI; no outcome flags or buttons preset.',s);s=re.sub(r'(?m)^Next:.*$', 'Next: Root reviews/allocates ONE005 controlled204 event unit; distinguish movieEOF/resultsUI/savewrite/radio. Preserve continuation if41s ends midstage. No combat or hostile003 replay.',s);p.write_text(s,encoding='utf-8')
for n in ['controlled-event005-warp.txt','observe-controlled-r204-event005.py','run-controlled-event005.py']:print(n,hashlib.sha256((L/n).read_bytes()).hexdigest())
