from pathlib import Path
import subprocess,resource,json,hashlib,sys
resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,256*1024*1024));resource.setrlimit(resource.RLIMIT_CORE,(0,0))
root=Path('/dev/shm/rain-diag-review94f/source');test=root/'port/dreamcast/tools/d367/rain_diag24/test_rain_diag.py';scope={'__file__':str(test),'__name__':'independent_extract'};s=test.read_text();exec(compile(s[:s.index("receipt={'source_base'")],str(test),'exec'),scope)
f=scope['unit'](scope['new'],scope['esp']);f=f.replace('int main(int argc,char**argv){if(argc>1)return legacy_main(argc,argv);','int original_test_main(int argc,char**argv){if(argc>1)return legacy_main(argc,argv);')
f+=r'''
void change_live_num(){flt06.num=1099;}
void change_live_alpha(){flt06.cur[3]=17;}
void change_live_target(){flt06.col[3]=79;}
void change_live_stop(){pG->Stop_flg|=0x08000000;}
void change_live_indoor(){pG->Status_flg[1]|=0x02000000;}
int main(int argc,char**argv){assert(argc==2);setup();switch(std::stoi(argv[1])){case0:break;}
 return 0;}
'''
# Avoid bringing an extra STL parser into actual excerpt fixture.
f=f[:f.rindex('int main(int argc')]+r'''
int main(){unsigned reproduced=0;
for(auto action:{change_live_num,change_live_alpha,change_live_target,change_live_stop,change_live_indoor}){
 setup();native_action=action;image();assert(sent==320);assert(valid_sample()&&(physical.state_flags&RD_SAMPLE));
 assert(physical.native_accepted==320);++reproduced;
}
std::printf("REPRODUCED %u native-return samples retain RD_SAMPLE while post-call live key changes are freshly snapshotted\n",reproduced);
}
'''
out=Path('/mnt/c/Game Dev/Emulators/codex-lanes/rain-diag24/review');ram=Path('/dev/shm/rain-diag-review94f/independent');ram.mkdir(exist_ok=True);cpp=ram/'live.cpp';exe=ram/'live';cpp.write_text(f);(out/'actual-return-live-state-counterexample.cpp').write_text(f)
cmd=['g++','-std=c++17','-O2','-Wall','-Wextra','-Wno-unused-parameter','-DRE4DC_GAME=1','-DRE4DC_RAIN_DIAG_HOST_TEST=1','-DRE4DC_RAIN_R10C_DC=1','-DRE4DC_RAIN_R10C_DIAG=1',str(cpp),'-o',str(exe)];p=subprocess.run(cmd,capture_output=True,text=True);assert p.returncode==0,p.stderr;p=subprocess.run(['/lib64/ld-linux-x86-64.so.2',str(exe)],capture_output=True,text=True);assert p.returncode==0,p.stderr
(out/'independent-live-state-counterexample.json').write_text(json.dumps({'source':'94f55ff4fe4a57478d35fdd392ee8e53914d36ce','scope':'actual new C++ helpers + actual setter/callback/flush excerpts; mocked native provider; deterministic contract adversaries, not observed guest mutation','cases':['flt06.num','flt06.cur alpha','flt06.col target alpha','Stop','indoor'],'reproduced':'RD_SAMPLE retained and valid_sample true after changed live state re-snapshotted at return','actual_current_native_mutation_reachability':'not demonstrated; no such writes evident in current provider','stdout':p.stdout,'fixture_sha256':hashlib.sha256(f.encode()).hexdigest(),'RLIMIT_AS_bytes':256*1024*1024,'SDK':False,'guests':False},indent=2)+'\n');print(p.stdout)