#!/usr/bin/env python3
"""Exercise actual r207 queued-command bodies and original Ganado setter."""
from pathlib import Path
import argparse,re,subprocess,tempfile
ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path);args=ap.parse_args();ROOT=args.root or Path(__file__).resolve().parents[5]
# Reuse the preceding source-extraction harness, not an alternate queue implementation.
base=(ROOT/'port/dreamcast/tools/d367/castle18/test_deferred_wrapper_flags.py').read_text()
namespace={'__file__':str(ROOT/'port/dreamcast/tools/d367/castle18/test_deferred_wrapper_flags.py'),'__name__':'queue_harness'}
exec(base[:base.index('macro=SOURCE[')],namespace)
HOST=namespace['HOST'];SOURCE=namespace['SOURCE'];WRAP=namespace['WRAP'];function=namespace['function']
HOST=HOST.replace('room_no=0xc,room_id=0x20c','room_no=7,room_id=0x207')
HOST=HOST.replace('static u32 flagsAtFirstMove;','static u32 flagsAtFirstMove,initialFlags=0x100,initialWork=0x800100;\nstruct Em10Work {u32 flags=0;int Goto_mode=0;Vec x5F0,Goto_pos;};')
HOST=HOST.replace('Vec pos,pos_old,ang;','Vec pos,pos_old,ang;Em10Work work;void setGoto(Vec*,int);int ckGoto(){return work.Goto_mode;}')
HOST=HOST.replace('flag=0x100;active=0;','flag=initialFlags;work.flags=initialWork;active=0;')
HOST=HOST.replace('void setFlag(u32);','void setFlag(u32);void setGoto(Vec*,int);int ckGoto();int isNormalGanade();')
HOST+='\nusing cEmGanado=cEm;using cEm10=cEm;\n#define EM10_WK(e) (&((e)->work))\nstruct Floor {bool missing=false;int calls=0;float getFloor(Vec*v,float a,float b,int c,int d){assert(a==600&&b==100000&&c==0&&d==0);calls++;return missing?-100000:v->x-v->z;}} SatMgr;\n'
start=SOURCE.index('struct AliveCapPendingGoto');end=SOURCE.index('\n#endif',start)
HOST+='\n#if RE4DC_ALIVE_CAP_DEFER_GOTO_R207\n'+SOURCE[start:end]+'\n#endif\n'
em10=(ROOT/'src/em10/em10.cpp').read_text();setter=function('cEm10::setGoto',em10)
macro=SOURCE[SOURCE.index('#define EM_SET_WORK('):SOURCE.index('// Squared XZ distance')]
base_names=['EmSetWork','EmSetDist','checkListId','aliveCapGanado','aliveCapEnemy','aliveCapWaitingK']
feature_names=['aliveCapGotoR207Eligible','re4dc_aliveCapSetGotoR207','re4dc_aliveCapGetGotoR207','aliveCapDeliverGotoR207']
queue_names=['aliveCapPush','aliveCapNoteFresh','aliveCapLive','re4dc_aliveCapHeldEntry','re4dc_aliveCapTake','re4dc_aliveCapHeldCount','re4dc_aliveCapDestroy','re4dc_aliveCapFarDrop','re4dc_aliveCapMove','re4dc_aliveCapDefer','EmSetFromList','EmSetFromList2','EmSetRoomInit']
code=HOST+setter+'\n'+macro+'\n'.join(function(n)for n in base_names)+'\n'+function('re4dc_aliveCapSetFlag')+'\n#if RE4DC_ALIVE_CAP_DEFER_GOTO_R207\n'+'\n'.join(function(n)for n in feature_names)+'\n#endif\n'+'\n'.join(function(n)for n in ['aliveCapApplyPending','aliveCapRestorePending']+queue_names)
code+='\n'+function('emWrapHeld',WRAP)+'\n#define EM_WRAP_HELD(w) emWrapHeld(w)\n'+function('emWrapLive',WRAP)+'\n'
code+='\n'.join(function('cEmWrap::'+n,WRAP)for n in ['initWork','setFlag','getPtr','isAlive','isActive','destroy','isNormalGanade','setGoto','ckGoto'])
TEST=r"""
static void reset(int room=0x207){
 global=Global{};global.room_id=room;global.stage_no=room>>8;global.room_no=room&255;player=cEm{};pPL=&player;
 for(auto&e:pool)e=cEm{};memset(dead,0,sizeof dead);aliveCapN=aliveCapReleasing=0;aliveCapLast=0;
 memset(aliveCapFreshEm,0,sizeof aliveCapFreshEm);failCreate=firstMoves=errors=0;flagsAtFirstMove=0;errEm=nullptr;
 initialFlags=0x100;initialWork=0x800100;SatMgr.missing=false;SatMgr.calls=0;EmSetRoomInit();
}
static cEmWrap hold(int no,int sent=1,int id=0x1b,int distance=1){
 auto&d=*EM_LIST(no);d=EmListData{};d.room=global.room_id;d.id=id;d.be_flag=sent?0:1;d.pos[0]=distance;
 aliveCapPush(no,sent);cEmWrap w;w.no=no;w.alive=2;return w;
}
static Vec target(int n){return Vec{float(100*n+7),float(n*10),float(3*n-9)};}
static bool equal(Vec a,Vec b){return a.x==b.x&&a.y==b.y&&a.z==b.z;}
static bool equal(const cEm&a,const cEm&b){return a.flag==b.flag&&a.work.flags==b.work.flags&&a.work.Goto_mode==b.work.Goto_mode&&equal(a.work.x5F0,b.work.x5F0)&&equal(a.work.Goto_pos,b.work.Goto_pos);}
static void commands(cEmWrap&w,int n){auto v=target(n);w.setFlag(0x20);w.setGoto(&v,13);w.setFlag(0x40);v=target(n+1);w.setGoto(&v,0);v={999,999,999};}
static cEm reference(int n){cEm e;e.move();e.flag|=0x20;auto v=target(n);e.setGoto(&v,13);e.flag|=0x40;v=target(n+1);e.setGoto(&v,0);return e;}
static cEm* release(cEmWrap&w,int path){if(path==0){re4dc_aliveCapMove(0);return GetEmPtrFromList(w.no);}if(path==1)return w.getPtr();if(path==2)return EmSetFromList2(w.no,1);EmSetFromList();return GetEmPtrFromList(w.no);}
int main(){int deliveries=0;
 // All four actual creation routes, post-init ordering, floor behavior, protected work and valid mode0.
 for(int path=0;path<4;path++)for(int base=0;base<2;base++)for(int bits=0;bits<8;bits++)for(int floor=0;floor<2;floor++){
  reset();initialFlags|=base?0x40:0;initialWork=((bits&1)?0x100:0)|((bits&2)?0x4000:0)|((bits&4)?0x800000:0);SatMgr.missing=floor;
  auto a=hold(6,path==3?0:1);auto shared=a;commands(a,3);assert(firstMoves==0&&SatMgr.calls==0&&EM_LIST(6)->flag==0);
#if RE4DC_ALIVE_CAP_DEFER_GOTO_R207
  assert(shared.ckGoto()==0&&aliveCapPendingGoto[0].valid&&aliveCapPendingGoto[0].firstFlags==0x20);
#endif
  auto e=release(a,path);assert(e&&flagsAtFirstMove==0&&firstMoves==1);auto expected=reference(3);
#if RE4DC_ALIVE_CAP_DEFER_GOTO_R207
  assert(equal(*e,expected));
#else
  assert(e->work.Goto_mode==0&&e->flag==(initialFlags|0x60));
#endif
  assert(shared.getPtr()==e);auto v=target(99);expected=*e;expected.setGoto(&v,13);shared.setGoto(&v,13);assert(equal(*e,expected));deliveries++;
 }
 // Shared handle mode waits; caller vector lifetime cannot change copied command.
 reset();auto a=hold(1);auto b=a;auto v=target(1);a.setGoto(&v,13);v={};aliveCapPush(1,1);re4dc_aliveCapMove(1);assert(firstMoves==0);
#if RE4DC_ALIVE_CAP_DEFER_GOTO_R207
 assert(b.ckGoto()==13&&equal(aliveCapPendingGoto[0].pos,target(1)));
#else
 assert(b.ckGoto()==0);
#endif
 re4dc_aliveCapMove(0);assert(a.getPtr()==b.getPtr());
 // Room-scoped eligibility: other rooms, Merchant, Novistador and unrelated IDs keep old behavior.
 for(int room: {0x101,0x206,0x214,0x300}){reset(room);a=hold(1);v=target(1);a.setGoto(&v,13);assert(a.ckGoto()==0);auto e=a.getPtr();assert(e&&e->work.Goto_mode==0);}
 for(int id: {0x18,0x2d,0x25,0x3c}){reset();a=hold(1,1,id);v=target(1);a.setGoto(&v,13);assert(a.ckGoto()==0);auto e=a.getPtr();assert(e&&e->work.Goto_mode==0);}
#if RE4DC_ALIVE_CAP_DEFER_GOTO_R207
 reset();a=hold(1);assert(!re4dc_aliveCapSetGotoR207(-1,&v,1)&&!re4dc_aliveCapSetGotoR207(256,&v,1)&&!re4dc_aliveCapSetGotoR207(1,nullptr,1));
 // Failed creator never consumes command (including nonnull error sentinel).
 for(int path=0;path<4;path++)for(int sent=0;sent<2;sent++){
  reset();a=hold(6,path==3?0:1);commands(a,6);errEm=sent?&sentinel:nullptr;failCreate=1;auto failed=release(a,path);assert(failed==nullptr||failed==errEm);assert(aliveCapN==1&&firstMoves==0&&aliveCapPendingGoto[0].valid);
  failCreate=0;global.Frame_cnt+=30;auto e=release(a,path);assert(e&&e!=errEm&&equal(*e,reference(6)));
 }
 // Full64 middle failed Take restores exact order and all command ownership.
 reset();for(int n=0;n<64;n++){a=hold(n);v=target(n);a.setGoto(&v,n);}a.no=31;a.alive=2;failCreate=1;assert(!a.getPtr()&&aliveCapN==64);
 for(int n=0;n<64;n++)assert(aliveCapHeld[n]==n&&aliveCapPendingGoto[n].mode==n&&equal(aliveCapPendingGoto[n].pos,target(n)));
 failCreate=0;assert(a.getPtr()->work.Goto_mode==31&&aliveCapN==63&&aliveCapHeld[31]==32&&aliveCapPendingGoto[31].mode==32);
 // Automatic middle failure and each compaction: commands never migrate to another entry.
 reset();a=hold(1,0,0x1b,1);b=hold(2,1,0x1b,100);auto c=hold(3,1,0x1b,2);commands(a,1);commands(b,2);commands(c,3);failCreate=1;re4dc_aliveCapMove(0);
 assert(aliveCapN==3&&aliveCapHeld[1]==2&&aliveCapPendingGoto[1].firstFlags==0x20);failCreate=0;global.Frame_cnt+=30;re4dc_aliveCapMove(0);assert(equal(*GetEmPtrFromList(2),reference(2))&&equal(aliveCapPendingGoto[1].pos,target(4)));
 reset();a=hold(1);b=hold(2,1,0x11);c=hold(3);commands(a,1);commands(b,2);commands(c,3);re4dc_aliveCapDestroy(0x11,-1);assert(aliveCapHeld[1]==3&&equal(*c.getPtr(),reference(3)));
 reset();a=hold(1);b=hold(2);c=hold(3,1,0x2d);commands(a,1);commands(b,2);assert(re4dc_aliveCapFarDrop(1,0)==1);assert(aliveCapHeld[1]==3&&equal(*a.getPtr(),reference(1)));
 reset();a=hold(1);b=hold(2);commands(a,1);commands(b,2);EM_LIST(1)->room=0x214;re4dc_aliveCapMove(0);assert(!GetEmPtrFromList(1)&&equal(*GetEmPtrFromList(2),reference(2)));
 reset();a=hold(1);commands(a,1);dead[1]=true;re4dc_aliveCapMove(0);assert(aliveCapN==0&&firstMoves==0);dead[1]=false;a=hold(1);assert(a.getPtr()->work.Goto_mode==0);
 reset();a=hold(1);commands(a,1);a.destroy();a=hold(1);assert(a.getPtr()->work.Goto_mode==0);
 reset();a=hold(1);commands(a,1);EmSetRoomInit();assert(aliveCapN==1&&!aliveCapPendingGoto[0].valid&&a.ckGoto()==0&&a.getPtr()->work.Goto_mode==0);
 reset();a=hold(1);commands(a,1);*EM_LIST(1)=EmListData{};EmSetRoomInit();a=hold(1);v=target(9);a.setGoto(&v,13);assert(equal(a.getPtr()->work.Goto_pos,target(9)));
 // Direct delivery cannot apply old r207 Goto metadata to another room or changed class.
 reset();a=hold(1);commands(a,1);global.room_id=0x214;global.room_no=0x14;EM_LIST(1)->room=0x214;assert(a.ckGoto()==0&&a.getPtr()->work.Goto_mode==0);
 reset();a=hold(1);commands(a,1);EM_LIST(1)->id=0x2d;assert(a.ckGoto()==0&&a.getPtr()->work.Goto_mode==0);
 // Original start-list compaction also keeps the right command.
 reset();a=hold(1,0);b=hold(2,0);commands(a,1);commands(b,2);EM_LIST(1)->room=0x214;EmSetFromList();assert(!GetEmPtrFromList(1)&&equal(*GetEmPtrFromList(2),reference(2)));
#endif
 printf("actual-source r207 goto=%d: %d creator/order/floor/work cases plus scope/retry/lifecycle PASS\n",RE4DC_ALIVE_CAP_DEFER_GOTO_R207,deliveries);
}
"""
with tempfile.TemporaryDirectory(prefix='castle-r207-goto-')as d:
 p=Path(d)/'source.cpp';p.write_text('#include <initializer_list>\n'+code+TEST)
 for enabled in [0,1]:
  exe=Path(d)/f'goto{enabled}'
  subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror','-Wno-unused-function','-Wno-misleading-indentation','-Wno-unused-but-set-variable','-fno-strict-aliasing','-fsanitize=address,undefined','-fno-omit-frame-pointer','-DRE4DC_ALIVE_CAP_DEFER_FLAGS=1',f'-DRE4DC_ALIVE_CAP_DEFER_GOTO_R207={enabled}',str(p),'-o',str(exe)],check=True)
  subprocess.run([str(exe)],check=True)
