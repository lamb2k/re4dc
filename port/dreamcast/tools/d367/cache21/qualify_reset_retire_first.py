"""Actual native reset functions with host ownership and cancellation seams."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

BASE='575953b0bc039dbc716d3411e275be1d04313e2e'
REL='src/game/main.cpp'
PREFIX=r'''
#include <cassert>
#include <cstring>
#include <stdexcept>
#include <vector>
using u32=unsigned;
struct Keep { unsigned sys_flags,language,region,game_language,sys_unlock_flg,g_flags_54,card_checked,valid;unsigned char sys_merc_stage[16],sys_merc_rank[8]; } keep;
struct Sys { unsigned flags=1,language=2,region=3,unlock_flg=4,merc_stage[4]{5,6,7,8},merc_rank[2]{9,10}; } sys;
struct Global { unsigned language=11,System_flg=0x4000000,CardStatus=0x80000000,IsMessageInit=12; } global;
auto* pRK=&keep;auto* pSys=&sys;auto* pG=&global;
#define U32Set(a,b) ((a)=(b))
#define U8Set(a,b) ((a)=(b))
void set32(void* p,unsigned off,unsigned value){std::memcpy(static_cast<char*>(p)+off,&value,4);}
#define U32SetOfs(a,off,b) set32(a,off,b)
int SubScreenWk;
bool live,active_ui,modules,motion,effect,ui_cache,cancelled,tasks;
int refusal=0,dead_reads=0;
std::vector<int> trace;
void event(int n){trace.push_back(n);}
void require_live(){if(!live){++dead_reads;throw std::runtime_error("dead heap");}}
void OSReport(const char*,...){}
void systemVISetBlack(int){event(1);}void VIFlush(){event(2);}void VIWaitForRetrace(){event(3);}void GXDrawDone(){event(4);}
struct DVD {void ReadCancelAll(){cancelled=true;event(5);}} Dvd;
struct ARAM {void DmaCancelAll(){event(6);}} Aram;
void SndSoftReset(){event(7);}void DbmenuModuleInit(){event(8);}
void ResetDebugAlloc(){event(18);}
void MemClearAllHeap(){event(19);live=false;}
void SndSystemReset(){event(20);}void RomFontSetting(){event(21);}
void SubScreenExitCore(int*){event(9);if(active_ui){require_live();active_ui=false;}}
void TaskAllClear(){assert(!active_ui);tasks=true;event(10);}
void EmReadInit(){event(11);if(modules){require_live();if(refusal==1)throw std::runtime_error("module pinned");modules=false;}}
void ReleasePlData(){event(12);if(modules)require_live();}
void ReleaseWepData(){event(13);if(modules)require_live();}
struct ROOM {void stopRelData(){event(14);}} RoomData;
extern "C" void re4dc_motion_retire_all(){event(15);require_live();assert(tasks&&cancelled&&!active_ui);if(refusal==2)throw std::runtime_error("motion pinned");motion=false;}
extern "C" void re4dc_effect_retire_room(){event(16);require_live();if(refusal==3)throw std::runtime_error("effect refuse");effect=false;}
extern "C" void re4dc_ui_retire_room(){event(17);require_live();if(refusal==4)throw std::runtime_error("UI fence refuse");ui_cache=false;}
'''
DRIVER=r'''
unsigned checks=0;
void setup(bool loaded,bool screen,int fail){
    live=true;active_ui=screen;modules=motion=effect=ui_cache=loaded;
    cancelled=tasks=false;refusal=fail;dead_reads=0;trace.clear();keep={};global.IsMessageInit=12;
}
unsigned index(int n){for(unsigned i=0;i<trace.size();++i)if(trace[i]==n)return i;return 999;}
int main(){
#if defined(RE4DC_GAME) && !defined(__PPC__) && RE4DC_RESET_RETIRE_BEFORE_HEAPS
    for(bool loaded:{false,true})for(bool screen:{false,true}){
        setup(loaded,screen,0);systemSoftReset();
        assert(!live&&!modules&&!motion&&!effect&&!ui_cache&&!active_ui&&cancelled&&tasks&&dead_reads==0);
        for(int e=9;e<=17;++e)assert(index(e)<index(18)&&index(e)<index(19));
        assert(index(8)<index(9)&&index(18)<index(19)&&index(19)<index(20));
        assert(keep.sys_flags==1&&keep.language==2&&keep.region==3&&keep.game_language==11&&keep.sys_unlock_flg==4&&keep.card_checked==1&&keep.valid==1&&global.IsMessageInit==0);
        ++checks;
    }
    for(int fail:{1,2,3,4})for(bool screen:{false,true}){
        setup(true,screen,fail);bool refused=false;
        try{systemSoftReset();}catch(const std::runtime_error&){refused=true;}
        assert(refused&&live&&dead_reads==0&&index(18)==999&&index(19)==999&&index(20)==999&&global.IsMessageInit==12);
        if(fail==1)assert(modules&&motion&&effect&&ui_cache);
        if(fail==2)assert(motion&&effect&&ui_cache);
        if(fail==3)assert(effect&&ui_cache);
        if(fail==4)assert(ui_cache);
        ++checks;
    }
#else
    for(bool loaded:{false,true})for(bool screen:{false,true}){
        setup(loaded,screen,0);bool failed=false;
        try{systemSoftReset();}catch(const std::runtime_error&){failed=true;}
        assert(failed==(loaded||screen));
        assert(index(18)<index(19)&&index(19)<index(20)&&index(20)<index(9));
        if(failed)assert(dead_reads==1);else assert(global.IsMessageInit==0);
        assert(index(15)==999&&index(16)==999&&index(17)==999);
        ++checks;
    }
#endif
    std::printf("%u\n",checks);
}
'''


def function(s,signature):
    at=s.index(signature);start=s.index('{',at);end=start+1;depth=1
    while depth:
        if s[end]=='{':depth+=1
        elif s[end]=='}':depth-=1
        end+=1
    return s[at:end]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--tree',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();a.out.mkdir(exist_ok=False)
    current=(a.tree/REL).read_text();old=subprocess.check_output(['git','-C',str(a.tree),'show',BASE+':'+REL],text=True)
    records={}
    for name,src,flags in [('baseline',old,['-DRE4DC_GAME=1']),('default',current,['-DRE4DC_GAME=1']),('off',current,['-DRE4DC_GAME=1','-DRE4DC_RESET_RETIRE_BEFORE_HEAPS=0']),('on',current,['-DRE4DC_GAME=1','-DRE4DC_RESET_RETIRE_BEFORE_HEAPS=1']),('ppc-on',current,['-DRE4DC_GAME=1','-D__PPC__=1','-DRE4DC_RESET_RETIRE_BEFORE_HEAPS=1']),('non-native-on',current,['-DRE4DC_RESET_RETIRE_BEFORE_HEAPS=1'])]:
        cpp=a.out/(name+'.cpp');cpp.write_text(PREFIX+function(src,'void systemResetCommon()')+'\n'+function(src,'void systemSoftReset()')+'\n'+DRIVER)
        exe=a.out/name
        cmd=['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-fsanitize=undefined,address',*flags,str(cpp),'-o',str(exe)]
        subprocess.run(cmd,check=True)
        checks=int(subprocess.check_output([str(exe)],text=True))
        pre=subprocess.check_output(['g++','-std=c++17','-E','-P',*flags,str(cpp)])
        records[name]=dict(checks=checks,pre_sha256=hashlib.sha256(pre).hexdigest(),command=cmd)
    assert records['baseline']['pre_sha256']==records['default']['pre_sha256']==records['off']['pre_sha256']==records['ppc-on']['pre_sha256']==records['non-native-on']['pre_sha256']
    result=dict(status='ACTUAL_RESET_FUNCTIONS_HOST_OWNERSHIP_SEAMS_ONLY',source_sha256=hashlib.sha256(current.encode()).hexdigest(),baseline=BASE,variants=records,
                native_enabled_cases=records['on']['checks'],legacy_order_characterized=True,default_zero_ppc_non_native_preprocessed_exact=True,
                refusal_keeps_heaps_and_unreleased_owners_live=True,whole_transaction_rollback=False,other_room4_owner_closure=False,target_acceptance=False)
    (a.out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='variants'}))


if __name__=='__main__':main()
