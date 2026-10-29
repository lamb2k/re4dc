"""EF11 narrow pTobjA: actual source adapter, owner, GX capture and native FIFO.

The host PVR header gives the synthetic uncached range a mappable host address;
it is not a hardware/cache qualification. Production uses pinned KOS's
PVR_RAM_INT_BASE, and all actual readback is aligned volatile uint32_t.
"""
from pathlib import Path
import importlib.util
import os
import re
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
INC = ROOT / "game/platform/include"
BASE = "d45eb759dd92685255929625e04fae3d7a46bca7"


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tests" / (name + ".py"))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


TILES = module("test_cloth_tiles11")
OWNER = module("test_plan_owner_scoped")
TPL_TEST = module("test_convert_tpl")
sys.path.insert(0, str(ROOT / "tools"))
import convert_tpl as TPL
import prepare_native_ui as UI


def fixture():
    stub, code = TILES.actual_source_fixture()
    code = code.split("int main(){", 1)[0]
    # Use the pinned KOS setting values in this recorder. This still records
    # contexts; it does not pretend to execute pvr_poly_compile on hardware.
    for before, after in (("PVR_DEPTHCMP_GEQUAL=3", "PVR_DEPTHCMP_GEQUAL=6"),
                          ("PVR_TXRALPHA_ENABLE=1", "PVR_TXRALPHA_ENABLE=0"),
                          ("PVR_TXRENV_MODULATEALPHA=1", "PVR_TXRENV_MODULATEALPHA=3"),
                          ("PVR_UVCLAMP_U=1,PVR_UVCLAMP_V=2", "PVR_UVCLAMP_U=2,PVR_UVCLAMP_V=1")):
        stub = stub.replace(before, after)
    code = code.replace("return 0x40000000;", "return 0x08000000;").replace("fmt==0x40000000", "fmt==0x08000000")
    stub += "\n#define PVR_RAM_INT_BASE 0x40000000U\n#define PVR_DEPTHWRITE_ENABLE 0\n"
    code = code.replace("#include <vector>", "#include <vector>\n#include <cstdio>\n#include <sys/mman.h>")
    code = code.replace("struct Texture{unsigned width=64,height=64;};", r'''
struct Texture{unsigned width=8,height=8,format=0,flags=0,data_size=128,payload=1,reserved_0=0;};
struct Header{unsigned texture_count=1;};
''')
    code = code.replace("struct Package{Texture value;const Texture* textures(){return &value;}void* pvr_texture(unsigned){return spill;}};", r'''
struct Package{Texture value;Header head;void* pixels=nullptr;bool complete=true;
 const Texture* textures(){return &value;}void* pvr_texture(unsigned){return pixels;}
 const Header& header()const{return head;}bool upload_complete()const{return complete;}};
''')
    code = code.replace("constexpr unsigned kTextureCount=1;", "constexpr unsigned kTextureCount=2;")
    code = code.replace("entries[1];Entry& entry", "entries[2];Entry& entry")
    code = code.replace("namespace re4dc::texture {unsigned", "namespace re4dc::texture {constexpr unsigned kRgb565=0,kPayloadLinear=0,kPayloadTwiddled=1;unsigned")
    code = code.replace("Entry* resolve(const Re4dcUiImage&,const void* mask,bool pin){assert(!mask&&pin);++opens;return missing?nullptr:&entry;}", r'''
alignas(32) unsigned char source_pixels[2][128];
struct GXTexObj{unsigned w[8];};GXTexObj source_objects[2];int owner_key,alias_key;
extern "C" void GXInitTexObj(GXTexObj*,void*,unsigned short,unsigned short,int,int,int,unsigned char);
extern "C" void GXInitTexObjLOD(GXTexObj*,int,int,float,float,float,unsigned char,unsigned char,int);
void(*resolve_hook)(unsigned)=nullptr;void(*sq_hook)()=nullptr;void(*spill_hook)()=nullptr;
void(*select_hook)()=nullptr;unsigned locks=0,waits=0,unlocks=0;bool missing_second=false;
struct Key{unsigned crc,fnv;};int external_result=0;
int external_image_key(const Re4dcUiImage&,Key&){return external_result;}
Entry* resolve(const Re4dcUiImage& image,const void* mask,bool pin){assert(!mask&&pin);++opens;
 const unsigned i=image.pixels==source_pixels[1];if(resolve_hook)resolve_hook(opens);
 return missing || (missing_second && i)?nullptr:&entries[i];}
std::uint32_t* sq_lock(void*){++locks;if(sq_hook)sq_hook();return nullptr;}
void sq_wait(){++waits;assert(locks==unlocks+1);}
void sq_unlock(){++unlocks;assert(locks==unlocks);}
''')
    code = code.replace("void* re4dc_model_deferred_storage(unsigned* n){", 'extern "C" void* re4dc_model_deferred_storage(unsigned* n){if(spill_hook)spill_hook();')
    code = code.replace("assert(list==PVR_LIST_TR_POLY);}", "assert(list==PVR_LIST_TR_POLY);if(select_hook)select_hook();}")
    code = code.replace("w==64&&h==64&&ptr==spill", "w>=8&&w<=16&&h>=8&&h<=16&&ptr!=nullptr")
    prefix = OWNER.existing_fixture()
    prefix = prefix.replace('extern "C" void re4dc_log(const char*,...){}', "")
    code += prefix + r'''
// One registered allocation covers both source objects and texels through
// separate publications, exercising the actual allocation/incarnation API.
int object_key;
void bind_source(){
 re4dc_model_bind_draw_owner(&object_key,source_objects,sizeof source_objects,0);
 re4dc_model_bind_draw_owner(&owner_key,source_pixels,sizeof source_pixels,0);
}
void fill_source(){
 std::memset(source_pixels[0],255,128);
 // Independent block walk: each of the four GC tiles has16 big-endian words.
 for(unsigned block_y=0;block_y<2;++block_y)for(unsigned block_x=0;block_x<2;++block_x)
 for(unsigned iy=0;iy<4;++iy)for(unsigned ix=0;ix<4;++ix){
  const unsigned x=block_x*4+ix,y=block_y*4+iy;
  const unsigned color=((x*4)&31)<<11|((y*8)&63)<<5|((x+y)*2&31);
  const unsigned offset=((block_y*2+block_x)*16+iy*4+ix)*2;
  source_pixels[1][offset]=color>>8;source_pixels[1][offset+1]=color;
 }
}
void upload_source(){
 for(unsigned n=0;n<2;++n){
  auto* words=static_cast<unsigned*>(entries[n].package.pixels);std::memset(words,0,128);
  for(unsigned y=0;y<8;++y)for(unsigned x=0;x<8;++x){
   unsigned index=0;for(unsigned bit=0;bit<3;++bit){index|=((y>>bit)&1)<<(2*bit);index|=((x>>bit)&1)<<(2*bit+1);}
   const unsigned byte=(((y/4)*2+x/4)*16+(y%4)*4+x%4)*2;
   const unsigned rgb=source_pixels[n][byte]*256U+source_pixels[n][byte+1];
   words[index/2]|=rgb<<((index%2)*16);
  }
 }
}
void material_fresh(unsigned cols,unsigned rows,std::vector<Vec>& grid){
 fresh();set_sheet(cols,rows,grid);resolve_hook=nullptr;sq_hook=spill_hook=select_hook=nullptr;
 locks=waits=unlocks=0;missing_second=false;external_result=0;
 for(unsigned i=0;i<2;++i){entries[i]={};entries[i].package.pixels=reinterpret_cast<void*>(PVR_RAM_INT_BASE+4096+i*256);}
 fill_source();upload_source();
 for(unsigned i=0;i<2;++i)GXInitTexObj(&source_objects[i],source_pixels[i],8,8,4,0,0,0);
 re4dc_model_unbind_draw_owner(&alias_key);bind_source();
 auto& c=ClothWk[0];c.tex=&source_objects[0];c.pTobjA=&source_objects[1];c.color={64,128,192,255};
 LightMgr.e.AmbientScr={255,255,255,255};for(auto& light:lights)light=nullptr;
}
unsigned checked=0;
re4dc::NativeDrawResult draw(){++checked;return re4dc_cloth_native(&ClothWk[0],lights,&pos,1);}
void expect(re4dc::NativeDrawResult r,Outcome outcome,unsigned sent=0,unsigned queued=0){
 assert(r.outcome==outcome&&r.submitted==sent&&r.queued==queued);
 assert(r.fallback_allowed()==(!r.published()&&(outcome==Outcome::UnsupportedBeforePublication||outcome==Outcome::Refused)));
 assert(locks==unlocks);
}
enum Mutation{none,pixel,descriptor,owner,object_owner,cloth_owner,frame_owner,primary_upload,secondary_upload,
             primary_invalid,primary_pointer,material_color,ambient_color,selected_light};
Mutation mutation=none;unsigned mutate_at=0;
void mutate(){
 switch(mutation){
 case pixel:source_pixels[1][19]^=1;break;
 case descriptor:source_objects[0].w[3]=1;break;
 case owner:re4dc_model_bind_draw_owner(&owner_key,source_pixels,sizeof source_pixels,0);break;
 case object_owner:re4dc_model_unbind_draw_owner(&object_key);break;
 case cloth_owner:++cloth11_incarnation[0];break;
 case frame_owner:++pG->Frame_cnt;break;
 case primary_upload:++entries[0].upload_incarnation;break;
 case secondary_upload:++entries[1].upload_incarnation;break;
 case primary_invalid:entries[0].valid=false;break;
 case primary_pointer:entries[0].package.pixels=reinterpret_cast<void*>(PVR_RAM_INT_BASE-32U);break;
 case material_color:ClothWk[0].color.r=63;break;
 case ambient_color:LightMgr.e.AmbientScr.r=254;break;
 case selected_light:lights[0]=reinterpret_cast<cLight*>(1);break;
 default:break;
 }
}
void mutate_resolve(unsigned call){if(call==mutate_at)mutate();}
void mutate_once(){mutate();sq_hook=spill_hook=select_hook=nullptr;}
void mutate_after_send(){mutate();after_send_hook=nullptr;}
int main(){
 auto* mapping=mmap(reinterpret_cast<void*>(PVR_RAM_INT_BASE+4096),4096,PROT_READ|PROT_WRITE,
                    MAP_PRIVATE|MAP_ANONYMOUS|MAP_FIXED_NOREPLACE,-1,0);
 assert(mapping==reinterpret_cast<void*>(PVR_RAM_INT_BASE+4096));std::vector<Vec> grid;
 for(unsigned width:{2U,99U,100U,101U,255U}){
  material_fresh(width,4,grid);const auto original=grid;
  const unsigned tiles=width<=100?1:1+(width-2)/99;
  expect(draw(),Outcome::Submitted,3*tiles);assert(opens==2&&compiles==2&&waits==1&&locks==1);
  assert(entries[0].frame==frame&&entries[1].frame==frame);
  assert(!std::memcmp(original.data(),grid.data(),grid.size()*sizeof(Vec)));
  for(const auto& packet:packet_log){assert(packet[0].flags==4);
   const auto* header=reinterpret_cast<const unsigned*>(packet.data());
   assert(header[0]==4&&header[1]==5&&header[2]==PVR_DEPTHCMP_GEQUAL&&header[3]==PVR_DEPTHWRITE_ENABLE);
   assert(header[4]==(PVR_UVCLAMP_U|PVR_UVCLAMP_V)&&header[5]==PVR_TXRALPHA_ENABLE);
   for(unsigned i=1;i<packet.size();++i)assert(packet[i].argb==0xffffffffU);
   assert(packet.back().flags==PVR_CMD_VERTEX_EOL);
  }
 }
 // Every primary-upload word is observed; CPU white cannot bless an old
 // nonwhite cached upload at the same source descriptor/owner/incarnation.
 for(unsigned word=0;word<32;++word){material_fresh(2,2,grid);
  static_cast<unsigned*>(entries[0].package.pixels)[word]^=1;expect(draw(),Outcome::UnsupportedBeforePublication);
  assert(opens==2&&packet_log.empty()&&waits==1);
 }
 // Likewise refuse a stale/boosted/tinted secondary upload, not just its
 // format/dimensions. Pattern exercises GX tile/endian versus PVR twiddle.
 for(unsigned word=0;word<32;++word){material_fresh(2,2,grid);
  static_cast<unsigned*>(entries[1].package.pixels)[word]^=1;expect(draw(),Outcome::UnsupportedBeforePublication);
 }
 material_fresh(2,2,grid);entries[0].package.value.payload=0;entries[1].package.value.payload=0;
 expect(draw(),Outcome::Submitted,1); // linear package upload is twiddled too
 for(unsigned which=0;which<2;++which)for(unsigned bad=0;bad<11;++bad){material_fresh(2,2,grid);
  auto& p=entries[which].package;switch(bad){
   case 0:p.complete=false;break;case 1:p.head.texture_count=2;break;case 2:p.value.width=16;break;
   case 3:p.value.height=16;break;case 4:p.value.format=1;break;case 5:p.value.flags=4;break;
   case 6:p.value.data_size=124;break;case 7:p.value.reserved_0=1;break;case 8:p.value.payload=2;break;
   case 9:p.pixels=reinterpret_cast<void*>(PVR_RAM_INT_BASE+4100);break;
   case 10:p.pixels=reinterpret_cast<void*>(PVR_RAM_INT_BASE-0x20000000U+4096);break;}
  expect(draw(),Outcome::UnsupportedBeforePublication);assert(packet_log.empty());
 }
 material_fresh(2,2,grid);entries[0].package.pixels=reinterpret_cast<void*>(PVR_RAM_INT_BASE+8U*1024U*1024U-96);
 expect(draw(),Outcome::UnsupportedBeforePublication);
 // Unknown/missing/ambiguous allocation authority is rejected before reads.
 material_fresh(2,2,grid);ClothWk[0].pTobjA=reinterpret_cast<void*>(1);expect(draw(),Outcome::UnsupportedBeforePublication);assert(!opens);
 material_fresh(2,2,grid);source_objects[0].w[0]=1;expect(draw(),Outcome::UnsupportedBeforePublication);assert(!opens);
 material_fresh(2,2,grid);re4dc_model_bind_draw_owner(&alias_key,source_pixels,sizeof source_pixels,0);
 expect(draw(),Outcome::UnsupportedBeforePublication);assert(!opens);
 material_fresh(2,2,grid);re4dc_model_bind_draw_owner(&owner_key,source_pixels,127,0);
 expect(draw(),Outcome::UnsupportedBeforePublication);assert(!opens);
 for(unsigned i=0;i<2;++i){material_fresh(2,2,grid);source_objects[i].w[5]=0;
  expect(draw(),Outcome::UnsupportedBeforePublication);assert(!opens);}
 material_fresh(2,2,grid);source_pixels[0][127]=254;expect(draw(),Outcome::UnsupportedBeforePublication);assert(!opens);
 material_fresh(2,2,grid);const unsigned proxy[]={0x524e3452U,0x00004645U};std::memcpy(source_pixels[1],proxy,8);
 expect(draw(),Outcome::UnsupportedBeforePublication);assert(!opens);
 for(int result:{-1,1}){material_fresh(2,2,grid);external_result=result;expect(draw(),Outcome::UnsupportedBeforePublication);assert(!opens);}
 // Source lighting/material class is checked at this call, never cached.
 for(unsigned channel=0;channel<4;++channel){material_fresh(2,2,grid);reinterpret_cast<unsigned char*>(&ClothWk[0].color)[channel]=63;
  expect(draw(),Outcome::UnsupportedBeforePublication);assert(!opens);}
 material_fresh(2,2,grid);LightMgr.e.AmbientScr.g=254;expect(draw(),Outcome::UnsupportedBeforePublication);
 material_fresh(2,2,grid);lights[0]=reinterpret_cast<cLight*>(1);expect(draw(),Outcome::UnsupportedBeforePublication);
 material_fresh(2,2,grid);ClothWk[0].x74=1;expect(draw(),Outcome::UnsupportedBeforePublication);
 // All source changes at either texture acquisition forbid stale GX replay.
 for(unsigned call:{1U,2U})for(auto changed:{pixel,descriptor,owner,object_owner,cloth_owner,frame_owner,material_color,ambient_color,selected_light}){
  material_fresh(2,2,grid);mutation=changed;mutate_at=call;resolve_hook=mutate_resolve;
  expect(draw(),Outcome::PartialAbort);assert(packet_log.empty()&&opens==call);
 }
 for(auto changed:{primary_upload,primary_invalid}){material_fresh(2,2,grid);
  mutation=changed;mutate_at=2;resolve_hook=mutate_resolve;expect(draw(),Outcome::Refused);assert(!waits);}
 // The SQ lock is a possible yield too. No stale pointer is read on entry.
 for(auto changed:{pixel,descriptor,owner,object_owner,cloth_owner,frame_owner,material_color,ambient_color,selected_light}){
  material_fresh(2,2,grid);mutation=changed;sq_hook=mutate_once;expect(draw(),Outcome::PartialAbort);assert(!waits);
 }
 for(auto changed:{primary_upload,secondary_upload,primary_invalid,primary_pointer}){
  material_fresh(2,2,grid);mutation=changed;sq_hook=mutate_once;expect(draw(),Outcome::Refused);assert(locks==1);
 }
 material_fresh(2,2,grid);missing_second=true;expect(draw(),Outcome::Refused);assert(!waits);
 material_fresh(2,2,grid);missing=true;expect(draw(),Outcome::Refused);assert(opens==1);
 // Direct selection and queue spill allocation can yield after preparation.
 material_fresh(2,2,grid);mutation=pixel;select_hook=mutate_once;expect(draw(),Outcome::PartialAbort);assert(packet_log.empty());
 material_fresh(2,2,grid);mutation=primary_upload;select_hook=mutate_once;expect(draw(),Outcome::Refused);assert(packet_log.empty());
 for(bool space:{false,true}){material_fresh(2,2,grid);source_draws_finished=false;deferred_top=8192;spill_available=space;
  mutation=pixel;spill_hook=mutate_once;expect(draw(),Outcome::PartialAbort);assert(!deferred_count);}
 material_fresh(2,3,grid);mutation=pixel;after_send_hook=mutate_after_send;
 expect(draw(),Outcome::PartialAbort,1);assert(packet_log.size()==1);
 material_fresh(2,3,grid);mutation=primary_upload;after_send_hook=mutate_after_send;
 expect(draw(),Outcome::PartialAbort,1);assert(packet_log.size()==1);
 // The admitted header/geometry uses the existing FIFO and clipping/tiles.
 material_fresh(101,2,grid);source_draws_finished=false;spill_available=false;
 deferred_top=16384+kEffectQuad21Node+201*sizeof(pvr_vertex_t);
 expect(draw(),Outcome::PartialAbort,0,1);assert(deferred_count==1);
 material_fresh(2,2,grid);source_draws_finished=false;deferred_top=8192;spill_available=false;
 expect(draw(),Outcome::Refused);assert(!deferred_count);
 material_fresh(3,2,grid);grid[0].z=grid[3].z=-.5f;
 expect(draw(),Outcome::Submitted,2);assert(packet_log[0].size()>4);
 material_fresh(3,2,grid);for(auto& p:grid)p.z=1;expect(draw(),Outcome::Culled);
 material_fresh(2,2,grid);source_draws_finished=false;expect(draw(),Outcome::Queued,0,1);
 auto* packet=reinterpret_cast<const pvr_vertex_t*>(reinterpret_cast<const unsigned char*>(deferred_first)+kEffectQuad21Node);
 const auto copied=packet[1];source_pixels[1][0]^=1;assert(!std::memcmp(&copied,&packet[1],sizeof copied));
 assert(!munmap(mapping,4096));std::printf("cloth material11: %u actual-source cases; owner/upload/SQ/FIFO gates PASS\n",checked);
}
'''
    return stub, code


