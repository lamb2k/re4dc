"""Host/source checks only; no target compiler, image, guest or process inventory."""
from pathlib import Path
import hashlib, json, re, subprocess, tempfile, sys

ROOT = Path('/root/probe/codex-damcause23')
BASE = '64a28a7bdc44312924b14414501b7d4ff1d2d032'
OUT = Path(sys.argv[1]) if len(sys.argv) == 2 else Path('/mnt/c/Game Dev/Emulators/codex-lanes/damcause23/host04')
assert not OUT.exists(), 'Preserve prior host evidence; provide a new output directory'
PATHS = ['src/game/em_set.cpp', 'src/game/em.cpp', 'src/game/read.cpp',
         'port/dreamcast/game/platform/crash_screen.cpp',
         'port/dreamcast/game/platform/include/issue52_actor_diag.h']

def sha(data): return hashlib.sha256(data).hexdigest()
def git(*args): return subprocess.check_output(['git','-C',str(ROOT),*args])
def body(text, signature):
    found = re.search(r'(?m)^' + re.escape(signature) + r'[^;\n]*\n?\s*\{', text)
    assert found, signature
    start = found.start()
    left = text.index('{', start)
    depth = 0
    for index in range(left, len(text)):
        if text[index] == '{': depth += 1
        elif text[index] == '}': depth -= 1
        if not depth: return text[start:index+1] + '\n'
    raise AssertionError(signature)

old = {p:git('show', BASE+':'+p).decode() for p in PATHS}
new = {p:(ROOT/p).read_text() for p in PATHS}
pins = [dict(path=p, before_sha256=sha(old[p].encode()), after_sha256=sha(new[p].encode())) for p in PATHS]
defines = ['-DRE4DC_GAME=1','-DRE4DC_EM_READ_RETRY=1','-DRE4DC_ALIVE_CAP=1',
           '-DRE4DC_CRASH_SCREEN=1','-DRE4DC_CRASH_FAULT_DETAIL=1']
preprocessed = []
for label, extra in [('default',[]),('zero',['-DRE4DC_ISSUE52_ACTOR_DIAG=0']),
                     ('ppc_one',['-DRE4DC_ISSUE52_ACTOR_DIAG=1','-D__PPC__=1']),
                     ('non_native_one',['-URE4DC_GAME','-DRE4DC_ISSUE52_ACTOR_DIAG=1'])]:
    # The native crash renderer has no PPC/non-native translation unit. Its
    # existing diagnostic gate is native Makefile-owned, so only off variants apply.
    for p in PATHS[:4] if label in ('default','zero') else PATHS[:3]:
        def preprocess(source):
            source = re.sub(r'^\s*#include[^\n]*', '', source, flags=re.M)
            run = subprocess.run(['g++','-E','-P','-x','c++',*defines,*extra,'-'],
                                 input=source, text=True, capture_output=True, check=True)
            return re.findall(r'"(?:\\.|[^"\\])*"|\w+|[^\s]', run.stdout)
        before, after = preprocess(old[p]), preprocess(new[p])
        assert before == after, (label,p,'preprocessed tokens differ')
        preprocessed.append(dict(variant=label,path=p,tokens=len(after),exact=True))

# Placement checks on the exact edited functions. They do not execute target I/O.
for text, needles in [
    (body(new[PATHS[2]], 'int readEmData('), ['I52_READ_ABSENT','I52_READ_SUBMIT, req, 0',
                                          'I52_READ_NEGATIVE, req, ret','I52_READ_COMPLETE, req, ret']),
    (body(new[PATHS[1]], 'int cEmMgr::construct('), ['I52_CONSTRUCT_BEGIN','I52_CONSTRUCT_NO_ARC','I52_CONSTRUCT_INIT']),
    (body(new[PATHS[2]], 'void* EmReadSearch('), ['m ? I52_READ_CACHED : I52_READ_MISS']),
]:
    assert all(n in text for n in needles), [n for n in needles if n not in text]
