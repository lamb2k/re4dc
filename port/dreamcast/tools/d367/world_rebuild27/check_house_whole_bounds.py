#!/usr/bin/env python3
"""Read actual arena R4IM/R4SG via MeshPackage and check spatial containment.

Host/source only. No asset writes, SDK, guests, rendering, or timing claims.
MeshLevel has no independent box: level vertices must fit their owning cluster.
The pinned A control has seven fused-decode exceptions. Require exact bitwise
exception-witness equality in B/C; report this separately from strict f32/grid
containment. No numeric allowance or universal fused-containment claim.
"""
import argparse,hashlib,json,resource,subprocess
from pathlib import Path

CPP=r'''
#include "instanced_mesh.hpp"
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <iterator>
#include <map>
#include <sstream>
#include <string>
#include <vector>
using namespace re4dc::room;
std::vector<unsigned char> read(const char* p){std::ifstream f(p,std::ios::binary);return {(std::istreambuf_iterator<char>(f)),{}};}
unsigned crc32(const unsigned char* p,unsigned n){unsigned c=~0U;while(n--){c^=*p++;for(unsigned k=0;k<8;++k)c=(c>>1)^((0U-(c&1U))&0xedb88320U);}return ~c;}
unsigned word(const unsigned char* p){unsigned x;std::memcpy(&x,p,4);return x;}
unsigned half(const unsigned char* p){unsigned short x;std::memcpy(&x,p,2);return x;}
struct Report{unsigned errors=0,meshlet_inputs=0,level_inputs=0,sg_inputs=0,sg_groups=0,meshlets=0,levels=0,clusters=0,unused_vertices=0,double_mesh_excesses=0;bool adopted=false;double max_mesh_excess=0,max_double_excess_ulps=0;std::vector<std::string> first,fma_witnesses;std::map<std::string,unsigned> categories;
 void fail(const std::string& s){++errors;++categories[s.substr(0,s.find(' '))];if(first.size()<32)first.push_back(s);}};
std::string location(const char* kind,unsigned part,unsigned let,unsigned axis,double value,double lo,double hi){std::ostringstream s;s<<kind<<" part="<<part<<" let="<<let<<" axis="<<axis<<" value="<<value<<" box="<<lo<<","<<hi;return s.str();}
Report check(const std::vector<unsigned char>& data,const std::vector<unsigned char>& sg){
 Report r;MeshPackage p;if(!p.adopt(data.data(),unsigned(data.size()),true,true)){r.fail("MeshPackage_adopt");return r;}
 r.adopted=true;const auto& h=p.header();if(crc32(data.data()+80,unsigned(data.size()-80))!=h.crc)r.fail("mesh_body_crc");
 std::vector<int> part_mesh(h.part_count,-1),let_part(h.meshlet_count,-1),let_level(h.meshlet_count,0);std::vector<bool> used(h.vertex_count,false);
 for(unsigned m=0;m<h.mesh_count;++m){const auto& mesh=p.meshes()[m];for(unsigned a=0;a<3;++a)if(!std::isfinite(mesh.origin[a])||!std::isfinite(mesh.step[a])||!std::isfinite(mesh.bounds_min[a])||!std::isfinite(mesh.bounds_max[a])||mesh.bounds_min[a]>mesh.bounds_max[a])r.fail("mesh_nonfinite_or_inverted");for(unsigned pi=mesh.first_part;pi<mesh.first_part+mesh.part_count;++pi){if(part_mesh[pi]>=0)r.fail("part_multiple_mesh_owners");part_mesh[pi]=int(m);}}
 auto vi=[&](unsigned li,unsigned k){const auto& l=p.meshlets()[li];return l.first_vertex+(p.indexed(l)?p.pool_offsets(l)[k]:k);};
 auto q=[&](unsigned li,unsigned k,unsigned a){const auto& v=p.vertices()[vi(li,k)];return a==0?unsigned(v.x):a==1?unsigned(v.y):unsigned(v.z);};
 for(unsigned pi=0;pi<h.part_count;++pi){const auto& part=p.parts()[pi];if(part.meshlet_count&&part_mesh[pi]<0){r.fail("nonempty_part_no_mesh");continue;}for(unsigned li=part.first_meshlet;li<part.first_meshlet+part.meshlet_count;++li){if(let_part[li]>=0)r.fail("meshlet_multiple_part_owners");let_part[li]=int(pi);const auto& l=p.meshlets()[li];const auto& mesh=p.meshes()[part_mesh[pi]];++r.meshlets;
   for(unsigned k=0;k<l.vertex_count;++k){++r.meshlet_inputs;used[vi(li,k)]=true;for(unsigned a=0;a<3;++a){const unsigned v=q(li,k,a);if(v<l.bounds_min[a]||v>l.bounds_max[a])r.fail(location("meshlet",pi,li,a,v,l.bounds_min[a],l.bounds_max[a]));const double decoded=double(mesh.origin[a])+double(v)*double(mesh.step[a]);const double excess=std::max(double(mesh.bounds_min[a])-decoded,decoded-double(mesh.bounds_max[a]));r.max_mesh_excess=std::max(r.max_mesh_excess,excess);if(excess>0){++r.double_mesh_excesses;const float edge=decoded<double(mesh.bounds_min[a])?mesh.bounds_min[a]:mesh.bounds_max[a];double ulp=std::abs(double(std::nextafter(edge,decoded<double(edge)?-INFINITY:INFINITY))-double(edge));if(ulp>0)r.max_double_excess_ulps=std::max(r.max_double_excess_ulps,excess/ulp);}
    const float product=float(v)*mesh.step[a];const float runtime=mesh.origin[a]+product;const float fused=std::fma(float(v),mesh.step[a],mesh.origin[a]);if(runtime<mesh.bounds_min[a]||runtime>mesh.bounds_max[a])r.fail(location("mesh_f32",pi,li,a,runtime,mesh.bounds_min[a],mesh.bounds_max[a]));if(fused<mesh.bounds_min[a]||fused>mesh.bounds_max[a]){std::ostringstream s;s<<pi<<":"<<a<<":"<<v<<":"<<word(reinterpret_cast<const unsigned char*>(&mesh.origin[a]))<<":"<<word(reinterpret_cast<const unsigned char*>(&mesh.step[a]))<<":"<<word(reinterpret_cast<const unsigned char*>(&mesh.bounds_min[a]))<<":"<<word(reinterpret_cast<const unsigned char*>(&mesh.bounds_max[a]))<<":"<<word(reinterpret_cast<const unsigned char*>(&fused));r.fma_witnesses.push_back(s.str());}}}
  }
  if(p.lod()){const auto& pl=p.part_lods()[pi];for(unsigned ci=pl.first_cluster;ci<pl.first_cluster+pl.cluster_count;++ci){const auto& c=p.clusters()[ci];++r.clusters;for(unsigned lv=c.first_level;lv<c.first_level+c.level_count;++lv){const auto& level=p.levels()[lv];++r.levels;for(unsigned li=level.first_meshlet;li<level.first_meshlet+level.meshlet_count;++li){++let_level[li];if(let_part[li]!=int(pi))r.fail("level_foreign_part");for(unsigned k=0;k<p.meshlets()[li].vertex_count;++k){++r.level_inputs;for(unsigned a=0;a<3;++a){unsigned v=q(li,k,a);if(v<c.bounds_min[a]||v>c.bounds_max[a])r.fail(location("cluster_level",pi,li,a,v,c.bounds_min[a],c.bounds_max[a]));}}}}}}
 }
 for(unsigned li=0;li<h.meshlet_count;++li){if(let_part[li]<0)r.fail("orphan_meshlet");if(p.lod()&&!let_level[li])r.fail("meshlet_not_in_any_level");}for(bool v:used)if(!v)++r.unused_vertices;
 if(sg.size()<32||std::memcmp(sg.data(),"R4SG",4)||word(sg.data()+4)!=1||word(sg.data()+8)!=h.meshlet_count||word(sg.data()+16)!=h.crc||word(sg.data()+20)!=h.bytes){r.fail("SG_header_identity");return r;}
 unsigned groups=word(sg.data()+12);if(!groups||groups>8||sg.size()!=32U+16U*groups*h.meshlet_count||crc32(sg.data()+32,unsigned(sg.size()-32))!=word(sg.data()+28)){r.fail("SG_size_or_crc");return r;}
 for(unsigned li=0;li<h.meshlet_count;++li){const auto& l=p.meshlets()[li];unsigned prev=0;const auto* bytes=p.strip_begin(l);for(unsigned g=0;g<groups;++g){const auto* row=sg.data()+32+16U*(li*groups+g);const unsigned end=half(row+12);if(end<prev||end>l.strip_bytes){r.fail("SG_strip_end_range");continue;}if(end==prev)continue;++r.sg_groups;unsigned at=prev;while(at<end){unsigned n=bytes[at++];if(n<3||n>end-at){r.fail("SG_boundary_splits_strip");break;}for(unsigned k=0;k<n;++k){unsigned index=bytes[at+k];++r.sg_inputs;if(index<row[14]||index>row[15])r.fail("SG_transform_index_range");for(unsigned a=0;a<3;++a){unsigned v=q(li,index,a),lo=half(row+2*a),hi=half(row+6+2*a);if(v<lo||v>hi)r.fail(location("strip_group",unsigned(let_part[li]),li,a,v,lo,hi));}}at+=n;}if(at!=end)r.fail("SG_group_end_not_strip_boundary");prev=end;}if(prev!=l.strip_bytes)r.fail("SG_omits_strip_tail");}
 return r;
}
bool shrink(std::vector<unsigned char>& data,std::vector<unsigned char>& sg,const std::string& which){MeshPackage p;if(!p.adopt(data.data(),unsigned(data.size()),true,true))return false;const auto& h=p.header();
 if(which=="meshlet"){for(unsigned li=0;li<h.meshlet_count;++li){const auto& l=p.meshlets()[li];for(unsigned a=0;a<3;++a)if(l.bounds_max[a]>l.bounds_min[a]){unsigned short v=l.bounds_min[a];std::memcpy(data.data()+h.meshlet_offset+sizeof(Meshlet)*li+offsetof(Meshlet,bounds_max)+2*a,&v,2);goto done;}}}
 if(which=="cluster"){MeshLodHeader lod;std::memcpy(&lod,data.data()+80,sizeof lod);for(unsigned ci=0;ci<lod.cluster_count;++ci){const auto& c=p.clusters()[ci];bool populated=false;for(unsigned lv=c.first_level;lv<c.first_level+c.level_count;++lv)populated|=p.levels()[lv].meshlet_count>0;if(!populated)continue;for(unsigned a=0;a<3;++a)if(c.bounds_max[a]>c.bounds_min[a]){unsigned short v=c.bounds_min[a];std::memcpy(data.data()+lod.cluster_offset+sizeof(MeshCluster)*ci+offsetof(MeshCluster,bounds_max)+2*a,&v,2);goto done;}}}
 if(which=="mesh"){for(unsigned mi=0;mi<h.mesh_count;++mi){const auto& m=p.meshes()[mi];bool populated=false;for(unsigned pi=m.first_part;pi<m.first_part+m.part_count;++pi)populated|=p.parts()[pi].meshlet_count>0;if(!populated)continue;for(unsigned a=0;a<3;++a)if(m.bounds_max[a]>m.bounds_min[a]){float v=m.bounds_min[a];std::memcpy(data.data()+h.mesh_offset+sizeof(MeshRecord)*mi+offsetof(MeshRecord,bounds_max)+4*a,&v,4);goto done;}}}
 if(which=="sg"){if(sg.size()<32)return false;for(unsigned at=32;at+16<=sg.size();at+=16)for(unsigned a=0;a<3;++a)if(half(sg.data()+at+6+2*a)>half(sg.data()+at+2*a)){unsigned short v=half(sg.data()+at+2*a);std::memcpy(sg.data()+at+6+2*a,&v,2);return true;}}
 return false;
 done:unsigned crc=crc32(data.data()+80,unsigned(data.size()-80));std::memcpy(data.data()+12,&crc,4);std::memcpy(sg.data()+16,&crc,4);return true;
}
int main(int argc,char** argv){if(argc<3||argc>4)return 2;auto data=read(argv[1]),sg=read(argv[2]);if(argc==4){if(!shrink(data,sg,argv[3]))return 3;if(std::string(argv[3])=="sg"){unsigned crc=crc32(sg.data()+32,unsigned(sg.size()-32));std::memcpy(sg.data()+28,&crc,4);}}
 auto r=check(data,sg);printf("{\"adopted\":%s,\"errors\":%u,\"meshlet_inputs\":%u,\"level_inputs\":%u,\"sg_inputs\":%u,\"sg_groups\":%u,\"meshlets\":%u,\"levels\":%u,\"clusters\":%u,\"unused_vertex_records\":%u,\"double_mesh_excesses\":%u,\"max_double_mesh_excess_mm\":%.12g,\"max_double_excess_ulps\":%.12g,\"categories\":{",r.adopted?"true":"false",r.errors,r.meshlet_inputs,r.level_inputs,r.sg_inputs,r.sg_groups,r.meshlets,r.levels,r.clusters,r.unused_vertices,r.double_mesh_excesses,r.max_mesh_excess,r.max_double_excess_ulps);unsigned ci=0;for(const auto& c:r.categories)printf("%s\"%s\":%u",ci++?",":"",c.first.c_str(),c.second);printf("},\"first_errors\":[");for(unsigned i=0;i<r.first.size();++i)printf("%s\"%s\"",i?",":"",r.first[i].c_str());printf("],\"fma_witnesses\":[");std::sort(r.fma_witnesses.begin(),r.fma_witnesses.end());for(unsigned i=0;i<r.fma_witnesses.size();++i)printf("%s\"%s\"",i?",":"",r.fma_witnesses[i].c_str());puts("]}");return r.errors?1:0;}
'''

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(c):return subprocess.run([str(x)for x in c],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
def main():
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--tree',type=Path,required=True);ap.add_argument('--asset-root',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    tree=a.tree.resolve();root=a.asset_root.resolve();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    tracked=sorted(p for p in root.rglob('*')if p.is_file())+[tree/'port/dreamcast/room/instanced_mesh.hpp',tree/'port/dreamcast/game/platform/native_static.cpp']
    snapshot={str(p):sha(p)for p in tracked}
    (out/'kos').mkdir();(out/'kos/fs.h').write_text('#pragma once\ntypedef int file_t;\n#define FILEHND_INVALID (-1)\n');cpp=out/'bounds.cpp';cpp.write_text(CPP);exe=out/'bounds'
    c=run(['g++','-std=c++17','-O2','-ffp-contract=off','-Wall','-Wextra','-Werror','-I'+str(out),'-I'+str(tree/'port/dreamcast/room'),cpp,'-o',exe]);(out/'compile.log').write_text(c.stdout);assert c.returncode==0,c.stdout
    result={'scope':'SOURCE/HOST spatial containment; actual MeshPackage reader; no SDK/guest/timing','mesh_level_has_no_independent_bounds':True,'strict_grid_bounds':True,'mesh_float_contract':'IEEE binary32 multiply-then-add must fit exactly; fused and binary64 diagnostic exceptions remain explicit. Fused exception witnesses in B/C must equal pinned A exactly, not fit a tolerance. Not a proof of universal real-arithmetic containment.','assets':{},'mutations':{},'reader_sha256':sha(tree/'port/dreamcast/room/instanced_mesh.hpp'),'helper_sha256':sha(Path(__file__))}
    for arm in range(3):
        mesh=root/f'native/r101/arena{arm}/ps2-world.re4mesh';sg=mesh.with_suffix('.r4sg');p=run([exe,mesh,sg]);(out/f'arm{arm}.log').write_text(p.stdout)
        result['assets'][str(arm)]={'pass':p.returncode==0,'mesh_sha256':sha(mesh),'sg_sha256':sha(sg),'checks':json.loads(p.stdout)}
    for kind in ('meshlet','cluster','mesh','sg'):
        mesh=root/'native/r101/arena0/ps2-world.re4mesh';p=run([exe,mesh,mesh.with_suffix('.r4sg'),kind]);(out/(kind+'-mutation.log')).write_text(p.stdout)
        checks=json.loads(p.stdout)if p.stdout.startswith('{')else {};category={'meshlet':'meshlet','cluster':'cluster_level','mesh':'mesh_f32','sg':'strip_group'}[kind];before=result['assets']['0']['checks']['categories'].get(category,0);after=checks.get('categories',{}).get(category,0)
        result['mutations'][kind]={'refused':p.returncode==1 and checks.get('adopted')is True and after>before,'new_category':category,'baseline_category_errors':before,'mutation_category_errors':after,'checks':checks}
    a_sha='29709f39ee8eae376c8f1bf68f70d8eb5656b8555ccfa14f7783b63888feafb8'
    witness=result['assets']['0']['checks']['fma_witnesses'];result['inherited_fused_contract']={'pinned_A_sha256':a_sha,'actual_A_matches':result['assets']['0']['mesh_sha256']==a_sha,'A_exception_count':len(witness),'B_C_exact_A_witness_match':all(v['checks']['fma_witnesses']==witness for v in result['assets'].values()),'strict_fused_containment':not witness}
    result['input_readback']={'sha256':snapshot,'unchanged':all(sha(Path(p))==h for p,h in snapshot.items())}
    result['source_head']=run(['git','-C',tree,'rev-parse','HEAD']).stdout.strip()
    result['pass']=all(v['pass']for v in result['assets'].values())and all(v['refused']for v in result['mutations'].values())and result['inherited_fused_contract']['actual_A_matches']and result['inherited_fused_contract']['B_C_exact_A_witness_match']and result['input_readback']['unchanged']
    (out/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return 0 if result['pass']else 1
if __name__=='__main__':raise SystemExit(main())
