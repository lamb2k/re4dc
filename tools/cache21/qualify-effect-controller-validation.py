"""Run the actual controller body with explicit native-read/model boundaries."""
from pathlib import Path
import subprocess, json, hashlib, shutil
tree=Path('/root/probe/codex-cache21-integration-next')
out=Path('/root/probe/cache21-effect-controller-host-20261021-01')
assert not out.exists()
assert shutil.disk_usage('/mnt/c').free >= 18*1024**3+64*1024**2
out.mkdir()
mk=tree/'port/dreamcast/game/game30.mk'
mk.write_text(mk.read_text().rstrip()+'\n')
subprocess.run(['git','-C',str(tree),'diff','--check'],check=True)
original=subprocess.check_output(['git','-C',str(tree),'show','2598b8a56819589644604e32b7c6577d2d1ec532:src/game/espgen10.cpp'],text=True)
candidate=(tree/'src/game/espgen10.cpp').read_text()
def body(s):
 start=s.index('void espgen10_Update(EspgenWork* w)\n{')
 end=s.index('\n// Step 0',start)
 return s[start:end]
prefix=r'''
#include <cassert>
#include <cstdio>
#include <stdexcept>
struct Vec { float x,y,z; };
struct cModel { unsigned be_flag=1,serial=7,nParts=1; Vec ang{}; float mat[3][4]{}; cModel* getPartsPtr(unsigned){return this;} };
struct EspGenWork { unsigned Set_time=0; };
struct EspSeqData { unsigned num=2,flags=0; EspGenWork rec[2]{}; };
struct Espgen10Work { EspSeqData* head; cModel* pMod; unsigned Guid_pMod=7,Null_parts_no=0,Flg=0,Time_cnt=0,no=0,Rand_seed=0; float Mat[3][4]{}; Vec Offset{},Ang{}; void* p8=nullptr; };
struct EspgenWork { void* work; int info=0; };
struct RetiredRead {};
static bool retired=false,accept=true;
static int refs,reads,pushes,errors,sets,matrices;
static unsigned last_flag;
static EspGenWork* re4dc_effect_ref(EspSeqData* h,unsigned n){++refs;if(retired)throw RetiredRead{}; assert(n<h->num);return &h->rec[n];}
static EspGenWork* re4dc_effect_read(EspGenWork* p,EspGenWork& scratch){++reads;scratch=*p;return &scratch;}
static void PushEspgen(EspgenWork*){++pushes;}
struct Log { template<class... A> void err(A...){++errors;} }; static Log log_; static Log* pLog=&log_;
static void PSMTXIdentity(float m[3][4]){++matrices;for(int i=0;i<3;++i)for(int j=0;j<4;++j)m[i][j]=(i==j);}
static void RotMatrix(float[3][4],Vec*){}
static void PSVECAdd(Vec*a,Vec*b,Vec*r){*r={a->x+b->x,a->y+b->y,a->z+b->z};}
static void PSMTXMultVecSR(float[3][4],Vec*a,Vec*r){*r=*a;}
template<class... A> static bool EspgenDataSet(EspSeqData*,unsigned,int*,unsigned*,cModel*,unsigned,float(*)[3][4],Vec*,Vec*,void*,int flag){++sets;last_flag=flag;return accept;}
'''
suffix=r'''
static void reset(){refs=reads=pushes=errors=sets=matrices=0;last_flag=0;retired=false;accept=true;}
int main(){
 int cases=0;
 // Retired backing is represented by a checked native-read boundary, not an
 // unsafe host dereference; all actual controller decisions are unmodified.
 for(int k=0;k<12;++k){reset();EspSeqData h;cModel model;Espgen10Work p{};p.head=&h;p.pMod=&model;EspgenWork w{&p};
  if(k==0)model.be_flag=0;
  else if(k==1)model.be_flag=0x201;
  else if(k==2)model.serial=8;
  else if(k>=3&&k<=9)p.Null_parts_no=(k==9?0xFF:0xF8+k-3);
  else if(k==10)p.pMod=nullptr;
  else p.Null_parts_no=1;
  retired=true;bool caught=false;try{espgen10_Update(&w);}catch(RetiredRead&){caught=true;}
#if defined(RE4DC_EFFECT_CONTROLLER_VALIDATE_FIRST) && RE4DC_EFFECT_CONTROLLER_VALIDATE_FIRST
  assert(!caught&&refs==0&&reads==0&&pushes==1&&p.Time_cnt==0&&p.no==0);
#else
  assert(caught&&refs==1&&reads==0&&pushes==0&&p.Time_cnt==0&&p.no==0);
#endif
  ++cases;
 }
 // Ordinary live sequences preserve final controller state and emissions.
 for(int k=0;k<7;++k){reset();EspSeqData h;cModel model;Espgen10Work p{};p.head=&h;p.pMod=&model;p.Offset={1,2,3};EspgenWork w{&p};
  h.rec[0].Set_time=1;h.rec[1].Set_time=2;
  if(k==0){} // future record
  if(k==1){p.pMod=nullptr;p.Null_parts_no=0xFE;}
  if(k==2){p.Time_cnt=2;} // unsorted record
  if(k==3){h.rec[0].Set_time=0;} // one emission
  if(k==4){h.rec[0].Set_time=h.rec[1].Set_time=0;p.Flg=2;} // two emissions
  if(k==5){h.rec[0].Set_time=0;accept=false;} // emitter refuses
  if(k==6){p.Flg=1;} // already prepared matrix
  espgen10_Update(&w);
  if(k==2)assert(errors==1&&pushes==1&&sets==0&&p.Time_cnt==2);
  else if(k==5)assert(sets==1&&p.no==0&&p.Time_cnt==0&&pushes==0);
  else {assert(p.Time_cnt==1);assert(sets==(k==3?1:k==4?2:0));assert(p.no==unsigned(sets));assert(pushes==(k==4?1:0));}
  if(k==4)assert(last_flag==1);
  if(k==1)assert(p.Mat[0][3]==1&&p.Mat[1][3]==2&&p.Mat[2][3]==3);
  assert(reads==refs);++cases;
 }
 // Global controllers and otherwise valid parents still need live backing.
 for(int k=0;k<2;++k){reset();EspSeqData h;cModel model;Espgen10Work p{};p.head=&h;p.pMod=k?&model:nullptr;p.Null_parts_no=0xFE;EspgenWork w{&p};retired=true;bool caught=false;try{espgen10_Update(&w);}catch(RetiredRead&){caught=true;}assert(caught&&refs==1);++cases;}
 printf("%d actual-source controller cases passed\n",cases);
}
'''
rows=[]
for mode,text in [('baseline',original),('unset',candidate),('zero',candidate),('enabled',candidate)]:
 folder=out/mode;folder.mkdir()
 src=folder/'fixture.cpp';src.write_text(prefix+body(text)+suffix)
 cmd=['g++','-std=c++17','-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all','-DRE4DC_GAME=1']
 if mode in ('zero','enabled'):cmd+=['-DRE4DC_EFFECT_CONTROLLER_VALIDATE_FIRST='+str(int(mode=='enabled'))]
 cmd += [str(src),'-o',str(folder/'fixture')]
 run=subprocess.run(cmd,text=True,capture_output=True);(folder/'compile.log').write_text(run.stdout+run.stderr);assert run.returncode==0,run.stderr
 test=subprocess.run([str(folder/'fixture')],text=True,capture_output=True);(folder/'test.log').write_text(test.stdout+test.stderr);assert test.returncode==0,(mode,test.stdout,test.stderr)
 rows.append({'mode':mode,'cases':21,'result':test.stdout.strip(),'fixture_sha256':hashlib.sha256(src.read_bytes()).hexdigest()})
receipt={'kind':'actual-source-controller-validation','source_head':'2598b8a56819589644604e32b7c6577d2d1ec532','candidate_sha256':hashlib.sha256(candidate.encode()).hexdigest(),'rows':rows,'limits':['Actual espgen10_Update body; model/matrix/log/emitter and native read boundaries explicit host stubs.','Retired backing represented by checked decoder boundary. Not a hardware UAF test.','Global/valid-parent backing lifetime, controller quiescence and whole reset remain open.','No full program, Flycast, release or physical Dreamcast acceptance.']}
(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
