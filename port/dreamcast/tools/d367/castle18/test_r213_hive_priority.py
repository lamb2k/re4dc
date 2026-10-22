#!/usr/bin/env python3
"""Actual r213 sends/callback: preserve collision-dependent initialization under cap4.

This is a host ordering/pointer contract, not a guest AI or route acceptance test.
The pre-fix function is a negative control: its two critical sends are held.
"""
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[5]
PATH = 'src/st2/r213.cpp'
source = (ROOT / PATH).read_text()


def function(text, name):
    m = re.search(r'^void ' + name + r'\(\)\n\{', text, re.M)
    assert m, name
    pos, depth = m.end(), 1
    while depth:
        depth += (text[pos] == '{') - (text[pos] == '}')
        pos += 1
    return text[m.start():pos]


HOST = r'''
#include <cassert>
#include <vector>
#include <algorithm>
#include <cstdio>
static bool broken = false;
struct Collision { unsigned m_Flag = 4; } sat, eat;
static int active = 0;
static std::vector<int> sent;
struct Wrap {
 int no=0, hp=1000; unsigned flag=0;
 bool actual=false, held=false, nest=false;
 void setPtr(int n,int,int) {
  assert(!no); no=n; sent.push_back(n);
  if (RE4DC_ALIVE_CAP_NOVIS && active==4) {held=true;return;}
  actual=true;active++;nest=(sat.m_Flag&4)!=0;
 }
 void setFlag(unsigned f) {flag|=f;}
 void setHp(int v) {if(actual)hp=v;}
};
struct Work { Wrap em[9]; Collision* sat[1]={&::sat}; Collision* eat[1]={&::eat}; } work;
struct {Work* p=&work;} r213_work;
#define G_ROOM_ID 0x213
int RsfCheck(int,int){return broken;}
void SmdSetTrans(int,int){}
void SceAtSetEnable(int,int){}
'''
TEST = r'''
int main(){
 R213EmSet();
 assert(sent.size()==9);
 auto sorted=sent;std::sort(sorted.begin(),sorted.end());
 assert((sorted==std::vector<int>{0xc2,0xc3,0xc4,0xc5,0xc6,0xc7,0xc8,0xc9,0xca}));
 if(RE4DC_ALIVE_CAP_NOVIS) {
  if(!work.em[3].actual || !work.em[6].actual)return 69;
  assert(sent[0]==0xc5&&sent[1]==0xc8&&active==4);
  int held=0;for(auto& e:work.em)held+=e.held;assert(held==5);
 } else {
  assert((sent==std::vector<int>{0xc2,0xc3,0xc4,0xc6,0xc7,0xc9,0xca,0xc5,0xc8}));
  assert(active==9);
 }
 assert(work.em[3].nest&&work.em[6].nest);
 R213SuBreakModel();
 assert(!(sat.m_Flag&4)&&!(eat.m_Flag&4));
 assert(work.em[3].hp==0&&work.em[6].hp==0);
 assert(work.em[3].actual&&work.em[6].actual); // no late critical pointer
 for(auto& e:work.em)assert(e.flag==0x20000000);
 for(auto& e:work.em){
  if(e.held)assert(e.no!=0xc5&&e.no!=0xc8);
  e=Wrap{};
 }
 sent.clear();active=0;broken=true;
 R213EmSet();
 assert((sent==std::vector<int>{0xc2,0xc3,0xc4,0xc6,0xc7,0xc9,0xca}));
 assert(work.em[3].no==0&&work.em[6].no==0);
 assert(active==(RE4DC_ALIVE_CAP_NOVIS?4:7));
 puts("PASS: actual sends initialize both critical nest actors; original callback reaches them; remaining sends held; broken-hive path and off ordering preserved");
}
'''

with tempfile.TemporaryDirectory(prefix='castle-r213-priority-') as temp:
    def run(text, enabled, name):
        path = Path(temp) / (name + '.cpp')
        path.write_text(HOST + function(text, 'R213EmSet') + function(text, 'R213SuBreakModel') + TEST)
        exe = path.with_suffix('')
        subprocess.run(['g++', '-std=c++17', '-Wall', '-Wextra', '-Werror',
                        f'-DRE4DC_ALIVE_CAP_NOVIS={enabled}', str(path), '-o', str(exe)], check=True)
        return subprocess.run([str(exe)]).returncode

    before = subprocess.check_output(['git', '-C', str(ROOT), 'show', '402116c9:' + PATH], text=True)
    assert run(before, 1, 'pre-fix') == 69, 'Negative control must reproduce held critical actors'
    assert run(source, 0, 'off') == 0
    assert run(source, 1, 'on') == 0
print('Source-extracted r213 regression PASS; pre-fix cap1 fails the required pointer/initialization property')