construct = body(new[PATHS[1]], 'int cEmMgr::construct(')
assert construct.index('I52_CONSTRUCT_INIT') < construct.index('EmInitFunc(p);', construct.index('    default:'))
assert body(old[PATHS[0]],'static cEm* emMustCreate(') == body(new[PATHS[0]],'static cEm* emMustCreate(')
assert git('diff',BASE,'--','src/st1/r10c.cpp','include/cManager.h',
           'port/dreamcast/game/Makefile','port/dreamcast/game/platform/modules.cpp') == b''

header = new[PATHS[4]]
collector = new[PATHS[3]][new[PATHS[3]].index('struct Issue52ActorSnapshot'):new[PATHS[3]].index('\n#endif\n\nnamespace {')]
prefix = r'''
#include <cassert>
#include <cstdio>
#include <cstring>
#include <climits>
#include <new>
#include <vector>
using u32 = unsigned long;
using u8 = unsigned char;
int irq_depth, irq_calls;
int irq_disable(){ ++irq_calls; return irq_depth++; }
void irq_restore(int old){ irq_depth=old; }
unsigned long module_base=0x8c88cae0;
extern "C" unsigned long re4dc_issue52_stage_base(){return module_base;}
'''
stub = r'''
struct PlArc {};
struct OSModuleHeader {unsigned bssSize;};
struct ReadModule {unsigned id,flag;void* pArc;unsigned long size;OSModuleHeader* pModule;unsigned long bssSize;void* pInitFunc;};
struct DvdReadInfo {void* addr[2][2];unsigned long size[2][2];};
struct ReadFile {int file,dll,unused;};
ReadFile EmFileTbl[64],EmFileTbl_Ada[64],EmFileTbl_Klauser[64],EmFileTbl_Wesker[64];
struct File {char name[16];} FileTbl[8];
struct Global {int stage_no,room_no,room_id,pl_type,Rno0;unsigned Frame_cnt;} global;
Global* pG=&global;
unsigned long source_task=0x1111;
extern "C" unsigned long re4dc_issue52_source_task(){return source_task;}
unsigned char archive_bytes[64];
int fail_mode,create_calls,moves,work_calls,dist_calls,fresh_calls,log_calls,sleeps,request_calls,read_calls;
int cap_refuse,dead_refuse,list_refuse,missing_file,bind_refuse,cache_on,request_fail,negative_left;
std::vector<int> polls;
struct Logger {void err(int,int,const char*,...){++log_calls;}} logger;
Logger* pLog=&logger;
extern "C" void OSReport(const char*,...){}
void re4dc_missing(const char*) {assert(false);}
void TaskSleep(int){++sleeps;}
void SceSleep(int){++sleeps;}
extern "C" void re4dc_em_sleep(int){++sleeps;}
struct Scenario {int x73; int checkCTaskRange(){return 0;}} SceSys;
void Mem_free(void*){}
void* fake_alloc(unsigned long){return archive_bytes;}
#define MEM_ALLOC(n,a,b) fake_alloc(n)
#define BitOff16(flag,bits) ((flag)&=~(bits))
#define SET_DRS_NAME(n) ((void)0)
int re4dc_ui_bind_enemy(void*,unsigned long){return !bind_refuse;}
int re4dc_effect_bind(void*,unsigned long){return 1;}
int re4dc_motion_bind(void*,unsigned long){return 1;}
struct Disc {
 int FileExistCheck(const char*,unsigned long* len){*len=64;return missing_file?-1:0;}
 int ReadCheckInfo(int req,DvdReadInfo* info){
   ++read_calls; int result;
   if(req<0) result=req;
   else if(negative_left){--negative_left;result=-2;}
   else if(!polls.empty()){result=polls.front();polls.erase(polls.begin());}
   else result=1;
   if(result==1){info->size[0][0]=64;info->addr[0][0]=archive_bytes;}
   return result;
 }
} Dvd;
int issue_request(){++request_calls;if(request_fail){--request_fail;return -2;}return 100+request_calls;}
#define DVD_READ_N(...) issue_request()
int checkAshleyId(int id){return id;}
ReadModule loaded;
ReadModule* SearchEmModule(int id){return cache_on&&loaded.id==(unsigned)id?&loaded:nullptr;}
struct cEm {int id;unsigned serial,be_flag,emset_no;PlArc* subArc;PlArc* subArc2;float l_sub;void move(){++moves;}} actor;
struct cEmMgr {unsigned Guid=0;int construct(cEm*,u32);} manager;
void initialize(cEm* p){p->id=0x12;p->be_flag=0;}
void (*EmInitFunc)(cEm*)=initialize;
void (*PlInitFunc)(cEm*)=initialize;
#define EM_INIT_FUNC (*(void**)&EmInitFunc)
int readEmData(ReadModule*,int,void*,u32);
void* readEm(int id,void* addr,u32 size){if(!readEmData(&loaded,id,addr,size))return nullptr;loaded.pInitFunc=(void*)initialize;return loaded.pArc;}
void* EmReadSearch(int,void*,u32);
cEm* EmCreate(int id){++create_calls;if(fail_mode)return nullptr;return manager.construct(&actor,id)?&actor:nullptr;}
struct EmListData {int id,room,be_flag;} entries[256];
#define EM_LIST(no) (&entries[no])
#define EM_SET_ID_NG(id) ((id)>=0x60)
#define EM_SET_WORK(em,d,no) (++work_calls)
int EmSetDieCk(int){return dead_refuse;}
int checkListId(int){return !list_refuse;}
int re4dc_aliveCapDefer(int,int){return cap_refuse;}
void aliveCapNoteFresh(cEm*,int){++fresh_calls;}
void EmSetDist(cEm*){++dist_calls;}
cEm* errEm=nullptr;
int re4dc_emSetMust;
'''
constructor = body(new[PATHS[1]], 'int cEmMgr::construct(')
aliases = '\n'.join('using '+name+'=cEm;' for name in sorted(set(re.findall(r'new \(p\) (\w+)',constructor))-{'cEm'}))
main = r'''
void reset(){
 global={1,12,0x10c,0,0,77}; actor={}; loaded={};loaded.id=0x12;loaded.pArc=archive_bytes;loaded.pInitFunc=(void*)initialize;
 entries[2]={0x12,0x10c,1}; entries[3]=entries[2]; EmFileTbl[0x12]={1,0,0};
 fail_mode=create_calls=moves=work_calls=dist_calls=fresh_calls=log_calls=sleeps=request_calls=read_calls=0;
 cap_refuse=dead_refuse=list_refuse=missing_file=bind_refuse=cache_on=request_fail=negative_left=re4dc_emSetMust=0;
 source_task=0x1111;g_issue52_attempt={};polls.clear();EmInitFunc=initialize;
}
int main(){
 unsigned long fingerprint=2166136261u;int scenarios=0;
 auto mix=[&](unsigned long x){fingerprint=(fingerprint^x)*16777619u;};
 for(int n=0;n<13;++n){
  reset();
  switch(n){
   case 0:cache_on=1;break;case 1:entries[2].id=0x60;break;
   case 2:entries[2].room=0x20c;break;case 3:entries[2].room=0x10d;break;
   case 4:entries[2].be_flag=3;break;case 5:entries[2].id=0;break;
   case 6:dead_refuse=1;break;case 7:list_refuse=1;break;case 8:cap_refuse=1;break;
   case 9:fail_mode=1;break;case 10:missing_file=1;break;
   case 11:request_fail=1;break;case 12:negative_left=9;re4dc_emSetMust=1;break;
  }
  cEm* result=EmSetFromList2(2,1);
  mix(result!=nullptr);mix(entries[2].be_flag);mix(moves);mix(work_calls);mix(dist_calls);mix(fresh_calls);
  mix(create_calls);mix(log_calls);mix(sleeps);mix(request_calls);mix(read_calls);++scenarios;
#if RE4DC_ISSUE52_ACTOR_DIAG
  const Issue52Attempt& s=g_issue52_attempt;assert(s.state==I52_COMPLETED);assert(s.actor==(unsigned long)result);
  const unsigned why[]={I52_CREATED,I52_ID_FILTER,I52_STAGE,I52_ROOM,I52_ALREADY_SET,I52_ZERO_ID,
   I52_DEAD,I52_LIST_FILTER,I52_CAP,I52_CREATE_FAILED,I52_CREATE_FAILED,I52_CREATED,I52_CREATED};
  assert(s.reason==why[n]);
  if(n==0)assert(s.read_path==1&&s.construct==3);
  if(n==9)assert(s.construct==0&&s.read_path==0); // creation failure is not claimed full pool
  if(n==10)assert(s.construct==2&&s.read_reason==1);
  if(n==11)assert(s.negatives==1&&s.first_negative==-2&&s.poll==1&&s.read_reason==3);
  if(n==12)assert(s.constructs==2&&s.negatives==9&&s.first_negative==-2&&s.poll==1);
#endif
 }
 std::printf("{\"scenarios\":%d,\"behavior_fingerprint\":\"%lx\"}\n",scenarios,fingerprint);
 int controls=0;
#if RE4DC_ISSUE52_ACTOR_DIAG
 reset();auto t=re4dc_issue52_begin(0x1111,1,0x10c,2,0x12);assert(t);
 assert(!re4dc_issue52_current(0x2222,0x12));assert(!re4dc_issue52_current(0x1111,0x13));++controls;
 re4dc_issue52_detail(t,0x2222,I52_CONSTRUCT_BEGIN,0,0);assert(!g_issue52_attempt.construct);++controls;
 re4dc_issue52_detail(t,0x1111,I52_CONSTRUCT_BEGIN,0,0);
 re4dc_issue52_detail(t,0x2222,I52_READ_NEGATIVE,99,-5);assert(!g_issue52_attempt.negatives);++controls;
 re4dc_issue52_detail(t,0x1111,I52_READ_NEGATIVE,7,-4);assert(g_issue52_attempt.first_negative==-4);++controls;
 re4dc_issue52_finish(t,0x2222,I52_CREATED,123,2);assert(g_issue52_attempt.state==I52_PENDING);++controls;
 auto t2=re4dc_issue52_begin(0x2222,3,0x10c,2,0x12);assert(t2!=t&&g_issue52_attempt.abandoned==1);++controls;
 re4dc_issue52_finish(t,0x1111,I52_CREATED,123,4);assert(g_issue52_attempt.state==I52_PENDING);++controls;
 re4dc_issue52_detail(t2,0x2222,I52_CONSTRUCT_BEGIN,0,0);
 re4dc_issue52_detail(t2,0x2222,I52_CONSTRUCT_INIT,0,0);
 assert(!re4dc_issue52_current(0x2222,0x12));
 re4dc_issue52_detail(t2,0x2222,I52_READ_NEGATIVE,8,-5);assert(!g_issue52_attempt.negatives);++controls;
 re4dc_issue52_finish(t2,0x2222,I52_CREATED,1,5);assert(g_issue52_attempt.state==I52_COMPLETED);++controls;
 char row[96];assert(issue52_attempt_line(row,sizeof(row)));assert(std::strlen(row)<=52);++controls;
 reset();t=re4dc_issue52_begin(0x1111,1,0x10c,2,0x12);
 re4dc_issue52_detail(t,0x1111,I52_CONSTRUCT_BEGIN,0,0);
 re4dc_issue52_detail(t,0x1111,I52_CONSTRUCT_BEGIN,0,0);
 assert(g_issue52_attempt.state==I52_ABANDONED);re4dc_issue52_finish(t,0x1111,I52_CREATED,1,2);
 assert(g_issue52_attempt.state==I52_ABANDONED);++controls;
 reset();g_issue52_attempt.serial=UINT_MAX;t=re4dc_issue52_begin(0x1111,1,0x10c,2,0x12);assert(t==1);++controls;
 reset();assert(!re4dc_issue52_begin(0,1,0x10c,2,0x12));assert(!re4dc_issue52_begin(1,1,0x101,2,0x12));
 assert(!re4dc_issue52_begin(1,1,0x10c,3,0x12));assert(!g_issue52_attempt.serial);++controls;
 reset();cache_on=1;entries[3]=entries[2];assert(EmSetFromList2(3,1));assert(!g_issue52_attempt.serial);++controls;
 assert(irq_depth==0);++controls;
 std::printf("{\"collector_controls\":%d,\"collector_bytes_host\":%zu}\n",controls,sizeof(Issue52Attempt));
#endif
}
'''
OUT.mkdir(parents=True,exist_ok=True)
results=[]
with tempfile.TemporaryDirectory(prefix='damcause23-host-') as temporary:
    temp=Path(temporary)
    for label, source, diag in [('baseline',old,0),('disabled',new,0),('enabled',new,1)]:
        text=prefix+'\n#include "'+str(ROOT/PATHS[4])+'"\n'+collector+'\n'+stub+'\n'+aliases+'\n'
        for p, sig in [(PATHS[2],'int readEmData('),(PATHS[2],'void* EmReadSearch('),
                       (PATHS[1],'int cEmMgr::construct('),(PATHS[0],'static cEm* emMustCreate('),
                       (PATHS[0],'cEm* EmSetFromList2(')]: text+=body(source[p],sig)+'\n'
        text+=main
        (OUT/(label+'.cpp')).write_text(text)
        file=temp/(label+'.cpp');exe=temp/(label+'-host');file.write_text(text)
        build=subprocess.run(['g++','-std=c++17','-O1','-g0','-fsanitize=undefined','-fno-sanitize-recover=all',
            *defines,'-DRE4DC_ISSUE52_ACTOR_DIAG='+str(diag),str(file),'-o',str(exe)],capture_output=True,text=True)
        assert build.returncode==0,(label,build.stderr[-12000:])
        run=subprocess.run([str(exe)],capture_output=True,text=True)
        assert run.returncode==0,(label,run.stdout,run.stderr)
        rows=[json.loads(line) for line in run.stdout.splitlines()]
        results.append(dict(variant=label,fixture_sha256=sha(text.encode()),exe_sha256=sha(exe.read_bytes()),
                            build_stderr=build.stderr,stdout=rows,stderr=run.stderr))
    assert results[0]['stdout'][0]==results[1]['stdout'][0]==results[2]['stdout'][0]
task_pins=[]
for p in ['src/game/scheduler.cpp','src/game/sce_sys.cpp','include/scheduler.h']:
    task_pins.append(dict(path=p,base=BASE,sha256=sha(git('show',BASE+':'+p))))
receipt=dict(base=BASE,source_pins=pins,source_task_pins=task_pins,
             runner_sha256=sha(Path(__file__).read_bytes()),disabled_preprocessor_controls=preprocessed,host=results,
             no_runtime_guard_changes=True,shared_claim='DIAGNOSTIC-SOURCE-CLAIM-02.json',
             limits=['Actual collector/wrappers and admission, constructor, enemy lookup/read functions execute with bounded host dependencies.',
                     'No SH4 layout, full translation-unit/target object, real scheduling, archive binding or physical I/O acceptance.',
                     'Host uses pointer-sized u32 to compile recovered pointer arithmetic; fixture DLL branch is not exercised.',
                     'Native task resolver is source-reviewed; host supplies task identities.',
                     'No image, guest, target build, process inventory, release or hardware check.'])
(OUT/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'receipt_sha256':sha((OUT/'receipt.json').read_bytes()),
                  'host':[(r['variant'],r['stdout']) for r in results],
                  'disabled_exact_controls':len(preprocessed)},indent=2))
