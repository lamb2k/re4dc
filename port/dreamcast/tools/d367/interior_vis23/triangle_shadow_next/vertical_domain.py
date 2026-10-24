"""Exact nominal Y halfspaces for the unchanged two-real-triangle union theorem.

Every predicate is affine in eye Y at fixed XZ and target/source endpoints.
No height sampling, PVS writing, interval-error or renderer admission occurs.
"""
from fractions import Fraction as Q
from itertools import product
from exact_shadow import vec,sub,cross,dot,det,corners
from exact_union import boundary,prove_union


def affine_row(label,evaluate):
 b=Q(evaluate(Q(0)));a=Q(evaluate(Q(1)))-b
 # Exact identity spot-control only; multilinearity supplies the theorem.
 if any(Q(evaluate(y))!=a*y+b for y in (Q(-1),Q(2))):raise ValueError('Nonaffine predicate')
 return dict(label=label,a=a,b=b)


def intersect(rows):
 lower=upper=None;lower_labels=[];upper_labels=[];constant_refusals=[]
 for row in rows:
  a,b=row['a'],row['b'];label=row['label']
  if a==0:
   if b<=0:constant_refusals.append(label)
  elif a>0:
   root=-b/a
   if lower is None or root>lower:lower=root;lower_labels=[label]
   elif root==lower:lower_labels.append(label)
  else:
   root=-b/a
   if upper is None or root<upper:upper=root;upper_labels=[label]
   elif root==upper:upper_labels.append(label)
 return dict(nonempty=not constant_refusals and (lower is None or upper is None or lower<upper),lower=lower,upper=upper,lower_strict=True,upper_strict=True,lower_labels=lower_labels,upper_labels=upper_labels,constant_refusals=constant_refusals)


def quantized_band(interval,eye_y):
 """Maximal int16 *100 closed band strictly inside all open halfspaces."""
 if not interval['nonempty']:return dict(representable=False,reason='empty_analytic_interval')
 lo=interval['lower'];hi=interval['upper']
 low=-32768 if lo is None else max(-32768,(lo/100).numerator//(lo/100).denominator+1)
 upper=32767 if hi is None else min(32767,-((-hi/100).numerator//(-hi/100).denominator)-1)
 if low>=upper:return dict(representable=False,reason='no_positive_width_signed100mm_band',minimum_ylo_units=low,maximum_yhi_units=upper)
 if not low*100<=eye_y<=upper*100:return dict(representable=False,reason='quantized_band_does_not_contain_authentic_eye',minimum_ylo_units=low,maximum_yhi_units=upper)
 return dict(representable=True,ylo_units=low,yhi_units=upper,minimum_mm=low*100,maximum_mm=upper*100,width_mm=(upper-low)*100,contains_authentic_eye=True)


def constraints(vertices,triangles,xz_box,target_box,sigma,diagonal_sign):
 ts,cycle,shared=boundary(triangles);v={i:vec(vertices[i]) for i in cycle};targets=corners(target_box);rows=[]
 normals=[cross(sub(v[t[1]],v[t[0]]),sub(v[t[2]],v[t[0]])) for t in ts]
 if any(not any(n) for n in normals):raise ValueError('Degenerate real source')
 direction=tuple(-sigma*x for x in normals[0]);ends=list(product((xz_box[0][0],xz_box[1][0]),(xz_box[0][1],xz_box[1][1])))
 def add(label,fn):rows.append(affine_row(label,fn))
 for fi,t in enumerate(ts):
  a,b,c=[v[i] for i in t]
  for ti,target in enumerate(targets):add(dict(kind='target_face_plane',face=fi,target_corner=ti),lambda y,a=a,b=b,c=c,target=target: sigma*det(sub(a,target),sub(b,target),sub(c,target)))
 for ei,(x,z) in enumerate(ends):
  def eye(y):return (x,y,z)
  for fi,t in enumerate(ts):
   a,b,c=[v[i] for i in t]
   add(dict(kind='eye_face_plane',face=fi,xz_corner=ei),lambda y,a=a,b=b,c=c:-sigma*det(sub(a,eye(y)),sub(b,eye(y)),sub(c,eye(y))))
  for pi,point in enumerate(list(v.values())+list(targets)):
   add(dict(kind='positive_chart',point=pi,xz_corner=ei),lambda y,point=point:dot(direction,sub(point,eye(y))))
  a,b=[v[i] for i in shared]
  for fi,t in enumerate(ts):
   c=v[next(i for i in t if i not in shared)];sign=diagonal_sign if fi==0 else -diagonal_sign
   add(dict(kind='opposite_diagonal',face=fi,xz_corner=ei),lambda y,a=a,b=b,c=c,sign=sign:-sign*det(sub(a,eye(y)),sub(b,eye(y)),sub(c,eye(y))))
  for k,ia in enumerate(cycle):
   ib=cycle[(k+1)%4];a,b=v[ia],v[ib]
   for j in ((k+2)%4,(k+3)%4):
    c=v[cycle[j]]
    add(dict(kind='convex_boundary',edge=[ia,ib],other_vertex=cycle[j],xz_corner=ei),lambda y,a=a,b=b,c=c:-sigma*det(sub(a,eye(y)),sub(b,eye(y)),sub(c,eye(y))))
   for ti,target in enumerate(targets):
    add(dict(kind='outer_edge',edge=[ia,ib],xz_corner=ei,target_corner=ti),lambda y,a=a,b=b,target=target:-sigma*det(sub(a,eye(y)),sub(b,eye(y)),sub(target,eye(y))))
 return rows


def solve(vertices,triangles,xz_box,target_box,eye_y):
 branches=[]
 for sigma in (1,-1):
  for sign in (1,-1):
   rows=constraints(vertices,triangles,xz_box,target_box,sigma,sign);interval=intersect(rows);band=quantized_band(interval,eye_y)
   result=dict(sigma=sigma,diagonal_sign=sign,interval=interval,quantized_band=band,rows=rows)
   if band['representable']:
    box=((xz_box[0][0],Q(band['minimum_mm']),xz_box[0][1]),(xz_box[1][0],Q(band['maximum_mm']),xz_box[1][1]));proof=prove_union(vertices,triangles,box,target_box)
    if not proof['proven']:raise ValueError('Analytic band disagrees with unchanged exact_union')
    result['nominal_band_oracle']=proof;result['strict_minimum_at_band_endpoints']=min(row['a']*y+row['b'] for row in rows for y in (Q(band['minimum_mm']),Q(band['maximum_mm'])))
   branches.append(result)
 return branches
