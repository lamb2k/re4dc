#!/usr/bin/env python3
"""Read-only bounded stage-1 PS2 water evidence; never extracts asset bytes or runs a guest."""
import argparse, collections, hashlib, importlib.util, json, math, pathlib, resource, signal, struct, sys, time
sys.dont_write_bytecode=True
BUDGET=240*1024*1024

def sha(b):return hashlib.sha256(b).hexdigest()
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def dat_entries(b):
 n,=struct.unpack_from('<I',b);assert 0<n<4096 and 0x10+8*n<=len(b)
 offsets=struct.unpack_from('<%dI'%n,b,0x10);assert list(offsets)==sorted(offsets) and offsets[0]>=0x10+8*n
 ends=list(offsets[1:])+[len(b)]
 return [(i,b[0x10+4*n+4*i:0x14+4*n+4*i].rstrip(b'\0').decode('ascii'),a,z) for i,(a,z) in enumerate(zip(offsets,ends))]

def pictures(e,wanted):
 h=struct.unpack_from('<12I',e);assert h[0]==11
 o,t=h[1],h[6]
 if not o or not t:return []
 n,=struct.unpack_from('<I',e,o);assert n<65536 and o+4+8*n<=len(e) and t+4+4*n<=len(e)
 assert struct.unpack_from('<I',e,t)[0]==n
 starts=[t+struct.unpack_from('<I',e,t+4+4*i)[0] for i in range(n)]
 out=[]
 for i,p in enumerate(starts):
  tid,=struct.unpack_from('<H',e,o+4+8*i)
  if tid not in wanted:continue
  magic,count,desc=struct.unpack_from('<3I',e,p);assert magic==0x1000 and count<65536 and p+desc+48*count<=len(e)
  end=min([x for x in starts if x>p]+[len(e)])
  frames=[]
  for k in range(count):
   q=p+desc+48*k;w,hh,depth,inter=struct.unpack_from('<4H',e,q);io,po=struct.unpack_from('<2I',e,q+32)
   row={'frame':k,'width':w,'height':hh,'depth':depth,'interlace':inter,'descriptor_sha256':sha(e[q:q+48])}
   if depth in (8,9):
    a=p+io;z=a+w*hh//(2 if depth==8 else 1);pa=p+po;pz=pa+(96 if depth==8 else 1024)
    assert p<=a<=z<=end and p<=pa<=pz<=end
    row.update(index_bytes=z-a,index_sha256=sha(e[a:z]),palette_span_bytes=pz-pa,palette_span_sha256=sha(e[pa:pz]))
   frames.append(row)
  out.append({'texture_id':tid,'tpl_bytes':end-p,'tpl_span_sha256':sha(e[p:end]),'frames':frames})
 return out

def main():
 a=argparse.ArgumentParser();a.add_argument('--source',type=pathlib.Path,required=True);a.add_argument('--iso',type=pathlib.Path,required=True);a.add_argument('--out',type=pathlib.Path,required=True);args=a.parse_args()
 resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,256*1024*1024));signal.alarm(120)
 assert not args.out.exists();start=time.monotonic();r=args.source
 X=module('room_extract',r/'port/dreamcast/tools/ps2_room_extract.py');A=module('fx_recipes',r/'tools/audit_ps2_fx_recipes.py')
 census=[];read=0
 with args.iso.open('rb') as f:
  idx,indexhash=X.afs_index(f)
  rooms=sorted(k for k in idx if len(k)==8 and k.startswith('r1') and k.endswith('.dat') and int(k[1:4],16)<=0x120)
  for name in rooms:
   m=idx[name];assert read+m['size']<=BUDGET;f.seek(m['offset']);b=f.read(m['size']);assert len(b)==m['size'];read+=len(b)
   room=name[:4];effs=[];selected=[];allplane=[]
   for k,kind,off,end in dat_entries(b):
    if kind!='EFF':continue
    e=b[off:end];records=A.decode_eff(e,'<');water=[]
    for v in records:
     if v['id']==8 and v['tool_flags']&1 and max(v['size_x'],v['size_y'])>=5000:
      assert all(math.isfinite(x) for x in (v['size_x'],v['size_y'],*v['angle']))
      row={x:v[x] for x in ['table','no','index','offset','record_sha256','tex','size_x','size_y','angle','tool_flags','blend']}
      allplane.append(row)
      if v['tex'] in (0xf2,0xf7,0xfe,0xef,0xc5):water.append(row);selected.append(row)
    effs.append({'entry':k,'offset':off,'bytes':len(e),'sha256':sha(e),'decoded_records':len(records),'water_like_records':water,'pictures':pictures(e,{v['tex'] for v in water})})
   census.append({'room':room,'member':dict(m,sha256=sha(b)),'effs':effs,'water_like_count':len(selected),'large_world_Esp08_count':len(allplane),'water_like_texture_counts':dict(collections.Counter(hex(v['tex']) for v in selected))})
 result={'schema':'river-identification-readonly-v1','iso':{'path':str(args.iso),'bytes':args.iso.stat().st_size,'full_iso_hashed':False,'afs_table_sha256':indexhash},'member_bytes_read':read,'budget_bytes':BUDGET,'address_space_limit_bytes':256*1024*1024,'timeout_seconds':120,'elapsed_seconds':time.monotonic()-start,'census':census,'interpretation':'Large world Esp08 plus water-associated texture ID is evidence of a water candidate, not proof of the user phrase. No guest/asset extraction/staging.'}
 args.out.write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({'rooms':len(census),'member_bytes_read':read,'elapsed_seconds':result['elapsed_seconds'],'candidates':[(v['room'],v['water_like_count'],v['water_like_texture_counts']) for v in census if v['water_like_count']],'sha256':sha(args.out.read_bytes())},indent=2))
if __name__=='__main__':main()