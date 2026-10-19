#!/usr/bin/env python3
"""Run the actual backing helpers and original healing decisions without game assets.

Host layouts/backing transport and UI rendering are mocked. The extracted source
bodies, original ItemMgr.use, healing eligibility, WHO arms and motion resets are
not reimplemented. This is not a guest, rendered-menu or hardware acceptance test.
"""
from pathlib import Path
import argparse, hashlib, json, subprocess, tempfile

ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path);ap.add_argument('--output',type=Path)
a=ap.parse_args();root=a.root or Path(__file__).resolve().parents[5]
out=a.output or Path(tempfile.mkdtemp(prefix='re4dc-ss-actor-'));out.mkdir(parents=True,exist_ok=True)
records=[]
def read(path):return (root/path).read_text()
def function(text,signature):
    start=text.index(signature);brace=text.index('{',start);i=brace+1;depth=1
    while depth:
        depth+=(text[i]=='{')-(text[i]=='}');i+=1
    return text[start:i]
def record(label,body):
    records.append({'label':label,'sha256':hashlib.sha256(body.encode()).hexdigest()});return body

bridge=read('port/dreamcast/game/sscrn_bridge.cpp');npc=read('src/game/pl_npc.cpp')
sub=read('src/game/pl_sub.cpp');item=read('src/game/item.cpp');puzzle=read('src/Sscrn/ss_pzzl.cpp')
start=bridge.index('// Resident backing-session metadata;');end=bridge.index('\n#endif',start)
helpers=record('actual backing metadata and API bodies',bridge[start:end])
header=read('include/re4dc_subscreen_actor.h').replace('#include "types.h"','')
original_condition=function(npc,'u32 SubCharGetCondition()')
feature_start=original_condition.index('#if defined(RE4DC_SS_ACTOR_LIFETIME)');feature_end=original_condition.index('#endif',feature_start)+len('#endif')
original_condition=(original_condition[:feature_start]+original_condition[feature_end:]).replace('SubCharGetCondition()','OriginalCondition()')
resets=[]
for sig in ['void PlMotionReset()','int SubCharMotionReset()']:
    body=record(sig,function(sub,sig));name=sig.split()[1].split('(')[0]
    resets.append(body.replace(name+'()','Source'+name+'()'))
entry=function(bridge,'extern "C" void re4dc_subscreen_swap_open')
close=function(bridge,'extern "C" void re4dc_subscreen_swap_close')
# Static source-order checks bind the host transport model to the actual hook sites.
assert entry.index('if (swapped) re4dc_missing(')<entry.index('open_hash = h;')<entry.index('ss_actor_capture(wk);')<entry.index('memset(wk->pBuf, 0, kSsAramSize);')
assert entry.index('re4dc_ssb_get(reinterpret_cast<void*>(lo), scratch);')<entry.index('ss_actor_capture(wk);')
assert close.index('re4dc_actor_swap_unpark(h == open_hash);')<close.index('if (h != open_hash) re4dc_missing(')<close.index('ss_actor_restore(wk);')
assert 'TaskSignal' not in helpers and 'Stop_flg' not in helpers
system_reset=function(read('src/game/main.cpp'),'void systemResetCommon()')
core_exit=function(read('src/game/sscrn.cpp'),'void SubScreenExitCore(SubScreenWork* wk)')
assert system_reset.index('SubScreenExitCore(&SubScreenWk);')<system_reset.index('TaskAllClear();')<system_reset.index('ReleasePlData();')
assert core_exit.index('re4dc_subscreen_swap_close(wk);')<core_exit.index('RoomData.restartRelData();')<core_exit.index('MGR_PTR(cModel::mm) = &ModInfoMgr;')
record('unchanged source system-reset close before task/player teardown',system_reset)
record('unchanged source close before room/model-manager restart',core_exit)
close_guard=close[close.index('    if (h != open_hash) re4dc_missing('):close.rfind('}')]
record('actual final close hash guard and deferred-reset hook',close_guard)
start=puzzle.index('            case 4:\n#if defined(RE4DC_SS_ACTOR_LIFETIME)',puzzle.index('void PieceCommand::move'))
who=puzzle[start+len('            case 4:'):puzzle.index('            case 5:',start)]
start=puzzle.index('            case 4:\n                if (subSel == 0)',start)
recipient=puzzle[start+len('            case 4:'):puzzle.index('            case 6:',start)]
assert 'wk->healing' in recipient and 're4dc_ss_actor_reset(1)' in recipient
cancel_start=puzzle.rfind('if (Key.trg & 0x40000000)',0,start)
cancel=puzzle[cancel_start:puzzle.index('} else if',cancel_start)]
assert 'ItemMgr.use' not in cancel and 'MotionReset' not in cancel and 're4dc_ss_actor_reset' not in cancel
record('actual WHO initial Use arm',who);record('actual WHO recipient Use arm',recipient);record('original cancel branch has no use/reset',cancel)
ss=read('src/game/sscrn.cpp');start=ss.index('            if (pSUB && pSUB->id == 3) {',ss.index('wk->alpha_cnt = 0;'))
eligibility=ss[start:ss.index('            BitOn(',start)];record('original pre-swap healing classification',eligibility)

