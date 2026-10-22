#!/usr/bin/env python3
"""Guarded shorter-side square approximation; no pack or runtime edits."""
from pathlib import Path
import argparse,ctypes,hashlib,json,math,struct,sys,zlib
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE),str(HERE.parents[1])]
import rectangular_vq as rect
import convert_tpl as tpl
import mipmap_vq as mip
from vram.vq_pak import read_pak

def sha(b):return hashlib.sha256(b).hexdigest()
def shorter_square(blob,source_pixels,*,enabled=False):
 if not enabled:return blob
 h=list(tpl.HEADER.unpack_from(blob));t=list(tpl.TEXTURE.unpack_from(blob,h[5]));w,hh=t[1:3]
 if t[3]!=0 or t[6] or t[7]!=2 or w!=2*hh or hh<8:raise ValueError('first approximation accepts only opaque RGB565 2:1 VQ')
 payload=blob[t[4]:t[4]+t[5]];rule='header' if h[8]==zlib.crc32(blob[48:])&0xffffffff else 'data'
 assert h[8]==zlib.crc32(blob[48:] if rule=='header' else payload)&0xffffffff
 feature=[mip._feature(tuple(source_pixels[i:i+4])) for i in range(0,len(source_pixels),4)]
 target=[tuple((feature[y*w+2*x][c]+feature[y*w+2*x+1][c]+1)//2 for c in range(4)) for y in range(hh) for x in range(hh)]
 words=struct.unpack('<1024H',payload[:2048]);book=[tuple(c for j in range(i,i+4) for c in mip._feature(mip.rgba(words[j],0))) for i in range(0,1024,4)]
 indices,_=mip._encode_level(target,hh,book,'python');p=payload[:2048]+indices;t[1]=t[2]=hh;t[5]=len(p);h[7]=len(p);body=tpl.TEXTURE.pack(*t)+p;h[8]=zlib.crc32(body)&0xffffffff
 return tpl.HEADER.pack(*h)+body

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 for k in ['pack','cohort','oracle','out']:ap.add_argument('--'+k,type=Path,required=True)
 a=ap.parse_args();assert not a.out.exists(),'Preserve existing output'
 raw=a.pack.read_bytes();cohort=json.loads(a.cohort.read_text());assert sha(raw)==cohort['source_pack_sha256'];pkgs=read_pak(raw)
 lib=ctypes.CDLL(str(a.oracle));decode=lib.rect_oracle_decode;decode.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_uint,ctypes.c_uint,ctypes.c_uint,ctypes.c_void_p,ctypes.c_size_t]
 call=lib.mipmap_oracle_decode;call.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_uint,ctypes.c_uint,ctypes.c_int,ctypes.c_uint,ctypes.c_void_p,ctypes.c_size_t]
 def decode_rect(b,w,h):
  head=tpl.HEADER.unpack_from(b);t=tpl.TEXTURE.unpack_from(b,head[5]);p=b[t[4]:t[4]+t[5]];o=(ctypes.c_ubyte*(w*h*4))();assert decode(p,len(p),t[3],w,h,o,len(o))==len(o);return bytes(o)
 a.out.mkdir(parents=True);(a.out/'packages').mkdir();results=[];held=[];images=[]
 from PIL import Image,ImageDraw
 for row in cohort['selected']:
  key=row['key'];blob=pkgs[tuple(int(x,16) for x in key.split('-'))];h=tpl.HEADER.unpack_from(blob);t=tpl.TEXTURE.unpack_from(blob,h[5])
  if t[3]!=0 or t[6]:held.append(dict(key=key,reason='alpha format or source flags excluded from first approximation'));continue
  source=decode_rect(blob,128,64);assert shorter_square(blob,source)==blob
  base=shorter_square(blob,source,enabled=True);assert base==shorter_square(blob,source,enabled=True)
  result,_=mip.add_mipmaps(base,enabled=True,engine='python');native=mip.read_native_vq(result);expanded=decode_rect(base,64,64);levels=[]
  for level in range(7):
   side=1<<level;o=(ctypes.c_ubyte*(side*side*4))();assert call(native.payload,len(native.payload),0,64,1,level,o,len(o))==len(o);assert bytes(o)==bytes(c for p in mip.decode_level(native,side) for c in p);levels.append(side)
  mse=0.;worst=0.;wrong=0
  for y in range(64):
   for x in range(128):
    u,v=(x+.5)/128,(y+.5)/64;old=source[(y*128+x)*4:(y*128+x+1)*4];new=rect.sample(expanded,64,64,u,v);bad=rect.sample(expanded,64,64,u*2,v)
    mse+=sum((old[c]-new[c])**2 for c in range(3));worst=max(worst,max(abs(old[c]-new[c]) for c in range(3)));wrong+=any(abs(new[c]-bad[c])>1e-8 for c in range(3))
  mse/=128*64*3
  out=a.out/'packages'/(key+'.re4tex');out.write_bytes(result);head=tpl.HEADER.unpack_from(result);tex=tpl.TEXTURE.unpack_from(result,head[5])
  im=Image.new('RGB',(384,88),'#202020');d=ImageDraw.Draw(im);d.text((2,2),key,fill='white');im.paste(Image.frombytes('RGBA',(128,64),source).convert('RGB'),(0,20));im.paste(Image.frombytes('RGBA',(64,64),expanded).convert('RGB').resize((128,64)),(128,20));low=Image.new('RGBA',(32,32));low.putdata(mip.decode_level(native,32));im.paste(low.convert('RGB').resize((128,64)),(256,20));images.append(im)
  results.append(dict(key=key,logical=[128,64],physical=[64,64],uv_scale=[1.,1.],rooms=row['rooms'],source_sha256=sha(blob),candidate_sha256=sha(result),candidate_crc32=head[8],candidate_format=tex[3],candidate_flags=tex[6],candidate_payload=tex[7],candidate_bytes=tex[5],original=4096,rounded_original=4096,rounded_candidate=(tex[5]+31)&~31,decoded_levels=levels,source_texel_center_rgb_rmse=math.sqrt(mse),source_texel_center_rgb_psnr=10*math.log10(255*255/mse) if mse else None,maximum_base_channel_error=worst,wrong_dimension_scale_negative_cases=wrong,codebook_exact=native.codebook==blob[144:2192],base_exact=False))
 sheet=Image.new('RGB',(384*3,88*((len(images)+2)//3)),'#202020')
 for i,im in enumerate(images):sheet.paste(im,((i%3)*384,(i//3)*88))
 sheet.save(a.out/'compact-contact.png')
 r=dict(schema='re4dc-rect-short-square-approximation-1',source_pack_sha256=sha(raw),cohort_sha256=sha(a.cohort.read_bytes()),oracle_sha256=sha(a.oracle.read_bytes()),selected=results,held=held,original_bytes=sum(v['original'] for v in results),rounded_original_bytes=sum(v['rounded_original'] for v in results),candidate_bytes=sum(v['candidate_bytes'] for v in results),rounded_candidate_bytes=sum(v['rounded_candidate'] for v in results),limits=['Guarded offline approximation only; codebook preserved, full-resolution base is deliberately filtered and requantized.','Normalized UVs stay unchanged despite changed physical aspect; using logical/physical dimension ratios is wrong.','Opaque RGB565 only; alpha formats and flags held.','Payload/request comparisons are not runtime allocation, frame time, look or physical Dreamcast acceptance.','No pack composed, no runtime hook installed, no production/default recipe changed.'])
 (a.out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:r[k] for k in ['original_bytes','candidate_bytes','rounded_original_bytes','rounded_candidate_bytes']}))
if __name__=='__main__':main()
