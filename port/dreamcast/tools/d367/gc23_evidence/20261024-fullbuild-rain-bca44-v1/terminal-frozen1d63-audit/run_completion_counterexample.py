#!/usr/bin/env python3
from pathlib import Path
import sys,subprocess,json,hashlib,resource
resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,256*1024*1024))
ROOT=Path('/dev/shm/gc-static-review1d63/source');GAME=ROOT/'port/dreamcast/game';OUT=Path(__file__).resolve().parent;RAM=Path('/dev/shm/gc-terminal-next1d63/completions');RAM.mkdir(exist_ok=True)
sys.path.insert(0,str(ROOT/'port/dreamcast/tools/d367/gc_port23'));from test_runtime_hooks import function
s=(GAME/'platform/audio_strm.cpp').read_text();fixture=r'''
#include <cassert>
#include <cstring>
#include <cstdint>
using u8=unsigned char;using s32=int;using u32=std::uintptr_t;
struct Pend{void(*dvd)(s32,void*);void(*arq)(u32);void*obj;s32 res;};Pend g_pend[8];u32 g_pendN;unsigned irq_on=1;
int irq_disable(){int old=irq_on;irq_on=0;return old;}void irq_restore(int old){irq_on=old;}
''' + function(s,'void pend_push(')+'\n'+function(s,'void re4dc_audio_pend_run(')+r'''
unsigned completed;bool requeue=true,empty_while_executing,inline_overflow;
void child(u32){assert(irq_on);++completed;empty_while_executing|=g_pendN==0;}
void parent(u32){assert(irq_on&&g_pendN==0);empty_while_executing=true;++completed;if(requeue){requeue=false;pend_push(Pend{nullptr,child,nullptr,0});}}
void overflow(u32){assert(irq_on&&g_pendN==8);inline_overflow=true;}
int main(){pend_push(Pend{nullptr,parent,nullptr,0});assert(g_pendN==1);re4dc_audio_pend_run();assert(completed==1&&empty_while_executing&&g_pendN==1);re4dc_audio_pend_run();assert(completed==2&&!g_pendN);
for(unsigned i=0;i<8;++i)pend_push(Pend{nullptr,child,nullptr,0});pend_push(Pend{nullptr,overflow,nullptr,0});assert(inline_overflow&&g_pendN==8);re4dc_audio_pend_run();assert(completed==10&&!g_pendN);}
'''
cpp=RAM/'fixture.cpp';exe=RAM/'fixture';cpp.write_text(fixture);(OUT/'actual-audio-completion-local-batch-counterexample.cpp').write_text(fixture)
q=subprocess.run(['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation',str(cpp),'-o',str(exe)],capture_output=True,text=True);assert q.returncode==0,q.stderr;q=subprocess.run(['/lib64/ld-linux-x86-64.so.2',str(exe)],capture_output=True,text=True);assert q.returncode==0,q.stderr
(OUT/'independent-completion-counterexample.json').write_text(json.dumps({'source':'1d63cffe3a232c402418f2f2d919e7abae476957','actual_functions':['audio_strm.cpp::pend_push','audio_strm.cpp::re4dc_audio_pend_run'],'scope':'source-extracted deterministic callback schedules; host uintptr_t stands in for SH4 u32 pointer carrier, IRQ provider mocked','global_empty_while_local_callback_executing':True,'callback_reenqueue_requires_another_actual_drain':True,'overflow_runs_callback_inline_on_producer':True,'no_terminal_quiescence_proved':True,'fixture_sha256':hashlib.sha256(fixture.encode()).hexdigest(),'rlimit_as_bytes':256*1024*1024,'jobs':1,'max_child_rss_kib':resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss},indent=2)+'\n');print('PASS actual audio pending completion schedules: empty global while local callbacks execute; callback reenqueues; overflow callback inline')