#!/usr/bin/env python3
"""Separate default-disabled periodic opaque horizontal box approximation."""
import struct,zlib
import compact
mip,tpl=compact.mip,compact.tpl

def shorter_square(blob,source_pixels,*,enabled=False,engine="python"):
 if not enabled:return blob
 h=list(tpl.HEADER.unpack_from(blob));t=list(tpl.TEXTURE.unpack_from(blob,h[5]));w,side=t[1:3]
 if t[3]!=0 or t[6] or t[7]!=2 or side<8 or side>256 or side&(side-1) or w%side or w//side not in(2,4,8,16,32):raise ValueError('opaque RGB565 horizontal power-two VQ ratio contract')
 if len(source_pixels)!=w*side*4 or source_pixels[3::4]!=b"\xff"*(w*side):raise ValueError('source pixel extent/opacity')
 payload=blob[t[4]:t[4]+t[5]]
 if h[8]not in(zlib.crc32(blob[48:])&0xffffffff,zlib.crc32(payload)&0xffffffff):raise ValueError('source CRC')
 ratio=w//side;feature=[mip._feature(tuple(source_pixels[i:i+4]))for i in range(0,len(source_pixels),4)]
 target=[tuple((sum(feature[y*w+ratio*x+k][c]for k in range(ratio))+ratio//2)//ratio for c in range(4))for y in range(side)for x in range(side)]
 words=struct.unpack('<1024H',payload[:2048]);book=[tuple(c for j in range(i,i+4)for c in mip._feature(mip.rgba(words[j],0)))for i in range(0,1024,4)]
 indices,_=mip._encode_level(target,side,book,engine);p=payload[:2048]+indices;t[1]=t[2]=side;t[5]=len(p);h[7]=len(p);body=tpl.TEXTURE.pack(*t)+p;h[8]=zlib.crc32(body)&0xffffffff
 return tpl.HEADER.pack(*h)+body
