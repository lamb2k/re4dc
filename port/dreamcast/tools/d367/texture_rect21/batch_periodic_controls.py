#!/usr/bin/env python3
"""Shared actual adapter and independent normalized periodic metric controls."""
from pathlib import Path
import ctypes,json,random,struct,sys,zlib
import compact,compact_periodic as adapter,rectangular_vq as rect

def main():
 lib=ctypes.CDLL(sys.argv[1]);err=lib.rect21_error_ratio;err.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_uint,ctypes.c_uint,ctypes.POINTER(ctypes.c_uint64),ctypes.POINTER(ctypes.c_uint)];cases=[];rng=random.Random(22177)
 for ratio in(2,4,8,16,32):
  n=8;w=ratio*n;src=bytes(rng.randrange(256)if i%4!=3 else 255 for i in range(w*n*4));dst=bytes(rng.randrange(256)if i%4!=3 else 255 for i in range(n*n*4));sse=ctypes.c_uint64();mx=ctypes.c_uint();assert err(src,dst,w,n,ctypes.byref(sse),ctypes.byref(mx))==0;den=2*ratio;d=[]
  for y in range(n):
   for x in range(w):
    p=rect.sample(dst,n,n,(x+.5)/w,(y+.5)/n);d.extend(round(den*(src[(y*w+x)*4+c]-p[c]))for c in range(3))
  assert sse.value==sum(x*x for x in d)and mx.value==max(map(abs,d));cases.append(dict(ratio=ratio,all_pixel_independent_periodic_metric=True,points=w*n))
  if ratio==2:
   old=lib.rect21_error4;old.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_uint,ctypes.POINTER(ctypes.c_uint64),ctypes.POINTER(ctypes.c_uint)];a=ctypes.c_uint64();b=ctypes.c_uint();assert old(src,dst,n,ctypes.byref(a),ctypes.byref(b))==0 and(a.value,b.value)==(sse.value,mx.value)
 # Exercise the actual filter with known constant feature blocks; assert its target passed to the existing encoder.
 for ratio in(2,4,8,16,32):
  side=8;w=ratio*side;pix=bytes(c for y in range(side)for x in range(w)for c in((x//ratio)*31,y*31,0,255));header=[b'RE4DCTX\0',1,48,1,0,48,144,0,0,0,0];tex=[bytes(64),w,side,0,144,2048+side*side//4,0,2,0]
  # Use real descriptor/header layouts and a real zero RGB565 codebook.
  payload=bytes(tex[5]);header[7]=len(payload);body=adapter.tpl.TEXTURE.pack(*tex)+payload;header[8]=zlib.crc32(body)&0xffffffff;blob=adapter.tpl.HEADER.pack(*header)+body
  calls=[];original=adapter.mip._encode_level
  def capture(target,n,book,engine):calls.append((target,n));return bytes(n*n//4),'test_capture'
  adapter.mip._encode_level=capture
  try:out=adapter.shorter_square(blob,pix,enabled=True)
  finally:adapter.mip._encode_level=original
  expected=[adapter.mip._feature((x*31,y*31,0,255))for y in range(side)for x in range(side)];assert calls==[(expected,side)];assert adapter.shorter_square(blob,pix)==blob
  assert adapter.tpl.HEADER.unpack_from(out)[8]==zlib.crc32(out[48:])&0xffffffff
  for bad in[pix[:-4],pix[:-1]+b'\x00']:
   try:adapter.shorter_square(blob,bad,enabled=True)
   except ValueError:pass
   else:raise AssertionError('invalid source pixels accepted')
  cases.append(dict(ratio=ratio,actual_filter_constant_blocks=True,default_off_exact=True,opacity_extent_rejections=2))
 print(json.dumps(dict(status='PASS_SHARED_PERIODIC_ADAPTER_METRIC',cases=cases)))
if __name__=='__main__':main()