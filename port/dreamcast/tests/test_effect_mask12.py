#!/usr/bin/env python3
"""Actual ESP producer/header/result/FIFO mask class, synthetic source/devices.

Host types/FP and captured context fields are not target/GPU image acceptance.
No assets or SDK execution. Existing GX sampler functions link as a host TU.
"""
import argparse
import difflib
import hashlib
import importlib.util
import json
import os
import struct
import sys
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('mask12_packets',HERE/'test_effect_outcomes03.py')
packets=importlib.util.module_from_spec(spec);spec.loader.exec_module(packets)
gate=packets.gate
ROOT,INC=gate.ROOT,gate.INCLUDE
BASE='15308a90d35b9b30e99ae320eaa42b29cfaf7f6b' # two clean requested dependency merges


def fixture(base=None):
    text=packets.fixture(base)
    text=gate.replace_once(text,'format=0x40000000,payload=1;','format=0,payload=1,flags=0,reserved_0=0;')
    if base is not None:
        native=gate.production(gate.NATIVE,base)
        wrapper=gate.extract.function(native,'extern "C" int re4dc_effect_sprite(')
        result=gate.definition(native,'extern "C" re4dc::NativeDrawResult re4dc_effect_sprite_result(')
        text=gate.replace_once(text,wrapper,result+'\n'+wrapper)
    # Capture the actual PVR texture-alpha field, with KOS's real enum values.
    text=gate.replace_once(text,'c->txr.uv_clamp<<16};','c->txr.uv_clamp<<16|c->txr.alpha<<24};')
    text=gate.replace_once(text,'struct Package {','''unsigned handle_reset=1,load_action12=0,trim_calls12=0;bool cold12=false;
struct Package {
    unsigned sample12=0xff123456;
    bool complete12=true;struct Header12{unsigned texture_count=1,flags=0;}h;
    bool upload_complete()const{return complete12;}const Header12& header()const{return h;}
''')
    old=gate.extract.function(text,'Entry* resolve(')
    new=old.replace('assert(!mask&&pin);','assert(!mask&&pin);if(cold12){cold12=false;++load_opens;}')
    new=new.replace('entries[index].frame=frame;return &entries[index];',r'''entries[index].frame=frame;
    const unsigned action=load_action12;load_action12=0;
    if(action==1)++frame;if(action==2)++handle_reset;if(action==3)entries[index].valid=false;
    if(action==4)entries[index].package.complete12=false;if(action==5)stream_aborted=true;
    if(action==6)entries[index].frame=frame-1;if(action==7)frame_ready=false;
    if(action==8)entries[index].package.h.texture_count=2;
    if(action==9)entries[index].package.address=nullptr;
    if(action==10)++entries[index].key.id;
    return &entries[index];''')
    assert new!=old;text=text.replace(old,new)
    if base is None:
        native=gate.production(gate.NATIVE)
        old=gate.definition(native,'extern "C" re4dc::NativeDrawResult re4dc_effect_sprite_result(')
        extra=gate.definition(native,'static re4dc::NativeDrawResult effectSpriteMaterial12(')
        extra+='\n'+old+'\n'+gate.definition(native,'extern "C" re4dc::NativeDrawResult re4dc_effect_masked_sprite12_result(')
        text=gate.replace_once(text,old,'#if RE4DC_EFFECT_MASK12\n'+extra+'\n#else\n'+old+'\n#endif')
    return text


