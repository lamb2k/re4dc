#!/usr/bin/env python3
"""Exact authored diffuse-alpha footprint reference for Salazar, offline only.

Coordinates are integers in texel-centre space divided by ``den``: PS2 raw
UV/256 at width W becomes x=(raw_u*W-128)/256. A texel contributes iff its
open bilinear support rectangle intersects the closed UV triangle. Strict
integer SAT excludes zero-weight neighbours; a separate Fraction polygon
clip supplies a positive-weight witness. No float threshold, rounding or
cyclic face canonicalization determines membership.

This is a source-texel coverage oracle. Material/TPL identity and source UV
correspondence must be proved by the caller. It does not model PS2 GS ALPHA,
TEST, LOD/filter selection, texture functions or runtime draw admission.
"""
from fractions import Fraction as F
import numpy as np


def _validate(pts, img, wrap, den):
    if type(den) is not int or den <= 0:
        raise ValueError('positive integer coordinate denominator required')
    if len(pts) != 3 or any(len(p) != 2 or any(type(x) is not int for x in p) for p in pts):
        raise ValueError('three exact integer UV points required')
    if len(wrap) != 2 or any(x not in (0, 1) for x in wrap):
        raise ValueError('only explicit clamp or repeat supported')
    if not isinstance(img, np.ndarray) or img.ndim != 2 or img.dtype != np.uint8 or min(img.shape) <= 0:
        raise ValueError('nonempty authored uint8 alpha plane required')


SAMPLES=[((1,0,0),1),((0,1,0),1),((0,0,1),1),((1,1,0),2),((0,1,1),2),((1,0,1),2),((1,1,1),3)]

def support_axis(n,d,size,wrap):
 # n/d is a texel coordinate, with centres at integers.
 j=n//d;r=n-j*d
 out=[]
 for i,num in [(j,d-r),(j+1,r)]:
  if num:
   out.append((i%size if wrap else min(size-1,max(0,i)),F(num,d)))
 return out

def alpha_at(img,x,y,wrap):
 h,w=img.shape;out=F(0)
 for ix,wx in support_axis(x.numerator,x.denominator,w,wrap[0]):
  for iy,wy in support_axis(y.numerator,y.denominator,h,wrap[1]):out+=int(img[iy,ix])*wx*wy
 return out

def seven(pts,img,wrap,den=256):
 _validate(pts,img,wrap,den)
 # pts are exact texel-centre coordinates scaled by den.
 for bary,d in SAMPLES:
  x=F(sum(v*p[0] for v,p in zip(bary,pts)),d*den);y=F(sum(v*p[1] for v,p in zip(bary,pts)),d*den)
  if alpha_at(img,x,y,wrap)<255:return True
 return False

def touches_open_rect(pts,j,k,den):
 # Closed triangle versus OPEN support rectangle. Strict SAT keeps zero-weight
 # neighbours excluded. All arithmetic is integer, including UV-degenerate faces.
 xl,xh=(j-1)*den,(j+1)*den;yl,yh=(k-1)*den,(k+1)*den
 xs=[p[0] for p in pts];ys=[p[1] for p in pts]
 if max(xs)<=xl or min(xs)>=xh or max(ys)<=yl or min(ys)>=yh:return False
 for a,b in zip(pts,pts[1:]+pts[:1]):
  nx,ny=-(b[1]-a[1]),b[0]-a[0]
  if not(nx or ny):continue
  q=[nx*x+ny*y for x,y in pts];lo=nx*(xl if nx>=0 else xh)+ny*(yl if ny>=0 else yh);hi=nx*(xh if nx>=0 else xl)+ny*(yh if ny>=0 else yl)
  if max(q)<=lo or min(q)>=hi:return False
 return True

def clipped_witness(pts,j,k,den):
 # Independent rational polygon clipping cross-check for a selected SAT hit.
 poly=[(F(x),F(y)) for x,y in pts];bounds=[(0,F((j-1)*den),1),(0,F((j+1)*den),-1),(1,F((k-1)*den),1),(1,F((k+1)*den),-1)]
 for axis,b,sign in bounds:
  if not poly:return None
  nxt=[]
  for a,c in zip(poly,poly[1:]+poly[:1]):
   da,dc=(a[axis]-b)*sign,(c[axis]-b)*sign
   if da>=0:nxt.append(a)
   if (da<0<=dc) or (dc<0<=da):
    t=da/(da-dc);nxt.append(tuple(a[z]+t*(c[z]-a[z]) for z in (0,1)))
  poly=nxt
 if not poly:return None
 q=tuple(sum(p[z] for p in poly)/len(poly) for z in (0,1))
 if all((q[axis]-b)*sign>0 for axis,b,sign in bounds):return q
 return None

def footprint(pts,img,wrap,den=256,witness=False):
 _validate(pts,img,wrap,den)
 h,w=img.shape
 if bool((img==255).all()):return None
 lo=[min(p[z] for p in pts)//den for z in (0,1)];hi=[-(-max(p[z] for p in pts)//den) for z in (0,1)]
 xx=np.arange(lo[0],hi[0]+1);yy=np.arange(lo[1],hi[1]+1)
 ix=xx%w if wrap[0] else np.clip(xx,0,w-1);iy=yy%h if wrap[1] else np.clip(yy,0,h-1)
 for by,bx in np.argwhere(img[np.ix_(iy,ix)]<255):
  j,k=int(xx[bx]),int(yy[by])
  if touches_open_rect(pts,j,k,den):
   if not witness:return (j,k)
   q=clipped_witness(pts,j,k,den);assert q is not None,('SAT/clip disagreement',pts,j,k)
   value=alpha_at(img,q[0]/den,q[1]/den,wrap);assert value<255,(pts,j,k,value)
   return dict(unwrapped_texel=[j,k],source_texel=[int(ix[bx]),int(iy[by])],texel_alpha8=int(img[iy[by],ix[bx]]),point_texel_coordinate=[[v.numerator,v.denominator*den] for v in q],sample_alpha8=[value.numerator,value.denominator])
 return None
