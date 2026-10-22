"""Lossless PAL4 format and actual native Package ownership/lifecycle contracts.

The fixture compiles texture_package.cpp and room_storage.cpp with ASan/UBSan.
Palette RAM, allocator and in-flight render mocks reject unfenced writes/frees.
"""
import importlib.util
import pathlib
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import convert_tpl as TPL
from assetpipe.texture import decode_pal4_argb4444, read_re4tex

spec = importlib.util.spec_from_file_location("pal4_world_registry", ROOT / "tools/d367/ps2world/world_registry.py")
REGISTRY = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = REGISTRY
spec.loader.exec_module(REGISTRY)


def native(words, width=8, height=8, flags=0):
    payload = struct.pack("<%dH" % len(words), *TPL.twiddle_16bpp(words, width, height))
    descriptor = TPL.TEXTURE.pack(b"unchanged material", width, height, 2, 144, len(payload), flags, 1, 0)
    body = descriptor + payload
    return TPL.HEADER.pack(TPL.MAGIC, 2, 48, 96, 1, 48, 144, len(payload),
                           zlib.crc32(body) & 0xffffffff, 7, 29) + body


def mutate(blob, field, value):
    out = bytearray(blob)
    t = list(TPL.TEXTURE.unpack_from(out, 48))
    t[field] = value
    TPL.TEXTURE.pack_into(out, 48, *t)
    struct.pack_into("<I", out, 36, zlib.crc32(out[48:]) & 0xffffffff)
    return bytes(out)


def synthetic(count=1, alias=False, fmt=4):
    payloads = []
    descriptors = []
    start = 48 + 96 * count
    for i in range(count):
        if i and alias:
            offset, payload = start, payloads[0]
        else:
            palette = [((k * 0x1111) ^ (i * 0x0123)) & 0xffff for k in range(16)]
            payload = (bytes([0x10, 0x32, 0x54, 0x76, 0x98, 0xba, 0xdc, 0xfe]) * 4
                       if fmt == 4 else bytes(2048 + 4))
            payload += struct.pack("<16H", *palette)
            offset = start + sum(map(len, payloads))
            payloads.append(payload)
        descriptors.append(TPL.TEXTURE.pack(("material%d" % i).encode(), 8, 8, fmt,
                                            offset, len(payload), 0, 1 if fmt == 4 else 2, 0))
    payload = b"".join(payloads)
    body = b"".join(descriptors) + payload
    return TPL.HEADER.pack(TPL.MAGIC, 2, 48, 96, count, 48, start, len(payload),
                           zlib.crc32(body) & 0xffffffff, count, 0) + body


