"""Native PAL8 admission, aligned palette lifetime, failures and OFF identity."""
import pathlib
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import compact_native_pal8 as pal8
import mipmap_twiddled as tw
from test_compact_native_pal8 import source
from test_pal4_alpha import FIXTURE,mutate,synthetic
from test_mipmap_pal4 import stubs,package as pal4_package


def joined(blobs,alias=False):
    start=48+96*len(blobs);descs=[];data=bytearray()
    for i,blob in enumerate(blobs):
        t=list(pal8.tpl.TEXTURE.unpack_from(blob,48));t[0]=('material%d'%i).encode()
        payload=blob[t[4]:t[4]+t[5]];t[4]=start+(0 if alias else len(data))
        if not alias or not i:data+=payload
        descs.append(pal8.tpl.TEXTURE.pack(*t))
    body=b''.join(descs)+data
    return pal8.tpl.HEADER.pack(pal8.tpl.MAGIC,2,48,96,len(blobs),48,start,len(data),zlib.crc32(body)&0xffffffff,7,29)+body


CHECK=r'''
void check_palette(const Package& p){
    for(unsigned i=0;i<p.header().texture_count;++i){
        const auto& t=p.textures()[i];const unsigned bank=t.reserved_0-1;
        const bool pal8=t.format==kPal8Argb4444;
        const unsigned count=pal8?256:16;
        assert(bank>=reserved_count && bank<64);
        if(pal8)assert(bank%16==0);
        const auto* colors=(const unsigned short*)((const unsigned char*)p.pvr_texture(i)+t.data_size-count*2);
        for(unsigned k=0;k<count;++k)assert(palette[bank*16+k]==expected_color(colors[k],t.format!=3));
        const unsigned tcw=pvr_format(t);
        assert((tcw&(7U<<27))==(pal8?PVR_TXRFMT_PAL8BPP:PVR_TXRFMT_PAL4BPP));
        assert(pal8?((tcw>>25)&3)==bank/16:((tcw>>21)&63)==bank);
        assert(bool(tcw&PVR_TXRFMT_VQ_ENABLE)==(t.format==3));
        assert(bool(tcw&0x80000000U)==bool(t.flags&kMipmap));
    }
    for(unsigned i=0;i<reserved_count*16;++i)assert(palette[i]==0x12345678U+i);
    assert(palette_format_calls==1 && palette_format==PVR_PAL_ARGB8888);
}
'''
MAIN=r'''
int main(int argc,char** argv){
    const auto root=std::string(argv[1]);reserved_count=8;
    for(unsigned i=0;i<1024;++i)palette[i]=0x12345678U+i;
    auto base=read_bytes(root+"/gray");Package p;
#if !RE4DC_TEX_PAL8_ALPHA
    assert(!p.adopt(base.data(),base.size()));assert(!p.open_streamed((root+"/gray").c_str()));
    assert(!allocs && !open_files && !palette_writes);return 0;
#else
    assert(p.adopt(base.data(),base.size()));assert(!p.upload() && !allocs && !palette_writes);p.close();
    assert(initialize_palettes(0xff) && initialize_palettes(0xff));
    assert(!initialize_palettes(0));
    auto chain=read_bytes(root+"/chain");assert(p.adopt(chain.data(),chain.size())==bool(RE4DC_TEX_PAL8_MIPMAP));p.close();
    if(!RE4DC_TEX_PAL8_MIPMAP){
        assert(p.adopt(base.data(),base.size()));assert(p.upload());check_palette(p);close_checked(p);
        assert(p.open_streamed((root+"/gray").c_str()));assert(p.upload());check_palette(p);close_checked(p);
        assert(!allocs && !open_files);return 0;
    }
    auto load=[&](Package& q,const char* name){assert(q.open_streamed((root+"/"+name).c_str()));inflight=true;assert(q.upload());check_palette(q);};
    Package gray,graymips,color,color2,small;
    load(gray,"gray");assert(gray.textures()[0].reserved_0==17);
    unsigned writes=palette_writes;
    load(graymips,"chain");assert(graymips.textures()[0].reserved_0==17 && palette_writes==writes);
    load(color,"color");assert(color.textures()[0].reserved_0==33);
    load(color2,"color2");assert(color2.textures()[0].reserved_0==49);
    load(small,"pal4");assert(small.textures()[0].reserved_0==9);
    assert(gray.release_payload() && graymips.release_payload());
    auto refusal=[&](const char* name){
        const unsigned before=palette_writes,live=allocs;
        assert(p.open_streamed((root+"/"+name).c_str()));assert(!p.upload());
        assert(!p.upload_complete() && !p.release_payload() && !p.upload());
        for(unsigned i=0;i<p.header().texture_count;++i)assert(p.textures()[i].reserved_0==0);
        assert(palette_writes==before);p.close();assert(allocs==live);
        check_palette(graymips);check_palette(color2);check_palette(small);
    };
    refusal("fourth");
    // Whole-transaction refusal: a free PAL4 bank must not be committed before
    // the later PAL8 descriptor discovers no aligned block.
    refusal("mixed");
    Package aliases;writes=palette_writes;load(aliases,"alias");
    assert(aliases.shared_textures()==1 && aliases.pvr_texture(0)==aliases.pvr_texture(1));
    assert(aliases.textures()[0].reserved_0==17 && aliases.textures()[1].reserved_0==17);
    assert(palette_writes==writes);close_checked(aliases);
    // One owner may close without releasing the shared PAL8 block.
    close_checked(gray);check_palette(graymips);refusal("fourth");
    close_checked(color);
    Package obstruction;load(obstruction,"obstruct");
    // Eight old impostor palettes occupy7 remaining low banks plus bank32;
    // 15 free slots in that block still cannot hold a PAL8 palette.
    assert(obstruction.textures()[7].reserved_0==33);refusal("fourth");
    close_checked(obstruction);load(p,"fourth");assert(p.textures()[0].reserved_0==33);close_checked(p);
    // Malformed flags/layout/tails cannot acquire or release a live bank.
    for(const char* name:{"reserved","rectangular","layout","topdrop","short"}){
        auto bad=read_bytes(root+"/"+name);assert(!p.adopt(bad.data(),bad.size()));
        assert(!p.open_streamed((root+"/"+name).c_str()));
        check_palette(graymips);check_palette(color2);check_palette(small);
    }
    close_checked(graymips);close_checked(color2);close_checked(small);
    assert(!allocs && !open_files);
    // Allocation/read/injected partial failures have no palette ownership.
    for(unsigned mode=0;mode<3;++mode){
        assert(p.open_streamed((root+"/two").c_str()));writes=palette_writes;
        if(mode==0)fail_allocation=allocation_calls+2;
        if(mode==1)p.inject_upload_failure_after(1);
        if(mode==2)fail_reads=true;
        assert(!p.upload() && !p.upload_complete() && !p.release_payload());
        assert(palette_writes==writes);p.close();p.close();fail_allocation=0;fail_reads=false;
        assert(!allocs && !open_files);
    }
    // Adopt/release can discard CPU data while exact palette state stays live.
    assert(p.adopt(base.data(),base.size()));inflight=true;assert(p.upload());check_palette(p);
    assert(p.release_payload());memset(base.data(),0xcc,base.size());check_palette(p);close_checked(p);
    // Normal pack reads, the live window and the closed-window fallback all use
    // the existing payload read path with no separate PAL8 preflight read.
    alignas(32) unsigned char window[32768];
    const std::string packed_path=root+"/packed";
    for(unsigned mode=0;mode<3;++mode){
        if(mode)assert(pack_window_open(packed_path.c_str(),window,sizeof(window)));
        assert(p.open_streamed_at(packed_path.c_str(),2048,chain.size()));
        if(mode==2)pack_window_close();
        inflight=true;assert(p.upload());check_palette(p);assert(p.release_payload());close_checked(p);pack_window_close();
        assert(!allocs && !open_files);
    }
    return 0;
#endif
}
'''