host=r'''
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <vector>
#include <stdexcept>
using u8=uint8_t;using u16=uint16_t;using s16=int16_t;using u32=uint32_t;using s32=int32_t;using f32=float;
#define RE4DC_SS_ACTOR_LIFETIME 1
struct Vec {float x=0,y=0,z=0;};
float GetDistance(Vec a,Vec b){return (a.x-b.x)*(a.x-b.x)+(a.y-b.y)*(a.y-b.y)+(a.z-b.z)*(a.z-b.z);}
struct FlagView {u32 bits;bool check(int i)const{return (bits&(1U<<i))!=0;}};
struct cPlayer {u8 id=0,r_no_0=0,r_no_1=0,r_no_2=5,r_no_3=8;u32 stat=0;u8 x4FC=7,x4FD=9;Vec pos;};
struct cSubChar {u8 id=3,r_no_0=0,r_no_1=1,r_no_2=5,r_no_3=8;u32 stat=0;u16 subFlags=0;Vec pos;};
using cModel=cSubChar;
FlagView flagView;FlagView* flags(cSubChar*s){flagView.bits=s->subFlags;return &flagView;}
#define SUBFLAG(s) flags(s)
struct GlobalWork {u32 Status_flg[4]{};u16 room_id=0x207,pl_life=720,pl_life_max=1440,ashley_life=360,ashley_life_max=600;u8 pl_type=0;u32 ammo=10,Stop_flg=0;};
GlobalWork global,otherGlobal;GlobalWork*pG=&global;
cPlayer player,otherPlayer;cPlayer*pPL=&player;cSubChar partner,otherPartner;cSubChar*pSUB=&partner;
#define G_ROOM_ID (pG->room_id)
struct SubScreenWork {void*pBuf;int healing=0;};using SUB_SCREEN=SubScreenWork;
unsigned char window[128],otherWindow[128];SubScreenWork screen{window},otherScreen{window};
std::vector<int> resetOrder;bool transportRestored=false;
void PlMotionReset();int SubCharMotionReset();
struct ItemWork{u16 id=5,num=1;u8 flags=1;};struct ItemInfo{};
struct cItemMgr {int m_to_whom=0;u32 m_pAvailable[16]{};int used_id=0;void flagclear(){};int use(ItemWork*); } ItemMgr;
struct Debug {u32 Debug_flg[4]{};}debug;Debug*pGS=&debug;
#define ITEM_TYPE(id) ((id)==0x100?1:0)
#define U16Set(x,y) ((x)=u16(y))
int healing(u16);
int mode=0,subSel=0,lastMessage=0;ItemWork spray;struct Selection{ItemWork*item=&spray;} selection;Selection*pzzl_sel=&selection;
void SndCall(int,int,int,int,int,int){}
void openMsgWindow(SubScreenWork*,int n){lastMessage=n;}
u32 open_hash=0x12345678;
[[noreturn]]void re4dc_missing(const char*){throw std::runtime_error("existing fatal");}
'''
host+=header+'\n'+'\n'.join(resets)+r'''
void PlMotionReset(){resetOrder.push_back(0);SourcePlMotionReset();}
int SubCharMotionReset(){resetOrder.push_back(1);return SourceSubCharMotionReset();}
'''+helpers+'\n'+record('current SubCharGetCondition',function(npc,'u32 SubCharGetCondition()'))+'\n'+original_condition+'\n'
for text,sig in [(sub,'int SubCharCheckHealing()'),(item,'int healing(u16 n)'),(item,'int lifeLevel(int levels'),(item,'static inline int useSubChar(cItemMgr* m)'),(item,'int cItemMgr::use(ItemWork* p)')]:
    host+=record(sig,function(text,sig))+'\n'
