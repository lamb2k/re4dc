from pathlib import Path
import sys,subprocess,resource,json,hashlib
resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,256*1024*1024));resource.setrlimit(resource.RLIMIT_CORE,(0,0))
root=Path('/dev/shm/gc-catalog-reviewa132/source');sys.path.insert(0,str(root/'port/dreamcast/tools/d367/gc_port23'));import test_catalog_defensive as t
out=Path('/mnt/c/Game Dev/Emulators/codex-lanes/gc-port23/review-cataloga132');C=t.DefensiveCatalogTests;C.setUpClass()
try:
 f=C.fixture[:C.fixture.index('int main(int argc')]+r'''
void fill_unknown(){for(unsigned i=0;i<8;++i){char id[8];snprintf(id,sizeof id,"id%u",i);assert(bind_checked("geometry",id,digest(i)).value);}}
unsigned hits(const std::string& text,const char* needle){unsigned n=0;size_t at=0;while((at=text.find(needle,at))!=std::string::npos){++n;++at;}return n;}
int main(int argc,char**argv){assert(argc==2);const unsigned test=std::stoi(argv[1]);
 if(test==0){assert(install(nullptr,0));fill_unknown();io_depth=1;assert(!bind_checked("geometry","overflow",digest(9)).value);assert(logs.empty());io_depth=0;assert(install(nullptr,0));begin(0x221,11,Required);const auto why=logs.find("why=unknown-capacity consumer=0 unowned=1");const auto next=logs.find("GC-ASSET-BEGIN v=2 room=0221 visit=11");assert(why!=std::string::npos&&next!=std::string::npos&&why<next);end(1);assert(logs.find("overflow=0 errors=0")!=std::string::npos&&hits(logs,"why=unknown-capacity")==1);}
 if(test==1){assert(install(nullptr,0));begin(0x222,12,Required);logs.clear();fill_unknown();io_depth=1;assert(!bind_checked("geometry","over1",digest(9)).value);assert(!bind_checked("geometry","over2",digest(10)).value);assert(logs.empty());io_depth=0;end(1);assert(logs.find("why=unknown-capacity consumer=0 room=0222 visit=12")!=std::string::npos&&logs.find("overflow=2 errors=2")!=std::string::npos&&hits(logs,"why=unknown-capacity")==1);const auto saved=logs;pump();assert(logs==saved);}
 if(test==2){disc_setup();const auto old=bind_a();begin(0x223,13,Required);end(1);logs.clear();hook=RetireDiscRead;assert(!bind_a().value&&logs.empty()&&!checked_current(old));explicit_reinstall(old);assert(logs.empty());begin(0x224,14,Required);const auto why=logs.find("why=catalog-read consumer=0 unowned=1");const auto next=logs.find("GC-ASSET-BEGIN v=2 room=0224 visit=14");assert(why!=std::string::npos&&next!=std::string::npos&&why<next);end(1);assert(hits(logs,"why=catalog-read")==1&&logs.find("overflow=0 errors=0")!=std::string::npos);}
 if(test==3){assert(install(nullptr,0));begin_startup_closed(15,Required);logs.clear();io_depth=1;retire_catalog();assert(logs.empty());io_depth=0;begin_closed(0x225,16,Required);const auto why=logs.find("why=catalog-retired-during-room consumer=0 phase=startup visit=15");const auto next=logs.find("GC-ASSET-BEGIN v=2 room=0225 visit=16");assert(why!=std::string::npos&&next!=std::string::npos&&why<next&&logs.find("errors=2")!=std::string::npos);end(1);assert(hits(logs,"why=catalog-retired-during-room")==1);}
 assert(!io_depth);
}
'''
 C.fixture=f;exe=C.compile('independent_faults');(out/'actual-fault-lifetime-controls.cpp').write_text(f);results=[]
 for i,name in enumerate(['unowned_capacity_survives_replacement_drains_before_new_begin','repeated_owned_capacity_deduplicates_reason_but_preserves_two_errors_and_overflow','post_END_unowned_read_survives_explicit_reinstall_before_new_begin','startup_owned_retire_reports_old_scope_before_room_begin']):
  p=subprocess.run(['/lib64/ld-linux-x86-64.so.2',str(exe),str(i)],capture_output=True,text=True);assert p.returncode==0,(name,p.stderr);results.append({'name':name,'exit':p.returncode})
 (out/'independent-fault-lifetime.json').write_text(json.dumps({'source':'a132648e8199b50a5ac51cec4d339fe7dbc60135','scope':'actual full gate/index/disc; strict log !io_depth; independent deterministic schedules, no guest','tests':results,'fixture_sha256':hashlib.sha256(f.encode()).hexdigest(),'RLIMIT_AS_bytes':256*1024*1024,'compiler_jobs':1},indent=2)+'\n');print('PASS',len(results),'independent fault lifetime schedules')
finally:C.tearDownClass()