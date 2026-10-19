#!/usr/bin/env python3
"""Actual source r207 functions under bounded event/cap scheduler stand-ins."""
from pathlib import Path
import argparse,re,subprocess,tempfile
ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path);a=ap.parse_args();T=a.root or Path(__file__).resolve().parents[5]
s=(T/'src/st2/r207.cpp').read_text()
def extract(name):
 m=re.search(r'^(?:static )?(?:void|int) '+name+r'\([^;]*?\)\n\{',s,re.M);assert m,name
 p=m.end();depth=1
 while depth:depth+=(s[p]=='{')-(s[p]=='}');p+=1
 return s[m.start():p]
host=r"""
#include <cassert>
#include <cstdio>
#include <stdexcept>
#include <vector>
using u32=unsigned;using f32=float;struct Vec {float x,y,z;};using TaskFunc=void(*)();
static int now,live,releaseAt,eventAt,firstSendAt,fullChecks,posReads;static bool busy,bit11,failLeader,stayFull;static std::vector<int>sends;
struct cSubChar{int atari=0;};static cSubChar sub,*pSUB=&sub;
struct Player{Vec pos{100,4200,0};} player,*pPL=&player;
struct Handle {bool held=false,active=false;int mode=0,no=0;Vec pos{0,0,0};int isActive(){return active||held;}void getPos(Vec*v){posReads++;*v=pos;}void setNoSuspend(int){}
 void setEm(int n,int,int,int,int){sends.push_back(n);if(!firstSendAt)firstSendAt=now;no=n;if(n==0xd3&&failLeader)return;if(live>=4)held=true;else{active=true;live++;}}
 void setGoto(Vec*,int m){if(active)mode=m;else if(RE4DC_ALIVE_CAP_DEFER_GOTO_R207&&held)mode=m;}
 int ckGoto(){if(active)mode=0;return mode;}};
struct R207Em{int moving=0,gotoNo=0;Handle em;};struct Work{R207Em em[10];cSubChar*sub=nullptr;}work;struct WorkPtr{Work*p=&work;}r207_work;
#define EM_WRAP_HELD_NOW(w) ((w)->held)
#define G_ROOM_ID 0x207
static void SceSleep(int n){now+=n;if(now>1000)throw std::runtime_error("normal gameplay interrupted");if(!busy&&!stayFull&&now>=releaseAt&&live==4)live=3;}
static int PlGetStatus(){return 0;}static void RoomSeCall(int,Vec*,int,int,int){}
static void RsfSet(int,int bit){assert(bit==11);bit11=true;}
static void SceEventStart(int){busy=true;eventAt=now;}
static void AtariFlagsAnd(int*,int){}static void SceSetEventCancel(int,TaskFunc,int,int,int){}
static void r207_EnemySetEndProc(){busy=false;}
struct Camera{void CutCall(int){}int IsMotionEnd(){return 1;}}CamCtrl;
static float PSVECSquareDistance(Vec*a,Vec*b){float x=a->x-b->x,y=a->y-b->y,z=a->z-b->z;return x*x+y*y+z*z;}
static int re4dc_aliveCapFull(){fullChecks++;assert(!busy);return live>=4;}
"""
tests=r"""
static void reset(){now=0;live=4;releaseAt=355;eventAt=firstSendAt=fullChecks=posReads=0;busy=bit11=failLeader=stayFull=false;sends.clear();work=Work{};pSUB=&sub;}
int main(){
 reset();work.em[0].em.held=true;work.em[1].em.active=true;work.em[1].em.pos={101,4200,0};
#if RE4DC_ALIVE_CAP_DEFER_GOTO_R207
 assert(r207_CkDist()==1&&posReads==1);
#else
 assert(r207_CkDist()==0&&posReads==2);
#endif
 reset();r207_EnemySet();assert(sends.size()==3&&sends[0]==0xd3&&sends[1]==0xd4&&sends[2]==0xd5&&bit11&&!busy);
 assert(firstSendAt==eventAt); // no scheduler yield between preflight and original first send
#if RE4DC_ALIVE_CAP_DEFER_GOTO_R207
 assert(eventAt>=355&&fullChecks>1&&work.em[2].em.active&&!work.em[2].em.held&&work.em[3].em.held&&work.em[4].em.held);
 assert(work.em[3].em.mode==13&&work.em[4].em.mode==13);
#else
 assert(eventAt==351&&fullChecks==0&&work.em[2].em.held&&work.em[3].em.mode==0);
#endif
 // A real allocation refusal retains the original missing-actor behavior; never manufacture a live leader.
 reset();live=3;releaseAt=2000;failLeader=true;r207_EnemySet();assert(!work.em[2].em.active&&!work.em[2].em.held&&!busy);
#if RE4DC_ALIVE_CAP_DEFER_GOTO_R207
 // While full, remain in normal gameplay without flag/event/sends; death/Continue/room exit may interrupt.
 reset();stayFull=true;try{r207_EnemySet();assert(false);}catch(const std::runtime_error&){}
 assert(!busy&&!bit11&&sends.empty()&&eventAt==0);
 // A fresh original task after reset can run: no new persistent guard state exists.
 reset();live=3;releaseAt=2000;r207_EnemySet();assert(bit11&&!busy&&work.em[2].em.active);
#endif
 printf("actual-source r207 guards=%d: held distance, full-cap pre-busy order, missing actor, interruption/reset PASS\n",RE4DC_ALIVE_CAP_DEFER_GOTO_R207);
}
"""
with tempfile.TemporaryDirectory(prefix='r207-event-guards-')as d:
 p=Path(d)/'test.cpp';p.write_text(host+extract('r207_CkDist')+'\n'+extract('r207_EnemySet')+tests)
 for enabled in [0,1]:
  exe=Path(d)/str(enabled);subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror','-Wno-unused-function','-fsanitize=address,undefined','-fno-omit-frame-pointer',f'-DRE4DC_ALIVE_CAP_DEFER_GOTO_R207={enabled}',str(p),'-o',str(exe)],check=True);subprocess.run([str(exe)],check=True)
