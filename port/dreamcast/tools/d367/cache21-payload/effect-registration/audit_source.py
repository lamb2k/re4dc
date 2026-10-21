"""Freeze the selected effect source/caller census without mutating the source tree."""
import argparse, collections, hashlib, json, re, subprocess
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--source', type=Path, required=True)
p.add_argument('--ref', required=True)
p.add_argument('--out', type=Path, required=True)
a = p.parse_args()
assert not a.out.exists()
def git(*args):
    return subprocess.check_output(['git', '-C', str(a.source), *args])
def blob(path, ref=None):
    return git('show', (ref or a.ref) + ':' + path)
def grep(word):
    r = subprocess.run(['git','-C',str(a.source),'grep','-n','-F',word,a.ref,'--','src','include'],capture_output=True,text=True)
    assert r.returncode in (0, 1), r.stderr
    return r.stdout.splitlines()

paths = ['src/game/eff_sys.cpp','include/espgen.h','src/game/emdata.cpp','src/game/event.cpp','src/game/et00.cpp','src/game/game.cpp','src/em10/em10.cpp','src/game/pl_leon.cpp','port/dreamcast/game/platform/gx_stub.cpp']
source = {path: {'sha256':hashlib.sha256(blob(path)).hexdigest(),'bytes':len(blob(path))} for path in paths}
prior = 'e7bb2e5bf'
prior_eff = blob('src/game/eff_sys.cpp', prior)
assert prior_eff == blob('src/game/eff_sys.cpp')
rows=[]
for entry in grep('EspDataLoad('):
    _,path,line,text=entry.split(':',3)
    prefix=text.split('EspDataLoad(',1)[0].strip()
    if text.lstrip().startswith('//') or prefix.startswith('OWNER_') or (prefix in ('int','void') or prefix.startswith('extern')): continue
    # All selected invocation argument lists fit on one source line. Split only outer commas.
    tail=text.split('EspDataLoad(',1)[1]; depth=0; parts=[]; start=0
    for i,c in enumerate(tail):
        if c=='(': depth+=1
        elif c==')':
            if depth==0: parts.append(tail[start:i].strip()); break
            depth-=1
        elif c==',' and depth==0: parts.append(tail[start:i].strip()); start=i+1
    assert len(parts)==3,(path,line,text,parts)
    try: owner=int(parts[1],0)
    except ValueError: owner=None
    rows.append({'path':path,'line':int(line),'call':text.strip(),'arguments':parts,'literal_owner':owner,'return_observed':prefix.startswith('if')})
counts=collections.Counter('literal' if x['literal_owner'] is not None else 'dynamic' for x in rows)
literals=[x['literal_owner']for x in rows if x['literal_owner']is not None]
assert all(0<=x<0xD2 for x in literals)
result={'ref':a.ref,'source':source,'eff_sys_identical_to':prior,'calls':rows,'call_counts':dict(counts),'literal_owner_range':[min(literals),max(literals)],'observed_returns':[r for r in rows if r['return_observed']],'dynamic_calls':[r for r in rows if r['literal_owner']is None], 'searches':{word:grep(word) for word in ['RoomEfmRegist(', 'EspPullTexObj(', 'texObj[', 'pTexObj[', 'EspGetTexObj(', 'effNo =']},'limits':'Textual source census only. Dynamic owner validity requires caller-specific proof; invocation counts do not imply simultaneous owners or capacity pressure.'}
a.out.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:result[k]for k in ['ref','eff_sys_identical_to','call_counts','literal_owner_range','observed_returns','dynamic_calls']},indent=2))
