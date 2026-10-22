#!/usr/bin/env python3
"""Offline repeated-square VQ candidate; not a runtime-compatible replacement."""
from pathlib import Path
import argparse,collections,ctypes,hashlib,json,math,random,struct,sys,zlib
TOOLS=Path(__file__).resolve().parents[2];sys.path[:0]=[str(TOOLS),str(TOOLS/'d367')]
import convert_tpl as tpl
import mipmap_vq as mip
from vram.vq_pak import read_pak

def sha(b):return hashlib.sha256(b).hexdigest()
def square_candidate(blob,*,enabled=False):
 if not enabled:return blob,{'enabled':False,'exact':True}
 h=list(tpl.HEADER.unpack_from(blob));t=list(tpl.TEXTURE.unpack_from(blob,h[5]));_,w,hh,fmt,off,n,flags,layout,reserved=t
 if h[:6]!=[tpl.MAGIC,tpl.VERSION,tpl.HEADER.size,tpl.TEXTURE.size,1,tpl.HEADER.size]:raise ValueError('nonstandard descriptor')
 if w==hh or min(w,hh)<8 or max(w,hh)>1024 or w&(w-1) or hh&(hh-1) or fmt>2 or layout!=2 or reserved or flags&tpl.FLAG_MIPMAP:raise ValueError('unsupported rectangle')
 if n!=2048+w*hh//4 or off!=144 or h[6]!=off or h[7]!=n or len(blob)!=off+n:raise ValueError('truncated VQ payload')
 payload=blob[off:]
 if h[8]==zlib.crc32(blob[48:])&0xffffffff:rule='header'
 elif h[8]==zlib.crc32(payload)&0xffffffff:rule='data'
 else:raise ValueError('source checksum mismatch')
 bw,bh=w//2,hh//2;s=max(w,hh);bs=s//2
 linear=bytearray(bw*bh)
 for at,index in enumerate(tpl.twiddle_16bpp(list(range(bw*bh)),bw,bh)):linear[index]=payload[2048+at]
 indices=bytes(linear[(i//bs%bh)*bw+(i%bs%bw)] for i in tpl.twiddle_16bpp(list(range(bs*bs)),bs,bs))
 square=payload[:2048]+indices;t[1:3]=[s,s];t[5]=len(square);h[7]=len(square)
 body=tpl.TEXTURE.pack(*t)+square;h[8]=zlib.crc32(body)&0xffffffff
 return tpl.HEADER.pack(*h)+body,dict(enabled=True,source_dimensions=[w,hh],square_side=s,uv_scale=[w/s,hh/s],source_payload_bytes=n,square_base_payload_bytes=len(square),crc_rule='header',source_crc_rule=rule,codebook_exact=True,runtime_compatible=False)

def sample(p,w,h,u,v):
 x,y=u*w-.5,v*h-.5;ix,iy=math.floor(x),math.floor(y);fx,fy=x-ix,y-iy
 return [sum(p[((iy+dy)%h*w+(ix+dx)%w)*4+c]*((fx if dx else 1-fx)*(fy if dy else 1-fy)) for dy in (0,1) for dx in (0,1)) for c in range(4)]
def main():
 ap=argparse.ArgumentParser();
 for k in ['pack','bindings','queue','oracle','out']:ap.add_argument('--'+k,type=Path,required=True)
 ap.add_argument('--room',default='r103');a=ap.parse_args();assert not a.out.exists()
 raw=a.pack.read_bytes();q=json.loads(a.queue.read_text());assert sha(raw)==q['source_pack_sha256'];pkgs=read_pak(raw)
 binds=json.loads(a.bindings.read_text())['bindings'];rows=[r for r in q['rows'] if any('/'+a.room+'/' in v['world'] for v in binds[r['key']]) and r['layout']==2 and r['width']==128 and r['height']==64]
 assert rows,'No proven128x64 VQ room cohort';row=rows[0];key=row['key'];blob=pkgs[tuple(int(x,16) for x in key.split('-'))];assert sha(blob)==row['source_package_sha256']
 square,meta=square_candidate(blob,enabled=True);assert square_candidate(blob)[0]==blob
 result,mips=mip.add_mipmaps(square,enabled=True,engine='python');native=mip.read_native_vq(result)
 lib=ctypes.CDLL(str(a.oracle));rect=lib.rect_oracle_decode;rect.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_uint,ctypes.c_uint,ctypes.c_uint,ctypes.c_void_p,ctypes.c_size_t]
 def decode(b,w,h):
  header=tpl.HEADER.unpack_from(b);t=tpl.TEXTURE.unpack_from(b,header[5]);payload=b[t[4]:t[4]+t[5]];o=(ctypes.c_ubyte*(w*h*4))();assert rect(payload,len(payload),t[3],w,h,o,len(o))==len(o);return bytes(o)
 w,h=meta['source_dimensions'];s=meta['square_side'];source=decode(blob,w,h);expanded=decode(square,s,s)
 for y in range(s):
  for x in range(s):assert expanded[(y*s+x)*4:(y*s+x+1)*4]==source[((y%h)*w+x%w)*4:((y%h)*w+x%w+1)*4]
 call=lib.mipmap_oracle_decode;call.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_uint,ctypes.c_uint,ctypes.c_int,ctypes.c_uint,ctypes.c_void_p,ctypes.c_size_t]
 levels=[]
 for level in range(s.bit_length()):
  side=1<<level;o=(ctypes.c_ubyte*(side*side*4))();assert call(native.payload,len(native.payload),native.texture[3],s,1,level,o,len(o))==len(o)
  assert bytes(o)==bytes(c for p in mip.decode_level(native,side) for c in p);levels.append(side)
 rng=random.Random(210103);coords=[(rng.uniform(-8,8),rng.uniform(-8,8)) for _ in range(2048)]+[(u,v) for u in [-8,-1,-.5,0,.5,1,8] for v in [-8,-1,-.5,0,.5,1,8]]
 worst=0;negative=0
 for u,v in coords:
  old=sample(source,w,h,u,v);new=sample(expanded,s,s,u*w/s,v*h/s);wrong=sample(expanded,s,s,u,v)
  worst=max(worst,max(abs(x-y) for x,y in zip(old,new)));negative+=any(abs(x-y)>1e-8 for x,y in zip(old,wrong))
 assert worst<1e-8 and negative>0
 a.out.mkdir(parents=True);(a.out/'source.re4tex').write_bytes(blob);(a.out/'square-base.re4tex').write_bytes(square);(a.out/'square-mips.re4tex').write_bytes(result)
 from PIL import Image
 Image.frombytes('RGBA',(w,h),source).save(a.out/'before.png');Image.frombytes('RGBA',(s,s),expanded).save(a.out/'repeated-square.png')
 receipt=dict(key=key,room=a.room,**meta,source_package_sha256=sha(blob),candidate_sha256=sha(result),mip_payload_bytes=len(native.payload),base_sampling_cases=len(coords),maximum_channel_error=worst,wrong_UV_negative_control_failures=negative,independently_decoded_levels=levels,base_pixels_exact=True,limits=['OFF preserves original bytes; enabled output is a private offline prototype.','World dimensions and all packet UV consumer paths still need an opt-in runtime contract.','Lower mips use existing filtered/quantized VQ; exact base sampling does not certify lower-level look.','Square storage is larger; no resource/performance win or release adoption.'])
 (a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
if __name__=='__main__':main()