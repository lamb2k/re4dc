#!/usr/bin/env python3
"""Extract actual missing-R4TC loader/policy path; host seams, no runtime edits."""
from pathlib import Path
import hashlib,json,struct,subprocess,sys
from provenance_actual_path import function
HERE=Path(__file__).resolve().parent;SOURCE=HERE.parents[2]/'game/platform/native_static.cpp';sha=lambda b:hashlib.sha256(b).hexdigest()
def main():
 O=Path(sys.argv[1]);s=SOURCE.read_text();ns=s[s.index('namespace trans{'):];names=['static bool listed(unsigned r)','static void open(unsigned r,std::uint32_t r4pw_crc,unsigned parts)','static unsigned target(unsigned c,unsigned p)','static void mask(const Ps2Part* parts,const Ps2Placement* pl,unsigned n)','static unsigned pass_of(const Ps2Part& m,unsigned index,unsigned now)','static bool candidate(unsigned index,unsigned pass)','static float far_of(const Ps2Part& m,unsigned index,unsigned drawn)'];funcs={name:function(ns,name)for name in names};prefix=ns.split('namespace trans{',1)[1].split('static bool listed(unsigned r)',1)[0];assert 'static void close(){'in prefix and 'cls=nullptr' in prefix and funcs[names[1]].split('{',1)[1].lstrip().startswith('close();');structs=s[s.index('struct Ps2Part {'):s.index('struct Ps2Counts {')];crc=function(s,'std::uint32_t ps2_crc32(const unsigned char* p,unsigned n)')
 R=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/texture-rect21-20261021');files=json.loads((R/'image-plan-04/baseline-file-identities.json').read_text())['files'];m=files['/dc/native/trclass.idx']
 with(R/'standalone-B-01/gdemu/track03.iso').open('rb')as f:f.seek((m['extent']-45000)*2048);idx=f.read(m['bytes'])
 assert sha(idx)==m['sha256']and idx[:4]==b'R4TI';n=struct.unpack_from('<I',idx,4)[0];rooms=struct.unpack_from('<%dH'%n,idx,8);assert n==26 and all(x not in rooms for x in(0x10c,0x10d,0x10e));assert all('/dc/native/r%03x/ps2-world.r4tc'%r not in files for r in(0x10c,0x10d,0x10e))
 source='''#include <cstdint>
#include <cstring>
#include <cstdio>
#include <cstdlib>
#include <cstdarg>
#include <cassert>
#include <fcntl.h>
#include <sys/types.h>
#define RE4DC_TRANS_POLICY_DEBUG 1
#define RE4DC_PS2_PASS_MASK 1
volatile unsigned re4dc_trans_policy=3,re4dc_trans_debug=0;
static unsigned frees=0,index_opens=0,profile_opens=0;static int pos[3]={};static char lastlog[512];
static unsigned char profile[28];
static unsigned char frozen_index[]={INDEX_BYTES};
using file_t=int;constexpr int FILEHND_INVALID=-1;
file_t fs_open(const char*p,int){if(!std::strcmp(p,"/cd/dc/native/trclass.idx")){++index_opens;pos[1]=0;return1;}if(std::strstr(p,"ps2-world.r4tc")){++profile_opens;if(std::strstr(p,"r103")){pos[2]=0;return2;}}return FILEHND_INVALID;}
int fs_close(file_t){return0;}ssize_t fs_total(file_t f){return f==1?sizeof(frozen_index):sizeof(profile);}
ssize_t fs_read(file_t f,void*out,std::size_t n){const unsigned char*b=f==1?frozen_index:profile;const std::size_t total=fs_total(f);if(n>total-pos[f])n=total-pos[f];std::memcpy(out,b+pos[f],n);pos[f]+=n;return n;}
void*re4dc_static_alloc(unsigned n){return std::malloc(n);}void re4dc_static_free(void*p){++frees;std::free(p);}int re4dc_static_heap_free(){return1024;}
void re4dc_log(const char*fmt,...){va_list a;va_start(a,fmt);std::vsnprintf(lastlog,sizeof(lastlog),fmt,a);va_end(a);}
ACTUAL_STRUCTS
struct MeshStub{unsigned first_part,part_count;};struct PackageStub{MeshStub mesh{0,3};const MeshStub*meshes()const{return &mesh;}};
struct WorldStub{unsigned room=0;bool masked=true;unsigned char pass_mask[4]={4,4,4,4};Ps2Part*parts=nullptr;PackageStub package;}ps2w;
ACTUAL_CRC
namespace trans{
ACTUAL_PREFIX
ACTUAL_FUNCTIONS
}
static unsigned long long checks=0;static std::uint32_t snapshot(){std::uint32_t h=2166136261U;Ps2Placement pl{};
 for(unsigned policy=0;policy<256;++policy){re4dc_trans_policy=policy;for(unsigned debug: {0U,1U,0xffffffffU}){re4dc_trans_debug=debug;for(unsigned i=0;i<4;++i)ps2w.pass_mask[i]=4;trans::mask(ps2w.parts,&pl,1);for(unsigned i=0;i<4;++i){assert(ps2w.pass_mask[i]==4);++checks;}
  for(unsigned i=0;i<3;++i){for(unsigned now=0;now<4;++now){unsigned got=trans::pass_of(ps2w.parts[i],i,now);assert(got==now);h=(h^got)*16777619U;++checks;h=(h^unsigned(trans::far_of(ps2w.parts[i],i,now)))*16777619U;++checks;}for(unsigned pass=0;pass<3;++pass){assert(!trans::candidate(i,pass));++checks;}}
 }}return h;}
int main(){Ps2Part parts[3]{};for(auto&m:parts)m.pass=2;ps2w.parts=parts;trans::Head header{{'R','4','T','C'},1,1,3,0x11223344U,0};profile[24]=4;profile[25]=6;profile[26]=10;header.body_crc=ps2_crc32(profile+24,3);std::memcpy(profile,&header,sizeof(header));unsigned closed=0;
 for(unsigned room: {0x10cU,0x10dU,0x10eU}){std::uint32_t digest=0;for(unsigned variant=0;variant<2;++variant){ps2w.room=0x103;trans::open(0x103,0x11223344U,3);assert(trans::cls&&trans::nparts==3&&trans::room==0x103);unsigned before=profile_opens,free_before=frees;ps2w.room=room;trans::open(room,variant?0xaabbccddU:0x12345678U,3);assert(!trans::cls&&!trans::block&&!trans::nparts&&trans::room==~0U);assert(profile_opens==before&&frees==free_before+1&&std::strstr(lastlog,"classes=unlisted"));++closed;trans::cut_low=100;trans::cut_high=200;unsigned got=snapshot();if(!variant)digest=got;else assert(digest==got);}std::printf("room=%03x original_candidate_UNKNOWN_digest=%08x\\n",room,digest);}
 assert(index_opens==1&&closed==6&&profile_opens==6);std::printf("PASS original_candidate_variants=6 index_reads=1 previous_table_closed=6 r4tc_missing_opens=0 policy_checks=%llu\\n",checks);}
'''
 source=source.replace('#include <cassert>','#include <cassert>\n#include <initializer_list>').replace('return1','return 1').replace('return2','return 2').replace('return0','return 0').replace('return1024','return 1024').replace('INDEX_BYTES',','.join(map(str,idx))).replace('ACTUAL_STRUCTS',structs).replace('ACTUAL_CRC',crc).replace('ACTUAL_PREFIX',prefix).replace('ACTUAL_FUNCTIONS','static float cut_low,cut_high;\n'+'\n'.join(funcs.values()))
 H=O/'unknown-source';H.mkdir();(H/'probe.cpp').write_text(source);cmd=['g++','-std=c++17','-O2','-g0','-fsanitize=undefined',str(H/'probe.cpp'),'-o',str(H/'probe')];built=subprocess.run(cmd,capture_output=True,timeout=30);(H/'compile.log').write_bytes((built.stdout+built.stderr)[:32768]);assert not built.returncode,built.stderr[:2000];run=subprocess.run([str(H/'probe')],capture_output=True,text=True,timeout=15);(H/'output.txt').write_text(run.stdout+run.stderr);assert not run.returncode and not run.stderr
 report=dict(status='PASS_ACTUAL_UNLISTED_R4TC_SOURCE_PATH_HOST_ONLY',native_static_sha256=sha(SOURCE.read_bytes()),source_functions={k:sha(v.encode())for k,v in funcs.items()},actual_structs_sha256=sha(structs.encode()),actual_prefix_close_idx_sha256=sha(prefix.encode()),index=dict(bytes=len(idx),sha256=sha(idx),hex=idx.hex(),rooms=['%03x'%x for x in rooms],extent=m['extent'],all3rooms_unlisted=True),original_metadata_files_absent=['r10c','r10d','r10e'],original_and_candidate_bodyCRC_variants=6,source_policy_word_variants=256,debug_word_variants=3,stale_previous_class_table_closed=6,index_read_once=True,no_missing_R4TC_IO=True,pass_of_returns_existing_pass=True,candidate_no_extra_pass=True,mask_unchanged=True,far_behavior_original_candidate_identical=True,output=run.stdout,command=cmd,binary_sha256=sha((H/'probe').read_bytes()),source_policy_callsite='trans::open(ps2w.room,policySourceCrc,h.parts);',limits=['Actual extracted functions/structs with explicit filesystem/heap/MeshPackage seams; no fullps2_open, programme or targetexecution.','No literalUNKNOWN R4TCtable created: cls staysnull, even debugwords cannot affectearly guard.','Proof requires samefrozen trclass.idx26list and no newclassmetadata; inherited originalmaterial/pass/cull/geometry and physicalidentity contracts remain.','No newgameasset output or23held release; main must select/approve any optionalunlisted-rule adoption.'])
 assert report['source_policy_callsite']in s;(O/'unknown-profile-proof.json').write_text(json.dumps(report,indent=2)+'\n');print(run.stdout)
if __name__=='__main__':main()