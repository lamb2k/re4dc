#!/usr/bin/env python3
"""OFF preprocessed-token identity for water source extensions; no SDK or Make."""
import hashlib,json,pathlib,re,resource,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[5]
BASE='140a699f8ead7b406e76581de7075191acf77a96'
def limits():resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,256*1024*1024))
def run(args,**kw):
 p=subprocess.run(args,capture_output=True,text=True,timeout=120,preexec_fn=limits,**kw)
 if p.returncode:raise RuntimeError(p.stderr)
 return p.stdout
TOKEN=re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[A-Za-z_]\w*|\d+(?:\.\d*)?(?:[eE][+-]?\d+)?|[^\s]')
def prep(text,flags):
 text=re.sub(r'^\s*#include[^\n]*','',text,flags=re.M)
 out=run(['g++','-x','c++','-E','-P','-nostdinc','-DRE4DC_WATER_R100_MATERIAL=0',*['-D'+x for x in flags],'-'],input=text)
 return '\n'.join(TOKEN.findall(out))
def main():
 controls=[]
 cases=[('src/game/espgen45.cpp',['RE4DC_WATER_PS2=1','RE4DC_WATER45_NATIVE=1','RE4DC_WATER45_LEAN=1','RE4DC_WATER_PS2_EXT=1']),
 ('port/dreamcast/game/platform/include/pvr_rtt.inc',['RE4DC_UI_HANDLES=1']),
 ('port/dreamcast/game/platform/native_static.cpp',['RE4DC_SS_UI_ORDER=1','RE4DC_PS2_WORLD_MESH=1','RE4DC_PS2_WORLD_DYNAMIC=1','RE4DC_PS2_WORLD_ROOMS=2','RE4DC_GC_ASSET_GATE=1']),
 ('port/dreamcast/game/platform/native_static.cpp',['RE4DC_SS_UI_ORDER=1','RE4DC_PS2_WORLD_MESH=1','RE4DC_PS2_WORLD_DYNAMIC=1','RE4DC_PS2_WORLD_ROOMS=2','RE4DC_GC_ASSET_GATE=1','RE4DC_SCENERY_CHUNK=1','RE4DC_SCENERY_SELECT_ONLY=1','RE4DC_SCENERY_REPLAY_LEAN=1','RE4DC_SCENERY_SUBMIT_BATCH=1','RE4DC_SCENERY_UV_SNAPSHOT=1','RE4DC_PS2_WORLD_LEAN=31','RE4DC_PS2_PASS_MASK=1','RE4DC_PS2_AREA_HIDE=1','RE4DC_PS2_WORLD_PARTS=1','RE4DC_PS2_WORLD_ROOT_POSE=1','__sh__=1','RE4DC_MESH_CLASSIFY=0','RE4DC_MESH_LOD=1','RE4DC_MESH_PRIME_LAZY=1','RE4DC_MESH_VP_SCHED=1','RE4DC_MESH_STRIP_LEAN=1','RE4DC_HW_LEAN=1','RE4DC_MESH_DIRECT=1','RE4DC_NATIVE_MESH=1','RE4DC_MESH_FASTPATH=1'])]
 for path,flags in cases:
  original=run(['git','show',BASE+':'+path],cwd=ROOT);current=(ROOT/path).read_text();old=prep(original,flags);new=prep(current,flags)
  if old!=new:raise AssertionError('OFF tokens differ '+path)
  controls.append({'path':path,'flags':flags,'sha256':hashlib.sha256(old.encode()).hexdigest(),'tokens_identical':True})
 print(json.dumps({'controls':controls,'target_object_identity':'NOT RUN','sdk_make_guest':False},indent=2))
if __name__=='__main__':main()
