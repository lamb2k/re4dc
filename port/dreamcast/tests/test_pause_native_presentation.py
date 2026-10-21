#!/usr/bin/env python3
"""Actual coarse_tick context and Make guard regressions; no target ABI claim."""
from pathlib import Path
import subprocess,tempfile,unittest
ROOT=Path(__file__).resolve().parents[3]
CPP=ROOT/'port/dreamcast/game/coarse.cpp'
MK=ROOT/'port/dreamcast/game/game30.mk'
def body(text):
 start=text.index('extern "C" int re4dc_coarse_tick(int dropped)')
 at=text.index('{',start);depth=1;end=at+1
 while depth:
  depth+=(text[end]=='{')-(text[end]=='}');end+=1
 return text[start:end]
PREFIX='''#include <cstring>
#include <cstdio>
struct State {unsigned Rno0,Rno1,System_flg,Status_flg[3];};
State state;State* pG;struct {unsigned Rno_bak;} Game;
int re4dc_coarse_image,movie,movieCalls,ticks,latched;
int re4dc_ui_movie_texture(){++movieCalls;return movie;}
void re4dc_std_scenery_tick(int value){++ticks;latched=value;}
#define RE4DC_NO_STD_SCENERY 0
#define RE4DC_PS2_WORLD_ROOMS 2
'''
MAIN='''
int main(){unsigned cases=0;
for(unsigned mode=0;mode<8;++mode)for(unsigned sub=0;sub<4;++sub)
for(unsigned saved=0;saved<8;++saved)for(unsigned bits=0;bits<8;++bits)
for(unsigned film=0;film<2;++film)for(unsigned drop=0;drop<2;++drop){
 state={};state.Rno0=mode;state.Rno1=sub;
 state.System_flg=((bits&1)?0x400:0)|((bits&2)?0x100000:0);
 state.Status_flg[2]=(bits&4)?0x04000000:0;
 const unsigned char backup[4]={static_cast<unsigned char>(saved),7,2,1};
 std::memcpy(&Game.Rno_bak,backup,4);const auto oldGame=Game.Rno_bak;
 const State before=state;pG=&state;movie=film;movieCalls=ticks=0;
 const bool eligible=mode==3 || (RE4DC_PAUSE_NATIVE_PRESENTATION && mode==6 && sub<=2 && saved==3);
 const bool qualified=eligible && !bits;const int expected=qualified && !film;
 const int result=re4dc_coarse_tick(drop);
 if(result!=expected || re4dc_coarse_image!=(expected&&!drop) || ticks!=1 || latched!=re4dc_coarse_image || movieCalls!=int(qualified) || std::memcmp(&state,&before,sizeof state) || Game.Rno_bak!=oldGame)return 10;
 ++cases;
}
pG=nullptr;movieCalls=ticks=0;
if(re4dc_coarse_tick(0) || re4dc_coarse_image || movieCalls || ticks!=1)return 11;
std::printf("%u context cases plus null state passed\\n",cases);
}
'''
class PauseContextTests(unittest.TestCase):
 def test_disabled_preprocessing_exact(self):
  old=subprocess.check_output(['git','show','HEAD:port/dreamcast/game/coarse.cpp'],cwd=ROOT,text=True)
  def pp(text):
   return subprocess.check_output(['g++','-E','-P','-x','c++','-DRE4DC_PAUSE_NATIVE_PRESENTATION=0','-'],input=PREFIX+body(text),text=True)
  self.assertEqual(pp(old),pp(CPP.read_text()))
 def test_actual_context_boundaries(self):
  with tempfile.TemporaryDirectory(prefix='feedback21-context-') as temp:
   p=Path(temp)
   for enabled in (0,1):
    source=p/f'context{enabled}.cpp';exe=p/f'context{enabled}'
    source.write_text(PREFIX+body(CPP.read_text())+MAIN)
    subprocess.run(['g++','-std=c++17','-O2','-fsanitize=undefined',f'-DRE4DC_PAUSE_NATIVE_PRESENTATION={enabled}',str(source),'-o',str(exe)],check=True,capture_output=True,text=True)
    result=subprocess.run([str(exe)],check=True,capture_output=True,text=True)
    self.assertIn('8192 context cases plus null state passed',result.stdout)
 def test_make_guard(self):
  text=MK.read_text();start=text.index('# PAUSE_NATIVE_PRESENTATION:');end=text.index('# COARSE_NO_STD_SCENERY=1',start)
  with tempfile.TemporaryDirectory(prefix='feedback21-make-') as temp:
   p=Path(temp)/'Makefile';p.write_text('OBJDIR=out\n'+text[start:end]+'\nout/coarse.o:\n\t@echo flags=$(GAME_CPPFLAGS)\n')
   for flag,coarse,ok in [('0','1',True),('1','1',True),('1','0',False),('2','1',False),('-1','1',False),('yes','1',False),('0 1','1',False),('','1',False)]:
    r=subprocess.run(['make','-s','-f',str(p),f'PAUSE_NATIVE_PRESENTATION={flag}',f'COARSE={coarse}','out/coarse.o'],capture_output=True,text=True)
    self.assertEqual(r.returncode==0,ok,(flag,coarse,r.stderr))
    if ok:self.assertEqual('RE4DC_PAUSE_NATIVE_PRESENTATION=1' in r.stdout,flag=='1')
if __name__=='__main__':unittest.main()
