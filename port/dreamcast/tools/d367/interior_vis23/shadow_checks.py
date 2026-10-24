#!/usr/bin/env python3
"""Actual KOS and hot/cold cheap-shadow header invariance; host only."""
from pathlib import Path
import re,hashlib,tempfile,subprocess,json
ROOT=Path(__file__).resolve().parents[5];KOS=Path('/root/work/kos-re4dc-d367')
def function(s,marker):
 start=s.index(marker);b=s.index('{',start);n=1;i=b+1
 while n:
  n+=(s[i]=='{')-(s[i]=='}');i+=1
 return s[start:i]
ph=(KOS/'kernel/arch/dreamcast/include/dc/pvr.h').read_text();hh=(KOS/'kernel/arch/dreamcast/include/dc/pvr/pvr_header.h').read_text();legacy=(KOS/'kernel/arch/dreamcast/include/dc/pvr/pvr_legacy.h').read_text();reg=(KOS/'include/kos/regfield.h').read_text();prim=(KOS/'kernel/arch/dreamcast/hardware/pvr/pvr_prim.c').read_text();ui=(ROOT/'port/dreamcast/game/platform/native_ui.cpp').read_text();tex=(ROOT/'port/dreamcast/room/texture_package.cpp').read_text();th=(ROOT/'port/dreamcast/room/texture_package.hpp').read_text()
for label,s in [('pvr.h',ph),('pvr_header.h',hh),('pvr_legacy.h',legacy),('regfield.h',reg),('pvr_prim.c',prim)]:print('KOS_SHA256',label,hashlib.sha256(s.encode()).hexdigest())
enums='\n'.join(re.findall(r'typedef enum\s+\w+\s*\{.*?\}\s*\w+;',hh+'\n'+ph,re.S))
macros='\n'.join(line.split('/**')[0] for s in (ph,legacy) for line in s.splitlines() if re.match(r'#define PVR_',line))
reg=reg.replace('#include <kos/cdefs.h>','').replace('__BEGIN_DECLS','').replace('__END_DECLS','')
cxt=ph[ph.index('typedef struct {\n    pvr_list_t'):ph.index('} pvr_poly_cxt_t;')+len('} pvr_poly_cxt_t;')]
hdr=hh[hh.index('typedef struct pvr_poly_hdr_cmd'):hh.index('_Static_assert(sizeof(pvr_poly_hdr_t)')]
constants='\n'.join(re.findall(r'inline constexpr std::uint32_t\s+\w+\s*=.*?;',th))
prefix='''#include <cassert>\n#include <cstdint>\n#include <cstring>\n#include <cstdio>\nusing pvr_ptr_t=uint32_t;using pvr_txr_ptr_t=uint32_t;\n#define assert_msg(c,m) assert(c)\n#define dcache_alloc_line_with_value(dst,v) ((dst)->cmd=(v))\n'''+reg+'\n'+enums+'\n'+macros+'\n'+cxt+'\n'+hdr+'''\nstatic pvr_txr_ptr_t to_pvr_txr_ptr(pvr_ptr_t addr){return (addr&0x7fffffU)>>3;}\n'''+function(prim,'void pvr_poly_compile(').replace('void pvr_poly_compile(', 'void __real_pvr_poly_compile(')+'\n'+function(prim,'void pvr_poly_cxt_txr(')+'''\nnamespace re4dc::texture {\n'''+constants+'''\nstruct Texture {unsigned width,height,format,flags,payload;};\n'''+function(tex,'std::uint32_t pvr_format(')+'''\n}\nstruct Package{re4dc::texture::Texture t{256,256,0,4,2};pvr_ptr_t pvr_texture(unsigned)const{return 0xa4000020U;}};\nstruct Entry{Package package;};\nunsigned fog_value=1;unsigned re4dc_ps2_world_fog(){return fog_value;}\nunsigned model_header_builds=0,re4dc_mv_receiver=0,mv_receivers=0;bool ui_order=false;\n#define RE4DC_TSP_W(t) ((t).width)\n#define RE4DC_TSP_H(t) ((t).height)\n'''
marker='pvr_poly_hdr_t header;pvr_poly_compile(&header,&c);++model_header_builds;'
end=ui.rindex(marker);start=ui.rfind('    pvr_poly_cxt_t c;',0,end)
cold=ui[start:end+len(marker)]
mods=[]
for m in re.finditer(r'#if RE4DC_MV_SHADOWS\n\s*if\(re4dc_mv_receiver && list==PVR_LIST_OP_POLY',ui):
 e=ui.index('++mv_receivers;}',m.start())+len('++mv_receivers;}');e=ui.index('#endif',e)+len('#endif');mods.append(ui[m.start():e])
