from pathlib import Path
import hashlib
L=Path(__file__).parent
src=(L/'observe-controlled-r204-event008.py').read_text().replace("cap==D/'route-walk-controlled-event008'","cap==D/'route-walk-controlled-event009'")
a=src.index('def pulse_action():');b=src.index('def close():',a)
helper='''def native_card():
 p=u32(0x8c396744)
 if not 0x8c000000<=p<0x8cfff000:return None
 return dict(ptr=hex(p),routines=list(read(p+4,4)),status=hex(u32(p+0x10)),type=struct.unpack('<i',read(p+0x14,4))[0],slot=read(p+0x1c,1)[0],save_no=read(p+0x1d,1)[0],error=struct.unpack('<i',read(p+0x20,4))[0])

def native_message():
 return dict(table_size=read(0x8c3b6938,1)[0],selection=read(0x8c3b6939,1)[0],current=read(0x8c3b693a,1)[0],button=read(0x8c3b684c+0x7c,1)[0],attribute=hex(u32(0x8c3b684c+0x8c)))

def pulse_ui(kind):
 check();assert age()<30,'UI action admission margin';wins=[]
 @CALL
 def cb(w,_):
  p=W.DWORD();u.GetWindowThreadProcessId(w,C.byref(p));b=C.create_unicode_buffer(256);u.GetClassNameW(w,b,256)
  if p.value==owner['pid']and b.value=='SDL_app':wins.append(int(w))
  return True
 assert u.EnumWindows(cb,0)and len(wins)==1;hwnd=wins[0];held=False;ack=[]
 try:
  check();pg_now=u32(0x8c2e91dc);assert 0x8c000000<=pg_now<0x8cffa000 and read(pg_now+0x4f8a,1)[0]==7 and u32(0x8c39d6fc)==0
  c=native_card();m=native_message();assert c and c['type']==1 and c['slot']==0 and c['save_no']==0 and c['error']==0
  if kind=='slot-A':
   assert c['routines'][:2]==[2,1];vk,scan,ext=ord('X'),0x2d,0
  else:
   assert c['routines'][:2]==[2,6] and m['table_size']==2 and m['selection']==0 and m['button']==1
   if kind=='confirm-A':assert m['current']==0;vk,scan,ext=ord('X'),0x2d,0
   else:
    assert kind=='choose-Yes' and m['current']==1
    vk,scan,ext=(0x26,0x48,1)if int(m['attribute'],16)&0x00800000 else(0x25,0x4b,1)
  assert age()<30;events.append(dict(immediate_native_save_UI_recheck=kind,card=c,message=m,process_age=age()))
  assert u.PostMessageW(hwnd,0x100,vk,1|(scan<<16)|(ext<<24));held=True;until=time.monotonic()+.2
  while time.monotonic()<until:
   check();assert age()<40.5;ack.append(dict(frame=u32(u32(0x8c2e91dc)+0x51e4),Key_trg=hex(u32(0x8c3a948c+24)),message=native_message()));time.sleep(.02)
 finally:
  if held:
   check();p=W.DWORD();u.GetWindowThreadProcessId(hwnd,C.byref(p));assert p.value==owner['pid'];assert u.PostMessageW(hwnd,0x101,vk,1|(scan<<16)|(ext<<24)|0xc0000000)
 events.append(dict(ordinary_source_UI_pulse=kind,seconds=.2,source_ack=ack,release_before_age=age()))

'''
src=src[:a]+helper+src[b:]
src=src.replace('action_age=None;card_shot=False','action_age=None;card_shot=False;direction_age=None;confirmed_age=None;confirmation_shot=False')
src=src.replace("row['CardStatus']=hex(u32(pg+8));row['message0']=dict(table_size=read(0x8c3b6938,1)[0],selection=read(0x8c3b6939,1)[0],current=read(0x8c3b693a,1)[0],button=read(0x8c3b684c+0x7c,1)[0],attribute=hex(u32(0x8c3b684c+0x8c)))", "row['CardStatus']=hex(u32(pg+8));row['message0']=native_message();row['card']=native_card()")
a=src.index("   m=row['message0']");b=src.index("   if not chapter_seen",a)
src=src[:a]+'''   m=row['message0'];c=row['card']
   if c and c['type']==1 and c['slot']==0 and c['save_no']==0 and c['error']==0:
    if action_age is None and 2<age()<25 and c['routines'][:2]==[2,1]:
     pulse_ui('slot-A');action_age=age()
    elif action_age is not None and confirmed_age is None and c['routines'][:2]==[2,6] and m['table_size']==2 and m['selection']==0 and m['button']==1:
     if not confirmation_shot:
      try:capture('original-empty-slot-confirmation',row)
      except Exception as e:events.append(dict(optional_confirmation_capture_unavailable=repr(e)))
      confirmation_shot=True
     if m['current']==1 and direction_age is None and age()<28:
      pulse_ui('choose-Yes');direction_age=age()
     elif m['current']==0 and (direction_age is None or age()>direction_age+.2) and age()<29:
      pulse_ui('confirm-A');confirmed_age=age()
   if confirmed_age is not None and not card_shot and age()>confirmed_age+6 and age()<35:
    try:capture('original-save-result',row)
    except Exception as e:events.append(dict(optional_save_result_capture_unavailable=repr(e)))
    card_shot=True
'''+src[b:]
src=src.replace('Exactly one ordinaryA pulse at coherent native SaveYes prompt; no later blind buttons.','Consolidated source save UI: normalA at Slot01, chooseYes from actual confirmation/current/attrs, confirmA; maxthreepulses with immediate native UI rechecks; no blind followups.')
src=src.replace('CONTROLLED EVENT COVERAGE, read-only observer/no input','CONTROLLED source save UI, read-only guest memory plus exact-owned normal key messages; no memory writes').replace('CONTROLLED direct continuation of closed006 movie state.','CONTROLLED direct continuation of closed008 CardSave Slot01 state.').replace('baseline_crank=baseline_crank,crank_full_frame=crank_full,baseline_RSF5_clear_seen=baseline_clear','baseline_RSF0_clear_seen=baseline_clear').replace("capture('original-r204-event-start',row)","capture('original-save-slot-start',row)")
compile(src,'observe009','exec');(L/'observe-controlled-r204-event009.py').write_text(src)
src=(L/'run-controlled-event008.py').read_text().replace("cap=D/'route-walk-controlled-event008'","cap=D/'route-walk-controlled-event009'").replace("observer=L/'observe-controlled-r204-event008.py'","observer=L/'observe-controlled-r204-event009.py'").replace("seed=D/'route-walk-controlled-event007/data'","seed=D/'route-walk-controlled-event008/data'").replace('e20edc2f58299c01b890e97cc321945a6e0d6d6459e18a768d14d87507f567b0','739bbcf1a551961d4b95c44079283f3a6879e4cddd3f1f242ae867f10f31cd8c').replace('closed controlled007 chapterresults snapshot','closed controlled008 originalCardSaveUI snapshot').replace('Continue007 actualSaveYes prompt without replay/rearm; one ordinaryownedA pulse then observe originalCardSaveUI. No later blindbuttons/outcome edits; savewrite/radio require actual evidence.','Continue008 actualSlot01 empty saveUI; ordinaryA, sourceconfirmation chooseYes by actualattrs/current, confirmA; max3ownedpulses onlyatnativeUIpredicates. Observe sourcewrite/VMUdelta/result; no outcome edits/rearm.').replace('chapter-save008','chapter-write009').replace("print('Controlledevent008 closed;","print('Controlledevent009 closed;")
compile(src,'run009','exec');(L/'run-controlled-event009.py').write_text(src)
src=(L/'run-controlled-event008.sh').read_text().replace('event008','event009');(L/'run-controlled-event009.sh').write_bytes(src.replace('\r','').encode())
for n in ['observe-controlled-r204-event009.py','run-controlled-event009.py']:print(n,hashlib.sha256((L/n).read_bytes()).hexdigest())
