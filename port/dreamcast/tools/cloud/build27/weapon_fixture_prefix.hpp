#pragma once
// Synthetic service boundary for executing unchanged recovered weapon sources.
// This is a host control-flow fixture, not a model of the SH-4 object ABI.
#include <algorithm>
#include <array>
#include <cassert>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <initializer_list>
#include <limits>
#include <new>
#include <string>
#include <type_traits>
#include <vector>

using u8=std::uint8_t; using u16=std::uint16_t;
using u32=std::uintptr_t; // Preserve host pointers in source archive arithmetic.
using s8=std::int8_t; using s16=std::int16_t; using s32=std::intptr_t;
using f32=float;
constexpr u32 RE4_MEM_LO=1, RE4_MEM_HI=std::numeric_limits<u32>::max();
constexpr float PI=3.14159265358979323846f;
struct Vec { float x=0,y=0,z=0; };
using Mtx=float[3][4];
struct MotionWork { unsigned state=0; };
struct VibDataTbl {};
struct PlArc { u32 ofs_1C=0; std::array<void*,128> entries{}; };
class cModel; class cObj; class cObjWep; class cPlayer;

namespace fixture {
struct Call { std::string name; std::vector<std::intptr_t> args; std::vector<float> values; };
inline std::vector<Call> calls;
inline bool model_ok=true, create_ok=true, cartridge_ok=true, cross_frame=false;
inline bool motion_done=false, aim_held=true, fire_held=false, fire_trg=false;
inline bool reloadable=true, reload_key=false, damage_motion=true;
inline int bullets=3, reload_capacity=50, snd_result=0x1234;
inline unsigned create_id=0;
inline cObjWep* created=nullptr;
inline float camera_direction=0.25f,camera_pitch=0.125f;
inline std::array<float,8> random_values{};
inline unsigned random_index=0;
template<class T> inline std::intptr_t word(T v) {
    if constexpr(std::is_pointer_v<T>) return reinterpret_cast<std::intptr_t>(v);
    else return static_cast<std::intptr_t>(v);
}
inline void record(const char* name,std::initializer_list<std::intptr_t> a={},
                   std::initializer_list<float> f={}) { calls.push_back({name,a,f}); }
template<class... T> inline void record_args(const char* name,T... v) {
    record(name,{word(v)...});
}
inline unsigned count(const char* name) {
    return unsigned(std::count_if(calls.begin(),calls.end(),[&](const Call& c){return c.name==name;}));
}
inline const Call& call(const char* name,unsigned ordinal=0) {
    for(const auto& c:calls) if(c.name==name && ordinal--==0) return c;
    assert(false && "missing expected service call"); return calls.front();
}
inline void clear_calls() { calls.clear(); }
void reset();
}

