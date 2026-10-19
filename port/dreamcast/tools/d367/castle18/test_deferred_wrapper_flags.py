#!/usr/bin/env python3
"""Compile actual queue, creator and wrapper bodies against a bounded host model."""
from pathlib import Path
import argparse, re, subprocess, tempfile
ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path);args=ap.parse_args()
ROOT=args.root or Path(__file__).resolve().parents[5]
SOURCE=(ROOT/'src/game/em_set.cpp').read_text();WRAP=(ROOT/'src/st/em_wrap.cpp').read_text()
# Select the ordinary loop branch before brace extraction (the gate has two opening braces).
SOURCE=re.sub(r'#if defined\(RE4DC_ALIVE_CAP_R202_GATE\)[^\n]*\n    // Keep the original.*?#else\n(.*?)#endif',r'\1',SOURCE,flags=re.S)
def function(name,source=SOURCE):
 m=re.search(r'^(?:static (?:inline )?|extern "C" )?(?:int|void|u32|cEm\*) '+re.escape(name)+r'\([^;]*?\)\n\{',source,re.M)
 assert m,name
 pos,depth=m.end(),1
 while depth:
  depth+=(source[pos]=='{')-(source[pos]=='}');pos+=1
 return source[m.start():pos]
HOST=r'''
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>
using u8=uint8_t;using s8=int8_t;using u16=uint16_t;using s16=int16_t;using u32=uint32_t;using f32=float;
struct Vec {float x=0,y=0,z=0;};
struct EmListData {u32 be_flag=0,flag=0;int id=0,type=0,set=0,Character=0,Guard_r=0,hp=1000,room=0;int pos[3]={},rot[3]={};};
struct Global {u8 pad[0x52e8];EmListData emlist[256];int stage_no=2,room_no=0xc,room_id=0x20c;u32 Frame_cnt=100;} global,*pG=&global;
struct EmListView {u8 pad[0x52e8];EmListData emlist[256];};
static int failCreate=0,firstMoves=0,errors=0;static bool dead[256];static u32 flagsAtFirstMove;
struct cEm {int id=0,type=0,set=0,Character=0,hp_max=0,hp=0,emset_no=0,active=0;u32 be_flag=0,flag=0;float Guard_r=0,plDist2=0,l_sub=0;Vec pos,pos_old,ang;
 int isAlive(){return (be_flag&0x201)==1;}int checkStatus(int){return active;}
 void move(){firstMoves++;flagsAtFirstMove=flag;flag=0x100;active=0;} } pool[32],player,*pPL=&player,sentinel,*errEm=nullptr;
struct Manager {u32 nArray=32;void destroy(cEm* e){e->be_flag=0x200;}} EmMgr;
struct Log {void err(int,int,const char*,int){errors++;}} logWork,*pLog=&logWork;
struct cEmWrap {cEm* pEm=nullptr;s16 no=-1;s8 list=-1;u8 alive=0;int errOn=0;
 void setFlag(u32);cEm* getPtr();int isAlive();int isActive();void destroy();void initWork();void err(const char*,int){errors++;}};
#define EM_LIST(n) (&pG->emlist[n])
#define EM_STATUS_ACTIVE 1
#define EM_SET_ID_NG(id) 0
#define RE4DC_ALIVE_CAP 4
#define RE4DC_ALIVE_CAP_ON 1
#define RE4DC_ALIVE_CAP_N 4
#define RE4DC_ALIVE_CAP_LOG 0
#define ALIVE_CAP_FRESH 16
static u8 aliveCapHeld[64],aliveCapSent[64],aliveCapFreshNo[16];static int aliveCapN,aliveCapReleasing;
static u32 aliveCapLast,aliveCapFreshF[16];static cEm* aliveCapFreshEm[16];
#if RE4DC_ALIVE_CAP_DEFER_FLAGS
static u32 aliveCapPendingFlags[64];static_assert(sizeof(aliveCapPendingFlags)==256);
#endif
static int aliveCapRoom(){return 1;}static int aliveCapKeep(int){return 0;}
static u32 EmSetDieCk(u32 no){return dead[no];}
static cEm* emSetWork(u32 i){return pool+i;}
static void EmListSetAlive(int no,int on){if(on)EM_LIST(no)->be_flag|=1;else EM_LIST(no)->be_flag&=~1;}
static cEm* EmCreate(u8 id){if(failCreate)return nullptr;for(auto& e:pool)if(!e.isAlive()){e=cEm{};e.id=id;e.be_flag=1;return &e;}return nullptr;}
static cEm* GetEmPtrFromList(int no){for(auto& e:pool)if(e.isAlive()&&e.emset_no==no)return &e;return nullptr;}
static EmListData* GetListPtrFromEm(cEm* e){return EM_LIST(e->emset_no);}
cEm* EmSetFromList2(int,int);
'''
macro=SOURCE[SOURCE.index('#define EM_SET_WORK('):SOURCE.index('// Squared XZ distance')]
base=['EmSetWork','EmSetDist','checkListId','aliveCapGanado','aliveCapEnemy','aliveCapWaitingK']
feature=['re4dc_aliveCapSetFlag','aliveCapApplyPending','aliveCapRestorePending']
queue=['aliveCapPush','aliveCapNoteFresh','aliveCapLive','re4dc_aliveCapHeldEntry','re4dc_aliveCapTake','re4dc_aliveCapHeldCount','re4dc_aliveCapDestroy','re4dc_aliveCapFarDrop','re4dc_aliveCapMove','re4dc_aliveCapDefer','EmSetFromList','EmSetFromList2','EmSetRoomInit']
code=HOST+macro+'\n'.join(function(n)for n in base)+'\n#if RE4DC_ALIVE_CAP_DEFER_FLAGS\n'+'\n'.join(function(n)for n in feature)+'\n#endif\n'+'\n'.join(function(n)for n in queue)
code+='\n'+function('emWrapHeld',WRAP)+'\n#define EM_WRAP_HELD(w) emWrapHeld(w)\n'+function('emWrapLive',WRAP)
code+='\n'+'\n'.join(function('cEmWrap::'+n,WRAP)for n in ['initWork','setFlag','getPtr','isAlive','isActive','destroy'])
TEST=r'''
static void reset(){
 global=Global{};player=cEm{};pPL=&player;for(auto&e:pool)e=cEm{};memset(dead,0,sizeof dead);
 aliveCapN=aliveCapReleasing=0;aliveCapLast=0;memset(aliveCapFreshEm,0,sizeof aliveCapFreshEm);
 failCreate=firstMoves=errors=0;flagsAtFirstMove=0;errEm=nullptr;
}
static cEmWrap hold(int no,int sent=1,int id=0x1b,int distance=1){
 auto& d=*EM_LIST(no);d=EmListData{};d.room=0x20c;d.id=id;d.be_flag=sent?0:1;d.pos[0]=distance;
 aliveCapPush(no,sent);cEmWrap w;w.no=no;w.alive=2;return w;
}
static u32 expected(u32 bits){return 0x100|(RE4DC_ALIVE_CAP_DEFER_FLAGS?bits:0);}
int main(){
 // Shared handles OR onto one held actor; duplicate sends do not clear the mask.
 reset();auto a=hold(6);auto b=a;a.setFlag(1);b.setFlag(0x20);a.setFlag(1);aliveCapPush(6,1);
 assert(aliveCapN==1&&firstMoves==0&&EM_LIST(6)->flag==0&&EM_LIST(6)->be_flag==0);
 re4dc_aliveCapMove(1);assert(aliveCapN==1);re4dc_aliveCapMove(0);
 auto e=GetEmPtrFromList(6);assert(e&&e->flag==expected(0x21)&&flagsAtFirstMove==0&&firstMoves==1);
 assert(a.getPtr()==e&&b.getPtr()==e);a.setFlag(0x800);assert(e->flag==(expected(0x21)|0x800));
 // Raw-pointer demand follows its existing Take path, delivering after first init.
 reset();a=hold(6);a.setFlag(2);e=a.getPtr();assert(e&&e->flag==expected(2)&&firstMoves==1&&flagsAtFirstMove==0);
 // Repeat direct source send and room start also consume commands after first move.
 reset();a=hold(6);a.setFlag(4);e=EmSetFromList2(6,1);assert(e&&e->flag==expected(4)&&flagsAtFirstMove==0);
 reset();a=hold(6,0);a.setFlag(8);EmSetFromList();e=GetEmPtrFromList(6);assert(e&&e->flag==expected(8)&&flagsAtFirstMove==0);
 // Failed automatic middle release preserves exact queue identity/order and sent bits.
 reset();a=hold(1,0,0x1b,1);b=hold(2,1,0x1b,100);auto c=hold(3,1,0x1b,2);
 a.setFlag(1);b.setFlag(2);c.setFlag(4);failCreate=1;re4dc_aliveCapMove(0);
#if RE4DC_ALIVE_CAP_DEFER_FLAGS
 assert(aliveCapN==3&&aliveCapHeld[0]==1&&aliveCapHeld[1]==2&&aliveCapHeld[2]==3);
 assert(aliveCapSent[0]==0&&aliveCapSent[1]==1&&aliveCapSent[2]==1);
 assert(aliveCapPendingFlags[0]==1&&aliveCapPendingFlags[1]==2&&aliveCapPendingFlags[2]==4);
 failCreate=0;pG->Frame_cnt+=30;re4dc_aliveCapMove(0);assert(GetEmPtrFromList(2)->flag==0x102);
 assert(aliveCapN==2&&aliveCapHeld[0]==1&&aliveCapHeld[1]==3&&aliveCapPendingFlags[1]==4);
#else
 assert(aliveCapN==2);
#endif
 // getPtr refusal keeps both shared wrappers held, and permits a later retry.
 reset();a=hold(9);b=a;a.setFlag(0x10);failCreate=1;assert(!a.getPtr());
#if RE4DC_ALIVE_CAP_DEFER_FLAGS
 assert(a.alive==2&&b.isAlive()==1&&aliveCapN==1);b.setFlag(0x20);failCreate=0;
 assert(a.getPtr()->flag==0x130&&b.getPtr()==a.pEm);
#else
 assert(a.alive==0&&aliveCapN==0);
#endif
 // A non-null error sentinel is never treated as successful initialization.
#if RE4DC_ALIVE_CAP_DEFER_FLAGS
 reset();a=hold(9);a.setFlag(0x10);errEm=&sentinel;failCreate=1;assert(!a.getPtr());
 assert(a.alive==2&&aliveCapN==1&&firstMoves==0);failCreate=0;assert(a.getPtr()->flag==0x110);
#endif
 // Direct and room-start failures retain pending bits until their real success.
 reset();a=hold(9);a.setFlag(0x40);failCreate=1;assert(!EmSetFromList2(9,1));assert(aliveCapN==1);
 failCreate=0;assert(EmSetFromList2(9,1)->flag==expected(0x40));
 reset();a=hold(9,0);a.setFlag(0x80);failCreate=1;EmSetFromList();assert(aliveCapN==1);
 failCreate=0;EmSetFromList();assert(GetEmPtrFromList(9)->flag==expected(0x80));
 // Middle destroy and far-delete compactions must not transfer another actor's command.
 reset();a=hold(1);b=hold(2,1,0x11);c=hold(3);a.setFlag(1);b.setFlag(2);c.setFlag(4);
 re4dc_aliveCapDestroy(0x11,-1);assert(aliveCapN==2&&aliveCapHeld[1]==3);
 assert(c.getPtr()->flag==expected(4));assert(a.getPtr()->flag==expected(1));
 reset();a=hold(1);b=hold(2);c=hold(3,1,0x2d);a.setFlag(1);b.setFlag(2);c.setFlag(4);
 assert(re4dc_aliveCapFarDrop(1,0)==1&&aliveCapN==2&&aliveCapHeld[1]==3);
 assert(c.getPtr()->flag==expected(4));assert(a.getPtr()->flag==expected(1));
 // Invalid room/dead entries and destroyed handles must not leak flags into reused slots.
 reset();a=hold(1);b=hold(2);a.setFlag(1);b.setFlag(2);EM_LIST(1)->room=0x20f;
 re4dc_aliveCapMove(0);assert(GetEmPtrFromList(2)->flag==expected(2));assert(!GetEmPtrFromList(1));
 a=hold(1);assert(a.getPtr()->flag==0x100);
 reset();a=hold(1);a.setFlag(0x40);dead[1]=true;re4dc_aliveCapMove(0);assert(aliveCapN==0&&firstMoves==0);
 dead[1]=false;a=hold(1);assert(a.getPtr()->flag==0x100);
 reset();a=hold(1);b=hold(2);a.setFlag(1);b.setFlag(2);EM_LIST(1)->room=0x20f;EM_LIST(2)->be_flag=1;
 EmSetFromList();assert(GetEmPtrFromList(2)->flag==expected(2));
 reset();a=hold(1);a.setFlag(0x40);a.destroy();assert(aliveCapN==0&&a.alive==0);a=hold(1);assert(a.getPtr()->flag==0x100);
 // Existing room reset clears old metadata before new init sends, even when
 // the same room/list/ESL ID is reused (Continue) or an entire list is replaced.
 reset();a=hold(1);a.setFlag(0x40);EmSetRoomInit();assert(aliveCapN==1);
 assert(a.getPtr()->flag==0x100);
 reset();a=hold(1);a.setFlag(0x40);*EM_LIST(1)=EmListData{};EM_LIST(1)->id=0x1b;EM_LIST(1)->room=0x20c;
 EmSetRoomInit();a=hold(1);a.setFlag(0x80);EmSetFromList2(1,1);assert(GetEmPtrFromList(1)->flag==expected(0x80));
 // Full queue: failed middle take restores all 64 entries without overflowing.
#if RE4DC_ALIVE_CAP_DEFER_FLAGS
 reset();for(int n=0;n<64;n++){a=hold(n);a.setFlag(1u<<(n%32));}a.no=31;a.alive=2;failCreate=1;
 assert(!a.getPtr()&&aliveCapN==64);for(int n=0;n<64;n++){assert(aliveCapHeld[n]==n);assert(aliveCapPendingFlags[n]==(1u<<(n%32)));}
#endif
 printf("actual-source deferred flags=%d: four creation paths, ordering, retries, handles, compaction, invalidation PASS\n",RE4DC_ALIVE_CAP_DEFER_FLAGS);
}
'''
with tempfile.TemporaryDirectory(prefix='castle-deferred-flags-')as tmp:
 p=Path(tmp)/'source.cpp';p.write_text(code+TEST)
 for enabled in [0,1]:
  exe=Path(tmp)/f'flags{enabled}'
  subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror','-Wno-unused-function','-fno-strict-aliasing','-fsanitize=address,undefined','-fno-omit-frame-pointer',f'-DRE4DC_ALIVE_CAP_DEFER_FLAGS={enabled}',str(p),'-o',str(exe)],check=True)
  subprocess.run([str(exe)],check=True)
