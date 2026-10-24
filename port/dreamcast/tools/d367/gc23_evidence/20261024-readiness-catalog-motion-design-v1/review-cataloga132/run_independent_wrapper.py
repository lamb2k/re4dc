from pathlib import Path
import sys,subprocess,resource,json,hashlib,tempfile
resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,256*1024*1024));resource.setrlimit(resource.RLIMIT_CORE,(0,0))
ROOT=Path('/dev/shm/gc-catalog-reviewa132/source');TESTS=ROOT/'port/dreamcast/tools/d367/gc_port23';sys.path.insert(0,str(TESTS));import test_catalog_defensive as t
out=Path('/mnt/c/Game Dev/Emulators/codex-lanes/gc-port23/review-cataloga132'); t.DefensiveCatalogTests.setUpClass();C=t.DefensiveCatalogTests
try:
 f=C.fixture[:C.fixture.index('int main(int argc')]
 f=f.replace('RetireOpen,RetireTotal,InterleaveBind}', 'RetireOpen,RetireTotal,InterleaveBind,CoreReplace,OpenFail,TotalShort,SeekFail,ReadFail}')
 f=f.replace('int fs_open(const char*,int){assert(!live_fd);','int fs_open(const char*,int){assert(!live_fd);if(hook==OpenFail){hook=NoHook;++opens;return -1;}')
 f=f.replace('off_t fs_total(int fd){assert(fd==live_fd);','off_t fs_total(int fd){assert(fd==live_fd);if(hook==TotalShort){hook=NoHook;return 127;}')
 f=f.replace('++seeks;cursor=unsigned(at);','++seeks;cursor=unsigned(at);if(hook==SeekFail){hook=NoHook;return at+1;}')
 f=f.replace('++reads;if(cursor+n>file.size())','++reads;if(hook==ReadFail){hook=NoHook;return -1;}if(hook==CoreReplace){hook=NoHook;retire_catalog();const unsigned char byte=17;const CatalogRow newer={"geometry","a",fingerprint(&byte,1),PS2};assert(install(&newer,1));}if(cursor+n>file.size())')
 f+=r'''
int main(int argc,char**argv){assert(argc==2);const unsigned n=std::stoi(argv[1]);
 if(n==0){hook=CoreReplace;assert(!ensure_disc_catalog());assert(disc_state.load()==Failed&&!bind_a().value&&live_fd&&opens==1&&!closes);assert(!ensure_disc_catalog());retire_disc_catalog();assert(!live_fd&&closes==1&&disc_state.load()==FreshInstall);assert(ensure_disc_catalog()&&opens==2&&bind_a().value);}
 if(n==1){disc_setup();const auto old=bind_a();hook=CoreReplace;AssetDescription d;memset(&d,0xff,sizeof d);assert(!describe_checked(old,&d)&&!d.kind[0]&&!d.id[0]);assert(disc_state.load()==Ready&&!checked_current(old));const auto fresh=bind_a();assert(fresh.value&&fresh.value!=old.value&&describe_checked(fresh,&d)&&d.provenance==PS2);}
 if(n==2){hook=OpenFail;assert(!ensure_disc_catalog()&&disc_state.load()==Failed&&!live_fd&&opens==1);assert(!ensure_disc_catalog()&&opens==1);retire_disc_catalog();assert(disc_state.load()==FreshInstall&&!closes);assert(ensure_disc_catalog()&&opens==2&&bind_a().value);}
 if(n==3){hook=TotalShort;assert(!ensure_disc_catalog()&&disc_state.load()==Failed&&live_fd&&opens==1);const int oldfd=live_fd;assert(!ensure_disc_catalog()&&live_fd==oldfd&&opens==1&&!closes);retire_disc_catalog();assert(!live_fd&&closes==1);assert(ensure_disc_catalog()&&opens==2&&bind_a().value);}
 if(n==4||n==5){disc_setup();const auto old=bind_a();hook=n==4?SeekFail:ReadFail;AssetDescription d;memset(&d,0xff,sizeof d);assert(!describe_checked(old,&d)&&!d.kind[0]&&!d.id[0]);assert(disc_state.load()==Failed&&!checked_current(old)&&live_fd&&!closes);explicit_reinstall(old);}
 assert(!io_depth);
}
'''
 C.fixture=f;exe=C.compile('independent_wrapper');(out/'actual-wrapper-policy-controls.cpp').write_text(f);results=[]
 for n,name in enumerate(['wrapper_failed_install_retires_new_core_replacement','ready_disc_read_preserves_replacement_but_rejects_old_description','open_failure_sticky_without_descriptor','short_total_retains_exact_descriptor_until_retry','seek_failure_sticky','negative_read_sticky']):
  p=subprocess.run(['/lib64/ld-linux-x86-64.so.2',str(exe),str(n)],capture_output=True,text=True);assert p.returncode==0,(name,p.stderr);results.append({'name':name,'exit':p.returncode})
 rec={'source':'a132648e8199b50a5ac51cec4d339fe7dbc60135','scope':'actual full gate/index/disc; independent extra mocked callback/error schedules; no SDK/guest','tests':results,'fixture_sha256':hashlib.sha256(f.encode()).hexdigest(),'RLIMIT_AS_bytes':256*1024*1024,'compiler_jobs':1};(out/'independent-wrapper-policy.json').write_text(json.dumps(rec,indent=2)+'\n');print('PASS',len(results),'independent actual wrapper schedules')
finally:C.tearDownClass()