def producer_fixture(packages, pixels):
    stub, code = fixture()
    code = code.split("using Outcome=re4dc::NativeDrawOutcome;", 1)[0]
    first = code.index("struct Texture{")
    last = code.index("constexpr unsigned kTextureCount", first)
    code = code[:first] + '#include "texture_package.hpp"\nusing Package=re4dc::texture::Package;\n' + code[last:]
    code = code.replace("namespace re4dc::texture {constexpr unsigned kRgb565=0,kPayloadLinear=0,kPayloadTwiddled=1;unsigned pvr_format(const Texture&){return 0x08000000;}}", "")
    code = code.replace("void sq_wait(){++waits;assert(locks==unlocks+1);}", "void finish_uploads();void sq_wait(){++waits;assert(locks==unlocks+1);finish_uploads();}")
    code += OWNER.existing_fixture().replace('extern "C" void re4dc_log(const char*,...){}', "")
    for n, blob in enumerate(packages):
        code += f'\nalignas(32) unsigned char package{n}[]={{' + ",".join(map(str, blob)) + '};\n'
    for n, data in enumerate(pixels):
        code += f'\nconst unsigned char cpu{n}[]={{' + ",".join(map(str, data)) + '};\n'
    code += r'''
unsigned allocations=0,upload_calls=0,readback_drains=0;
struct Pending{void* destination;unsigned char bytes[128];};std::vector<Pending> pending;
void* pvr_mem_malloc(std::size_t n){assert(n==128&&allocations<2);
 return reinterpret_cast<void*>(PVR_RAM_INT_BASE+4096+256*allocations++);}
void pvr_mem_free(void*){}
void pvr_txr_load(const void* p,void* q,std::size_t n){assert(n==128);Pending copy{};
 copy.destination=q;std::memcpy(copy.bytes,p,n);pending.push_back(copy);++upload_calls;}
void pvr_txr_load_ex(const void*,void*,unsigned,unsigned,unsigned){assert(false);}
void finish_uploads(){++readback_drains;for(auto& p:pending)std::memcpy(p.destination,p.bytes,128);pending.clear();}
int fs_open(const char*,int){return -1;}int fs_close(int){return 0;}ssize_t fs_total(int){return -1;}
void* fs_mmap(int){return nullptr;}ssize_t fs_read(int,void*,std::size_t){return -1;}off_t fs_seek(int,off_t,int){return -1;}
std::uint64_t timer_us_gettime64(){return 0;}
int main(){
 auto* mapping=mmap(reinterpret_cast<void*>(PVR_RAM_INT_BASE+4096),4096,PROT_READ|PROT_WRITE,
                    MAP_PRIVATE|MAP_ANONYMOUS|MAP_FIXED_NOREPLACE,-1,0);
 assert(mapping==reinterpret_cast<void*>(PVR_RAM_INT_BASE+4096));std::memset(mapping,0,4096);
 std::memcpy(source_pixels[0],cpu0,128);std::memcpy(source_pixels[1],cpu1,128);
 assert(entries[0].package.adopt(package0,sizeof package0));assert(entries[1].package.adopt(package1,sizeof package1));
 for(auto& e:entries){assert(!e.package.upload_complete());assert(e.package.upload());assert(e.package.upload_complete());
  assert(e.package.release_payload()&&e.package.payload_released());e.valid=true;e.upload_incarnation=7;}
 assert(upload_calls==2&&pending.size()==2&&!readback_drains);
 // Completion/publication does not itself mean the last SQ write has drained.
 assert(*static_cast<const unsigned*>(entries[0].package.pvr_texture(0))==0);
 for(unsigned i=0;i<2;++i)GXInitTexObj(&source_objects[i],source_pixels[i],8,8,4,0,0,0);
 int objects_key;re4dc_model_bind_draw_owner(&objects_key,source_objects,sizeof source_objects,0);
 re4dc_model_bind_draw_owner(&owner_key,source_pixels,sizeof source_pixels,0);
 Vec grid[]={{-1,1,-10},{1,1,-10},{-1,0,-10},{1,0,-10},{-1,-1,-10},{1,-1,-10}};
 auto& c=ClothWk[0];c={};c.tex=&source_objects[0];c.pTobjA=&source_objects[1];c.divH=2;c.divV=3;c.pVer=grid;
 c.be_flag=0x31;c.Scale=1;c.color={64,128,192,255};pG->Frame_cnt=frame;source_draws_finished=true;
 cLight* lights[8]{};Vec position{};auto result=re4dc_cloth_native(&c,lights,&position,1);
 assert(result.outcome==re4dc::NativeDrawOutcome::Submitted&&result.submitted==2&&packet_log.size()==2);
 assert(opens==2&&readback_drains==1&&pending.empty()&&allocations==2);
 // Same live source/entry keys, a different actual upload: refuse both the
 // primary-white and secondary-pattern cases before any next packet.
 for(unsigned which=0;which<2;++which){auto* upload=static_cast<unsigned*>(entries[which].package.pvr_texture(0));
  upload[31]^=1;packet_log.clear();result=re4dc_cloth_native(&c,lights,&position,1);
  assert(result.outcome==re4dc::NativeDrawOutcome::UnsupportedBeforePublication&&packet_log.empty());upload[31]^=1;}
 for(auto& e:entries)e.package.close();assert(!munmap(mapping,4096));
 std::puts("cloth material11: actual prepare -> Package validate/upload/release -> source adapter/FIFO PASS");
}
'''
    stub += "\nusing pvr_ptr_t=void*;\n#define PVR_TXRFMT_RGB565 (1U<<27)\n#define PVR_TXRFMT_ARGB1555 0U\n#define PVR_TXRFMT_ARGB4444 (2U<<27)\n#define PVR_TXRFMT_VQ_ENABLE (1U<<30)\n"
    return stub, code