@unittest.skipUnless(shutil.which('g++'),'host compiler required')
class Pal8Runtime(unittest.TestCase):
    def test_actual_Package_admission_aligned_sharing_lifetime_and_failure_transaction(self):
        with tempfile.TemporaryDirectory() as directory:
            d=pathlib.Path(directory);stubs(d)
            with (d/'dc/pvr.h').open('a') as f:f.write('\n#define PVR_TXRFMT_PAL8BPP (6U<<27)\n#define PVR_TXRFMT_8BPP_PAL(bank) ((bank)<<25)\n')
            prefix=FIXTURE[:FIXTURE.index('int main(')]
            prefix=prefix[:prefix.index('void check_palette(')]+CHECK+prefix[prefix.index('void close_checked('):]
            (d/'reader.cpp').write_text(prefix+MAIN)
            native=source();gray=pal8.compact(native,enabled=True)[0]
            chain=pal8.compact(tw.add_mipmaps(native,enabled=True)[0],enabled=True)[0]
            color=pal8.compact(source(gray=False),enabled=True)[0]
            def colored(shift):
                n=tw.read_native_twiddled(source(gray=False));payload=bytearray(n.payload)
                words=struct.unpack('<%dH'%(len(payload)//2),payload)
                payload=struct.pack('<%dH'%len(words),*(w^shift for w in words))
                h=list(n.header);body=pal8.tpl.TEXTURE.pack(*n.texture)+payload;h[8]=zlib.crc32(body)&0xffffffff
                return pal8.compact(pal8.tpl.HEADER.pack(*h)+body,enabled=True)[0]
            color2,fourth=colored(0x4000),colored(0x8000)
            cases=dict(gray=gray,chain=chain,color=color,color2=color2,fourth=fourth,pal4=pal4_package(64),
                       alias=joined([gray,gray],alias=True),two=joined([gray,color]),
                       mixed=joined([pal4_package(64),fourth]),obstruct=synthetic(8,fmt=3),
                       reserved=mutate(chain,8,17),rectangular=mutate(chain,2,32),layout=mutate(chain,7,2),
                       topdrop=mutate(chain,6,4|(1<<30)),short=chain[:-1],packed=bytes(2048)+chain)
            for name,b in cases.items():(d/name).write_bytes(b)
            for alpha,mip in ((0,0),(1,0),(1,1)):
                for vram in (0,1):
                    exe=d/'reader'
                    cmd=['g++','-std=c++17','-DRE4DC_STORAGE_BOUNCE_BYTES=16384',
                         '-DRE4DC_PVR_PIPELINE=1','-DRE4DC_TEX_PAL4_ALPHA=1','-DRE4DC_TREE_IMPOSTOR=1',
                         '-DRE4DC_CAST_MIPMAP=1','-DRE4DC_TEX_PAL4_MIPMAP=1',
                         '-DRE4DC_TEX_PAL8_ALPHA='+str(alpha),'-DRE4DC_TEX_PAL8_MIPMAP='+str(mip),
                         '-DRE4DC_UI_VRAM='+str(vram),'-DRE4DC_TEX_META_EVICT=1',
                         '-DRE4DC_TEX_PACK=1','-DRE4DC_TEX_PACK_WINDOW=1','-DRE4DC_TEX_RESIDENT=1',
                         '-fsanitize=address,undefined','-fno-omit-frame-pointer',
                         '-I'+str(d),'-I'+str(ROOT/'room'),str(d/'reader.cpp'),
                         str(ROOT/'room/texture_package.cpp'),str(ROOT/'room/room_storage.cpp'),'-o',str(exe)]
                    built=subprocess.run(cmd,capture_output=True,text=True)
                    self.assertEqual(built.returncode,0,built.stderr)
                    ran=subprocess.run([str(exe),str(d)],capture_output=True,text=True)
                    self.assertEqual(ran.returncode,0,f'alpha={alpha} mip={mip} vram={vram}\n{ran.stderr}')

    def test_preexisting_window_handle_and_palette_interpretation_defects_are_controlled(self):
        main=r'''
int main(int argc,char** argv){
    const std::string path=std::string(argv[1])+"/packed";reserved_count=8;
    for(unsigned i=0;i<1024;++i)palette[i]=0x12345678U+i;
    assert(initialize_palettes(0xff));alignas(32) unsigned char window[32768];
    assert(pack_window_open(path.c_str(),window,sizeof(window)));
    Package p;assert(p.open_streamed_at(path.c_str(),2048,atoi(argv[3])));
    assert(p.upload());check_palette(p);assert(p.release_payload());
    assert(invalid_closes==unsigned(atoi(argv[2])));
    close_checked(p);pack_window_close();assert(!allocs && !open_files);
    // The old sharing loop ignores whether identical words are ARGB1555 or
    // ARGB4444. The new combined manager must preserve that interpretation.
    Package legacy,alpha;
    assert(legacy.open_streamed((std::string(argv[1])+"/legacy").c_str()));assert(legacy.upload());check_palette(legacy);
    assert(alpha.open_streamed((std::string(argv[1])+"/alpha").c_str()));assert(alpha.upload());
    const auto& t=alpha.textures()[0];unsigned bank=t.reserved_0-1;bool wrong_alpha=false;
    const auto* colors=(const unsigned short*)((const unsigned char*)alpha.pvr_texture(0)+t.data_size-32);
    for(unsigned k=0;k<16;++k)wrong_alpha|=palette[bank*16+k]!=expected_color(colors[k],true);
    assert(wrong_alpha==bool(atoi(argv[4])));
    close_checked(alpha);close_checked(legacy);assert(!allocs && !open_files);
    return 0;
}
'''
        with tempfile.TemporaryDirectory() as directory:
            d=pathlib.Path(directory);stubs(d)
            with (d/'dc/pvr.h').open('a') as f:f.write('\n#define PVR_TXRFMT_PAL8BPP (6U<<27)\n#define PVR_TXRFMT_8BPP_PAL(bank) ((bank)<<25)\n')
            prefix=FIXTURE[:FIXTURE.index('int main(')]
            prefix=prefix.replace('int fs_open(const char* p,int f){','unsigned invalid_closes;\nint fs_open(const char* p,int f){')
            prefix=prefix.replace('int fs_close(int f){assert(open_files);','int fs_close(int f){if(f==FILEHND_INVALID){++invalid_closes;return -1;}assert(open_files);')
            (d/'reader.cpp').write_text(prefix+main)
            data=pal4_package(64);(d/'packed').write_bytes(bytes(2048)+data)
            (d/'alpha').write_bytes(synthetic());(d/'legacy').write_bytes(synthetic(fmt=3))
            old=subprocess.check_output(['git','-C',str(ROOT),'show','dc4e5e507:port/dreamcast/room/texture_package.cpp'])
            for label,blob,enabled,invalid in (('control',old,0,1),('current',(ROOT/'room/texture_package.cpp').read_bytes(),1,0)):
                q=d/label;q.mkdir();(q/'texture_package.cpp').write_bytes(blob);exe=q/'reader'
                cmd=['g++','-std=c++17','-DRE4DC_STORAGE_BOUNCE_BYTES=16384',
                    '-DRE4DC_PVR_PIPELINE=1','-DRE4DC_TEX_PAL4_ALPHA=1','-DRE4DC_TREE_IMPOSTOR=1',
                    '-DRE4DC_TEX_PAL8_ALPHA='+str(enabled),'-DRE4DC_TEX_PACK=1',
                    '-DRE4DC_TEX_PACK_WINDOW=1','-DRE4DC_TEX_RESIDENT=1',
                    '-fsanitize=address,undefined','-fno-omit-frame-pointer','-I'+str(d),'-I'+str(ROOT/'room'),
                    str(d/'reader.cpp'),str(q/'texture_package.cpp'),str(ROOT/'room/room_storage.cpp'),'-o',str(exe)]
                subprocess.run(cmd,capture_output=True,check=True)
                ran=subprocess.run([str(exe),str(d),str(invalid),str(len(data)),str(invalid)],capture_output=True,text=True)
                self.assertEqual(ran.returncode,0,ran.stderr)


    def test_default_off_object_identical_to_pre_PAL8_source(self):
        with tempfile.TemporaryDirectory() as directory:
            d=pathlib.Path(directory);stubs(d)
            original=subprocess.check_output(['git','-C',str(ROOT),'show','dc4e5e507:port/dreamcast/room/texture_package.cpp'])
            results=[]
            for label,blob in (('control',original),('current',(ROOT/'room/texture_package.cpp').read_bytes())):
                q=d/label;q.mkdir();(q/'texture_package.cpp').write_bytes(blob)
                obj=q/'package.o'
                cmd=['g++','-std=c++17','-O2','-g0','-frandom-seed=pal8',
                     '-DRE4DC_STORAGE_BOUNCE_BYTES=16384','-DRE4DC_TEX_PAL4_ALPHA=1','-DRE4DC_CAST_MIPMAP=1',
                     '-DRE4DC_TEX_PAL4_MIPMAP=1','-DRE4DC_TEX_TWIDDLED_MIPMAP=1',
                     '-I'+str(d),'-I'+str(ROOT/'room'),'-c',str(q/'texture_package.cpp'),'-o',str(obj)]
                subprocess.run(cmd,capture_output=True,check=True);results.append(obj.read_bytes())
            self.assertEqual(*results)

    def test_default_off_make_guards_refuse_invalid_parent_settings(self):
        make=shutil.which('make')
        if not make:self.skipTest('make optional')
        text=(ROOT/'game/game30.mk').read_text();block=text[text.index('# Exact square uncompressed PAL8'):text.index('# Native square 16-bit twiddled mip chains')]
        with tempfile.TemporaryDirectory() as directory:
            p=pathlib.Path(directory)/'guard.mk';p.write_text(block+'\nobj/native-reuse/texture_package.o:\n\t@echo FLAGS=$(PLATFORM_CPPFLAGS)\n')
            for args,allowed in (([],True),(['TEX_PAL8_ALPHA=2'],False),(['TEX_PAL8_MIPMAP=2'],False),
                (['TEX_PAL8_ALPHA=1'],False),(['TEX_PAL8_MIPMAP=1'],False),
                (['TEX_PAL8_ALPHA=1','TEX_PAL4_ALPHA=1'],True),
                (['TEX_PAL8_ALPHA=1','TEX_PAL4_ALPHA=1','TEX_PAL8_MIPMAP=1'],False),
                (['TEX_PAL8_ALPHA=1','TEX_PAL4_ALPHA=1','TEX_PAL8_MIPMAP=1','CAST_MIPMAP=1'],True)):
                ran=subprocess.run([make,'--no-print-directory','-f',str(p),'OBJDIR=obj','obj/native-reuse/texture_package.o',*args],capture_output=True,text=True)
                self.assertEqual(ran.returncode==0,allowed,ran.stderr)
                if not args:self.assertNotIn('RE4DC_TEX_PAL8',ran.stdout)


if __name__=='__main__':unittest.main()
