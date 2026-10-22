from pathlib import Path
import hashlib
L=Path(__file__).parent
src=(L/'observe-controlled-r204-event007.py').read_text().replace("cap==D/'route-walk-controlled-event007'","cap==D/'route-walk-controlled-event008'")
src=src.replace("def close():",'''def pulse_action():
 check();assert age()<35,'Action admission margin';wins=[]
 @CALL
 def cb(w,_):
  p=W.DWORD();u.GetWindowThreadProcessId(w,C.byref(p));b=C.create_unicode_buffer(256);u.GetClassNameW(w,b,256)
  if p.value==owner['pid']and b.value=='SDL_app':wins.append(int(w))
  return True
 assert u.EnumWindows(cb,0)and len(wins)==1;hwnd=wins[0];held=False;ack=[]
 try:
  check();assert u.PostMessageW(hwnd,0x100,ord('X'),1|(0x2d<<16));held=True;until=time.monotonic()+.2
  while time.monotonic()<until:
   check();assert age()<40.5;ack.append(dict(frame=u32(u32(0x8c2e91dc)+0x51e4),Key_trg=hex(u32(0x8c3a948c+24))));time.sleep(.02)
 finally:
  if held:
   check();p=W.DWORD();u.GetWindowThreadProcessId(hwnd,C.byref(p));assert p.value==owner['pid'];assert u.PostMessageW(hwnd,0x101,ord('X'),1|(0x2d<<16)|0xc0000000)
 events.append(dict(ordinary_A_X_pulse_seconds=.2,source_Key_trg_samples=ack,release_before_age=age()))

def close():''')
src=src.replace("out=cap/'controlled-events-observations.jsonl';movie_shot=False;chapter_seen=False","out=cap/'controlled-events-observations.jsonl';movie_shot=False;chapter_seen=False;action_age=None;card_shot=False")
src=src.replace("row['saved_RSF']=hex(rsf)if rsf is not None else None", "row['saved_RSF']=hex(rsf)if rsf is not None else None\n   row['CardStatus']=hex(u32(pg+8));row['message0']=dict(table_size=read(0x8c3b6938,1)[0],selection=read(0x8c3b6939,1)[0],current=read(0x8c3b693a,1)[0],button=read(0x8c3b684c+0x7c,1)[0],attribute=hex(u32(0x8c3b684c+0x8c)))")
needle="   if not chapter_seen and row['chapter']!=6:"
insert="""   m=row['message0']
   if action_age is None and 2<age()<30 and row['chapter']==7 and row['partner_ptr']=='0x0' and rsf is not None and rsf&0x80000000 and (m['table_size'],m['selection'],m['current'],m['button'],m['attribute'])==(2,0,0,1,'0x1001'):
    events.append(dict(actual_native_Save_Yes_prompt_before_A=row));pulse_action();action_age=age()
   if action_age is not None and not card_shot and age()>action_age+6 and age()<35:
    try:capture('original-chapter-CardSave-after-A',row)
    except Exception as e:events.append(dict(optional_CardSave_capture_unavailable=repr(e)))
    card_shot=True
"""
assert needle in src;src=src.replace(needle,insert+needle)
src=src.replace('No rearm/outcome state edits or gameplay buttons.','No rearm/outcome state edits. Exactly one ordinaryA pulse at coherent native SaveYes prompt; no later blind buttons.')
compile(src,'observe008','exec');(L/'observe-controlled-r204-event008.py').write_text(src)
src=(L/'run-controlled-event007.py').read_text().replace("cap=D/'route-walk-controlled-event007'","cap=D/'route-walk-controlled-event008'").replace("observer=L/'observe-controlled-r204-event007.py'","observer=L/'observe-controlled-r204-event008.py'").replace("seed=D/'route-walk-controlled-event006/data'","seed=D/'route-walk-controlled-event007/data'").replace('606f9193c58c5e9d5df4b5374a3b4d4e864914f25b8da6ee09c4fd842dd672ff','e20edc2f58299c01b890e97cc321945a6e0d6d6459e18a768d14d87507f567b0').replace('closed controlled006 movie snapshot','closed controlled007 chapterresults snapshot').replace('Continue006 in-progress movie20400 without replay/rearm; observe actualEOF/chapter results/saveprompt separately; no buttons/savewrites in this unit. Earlyflags are not completion.','Continue007 actualSaveYes prompt without replay/rearm; one ordinaryownedA pulse then observe originalCardSaveUI. No later blindbuttons/outcome edits; savewrite/radio require actual evidence.').replace('movie-continuation007','chapter-save008').replace("print('Controlledevent007 closed;","print('Controlledevent008 closed;")
compile(src,'run008','exec');(L/'run-controlled-event008.py').write_text(src)
src=(L/'run-controlled-event007.sh').read_text().replace('event007','event008');(L/'run-controlled-event008.sh').write_bytes(src.replace('\r','').encode())
for n in ['observe-controlled-r204-event008.py','run-controlled-event008.py']:print(n,hashlib.sha256((L/n).read_bytes()).hexdigest())