host+='void classify(SubScreenWork*wk){\n'+eligibility+'}\n'
host+='void initialUseBody(SubScreenWork*wk,int&used){do{\n'+who+'\n}while(0);}\nint initialUse(SubScreenWork*wk){int used=0;initialUseBody(wk,used);return used;}\n'
host+='int recipientUse(SubScreenWork*wk){int used=0,msg=0;do{\n'+recipient+'\n}while(0);return used;}\n'
host+='void checkedClose(SubScreenWork*wk,u32 h){\n'+close_guard+'}\n'
host+=r'''
void reset(){global=GlobalWork{};otherGlobal=GlobalWork{};pG=&global;player=cPlayer{};otherPlayer=cPlayer{};partner=cSubChar{};otherPartner=cSubChar{};pPL=&player;pSUB=&partner;screen={window};otherScreen={window};ss_actor_backing={};resetOrder.clear();mode=subSel=lastMessage=0;ItemMgr={};spray={};selection.item=&spray;}
void poison(){player.id=0xF1;player.stat=0xFFFFFFFF;player.r_no_0=0x81;partner.id=0;partner.subFlags=0xFFFF;partner.stat=0xFFFFFFFF;partner.r_no_0=0x82;partner.r_no_1=0x83;}
int main(){
 unsigned long long frozenCases=0;unsigned lifecycleCases=0;
 // Every routine byte, source flag priority and relevant stat category. Deliberately
 // corrupt both actor objects while global Status_flg remains live.
 for(unsigned r0=0;r0<256;r0++)for(unsigned r1=0;r1<256;r1++)for(unsigned f=0;f<4;f++)for(unsigned st=0;st<3;st++){
  reset();partner.r_no_0=r0;partner.r_no_1=r1;partner.subFlags=((f&1)?2:0)|((f&2)?8:0);partner.stat=st==0?0:st==1?0x00100000:0x000F0000;player.stat=0xF0000;
  auto oldP=player;auto oldS=partner;u32 expected[2];for(int bit=0;bit<2;bit++){pG->Status_flg[1]=bit?0x10000:0;expected[bit]=OriginalCondition();}
  ss_actor_capture(&screen);poison();auto poisonedP=player;auto poisonedS=partner;
  assert(re4dc_ss_actor_is_ashley()&&re4dc_ss_actor_has_partner()&&re4dc_ss_actor_player_stat()==0xF0000);
  for(int bit=0;bit<2;bit++){pG->Status_flg[1]=bit?0x10000:0;assert(SubCharGetCondition()==expected[bit]);frozenCases++;}
  re4dc_ss_actor_reset(1);re4dc_ss_actor_reset(0);re4dc_ss_actor_reset(1);re4dc_ss_actor_reset(99);
  assert(resetOrder.empty()&&memcmp(&player,&poisonedP,sizeof player)==0&&memcmp(&partner,&poisonedS,sizeof partner)==0);
  player=oldP;partner=oldS;checkedClose(&screen,open_hash);assert((resetOrder==std::vector<int>{0,1}));
  assert(!ss_actor_backing.active&&ss_actor_backing.pending==0);assert(SubCharGetCondition()==expected[1]);
  assert(pG->pl_life==720&&pG->ashley_life==360&&pG->ammo==10);auto afterP=player;auto afterS=partner;checkedClose(&screen,open_hash);assert(resetOrder.size()==2&&memcmp(&player,&afterP,sizeof player)==0&&memcmp(&partner,&afterS,sizeof partner)==0);
 }
 // Original pre-open eligibility is frozen by the existing screen work; null,
 // non-Ashley, near, far and busy all use the actual original decision arms.
 for(int scenario=0;scenario<5;scenario++){
  reset();if(scenario==0)pSUB=nullptr;if(scenario==1)partner.id=2;if(scenario==3)partner.pos.x=5001;if(scenario==4)partner.r_no_0=1;
  classify(&screen);assert(screen.healing==(scenario==2?1:scenario==4?-1:0));auto oldP=player;auto oldS=partner;ss_actor_capture(&screen);poison();
  if(scenario<2){assert(initialUse(&screen)==1);assert(pG->pl_life==1440&&spray.num==0&&ss_actor_backing.pending==1);}
  else {assert(initialUse(&screen)==0&&mode==1&&spray.num==1);subSel=1;int used=recipientUse(&screen);assert(used==(scenario==2));assert(ss_actor_backing.pending==(scenario==2?2U:0U));if(scenario==3)assert(lastMessage==0x25);if(scenario==4)assert(lastMessage==0x26);}
  assert(resetOrder.empty());player=oldP;partner=oldS;checkedClose(&screen,open_hash);assert(resetOrder.size()==(scenario<=2?1:0));lifecycleCases++;
 }
 // Real original ItemMgr.use and health saturation: repeated successful uses,
 // failed full-health uses and both orders of mixed recipients, no ammo rollback.
 for(int order=0;order<2;order++){
  reset();classify(&screen);auto oldP=player;auto oldS=partner;ss_actor_capture(&screen);poison();
  for(int j=0;j<2;j++){int target=(j+order)%2;subSel=target;spray={};assert(recipientUse(&screen)==1);assert(spray.num==0&&spray.flags==0);spray={};assert(recipientUse(&screen)==0&&spray.num==1);}
  // A second use after a live global injury does not read stale captured health.
  pG->ashley_life=200;subSel=1;assert(recipientUse(&screen)==1&&pG->ashley_life==600);assert(resetOrder.empty()&&ss_actor_backing.pending==3);
  pG->ammo=7;pG->Status_flg[1]=0x10000;player=oldP;partner=oldS;checkedClose(&screen,open_hash);assert((resetOrder==std::vector<int>{0,1}));assert(pG->pl_life==1440&&pG->ashley_life==600&&pG->ammo==7&&pG->Status_flg[1]==0x10000);lifecycleCases++;
 }
 // The original yellow-herb branch raises live maximum health; neither current
 // nor maximum health is rolled back when the source actor backing returns.
 for(int target=0;target<2;target++)for(int kind=0;kind<2;kind++){
  reset();classify(&screen);auto oldP=player;auto oldS=partner;ss_actor_capture(&screen);poison();subSel=target;spray.id=kind?0x16:0x15;
  auto oldMax=target?pG->ashley_life_max:pG->pl_life_max;assert(recipientUse(&screen)==1);assert((target?pG->ashley_life_max:pG->pl_life_max)>oldMax);auto live=*pG;
  assert(resetOrder.empty()&&ss_actor_backing.pending==(1U<<target));player=oldP;partner=oldS;checkedClose(&screen,open_hash);assert(memcmp(pG,&live,sizeof live)==0&&resetOrder.size()==1&&resetOrder[0]==target);lifecycleCases++;
 }
 // Cancel/no Use, close/reopen and rejected-open ordering: no retained reset.
 reset();ss_actor_capture(&screen);auto before=ss_actor_backing;try{re4dc_missing("sub screen area swapped twice");}catch(const std::runtime_error&){}assert(memcmp(&before,&ss_actor_backing,sizeof before)==0);checkedClose(&screen,open_hash);assert(resetOrder.empty());
 re4dc_ss_actor_reset(0);assert(resetOrder.size()==1);resetOrder.clear();ss_actor_capture(&screen);checkedClose(&screen,open_hash);assert(resetOrder.empty());lifecycleCases++;
 // Restore corruption reaches the existing fatal BEFORE delivery. It does not
 // clear, resume or silently accept the invalid transaction.
 reset();ss_actor_capture(&screen);re4dc_ss_actor_reset(1);try{checkedClose(&screen,open_hash^1);assert(false);}catch(const std::runtime_error&){}assert(resetOrder.empty()&&ss_actor_backing.active&&ss_actor_backing.pending==2);lifecycleCases++;
 // Every captured identity, plus null globals/actors and room/system reset.
 for(int change=0;change<10;change++){
  reset();ss_actor_capture(&screen);re4dc_ss_actor_reset(0);re4dc_ss_actor_reset(1);SubScreenWork*wk=&screen;
  switch(change){case 0:pG=&otherGlobal;break;case 1:pG=nullptr;break;case 2:pPL=&otherPlayer;break;case 3:pSUB=&otherPartner;break;case 4:wk=&otherScreen;break;case 5:screen.pBuf=otherWindow;break;case 6:global.room_id++;break;case 7:player.id++;break;case 8:partner.id++;break;case 9:pPL=nullptr;pSUB=nullptr;break;}
  checkedClose(wk,open_hash);assert(resetOrder.empty()&&!ss_actor_backing.active&&ss_actor_backing.pending==0);lifecycleCases++;
 }
 reset();pPL=nullptr;pSUB=nullptr;ss_actor_capture(&screen);assert(!re4dc_ss_actor_has_partner()&&!re4dc_ss_actor_is_ashley()&&SubCharGetCondition()==0);re4dc_ss_actor_reset(0);re4dc_ss_actor_reset(1);checkedClose(&screen,open_hash);assert(resetOrder.empty());lifecycleCases++;
 printf("frozen_condition_cases=%llu lifecycle_cases=%u actual_source_use_healing_reset=PASS identity_reset_hash_order=PASS\n",frozenCases,lifecycleCases);
}
'''
cpp=out/'actual-source-ss-actor-lifetime.cpp';cpp.write_text(host)
exe=out/'actual-source-ss-actor-lifetime';command=['g++','-std=c++20','-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer',str(cpp),'-o',str(exe)]
r=subprocess.run(command,capture_output=True,text=True);(out/'compile.txt').write_text(r.stdout+r.stderr);assert r.returncode==0,r.stderr
r=subprocess.run([str(exe)],capture_output=True,text=True);(out/'run.txt').write_text(r.stdout+r.stderr);assert r.returncode==0,r.stdout+r.stderr
assert 'frozen_condition_cases=1572864' in r.stdout
proof={'status':'SOURCE_ACTOR_LIFETIME_PASS','compiler':command,'output':r.stdout.strip(),'extracted_sources':records,'harness_sha256':hashlib.sha256(cpp.read_bytes()).hexdigest(),'limits':__doc__,'source_order_checks':['capture after SS_PACK scratch restored and successful backing open','capture before actor window clear','restore after existing full-hash fatal','cancel source branch cannot use item or request reset','helper has no task-resume or stop flag changes']}
(out/'proof.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'status':proof['status'],'output':proof['output'],'proof':str(out/'proof.json')}))
