"""Actual swap-close control flow: failed restore must halt before borrowed reads."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

REL='port/dreamcast/game/sscrn_bridge.cpp'
BASE='54ba44079c33117b8241a9277c3aecdce8b4f9ce'
PREFIX=r'''
#include <cassert>
#include <cstdint>
#include <cstring>
#include <vector>
using u32=std::uintptr_t;
struct SubScreenWork {void* pBuf;};
struct Span {std::uintptr_t start;unsigned bytes;}spans[1]{{0x123400,32}};
unsigned nspan=1,live_bytes=32;
constexpr unsigned kSsAramSize=0x300000;
u32 open_hash=0x12345678,computed_hash;
bool swapped=true;
std::vector<unsigned>steps;
void w11_text_check(const char*){steps.push_back(1);}
unsigned long long re4dc_ssb_us(){return 0;}
void re4dc_ssb_rewind(){steps.push_back(2);}
void re4dc_ssb_get(void*,unsigned){steps.push_back(3);}
u32 hash_words(const void*,unsigned,u32){steps.push_back(4);return computed_hash;}
void re4dc_ssb_close(){steps.push_back(5);}
void re4dc_parts_thaw(){steps.push_back(6);}
void restore_message_state(u32,u32){steps.push_back(7);}
unsigned re4dc_motion_forget_dead_heaps(){steps.push_back(8);return 0;}
void re4dc_ui_invalidate_sources(){steps.push_back(9);}
unsigned re4dc_ssb_pool_free(){return 0;}
void re4dc_log(const char*,...){steps.push_back(10);}
[[noreturn]] void re4dc_missing(const char*){steps.push_back(11);throw 1;}
'''
SUFFIX=r'''
int main(){
    SubScreenWork wk{reinterpret_cast<void*>(0x123400)};
    computed_hash=open_hash;
    re4dc_subscreen_swap_close(&wk);
    assert(!swapped && (steps==std::vector<unsigned>{1,2,3,4,5,6,7,8,9,10}));
    swapped=true;steps.clear();computed_hash=open_hash^1;
    try{re4dc_subscreen_swap_close(&wk);assert(false);}catch(int){}
#if RE4DC_SS_RESTORE_VALIDATE_FIRST
    assert(swapped && (steps==std::vector<unsigned>{1,2,3,4,11}));
#else
    assert(!swapped && (steps==std::vector<unsigned>{1,2,3,4,5,6,7,8,9,10,11}));
#endif
}
'''


def extract(source):
    at=source.index('extern "C" void re4dc_subscreen_swap_close(SubScreenWork* wk)')
    start=source.index('{',at)
    depth=1
    end=start+1
    while depth:
        if source[end]=='{':depth+=1
        elif source[end]=='}':depth-=1
        end+=1
    return source[at:end]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--tree',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    a.out.mkdir(exist_ok=False)
    old=subprocess.check_output(['git','-C',str(a.tree),'show',BASE+':'+REL],text=True)
    current=(a.tree/REL).read_text()
    variants={}
    for name,source,flags in [('baseline',old,[]),('default',current,[]),('off',current,['-DRE4DC_SS_RESTORE_VALIDATE_FIRST=0']),('on',current,['-DRE4DC_SS_RESTORE_VALIDATE_FIRST=1'])]:
        cpp=a.out/(name+'.cpp')
        cpp.write_text(PREFIX+extract(source)+SUFFIX)
        exe=a.out/name
        cmd=['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-fsanitize=undefined,address',*flags,str(cpp),'-o',str(exe)]
        subprocess.run(cmd,check=True)
        subprocess.run([str(exe)],check=True)
        pre=subprocess.check_output(['g++','-std=c++17','-E','-P',*flags,str(cpp)])
        (a.out/(name+'.pre')).write_bytes(pre)
        variants[name]=dict(pre_sha256=hashlib.sha256(pre).hexdigest(),command=cmd)
    assert variants['baseline']['pre_sha256']==variants['default']['pre_sha256']==variants['off']['pre_sha256']
    result=dict(status='ACTUAL_SOURCE_HOST_CONTROL_FLOW_ONLY',baseline=BASE,source_sha256=hashlib.sha256(current.encode()).hexdigest(),
                variants=variants,matching_restore_sequence_unchanged=True,enabled_mismatch_halts_before_backing_close_thaw_or_recount=True,
                disabled_preprocessed_function_exact=True,observed_game_corruption=False,target_acceptance=False)
    (a.out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='variants'}))


if __name__=='__main__':main()
