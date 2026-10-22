#!/usr/bin/env python3
"""Batch existing vertical opaque native-world contracts. Source/data only; no pack/programme/image writes."""
from pathlib import Path
from array import array
import argparse,collections,ctypes,hashlib,json,math,random,shutil,struct,sys,time,zlib
HERE=Path(__file__).resolve().parent;sys.path[:0]=[str(HERE),str(HERE.parent),str(HERE.parents[1])]
import compact_axis as compact
import rectangular_vq as rect,convert_tpl as tpl,mipmap_vq as mip,scoped_candidate as scoped
from vram.vq_pak import read_pak

def sha(b):return hashlib.sha256(b).hexdigest()
def keystr(k):return '%08x-%08x'%k
def rounded(n):return(n+31)&~31

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--evidence',type=Path,required=True);p.add_argument('--library',type=Path,required=True);args=p.parse_args()
 out,E=args.out,args.evidence;assert out.exists()and set(x.name for x in out.iterdir())=={'nearest64.so'};assert E.exists()
 prior=Path('/root/re4data/private/texture-rect21-next415-20261021-v1');priorE=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/texture-rect21-20261021/next415-batch-01')
 cap=32*1024**2;floor=18*1024**3+64*1024**2
 prior177=Path('/root/re4data/private/texture-rect21-next177-20261022-v2');prior177E=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/texture-rect21-20261021/next177-batch-01')
 prior_charge=sum(f.stat().st_size for root in(prior,priorE,prior177,prior177E,Path('/root/re4data/private/texture-rect21-next177-20261022-v1'))for f in root.rglob('*')if f.is_file())
 def charge():return prior_charge+sum(f.stat().st_size for root in(out,E)for f in root.rglob('*')if f.is_file())+65536
 def guard(extra=0):assert charge()+extra<cap and shutil.disk_usage('/mnt/c').free>=floor,('resource',charge(),shutil.disk_usage('/mnt/c').free)
 def write(path,blob):
  guard(len(blob));path.parent.mkdir(parents=True,exist_ok=True)
  with path.open('xb')as f:f.write(blob)
 def emit(path,item):write(path,(json.dumps(item,indent=2)+'\n').encode())
 baseline=Path('/root/re4data/private/mipmap21-release21-pack-recovery-20261021/tex.pak');raw=baseline.read_bytes();assert sha(raw)=='18fcee11491f2c1f212863d6d6b572b3997f691b2e990217e1c2518f134021ef';pkgs=read_pak(raw)
 binding_path=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/texture-rect21-20261021/native-bindings-01/bindings.json');bind=json.loads(binding_path.read_text());assert sha(binding_path.read_bytes())=='e24a1ee4150c91f1228879f92bb9e6e934176fc6d3c1011f45c265ea8d606003'
 remaining_path=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/texture-consumers21-native-coverage-20261021/remaining756-keys.json');remaining=json.loads(remaining_path.read_text());assert len(remaining)==756
 selected=sorted([r for r in remaining if r['format']==0 and r['layout']==2 and r['height']==2*r['width'] and r['width']in(32,128)],key=lambda r:(r['height'],r['key']));assert len(selected)==4
 current=Path('/root/re4data/private/texture-canonical1004-20261021/tex.pak')
 with current.open('rb')as f:
  header=f.read(2048);magic,ver,count,ioff,doff=struct.unpack_from('<8s4I',header);assert magic==b'RE4PAK1\0'and count==6537;f.seek(ioff);index=f.read(count*16)
 occupied={tuple(struct.unpack_from('<4I',index,i*16)[:2])for i in range(count)}|{(0x3662c0aa,0xc9e71c00),(0xfefdf580,0xf15c1f47)}
 occupied.update(tuple(int(y,16)for y in x['scoped_key'].split('-'))for x in json.loads((prior/'conversion-receipt.json').read_text())['selected'])
 occupied.update(tuple(int(y,16)for y in x['scoped_key'].split('-'))for x in json.loads((prior177/'conversion-receipt.json').read_text())['selected'])
 coverage_path=Path('/root/re4data/private/mipmap21-fullpack-core-pairs-coverage-20261021/coverage.json');coverage=json.loads(coverage_path.read_text());occupied.update(tuple(int(x,16)for x in r['key'].split('-'))for r in coverage['loose_and_quality_rows'])
 lib=ctypes.CDLL(str(args.library));fn=lib.rect21_nearest64;fn.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_void_p,ctypes.c_size_t,ctypes.c_size_t,ctypes.c_void_p];fn.restype=ctypes.c_int
 error=lib.rect21_error_ratio;error.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_uint,ctypes.c_uint,ctypes.POINTER(ctypes.c_uint64),ctypes.POINTER(ctypes.c_uint)];error.restype=ctypes.c_int
 old_nearest=mip._nearest
 def fast(targets,book,engine):
  if engine!='rect21_c64':return old_nearest(targets,book,engine)
  if not targets:return [],'rect21_c64'
  width=len(targets[0]);a=array('i',(x for row in targets for x in row));b=array('i',(x for row in book for x in row));assert a.itemsize==b.itemsize==4
  result=(ctypes.c_ubyte*len(targets))();aa=(ctypes.c_int32*len(a)).from_buffer(a);bb=(ctypes.c_int32*len(b)).from_buffer(b)
  assert fn(aa,len(targets),bb,len(book),width,result)==0
  return list(result),'rect21_c64'
 rng=random.Random(211004);engine_cases=0
 for width in(4,16):
  for n in(1,3,32,128):
   book=[tuple(rng.randrange(65026)for _ in range(width))for j in range(256)];book[1]=book[0]
   targets=[tuple(rng.randrange(65026)for _ in range(width))for j in range(n)]+[book[0],tuple([65025]*width),tuple([0]*width)]
   assert fast(targets,book,'rect21_c64')[0]==old_nearest(targets,book,'python')[0];engine_cases+=len(targets)
 mip._nearest=fast
 oracle=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/texture-rect21-20261021/oracle-02/oracle.so');dec=ctypes.CDLL(str(oracle));rc=dec.rect_oracle_decode;rc.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_uint,ctypes.c_uint,ctypes.c_uint,ctypes.c_void_p,ctypes.c_size_t];mc=dec.mipmap_oracle_decode;mc.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_uint,ctypes.c_uint,ctypes.c_int,ctypes.c_uint,ctypes.c_void_p,ctypes.c_size_t]
 def pixels(blob,w,h):
  head=tpl.HEADER.unpack_from(blob);t=tpl.TEXTURE.unpack_from(blob,head[5]);payload=blob[t[4]:t[4]+t[5]];buf=(ctypes.c_ubyte*(4*w*h))();assert rc(payload,len(payload),t[3],w,h,buf,len(buf))==len(buf);return bytes(buf)
 started=time.monotonic();results=[];held=[];controls=[];images=[]
 from PIL import Image,ImageDraw
 for row in selected:
  guard();oldkey=tuple(int(x,16)for x in row['key'].split('-'));blob=pkgs[oldkey];assert sha(blob)==row['source_package_sha256'];h=tpl.HEADER.unpack_from(blob);t=tpl.TEXTURE.unpack_from(blob,h[5]);w,height=row['width'],row['height'];side=w
  if t[6]or t[3]!=0 or t[7]!=2:held.append(dict(key=row['key'],reason='outside sourceflag/format/layout contract',actual_descriptor=list(t)));continue
  refs=bind['bindings'][row['key']];assert len(refs)==row['material_refs']and all(r['width']==w and r['height']==height and r['flags']in(0,1)and r['render_pass']in(0,2)for r in refs)
  before=pixels(blob,w,height);assert before[3::4]==b'\xff'*(w*height);assert compact.shorter_square(blob,before)==blob
  base=compact.shorter_square(blob,before,enabled=True,engine='rect21_c64');candidate,meta=mip.add_mipmaps(base,enabled=True,engine='rect21_c64');native=mip.read_native_vq(candidate);after=pixels(base,side,side)
  assert native.size==side and native.texture[3]==0 and native.texture[6]==4 and native.texture[7]==2 and native.codebook==blob[t[4]:t[4]+2048]
  assert native.header[8]==zlib.crc32(candidate[48:])&0xffffffff
  levels=[]
  for level in range(side.bit_length()):
   n=1<<level;buf=(ctypes.c_ubyte*(4*n*n))();assert mc(native.payload,len(native.payload),0,side,1,level,buf,len(buf))==len(buf)
   assert bytes(buf)==bytes(c for px in mip.decode_level(native,n)for c in px) and bytes(buf)[3::4]==b'\xff'*(n*n);levels.append(n)
  # Full byte-equivalence one representative perdimension; shared engine vectors include ties/extremes.
  if (side,height//w) not in {(v['side'],v['ratio'])for v in controls}:
   reference=compact.shorter_square(blob,before,enabled=True,engine='python');ref_mips,_=mip.add_mipmaps(reference,enabled=True,engine='python');assert reference==base and ref_mips==candidate
   controls.append(dict(side=side,ratio=height//w,key=row['key'],base_and_all_mips_byteexact_C_vs_Python=True))
  sse=ctypes.c_uint64();maximum=ctypes.c_uint();trans=lambda b,ww,hh:bytes(c for x in range(ww)for y in range(hh)for c in b[(y*ww+x)*4:(y*ww+x+1)*4]);assert error(trans(before,w,height),trans(after,side,side),height,w,ctypes.byref(sse),ctypes.byref(maximum))==0
  # Normalized repeat period and seam/negative-domain sampling shared per representation, no UV/dimension scaling.
  coords=[(-2.0001,-.0001),(-1.,1.),(0.,0.),(.5,.5),(.9999,1.0001),(3.125,-2.75)]+[(rng.uniform(-8,8),rng.uniform(-8,8))for _ in range(26)]
  periodic=max(max(abs(a-b)for a,b in zip(rect.sample(after,side,side,u,v),rect.sample(after,side,side,u+3,v-2)))for u,v in coords);assert periodic<1e-8
  # Verify accelerated all-pixel quarter metric against reference bilinear at deterministic texel centers.
  for x,y in[(0,0),(w-1,height-1),(w//2,height//2),(1,0),(w-2,height-1)]:
   value=rect.sample(after,side,side,(x+.5)/w,(y+.5)/height);assert all(abs(c*4-round(c*4))<1e-8 for c in value)
  new=scoped.scoped_key(oldkey,sha(candidate));assert new not in occupied;occupied.add(new);newkey=keystr(new);path=out/'textures'/(newkey+'.re4tex');write(path,candidate)
  den=4;mse=sse.value/(den*den*w*height*3);res=dict(original_key=row['key'],scoped_key=newkey,relative_path=str(path.relative_to(out)),source_package_sha256=sha(blob),candidate_sha256=sha(candidate),candidate_crc32=native.header[8],logical=[w,height],physical=[side,side],uv_scale=[1.,1.],format=0,flags=4,payload_type=2,source_payload=t[5],candidate_payload=len(native.payload),source_request_rounded=rounded(t[5]),candidate_request_rounded=rounded(len(native.payload)),package_bytes=len(candidate),decoded_levels=levels,codebook_exact=True,base_exact=False,base_rule='integer-ratio source-y periodic box feature average then original-codebook nearest quantization',rgb_texel_center_MSE=mse,rgb_texel_center_RMSE=math.sqrt(mse),max_channel_error=maximum.value/den,periodic_probe_count=len(coords),periodic_max_error=periodic,world_refs=refs)
  results.append(res)
  if len(images)<12 and(len(images)<3 or side>images[-1][0]):
   im=Image.new('RGB',(384,88),'#202020');ImageDraw.Draw(im).text((2,2),row['key']+' '+str(w)+'x'+str(height),fill='white');im.paste(Image.frombytes('RGBA',(w,height),before).convert('RGB').resize((128,64)),(0,22));im.paste(Image.frombytes('RGBA',(side,side),after).convert('RGB').resize((128,64)),(128,22));low=Image.new('RGBA',(min(32,side),min(32,side)));low.putdata(mip.decode_level(native,min(32,side)));im.paste(low.convert('RGB').resize((128,64)),(256,22));images.append((side,im))
  if len(results)%25==0 or len(results)==len(selected):print(json.dumps(dict(converted=len(results),selected=len(selected),last_class=[w,side],seconds=round(time.monotonic()-started,3),charged=charge())),flush=True)
 sheet=Image.new('RGB',(384,88*len(images)),'#202020')
 for n,(_,im)in enumerate(images):sheet.paste(im,(0,n*88))
 sheet.save(out/'contact-sample.png');guard()
 report=dict(schema='rect21-batched-vertical-v1',status='CONVERTED_SOURCE_DATA_ONLY_NOT_ACTIVE',selection='Existing remaining756 reconciliation; format0/layout2/vertical1:2 dimensions; actual sourceflag0 contract applied. No all792 reassessment.',source_pack_sha256=sha(raw),canonical1004_preserved='89ef27a767fcee529c3ac6ca07fef5a8f9a3e2515f38eda63b61c8929fb0be62',bindings_sha256=sha(binding_path.read_bytes()),remaining_inventory_sha256=sha(remaining_path.read_bytes()),coverage_sha256=sha(coverage_path.read_bytes()),accelerator_source_sha256=sha((HERE/'nearest64.c').read_bytes()),accelerator_library_sha256=sha(args.library.read_bytes()),oracle_sha256=sha(oracle.read_bytes()),engine_shared_vector_cases=engine_cases,dimension_engine_controls=controls,selected=results,held=held,converted_keys=len(results),selected_keys=len(selected),dimension_groups=dict(collections.Counter(str(v['logical'])for v in results)),material_refs=sum(len(v['world_refs'])for v in results),independent_level_decodes=sum(len(v['decoded_levels'])for v in results),candidate_package_bytes=sum(v['package_bytes']for v in results),source_request_bytes=sum(v['source_request_rounded']for v in results),candidate_request_bytes=sum(v['candidate_request_rounded']for v in results),possible_original_plus_candidate_requests=sum(v['source_request_rounded']+v['candidate_request_rounded']for v in results),conversion_seconds=time.monotonic()-started,limits=['No active pack/programme/image/guest/default/runtime edits.','Compact base is filtered/requantized approximation; codebook exact, normalized periodic UV1,1 and all alpha255. No RGB look acceptance.','Original source keys/packages stay untouched; scoped keys only selected by proposed nativeworld remaps. Other source/model/actor/UI/legacy consumers unqualified.','Requested payload deltas not actual VRAM/residency/highwater/performance/hardware.','Shared synthetic engine and actual independent decoder checks distinct from actual Package strict/CRC1 batch gate to follow.'])
 emit(out/'conversion-receipt.json',report);print(json.dumps({k:report[k]for k in('converted_keys','material_refs','independent_level_decodes','source_request_bytes','candidate_request_bytes','conversion_seconds')}),flush=True)
if __name__=='__main__':main()