#!/usr/bin/env python3
"""Extract source-linked VRAM and model self-cost evidence without launching a game."""
import argparse, csv, hashlib, json
from pathlib import Path

def read(path):
    b=path.read_bytes()
    return b.decode('utf-16') if b[:2] in (bytes((255,254)),bytes((254,255))) else b.decode(errors='replace')

ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('--model-capture',type=Path,required=True)
ap.add_argument('--movie-capture',type=Path,required=True)
ap.add_argument('--out',type=Path,required=True)
a=ap.parse_args()
result={}
for tag,path in [('cross',a.model_capture/'boot.log'),('bell',a.movie_capture/'capture/run-output.txt')]:
    terms=['native VRAM layout:','MV shadows:','TA headroom ','native UI: texture VRAM budget=',
        'vram room:','native texture claim:','native texture unclaim:','route movie start:']
    result[tag]={'source':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'lines':[{'line':i+1,'text':s} for i,s in enumerate(read(path).splitlines()) if any(t in s for t in terms)]}
p=a.model_capture/'proj/rep/functions.tsv'
names=['re4dc_ps2_world_direct_begin','re4dc_model_direct_end','(anonymous namespace)::stream_select(pvr_list_type)',
    '(anonymous namespace)::MeshDraw::run()','(anonymous namespace)::ps2_pass(unsigned int, float)']
rows=list(csv.DictReader(p.read_text().splitlines(),delimiter='\t'))
result['costs']={'source':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
    'label':'Self costs from 30 sampled frames500:799 stride10; console-fit model, not console timing or atlas savings.',
    'rows':[{'function':r['func'],'console_fit_ms':float(r['wi_console']),'nominal_ms':float(r['hw_ms'])} for r in rows if r['func'] in names]}
a.out.parent.mkdir(parents=True,exist_ok=True)
a.out.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
print(json.dumps(result,indent=2,sort_keys=True))
