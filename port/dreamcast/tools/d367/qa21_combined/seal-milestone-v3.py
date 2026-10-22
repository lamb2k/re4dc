from pathlib import Path
import hashlib,json,re
R=Path('C:/Flycast-Evidence/re4-dreamcast/qa21-combined-regression-20261021');base=json.loads((R/'regression-summary-v2.json').read_text())
for name in ('movie-natural-cold01','movie-natural-finish01','qa-after-continue02','radio-route01'):
 C=R/name;run=json.loads((C/'run-result.json').read_text());assert run['errors']==[] and run['emulator_exited'] and run['elapsed_s']<50
 checkpoint=json.loads((C/'checkpoint.json').read_text());assert checkpoint['state_edits'] is False
 samples=[json.loads(line) for line in (C/'read-only-state.jsonl').read_text().splitlines()];log=(C/'run-output.txt').read_text(errors='replace');supervisor=json.loads((R/'invocations'/name/'process-supervisor.json').read_text())
 if name!='movie-natural-cold01':assert 0<supervisor['actual_guest_seconds']<47.5 and supervisor['exit_filetime']>=supervisor['start_filetime']
 else:supervisor['metric_rejected']='Initial exit-code/time race recorded zero exit FILETIME; complete harness41.8s establishes bounded run, but this process metric is invalid. Corrected by waiting for process signal before final timestamps.'
 base['runs'][name]={'elapsed_s':run['elapsed_s'],'errors':[],'emulator_exited':True,'keys_executed':len(run['key_log']),'final_sample':samples[-1],'checkpoint_sha256':hashlib.sha256((C/'checkpoint.json').read_bytes()).hexdigest(),'checkpoint_audit':checkpoint['audit'],'supervisor':supervisor,'movie_results':re.findall(r'route movie (?:start:|skip:|terminal=)[^\n]+',log),'window_closes':re.findall(r'subscreen backing: close[^\n]+',log)}
base['qualified']+=['Natural s03 EOF1465/1465 across fresh cold same-program checkpoints, no movie skip input','Three post-Continue QA reopening cycles and ordinary movement under independently measured41.8233218s guest','Original first kill from four handgun shots, natural s20 EOF571/571, six-second original radio hold, normal Start close and exact backing restore']
base['remaining']=['Original door/new-room progression and QA reopening at the new room','Resource/KOS/fragmentation qualification','Audio quality: s03 reports1 underrun1472silence bytes; s20 reports2 underruns8448silence bytes','Release full tier','Physical Dreamcast acceptance']
base['storage_context']='Root losslessly compressed retained original QA storage while logical input identity stayed exact. These are functional checks, never matched host-throughput or performance comparisons.'
for relative in ('movie-natural-cold01/shots/t0033/frames/fb0.png','movie-natural-finish01/events/01-checkpoint-close/frames/fb0.png','radio-route01/shots/t0036/frames/fb0.png'):
 p=R/relative;assert p.is_file();base['inspected_images'][relative]=hashlib.sha256(p.read_bytes()).hexdigest()
(R/'regression-summary-v3.json').write_text(json.dumps(base,indent=2)+'\n');print(json.dumps({'accepted_runs':len(base['runs']),'remaining':base['remaining']}))