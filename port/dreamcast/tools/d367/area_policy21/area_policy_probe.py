#!/usr/bin/env python3
"""Execute extracted AREA source against retained metadata; never stages assets."""
import argparse,hashlib,json,pathlib,re,struct,subprocess,zlib
A=argparse.ArgumentParser();A.add_argument('--source',type=pathlib.Path,required=True);A.add_argument('--original-world',type=pathlib.Path,required=True);A.add_argument('--ids',type=pathlib.Path,required=True);A.add_argument('--candidate-world',type=pathlib.Path,required=True);A.add_argument('--world-proposals',type=pathlib.Path,required=True);A.add_argument('--certificate-rows',type=pathlib.Path,required=True);A.add_argument('--output',type=pathlib.Path,required=True);a=A.parse_args();a.output.mkdir(exist_ok=False)
sha=lambda b:hashlib.sha256(b).hexdigest();PIN='0425534d848973c1dae3ab960d0006ac9afcf363';repo=a.source.parents[4];parent=subprocess.check_output(['git','show',PIN+':port/dreamcast/game/platform/native_static.cpp'],cwd=repo).decode();candidate=a.source.read_text()
# Reducing exactly the two added guard regions restores the complete parent file.
pat=r'#if RE4DC_WORLD_RECT21\n(?P<on>(?:        // The retained r107|    area::open).*?)#else\n(?P<off>.*?)#endif'
off,count=re.subn(pat,lambda m:m.group('off').rstrip('\n'),candidate,flags=re.S);assert count==2 and off==parent,'OFF whole source is not exact'
original=a.original_world.read_bytes();ids=a.ids.read_bytes();world=a.candidate_world.read_bytes();w=next(w for w in json.loads(a.world_proposals.read_text())['worlds']if w['room']=='r107');h=struct.unpack_from('<4s7I',original)
assert sha(original)==w['source_original_sha256']=='0b17e5f48c0cbea6fdf63ee6247296c7f27d0493fb53db80aa7b6600a87016f0'and sha(world)==w['candidate_sha256'];assert h[5]==zlib.crc32(original[32:])&0xffffffff==0x43dc8ff9
assert sha(ids)=='198f37d2c16acacca5536bed541b5fd0696a5b0bf7d5c969a7042424e4a91857';assert struct.unpack_from('<4s3I',ids)==(b'R4ID',1,71,h[5]);assert len(ids)==96 and h[2]==71 and original[32+16*h[3]:]==world[32+16*h[3]:]
placements=[struct.unpack_from('<2H12f',original,32+16*h[3]+52*i)for i in range(71)];assert all(p[1]==i for i,p in enumerate(placements));groupids=list(ids[16:87]);assert len(groupids)==71
helper_path=repo/'port/dreamcast/tools/d367/texture_rect21/world_rect_provenance.h';helper=helper_path.read_text();fixture,n=re.subn(r'(static_assert\(sizeof\(certificates\)/sizeof\(certificates\[0\]\)==)3U',r'\g<1>29U',helper);assert n==1;cert=a.certificate_rows.read_text();assert sum(l.lstrip().startswith('{')for l in cert.splitlines())==29;(a.output/'provenance_fixture.h').write_text(fixture);(a.output/'provenance_certificates.inc').write_text(cert)
def between(s,lo,hi):return s[s.index(lo):s.index(hi,s.index(lo))]
def function(s,mark):
 start=s.index(mark);i=s.index('{',start);level=1;j=i+1
 while level:
  level+=(s[j]=='{')-(s[j]=='}');j+=1
 return s[start:j]
