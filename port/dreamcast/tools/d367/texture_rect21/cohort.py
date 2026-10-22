#!/usr/bin/env python3
"""Price all proven rectangles and qualify a bounded repeat-square cohort."""
from pathlib import Path
import argparse,collections,ctypes,hashlib,json,random,sys
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE),str(HERE.parents[1])]
import rectangular_vq as rect
import convert_tpl as tpl
import mipmap_vq as mip
from vram.vq_pak import read_pak

def sha(b):return hashlib.sha256(b).hexdigest()
def rounded(n):return (n+31)&~31

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 for k in ['pack','queue','bindings','oracle','out']:ap.add_argument('--'+k,type=Path,required=True)
 a=ap.parse_args()
 if a.out.exists():raise SystemExit('Preserve existing output: '+str(a.out))
 queue_raw=a.queue.read_bytes();binding_raw=a.bindings.read_bytes();q=json.loads(queue_raw);bindings=json.loads(binding_raw)['bindings']
 raw=a.pack.read_bytes();assert sha(raw)==q['source_pack_sha256'];pkgs=read_pak(raw)
 priced=[];held=[]
 for row in q['rows']:
  key=row['key'];blob=pkgs[tuple(int(x,16) for x in key.split('-'))];assert sha(blob)==row['source_package_sha256']
  if row['layout']!=2 or row['native_format']>2:
   held.append(dict(key=key,reason='not original full-codebook 16-bit VQ'));continue
  w,h=row['width'],row['height'];s=max(w,h);base=2048+s*s//4;chain=2048+tpl.vq_mip_index_bytes(s)
  rooms=sorted(set(v['world'].split('/')[2] for v in bindings[key]))
  priced.append(dict(key=key,logical=[w,h],rooms=rooms,ratio=s//min(w,h),original=row['payload_bytes'],square_base=base,square_mips=chain,rounded_original=rounded(row['payload_bytes']),rounded_square_mips=rounded(chain),delta=chain-row['payload_bytes']))
 selected=[r for r in priced if r['logical']==[128,64] and set(r['rooms'])&{'r100','r103'}]
 assert len(selected)==19
 lib=ctypes.CDLL(str(a.oracle));decode=lib.rect_oracle_decode;decode.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_uint,ctypes.c_uint,ctypes.c_uint,ctypes.c_void_p,ctypes.c_size_t]
 call=lib.mipmap_oracle_decode;call.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_uint,ctypes.c_uint,ctypes.c_int,ctypes.c_uint,ctypes.c_void_p,ctypes.c_size_t]
 def original_pixels(b,w,h):
  head=tpl.HEADER.unpack_from(b);t=tpl.TEXTURE.unpack_from(b,head[5]);p=b[t[4]:t[4]+t[5]];o=(ctypes.c_ubyte*(w*h*4))();assert decode(p,len(p),t[3],w,h,o,len(o))==len(o);return bytes(o)
 a.out.mkdir(parents=True);(a.out/'packages').mkdir();results=[];images=[]
 from PIL import Image,ImageDraw
 rng=random.Random(211003)
 coords=[(rng.uniform(-8,8),rng.uniform(-8,8)) for _ in range(96)]+[(u,v) for u in [-1,0,.5,1] for v in [-1,0,.5,1]]
 for row in selected:
  key=row['key'];blob=pkgs[tuple(int(x,16) for x in key.split('-'))];square,meta=rect.square_candidate(blob,enabled=True)
  assert rect.square_candidate(blob)[0]==blob
  candidate,_=mip.add_mipmaps(square,enabled=True,engine='python');native=mip.read_native_vq(candidate)
  w,h=row['logical'];s=meta['square_side'];before=original_pixels(blob,w,h);expanded=original_pixels(square,s,s)
  assert expanded==b''.join(before[(y%h)*w*4:(y%h+1)*w*4] for y in range(s))
  worst=max(max(abs(x-y) for x,y in zip(rect.sample(before,w,h,u,v),rect.sample(expanded,s,s,u*w/s,v*h/s))) for u,v in coords)
  assert worst<1e-8
  levels=[]
  for level in range(s.bit_length()):
   side=1<<level;o=(ctypes.c_ubyte*(side*side*4))();assert call(native.payload,len(native.payload),native.texture[3],s,1,level,o,len(o))==len(o)
   assert bytes(o)==bytes(c for p in mip.decode_level(native,side) for c in p);levels.append(side)
  (a.out/'packages'/(key+'.re4tex')).write_bytes(candidate)
  im=Image.new('RGB',(384,152),'#202020');draw=ImageDraw.Draw(im);draw.text((4,2),key,fill='white');im.paste(Image.frombytes('RGBA',(w,h),before).convert('RGB'),(0,20));im.paste(Image.frombytes('RGBA',(s,s),expanded).convert('RGB'),(128,20));mip32=Image.new('RGBA',(32,32));mip32.putdata(mip.decode_level(native,32));im.paste(mip32.convert('RGB').resize((128,128)),(256,20));images.append(im)
  head=tpl.HEADER.unpack_from(candidate);tex=tpl.TEXTURE.unpack_from(candidate,head[5])
  results.append(dict(**row,source_sha256=sha(blob),candidate_sha256=sha(candidate),candidate_crc32=head[8],candidate_format=tex[3],candidate_flags=tex[6],candidate_payload=tex[7],candidate_bytes=tex[5],uv_scale=meta['uv_scale'],sample_cases=len(coords),maximum_base_error=worst,decoded_levels=levels))
 sheet=Image.new('RGB',(384*3,152*((len(images)+2)//3)),'#202020')
 for i,im in enumerate(images):sheet.paste(im,((i%3)*384,(i//3)*152))
 sheet.save(a.out/'cohort-contact.png')
 def totals(rows):return {k:sum(r[k] for r in rows) for k in ['original','square_base','square_mips','rounded_original','rounded_square_mips','delta']}
 report=dict(schema='re4dc-rect-cohort-source-1',source_pack_sha256=sha(raw),queue_sha256=sha(queue_raw),bindings_sha256=sha(binding_raw),oracle_sha256=sha(a.oracle.read_bytes()),supported_keys=len(priced),held_keys=held,whole_supported_totals=totals(priced),groups={str(ratio):dict(keys=len(rows),**totals(rows)) for ratio in sorted(set(r['ratio'] for r in priced)) for rows in [[r for r in priced if r['ratio']==ratio]]},room_selected_totals={room:dict(keys=len(rows),**totals(rows)) for room in ['r100','r103'] for rows in [[r for r in selected if room in r['rooms']]]},selected_totals=totals(selected),selected=results,priced=priced,limits=['Offline source and independent decoder gates only; no runtime program or rendered scene exists for this cohort.','Costs are descriptor payload requests and rounded requests, not observed VRAM, allocator fragmentation or load peak.','Whole-set cost sums unique keys; room residency must use actual simultaneous textures and other consumers.','Original full-resolution VQ pixels/codebooks are exact; lower mip levels are filtered and requantized.','Representation grows storage and memory; no performance benefit or look acceptance is claimed.','Legacy native_ps2_world packet consumers omit packet UV scales and remain excluded.'])
 (a.out/'receipt.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({k:report[k] for k in ['supported_keys','whole_supported_totals','selected_totals','room_selected_totals']}))
if __name__=='__main__':main()
