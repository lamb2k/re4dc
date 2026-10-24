#!/usr/bin/env python3
"""Compare existing early-water table rows to actual PS2 EFF; no extraction/conversion."""
import argparse,hashlib,importlib.util,json,pathlib,resource,signal,sys
ROOT=pathlib.Path(__file__).resolve().parents[5]
def load(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def sha(d):return hashlib.sha256(d).hexdigest()
class Entry:
 def __init__(self,name,data):self.name,self.data=name,data
 def read_bytes(self):return self.data
 def __lt__(self,other):return self.name<other.name
class Cache:
 def __init__(self,entries):self.entries=entries
 def glob(self,pattern):return self.entries

def main():
 p=argparse.ArgumentParser();p.add_argument('--iso',type=pathlib.Path,required=True);p.add_argument('--out',type=pathlib.Path,required=True);a=p.parse_args();resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,256*1024*1024));signal.alarm(120)
 if a.out.exists():raise ValueError('output exists')
 B=load('early_water_bin',ROOT/'port/dreamcast/tools/ps2_bin.py');W=load('early_water_table',ROOT/'port/dreamcast/tools/d367/water/water_ps2_table.py');A=load('early_water_recipes',ROOT/'tools/audit_ps2_fx_recipes.py')
 index=B.afs_index(a.iso);table=(ROOT/'src/game/water_ps2_table.inc').read_text();result={'schema':'early-water-table-bindings-v1','table_sha256':sha(table.encode()),'rooms':{}}
 for room in ('r107','r10a'):
  raw=B.afs_read(a.iso,room+'.dat',index);entries=[Entry(room+'.ps2.eff%d'%j,d) for j,(_,tag,d) in enumerate(x for x in B.dat_entries(raw) if x[1]=='EFF')]
  rows=W.rows_for(Cache(entries),room)
  existing=[line.rstrip() for line in table.splitlines() if line.strip().startswith('{0x'+room[1:]+',')]
  emitted=[W.c_row(r) for r in rows]
  if existing!=emitted:raise ValueError('existing table differs from actual PS2 '+room)
  records=[]
  for entry in entries:
   for r in A.decode_eff(entry.data,'<'):
    if r['id']==8 and r['tool_flags']&1 and abs(r['angle'][0]-90)<.5 and min(r['size_x'],r['size_y'])>=5000:
     records.append({k:r[k] for k in ('table','no','area','list_flags','index','offset','record_sha256','tex','tool_flags','blend','life_max','life_time','set_time')})
  result['rooms'][room]={'member_sha256':sha(raw),'rows':len(rows),'exact_existing_rows':True,'original_records':records,'runtime_lifetime':'area>=0 uses EffGetAreaState; area<0 uses live recovered GC generator; source display flag not checked','runtime_texture_path':'registered EspTexWk -> WaterPs2Pattern -> TEXGet -> native water resolve; current consumed PS2 package ancestry and native acceptance need root QA'}
 a.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'rows':{r:x['rows'] for r,x in result['rooms'].items()},'sha256':sha(a.out.read_bytes())}))
if __name__=='__main__':main()