class ClothMaterial11(unittest.TestCase):
    def build_run(self, stub, code, *, sanitize=False, full_owner=True, full_package=False, extra=()):
        with tempfile.TemporaryDirectory(prefix="re4dc-cloth-material11-") as td:
            tmp = Path(td)
            (tmp / "dc").mkdir()
            (tmp / "kos").mkdir()
            (tmp / "dc/pvr.h").write_text(stub)
            (tmp / "dc/sq.h").write_text("#pragma once\n#include <cstdint>\nstd::uint32_t* sq_lock(void*);void sq_wait();void sq_unlock();\n")
            (tmp / "kos/fs.h").write_text("#pragma once\n#include <sys/types.h>\n#include <cstddef>\n#include <fcntl.h>\nusing file_t=int;\n#define FILEHND_INVALID -1\nfile_t fs_open(const char*,int);ssize_t fs_read(file_t,void*,size_t);ssize_t fs_total(file_t);int fs_close(file_t);void* fs_mmap(file_t);off_t fs_seek(file_t,off_t,int);\n")
            (tmp / "kos.h").write_text("#include <kos/fs.h>\n#include <cstdint>\nstd::uint64_t timer_us_gettime64();\n")
            cpp = tmp / "fixture.cpp"
            cpp.write_text(code)
            exe = tmp / "check"
            flags = ["-std=c++20", "-O2", "-fpermissive", "-fno-pie", "-no-pie", "-ffunction-sections", "-fdata-sections", "-Wl,--gc-sections",
                     "-DRE4DC_FX_STRIP21=1", "-DRE4DC_CLOTH_NATIVE=1", "-DRE4DC_NATIVE_DRAW_OUTCOMES=1",
                     "-DRE4DC_CLOTH_SHEET11=1", "-DRE4DC_CLOTH_TILES11=1", "-DRE4DC_PS2_UPLOAD_INCARNATION=1",
                     "-DRE4DC_UI_HANDLES=1", "-DRE4DC_TA_DIRECT=1", "-DRE4DC_EFFECT_SPRITE_MAX=256",
                     "-DRE4DC_CLOTH_MATERIAL11=1", "-DRE4DC_PLAN_OWNER_SCOPED=1", "-DRE4DC_MODEL_DRAW_PLANS=1",
                     "-I" + str(tmp), "-I" + str(INC), "-I" + str(ROOT / "room"), *extra]
            if sanitize:
                flags += ["-fsanitize=address,undefined", "-fno-omit-frame-pointer"]
            sources = [str(cpp), str(ROOT / "game/platform/gx_stub.cpp")]
            if full_owner:
                sources += [str(ROOT / "room/pvr_geometry.cpp"), str(ROOT / "game/platform/native_draw_plan_owner.cpp"),
                            str(ROOT / "room/native_draw_plan.cpp"), str(ROOT / "room/room_storage.cpp")]
            if full_package:
                (tmp / "dc/pvr").mkdir()
                (tmp / "dc/pvr/pvr_mem.h").write_text("#include <cstddef>\nvoid* pvr_mem_malloc(std::size_t);void pvr_mem_free(void*);\n")
                (tmp / "dc/pvr/pvr_txr.h").write_text("#include <cstddef>\n#define PVR_TXRLOAD_16BPP 0\nvoid pvr_txr_load_ex(const void*,void*,unsigned,unsigned,unsigned);void pvr_txr_load(const void*,void*,std::size_t);\n")
                sources.append(str(ROOT / "room/texture_package.cpp"))
            run = subprocess.run(["g++", *flags, *sources, "-o", str(exe)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            run = subprocess.run([str(exe)], capture_output=True, text=True, env=dict(os.environ, ASAN_OPTIONS="detect_leaks=0"))
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            return run.stdout

    def test_actual_source_owner_upload_sampler_and_publication(self):
        stub, code = fixture()
        for sanitize in (False, True):
            with self.subTest(sanitize=sanitize):
                output = self.build_run(stub, code, sanitize=sanitize)
                self.assertIn("actual-source cases", output)

    def test_actual_sampler_calls_match_source_defaults_and_revoke_unknown_state(self):
        sdk = (REPO / "src/lib/GXTexture.c").read_text()
        init = OWNER.function(sdk, "void GXInitTexObj(").replace("GXInitTexObj(", "SourceGXInitTexObj(", 1)
        lod = OWNER.function(sdk, "void GXInitTexObjLOD(").replace("GXInitTexObjLOD(", "SourceGXInitTexObjLOD(", 1)
        frontend = OWNER.function((REPO / "src/game/trans.cpp").read_text(), "void ftObj(")
        code = r'''
#include <cassert>
#include <cstring>
#include <limits>
#include "cloth_material11_sampler.hpp"
using u8=unsigned char;using u16=unsigned short;using u32=unsigned;using f32=float;
using GXTexFmt=int;using GXTexWrapMode=int;using GXBool=unsigned char;using GXTexFilter=int;using GXAnisotropy=int;
struct GXTexObj{unsigned w[8];};struct FtRec{unsigned w[4];};
struct __GXTexObjInt{u32 mode0,mode1,image0,image3,userData;GXTexFmt fmt;u32 tlutName;u16 loadCnt;u8 loadFmt,flags;};
static_assert(sizeof(__GXTexObjInt)==32);
constexpr int GX_TF_I4=0,GX_TF_I8=1,GX_TF_IA4=2,GX_TF_IA8=3,GX_TF_RGB565=4,GX_TF_RGB5A3=5,GX_TF_RGBA8=6,GX_TF_CMPR=14;
constexpr int GX_CLAMP=0,GX_LINEAR=1,_GX_TF_CTF=32;
unsigned GX2HWFiltConv[]={0,4,1,5,2,6};
#define ASSERTMSGLINE(line,cond,...) assert(cond)
#define ASSERTMSGLINEV(line,cond,...) assert(cond)
#define ASSERTMSG1LINE(line,cond,...) assert(cond)
#define CHECK_GXBEGIN(...)
#define __cntlzw(x) __builtin_clz(x)
#define SET_REG_FIELD(line,reg,size,shift,val) (reg=((reg)&~(((1U<<(size))-1)<<(shift)))|((u32(val)&((1U<<(size))-1))<<(shift)))
#define SOME_SET_REG_MACRO(reg,size,shift,val) SET_REG_FIELD(0,reg,size,shift,val)
extern "C" void GXInitTexObj(GXTexObj*,void*,u16,u16,int,int,int,u8);
extern "C" void GXInitTexObjCI(GXTexObj*,void*,u16,u16,int,int,int,u8,unsigned);
extern "C" void GXInitTexObjLOD(GXTexObj*,int,int,float,float,float,u8,u8,int);
''' + init + "\n" + lod + "\n" + frontend + r'''
bool captured(const GXTexObj& o){return re4dc::cloth_material11::linear_clamp(o.w);}
int main(){alignas(32) static unsigned char pixels[128];GXTexObj port{},source{};
 for(unsigned mip:{0U,1U})for(int ws=0;ws<3;++ws)for(int wt=0;wt<3;++wt){
  std::memset(&port,0xff,sizeof port);GXInitTexObj(&port,pixels,8,8,4,ws,wt,mip);
  SourceGXInitTexObj(&source,pixels,8,8,4,ws,wt,mip);
  const auto& s=*reinterpret_cast<const __GXTexObjInt*>(&source);
  const bool source_linear=((s.mode0>>4)&1)==1&&((s.mode0>>5)&7)==4&&!(s.mode0&15)&&s.mode1==0;
  assert(captured(port)==source_linear);assert(captured(port)==(!mip&&!ws&&!wt));
 }
 for(int min=0;min<6;++min)for(int mag=0;mag<2;++mag)for(unsigned bc=0;bc<2;++bc)for(unsigned edge=0;edge<2;++edge){
  GXInitTexObj(&port,pixels,8,8,4,0,0,0);SourceGXInitTexObj(&source,pixels,8,8,4,0,0,0);
  GXInitTexObjLOD(&port,min,mag,0,0,0,bc,edge,0);SourceGXInitTexObjLOD(&source,min,mag,0,0,0,bc,edge,0);
  const auto& s=*reinterpret_cast<const __GXTexObjInt*>(&source);
  assert(captured(port)==(((s.mode0>>4)&1)==1&&((s.mode0>>5)&7)==4));
 }
 for(float value:{-.5f,.5f,1.f,std::numeric_limits<float>::infinity(),std::numeric_limits<float>::quiet_NaN()})
 for(unsigned field=0;field<3;++field){GXInitTexObj(&port,pixels,8,8,4,0,0,0);
  GXInitTexObjLOD(&port,1,1,field==0?value:0,field==1?value:0,field==2?value:0,0,1,0);assert(!captured(port));
  GXInitTexObjLOD(&port,1,1,0,0,0,0,1,0);assert(captured(port));}
 for(unsigned bad=0;bad<3;++bad){GXInitTexObj(&port,pixels,8,8,4,0,0,0);
  GXInitTexObjLOD(&port,1,1,0,0,0,bad==0?2:0,bad==1?2:1,bad==2?1:0);assert(!captured(port));}
 // Every init resets prior state; copies preserve only an established capture.
 GXInitTexObj(&port,pixels,8,8,4,0,0,0);GXTexObj copied;std::memcpy(&copied,&port,sizeof port);assert(captured(copied));
 GXInitTexObj(&port,pixels,8,8,4,0,0,1);assert(!captured(port));
 GXInitTexObj(&port,pixels,8,8,4,0,0,0);assert(captured(port));
 GXInitTexObjCI(&port,pixels,8,8,8,0,0,0,19);assert(port.w[4]==19&&captured(port)); // format refused by material preflight
 FtRec record{{unsigned(reinterpret_cast<std::uintptr_t>(pixels)),0x00080008,4,0}};
 ftObj(&port,record);assert(!captured(port));for(unsigned i=4;i<8;++i)assert(!port.w[i]);
 GXInitTexObjLOD(&port,1,1,0,0,0,0,1,0);assert(!captured(port)); // LOD cannot promote a synthesized object
 GXInitTexObj(&port,pixels,8,8,4,0,0,0);assert(captured(port));
}
'''
        code = code.replace("#include <limits>", "#include <limits>\n#include <initializer_list>\n#include <cstdint>")
        for sanitize in (False, True):
            with self.subTest(sanitize=sanitize):
                self.build_run("#pragma once\n", code, sanitize=sanitize, full_owner=False)

    def test_actual_source_stage_and_full_ambient_contract(self):
        cloth = (REPO / "src/game/cloth.cpp").read_text()
        lighting = (REPO / "src/game/trans_lit.cpp").read_text()
        start = cloth.index("    GXSetCullMode(0);", cloth.index("void clothTrans(Cloth* pCL)\n{"))
        initial = cloth[start:cloth.index("    cModel model;", start)]
        start = cloth.index("    GXSetNumTexGens(1);", start)
        final_call = "    GXSetNumTevStages(nStages);"
        final = cloth[start:cloth.index(final_call, start) + len(final_call)]
        function = OWNER.function(lighting, "void commonClothLightSet(cLight** list, int n, Vec* pos, f32 size)\n{")
        ambient = OWNER.function(lighting, "void lightSetAmbient(GXColor* col0)\n{")
        table = lighting[lighting.index("#define LIGHT_FUNC_TABLE"):lighting.index("static GXLightObj lightObjBlack;")]
        code = r'''
#include <algorithm>
#include <cassert>
#include <cstring>
#include <initializer_list>
#include <string>
#include <vector>
using u8=unsigned char;using u32=unsigned;using f32=float;using Mtx=float[3][4];
struct Vec{float x,y,z;};struct GXColor{u8 r,g,b,a;};struct GXLightObj{unsigned word;};
struct cLight{unsigned xD;void getPos(Vec*){assert(false);}};struct cEm{};struct GXTexObj{};
struct Cloth{unsigned x74;GXColor color;};struct Env{GXColor AmbientScr{255,255,255,255};};
struct LightManager{Env e;Env* getEnvPtr(){return &e;}}LightMgr;
struct Global{struct{Mtx v_mat;}Cam;}global_value,*pG=&global_value;
struct Log{void err(int,int,const char*,unsigned){assert(false);}}logger,*pLog=&logger;
GXLightObj lightObjBlack;Vec obj_pos;int obj_flag;float obj_size;GXColor last_ambient{},last_material{};
struct Call{std::string name;std::vector<int> args;};std::vector<Call> calls;
void record(const char* name,std::initializer_list<int> args){calls.push_back({name,args});}
bool saw(const char* name,std::initializer_list<int> args){for(const auto& call:calls)
 if(call.name==name&&call.args==std::vector<int>(args))return true;return false;}
void GXLoadLightObjImm(GXLightObj* obj,unsigned mask){assert(obj==&lightObjBlack&&mask==1);record("black",{1});}
void GXSetChanCtrl(int a,int b,int c,int d,unsigned e,int f,int g){record("channel",{a,b,c,d,int(e),f,g});}
void GXSetChanAmbColor(int channel,GXColor value){assert(channel==4);last_ambient=value;}
void GXSetChanMatColor(int channel,GXColor value){assert(channel==4);last_material=value;}
void GXSetNumChans(int n){record("channels",{n});}
void ISet(int& value,int n){value=n;}
void PSMTXMultVec(const Mtx,const Vec*,Vec*){assert(false);}
void GXInitLightPos(GXLightObj*,float,float,float){assert(false);}
void GXInitLightDir(GXLightObj*,float,float,float){assert(false);}
void lightSetColor(GXLightObj*,cLight*,cEm*){assert(false);}
void lightSetLocalAmb(cLight*,GXColor*){assert(false);}
void memclr_asm(void*,unsigned){assert(false);}
void lightSetConstant(cLight*,GXLightObj*){assert(false);}
void lightSetLinear(cLight*,GXLightObj*){assert(false);}
void lightSetQuadratic(cLight*,GXLightObj*){assert(false);}
void lightSetSpotlight(cLight*,GXLightObj*){assert(false);}
void lightSetCustom(cLight*,GXLightObj*){assert(false);}
void lightSetParallel(cLight*,GXLightObj*){assert(false);}
void lightSetSpotQuad(cLight*,GXLightObj*){assert(false);}
#define MAX(a,b) ((a)>(b)?(a):(b))
#define GXSetCullMode(...) record("cull",{__VA_ARGS__})
#define GXSetZMode(...) record("depth",{__VA_ARGS__})
#define GXSetTevColorIn(...) record("color-in",{__VA_ARGS__})
#define GXSetTevColorOp(...) record("color-op",{__VA_ARGS__})
#define GXSetTevAlphaIn(...) record("alpha-in",{__VA_ARGS__})
#define GXSetTevAlphaOp(...) record("alpha-op",{__VA_ARGS__})
#define GXSetTevOrder(...) record("order",{__VA_ARGS__})
#define GXSetNumTexGens(...) record("texgens",{__VA_ARGS__})
#define GXSetTexCoordGen2(...) record("texcoord",{__VA_ARGS__})
#define GXSetBlendMode(...) record("blend",{__VA_ARGS__})
#define GXSetAlphaCompare(...) record("alpha-test",{__VA_ARGS__})
#define GXSetZCompLoc(...) record("z-location",{__VA_ARGS__})
#define GXSetTevOp(...) record("stage-op",{__VA_ARGS__})
#define GXSetNumTevStages(...) record("stages",{__VA_ARGS__})
void GXLoadTexObj(GXTexObj*,int index){record("texture",{index});}
void GXLoadTlut(void*,int){assert(false);}
void GXLoadTexMtxImm(const Mtx,int index,int type){assert(index==0x1e&&type==1);}
''' + table + "\n" + ambient + "\n" + function + "\nvoid source_stages(Cloth* pCL){Mtx texMtx{};GXTexObj object;GXTexObj* tex=&object;void* tex2=&object;void* tlut=nullptr;int nStages;\n" + initial + final + r'''
}
int main(){Cloth c{0,{64,128,192,255}};cLight* lights[8]{};Vec pos{1,2,3};
 commonClothLightSet(lights,8,&pos,4);assert(obj_flag==0&&obj_pos.x==1&&obj_size==4);
 assert(saw("black",{1})&&saw("channel",{0,1,0,0,1,2,1})&&saw("channel",{2,0,0,0,0,2,2}));
 assert(last_ambient.r==255&&last_ambient.g==255&&last_ambient.b==255);
 assert(last_material.r==255&&last_material.a==255);
 GXSetChanMatColor(4,c.color);assert(!std::memcmp(&last_material,&c.color,4));source_stages(&c);
 assert(saw("cull",{0})&&saw("depth",{1,3,1})&&!saw("depth",{1,3,0}));
 assert(saw("color-in",{0,15,8,10,15})&&saw("color-op",{0,0,0,2,1,0}));
 assert(saw("alpha-in",{0,7,4,5,7})&&saw("alpha-op",{0,0,0,2,1,0}));
 assert(saw("order",{0,0,0,4})&&saw("order",{1,0,1,4})&&saw("stage-op",{1,0}));
 assert(saw("texcoord",{0,1,4,30,0,125})&&saw("blend",{1,4,5,0})&&saw("stages",{2}));
 assert(saw("alpha-test",{4,4,1,4,255})&&saw("z-location",{0}));
 // Independent integer TEV arithmetic for these captured add/zero-bias
 // multiply stages: coefficient255 expands to256, SCALE4 precedes rounding.
 for(unsigned raster=0;raster<256;++raster){
  const unsigned first=std::min(255U,(255U*(raster+(raster>>7))*4U+128U)>>8);
  assert((first==255)==(raster>=64));
  if(raster>=64)for(unsigned secondary=0;secondary<256;++secondary){
   const unsigned second=(secondary*(first+(first>>7))+128U)>>8;
   assert(second==secondary);assert(first>4&&first<=255);
  }
 }
}
'''
        self.build_run("#pragma once\n", code, full_owner=False)

    def test_actual_producer_to_package_upload_and_material(self):
        pixels = [bytes([255]) * 128, bytes((n * 37 + n // 7) & 255 for n in range(128))]
        with tempfile.TemporaryDirectory(prefix="re4dc-cloth-producer11-") as td:
            tmp = Path(td)
            source = tmp / "source"
            source.mkdir()
            for n, data in enumerate(pixels):
                (source / f"material{n}.tpl").write_bytes(TPL_TEST.make_tpl([(8, 8, 4, data)]))
            packages = []
            for rounded in (False, True):
                old_round = TPL.PACK_ROUND
                try:
                    TPL.PACK_ROUND = rounded
                    out = tmp / f"native{int(rounded)}"
                    report = UI.prepare(source, ["material0.tpl", "material1.tpl"], out)
                finally:
                    TPL.PACK_ROUND = old_round
                self.assertEqual(report["errors"], [])
                self.assertEqual(report["unique_images"], 2)
                current = []
                for entry in report["entries"]:
                    blob = (out / (entry["key"] + ".re4tex")).read_bytes()
                    descriptor = TPL.TEXTURE.unpack_from(blob, TPL.HEADER.size)
                    self.assertEqual((descriptor[1:4], descriptor[5:]), ((8, 8, TPL.FORMAT_RGB565), (128, 0, TPL.PAYLOAD_TWIDDLED, 0)))
                    n = int(entry["file"][8])
                    expected = [0] * 64
                    for y in range(8):
                        for x in range(8):
                            gc = (((y // 4) * 2 + x // 4) * 16 + y % 4 * 4 + x % 4) * 2
                            index = sum(((y >> b) & 1) << (2 * b) | ((x >> b) & 1) << (2 * b + 1) for b in range(3))
                            expected[index] = int.from_bytes(pixels[n][gc:gc + 2], "big")
                    self.assertEqual(blob[descriptor[4]:], struct.pack("<64H", *expected))
                    current.append(blob)
                if packages:
                    self.assertEqual(current, packages)
                packages = current
            stub, code = producer_fixture(packages, pixels)
            for sanitize in (False, True):
                with self.subTest(sanitize=sanitize):
                    output = self.build_run(stub, code, sanitize=sanitize, full_package=True)
                    self.assertIn("actual prepare -> Package", output)

    def test_rgb565_boundaries_and_preexisting_producer_bytes(self):
        old_round = TPL.PACK_ROUND
        try:
            for rounded in (False, True):
                TPL.PACK_ROUND = rounded
                for word in range(65536):
                    self.assertEqual(TPL._pack_565((*TPL._expand_565(word), 255)), word)
        finally:
            TPL.PACK_ROUND = old_round
        raw = bytes((n * 17) & 255 for n in range(64))
        encoded = TPL_TEST.make_tpl([(3, 5, 4, raw)])
        image = TPL.parse_tpl(encoded)[0]
        self.assertEqual(len(image.data), 64)
        decoded = TPL.decode_image(image)
        self.assertEqual(len(decoded), 15)
        for y in range(5):
            for x in range(3):
                byte=((y//4)*16+(y%4)*4+x)*2
                self.assertEqual(decoded[y*3+x], (*TPL._expand_565(int.from_bytes(raw[byte:byte+2], "big")), 255))
        with self.assertRaises(ValueError):
            TPL.parse_tpl(encoded[:-1])
        with self.assertRaises(struct.error):
            TPL.decode_image(TPL.TplImage(3, 5, 4, raw[:-1]))
        with tempfile.TemporaryDirectory(prefix="re4dc-cloth-converter-off-") as td:
            path = Path(td) / "baseline.py"
            path.write_bytes(subprocess.check_output(["git", "show", BASE + ":port/dreamcast/tools/convert_tpl.py"], cwd=REPO))
            spec = importlib.util.spec_from_file_location("cloth_converter_baseline", path)
            previous = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = previous
            spec.loader.exec_module(previous)
            try:
                for rounded in (False, True):
                    TPL.PACK_ROUND = previous.PACK_ROUND = rounded
                    for fmt in (0, 1, 2, 3, 6, 8, 9, 14):
                        for width, height in ((1, 1), (8, 8), (13, 5)):
                            size=previous._expected_image_size(width,height,fmt)
                            palette=bytes((i*13)&255 for i in range(512)) if fmt in (8,9) else None
                            image=TPL.TplImage(width,height,fmt,bytes((i*19)&255 for i in range(size)),1 if palette else None,palette)
                            self.assertEqual(TPL.decode_image(image),previous.decode_image(image))
                            for twiddle in (False,True):
                                args=([image],[TPL.MaterialBinding("source",0,None)])
                                options=dict(twiddle=twiddle,pad_to_power_of_two=True,source_intensity_alpha=True)
                                self.assertEqual(TPL.build_package(*args,**options),previous.build_package(*args,**options))
                    for fmt in (5,7,10,11,12,13,15):
                        for implementation in (TPL,previous):
                            with self.assertRaisesRegex(ValueError,"unsupported TPL image format"):
                                implementation._expected_image_size(8,8,fmt)
            finally:
                TPL.PACK_ROUND=old_round
                del sys.modules[spec.name]

    def test_default_off_actual_adapter_native_and_full_gx_objects(self):
        baseline_source = subprocess.check_output(["git", "show", BASE + ":src/game/cloth.cpp"], cwd=REPO, text=True)
        baseline_gx = subprocess.check_output(["git", "show", BASE + ":port/dreamcast/game/platform/gx_stub.cpp"], cwd=REPO, text=True)
        with tempfile.TemporaryDirectory(prefix="re4dc-cloth-material11-off-") as td:
            tmp = Path(td)
            (tmp / "dc").mkdir()
            old_inc = tmp / "baseline"
            old_inc.mkdir()
            for name in ("native_effect_strip21.inc", "native_cloth_sheet11.inc", "native_cloth_sheet11.hpp"):
                (old_inc / name).write_bytes(subprocess.check_output(["git", "show", BASE + ":port/dreamcast/game/platform/include/" + name], cwd=REPO))
            stub, current = TILES.actual_source_fixture()
            _, previous = TILES.actual_source_fixture(baseline_source)
            (tmp / "dc/pvr.h").write_text(stub)
            cpp = tmp / "unit.cpp"
            obj = tmp / "unit.o"
            flags = ["-std=c++20", "-O2", "-g0", "-fpermissive", "-w", "-DRE4DC_FX_STRIP21=1",
                     "-DRE4DC_CLOTH_NATIVE=1", "-DRE4DC_NATIVE_DRAW_OUTCOMES=1", "-DRE4DC_CLOTH_SHEET11=1",
                     "-DRE4DC_CLOTH_TILES11=1", "-DRE4DC_PS2_UPLOAD_INCARNATION=1", "-DRE4DC_UI_HANDLES=1",
                     "-DRE4DC_TA_DIRECT=1", "-DRE4DC_EFFECT_SPRITE_MAX=256", "-I" + str(tmp), "-I" + str(ROOT / "room")]
            tokens = re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|\w+|[^\s]')
            objects, preprocessed = [], []
            for source, includes, controls in ((previous, old_inc, []), (current, INC, []),
                                              (current, INC, ["-DRE4DC_CLOTH_MATERIAL11=0"])):
                cpp.write_text(source.split("int main(){", 1)[0])
                command = ["g++", *flags, *controls, "-I" + str(includes), "-I" + str(INC)]
                pp = subprocess.run([*command, "-E", "-P", str(cpp)], capture_output=True, text=True)
                self.assertEqual(pp.returncode, 0, pp.stderr)
                preprocessed.append(tokens.findall(pp.stdout))
                build = subprocess.run([*command, "-c", str(cpp), "-o", str(obj)], capture_output=True, text=True)
                self.assertEqual(build.returncode, 0, build.stderr)
                objects.append(obj.read_bytes())
            self.assertEqual(preprocessed[0], preprocessed[1])
            self.assertEqual(preprocessed[0], preprocessed[2])
            self.assertEqual(objects[0], objects[1])
            self.assertEqual(objects[0], objects[2])
            for profile in ([], ["-DRE4DC_COPY_LEAN=1"], ["-DRE4DC_D349_RENDERER_STACK=1"]):
                objects, preprocessed = [], []
                for source, controls in ((baseline_gx, []), ((ROOT / "game/platform/gx_stub.cpp").read_text(), []),
                                         ((ROOT / "game/platform/gx_stub.cpp").read_text(), ["-DRE4DC_CLOTH_MATERIAL11=0"])):
                    command = ["g++", "-std=c++20", "-O2", "-g0", "-fpermissive", "-w", *profile, *controls,
                               "-I" + str(INC), "-I" + str(ROOT / "game/platform"), "-x", "c++", "-"]
                    pp = subprocess.run([*command, "-E", "-P"], input=source, capture_output=True, text=True, cwd=ROOT / "game/platform")
                    self.assertEqual(pp.returncode, 0, pp.stderr)
                    preprocessed.append(tokens.findall(pp.stdout))
                    build = subprocess.run([*command, "-c", "-o", str(obj)], input=source, capture_output=True, text=True, cwd=ROOT / "game/platform")
                    self.assertEqual(build.returncode, 0, build.stderr)
                    objects.append(obj.read_bytes())
                self.assertEqual(preprocessed[0], preprocessed[1])
                self.assertEqual(preprocessed[0], preprocessed[2])
                self.assertEqual(objects[0], objects[1])
                self.assertEqual(objects[0], objects[2])

    def test_effective_make_scope_strict_values_and_dependencies(self):
        with tempfile.TemporaryDirectory(prefix="re4dc-cloth-material11-make-") as td:
            tmp = Path(td)
            (tmp / "Makefile.rules").write_text("")
            targets = ["obj/src/game/cloth.o", "obj/platform/native_ui.o", "obj/platform/gx_stub.o",
                       "obj/src/game/esp_sub.o", "obj/src/game/trans.o"]
            make = ["make", "--no-print-directory", "-f", "Makefile", "-n", "KOS_BASE=" + str(tmp)]
            deps = ["EFFECT_SPRITES=1", "FX_STRIP21=1", "CLOTH_NATIVE=1", "NATIVE_DRAW_OUTCOMES=1",
                    "PS2_UPLOAD_INCARNATION=1", "CLOTH_SHEET11=1", "MODEL_DRAW_PLANS=1", "PLAN_OWNER_SCOPED=1"]
            outputs = []
            for value in (None, "0", "1"):
                controls = [] if value is None else ["CLOTH_MATERIAL11=" + value]
                run = subprocess.run([*make, *targets, *deps, *controls], capture_output=True, text=True, cwd=ROOT / "game")
                self.assertEqual(run.returncode, 0, run.stderr)
                lines = [line for line in run.stdout.splitlines() if line.startswith("kos-c++")]
                self.assertEqual(len(lines), len(targets))
                outputs.append(lines)
            self.assertEqual(outputs[0], outputs[1])
            for i, line in enumerate(outputs[2]):
                self.assertEqual(line.count("-DRE4DC_CLOTH_MATERIAL11=1"), int(i < 3))
                if i < 2:
                    self.assertIn("-DRE4DC_PLAN_OWNER_SCOPED=1", line)
            for value in ("", "0 1", "1 1", "2", "-1"):
                run = subprocess.run([*make, targets[0], *deps, "CLOTH_MATERIAL11=" + value], capture_output=True, text=True, cwd=ROOT / "game")
                self.assertNotEqual(run.returncode, 0)
                self.assertIn("CLOTH_MATERIAL11 must be", run.stderr)
            for dependency in ("CLOTH_SHEET11", "PLAN_OWNER_SCOPED"):
                run = subprocess.run([*make, targets[0], *deps, "CLOTH_MATERIAL11=1", dependency + "=0"], capture_output=True, text=True, cwd=ROOT / "game")
                self.assertNotEqual(run.returncode, 0)
                self.assertIn("CLOTH_MATERIAL11 needs", run.stderr)


if __name__ == "__main__":
    unittest.main()
