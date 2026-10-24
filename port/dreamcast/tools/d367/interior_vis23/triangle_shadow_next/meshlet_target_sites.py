#!/usr/bin/env python3
"""Read-only exact-source target-query placement inventory; no runtime patch."""
import argparse,json,resource
from pathlib import Path
import feasibility as f
EXPECTED={'port/dreamcast/game/platform/native_static.cpp':'e23dda292ae37aff409bd66228c0a2edf80c27536ba477b9b9a51c1cc19113eb','port/dreamcast/game/platform/include/scenery_chunk_select.inc':'8460fc023840e87f52ab97eac3b9d8b7192a7d22070219f08f1631e593149cc9','port/dreamcast/game/platform/include/pvs23_runtime.inc':'09a05d430e31216570bcce9e7ef6a8c5fde929bd32f4c2b6979a25df967609a0','port/dreamcast/room/nonempty_lod.hpp':'75c7a9a591827257e81e0681ce3a5c1e6947ac9a2657d68deef37f828ad01061'}
NEEDLES={'port/dreamcast/game/platform/native_static.cpp':['const std::uint8_t* const pvs_cur=pvs::can_cut(i)?pvs::cur:nullptr;','const unsigned pvs_source_placement=(RE4DC_PS2_AFFINE==pl.affine)?i:~0U;','level=re4dc::room::nonempty_lod(levels+cl.first_level,cl.level_count,level);','const auto& lv=levels[cl.first_level+level];','const int result=draw(lets[i]','d.pvs_set=pvs_cur;','if(chunk_flush()<0)return -1;','int emit_pick(const Pick& pk)','struct Pick {','unsigned placement;'], 'port/dreamcast/game/platform/include/scenery_chunk_select.inc':['&& !pvs_set','level=re4dc::room::nonempty_lod(levels+cl.first_level,cl.level_count,level);','const unsigned li=lv.first_meshlet+i;','pk.let=std::uint16_t(li);'],'port/dreamcast/game/platform/include/pvs23_runtime.inc':['if(cl.level_count!=1U)','bool pvs::can_cut(unsigned placement)','placement<=cert->max_placement','receipts.complete(cert->npanels)'],'port/dreamcast/room/nonempty_lod.hpp':['while(selected && !levels[selected].meshlet_count)--selected;']}

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--source-tree',type=Path,required=True);ap.add_argument('--profile',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
 if a.out.exists():raise ValueError('Preserve prior inventory')
 resource.setrlimit(resource.RLIMIT_AS,(f.LIMIT,f.LIMIT));source=f.audit.bind_source(a.source_tree,a.profile);files={}
 for rel,digest in EXPECTED.items():
  p=a.source_tree/rel
  if f.digest(p)!=digest:raise ValueError('Unreviewed core source '+rel)
  lines=p.read_text().splitlines();found={}
  for needle in NEEDLES[rel]:
   hits=[dict(line=i+1,text=line.strip()) for i,line in enumerate(lines) if needle in line]
   if not hits:raise ValueError('Query-site anchor missing '+needle)
   found[needle]=hits
  files[rel]=dict(identity=f.identity(p),anchors=found)
 out=dict(kind='Read-only selected-meshlet query design inventory, no proposal applied',tool=f.identity(Path(__file__)),source=source,files=files,selected_target_affine_knob_present='RE4DC_PS2_PVS_SELECTED_TARGETS' in (a.source_tree/'port/dreamcast/game/platform/native_static.cpp').read_text(),runtime_admitted_cuts=0,modelled_ms=None,limits=dict(address_space_bytes=f.LIMIT,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,jobs=1))
 with a.out.open('x') as dst:json.dump(out,dst,indent=1);dst.write('\n')
 print(json.dumps(dict(files=len(files),selected_target_affine_knob_present=out['selected_target_affine_knob_present'],source=source['owned_head'],limits=out['limits'])))
if __name__=='__main__':main()
