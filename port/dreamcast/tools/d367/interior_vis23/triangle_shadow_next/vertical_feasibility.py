#!/usr/bin/env python3
"""Fixed hut647 nominal analytic Y-domain design, no data or runtime change."""
import argparse,json,resource
from pathlib import Path
from fractions import Fraction as Q
import feasibility as f
from smaller_domains import eye_from_bits
from vertical_domain import solve

PAIR_REPORT='dbda668aa4cd20f4bea43b742f742de2c8ef59f49c28e1f86836e0a741bb92d6'

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--source-tree',required=True,type=Path);ap.add_argument('--pair-report',required=True,type=Path);ap.add_argument('--out',required=True,type=Path);a=ap.parse_args()
 if a.out.exists():raise ValueError('Preserve old analysis')
 resource.setrlimit(resource.RLIMIT_AS,(f.LIMIT,f.LIMIT))
 if f.digest(a.pair_report)!=PAIR_REPORT:raise ValueError('Frozen same-pair/domain binding changed')
 d=json.loads(a.pair_report.read_text());source=f.audit.bind_source(a.source_tree,Path(d['source']['profile']['path']))
 for pin in d['inputs'].values():
  if f.digest(Path(pin['path']))!=pin['sha256']:raise ValueError('Source geometry/physical affine/ID input changed')
 for pin in d['material_pins'].values():
  if isinstance(pin,dict) and 'path' in pin and f.digest(Path(pin['path']))!=pin['sha256']:raise ValueError('Material prerequisite source changed')
 if f.digest(Path(__file__).with_name('exact_union.py'))!='b891139899814a5dc840d17982cbbc5147318d70e27ac91dfadd4928789880f8':raise ValueError('Reviewed union oracle changed')
 v={int(i):tuple(map(Q,p)) for i,p in d['source_geometry']['positions'].items()};ts=tuple(tuple(t) for t in d['source_geometry']['actual_parity_triangles']);target=tuple(tuple(map(Q,p)) for p in d['target']['box'])
 if ts!=((14,13,12),(13,14,15)):raise ValueError('Only approved actual pair')
 rows=[]
 for sized in d['results']:
  old=next(r for r in sized['per_camera'] if r['label']=='hut' and r['frame']==647);eye=eye_from_bits(old['view_bits']);box=tuple(tuple(map(Q,p)) for p in old['box_exact']);xz=((box[0][0],box[0][2]),(box[1][0],box[1][2]));branches=solve(v,ts,xz,target,eye[1])
  rows.append(dict(size_mm=sized['size_mm'],original_full_box=old['box_exact'],original_full_box_result=old['outcomes']['exact_union']['nominal'],fixed_xz_exact=xz,authentic_eye_exact=eye,branches=branches,selector_preimage_or_true_eye_error_certified=False,runtime_admitted=False))
 refs={}
 for rel,needles in {
 'port/dreamcast/game/platform/native_static.cpp':['struct Cell { std::uint16_t set; std::int16_t ylo,yhi,pad; };','cell.ylo>cell.yhi','cur_frame=f;cur=nullptr;cur_cell=-1;++frames;','eye[1]<float(e.ylo)*100.0f || eye[1]>float(e.yhi)*100.0f','if(!cur || !base || i>=ps2w.nplacements || !can_cut(i))return false;'],
 'port/dreamcast/tools/d367/ps2world/pvs/pvs_emit.py':['i16 ylo, yhi (decimetres)',"lo = int(np.floor((C['ylo'][c] - 1000) / 100))"]}.items():
  p=a.source_tree/rel;lines=p.read_text().splitlines();anchors=[]
  for needle in needles:
   hits=[dict(line=i+1,text=line) for i,line in enumerate(lines) if needle in line]
   if len(hits)!=1:raise ValueError('Read-only format/selector source anchor changed '+needle)
   anchors+=hits
  refs[rel]=dict(identity=f.identity(p),anchors=anchors)
 out=dict(kind='Same pair/target, fixed hut647 XZ nominal analytic vertical-domain DESIGN ONLY',tool=f.identity(Path(__file__)),dependencies={n:f.identity(Path(__file__).with_name(n)) for n in ('vertical_domain.py','exact_union.py','exact_shadow.py')},source=source,preserved_full_height_pair_report=f.identity(a.pair_report),readonly_format_selector_sources=refs,derivation='Every determinant is affine in eye Y at fixed XZ/source/target endpoints. Strict a*Y+b>0 halfspaces are intersected exactly for both global orientation and diagonal branches. XZ/source/target product corners enclose every nominal continuous box; no repeated height samples.',quantization='Closed integer100mm endpoints must lie strictly inside the analytic open interval, fit signed int16, have positive width and contain the exact recorded eye.',rows=rows,runtime_admitted_cuts=0,modelled_ms=None,go_1ms=False,limits=dict(address_space_bytes=f.LIMIT,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,jobs=1),limitations=['Nominal exact-real domain design only. No requested32mm geometry, actual true-eye/SH4 inverse/grid-selector uncertainty, cull/near/clip/cache/kernel/raster/depth/material/prefix receipt qualification.','Current selector admits inclusive signed100mm Y endpoints and clears current set outside; this source property does not certify actual float-eye preimage.','All signed int16*100 integer products fit below2^24 and are exactly representable as float; actual eye_of remains unbounded here.','The existing generic emitter expands authored Y by1000mm each side and outward-rounds; an in-format narrow band is not automatically an output of its unchanged CLI. No emitter/converter edit.','No new PVS/data/table/renderer/runtime/SDK/guest/asset/recipe/target partition or allocation. Full-height zero receipts remain immutable.'])
 with a.out.open('x') as dst:json.dump(out,dst,indent=1,default=lambda x:str(x) if isinstance(x,Q) else (_ for _ in ()).throw(TypeError(type(x))));dst.write('\n')
 for row in rows:
  print(json.dumps(dict(size=row['size_mm'],branches=[dict(sigma=b['sigma'],diagonal_sign=b['diagonal_sign'],nonempty=b['interval']['nonempty'],lower=str(b['interval']['lower']),upper=str(b['interval']['upper']),quantized_band=b['quantized_band']) for b in row['branches']]),default=str))
 print(json.dumps(dict(limits=out['limits'],runtime_admitted=0,modelled_ms=None)))

if __name__=='__main__':main()