struct Atari {
    u16 m_flag=0xffff;
    template<class... T> void init(T... v) { fixture::record_args("atari.init",v...); }
};
using cAtariInfo=Atari;
struct Light {
    void init2(int a,int b,const Vec* p,const Vec* q,int c) {
        fixture::record("light.init2",{a,b,c},{p->x,p->y,p->z,q->x,q->y,q->z});
    }
};
class cModel {
public:
    cModel* pParts=this;
    cModel* pParent=nullptr;
    Vec world{},pos{},ang{};
    Mtx mat{{1,0,0,0},{0,1,0,0},{0,0,1,0}};
    MotionWork Motion{};
    float frame=0;
    virtual ~cModel()=default;
    virtual void init(cModel*) {}
    int modelInit(void* bin,void* tpl) {
        fixture::record_args("model.init",bin,tpl); return fixture::model_ok;
    }
    void motionSet(void* mot,int a,int b,int c,int d) {
        fixture::record_args("motion.set",mot,a,b,c,d);
    }
    int motionMove() { fixture::record("motion.move"); return fixture::motion_done; }
    cModel* getPartsPtr(unsigned no);
};
class cObj:public cModel {
public:
    unsigned type=0;
    struct { Atari atari; } sub2B4;
    Light LightInfo;
};
struct WeaponWork {
    cModel* parent=nullptr;
    u16 x24=0;
    void* pMotNormal=nullptr;
    void* pMotEmpty=nullptr;
    u8 mode=0,step=0,x18=0,x19=0,x1A=0;
    int seHandle=0;
    float lockRandPitch=0,lockRandYaw=0,lockRandPitchStep=0,lockRandYawStep=0;
};
class cObjWep:public cObj {
public:
    WeaponWork wep;
    virtual void setMotion(cPlayer*) {}
    virtual void moveFire() {}
    virtual void moveReload() {}
    void resetMotion() { fixture::record("motion.reset"); }
    void setAbility(float a,float b,float c,float d) {
        fixture::record("weapon.ability",{},{a,b,c,d});
        wep.lockRandPitch=a*0.017453292f; wep.lockRandYaw=b*0.017453292f;
        wep.lockRandPitchStep=c*0.017453292f; wep.lockRandYawStep=d*0.017453292f;
    }
    void trigger() { fixture::record("weapon.trigger"); if(fixture::bullets>0)--fixture::bullets; }
    int bulletNum() { return fixture::bullets; }
    int reloadable() { return fixture::reloadable; }
    void drawLaserSight(int a,int b) { fixture::record("weapon.laser",{a,b}); }
};
struct PlayerWeapon {
    cObjWep* m_pWep=nullptr;
    unsigned m_Flag=0,knifeStance=0;
    float m_CenterY=0,m_CamAdjY=0,pitch=0;
    void lockMove() { fixture::record("lock.move"); }
    void lockInit() { fixture::record("lock.init"); }
};
struct PlayerBody {
    void initWepHand(u32 p) { fixture::record_args("body.hand",p); }
    void waistMove() { fixture::record("body.waist"); }
};
struct PlayerNeck {
    void init(int a,int b,int c) { fixture::record("neck.init",{a,b,c}); }
};
struct PlayerWaist {
    void set(float a,float b) { fixture::record("waist.set",{},{a,b}); }
};
class cPlayer:public cModel {
public:
    PlayerWeapon weapon{}; PlayerWeapon* Wep=&weapon;
    PlayerBody body{}; PlayerBody* Body=&body;
    PlayerNeck neck{}; PlayerNeck* Neck=&neck;
    PlayerWaist waist{}; PlayerWaist* Waist=&waist;
    std::array<void*,128> pMotTbl{};
    u8 r_no_0=0,r_no_1=0,r_no_2=0,r_no_3=0,x4FC=0,x4FD=0;
    unsigned flags_420=0,m_Work0=0,m_Work1=0,m_Work2=0,m_Work4=0,m_Work5=0,m_Work6=0;
    float m_Fwork0=0;
    void setRightHand(int n) { fixture::record("hand.right",{n}); }
    void setLeftHand(int n) { fixture::record("hand.left",{n}); }
    int keyReload() { return fixture::reload_key; }
    void setLaserSight(int a,int b) { fixture::record("player.laser",{a,b}); }
    void partsWorldCalc() { fixture::record("player.parts_world"); }
};
inline std::array<cModel,64> fixture_bones;
inline cModel* cModel::getPartsPtr(unsigned no) {
    assert(no<fixture_bones.size()); fixture::record("parts",{no}); return &fixture_bones[no];
}
struct GlobalWork {
    unsigned weapon_type=0,weapon_lv_reload=0,weapon_no=0x12;
    std::array<u32,4> Status_flg{};
    PlArc* pWep=nullptr; PlArc* pPlayer=nullptr; PlArc* pArc=nullptr;
};
inline GlobalWork fixture_global;
inline GlobalWork* pG=&fixture_global;
inline cPlayer* pPL=nullptr;
inline PlArc fixture_weapon_archive,fixture_player_archive,fixture_common_archive;
#define PL_ARC_PTR(arc,no) (static_cast<PlArc*>(arc)->entries.at(no))
#define WEP_ARC_PTR(no) PL_ARC_PTR((PlArc*) pG->pWep, no)
inline void* PlWepMot[3]{};
inline void (*WeaponInitFunc)(cModel*)=nullptr;
inline void (*WeaponMoveFunc)(cPlayer*)=nullptr;
inline void (*ObjInitFunc[0x40])(cObj*){};
struct ObjectManager {
    cObj* createBack(unsigned id) {
        fixture::record("object.create",{id});fixture::create_id=id;
        return fixture::create_ok?fixture::created:nullptr;
    }
};
inline ObjectManager ObjMgr;
struct ItemManager {
    int bulletNum() { fixture::record("item.bullets"); return fixture::bullets; }
    void reload() { fixture::record("item.reload");fixture::bullets=fixture::reload_capacity; }
};
inline ItemManager ItemMgr;
struct Logger { void err(int,int,const char* message,...) { fixture::record(message); } };
inline Logger fixture_logger; inline Logger* pLog=&fixture_logger;
inline void OSReport(const char* message,...) { fixture::record(message); }
inline void EspDataLoad(u32 p,int group,int flag) { fixture::record_args("effect.load",p,group,flag); }
template<class... T> inline void EstSet(T... v) { fixture::record_args("effect.set",v...); }
inline int SndCall(int bank,u16 no,const Vec* p,int a,int b,int c) {
    fixture::record("sound",{bank,no,a,b,c},{p->x,p->y,p->z});return fixture::snd_result;
}
inline void VibSetData(VibDataTbl* p,int no,int mode) { fixture::record_args("vibration",p,no,mode); }
inline void MotionSetCore(cModel* obj,MotionWork* motion,void* p,int a,int b,int c,int d) {
    fixture::record_args("motion.core",obj,motion,p,a,b,c,d);
}
inline unsigned MotionGetState(MotionWork* motion) { return motion->state; }
inline unsigned MotionGetState(cModel*) { fixture::record("motion.state");return fixture::motion_done; }
inline bool MotionCheckCrossFrame(MotionWork* motion,float frame) {
    fixture::record("motion.cross",{fixture::word(motion)},{frame});return fixture::cross_frame;
}
extern "C" __attribute__((used,noinline)) inline int MotionMove(cModel*,int flag) {
    fixture::record("motion.move_i",{flag}); return fixture::motion_done;
}
inline void PSMTXMultVec(const Mtx m,const Vec* p,Vec* out) {
    const Vec v=*p;
    *out={m[0][0]*v.x+m[0][1]*v.y+m[0][2]*v.z+m[0][3],
          m[1][0]*v.x+m[1][1]*v.y+m[1][2]*v.z+m[1][3],
          m[2][0]*v.x+m[2][1]*v.y+m[2][2]*v.z+m[2][3]};
}
inline void PSMTXMultVecSR(const Mtx m,const Vec* p,Vec* out) {
    const Vec v=*p;
    *out={m[0][0]*v.x+m[0][1]*v.y+m[0][2]*v.z,
          m[1][0]*v.x+m[1][1]*v.y+m[1][2]*v.z,
          m[2][0]*v.x+m[2][1]*v.y+m[2][2]*v.z};
}
inline void PSVECAdd(const Vec* a,const Vec* b,Vec* out) { *out={a->x+b->x,a->y+b->y,a->z+b->z}; }
inline float fRand1_1() { return fixture::random_values[fixture::random_index++%fixture::random_values.size()]; }
inline cObj fixture_cartridge;
inline cObj* SetObj10(void* bin,void* tpl,Vec* pos,Vec* rot,Vec* spd,float grav,float rad,int life,int flags) {
    fixture::record("cartridge",{fixture::word(bin),fixture::word(tpl),life,flags},
                    {pos->x,pos->y,pos->z,rot->x,rot->y,rot->z,spd->x,spd->y,spd->z,grav,rad});
    return fixture::cartridge_ok?&fixture_cartridge:nullptr;
}
template<class... T> inline void Obj10SetEst(cObj* obj,T... v) { fixture::record_args("cartridge.effect",obj,v...); }
inline void AtariFlagsAnd(cAtariInfo* a,u16 mask) { a->m_flag&=mask; }
inline void U16Set(u16& d,int v) { d=u16(v); }
template<class T> inline void PSet(T& d,T v) { d=v; }
inline void PSet(void*& d,int v) { assert(v==0);d=nullptr; }
#define BitOn(f,b) ((f)|=(b))

