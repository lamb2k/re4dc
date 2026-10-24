#!/usr/bin/env python3
"""Run actual OS terminal boundary code with deterministic kernel-state stubs."""
from pathlib import Path
import subprocess,tempfile,unittest
ROOT=Path(__file__).resolve().parents[5]
FILE='port/dreamcast/game/platform/os.cpp'
def function(text,signature):
    start=text.index(signature);i=text.index('{',start)+1;depth=1
    while depth:
        depth+=(text[i]=='{')-(text[i]=='}');i+=1
    return text[start:i]
class TerminalOs(unittest.TestCase):
    def test_actual_boundary_and_admission(self):
        text=(ROOT/FILE).read_text()
        quiesce=function(text,'extern "C" unsigned re4dc_gcasset_os_frame_boundary(')+'\n'+function(text,'extern "C" unsigned re4dc_gcasset_os_quiesce(')
        resume=function(text,'s32 OSResumeThread(')
        check=function(text,'static void checkGate(')
        creation=function(text,'struct GcAssetOsCreation')+';'
        create=function(text,'int OSCreateThread(')
        end=create.index('                re4dc_log("OSCreateThread: reap list full;')
        start=create.rfind('#if RE4DC_GC_ASSET_GATE',0,end)
        overflow=create[start:end]

        code=r"""
#include <cassert>
#include <cstring>
using s32=int;
enum {STATE_WAIT=1,STATE_READY=2,STATE_FINISHED=3,OS_THREAD_STATE_RUNNING=4};
struct kthread_t {int state;void* wait_obj;const char* wait_msg;};
struct OSThread {kthread_t* kt;unsigned nativeIoDepth;int suspend,state;void* queue;int gateCount=0;};
static OSThread g_mainThread,*g_threads[32];static int g_threadCount,g_gate;
static unsigned gcasset_os_terminal,gcasset_os_creating,gcasset_os_late;
static kthread_t* g_reapPending[32];static unsigned g_reapPendingCount;
static kthread_t *thd_current,*motion_busy;
static int irq_depth,interrupt_context,unparks,parks,waits;
int irq_disable(){return irq_depth++;}
void irq_restore(int prior){irq_depth=prior;}
int irq_inside_int(){return interrupt_context;}
int re4dc_motion_thread_busy(const void* p){return p==motion_busy;}
int unpark(OSThread*){++unparks;return 1;}
void thd_pass(){}
void parkSelf(OSThread*){++parks;}
void genwait_wait(void*,const char*,int){++waits;throw 7;}
"""+creation+'\n'+quiesce+'\n'+resume+'\n'+check+'\nvoid actual_tracking_overflow(){\n'+overflow+'\n}\n'+r"""
int main(){
 kthread_t main{STATE_READY,nullptr,nullptr},task{STATE_WAIT,&g_gate,"os-suspend"};
 OSThread t{&task,0,1,0,nullptr};g_mainThread.kt=&main;thd_current=&main;g_threads[0]=&t;g_threadCount=1;
 unsigned blocked=99;
 actual_tracking_overflow();
 assert(!re4dc_gcasset_os_quiesce(&blocked) && !gcasset_os_terminal);
 gcasset_os_late=0;
 // Reused source slot: its replacement is idle, but the prior KOS task is not.
 kthread_t prior{STATE_READY,nullptr,nullptr};g_reapPending[0]=&prior;g_reapPendingCount=1;
 assert(!re4dc_gcasset_os_quiesce(&blocked) && !gcasset_os_terminal);
 prior.state=STATE_FINISHED;assert(re4dc_gcasset_os_quiesce(&blocked));
 g_reapPendingCount=0;gcasset_os_terminal=0;
 assert(re4dc_gcasset_os_quiesce(&blocked)==1 && blocked==0 && gcasset_os_terminal==1 && irq_depth==0);
 assert(OSResumeThread(&t)==1 && t.suspend==1 && unparks==0 && gcasset_os_late==1);
 assert(!re4dc_gcasset_os_quiesce(&blocked));
 gcasset_os_late=0;
 {GcAssetOsCreation create;assert(!create.live && gcasset_os_creating==0 && gcasset_os_late==1);}
 gcasset_os_terminal=0;gcasset_os_late=0;
 {GcAssetOsCreation create;assert(create.live && gcasset_os_creating==1);assert(!re4dc_gcasset_os_quiesce(&blocked));}
 assert(gcasset_os_creating==0);
 g_mainThread.nativeIoDepth=1;assert(!re4dc_gcasset_os_frame_boundary() && !re4dc_gcasset_os_quiesce(&blocked));g_mainThread.nativeIoDepth=0;
 motion_busy=&main;assert(!re4dc_gcasset_os_quiesce(&blocked));motion_busy=nullptr;
 // Every actual in-flight/unknown wait refuses, without setting terminal.
 t.nativeIoDepth=1;assert(!re4dc_gcasset_os_quiesce(&blocked));t.nativeIoDepth=0;
 motion_busy=&task;assert(!re4dc_gcasset_os_quiesce(&blocked));motion_busy=nullptr;
 task.state=STATE_READY;assert(!re4dc_gcasset_os_quiesce(&blocked));task.state=STATE_WAIT;
 t.suspend=0;assert(!re4dc_gcasset_os_quiesce(&blocked));
 int queue=0,other=0;task.wait_msg="os-queue";task.wait_obj=&queue;t.queue=&other;
 assert(!re4dc_gcasset_os_quiesce(&blocked));t.queue=&queue;
 assert(re4dc_gcasset_os_quiesce(&blocked));
 // An accepted queue waiter cannot return into source after a later wake.
 bool held=false;try{checkGate(&t);}catch(int value){held=value==7;}
 assert(held && waits==1);irq_depth=0;
 gcasset_os_terminal=0;task.wait_msg="g2";assert(!re4dc_gcasset_os_quiesce(&blocked));
 task.wait_msg="os-sema";assert(re4dc_gcasset_os_quiesce(&blocked));
 gcasset_os_terminal=0;task.state=STATE_FINISHED;assert(re4dc_gcasset_os_quiesce(&blocked));
 gcasset_os_terminal=0;thd_current=&task;assert(!re4dc_gcasset_os_quiesce(&blocked) && blocked==~0U);
 thd_current=&main;interrupt_context=1;assert(!re4dc_gcasset_os_quiesce(&blocked));interrupt_context=0;
 assert(irq_depth==0);
}
"""
        with tempfile.TemporaryDirectory(prefix='gc-terminal-os24-') as tmp:
            d=Path(tmp);p=d/'actual.cpp';p.write_text(code)
            subprocess.run(['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-DRE4DC_GC_ASSET_GATE=1',str(p),'-o',str(d/'actual')],check=True,timeout=30)
            subprocess.run([str(d/'actual')],check=True,timeout=10)
    def test_off_projection(self):
        old=subprocess.check_output(['git','show','140a699f:'+FILE],cwd=ROOT,text=True);new=(ROOT/FILE).read_text()
        def project(s):
            s='\n'.join(function(s,v) for v in ['static void checkGate(','s32 OSResumeThread(','int OSCreateThread('])
            return subprocess.run(['g++','-E','-P','-x','c++','-DRE4DC_GC_ASSET_GATE=0','-'],input=s,text=True,capture_output=True,check=True,timeout=10).stdout.split()
        self.assertEqual(project(old),project(new))
if __name__=='__main__':unittest.main()
