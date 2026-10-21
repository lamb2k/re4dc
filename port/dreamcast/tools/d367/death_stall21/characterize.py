#!/usr/bin/env python3
"""Characterize exact recovered damage functions; synthetic callers are not gameplay evidence."""
from pathlib import Path
import hashlib,json,subprocess,tempfile
root=Path(__file__).resolve().parents[5]
out=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/death-stall21-20261021')
def extract(rel,signature):
 s=(root/rel).read_text(); start=s.index(signature); a=s.index('{',start); depth=1; b=a+1
 while depth:
  depth += (s[b]=='{')-(s[b]=='}'); b+=1
 text=s[start:b]; receipts.append({'path':rel,'signature':signature,'source_file_sha256':hashlib.sha256(s.encode()).hexdigest(),'function_sha256':hashlib.sha256(text.encode()).hexdigest()});return text
receipts=[]
functions=[extract('src/game/em_sub.cpp','int LifeDownSet(cEm*'),extract('src/game/em_sub.cpp','int LifeDownSet2(cEm*'),extract('src/game/em_sub.cpp','void PlSetDamage(int'),extract('src/game/pl_class.cpp','void cPlayer::setDamage(u8'),extract('src/game/pl_dmg.cpp','void damageNormal(cPlayer* pl)\n{')]
stub=r"""
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cassert>
using s16=int16_t;using u16=uint16_t;using u8=uint8_t;using u32=uint32_t;using f32=float;
struct Vec {float x=0,y=0,z=0;};
struct Dmg {int m_Flag=0,m_Timer=0;void set(int a,int b){m_Flag=a;m_Timer=b;}};
struct Arc {int ofs[128]{};};
struct Model {Vec ang,world;};
using cModel=Model;
struct cEm {int id=0,hp=1200;};
struct cPlayer:cEm {Dmg dmg;void*subArc=nullptr,*subArc2=nullptr,*pMotion=nullptr;int r_no_0=0,r_no_1=0,r_no_2=0,r_no_3=0,m_Work0=0,m_Work1=0,m_Work2=0,m_ConDmTimer=0,m_ConDmFlag=0;float m_Fwork0=123,frame=0;Vec ang,pos;Model part,*pParts=&part;bool motionDone=false;void beginDamage(){};void setFace(int){};Model*getPartsPtr(int){return &part;};int motionMove(){return motionDone;};void setDamage(u8,int,float,int,int);};
struct G {u16 pl_life=1200,pl_life_max=1200,ashley_life=600,ashley_life_max=600;int Game_level=5;u32 Debug_flg[4]{};Arc* pPlayer=nullptr;} global,*pG=&global;
cPlayer player,*pPL=&player,*pPLS=&player; int seq[32]{},n=0;int Rnd(){return seq[n++];}
int PlIsArmor(){return 0;} void GameAddPoint(int){};
#define LVADD_PL_BIG_DAMAGE 1
#define LVADD_PL_DAMAGE 2
#define LVADD_EM_DAMAGE 3
#define LVADD_EM_DIE 4
#define HSet(x,v) ((x)=(v))
#define BitSet(x,v) ((x)=(v))
#define PI 3.1415927f
#define LIMIT_ANGLE(x) (x)
float Muku2(float,float,float){return 0;}
void PlRoutineSet(cPlayer*p,int a,int b,int c,int d){p->r_no_0=a;p->r_no_1=b;p->r_no_2=c;p->r_no_3=d;}
void MotionSetCore(cPlayer*,void*,void*,int,int,int,int){};
#define PL_ARC_PTR(a,n) ((void*)(uintptr_t)(n))
void PlSetDamageSe(int){};void EndPlDamage(){};int ChkWaterEffectEnable(Vec*){return 0;}
int EstSet(int,int,int,int,int,int,int,int,u32,int){return 0;}
int MotionCheckCrossFrame(void*,float){return 0;}int GetWaterHeight(Vec*,float*){return 0;}void SndCall(int,int,Vec*,int,int,int){};
struct Log{void err(int,int,const char*,int){abort();}}logobj,*pLog=&logobj;
struct KeyT{int on=0;}Key;
int LifeDownSet2(cEm*,int,int,int);
"""
tests=r"""
void reset(int life,int finalRnd=0){global=G{};global.pl_life=life;static Arc arc;global.pPlayer=&arc;player=cPlayer{};player.pParts=&player.part;for(auto&v:seq)v=0;seq[2]=finalRnd;n=0;}
int main(){
 reset(440);assert(LifeDownSet2(pPL,800,0,0)==1);assert(n==3);
 reset(440,1);assert(LifeDownSet2(pPL,800,0,0)==0);
 reset(1);assert(LifeDownSet2(pPL,1,0,0)==0);
 reset(0);assert(LifeDownSet2(pPL,0,0,1)==0);assert(global.pl_life==0);
 reset(440);PlSetDamage(0,800,0);assert(global.pl_life==1&&player.r_no_0==1&&player.r_no_3==0);
 reset(440,1);PlSetDamage(0,800,0);assert(global.pl_life==0&&player.r_no_0==2);
 reset(440);PlSetDamage(6,800,0);assert(global.pl_life==1&&player.r_no_0==1&&player.r_no_3==6);damageNormal(&player);player.motionDone=true;damageNormal(&player);assert(global.pl_life==1&&player.r_no_0==2&&player.r_no_1==2);assert(!((s16)global.pl_life<=0));
 reset(440);PlSetDamage(7,800,0);assert(global.pl_life==1&&player.r_no_0==1&&player.r_no_1==1);
 reset(10);assert(LifeDownSet(pPL,20,1)==0);assert(n==2); // rnd=1, flag=0; swapped keep1 would leave 1
 puts("9 exact-source characterization cases pass; synthetic type6 caller is not runtime attribution");
}
"""
with tempfile.TemporaryDirectory(prefix='death-stall21-') as d:
 d=Path(d);src=d/'characterize.cpp';src.write_text(stub+'\n'.join(functions)+tests)
 subprocess.run(['g++','-std=c++17','-fpermissive','-w','-fsanitize=undefined','-O1',str(src),'-o',str(d/'characterize')],check=True)
 result=subprocess.run([str(d/'characterize')],capture_output=True,text=True,check=True)
 report={'scope':'Actual-source host characterization with narrow stubs; synthetic incoming callers; not Flycast or hardware','source_head':subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip(),'functions':receipts,'stdout':result.stdout,'cases':9,'sanitizer':'UBSan','runtime_repair':False}
 (out/'actual-source-host-characterization.json').write_text(json.dumps(report,indent=2));print(result.stdout)
