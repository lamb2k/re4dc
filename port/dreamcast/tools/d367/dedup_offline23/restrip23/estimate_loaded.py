"""Loaded-package strict-order census; no asset output or camera/TA gate claim."""
import argparse,hashlib,importlib.util,json,os,re,shlex,struct,sys,zlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;TOOLS=HERE.parents[1]
sys.path.insert(0,str(HERE.parent))
from offline_dedup import Package
from ordered_strip import grouped_partition,triangles
SOURCE='fb254e82ee6f9a3d9e34d53d1d442348a46b9cf2'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def pin(p):return dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p))
def release_inputs():
 recipe=TOOLS/'rr/recipe.conf';text=recipe.read_text()
 names=re.search(r'^DATA="([^"]+)"$',text,re.M)[1].split(',')
 for k,v in re.findall(r'^export ([A-Z][A-Z0-9_]*)=(.+)$',text,re.M):
  words=shlex.split(v,comments=True)
  if len(words)!=1 or '$' in words[0] or chr(96) in words[0]:raise ValueError('nonliteral recipe export')
  os.environ[k]=words[0]
 spec=importlib.util.spec_from_file_location('restrip23_t11',TOOLS/'test11/t11-fix.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 rows={}
 for room in ('r100','r101','r103'):
  files={};history={}
  for ext in ('re4mesh','r4pw','r4sg','ids'):
   rel=f'dc/native/{room}/ps2-world.{ext}';p=Path(mod.PAYLOAD_ROOT)/'tree'/rel;seq=[dict(dataset='payload',path=str(p))]
   for name in names:
    if rel in mod.DATA[name]:p=Path(mod.DATA[name][rel]);seq.append(dict(dataset=name,path=str(p)))
   if p.exists():files[ext]=pin(p)
   elif ext in ('re4mesh','r4pw'):raise FileNotFoundError(p)
   history[ext]=seq
  rows[room]=dict(files=files,history=history)
 return dict(source=SOURCE,recipe=pin(recipe),datasets=names,rooms=rows)
def groups(p,sg,li):
 l=p.lets[li]
 if sg is None:return [len(l['strips'])]
 w=struct.unpack_from('<4s7I',sg)
 if w[:3]!=(b'R4SG',1,p.h[6]) or w[4:6]!=(p.h[3],len(p.data)) or zlib.crc32(sg[32:])!=w[7]:raise ValueError('SG identity')
 stops={0:0};off=0
 for i,s in enumerate(l['strips']):off+=1+len(s);stops[off]=i+1
 ends=[]
 for j in range(w[3]):
  end=struct.unpack_from('<H',sg,32+16*(li*w[3]+j)+12)[0]
  if end not in stops:raise ValueError('SG boundary')
  ends.append(stops[end])
 return ends
def estimate(mesh,policy,sg=None):
 p=Package(mesh,True);h=p.h;ph=struct.unpack_from('<4s7I',policy)
 if ph[0]!=b'R4PW' or ph[1]!=1 or ph[3]!=h[5] or zlib.crc32(policy[32:])!=ph[5]:raise ValueError('policy')
 admit=[False]*h[6];reasons={};cover=0
 for pi in range(h[5]):
  part=struct.unpack_from('<IIBBBBII4f',mesh,h[11]+36*pi);first,count=part[6:8]
  if first!=cover:raise ValueError('part partition')
  cover+=count;rec=policy[32+16*pi:48+16*pi]
  reason='opaque' if rec[12]==0 and part[3]==255 and rec[15]==0 else 'nonopaque_alpha_or_marked'
  reasons[reason]=reasons.get(reason,0)+count
  for li in range(first,first+count):admit[li]=reason=='opaque'
 if cover!=h[6]:raise ValueError('part coverage')
 new=[];changed=0;old_s=old_c=new_s=new_c=tri=0;seen={};pool=bytearray()
 for li,l in enumerate(p.lets):
  old=l['strips'];corners=p.decoded(l);ends=groups(p,sg,li)
  ss,gs=grouped_partition(old,corners,ends,admit[li])
  before=[tuple(tuple(corners[q]) for q in t) for t in triangles(old)]
  after=[tuple(tuple(corners[q]) for q in t) for t in triangles(ss)]
  if before!=after:raise AssertionError('ordered/winding/provoking attributes')
  old_s+=len(old);new_s+=len(ss);old_c+=sum(map(len,old));new_c+=sum(map(len,ss));tri+=len(before);changed+=ss!=old
  raw=(mesh[h[14]+l['fs']:h[14]+l['fs']+2*l['n']] if l['ix'] else b'')+b''.join(bytes([len(s)])+bytes(s) for s in ss)
  if raw not in seen:
   if len(pool)&1:pool.append(0)
   seen[raw]=len(pool);pool.extend(raw)
  new.append(dict(strips=ss,group_ends=gs,changed=ss!=old,admitted=admit[li]))
 tail=(h[14]+len(pool)+31)&~31;size=tail+len(mesh)-h[15]
 if tri!=old_c-2*old_s or tri!=new_c-2*new_s:raise AssertionError('triangle count')
 return p,new,dict(meshlets=h[6],changed_meshlets=changed,admission=reasons,all_loaded_LOD_strips_before=old_s,all_loaded_LOD_strips_after=new_s,all_loaded_LOD_corners_before=old_c,all_loaded_LOD_corners_after=new_c,all_loaded_LOD_triangles=tri,average_strip_before=old_c/old_s,average_strip_after=new_c/new_s,corner_reduction_percent=100*(1-new_c/old_c),physical_bytes_before=len(mesh),estimated_physical_bytes_after=size,allocation32_before=(len(mesh)+31)&~31,allocation32_after=(size+31)&~31,strip_pool_before=h[8],estimated_strip_pool_after=len(pool),vertex_bytes_unchanged=12*h[7],limits='Loaded packages including unused LOD/fallback; not camera-weighted or clipped TA traffic. No asset written; not GO evidence.')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--resolve',type=Path);ap.add_argument('--inputs',type=Path);ap.add_argument('--output',type=Path);ap.add_argument('--assets',type=Path);a=ap.parse_args()
 if a.resolve:
  assert not a.resolve.exists();r=release_inputs();a.resolve.write_text(json.dumps(r,indent=2)+'\n');print('CURRENT_RELEASE_INPUTS_PINNED');return
 if not(a.inputs and a.output and a.assets):ap.error('need inputs/output/assets')
 resolved=json.loads(a.inputs.read_text());assert resolved['source']==SOURCE;out={}
 for room,row in resolved['rooms'].items():
  pol=Path(row['files']['r4pw']['path']);assert sha(pol)==row['files']['r4pw']['sha256']
  mesh=a.assets/(room+'-stripshare-v1')/'ps2-dd3.re4mesh';sg=mesh.with_suffix('.r4sg') if room=='r101' else None
  p,new,st=estimate(mesh.read_bytes(),pol.read_bytes(),sg.read_bytes() if sg else None)
  original=Path(row['files']['re4mesh']['path']);oh=struct.unpack_from('<4s19I',original.read_bytes())
  assert p.h[18]==oh[3] and (p.h[17] or len(p.data))==original.stat().st_size
  out[room]=dict(input=pin(mesh),policy=pin(pol),groups=pin(sg) if sg else None,**st)
 assert not a.output.exists();a.output.write_text(json.dumps(dict(source=SOURCE,status='OFFLINE_LOADED_CENSUS_ONLY_NOT_CAMERA_GATE',inputs_sha256=sha(a.inputs),rooms=out),indent=2)+'\n')
 print(json.dumps({r:{k:v for k,v in x.items() if k in ['corner_reduction_percent','changed_meshlets','physical_bytes_before','estimated_physical_bytes_after']} for r,x in out.items()},indent=2))
if __name__=='__main__':main()

