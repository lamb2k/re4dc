#!/usr/bin/env python3
"""Held source-only opaque 2:1 room cohort; does not alter an active fixture."""
from pathlib import Path
import argparse,ctypes,hashlib,json,math,shutil,sys
HERE=Path(__file__).resolve().parent;sys.path[:0]=[str(HERE),str(HERE.parent),str(HERE.parents[1])]
import compact
import rectangular_vq as rect
import convert_tpl as tpl
import mipmap_vq as mip
from vram.vq_pak import read_pak

def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 ap=argparse.ArgumentParser(description=__doc__)
 for k in ['pack','queue','bindings','oracle','out']:ap.add_argument('--'+k,type=Path,required=True)
 ap.add_argument('--room',default='r101');ap.add_argument('--width',type=int,default=256);ap.add_argument('--height',type=int,default=128);a=ap.parse_args();assert not a.out.exists() and a.width==2*a.height
 assert shutil.disk_usage('/mnt/c').free>18*1024**3+16*1024**2,'C source-output floor'
 raw=a.pack.read_bytes();q=json.loads(a.queue.read_text());b=json.loads(a.bindings.read_text());assert sha(raw)==q['source_pack_sha256']==b['source_pack_sha256'];pkgs=read_pak(raw)
 selected=[r for r in q['rows'] if r['width']==a.width and r['height']==a.height and r['layout']==2 and r['native_format']==0 and any('/'+a.room+'/' in v['world'] for v in b['bindings'][r['key']])];assert selected
 lib=ctypes.CDLL(str(a.oracle));decode=lib.rect_oracle_decode;decode.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_uint,ctypes.c_uint,ctypes.c_uint,ctypes.c_void_p,ctypes.c_size_t];call=lib.mipmap_oracle_decode;call.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_uint,ctypes.c_uint,ctypes.c_int,ctypes.c_uint,ctypes.c_void_p,ctypes.c_size_t]
 def pixels(blob,w,h):
  head=tpl.HEADER.unpack_from(blob);t=tpl.TEXTURE.unpack_from(blob,head[5]);payload=blob[t[4]:t[4]+t[5]];out=(ctypes.c_ubyte*(w*h*4))();assert decode(payload,len(payload),t[3],w,h,out,len(out))==len(out);return bytes(out)
 a.out.mkdir(parents=True);(a.out/'packages').mkdir();results=[];held=[];images=[]
 from PIL import Image,ImageDraw
 for row in selected:
  key=row['key'];blob=pkgs[tuple(int(v,16) for v in key.split('-'))];assert sha(blob)==row['source_package_sha256'];head=tpl.HEADER.unpack_from(blob);t=tpl.TEXTURE.unpack_from(blob,head[5])
  if t[6]:held.append(dict(key=key,reason='source alpha/other flags held'));continue
  before=pixels(blob,a.width,a.height);assert compact.shorter_square(blob,before)==blob;base=compact.shorter_square(blob,before,enabled=True);candidate,_=mip.add_mipmaps(base,enabled=True,engine='python');native=mip.read_native_vq(candidate);after=pixels(base,a.height,a.height);levels=[]
  assert native.codebook==blob[144:2192]
  for level in range(a.height.bit_length()):
   side=1<<level;out=(ctypes.c_ubyte*(side*side*4))();assert call(native.payload,len(native.payload),0,a.height,1,level,out,len(out))==len(out);assert bytes(out)==bytes(c for p in mip.decode_level(native,side) for c in p);levels.append(side)
  mse=0.;worst=0.
  for y in range(a.height):
   for x in range(a.width):
    old=before[(y*a.width+x)*4:(y*a.width+x+1)*4];new=rect.sample(after,a.height,a.height,(x+.5)/a.width,(y+.5)/a.height);mse+=sum((old[c]-new[c])**2 for c in range(3));worst=max(worst,max(abs(old[c]-new[c]) for c in range(3)))
  mse/=a.width*a.height*3
  (a.out/'packages'/(key+'.re4tex')).write_bytes(candidate)
  im=Image.new('RGB',(a.width*3,a.height+24),'#202020');draw=ImageDraw.Draw(im);draw.text((3,3),key+' original | compact | lower32',fill='white');im.paste(Image.frombytes('RGBA',(a.width,a.height),before).convert('RGB'),(0,24));im.paste(Image.frombytes('RGBA',(a.height,a.height),after).convert('RGB').resize((a.width,a.height)),(a.width,24));low=Image.new('RGBA',(32,32));low.putdata(mip.decode_level(native,32));im.paste(low.convert('RGB').resize((a.width,a.height)),(2*a.width,24));images.append(im)
  results.append(dict(key=key,logical=[a.width,a.height],physical=[a.height,a.height],uv_scale=[1.,1.],source_sha256=sha(blob),candidate_sha256=sha(candidate),candidate_crc32=native.header[8],source_payload=t[5],candidate_payload=len(native.payload),source_rounded=(t[5]+31)&~31,candidate_rounded=(len(native.payload)+31)&~31,codebook_exact=True,base_exact=False,source_texel_center_rgb_rmse=math.sqrt(mse),source_texel_center_rgb_psnr=10*math.log10(255*255/mse) if mse else None,maximum_base_channel_error=worst,decoded_levels=levels,bindings=b['bindings'][key]))
 sheet=Image.new('RGB',(a.width*3,(a.height+24)*len(images)),'#202020')
 for i,im in enumerate(images):sheet.paste(im,(0,i*(a.height+24)))
 sheet.save(a.out/'contact.png')
 r=dict(schema='re4dc-rect21-held-room-cohort-1',room=a.room,logical=[a.width,a.height],source_pack_sha256=sha(raw),queue_sha256=sha(a.queue.read_bytes()),bindings_sha256=sha(a.bindings.read_bytes()),oracle_sha256=sha(a.oracle.read_bytes()),selected=results,held=held,source_payload=sum(v['source_payload'] for v in results),candidate_payload=sum(v['candidate_payload'] for v in results),source_rounded=sum(v['source_rounded'] for v in results),candidate_rounded=sum(v['candidate_rounded'] for v in results),independent_mip_decodes=sum(len(v['decoded_levels']) for v in results),limits=['Held offline approximation only; active scoped17 source table and frozen data set stay unchanged.','Original codebooks retained; full-resolution base filtered/requantized. Normalized UVs remain1,1.','Original-key filenames are evidence labels only; none is inserted into a runtime pack or staged. Scoped IDs/consumer closure are required before future selection.','No actual allocation, scene look, frame-time, full program, release or physical Dreamcast acceptance.'])
 (a.out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:r[k] for k in ['source_payload','candidate_payload','source_rounded','candidate_rounded','independent_mip_decodes']}))
if __name__=='__main__':main()