struct Camera {
    float getCameraDirection() { return fixture::camera_direction; }
    float getCameraPitch() { return fixture::camera_pitch; }
};
inline Camera CamCtrl;
inline void CamCtrlShoulderSetAim(const Vec* p) { fixture::record("camera.aim",{},{p->x,p->y,p->z}); }
struct Collision {
    template<class... T> void hitCheck(Vec* p,Vec* aim,Vec* hit,T...) {
        *hit=*aim;fixture::record("collision.aim",{},{p->x,p->y,p->z,aim->x,aim->y,aim->z});
    }
};
inline Collision SatMgr;
struct MotionBlend {
    template<class... T> void set(cPlayer*,void* a,void* b,void* c,T... v) {
        fixture::record_args("motion.blend_set",a,b,c,v...);
    }
    void move(float f) { fixture::record("motion.blend_move",{},{f}); }
};
inline MotionBlend mot3;
inline float m3r[3]{},PlReloadEndTbl[64][3]{};
struct JoyInput { unsigned trg=0; }; inline JoyInput Joy[1];
struct KeyInput { unsigned on=0; }; inline KeyInput Key;
inline int joyKamae() { return fixture::aim_held; }
inline int joyFireOn() { return fixture::fire_held; }
inline int joyFireTrg() { return fixture::fire_trg; }
inline int dmMotCk() { return fixture::damage_motion; }
inline void PlWepLockCtrl(cPlayer*) { fixture::record("lock.control"); }
inline void PlWepLockRandInit() { fixture::record("lock.random_init"); }
inline void PlWepLockRand(cPlayer*,int kind,float* pitch,float* yaw) {
    fixture::record("lock.random",{kind});*pitch+=0.125f;*yaw-=0.25f;
}
inline void PlWepHitCheck2(cPlayer*,Vec* a,Vec* b,unsigned no,int flag,float range) {
    fixture::record("bullet.hit",{no,flag},{a->x,a->y,a->z,b->x,b->y,b->z,range});
}