class ExactPal4Tests(unittest.TestCase):
    def test_full_word_and_rgba_identity_including_rectangular_twiddle(self):
        palette = [0x0000, 0x1000, 0xe000, 0xf000, 0xffff, 0x0123, 0x4567, 0x89ab,
                   0xcdef, 0x1357, 0x2468, 0xabcd, 0x5555, 0xaaaa, 0x0f0f, 0xf0f0]
        for w, h in ((8, 8), (32, 8), (8, 32), (256, 256)):
            words = [palette[(x * 7 + y * 3 + x * y) % 16] for y in range(h) for x in range(w)]
            original = native(words, w, h, 1)
            packed, meta = TPL.package_exact_pal4_argb4444(original)
            t = TPL.TEXTURE.unpack_from(packed, 48)
            decoded, rgba = decode_pal4_argb4444(packed[t[4]:t[4] + t[5]], w, h)
            self.assertEqual(decoded, words)
            self.assertEqual(rgba, bytes(c for v in words for c in
                             ((v >> 8 & 15) * 17, (v >> 4 & 15) * 17, (v & 15) * 17, (v >> 12) * 17)))
            self.assertEqual(TPL.HEADER.unpack_from(packed)[9:], (7, 29))
            self.assertEqual((t[0], t[1:3], t[6:]), (TPL.TEXTURE.unpack_from(original, 48)[0], (w, h), (1, 1, 0)))
            self.assertEqual(meta["saved_bytes"], w * h * 2 - (w * h // 2 + 32))
            self.assertEqual(TPL.package_exact_pal4_argb4444(original)[0], packed)
            old_source = bytearray(original)
            struct.pack_into("<I", old_source, 36, zlib.crc32(old_source[144:]) & 0xffffffff)
            old_packed, old_meta = TPL.package_exact_pal4_argb4444(old_source)
            self.assertEqual(old_packed, packed)
            self.assertEqual(old_meta["source_crc_rule"], "data")
            self.assertIsNotNone(REGISTRY.tex_package_error(packed, w, h)[0])
            self.assertEqual(REGISTRY.tex_package_error(packed, w, h, pal4_alpha=True), (None, "header"))
            legacy = bytearray(packed)
            struct.pack_into("<I", legacy, 36, zlib.crc32(legacy[144:]) & 0xffffffff)
            self.assertEqual(REGISTRY.tex_package_error(legacy, w, h, pal4_alpha=True), (None, "data"))
            with tempfile.TemporaryDirectory() as d:
                p = pathlib.Path(d) / "asset.re4tex"; p.write_bytes(packed)
                stats = read_re4tex(p)
                self.assertEqual(stats["vram_bytes"], w * h // 2 + 32)
                self.assertEqual(stats["textures"][0]["format"], "PAL4_ARGB4444")

    def test_reject_lossy_or_unsupported_conversion(self):
        original = native([i % 16 for i in range(64)])
        packed, _ = TPL.package_exact_pal4_argb4444(original)
        bad = [native(list(range(64))), native([0] * 64, flags=4), original[:-1],
               mutate(original, 7, 0), mutate(original, 3, 0), mutate(original, 8, 1)]
        corrupt = bytearray(original); corrupt[-1] ^= 1; bad.append(corrupt)
        for data in bad:
            with self.assertRaises(ValueError):
                TPL.package_exact_pal4_argb4444(data)
        for field, value in ((6, 4), (7, 2), (8, 1), (1, 9), (5, 63)):
            self.assertIsNotNone(REGISTRY.tex_package_error(mutate(packed, field, value), 8, 8, pal4_alpha=True)[0])
        with self.assertRaises(ValueError):
            decode_pal4_argb4444(packed[144:-1], 8, 8)


PVR_H = """#pragma once
#include <cstdint>
using pvr_ptr_t=void*;
#define PVR_TXRFMT_RGB565 (1U<<27)
#define PVR_TXRFMT_ARGB1555 0U
#define PVR_TXRFMT_ARGB4444 (2U<<27)
#define PVR_TXRFMT_PAL4BPP (5U<<27)
#define PVR_TXRFMT_4BPP_PAL(bank) ((bank)<<21)
#define PVR_TXRFMT_VQ_ENABLE (1U<<30)
#define PVR_TXRFMT_TWIDDLED 0U
#define PVR_PAL_ARGB1555 0U
#define PVR_PAL_ARGB8888 3U
void pvr_set_pal_format(unsigned);
void pvr_set_pal_entry(unsigned, unsigned);
"""
FIXTURE = r"""
#include "texture_package.hpp"
#include "room_storage.hpp"
#include <unistd.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <algorithm>
#include <cassert>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iterator>
#include <memory>
#include <string>
#include <vector>
using namespace re4dc::texture;
unsigned allocs, allocation_calls, fail_allocation, open_files, palette_format_calls, palette_writes, fences;
unsigned reserved_count, palette_format, palette[1024];
bool inflight, fail_reads;
const Package* closing;
std::vector<unsigned> close_banks;
void* pvr_mem_malloc(std::size_t n){
    assert(!inflight);++allocation_calls;
    if(fail_allocation && allocation_calls==fail_allocation)return nullptr;
    ++allocs;return malloc((n+31)&~std::size_t(31));
}
void pvr_mem_free(void* p){assert(!inflight && allocs);--allocs;free(p);}
void pvr_txr_load_ex(const void* p,void* q,unsigned w,unsigned h,unsigned){assert(!inflight);memcpy(q,p,w*h*2);}
void pvr_txr_load(const void* p,void* q,std::size_t n){assert(!inflight && n%32==0);memcpy(q,p,n);}
void pvr_set_pal_format(unsigned f){assert(!inflight);palette_format=f;++palette_format_calls;}
void pvr_set_pal_entry(unsigned i,unsigned color){
    assert(!inflight && i<1024 && i>=reserved_count*16);
    palette[i]=color;++palette_writes;
}
extern "C" void re4dc_pvr_vram_fence(){
    // A close fence must observe the still-owned banks, including aliases.
    if(closing){
        for(unsigned i=0;i<close_banks.size();++i)assert(closing->textures()[i].reserved_0==close_banks[i]);
        closing=nullptr;
    }
    inflight=false;++fences;
}
int fs_open(const char* p,int f){int fd=open(p,f);if(fd>=0)++open_files;return fd;}
int fs_close(int f){assert(open_files);--open_files;return close(f);}
ssize_t fs_total(int f){struct stat s;return fstat(f,&s)?-1:s.st_size;}
void* fs_mmap(int){return nullptr;}
ssize_t fs_read(int f,void* b,size_t n){return fail_reads?0:read(f,b,std::min(n,size_t(37)));}
off_t fs_seek(int f,off_t o,int w){return lseek(f,o,w);}
std::uint64_t timer_us_gettime64(){return 0;}
std::vector<unsigned char> read_bytes(const std::string& p){
    std::ifstream f(p,std::ios::binary);return {(std::istreambuf_iterator<char>(f)),{}};
}
unsigned expected_color(unsigned v, bool alpha4){
    if(alpha4)return ((v&0xf000)*0x11000U)|((v&0x0f00)*0x1100U)|((v&0x00f0)*0x110U)|((v&15)*17U);
    unsigned out=(v&0x8000)?0xff000000U:0;
    for(unsigned n=0;n<3;++n){unsigned c=(v>>(5*n))&31;out|=((c*8)+(c/4))<<(8*n);}
    return out;
}
void check_palette(const Package& p){
    for(unsigned i=0;i<p.header().texture_count;++i){
        const auto& t=p.textures()[i];unsigned bank=t.reserved_0-1;
        assert(bank>=reserved_count && bank<64);
        const auto* colors=(const unsigned short*)((const unsigned char*)p.pvr_texture(i)+t.data_size-32);
        for(unsigned k=0;k<16;++k)assert(palette[bank*16+k]==expected_color(colors[k],t.format==4));
        const unsigned tcw=pvr_format(t);
        assert((tcw&(7U<<27))==PVR_TXRFMT_PAL4BPP);
        assert(((tcw>>21)&63)==bank);
        assert(bool(tcw&PVR_TXRFMT_VQ_ENABLE)==(t.format==3));
        assert(!(tcw&0x80000000U));
    }
    for(unsigned i=0;i<reserved_count*16;++i)assert(palette[i]==0x12345678U+i);
    assert(palette_format_calls==1 && palette_format==PVR_PAL_ARGB8888);
}
void close_checked(Package& p){
    if(p.upload_complete()){
        close_banks.clear();
        for(unsigned i=0;i<p.header().texture_count;++i)close_banks.push_back(p.textures()[i].reserved_0);
        closing=&p;inflight=true;
    }
    p.close();assert(!closing);p.close();
}
int main(int argc,char** argv){
    std::string root=argv[1];reserved_count=unsigned(atoi(argv[2]));
    for(unsigned i=0;i<1024;++i)palette[i]=0x12345678U+i;
    auto bytes=read_bytes(root+"/alpha");
    Package p;
#if !RE4DC_TEX_PAL4_ALPHA
    assert(!p.adopt(bytes.data(),bytes.size()));
    assert(!p.open_streamed((root+"/alpha").c_str()));
    assert(!allocs && !open_files && !palette_format_calls);
    return 0;
#else
    assert(p.adopt(bytes.data(),bytes.size()));
    assert(!p.upload() && !allocs && !palette_writes);p.close();
    const std::uint64_t mask=reserved_count?0xffU:0U;
    assert(initialize_palettes(mask) && initialize_palettes(mask));
    assert(palette_format_calls==1);
    unsigned capacity=64-reserved_count;
    std::vector<std::unique_ptr<Package>> owners;
    for(unsigned i=0;i<capacity;++i){
        auto q=std::make_unique<Package>();
        assert(q->open_streamed((root+"/cap"+std::to_string(i)).c_str()));
        inflight=true;assert(q->upload());check_palette(*q);
        assert(q->release_payload() && !open_files);owners.push_back(std::move(q));
    }
    assert(initialize_palettes(mask));
    assert(!initialize_palettes(mask ^ 0xffU)); // no ownership reset
    const unsigned previous_writes=palette_writes,previous_allocs=allocation_calls;
    assert(p.open_streamed((root+"/alpha").c_str()));
    assert(!p.upload() && !p.upload_complete() && !p.release_payload());
    assert(palette_writes==previous_writes && allocation_calls==previous_allocs);p.close();
    // A crafted reserved field must not release a currently live bank on rejection.
    for(const char* name:{"reserved","layout","linear","mip","width","size","crc","truncated"}){
        auto bad=read_bytes(root+"/"+name);
        assert(!p.adopt(bad.data(),bad.size()));assert(!p.open_streamed((root+"/"+name).c_str()));
        assert(!open_files);
    }
    assert(p.open_streamed((root+"/alpha").c_str()));assert(!p.upload());p.close();
    // Two-descriptor preflight is transactional when only one bank is free.
    close_checked(*owners.back());owners.pop_back();
    assert(p.open_streamed((root+"/alias").c_str()));
    const auto attempts=allocation_calls,writes=palette_writes;
    assert(!p.upload() && allocation_calls==attempts && palette_writes==writes);p.close();
    close_checked(*owners.back());owners.pop_back();
    // Reuse after the fence; identical ARGB4444 palettes share one bank,
    // and aliases share one VRAM payload while retaining separate references.
    assert(p.open_streamed((root+"/alias").c_str()));assert(p.upload());check_palette(p);
    assert(p.shared_textures()==1 && p.pvr_texture(0)==p.pvr_texture(1));
    assert(p.textures()[0].reserved_0==p.textures()[1].reserved_0);
    assert(p.release_payload());close_checked(p);
    // Partial allocation/read/injected failures own no bank; their VRAM closes once.
    for(unsigned mode=0;mode<3;++mode){
        assert(p.open_streamed((root+"/multi").c_str()));
        if(mode==0)fail_allocation=allocation_calls+2;
        if(mode==1)p.inject_upload_failure_after(1);
        if(mode==2)fail_reads=true;
        assert(!p.upload() && !p.upload_complete() && !p.release_payload());
        assert(!p.upload());p.close();p.close();fail_allocation=0;fail_reads=false;assert(!open_files);
        Package recovery;assert(recovery.open_streamed((root+"/multi").c_str()));
        assert(recovery.upload());check_palette(recovery);close_checked(recovery);
    }
    for(auto& q:owners)close_checked(*q);
    owners.clear();assert(!allocs && !open_files);
    // Adopted CPU bytes can be overwritten after release, with live banks retained.
    assert(p.adopt(bytes.data(),bytes.size()));assert(p.upload());check_palette(p);
    assert(p.release_payload());memset(bytes.data(),0xcc,bytes.size());check_palette(p);
    assert(p.upload());close_checked(p);assert(!allocs);
    // Exhaustive exact expansion of every 16-bit palette word, old1555 and new4444.
    for(const char* name:{"legacy","alpha"}){
        auto base=read_bytes(root+"/"+name);
        auto* desc=(Texture*)(base.data()+48);
        for(unsigned first=0;first<65536;first+=16){
            auto* pal=(unsigned short*)(base.data()+desc->data_offset+desc->data_size-32);
            for(unsigned k=0;k<16;++k)pal[k]=first+k;
            // Package validates CRC, so recompute the actual serialized body.
            unsigned crc=~0U;
            for(unsigned n=48;n<base.size();++n){
                crc^=base[n];for(unsigned k=0;k<8;++k)crc=(crc>>1)^((crc&1)?0xedb88320U:0);
            }
            ((Header*)base.data())->payload_crc32=~crc;
            assert(p.adopt(base.data(),base.size()));assert(p.upload());check_palette(p);close_checked(p);
        }
    }
    assert(!allocs && !open_files && palette_format_calls==1 && fences>0);
    return 0;
#endif
}
"""


@unittest.skipUnless(shutil.which("g++"), "host compiler required")
class PackagePaletteTests(unittest.TestCase):
    def test_actual_package_capacity_fences_failures_and_exact_palette_colors(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            (root / "dc/pvr").mkdir(parents=True); (root / "kos").mkdir()
            (root / "dc/pvr.h").write_text(PVR_H)
            (root / "dc/pvr/pvr_mem.h").write_text("#include <cstddef>\nvoid* pvr_mem_malloc(std::size_t);void pvr_mem_free(void*);\n")
            (root / "dc/pvr/pvr_txr.h").write_text("#include <cstddef>\n#define PVR_TXRLOAD_16BPP 0\nvoid pvr_txr_load_ex(const void*,void*,unsigned,unsigned,unsigned);void pvr_txr_load(const void*,void*,std::size_t);\n")
            (root / "kos/fs.h").write_text("#pragma once\n#include <sys/types.h>\nusing file_t=int;\n#define FILEHND_INVALID -1\nint fs_open(const char*,int);int fs_close(int);ssize_t fs_total(int);void* fs_mmap(int);ssize_t fs_read(int,void*,size_t);off_t fs_seek(int,off_t,int);\n")
            (root / "kos.h").write_text("#include <kos/fs.h>\n#include <fcntl.h>\n#include <cstdint>\nstd::uint64_t timer_us_gettime64();\n")
            alpha = synthetic()
            for name, data in {"alpha": alpha, "legacy": synthetic(fmt=3), "alias": synthetic(2, True),
                               "multi": synthetic(2), "reserved": mutate(alpha, 8, 9), "layout": mutate(alpha, 7, 2),
                               "linear": mutate(alpha, 7, 0), "mip": mutate(alpha, 6, 4), "width": mutate(alpha, 1, 9),
                               "size": mutate(alpha, 5, 63), "crc": alpha[:-1] + bytes([alpha[-1] ^ 1]),
                               "truncated": alpha[:-1]}.items():
                (root / name).write_bytes(data)
            # Sharing makes repeated identical alpha palettes consume one bank.
            # Use distinct palettes to exercise real bank-capacity exhaustion.
            for index in range(64):
                cap = bytearray(alpha)
                words = struct.unpack_from("<16H", cap, len(cap) - 32)
                struct.pack_into("<16H", cap, len(cap) - 32, *(w ^ index for w in words))
                struct.pack_into("<I", cap, 36, zlib.crc32(cap[48:]) & 0xffffffff)
                (root / ("cap" + str(index))).write_bytes(cap)
            cpp = root / "fixture.cpp"; cpp.write_text(FIXTURE)
            exe = root / "fixture"
            for knob in (0, 1):
                for vram in (0, 1):
                    subprocess.run(["g++", "-std=c++17", "-DRE4DC_STORAGE_BOUNCE_BYTES=16384",
                                    "-DRE4DC_TREE_IMPOSTOR=1", "-DRE4DC_PVR_PIPELINE=1",
                                    "-DRE4DC_TEX_PAL4_ALPHA="+str(knob), "-DRE4DC_UI_VRAM="+str(vram),
                                    "-fsanitize=address,undefined", "-fno-omit-frame-pointer",
                                    "-I"+str(root), "-I"+str(ROOT / "room"), str(cpp),
                                    str(ROOT / "room/texture_package.cpp"), str(ROOT / "room/room_storage.cpp"),
                                    "-o", str(exe)], check=True)
                    for reserved in (0, 8):
                        subprocess.run([str(exe), str(root), str(reserved)], check=True)


if __name__ == "__main__":
    unittest.main()