assert len(mods)==2
prefix+='\n#define RE4DC_HDR_PROBE(d,k) ((void)0)\n'+function(ui,'extern "C" void __wrap_pvr_poly_compile(')+'\n#define pvr_poly_compile __wrap_pvr_poly_compile\n'
code=prefix+'\npvr_poly_hdr_t cold(const unsigned* k,Entry* handle){const auto& t=handle->package.t;const unsigned pass=k[4];const pvr_list_t list=PVR_LIST_OP_POLY;\n'+cold+'\nreturn header;}\n'
for i,block in enumerate(mods):code+='\npvr_poly_hdr_t final'+str(i)+'(pvr_poly_hdr_t header,pvr_list_t list){\n'+block+'\nreturn header;}\n'
code+=r'''
unsigned checks=0;
#define CHECK(c) do {++checks;assert(c);}while(0)
int main(){
 unsigned k[6]={0x33ea067e,0x3e26baf5,512,256,0,2};Entry e;
 for(unsigned fog=0;fog<2;fog++)for(unsigned cull:{0U,2U}){
 fog_value=fog;k[5]=cull;const auto base=cold(k,&e);
 CHECK(!(base.cmd&(PVR_TA_CMD_MODIFIER|PVR_TA_CMD_MODIFIERMODE)));
 CHECK(FIELD_GET(base.cmd,PVR_TA_CMD_TYPE)==PVR_LIST_OP_POLY);
 CHECK(FIELD_GET(base.mode1,PVR_TA_PM1_DEPTHCMP)==PVR_DEPTHCMP_GEQUAL);
 CHECK(FIELD_GET(base.mode1,PVR_TA_PM1_DEPTHWRITE)==PVR_DEPTHWRITE_ENABLE);
 CHECK(FIELD_GET(base.mode2,PVR_TA_PM2_SRCBLEND)==PVR_BLEND_ONE);
 CHECK(FIELD_GET(base.mode2,PVR_TA_PM2_DSTBLEND)==PVR_BLEND_ZERO);
 CHECK(!(base.mode2&PVR_TA_PM2_ALPHA));
 CHECK(FIELD_GET(base.mode2,PVR_TA_PM2_TXRALPHA)==PVR_TXRALPHA_DISABLE);
 CHECK((base.mode2&63U)==45U); // physical256x256, not logical512x256
 CHECK((base.mode3&0xf8000000U)==0xc8000000U); // mip|VQ|RGB565
 for(unsigned receiver=0;receiver<2;receiver++){
 re4dc_mv_receiver=receiver;auto a=final0(base,PVR_LIST_OP_POLY),b=final1(base,PVR_LIST_OP_POLY);
 CHECK(!std::memcmp(&a,&b,16));CHECK((a.cmd^base.cmd)==(receiver?PVR_TA_CMD_MODIFIER:0));
 CHECK(a.mode1==base.mode1);CHECK(a.mode2==base.mode2);CHECK(a.mode3==base.mode3);
 CHECK(!(a.cmd&PVR_TA_CMD_MODIFIERMODE));
 }
 re4dc_mv_receiver=1;ui_order=true;auto a=final0(base,PVR_LIST_OP_POLY);CHECK(!std::memcmp(&a,&base,16));ui_order=false;
 a=final1(base,PVR_LIST_TR_POLY);CHECK(!std::memcmp(&a,&base,16));
 std::printf("HEADER fog=%u cull=%u %08x %08x %08x %08x\n",fog,cull,base.cmd,base.mode1,base.mode2,base.mode3);
 }
 std::printf("PASS real KOS compiler/cxt + actual cold header and both final modifier blocks: %u checks\n",checks);
}
'''
code=code.replace('#include <cstdio>','#include <cstdio>\n#include <initializer_list>')
# Keep the source fixture available in RAM for the primary reviewer; compiler output is temporary.
Path('/dev/shm/iv23-mv-review.cpp').write_text(code)
print('FIXTURE_SHA256',hashlib.sha256(code.encode()).hexdigest())
print('TOOL_SHA256',hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
print('NATIVE_UI_SHA256',hashlib.sha256(ui.encode()).hexdigest())
with tempfile.TemporaryDirectory(prefix='iv23-mv-review-',dir='/dev/shm') as td:
 out=Path(td)/'review'
 flags=['-DRE4DC_TEX_MIP_DADJ=3','-DRE4DC_PT_BLEND_FIX=0','-DRE4DC_MV_SHADOWS=1','-DRE4DC_UI_POLY_ORDER=1','-DRE4DC_CAST_MIPMAP=1','-DRE4DC_NATIVE_FOG=1','-DRE4DC_PS2_WORLD_FOG_SOURCE=1']
 subprocess.run(['g++','-std=c++17','-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer',*flags,'/dev/shm/iv23-mv-review.cpp','-o',str(out)],check=True)
 subprocess.run([str(out)],check=True)


