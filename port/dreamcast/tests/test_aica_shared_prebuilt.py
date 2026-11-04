#!/usr/bin/env python3
"""Exercise the real prebuilt-bank admission/placement and ownership functions."""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "port/dreamcast/game/platform/audio_aica.cpp"


def function(text, signature):
    start = text.index(signature)
    brace = text.index("{", start)
    depth = 1
    end = brace + 1
    while depth:
        depth += (text[end] == "{") - (text[end] == "}")
        end += 1
    return text[start:end]


PRE = r"""
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>
using u8=uint8_t; using u16=uint16_t; using u32=uint32_t;
struct WTSAMPLE { u32 offset,length,bytes; };
struct WTADPCM { u32 unused; };
struct AicaBankHeader {
    u32 magic,version,cap_hz,total,nsamples,fnv,gc_size,slot,flags,slot_bytes[9];
};
struct Slot { u32 base,size; };
struct MapEnt { u32 gc_nib,len,aica; };
struct Blk {
    const WTSAMPLE* smp; const WTADPCM* adpcm;
    u32 aica,aica_size,gc_base,gc_size,first,count,slotted,rate_cap,valid;
};
struct Conv { int blk,prebuilt; u32 img_total; };
struct Stats { u32 blocks_skipped,blocks,blocks_prebuilt; };
Slot g_slot[9]; Blk g_blk[14]; MapEnt g_map[64]; Conv g_conv; Stats S;
u32 g_mapUsed,g_arenaNext,g_arenaTop,g_aicaUsed;
int g_highBlk=-1,g_spillBlk=-1;
constexpr u32 kMapMax=64;
u32 UseAramSize[14];
WTSAMPLE samples[2]; WTADPCM adpcm[2];
unsigned frees,cuts; bool layout_ok=true;
void re4dc_log(const char*,...) {}
void snd_mem_free(u32) { ++frees; }
void blk_cut(int) { ++cuts; }
bool room_arena(int t) { return t==5 || t==6 || t>=8; }
int slot_of(int t) { return room_arena(t)?8:t; }
u32 sample_shift(const WTSAMPLE&,u32) { return 0; }
u32 sample_bytes(const WTSAMPLE& s,u32) { return s.bytes; }
bool blk_wavetable(int,const WTSAMPLE*& s,const WTADPCM*& a,u32& n) {
    s=samples; a=adpcm; n=2; return true;
}
bool layout_init(const AicaBankHeader&) { return layout_ok; }
"""


