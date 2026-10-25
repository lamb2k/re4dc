#!/usr/bin/env python3
"""Exact full-domain edge refusal diagnostics for the existing hut647 case only.

Full-height boxes remain intact. A separate root-authorized point-eye diagnostic
uses the same whole target box and cannot admit a table or continuous cell.
"""
import argparse,json,resource
from pathlib import Path
from fractions import Fraction as Q
import feasibility as f
from exact_shadow import corners,sub,det,cross,dot
from exact_patch import prove_patch
from smaller_domains import eye_from_bits

def closed_ray_hit(eye,target,triangle):
 a,b,c=triangle;n=cross(sub(b,a),sub(c,a));se=dot(n,sub(eye,a));st=dot(n,sub(target,a));den=se-st
 if not den or not(se*st<0):return None
 fraction=se/den
 if not 0<fraction<1:return None
 point=tuple(eye[k]+fraction*(target[k]-eye[k]) for k in range(3))
 if all(dot(n,cross(sub(y,x),sub(point,x)))>=0 for x,y in ((a,b),(b,c),(c,a))):return dict(ray_fraction=str(fraction),point_exact=[str(x) for x in point])
 return None


def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--report',required=True,type=Path);ap.add_argument('--out',required=True,type=Path);a=ap.parse_args()
 if a.out.exists():raise ValueError('Preserve prior report')
 resource.setrlimit(resource.RLIMIT_AS,(f.LIMIT,f.LIMIT))
 if f.digest(a.report)!='7715fe03a89fd5d7e03b716065a57583bc061b66e549ca0b9059d2ae8906c181':raise ValueError('Frozen actual report changed')
 d=json.loads(a.report.read_text())
 if d['tool']['sha256']!='9b81928484efff845536ce75862b2bb78a9370a8de01158b2756cfe8c585518d':raise ValueError('Unreviewed actual runner result')
 v={int(i):tuple(map(Q,p)) for i,p in d['source_geometry']['positions'].items()};cycle=d['source_geometry']['topology']['boundary'];tri=d['source_geometry']['actual_parity_triangles'][0];target=tuple(tuple(map(Q,p)) for p in d['target']['box']);ts=corners(target);rows=[]
 for sized in d['results']:
  row=next(x for x in sized['per_camera'] if x['label']=='hut' and x['frame']==647);box=tuple(tuple(map(Q,p)) for p in row['box_exact']);es=corners(box);eye=eye_from_bits(row['view_bits']);a0,b0,c0=[v[i] for i in tri];value=-det(sub(a0,es[0]),sub(b0,es[0]),sub(c0,es[0]));sigma=1 if value>0 else -1;edges=[]
  for k,ia in enumerate(cycle):
   ib=cycle[(k+1)%len(cycle)];a0,b0=v[ia],v[ib];values=[(sigma*-det(sub(a0,e),sub(b0,e),sub(t,e)),ei,ti) for ei,e in enumerate(es) for ti,t in enumerate(ts)];lo,ei,ti=min(values);hi=max(x[0] for x in values)
   point_values=[sigma*-det(sub(a0,eye),sub(b0,eye),sub(t,eye)) for t in ts]
   edges.append(dict(point_eye_target_box_minimum=str(min(point_values)),point_eye_target_box_maximum=str(max(point_values)),point_eye_nonpositive_target_corners=sum(x<=0 for x in point_values),edge=[ia,ib],minimum=str(lo),maximum=str(hi),nonpositive_corner_pairs=sum(x[0]<=0 for x in values),corner_pairs=len(values),minimum_eye_corner=ei,minimum_target_corner=ti,eye_at_minimum=[str(x) for x in es[ei]],target_at_minimum=[str(x) for x in ts[ti]],strict_positive=lo>0))
  point_proof=prove_patch(v,d['source_geometry']['actual_parity_triangles'],(eye,eye),target,boundary_mode='boundary_kernel')
  corner_rays=[]
  for ti,t in enumerate(ts):
   hits=[]
   for fi,face in enumerate(d['source_geometry']['actual_parity_triangles']):
    hit=closed_ray_hit(eye,t,[v[i] for i in face])
    if hit:hits.append(dict(face=fi,**hit))
   corner_rays.append(dict(target_corner=ti,hits=hits))
  rows.append(dict(point_eye_exact=[str(x) for x in eye],point_eye_whole_target_box_kernel=point_proof,point_eye_corner_rays=corner_rays,corner_rays_are_not_continuous_box_proof=True,size_mm=sized['size_mm'],eye_box=row['box_exact'],strict=row['outcomes']['strict_convex']['nominal'],kernel=row['outcomes']['boundary_kernel']['nominal'],all_boundary_edges=edges))
 out=dict(kind='Fixed hut647 full-domain exact boundary refusal diagnostics only',tool=f.identity(Path(__file__)),input=f.identity(a.report),rows=rows,runtime_admitted_cuts=0,modelled_ms=None,scope='All 8x8 eye/target corners per directed edge, original full Y unchanged; separate point-eye diagnostic is not a cell/selector or runtime proof. Corner ray hits are not continuous box coverage. Negative sufficient-test margin is not proof of visibility or global exclusion.')
 with a.out.open('x') as dst:json.dump(out,dst,indent=1);dst.write('\n')
 print(json.dumps(out))

if __name__=='__main__':main()