print('Source-extracted queue/creator/wrapper checks passed with the feature disabled and enabled')
make=(ROOT/'port/dreamcast/game/Makefile').read_text()
block=re.search(r'# ALIVE_CAP_DEFER_FLAGS_BEGIN.*?# ALIVE_CAP_DEFER_FLAGS_END\n',make,re.S).group()
with tempfile.TemporaryDirectory(prefix='castle-deferred-make-')as tmp:
 p=Path(tmp)/'Makefile'
 targets=['obj/src/game/em_set.o','obj/mod/st2_1/src/st/em_wrap.o','obj/mod/st2_4/src/st/em_wrap_v2.o','obj/mod/st4_0/src/st/em_wrap_v3.o']
 p.write_text('ALIVE_CAP ?= 4\nOBJDIR := obj\n'+block+'\nall: '+' '.join(targets)+'\n'+''.join(t+":\n\t@printf '%s\\n' '$@=$(GAME_CPPFLAGS)'\n"for t in targets)+'.PHONY: all '+' '.join(targets)+'\n')
 for settings,ok,on in [([],True,False),(['ALIVE_CAP_DEFER_FLAGS=0'],True,False),(['ALIVE_CAP_DEFER_FLAGS=1'],True,True),(['ALIVE_CAP_DEFER_FLAGS=2'],False,False),(['ALIVE_CAP_DEFER_FLAGS='],False,False),(['ALIVE_CAP_DEFER_FLAGS=0 1'],False,False),(['ALIVE_CAP_DEFER_FLAGS=1','ALIVE_CAP=0'],False,False),(['ALIVE_CAP_DEFER_FLAGS=0','ALIVE_CAP=0'],True,False)]:
  r=subprocess.run(['make','-s','-f',str(p),'all',*settings],text=True,capture_output=True)
  assert (r.returncode==0)==ok,(settings,r.stdout,r.stderr)
  if ok:
   lines=r.stdout.splitlines();assert len(lines)==4
   assert all(('-DRE4DC_ALIVE_CAP_DEFER_FLAGS=1'in line)==on for line in lines),(settings,lines)
print('Eight Makefile default/off/on/invalid/cap-off cases and all wrapper variants: PASS')
game=(ROOT/'src/game/game.cpp').read_text();scenario=(ROOT/'src/game/sce_sys.cpp').read_text()
assert game.index('EmSetRoomInit();')<game.index('ScenarioRoomInit();')
init=function('ScenarioRoomInit',scenario)
assert init.index('RoomData.execInitFunc')<init.index('SceSys.scheduler()')<init.index('EmSetFromList();')
print('Original room reset precedes room-script sends and list creation: PASS')