# Validate actual knob declarations and the room/wrapper object dispatch, without a game build.
make=(T/'port/dreamcast/game/Makefile').read_text();block=re.search(r'# ALIVE_CAP_DEFER_GOTO_R207_BEGIN.*?# ALIVE_CAP_DEFER_GOTO_R207_END\n',make,re.S).group()
with tempfile.TemporaryDirectory(prefix='r207-goto-make-')as d:
 p=Path(d)/'Makefile';targets=['obj/src/game/em_set.o','obj/mod/st2_1/src/st/em_wrap.o','obj/mod/st2_1/src/st2/r207.o','obj/mod/st2_4/src/st/em_wrap_v2.o','obj/mod/st4_0/src/st/em_wrap_v3.o'];p.write_text('ALIVE_CAP ?= 4\nALIVE_CAP_DEFER_FLAGS ?= 1\nOBJDIR := obj\n'+block+'all: '+' '.join(targets)+'\n'+''.join(t+":\n\t@printf '%s\\n' '$@=$(GAME_CPPFLAGS)'\n"for t in targets))
 for args,ok,on in [([],1,0),(['ALIVE_CAP_DEFER_GOTO_R207=0'],1,0),(['ALIVE_CAP_DEFER_GOTO_R207=1'],1,1),(['ALIVE_CAP_DEFER_GOTO_R207=2'],0,0),(['ALIVE_CAP_DEFER_GOTO_R207='],0,0),(['ALIVE_CAP_DEFER_GOTO_R207=0 1'],0,0),(['ALIVE_CAP_DEFER_GOTO_R207=1','ALIVE_CAP=0'],0,0),(['ALIVE_CAP_DEFER_GOTO_R207=1','ALIVE_CAP_DEFER_FLAGS=0'],0,0),(['ALIVE_CAP_DEFER_GOTO_R207=0','ALIVE_CAP=0','ALIVE_CAP_DEFER_FLAGS=0'],1,0)]:
  r=subprocess.run(['make','-s','-f',str(p),'all',*args],text=True,capture_output=True);assert (r.returncode==0)==bool(ok),(args,r.stdout,r.stderr)
  if ok:assert len(r.stdout.splitlines())==5 and all(('-DRE4DC_ALIVE_CAP_DEFER_GOTO_R207=1'in l)==bool(on)for l in r.stdout.splitlines()),(args,r.stdout)
print('Nine actual Makefile scope/default/prerequisite cases: PASS; actual guest event/death/Continue qualification remains pending')