recorddefs='\n'.join(re.search(r'struct '+n+r' \{[^\n]+',candidate).group(0)for n in ['Ps2Part','Ps2Placement','Ps2Head'])
pre='''#include <cstdint>\n#include <cstring>\n#include <cassert>\n#include <cstdio>\n#include <fstream>\n#include <vector>\n#include "provenance_fixture.h"\nextern "C" void re4dc_log(const char*,...){}\n'''
body=r'''
struct MeshHeader {unsigned crc,bytes,part_count,mesh_count;};
struct FakePackage { MeshHeader h;const MeshHeader& header()const{return h;} };
struct FakeWorld {unsigned room;FakePackage package;} ps2w;
unsigned cases;
void check(bool x){++cases;if(!x){std::fprintf(stderr,"case %u failed\n",cases);std::abort();}}
std::vector<unsigned char> load(const char* p){std::ifstream f(p,std::ios::binary);return {std::istreambuf_iterator<char>(f),{}};}
unsigned readword(const std::vector<unsigned char>& v,unsigned n){return re4dc::rect21::provenance::word(v.data()+n);}
void putword(std::vector<unsigned char>&v,unsigned n,unsigned w){for(unsigned k=0;k<4;++k)v[n+k]=w>>(8*k);}
bool actual_open(const std::vector<unsigned char>& b,unsigned room=0x107,unsigned meshcrc=MESHCRC,unsigned meshbytes=MESHBYTES,unsigned parts=PARTS,unsigned meshes=MESHES){
 auto before=b;area::cur=nullptr;if(b.size()<sizeof(Ps2Head))return false;
 ps2w={room,{{meshcrc,meshbytes,parts,meshes}}};const unsigned char* s=b.data();const unsigned mbytes=0,psize=b.size();Ps2Head h;std::memcpy(&h,s,sizeof(h));const auto&mh=ps2w.package.header();const unsigned body=psize-sizeof(h);const char*why=nullptr;bool ok=true;
 PHYSICAL
 if(!ok)return false;
 POLICY
 CALL
 check(b==before);return area::cur!=nullptr;
}
void masks(const std::vector<unsigned char>& id){
 for(unsigned f: {0U,1U,2U,3U,4U,~0U}){
  area::flags_room=0x107;area::flags=f;area::state=~0U;area::update();unsigned state=(f&2)?2:(f&1)?1:0;
  for(unsigned p=0;p<71;++p){unsigned g=id[16+p];bool visible=true;
   if(g==50||g==60||g==70||g==80||g==90||g==100)visible=state==0?(g==50||g==60):state==1?(g==90||g==100):(g==60||g==70||g==80||g==90);
   check(area::hide(p)==!visible);
  }
  check(!area::hide(96));check(!area::hide(~0U));
 }
}
int main(int argc,char**argv){
 check(argc==4);auto original=load(argv[1]),id=load(argv[2]),candidate=load(argv[3]);check(id.size()==96);
 // Direct legacy profile exercises source masks without forging a physical file.
 area::open(0x107,0x9081e7fdU,71);check(area::cur);masks(id);
 for(unsigned n:{0U,70U,72U,~0U}){area::open(0x107,0x9081e7fdU,n);check(!area::cur);}
 for(unsigned room:{0U,0x106U,0x108U}){area::open(room,0x9081e7fdU,71);check(!area::cur);}
 check(actual_open(original)==EXPECTED);if(EXPECTED)masks(id);check(actual_open(candidate)==EXPECTED);if(EXPECTED)masks(id);
 auto b=candidate;b[32]^=1;check(!actual_open(b));putword(b,20,ps2_crc32(b.data()+32,b.size()-32));check(!actual_open(b));
 b=candidate;b[20]^=1;check(!actual_open(b));b=candidate;b[24]^=1;check(!actual_open(b));b=candidate;b[8]^=1;check(!actual_open(b));b=candidate;b.pop_back();check(!actual_open(b));b=candidate;b.push_back(0);check(!actual_open(b));
 check(!actual_open(candidate,0x106));check(!actual_open(candidate,0x107,MESHCRC^1));check(!actual_open(candidate,0x107,MESHCRC,MESHBYTES+32));check(!actual_open(candidate,0x107,MESHCRC,MESHBYTES,PARTS+1));check(!actual_open(candidate,0x107,MESHCRC,MESHBYTES,PARTS,MESHES+1));
 area::open(0x107,0x12345678U,71);check(!area::cur);area::flags_room=0x107;area::update();for(unsigned i=0;i<96;++i)check(!area::hide(i));
 std::printf("PASS %u checks\n",cases);
}
'''
physical=function(candidate,'std::uint32_t ps2_crc32(')
pred=between(candidate,'        if(std::memcmp(h.magic,"R4PW",4)','    }\n    if(ok){').strip();assert pred.endswith('{why="sidecar";ok=false;}')
policy=between(candidate,'    const std::uint32_t policySourceCrc=','#if RE4DC_PS2_AREA_HIDE')
reports=[];pp={}
for kind,src,guard in [('parent',parent,'0'),('parent',parent,'1'),('candidate',candidate,None),('candidate',candidate,'0'),('candidate',candidate,'1')]:
 name=kind+'-'+('default'if guard is None else guard);on=kind=='candidate'and guard=='1';area=between(src,'namespace area {','extern "C" void re4dc_ps2_area_flags').rstrip();start=src.index('    const std::uint32_t policySourceCrc=');call=src[src.index('#if RE4DC_PS2_AREA_HIDE',start):src.index('#if RE4DC_PS2_WORLD_R11F_OWNER',start)]
 text=pre+recorddefs+'\n'+physical+'\n'+area+'\n'+body.replace('PHYSICAL',pred).replace('POLICY',policy).replace('CALL',call).replace('EXPECTED','true'if on else'false').replace('MESHCRC',str(w['mesh_crc'])+'U').replace('MESHBYTES',str(w['mesh_bytes'])+'U').replace('PARTS',str(w['parts'])+'U').replace('MESHES',str(w['meshes'])+'U')
 source=a.output/(name+'.cpp');source.write_text(text);exe=a.output/(name+'.exe');cmd=['g++','-std=c++17','-Os','-s','-fsanitize=undefined','-fno-sanitize-recover=all','-DRE4DC_PS2_WORLD_ROOMS=1','-DRE4DC_PS2_AREA_HIDE=1']+([]if guard is None else['-DRE4DC_WORLD_RECT21='+guard]);subprocess.run(cmd+[str(source),'-o',str(exe)],check=True,capture_output=True)
 r=subprocess.run([str(exe),str(a.original_world),str(a.ids),str(a.candidate_world)],check=True,capture_output=True,text=True);assert not r.stderr
 preprocessed=subprocess.check_output(cmd[:1]+['-std=c++17','-E','-P']+cmd[6:]+[str(source)],text=True);pp[name]=preprocessed
 (a.output/(name+'.stdout')).write_text(r.stdout);reports.append(dict(name=name,command=cmd+[str(source),'-o',str(exe)],executable_sha256=sha(exe.read_bytes()),source_sha256=sha(source.read_bytes()),stdout=r.stdout.strip()))