def producer():
    source=(ROOT/'src/game/esp_sub.cpp').read_text()
    typed=source.index('static int EspSpriteEligible(cEsp* esp,bool')
    start=source.rfind('#if defined(RE4DC_ESP1B_GRID03)',0,source.index('#if defined(RE4DC_EFFECT_MASK12)',source.index('extern "C" int re4dc_rtt_capturing')))
    eligibility=source[start:source.index('#if RE4DC_PS2FX_DRAW',typed)]
    return r'''
using u8=unsigned char;using u16=unsigned short;using s8=signed char;using u32=unsigned;using f32=float;using Mtx=float[3][4];
struct GXTexObj{u32 dummy[8];};static_assert(sizeof(GXTexObj)==32);
extern "C" void GXInitTexObj(GXTexObj*,void*,u16,u16,int,int,int,u8);
extern "C" void GXInitTexObjLOD(GXTexObj*,int,int,float,float,float,u8,u8,int);
struct TEXHeader{void* data;unsigned width,height,format;};
struct CLUT{void* data;unsigned format,numEntries;};
struct TEXDescriptor{TEXHeader* textureHeader;CLUT* CLUTHeader;};
struct TEXPalette{unsigned numDescriptors;TEXDescriptor* descriptors;};
struct EspTexWk{unsigned Owner=0;TEXPalette* pTpl=nullptr;Mtx mtx{};GXTexObj* pTexObj=nullptr;unsigned nTexObj=0;};
struct System{EspTexWk Esp_tex_tbl[3];}system12,*g_pEspSys=&system12;
struct Vec{float x,y,z;};
struct Parent12{Mtx mat{};}parent12;
struct {unsigned Frame_cnt=1;struct{Mtx v_mat{};}Cam;unsigned Status_flg[2]{};}game12,*pG=&game12;
struct cEsp{unsigned m_Id=0,m_Flg=0,m_Parts_no=0xff,m_Tool_flg=0x4000,m_Shimmer_type=0;
 unsigned m_Shimmer_pow=0;float m_Size_base_x=1,m_Size_base_y=1,m_Size_mul=1,m_Col_a=192;
 Vec m_Pos{},m_Ang{};Parent12* parent=&parent12;int ChannelSet();void CommonStateSet(){}
 unsigned m_Tex_id=0,m_Ptn_no=0,m_MaskTex_id=1,m_MaskPtn_no=0,xA4=1,xA5=4,xA6=5;
 struct{unsigned owner=0,Core_flg=0;}info;Mtx m_Mat{};};
void EspCommonTrans(cEsp*);using EspTransFunc=void(*)(cEsp*);
TEXHeader base_headers12[2]{{(void*)1,64,64,14},{(void*)2,64,64,14}};
TEXHeader mask_headers12[2]{{(void*)3,16,32,4},{(void*)4,8,8,4}};
TEXDescriptor base_desc12[2]{{&base_headers12[0],nullptr},{&base_headers12[1],nullptr}};
TEXDescriptor mask_desc12[2]{{&mask_headers12[0],nullptr},{&mask_headers12[1],nullptr}};
TEXPalette base_palette12{2,base_desc12},mask_palette12{2,mask_desc12};GXTexObj base_objects12[2];
TEXDescriptor* TEXGet(TEXPalette* p,unsigned i){return i<p->numDescriptors?&p->descriptors[i]:nullptr;}
struct{u8 r=128,g=64,b=32,a=192;}s_effect_col;
void projection12(float* p){const float value[]={0,1,0,1,0,-.01f,-1.01f};std::memcpy(p,value,sizeof value);}
void viewport12(float* p){const float value[]={0,0,640,480,0,1};std::memcpy(p,value,sizeof value);}
#define RE4DC_FX_FLIP_PTN(p,n) (p)
#define RE4DC_GXF_GET_PROJECTION(p) projection12(p)
#define RE4DC_GXF_GET_VIEWPORT(p) viewport12(p)
bool level_accept12=true;unsigned level_calls12;
int FxLevelSprite(cEsp*,Re4dcEffectSprite*){++level_calls12;return level_accept12;}
''' + eligibility+'\nEspTransFunc EspTransTbl[0xFF]{};\n'+gate.definition(source,'static re4dc::NativeDrawResult EspSpriteEmitResult03(')


def routing():
    spec=importlib.util.spec_from_file_location('mask12_grid',HERE/'test_esp1b_grid03.py')
    grid=importlib.util.module_from_spec(spec);spec.loader.exec_module(grid)
    source=(ROOT/'src/game/esp_sub.cpp').read_text()
    text=grid.routing_fixture().split('extern "C" int re4dc_esp_strip21_eligible(',1)[0]
    text=gate.replace_once(text,'struct{struct{Mtx v_mat{};}Cam;unsigned Status_flg[2]{};}global03,*pG=&global03;','')
    text=gate.replace_once(text,'int cEsp::ChannelSet(){++channel_calls03;return channel_ok03;}',
                           'int cEsp::ChannelSet(){++channel_calls03;s_effect_col.a=m_Col_a;return channel_ok03 && s_effect_col.a;}')
    text=text.replace('void EspSpriteEmit(cEsp*){++flat_calls03;}','')
    text=text.replace('sys03.Esp_tex_tbl','system12.Esp_tex_tbl')
    support=r'''
struct Log12{void err(int,int,const char*,...){throw std::runtime_error("unexpected legacy source error");}}log12,*pLog=&log12;
void Esp1b_SpTrans(cEsp*){throw std::runtime_error("masked class entered legacy grid");}
void PSMTXMultVec(const Mtx m,const Vec* a,Vec* o){const Vec value{
 m[0][0]*a->x+m[0][1]*a->y+m[0][2]*a->z+m[0][3],
 m[1][0]*a->x+m[1][1]*a->y+m[1][2]*a->z+m[1][3],
 m[2][0]*a->x+m[2][1]*a->y+m[2][2]*a->z+m[2][3]};*o=value;}
#if RE4DC_ESP1B_GRID03
static re4dc::NativeDrawResult Esp1bGridDraw03(cEsp*){throw std::runtime_error("masked class entered grid producer");}
#endif
'''
    begin=source.index('void EspCommonTrans(cEsp* esp)\n{')
    common=source[begin:source.index('// Heat shimmer sprite:',begin)]
    return support+text+'\n'+gate.definition(source,'static void EspSpriteEmit(')+'\n'+common


