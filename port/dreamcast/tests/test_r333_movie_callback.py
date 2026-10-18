#!/usr/bin/env python3
"""Compare the actual S00 movie adapter with the unchanged source callback.

Host transport/lasting-state proof only. Private PS2/GC EVD camera lengths are
independently audited in r333-ps2-gc-cut-alignment.json; no private asset needed.
"""
import argparse
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / 'src/st3/r333.cpp'


def function(text, signature):
    start = text.index(signature + '\n{')
    at = text.index('{', start)
    depth = 1
    end = at + 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    text = SOURCE.read_text()
    source = function(text, 'extern "C" void Evt_R333S00_Func(Event* e)')
    adapter = text.split('// R333_MOVIE_ADAPTER_BEGIN\n', 1)[1].split('// R333_MOVIE_ADAPTER_END', 1)[0]
    common = r'''
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <cstdarg>
using u32=uint32_t;
#define BitOn(a,b) ((a)|=(b))
#define BitOff(a,b) ((a)&=~(b))
struct Global {u32 Stop_flg,Disp_flg,Status_flg[4];};
struct Work {int timer;};
struct cModel {u32 be_flag;};
struct Event {
 int funcMode=0,NowCut=0,NowFrame=0,MaxTotalFrame=0;
 int GetMod(void**,const char*,int,int){return 0;}
};
static Global global;static Global* pG=&global;
static Work work;static Work* r333_work=&work;
static int timer,running,smd3,reads,writes,starts;
void SmdSetTrans(int no,int v){assert(no==3);smd3=v;}
int st3_getCountDownTimer(){++reads;return timer;}
void st3_setCountDownTimer(int n){++writes;timer=n;}
void st3_startCountDown(){++starts;running=1;}
void re4dc_log(const char*,...){}
'''
    driver = r'''
struct State {Global g;Work w;int timer,running,smd3,writes,starts;};
static void reset(unsigned seed,int value){
 global={seed*0x10204081u,seed*0x25182049u,{seed,seed*0x53a10471u,seed+1,~seed}};
 work.timer=-12345;timer=value;running=0;smd3=-1;reads=writes=starts=0;
}
static State state(){return {global,work,timer,running,smd3,writes,starts};}
static void same(const State&a,const State&b){
 assert(!std::memcmp(&a.g,&b.g,sizeof(a.g)));
 assert(a.w.timer==b.w.timer&&a.timer==b.timer&&a.running==b.running);
 assert(a.smd3==b.smd3&&a.writes==b.writes&&a.starts==b.starts);
}
static int cut(unsigned picture){
 static const unsigned ends[]={35,159,276,314,335,430};
 for(int i=0;i<6;++i)if(picture<ends[i])return i;
 assert(false);return 0;
}
int main(){
 unsigned comparisons=0;
 for(unsigned seed=0;seed<8;++seed)for(int value:{300,430,3600,7200}){
  for(unsigned picture=0;picture<430;++picture)for(int skip=0;skip<2;++skip){
   reset(seed,value);Event e;e.MaxTotalFrame=430;Evt_R333S00_Func(&e);
   e.funcMode=1;e.NowCut=cut(picture);e.NowFrame=1;Evt_R333S00_Func(&e);
   // Source cancel suppresses remaining mode1 callbacks, then mode3/2.
   if(skip){e.funcMode=3;Evt_R333S00_Func(&e);}
   e.funcMode=2;Evt_R333S00_Func(&e);const State expected=state();
   reset(seed,value);Event movie;r333MovieS00(&movie);
   // Only a late picture may be presented: crossed earlier flags are superseded.
   r333MovieS00Tick(picture);
   if(skip){movie.funcMode=3;r333MovieS00(&movie);}
   movie.funcMode=2;r333MovieS00(&movie);same(expected,state());
   assert(timer==value-430&&smd3==1&&starts==1&&writes==1);
   ++comparisons;
  }
  // No picture means no source mode1 state invented (e.g. early media failure).
  reset(seed,value);Event original;original.MaxTotalFrame=430;
  Evt_R333S00_Func(&original);original.funcMode=2;Evt_R333S00_Func(&original);
  const State expected=state();reset(seed,value);Event movie;r333MovieS00(&movie);
  movie.funcMode=2;r333MovieS00(&movie);same(expected,state());++comparisons;
 }
 std::printf("R333_CALLBACK_PASS comparisons=%u all430pictures natural/cancel dropped/no-picture\n",comparisons);
}
'''
    common += '#include <initializer_list>\n'
    with tempfile.TemporaryDirectory(prefix='r333-callback-') as directory:
        cpp = Path(directory) / 'test.cpp'
        exe = Path(directory) / 'test'
        cpp.write_text(common + source + '\n' + adapter + '\n' + driver)
        subprocess.run(['g++', '-std=c++17', '-O1', '-g', '-Wall', '-Wextra', '-Werror',
                        '-fsanitize=address,undefined', str(cpp), '-o', str(exe)], check=True)
        result = subprocess.run([str(exe)], text=True, capture_output=True, check=True)
    print(result.stdout, end='')
    report = dict(status='PASS', comparisons=27552, pictures=430,
                  scope='Source-extracted S00 lasting callback state/timer; host only. No movie decode, SH4 or gameplay proof.')
    if args.output:
        assert not args.output.exists()
        args.output.write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()