inline void fixture::reset() {
    calls.clear();model_ok=create_ok=cartridge_ok=true;cross_frame=motion_done=false;
    aim_held=true;fire_held=fire_trg=false;reloadable=true;reload_key=false;damage_motion=true;
    bullets=3;reload_capacity=50;snd_result=0x1234;created=nullptr;create_id=0;
    camera_direction=.25f;camera_pitch=.125f;random_values={};random_index=0;
    for(unsigned i=0;i<128;++i) {
        fixture_weapon_archive.entries[i]=reinterpret_cast<void*>(0x100000U+i*0x100U);
        fixture_player_archive.entries[i]=reinterpret_cast<void*>(0x200000U+i*0x100U);
        fixture_common_archive.entries[i]=reinterpret_cast<void*>(0x300000U+i*0x100U);
    }
    fixture_common_archive.ofs_1C=64;
    fixture_global={};fixture_global.pWep=&fixture_weapon_archive;
    fixture_global.pPlayer=&fixture_player_archive;fixture_global.pArc=&fixture_common_archive;
    for(auto& bone:fixture_bones) {
        bone.world={};bone.pos={};bone.ang={};bone.pParent=nullptr;
        for(unsigned i=0;i<3;++i)for(unsigned j=0;j<4;++j)bone.mat[i][j]=i==j?1.0f:0.0f;
    }
    fixture_cartridge.type=0;
    std::fill(std::begin(PlWepMot),std::end(PlWepMot),nullptr);
    WeaponInitFunc=nullptr;WeaponMoveFunc=nullptr;
    std::fill(std::begin(ObjInitFunc),std::end(ObjInitFunc),nullptr);
    std::fill(std::begin(m3r),std::end(m3r),0.0f);
    for(unsigned i=0;i<64;++i)for(unsigned j=0;j<3;++j)PlReloadEndTbl[i][j]=float(100+i*3+j);
    Joy[0]={};Key={};pPL=nullptr;
}