def run(command,out,label,*,input=None,success=True,cwd=ROOT):
    result=subprocess.run(command,input=input,capture_output=True,text=True,cwd=cwd,
                          env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1'))
    (out/(label+'.log')).write_text(result.stdout+result.stderr)
    if success and result.returncode:raise RuntimeError(label+': '+result.stdout+result.stderr)
    return result


def make_checks(out):
    kos=out/'kos-make';kos.mkdir();(kos/'Makefile.rules').write_text('')
    targets=['obj/src/game/esp_sub.o','obj/platform/native_ui.o','obj/platform/gx_stub.o','obj/src/game/esp1b.o','obj/src/game/cloth.o']
    parents=['EFFECT_SPRITES=1','EFFECT_LEAN=1','NATIVE_DRAW_OUTCOMES=1','FX_STRIP21=1','D349_RENDERER_STACK=1','PVR_STREAM=1','UI_HANDLES=1']
    command=['make','--no-print-directory','-n','-f','Makefile','KOS_BASE='+str(kos),*parents,*targets]
    lines=[]
    for value in (None,'0','1'):
        r=run(command+([] if value is None else ['EFFECT_MASK12='+value]),out,'make-'+str(value),cwd=ROOT/'port/dreamcast/game')
        lines.append([line for line in r.stdout.splitlines() if line.startswith('kos-c++')])
    assert lines[0]==lines[1] and len(lines[2])==5
    for i,line in enumerate(lines[2]):assert line.count('-DRE4DC_EFFECT_MASK12=1')==int(i<3),line
    for i,value in enumerate(('', '2','-1','0 1','%','1%','0%','1 ','0 ')):
        r=run(command+['EFFECT_MASK12='+value],out,'make-bad-'+str(i),success=False,cwd=ROOT/'port/dreamcast/game')
        assert r.returncode and 'EFFECT_MASK12' in r.stderr
    for value in ('0','1','1 ','0 ','','1 0'):
        r=run(command+['MASK_VALUE='+value,'EFFECT_MASK12=$(MASK_VALUE)'],out,'make-expand-'+str(len(value))+'-'+value.replace(' ','_'),success=value in ('0','1'),cwd=ROOT/'port/dreamcast/game')
        if value in ('0','1'):assert [line for line in r.stdout.splitlines() if line.startswith('kos-c++')]==lines[1 if value=='0' else 2]
        else:assert r.returncode and 'EFFECT_MASK12' in r.stderr
    for name in ('EFFECT_SPRITES','EFFECT_LEAN','NATIVE_DRAW_OUTCOMES','D349_RENDERER_STACK','PVR_STREAM','UI_HANDLES'):
        r=run(command+['EFFECT_MASK12=1',name+'=0'],out,'make-dep-'+name,success=False,cwd=ROOT/'port/dreamcast/game')
        assert r.returncode
    return dict(exact_expanded_01=True,whitespace=True,dependencies=True,esp_ui_gx_only=True)


def identity(out,stub):
    rows=[]
    # Complete recovered adapter and GX TUs, SH-conditioned and host controls.
    for file in ('src/game/esp_sub.cpp','port/dreamcast/game/platform/gx_stub.cpp'):
        baseline=subprocess.check_output(['git','show',BASE+':'+file],cwd=ROOT,text=True)
        current=(ROOT/file).read_text()
        for grid in (0,1):
            args=['g++','-std=gnu++20','-fpermissive','-w','-DRE4DC_GAME','-DRE4DC_EFFECT_SPRITES=1','-DRE4DC_EFFECT_LEAN=1',
                  '-DRE4DC_FX_STRIP21=1','-DRE4DC_NATIVE_DRAW_OUTCOMES=1',f'-DRE4DC_ESP1B_GRID03={grid}',
                  '-include',str(INC/'re4dc_prelude.h'),'-I'+str(ROOT/'include'),'-I'+str(ROOT/'src'),
                  '-I'+str(INC),'-I'+str(gate.PLATFORM),'-iquote',str(ROOT/'src/game')]
            for sh in (0,1):
                pp=[]
                for arm,text,extra in (('base',baseline,[]),('absent',current,[]),('zero',current,['-DRE4DC_EFFECT_MASK12=0'])):
                    pp.append(run(args+(['-D__sh__'] if sh else [])+extra+['-E','-P','-x','c++','-'],out,
                                  f'pp-{Path(file).stem}-grid{grid}-sh{sh}-{arm}',input=text).stdout)
                assert pp[0]==pp[1]==pp[2], '\n'.join(list(difflib.unified_diff(pp[0].splitlines(),pp[1].splitlines()))[:80])
                rows.append(dict(source=file,grid=grid,sh=sh,bytes=len(pp[0])))
    for fast in (0,1):
        config=dict(gate.CONFIG,RE4DC_NATIVE_DRAW_OUTCOMES=1,RE4DC_PVR_RTT=1,RE4DC_WATER_PS2=1,RE4DC_ESP_SPRITE_FAST=fast,RE4DC_ESP_SETUP_LEAN=fast)
        header=out/f'off-fast{fast}.h';header.write_text('\n'.join(f'#define {k} {v}' for k,v in config.items()))
        pp=[];objects=[]
        for arm,base,extra in (('base',BASE,[]),('absent',None,[]),('zero',None,['-DRE4DC_EFFECT_MASK12=0'])):
            args=['g++','-std=c++20','-O2','-g0','-ffp-contract=off','-include',str(header),'-I'+str(out),'-I'+str(INC),'-I'+str(gate.PLATFORM),'-I'+str(ROOT/'port/dreamcast/room'),*extra]
            code=fixture(base)
            pp.append(run(args+['-E','-P','-x','c++','-'],out,f'off-native{fast}-{arm}-pp',input=code).stdout)
            obj=out/f'off-native{fast}-{arm}.o'
            run(args+['-c','-x','c++','-','-o',str(obj)],out,f'off-native{fast}-{arm}-object',input=code);objects.append(obj.read_bytes())
        assert pp[0]==pp[1]==pp[2] and objects[0]==objects[1]==objects[2]
        rows.append(dict(native_scaffold_fast=fast,object_sha256=hashlib.sha256(objects[0]).hexdigest()))
    gx_path=gate.PLATFORM/'gx_stub.cpp'
    baseline=subprocess.check_output(['git','show',BASE+':port/dreamcast/game/platform/gx_stub.cpp'],cwd=ROOT,text=True)
    for cloth in (0,1):
        pp=[];objects=[]
        for arm,text,extra in (('base',baseline,[]),('absent',gx_path.read_text(),[]),('zero',gx_path.read_text(),['-DRE4DC_EFFECT_MASK12=0'])):
            flags=['g++','-std=c++20','-O2','-g0','-fpermissive',f'-DRE4DC_CLOTH_MATERIAL11={cloth}',
                   '-I'+str(INC),'-I'+str(gate.PLATFORM),'-iquote',str(gate.PLATFORM),*extra]
            pp.append(run(flags+['-E','-P','-x','c++','-'],out,f'gx-object-{cloth}-{arm}-pp',input=text).stdout)
            obj=out/f'gx-object-{cloth}-{arm}.o'
            run(flags+['-c','-x','c++','-','-o',str(obj)],out,f'gx-object-{cloth}-{arm}',input=text);objects.append(obj.read_bytes())
        assert pp[0]==pp[1]==pp[2] and objects[0]==objects[1]==objects[2]
        rows.append(dict(full_gx_cloth=cloth,object_sha256=hashlib.sha256(objects[0]).hexdigest()))
    # Its real Make scope has MASK only, not sprite/outcome/UI macros. The
    # shared sampler capture must compile without activating cloth consumers.
    run(['g++','-std=c++20','-O2','-fpermissive','-DRE4DC_EFFECT_MASK12=1','-I'+str(INC),'-c',str(gx_path),
         '-o',str(out/'gx-mask-only.o')],out,'gx-mask-only-scope')
    return rows


def producer_upload(out,sanitize):
    """Real RGBA8 decode/pack and production Package upload, synthetic device."""
    spec=importlib.util.spec_from_file_location('mask12_upload',HERE/'test_cloth_material11.py')
    material=importlib.util.module_from_spec(spec);spec.loader.exec_module(material)
    tpl=material.TPL
    pixels=[((x*17+34)%256,(y*17+68)%256,170,0 if x<4 else 128) for y in range(8) for x in range(8)]
    tiled=bytearray(256)
    for y in range(8):
        for x in range(8):
            r,g,b,a=pixels[y*8+x];i=((y//4)*2+x//4)*64+(y%4*4+x%4)*2
            tiled[i:i+2]=bytes((a,r));tiled[i+32:i+34]=bytes((g,b))
    image=tpl.TplImage(8,8,tpl.GX_TF_RGBA8,bytes(tiled))
    assert tpl.decode_image(image)==pixels
    packages=[tpl.build_package([image],[tpl.MaterialBinding('mask-base',0,None)],twiddle=twiddle)[0] for twiddle in (False,True)]
    linear=[tpl._pack_4444(p) for p in pixels]
    assert all((linear[y*8+x]&0xf000)==0 and (linear[y*8+x]&0xfff)!=0 for y in range(8) for x in range(4))
    expected=struct.pack('<64H',*tpl.twiddle_16bpp(linear,8,8))
    stub,code=material.producer_fixture(packages,[bytes(tiled),bytes(tiled)])
    code=code[:code.rindex('int main(){')]
    # Emulate only the device twiddle boundary. Check exactly which source
    # words the real Package passes; production linear upload selects this API.
    code=code.replace('void pvr_txr_load_ex(const void*,void*,unsigned,unsigned,unsigned){assert(false);}',r'''
void pvr_txr_load_ex(const void* source,void* destination,unsigned w,unsigned h,unsigned){
 assert(w==8&&h==8);const auto* words=static_cast<const unsigned short*>(source);Pending copy{};copy.destination=destination;
 for(unsigned y=0;y<8;++y)for(unsigned x=0;x<8;++x){unsigned index=0;
  for(unsigned b=0;b<3;++b)index|=((y>>b)&1)<<(2*b)|((x>>b)&1)<<(2*b+1);
  std::memcpy(copy.bytes+2*index,words+y*8+x,2);}
 pending.push_back(copy);++upload_calls;
}
''')
    code+='\nconst unsigned char expected12[]={'+','.join(map(str,expected))+'};\n'
    code+=r'''
#include "effect_mask12.hpp"
static_assert(re4dc::texture::kRgb565==0 && re4dc::texture::kArgb1555==1 && re4dc::texture::kArgb4444==2);
static_assert(re4dc::texture::kPayloadLinear==0 && re4dc::texture::kPayloadTwiddled==1);
static_assert(re4dc::texture::kAlpha==1 && re4dc::texture::kBinaryAlpha==2);
int main(){
 auto* mapping=mmap(reinterpret_cast<void*>(PVR_RAM_INT_BASE+4096),4096,PROT_READ|PROT_WRITE,
                    MAP_PRIVATE|MAP_ANONYMOUS|MAP_FIXED_NOREPLACE,-1,0);
 assert(mapping==reinterpret_cast<void*>(PVR_RAM_INT_BASE+4096));
 assert(entries[0].package.adopt(package0,sizeof package0));assert(entries[1].package.adopt(package1,sizeof package1));
 for(auto& e:entries){assert(!e.package.header().flags && re4dc::effect_mask12::native_rgb(*e.package.textures()));
  assert(e.package.upload()&&e.package.upload_complete());assert(e.package.release_payload()&&e.package.payload_released());}
 assert(upload_calls==2);finish_uploads();
 for(auto& e:entries){assert(!std::memcmp(e.package.pvr_texture(0),expected12,128));e.package.close();}
 assert(!munmap(mapping,4096));std::puts("mask12 actual RGBA8 decode/pack -> Package adopt/upload/release: transparent nonzero RGB preserved; linear+twiddled PASS");
}
'''
    (out/'producer-upload.cpp').write_text(code)
    output=material.ClothMaterial11().build_run(stub,code,sanitize=sanitize,full_package=True)
    (out/'producer-upload.log').write_text(output)
    assert 'transparent nonzero RGB preserved' in output
    return dict(real_decode_pack_adopt_upload_release=True,linear_twiddled=True,transparent_nonzero_rgb=True,
                device='synthetic host allocations/copy/twiddle, not PVR rendering')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--sanitize',action='store_true')
    args=parser.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=False);(out/'dc').mkdir()
    stub=gate.PVR_STUB.replace('PVR_TXRALPHA_ENABLE=1','PVR_TXRALPHA_ENABLE=0,PVR_TXRALPHA_DISABLE=1').replace('PVR_LIST_OP_POLY=0,','PVR_ALPHA_ENABLE=1,PVR_UVCLAMP_NONE=0,PVR_LIST_OP_POLY=0,')
    (out/'dc/pvr.h').write_text(stub)
    trim=(INC/'fx_sprite_trim.inc').read_text()
    definition=gate.extract.function(trim,'int fx_trim(')
    # Observe the real trim call only; selected material must bypass it because
    # base alpha is discarded. This local copy changes no production helper.
    observed=definition.replace('{','{\n#if RE4DC_EFFECT_MASK12\n++trim_calls12;\n#endif\n',1)
    (out/'fx_sprite_trim.inc').write_text(trim.replace(definition,observed))
    source=fixture()+producer()+routing()+'\n'+(HERE/'effect_mask12_cases.cpp.in').read_text()
    cpp=out/'actual.cpp';cpp.write_text(source)
    rows=[]
    for fast,setup,grid in ((1,0,0),(1,1,0),(1,1,1),(0,0,1)):
        config=dict(gate.CONFIG,RE4DC_NATIVE_DRAW_OUTCOMES=1,RE4DC_EFFECT_MASK12=1,RE4DC_EFFECT_LEAN=1,
                    RE4DC_PVR_RTT=1,RE4DC_WATER_PS2=1,RE4DC_ESP_SPRITE_FAST=fast,RE4DC_ESP_SETUP_LEAN=setup,
                    RE4DC_ESP1B_GRID03=grid,RE4DC_FX_LEVEL=1)
        header=out/f'config-{fast}{setup}{grid}.h';header.write_text('\n'.join(f'#define {k} {v}' for k,v in config.items()))
        binary=out/f'run-{fast}{setup}{grid}'
        flags=['-std=c++20','-O2','-fpermissive','-fno-pie','-no-pie','-ffunction-sections','-fdata-sections','-Wl,--gc-sections',
               '-ffp-contract=off','-include',str(header),'-I'+str(out),'-I'+str(INC),'-I'+str(gate.PLATFORM),'-I'+str(ROOT/'port/dreamcast/room')]
        if args.sanitize:flags+=['-fsanitize=address,undefined','-fno-omit-frame-pointer']
        run(['g++',*flags,str(cpp),str(gate.PLATFORM/'gx_stub.cpp'),str(ROOT/'port/dreamcast/room/pvr_geometry.cpp'),'-o',str(binary)],out,binary.name+'-compile')
        rows.append(json.loads(run([str(binary)],out,binary.name+'-run').stdout))
    upload=producer_upload(out,args.sanitize)
    receipt=dict(status='PASS_SCOPED_OPAQUE_MASK_SOURCE_MATERIAL',base=BASE,sanitized=args.sanitize,rows=rows,producer_upload=upload,
                 make=make_checks(out),off=identity(out,stub),
                 limits=['actual source/packet/result/FIFO with synthetic registered descriptors and fake texture/device boundaries',
                         'KOS alpha enum and captured header field are tested, not real PVR interpolation/blending',
                         'RGB565 mask class only; no variable-mask, RTT, whole-EFB or private frequency claim',
                         'no SDK, runtime, cost, image or console acceptance'])
    owned=['src/game/esp_sub.cpp','port/dreamcast/game/effects30.mk',
           'port/dreamcast/game/platform/native_ui.cpp','port/dreamcast/game/platform/gx_stub.cpp']
    owned += ['port/dreamcast/game/platform/include/'+name for name in
              ('native_ui.h','native_effect_sprite03.inc','esp_sprite_outcomes03.inc','effect_mask12.hpp','esp_mask12.inc','cloth_material11_sampler.hpp')]
    owned += ['port/dreamcast/room/texture_package.cpp','port/dreamcast/room/texture_package.hpp','port/dreamcast/tools/convert_tpl.py']
    receipt['source_sha256']={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in owned}
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))


if __name__=='__main__':main()
