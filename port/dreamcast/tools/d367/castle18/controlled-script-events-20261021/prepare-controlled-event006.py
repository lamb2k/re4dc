from pathlib import Path
import hashlib,re
L=Path(__file__).parent
src=(L/'observe-controlled-r204-event005.py').read_text().replace("cap==D/'route-walk-controlled-event005'","cap==D/'route-walk-controlled-event006'")
src=src.replace('CONTROLLED cold204 original scripted event coverage. Chapter6/partner/initialAEV2 are SETUP; no event outcome bits preset.','CONTROLLED direct continuation of closed005 movie state. No rearm/outcome state edits or gameplay buttons. Original005 chapter6/partner/AEV2 setup inherited.')
compile(src,'observe006','exec');(L/'observe-controlled-r204-event006.py').write_text(src)
src=(L/'run-controlled-event005.py').read_text().replace("cap=D/'route-walk-controlled-event005'","cap=D/'route-walk-controlled-event006'").replace("observer=L/'observe-controlled-r204-event005.py'","observer=L/'observe-controlled-r204-event006.py'")
src=src.replace("segment=D/'segments'/cap.name;", "seed=D/'route-walk-controlled-event005/data';assert sha(seed/'disc.state')=='40556645e59094f21b3051eecbffb0c71d08182acdef60e321ac76eb33705f86'\nsegment=D/'segments'/cap.name;")
src=src.replace('NEW COLD TEST LINEAGE. No authentic snapshot input','DIRECT CONTINUATION of closed controlled005 movie snapshot. No authentic snapshot input').replace('Native fixture initialchapter6/partner/position in originalAEV2 are declared SETUP','Inherited005 fixture and movie globals are restored unchanged, no rearm or outcome edits')
src=src.replace("fixture_raw_sha256=sha(fixture)","seed_state_sha256=sha(seed/'disc.state'),fixture_raw_sha256=sha(fixture)")
src=src.replace('Cold204 originalAEV2 triggers r204EventExec/movie20400/chapter-end task. Early flags/chapter transitions are recorded separately from actualEOF/resultsUI/savewrite/radio. Preserve continuation if bounded stop midstage.','Continue005 in-progress movie20400 without replay/rearm; observe actualEOF/chapter results/saveprompt separately; no buttons/savewrites in this unit. Earlyflags are not completion.')
src=src.replace("'--seconds','41','--warp'","'--seconds','41','--state-seed',str(seed),'--warp'").replace('castle21-CONTROLLED-r204-chapter-event005','castle21-CONTROLLED-r204-movie-continuation006')
compile(src,'run006','exec');(L/'run-controlled-event006.py').write_text(src)
src=(L/'run-controlled-event005.sh').read_text().replace('event005','event006');(L/'run-controlled-event006.sh').write_bytes(src.replace('\r','').encode())
p=L/'STATUS.md';s=p.read_text(encoding='utf-8');s=re.sub(r'(?m)^Doing now:.*$', 'Doing now: No active PID. CONTROLLED005 closed source181,204phase3/chapter6/Stop80400900 mid-originalmovie20400; state40556645...5f86. Movie start/firstpicture and actualcutscenePNG observed; noEOF/chapterUI/save/radio yet. Preparing006 directsnapshot continuation, no rearm/replay/stateedit/buttons.',s);p.write_text(s,encoding='utf-8')
for n in ['observe-controlled-r204-event006.py','run-controlled-event006.py']:print(n,hashlib.sha256((L/n).read_bytes()).hexdigest())
