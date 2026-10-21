from pathlib import Path
import hashlib,json,re
R=Path('C:/Flycast-Evidence/re4-dreamcast/qa21-combined-regression-20261021');runs={}
accepted=('qa-cold01','pause-cold01','pause-return01','inventory01','inventory02','movie-skip02','death-continue01')
for name in accepted:
 C=R/name;r=json.loads((C/'run-result.json').read_text());assert r['errors']==[] and r['emulator_exited'] and r['elapsed_s']<50
 s=[json.loads(line) for line in (C/'read-only-state.jsonl').read_text().splitlines()];log=(C/'run-output.txt').read_text(errors='replace')
 runs[name]={'elapsed_s':r['elapsed_s'],'errors':r['errors'],'keys_executed':len(r['key_log']),'emulator_exited':r['emulator_exited'],'checkpoint_sealed':(C/'checkpoint.json').exists(),'final_sample':s[-1],'actual_health_min':min(x.get('global',{}).get('player_life',1200) for x in s),'window_closes':re.findall(r'subscreen backing: close[^\n]+',log),'movie_results':re.findall(r'route movie (?:start:|skip:|terminal=)[^\n]+',log),'room_lifecycle':re.findall(r'room lifecycle: phase=(?:enter|leave)[^\n]+',log)}
# Preserve and clearly reject unsafe or unsealed continuations.
rejected={
 'qa-cold01-checkpoint':{'reason':'Initial launcher selected plain runner; QA input qualifies but no checkpoint exists. No later scenario restores it.'},
 'movie-skip01':{'reason':'Watchdog empty PID-file race; root lane stopped only its verified owned guest at43s. No state is restored from this trial.'},
 'qa-after-continue01':{'reason':'Overall harness52.3s, hard-limit termination and truncated/rejected checkpoint. Process lifetime was not independently recorded; do not qualify or continue it.'},
 'movie-natural-cold01':{'reason':'C floor preflight refused launch; no guest started.'},
}
images={}
for relative in ('pause-cold01/events/07-before-start/frames/fb0.png','pause-cold01/events/08-before-start/frames/fb0.png','inventory02/shots/t0013/frames/fb0.png','inventory02/shots/t0036/frames/fb0.png','death-continue01/shots/t0006/frames/fb0.png','death-continue01/events/03-checkpoint-close/frames/fb0.png'):
 p=R/relative;assert p.is_file();images[relative]=hashlib.sha256(p.read_bytes()).hexdigest()
result={'source':'6f9d31b0e00497a75fdd7e25bb04f92305103087','program':'ce080eb290aec073f406e93da27911f4fa70b457768288f52a893175a6846e8e','elf':'0d6dcf6fbec0f543fae5818895c7cb4d461cbe9e050563fd7fd309f86923c43e','track':'97a3219f2876783cd28c5250479882e0b7643fecbff7a9bbbfc5df0886fc0a18','qualified':['Three fresh-cold QA reopening cycles and normal world return','OPTIONS native walls/floor/menu, ordinary resume and movement','Four original inventory opens/closes; matching source backing hashes restored','Original r100s03 normal Start skip followed by live original encounter','Authentic original damage/death1200 to440 to0, then original Continue leave/entry generation1 to2 and free play life1200'],'runs':runs,'rejected':rejected,'inspected_images':images,'resource_limits':['Continue KOS free3840B leaving/7936B entering','Inventory texture fragmentation retries remain','New guests blocked under C18GiB+64MiB; no floor lowered'],'remaining':['Natural movie EOF','Radio/held background','Original doors/new-room progression','Post-Continue QA qualification under new independent supervisor','Release full tier','Physical Dreamcast acceptance'],'scope':'Bounded preset-started functional Flycast only. No performance, whole-cache, release or physical-console acceptance.'}
(R/'regression-summary-v2.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'qualified':len(result['qualified']),'accepted_runs':len(runs),'rejected':list(rejected),'remaining':result['remaining']}))