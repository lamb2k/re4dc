#!/usr/bin/env python3
"""Default-disabled native-format premultiplied alpha rectangle approximation."""
import struct,zlib
import compact
import mipmap_twiddled as tw
mip,tpl=compact.mip,compact.tpl

def shorter_square(blob,source_pixels,*,enabled=False,engine="python"):
 if not enabled:return blob
 h=list(tpl.HEADER.unpack_from(blob));t=list(tpl.TEXTURE.unpack_from(blob,h[5]));w,side,fmt=t[1:4];layout=t[7]
 if h[:6]!=[tpl.MAGIC,tpl.VERSION,48,96,1,48]or h[6]!=144 or len(blob)!=144+h[7]:raise ValueError('source header/extent')
 if fmt not in(1,2)or t[6]or layout not in(1,2)or t[8]or side not in(16,32,64,128)or w//side not in(2,4,8)or w%side or t[4]!=144:raise ValueError('alpha native horizontal contract')
 expected=2048+w*side//4 if layout==2 else w*side*2
 if t[5]!=expected or h[7]!=expected or len(source_pixels)!=w*side*4:raise ValueError('source native payload/pixels')
 if h[8]not in(zlib.crc32(blob[48:])&0xffffffff,zlib.crc32(blob[144:])&0xffffffff):raise ValueError('source CRC')
 ratio=w//side;features=[mip._feature(tuple(source_pixels[i:i+4]))for i in range(0,len(source_pixels),4)]
 target=[tuple((sum(features[y*w+ratio*x+k][c]for k in range(ratio))+ratio//2)//ratio for c in range(4))for y in range(side)for x in range(side)]
 if layout==2:
  book=blob[144:2192];words=struct.unpack('<1024H',book);vectors=[tuple(c for j in range(i,i+4)for c in mip._feature(mip.rgba(words[j],fmt)))for i in range(0,1024,4)];indices,_=mip._encode_level(target,side,vectors,engine);payload=book+indices
 else:payload=tw._encode_level(target,side,fmt)
 t[1]=t[2]=side;t[5]=h[7]=len(payload);body=tpl.TEXTURE.pack(*t)+payload;h[8]=zlib.crc32(body)&0xffffffff
 return tpl.HEADER.pack(*h)+body
