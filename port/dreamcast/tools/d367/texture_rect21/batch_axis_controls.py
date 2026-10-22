#!/usr/bin/env python3
"""Vertical source-feature filtering and independent UV metric controls."""
import ctypes,json,random,sys,zlib
import compact_axis as a,rectangular_vq as rect

def transpose(b,w,h):return bytes(c for x in range(w)for y in range(h)for c in b[(y*w+x)*4:(y*w+x+1)*4])
def main():
 lib=ctypes.CDLL(sys.argv[1]);err=lib.rect21_error_ratio;err.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_uint,ctypes.c_uint,ctypes.POINTER(ctypes.c_uint64),ctypes.POINTER(ctypes.c_uint)];rng=random.Random(224);n=8;h=16;src=bytes(rng.randrange(256)if i%4!=3 else 255 for i in range(n*h*4));dst=bytes(rng.randrange(256)if i%4!=3 else 255 for i in range(n*n*4));s=ctypes.c_uint64();mx=ctypes.c_uint();assert err(transpose(src,n,h),transpose(dst,n,n),h,n,ctypes.byref(s),ctypes.byref(mx))==0;d=[]
 for y in range(h):
  for x in range(n):
   p=rect.sample(dst,n,n,(x+.5)/n,(y+.5)/h);d.extend(round(4*(src[(y*n+x)*4+c]-p[c]))for c in range(3))
 assert s.value==sum(x*x for x in d)and mx.value==max(map(abs,d))
 pix=bytes(c for y in range(h)for x in range(n)for c in(x*31,(y//2)*31,0,255));payload=bytes(2048+n*n//4);tex=[bytes(64),n,h,0,144,len(payload),0,2,0];body=a.tpl.TEXTURE.pack(*tex)+payload;head=[b'RE4DCTX\0',1,48,1,0,48,144,len(payload),zlib.crc32(body)&0xffffffff,0,0];blob=a.tpl.HEADER.pack(*head)+body;calls=[];old=a.mip._encode_level
 def capture(target,side,book,engine):calls.append((target,side));return bytes(side*side//4),'test_capture'
 a.mip._encode_level=capture
 try:result=a.shorter_square(blob,pix,enabled=True)
 finally:a.mip._encode_level=old
 assert calls==[([a.mip._feature((x*31,y*31,0,255))for y in range(n)for x in range(n)],n)]and a.shorter_square(blob,pix)==blob
 bad=[]
 for kind in('flag','format','extent','opacity'):
  t=list(tex);p=pix
  if kind=='flag':t[6]=1
  if kind=='format':t[3]=2
  if kind=='extent':p=p[:-4]
  if kind=='opacity':p=p[:-1]+b'\x00'
  b=a.tpl.TEXTURE.pack(*t)+payload;hh=list(head);hh[8]=zlib.crc32(b)&0xffffffff
  try:a.shorter_square(a.tpl.HEADER.pack(*hh)+b,p,enabled=True)
  except ValueError:bad.append(kind)
  else:raise AssertionError(kind)
 print(json.dumps(dict(status='PASS_VERTICAL_ACTUAL_FILTER_AND_UV_METRIC',known_target_blocks=64,independent_source_center_pixels=128,default_off_byteexact=True,rejected=bad)))
if __name__=='__main__':main()