MAIN = r"""
void reset() {
    memset(g_slot,0,sizeof(g_slot)); memset(g_blk,0,sizeof(g_blk));
    memset(g_map,0,sizeof(g_map)); memset(&g_conv,0,sizeof(g_conv));
    memset(&S,0,sizeof(S)); memset(samples,0,sizeof(samples));
    g_mapUsed=g_arenaNext=g_arenaTop=g_aicaUsed=frees=cuts=0;
    g_highBlk=g_spillBlk=-1; layout_ok=true;
    samples[0]={0,64,64}; samples[1]={64,32,32};
    for (auto& n:UseAramSize) n=4096;
    g_slot[3]={0x90000,264576}; g_slot[4]={0,0};
    g_slot[8]={0xe7820,1004192};
}
AicaBankHeader header(unsigned slot=3) {
    AicaBankHeader h{};
    h.version=1; h.cap_hz=32000; h.total=samples[0].bytes+samples[1].bytes;
    h.nsamples=2; h.fnv=fnv1a((const u8*)samples,sizeof(samples));
    h.gc_size=4096; h.slot=slot;
    h.slot_bytes[3]=264576; h.slot_bytes[8]=1004192;
    return h;
}
void malformed(unsigned which) {
    reset(); auto h=header();
    switch(which) {
    case 0: h.version=2; break;
    case 1: h.nsamples=1; break;
    case 2: h.fnv^=1; break;
    case 3: h.gc_size=4128; break;
    case 4: h.total+=32; break;
    case 5: h.slot=2; break;
    }
    assert(!blk_begin_prebuilt(4,0x5f60c0,h));
    assert(S.blocks_skipped==1 && !S.blocks && !g_mapUsed && g_highBlk==-1);
    assert(!g_blk[4].valid && !frees && !cuts);
}
int main() {
    for(unsigned i=0;i<6;i++) malformed(i);
    reset(); auto h=header();
    assert(blk_begin_prebuilt(3,0x1000,h));
    assert(g_blk[3].aica==g_slot[3].base && g_blk[3].slotted && g_highBlk==-1);
    blk_prepare(3,0x1000); assert(!g_mapUsed && !frees);

    reset(); h=header(4); h.slot_bytes[4]=256; g_slot[4]={0xd0000,256};
    assert(blk_begin_prebuilt(4,0x1000,h));
    assert(g_blk[4].aica==0xd0000 && g_highBlk==-1);

    reset(); h=header();
#if RE4DC_AICA_SPILL
    g_arenaNext=645088;
    assert(blk_begin_prebuilt(4,0x5f60c0,h));
    assert(g_highBlk==4 && g_arenaTop==1004192-96);
    assert(g_blk[4].aica==g_slot[8].base+g_arenaTop && g_blk[4].slotted);
    assert(S.blocks_prebuilt==1 && g_mapUsed==2 && !frees);
    assert(blk_begin_prebuilt(4,0x5f60c0,h)); // replacement, no leaked map/ownership
    assert(g_mapUsed==2 && g_highBlk==4 && cuts==1 && !frees);
    blk_prepare(6,0x1f4100); // actual room reset retires the high bank
    assert(g_highBlk==-1 && !g_blk[4].valid && !g_mapUsed && !frees);

    reset(); h=header(); assert(blk_begin_prebuilt(4,0x5f60c0,h));
    samples[0].bytes=1004160; samples[1].bytes=32;
    auto room=header(8);
    assert(blk_begin_prebuilt(8,0x300000,room)); // existing room-bank priority
    assert(g_highBlk==-1 && !g_blk[4].valid && g_blk[8].valid);
    assert(g_blk[8].aica==g_slot[8].base && g_mapUsed==2 && !frees);

    for(unsigned i=0;i<7;i++) {
        reset(); h=header(); g_arenaNext=100;
        switch(i) {
        case 0: g_slot[8].base=0; break;
        case 1: g_arenaNext=g_slot[8].size+1; break;
        case 2: g_arenaNext=g_slot[8].size-32; break;
        case 3: g_highBlk=8; break;
        case 4: g_slot[4].size=256; break;
        case 5:
            samples[0].bytes=0xfffffff0u; samples[1].bytes=0;
            h=header(); break; // alignment overflow, before publication
        case 6:
            samples[0].bytes=samples[1].bytes=0; h=header(); break;
        }
        assert(!blk_begin_prebuilt(4,0x5f60c0,h));
        assert(!g_blk[4].valid && !S.blocks && S.blocks_skipped==1);
        assert(!g_mapUsed && !frees);
        assert(g_highBlk==(i==3?8:-1));
    }
    reset(); h=header(); h.slot_bytes[4]=256; // incompatible image layout
    assert(!blk_begin_prebuilt(4,0x5f60c0,h) && S.blocks_skipped==1);
#else
    assert(!blk_begin_prebuilt(4,0x5f60c0,h));
    assert(S.blocks_skipped==1 && !g_mapUsed && g_highBlk==-1);
#endif
    reset(); h=header(); layout_ok=false;
    assert(!blk_begin_prebuilt(3,0x1000,h) && S.blocks_skipped==1);
    puts("actual prebuilt admission, malformed banks, legacy slots and ownership PASS");
}
"""


def main():
    text = SOURCE.read_text()
    bodies = "\n".join(function(text, signature) for signature in (
        "u32 fnv1a(", "void blk_free(", "void blk_prepare(", "void blk_map(",
        "bool blk_begin_prebuilt("))
    with tempfile.TemporaryDirectory(prefix="aica-shared-prebuilt-") as tmp:
        root = Path(tmp)
        source = root / "check.cpp"
        source.write_text(PRE + bodies + MAIN)
        for enabled in (0, 1):
            exe = root / ("spill" + str(enabled))
            subprocess.run(["g++", "-std=c++17", "-O2",
                            "-DRE4DC_AICA_SPILL=" + str(enabled),
                            str(source), "-o", str(exe)], check=True)
            subprocess.run([str(exe)], check=True, timeout=10)
            print("AICA_SPILL=" + str(enabled) + " PASS")


if __name__ == "__main__":
    main()
