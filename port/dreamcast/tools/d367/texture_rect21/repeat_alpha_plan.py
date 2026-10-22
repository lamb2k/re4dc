#!/usr/bin/env python3
"""CLI remains source/plan only; an explicitly allocated caller may receive candidate RAM bytes."""
from pathlib import Path
from array import array
import argparse,collections,ctypes,hashlib,json,math,random,struct,sys,zlib
HERE=Path(__file__).resolve().parent;sys.path[:0]=[str(HERE),str(HERE.parents[1]),str(HERE.parents[1]/'d367')]
import convert_tpl as tpl,mipmap_vq as vq,mipmap_twiddled as tw,rectangular_vq as rect,scoped_candidate as scoped,tr_classify as classifier
sha=lambda b:hashlib.sha256(b).hexdigest()
def repeat_base(blob,*,enabled=False):
 if not enabled:return blob
 h=list(tpl.HEADER.unpack_from(blob));t=list(tpl.TEXTURE.unpack_from(blob,48));w,hh,fmt=t[1:4];layout=t[7]
 if fmt!=2 or t[6]or layout not in(1,2)or w<=hh or w%hh or w//hh not in(2,4)or t[8]:raise ValueError('exact alpha-repeat16 contract')
 if layout==2:return rect.square_candidate(blob,enabled=True)[0]
 if h[:6]!=[tpl.MAGIC,tpl.VERSION,48,96,1,48]or t[4]!=144 or h[6]!=144 or t[5]!=w*hh*2 or h[7]!=t[5]or len(blob)!=144+t[5]:raise ValueError('nativeTWID source shape')
 payload=blob[144:]
 if h[8]not in(zlib.crc32(blob[48:])&0xffffffff,zlib.crc32(payload)&0xffffffff):raise ValueError('source CRC')
 words=struct.unpack('<%dH'%(w*hh),payload);order=tpl.twiddle_16bpp(list(range(w*hh)),w,hh);linear=[0]*len(words)
 for at,index in enumerate(order):linear[index]=words[at]
 full=[linear[(i//w%hh)*w+i%w]for i in tpl.twiddle_16bpp(list(range(w*w)),w,w)];p=struct.pack('<%dH'%len(full),*full);t[1]=t[2]=w;t[5]=h[7]=len(p);body=tpl.TEXTURE.pack(*t)+p;h[8]=zlib.crc32(body)&0xffffffff
 return tpl.HEADER.pack(*h)+body

def main(emit=None):
 ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);args=ap.parse_args();O=args.out;assert O.exists()and not list(O.iterdir());A=Path('/root/re4data/private/texture-rect21-next142-alpha-20261022-v1');a=json.loads((A/'conversion-receipt.json').read_text());policy=json.loads((A/'policy-classification.json').read_text());rows=[x for x in a['selected']if not x['policy_qualified']and x['source_texture_class']!=x['candidate_texture_class']];assert len(rows)==16
 source=Path('/root/re4data/private/mipmap21-release21-pack-recovery-20261021/tex.pak');raw=source.read_bytes();assert sha(raw)=='18fcee11491f2c1f212863d6d6b572b3997f691b2e990217e1c2518f134021ef';v,n,ioff,doff,crc=struct.unpack_from('<5I',raw,8);index={tuple(struct.unpack_from('<4I',raw,ioff+16*i)[:2]):struct.unpack_from('<4I',raw,ioff+16*i)[2:]for i in range(n)}
 old=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/texture-rect21-20261021/oracle-02/oracle.so');L=ctypes.CDLL(str(old));V=L.rect_oracle_decode;T=ctypes.CDLL('/root/re4data/private/texture-rect21-next18-twiddled-20261022-v1/rect-twiddled-oracle.so').rect_oracle_decode
 for f in(V,T):f.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_uint,ctypes.c_uint,ctypes.c_uint,ctypes.c_void_p,ctypes.c_size_t]
 dec={2:L.mipmap_oracle_decode,1:L.mipmap_oracle_decode_twiddled}
 for f in dec.values():f.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_uint,ctypes.c_uint,ctypes.c_int,ctypes.c_uint,ctypes.c_void_p,ctypes.c_size_t]
 def pixels(b,w,h):
  t=tpl.TEXTURE.unpack_from(b,48);p=b[t[4]:t[4]+t[5]];buf=(ctypes.c_ubyte*(w*h*4))();assert{2:V,1:T}[t[7]](p,len(p),t[3],w,h,buf,len(buf))==len(buf);return bytes(buf)
 lib=ctypes.CDLL(str(A/'nearest64.so'));fn=lib.rect21_nearest64;fn.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_void_p,ctypes.c_size_t,ctypes.c_size_t,ctypes.c_void_p];orig=vq._nearest
 def fast(targets,book,engine):
  if engine!='rect21_c64':return orig(targets,book,engine)
  if not targets:return [],engine
  aa=array('i',(c for x in targets for c in x));bb=array('i',(c for x in book for c in x));out=(ctypes.c_ubyte*len(targets))();assert fn((ctypes.c_int32*len(aa)).from_buffer(aa),len(targets),(ctypes.c_int32*len(bb)).from_buffer(bb),len(book),len(targets[0]),out)==0;return list(out),engine
 vq._nearest=fast;results=[];rng=random.Random(2216)
 for row in rows:
  key=tuple(int(x,16)for x in row['original_key'].split('-'));off,n=index[key];blob=raw[off:off+n];assert sha(blob)==row['source_package_sha256'];w,h=row['logical'];layout=row['payload_type'];before=pixels(blob,w,h);assert repeat_base(blob)==blob;base=repeat_base(blob,enabled=True);after=pixels(base,w,w)
  assert after==bytes(c for y in range(w)for x in range(w)for c in before[((y%h)*w+x)*4:((y%h)*w+x+1)*4]);ah=collections.Counter(before[3::4]);bh=collections.Counter(after[3::4]);ratio=w//h;assert bh=={k:v*ratio for k,v in ah.items()};source_class=classifier.tex_class((dict(collections.Counter(x//17 for x in before[3::4])),15));base_class=classifier.tex_class((dict(collections.Counter(x//17 for x in after[3::4])),15));assert source_class==base_class==row['source_texture_class']
  module={2:vq,1:tw}[layout];candidate,_=module.add_mipmaps(base,enabled=True,engine='rect21_c64');native=module.read_native_vq(candidate)if layout==2 else module.read_native_twiddled(candidate);assert native.header[8]==zlib.crc32(candidate[48:])&0xffffffff;levels=[]
  for level in range(w.bit_length()):
   side=1<<level;buf=(ctypes.c_ubyte*(side*side*4))();assert dec[layout](native.payload,len(native.payload),2,w,1,level,buf,len(buf))==len(buf);assert bytes(buf)==bytes(c for x in module.decode_level(native,side)for c in x);levels.append(dict(side=side,decoded_sha256=sha(bytes(buf))))
  coords=[(u,v)for u in(-8.,-1.,-.5,0.,.5,1.,8.)for v in(-8.,-1.,-.5,0.,.5,1.,8.)]+[(rng.uniform(-8,8),rng.uniform(-8,8))for _ in range(128)];worst=max(max(abs(a-b)for a,b in zip(rect.sample(before,w,h,u,v),rect.sample(after,w,w,u,v*h/w)))for u,v in coords);assert worst<1e-8
  chk=next(x for x in policy['checks']if x['original_key']==row['original_key']);missing=[x for x in chk['refs']if x['shipped_class']is None];assert all(x['shipped_class']==x['source_class']for x in chk['refs']if x['shipped_class']is not None)
  new=scoped.scoped_key(key,sha(candidate));results.append(dict(original_key=row['original_key'],virtual_candidate_key='%08x-%08x'%new,virtual_package_sha256=sha(candidate),virtual_package_bytes=len(candidate),virtual_payload_crc32=native.header[8],logical=[w,h],physical=[w,w],uv_scale=[1.,h/w],format=2,flags=4,payload_type=layout,source_package_sha256=sha(blob),source_texture_class=source_class,virtual_base_class=base_class,base_exact=True,alpha_hist_count_multiplier=ratio,source_payload_bytes=row['source_payload'],compact_payload_bytes=row['candidate_payload'],repeat_payload_bytes=len(native.payload),source_request_rounded=row['source_request_rounded'],compact_request_rounded=row['candidate_request_rounded'],repeat_request_rounded=(len(native.payload)+31)&~31,VQbook_exact=layout==2,independent_C_levels=levels,normalized_bilinear_cases=len(coords),normalized_max_error=worst,all_known_refs=len(chk['refs']),missing_profile_refs=missing,strict_profile_gate_closed_if_materialized=not missing,world_refs=row['world_refs']))
  if emit is not None:emit(row,candidate,new)
 result=dict(status='VIRTUAL_SOURCE_PLAN_NO_ASSET_OUTPUT_NO_SELECTION',input_alpha_seal='14fed52e7375c47bace26588c2f556c776eb5ee4c628202442ed1b34148813c1',source_pack_sha256=sha(raw),keys=16,source_exact_base=True,source_exact_normalized_sampling=True,source_texture_class_restored=16,strict_present_profile_keys_closed=14,missing_profile_keys_still_held=2,virtual_package_and_mirror_bytes=2*sum(x['virtual_package_bytes']for x in results),source_requests=sum(x['source_request_rounded']for x in results),compact_requests=sum(x['compact_request_rounded']for x in results),repeat_requests=sum(x['repeat_request_rounded']for x in results),additional_repeat_vs_compact_requests=sum(x['repeat_request_rounded']-x['compact_request_rounded']for x in results),independent_C_level_decodes=sum(len(x['independent_C_levels'])for x in results),records=results,limits=['Allcandidatebytes existed onlyinRAM; onlyJSON/sourceplan written. Original23held and allassets unchanged.','Repeat-square BASE/normalizedUV sampling exact; lower mips filtered/quantized. Largerpayload/request thancompact, no performance/netVRAM claim.','Present-profile14sourcepolicy closes invirtualproof,2keys also need3missing-profileUNKNOWN proof. No runtimehelper/metadata/recipe/programme/image/guest changes.','Main must select/allocate actualdata output; futuredirectworldtable exactkeys/descriptors/scales andphysicalworldCRC/FNV certificates needfresh integration/programme/targetqualification.'])
 B=(json.dumps(result,indent=2)+'\n').encode();assert len(B)<131072;(O/'virtual-repeat16.json').write_bytes(B);print(json.dumps({k:result[k]for k in('keys','virtual_package_and_mirror_bytes','source_requests','compact_requests','repeat_requests','additional_repeat_vs_compact_requests','independent_C_level_decodes','strict_present_profile_keys_closed','missing_profile_keys_still_held')}))
if __name__=='__main__':main()