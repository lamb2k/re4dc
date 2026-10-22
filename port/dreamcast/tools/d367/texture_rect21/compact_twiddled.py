#!/usr/bin/env python3
"""Default-disabled opaque horizontal nativeTWIDDLED compact base; no VQ book."""
import struct,zlib
import compact
import mipmap_twiddled as tw
mip,tpl=compact.mip,compact.tpl

def shorter_square(blob,source_pixels,*,enabled=False,engine="python"):
 if not enabled:return blob
 h=list(tpl.HEADER.unpack_from(blob));t=list(tpl.TEXTURE.unpack_from(blob,h[5]));w,side=t[1:3]
 if h[:6]!=[tpl.MAGIC,tpl.VERSION,48,96,1,48]or h[6]!=144 or h[7]!=w*side*2 or len(blob)!=144+h[7]:raise ValueError('source header/extent')
 if t[3]!=0 or t[6] or t[7]!=1 or t[8]or side!=16 or w not in(32,64)or t[4]!=144 or t[5]!=w*side*2:raise ValueError('opaque twiddled32/64x16 contract')
 if len(source_pixels)!=w*side*4 or source_pixels[3::4]!=b"\xff"*(w*side):raise ValueError('source pixel extent/opacity')
 if h[8]not in(zlib.crc32(blob[48:])&0xffffffff,zlib.crc32(blob[144:])&0xffffffff):raise ValueError('source CRC')
 r=w//side;features=[mip._feature(tuple(source_pixels[i:i+4]))for i in range(0,len(source_pixels),4)]
 target=[tuple((sum(features[y*w+r*x+k][c]for k in range(r))+r//2)//r for c in range(4))for y in range(side)for x in range(side)]
 payload=tw._encode_level(target,side,0);t[1]=t[2]=side;t[5]=h[7]=len(payload);body=tpl.TEXTURE.pack(*t)+payload;h[8]=zlib.crc32(body)&0xffffffff
 return tpl.HEADER.pack(*h)+body