# EXPECTED and helper/caller are identical in the two OFF arms, so actual host preprocessing is byte-identical.
assert pp['candidate-default']==pp['parent-0']==pp['candidate-0'];(a.output/'off-preprocessed-sha.txt').write_text(sha(pp['candidate-0'].encode())+'\n')
result=dict(status='PASS_ACTUAL_EXTRACTED_SOURCE_HOST_ONLY',source_path=str(a.source),source_sha256=sha(candidate.encode()),parent_pin=PIN,parent_source_sha256=sha(parent.encode()),whole_OFF_source_exact=True,actual_host_OFF_preprocessing_exact=True,fixture_helper_original_sha256=sha(helper.encode()),fixture_helper_sha256=sha(fixture.encode()),fixture_count_change='Test-only static count3to29; function bodies exact. Runtime header/table untouched.',proposed_certificate_sha256=sha(cert.encode()),original_R4PW_sha256=sha(original),R4ID_sha256=sha(ids),candidate_R4PW_sha256=sha(world),all71_ids=groupids,all71_placement_ordinals=[p[1]for p in placements],all71_placement_bytes_exact=True,arms=reports,limits=['Host source regression with separately proposed29-certificate fixture; not target/newprogramme evidence.','Parent/candidate physical body predicate and policy/AREA call bodies extracted from real source.','No full engine/game build, source asset writes,image or guest.'])
(a.output/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(status=result['status'],checks=[r['stdout']for r in reports],out=str(a.output))))

