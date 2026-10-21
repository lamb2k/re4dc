from pathlib import Path
import hashlib
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18');p=L/'owned-window-recovered-j-r201-source-ack18-bounded-Back-refresh-full-walk-still.py';assert not p.exists();s=(L/'owned-window-recovered-j-r201-source-ack-quickturn18-full-walk-still.py').read_text();s=s.replace("before=u32(pg+0x51e4);transition(set());transition({'back'});until=time.monotonic()+1","before=u32(pg+0x51e4);transition(set());transition({'back'});until=time.monotonic()+1;ack_refresh=0;ack_last=before")
s=s.replace("    assert time.monotonic()<until and qf-before<30,'Normal Back source acknowledgment timed out';time.sleep(.005)","""    if joy_y==0 and not(kon&2) and qf-ack_last>=6 and ack_refresh<2:
     transition(set());settle=qf+2
     while u32(pg+0x51e4)<settle:quick_guard();assert time.monotonic()<until;time.sleep(.005)
     transition({'back'});ack_refresh+=1;ack_last=u32(pg+0x51e4);events.append({'bounded_normal_Back_release_repress_after_source_no_ack':dict(frame=ack_last,attempt=ack_refresh)})
    assert time.monotonic()<until and qf-before<30,'Normal Back source acknowledgment timed out';time.sleep(.005)""");compile(s,str(p),'exec');p.write_text(s);print(p.name,hashlib.sha256(p.read_bytes()).hexdigest())
