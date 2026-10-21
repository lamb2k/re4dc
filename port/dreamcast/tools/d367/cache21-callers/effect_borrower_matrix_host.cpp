#include <cassert>
#include <cstdint>
#include <iostream>
using u32=std::uint32_t;
struct EspgenWork{u32 flag,id;struct{u32 Core_flg;}info;const void*retained_head;};
struct Global{u32 Status_flg[4];}global,*pG=&global;
static EspgenWork units[1],*EspgenArray=units;static u32 nEspgen=1;
using Destruct=void(*)(EspgenWork*);
static Destruct EspgenDestructTbl[1],EspgenDestructTblApp[1];
#define ESPGEN_APP_ID 0x50
static u32 GetEspgenIdMax(){return 0;} // Actual Push's optional destruct dispatch stays empty.
#include "borrower_actual_methods.inc"
int main(){
    unsigned cases=0;
    for(u32 core:{0U,1U,0x800U,0x801U,0x2000U,0x2001U,0x3000U,0x3001U})
    for(u32 flag:{0U,1U,2U,3U})for(bool event:{false,true}){
        int archive_marker=0x1234;units[0]={flag,0,{core},&archive_marker};global={};
        global.Status_flg[1]=event?0x10000000:0;
        const bool alive=(flag&1)&&!(flag&2);
        assert(bool(EspgenIsActive(&units[0]))==(alive&&(!event||(core&1))));
        EspgenDeleteEvent();const bool removed=alive&&!(core&1)&&!(core&0x800);
        assert(units[0].flag==(removed?flag|2:flag));
        assert(units[0].retained_head==&archive_marker);
        const bool active=EspgenIsActive(&units[0]);
        assert(active==(alive&&!removed&&(!event||(core&1))));
        ++cases;
        if(alive&&event)std::cout<<"BORROWER core="<<std::hex<<core<<std::dec<<" removed="<<removed<<" active_during_event="<<active<<" PASS\n";
    }
    std::cout<<"EFFECT_BORROWER_MATRIX_CASES="<<cases<<" PASS\n";
}
