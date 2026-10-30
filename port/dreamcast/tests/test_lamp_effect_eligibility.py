#!/usr/bin/env python3
"""Exercise the source sprite/class filters for the hanging lamp fire owner."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[3]

def function(source, signature):
    start=source.index(signature); begin=source.index('{',start); depth=1; at=begin+1
    while depth:
        depth += (source[at]=='{')-(source[at]=='}'); at+=1
    return source[start:at]

def eligibility(source):
    # The private Esp1b parameter and spline test are selector conditional.
    # Keep that complete source conditional; no reconstructed owner predicate.
    typed=source.index('static int EspSpriteEligible(')
    begin=source.rfind('#if defined(RE4DC_ESP1B_GRID03)',0,typed)
    end=source.index('#undef RE4DC_SPLINE_BLOCK03',typed)+len('#undef RE4DC_SPLINE_BLOCK03')
    return source[begin:end]

class LampEligibility(unittest.TestCase):
    def test_source_lamp_and_existing_filters(self):
        source=(ROOT/'src/game/esp_sub.cpp').read_text()
        code=r"""
#include <cassert>
using u32=unsigned;
using s8=signed char;
struct cEsp { struct {unsigned owner;} info; unsigned m_Id,m_Tool_flg,m_Flg,xA4;
             unsigned m_Parts_no=0xff,m_Shimmer_type=0,xA5=4,xA6=5; };
void EspCommonTrans(cEsp*) {}
void UnsupportedTrans(cEsp*) {}
using EspTransFunc=void(*)(cEsp*);
EspTransFunc EspTransTbl[255];
"""+eligibility(source)+"\n"+r"""
#if defined(RE4DC_ESP1B_GRID03) && RE4DC_ESP1B_GRID03
"""+function(source,'static int Esp1bGridClass03(')+r"""
#endif
"""+function(source,'extern "C" int re4dc_esp_sprite_class(')+r"""
int main() {
    for(auto& p:EspTransTbl)p=UnsupportedTrans;
    EspTransTbl[0]=EspCommonTrans;
    // Source Et0a loads et0a.eff as 0x5e; its impact sequence uses common
    // flame/smoke sprites and class 0x0b. Adjacent prop owners stay excluded.
    for(unsigned owner=0;owner<256;++owner) {
        cEsp e{{owner},0,0x8018,0,1};
        bool expected=owner==0 || owner==0x10 || (owner>=0x34 && owner<=0x4f) || owner==0x5e;
        if(owner==1)expected=RE4DC_EFFECT_ROOM&1;
        if(owner==0xd0)expected=RE4DC_EFFECT_ROOM&2;
        assert(bool(EspSpriteEligible(&e))==expected);
    }
    cEsp lamp{{0x5e},0,0x8018,0,1};
    assert(re4dc_esp_sprite_class(&lamp));
    lamp.m_Id=0x0b;assert(re4dc_esp_sprite_class(&lamp));
    lamp.m_Id=0x46;assert(!re4dc_esp_sprite_class(&lamp));
    lamp.m_Id=0;
    for(unsigned bit: {0x4000u,0x10000u}) {
        lamp.m_Tool_flg=0x8018|bit;assert(!EspSpriteEligible(&lamp));
        assert(!re4dc_esp_sprite_class(&lamp));
    }
    lamp.m_Tool_flg=0x8018;lamp.m_Flg=0x10;assert(!EspSpriteEligible(&lamp));
    lamp.m_Flg=0;lamp.xA4=0;assert(!EspSpriteEligible(&lamp));
    lamp.xA4=2;assert(!EspSpriteEligible(&lamp));
    cEsp haze{{0xd0},0x15,0,0,1};
    assert(bool(EspSpriteEligible(&haze))==bool(RE4DC_EFFECT_ROOM&4));
    haze.m_Id=0x48;assert(bool(EspSpriteEligible(&haze))==bool(RE4DC_EFFECT_ROOM&4));
#if defined(RE4DC_ESP1B_GRID03) && RE4DC_ESP1B_GRID03
    cEsp grid{{0},0x1b,0,0x10,1};EspTransTbl[0x1b]=EspCommonTrans;
    assert(EspSpriteEligible(&grid,true));assert(!EspSpriteEligible(&grid));
    grid.m_Id=0;assert(!EspSpriteEligible(&grid,true));grid.m_Id=0x1b;
    grid.m_Flg=0;assert(!EspSpriteEligible(&grid,true));grid.m_Flg=0x10;
    grid.info.owner=0x23;assert(!EspSpriteEligible(&grid,true));grid.info.owner=0;
    EspTransTbl[0x1b]=UnsupportedTrans;assert(!EspSpriteEligible(&grid,true));
    assert(!re4dc_esp_sprite_class(&grid));
#endif
}
"""
        code='#include <initializer_list>\n'+code
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp);p=d/'filter.cpp';p.write_text(code)
            for room in (0,1,2,4,7):
                for grid in (0,1):
                    exe=d/('check'+str(room)+'-'+str(grid))
                    subprocess.run(['g++','-std=c++17','-O2','-DRE4DC_EFFECT_ROOM='+str(room),
                                    '-DRE4DC_ESP1B_GRID03='+str(grid),str(p),'-o',str(exe)],check=True)
                    subprocess.run([str(exe)],check=True)

if __name__=='__main__':unittest.main()
