import hashlib
import os
from pathlib import Path
import resource
import subprocess
import tempfile
import unittest

from catalog_index import build

ROOT = Path(__file__).resolve().parents[3]
GAME = ROOT / 'game'
PLATFORM = GAME / 'platform'
BASE = '1d63cffe3a232c402418f2f2d919e7abae476957'

FIXTURE = r'''
#include "gc_asset_gate.h"
#include "native_io.h"
#include <cassert>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>
#include <sys/types.h>
using namespace re4dc_gcasset;
unsigned char initial_file[]={@FILE@};
std::vector<unsigned char> file(initial_file,initial_file+sizeof initial_file);
std::string logs;unsigned cursor,io_depth,opens,closes,seeks,reads;int live_fd;
bool short_read,close_failure,nested_failed;CheckedAsset other;
enum Hook{NoHook,Interleave,RetireDiscSeek,RetireDiscRead,RetireCoreRead,EnsureOpen,RetireOpen,RetireTotal};Hook hook=NoHook;
extern "C" void re4dc_log(const char* fmt,...){char s[256];va_list a;va_start(a,fmt);vsnprintf(s,sizeof s,fmt,a);va_end(a);logs+=s;}
extern "C" void* re4dc_io_begin(){++io_depth;return &io_depth;}
extern "C" void re4dc_io_end(void* p){assert(p==&io_depth&&io_depth);--io_depth;}
int fs_open(const char*,int){assert(!live_fd);live_fd=100+int(++opens);cursor=0;
 if(hook==EnsureOpen){hook=NoHook;nested_failed=!ensure_disc_catalog();}
 if(hook==RetireOpen){hook=NoHook;retire_disc_catalog();}
 return live_fd;}
int fs_close(int fd){assert(fd==live_fd);++closes;if(close_failure)return -1;live_fd=0;return 0;}
off_t fs_total(int fd){assert(fd==live_fd);if(hook==RetireTotal){hook=NoHook;retire_disc_catalog();}return file.size();}
off_t fs_seek(int fd,off_t at,int){assert(fd==live_fd);++seeks;cursor=unsigned(at);
 if(hook==Interleave){hook=NoHook;AssetDescription d;memset(&d,0xff,sizeof d);nested_failed=!describe_checked(other,&d);assert(nested_failed&&!d.kind[0]&&!d.id[0]);}
 if(hook==RetireDiscSeek){hook=NoHook;retire_disc_catalog();assert(closes==0&&live_fd==fd);}
 return at;}
ssize_t fs_read(int fd,void* p,unsigned n){assert(fd==live_fd);++reads;if(cursor+n>file.size())return 0;memcpy(p,file.data()+cursor,n);cursor+=n;
 if(hook==RetireDiscRead){hook=NoHook;retire_disc_catalog();assert(closes==0&&live_fd==fd);}
 if(hook==RetireCoreRead){hook=NoHook;retire_catalog();}
 return short_read?n-1:n;}
#include "gc_asset_disc.cpp"
Digest digest(unsigned i){const unsigned char byte=17+i;return fingerprint(&byte,1);}
CheckedAsset bind_a(){return bind_checked("geometry","a",digest(0));}
void disc_setup(){assert(ensure_disc_catalog());assert(opens==1&&live_fd&&io_depth==0);assert(disc_state.load()==Ready);}
void explicit_reinstall(CheckedAsset old){
 const int fd=live_fd;const unsigned old_closes=closes;
 assert(!ensure_disc_catalog());assert(opens==1&&live_fd==fd&&closes==old_closes);
 retire_disc_catalog();assert(!live_fd&&closes==old_closes+1&&disc_state.load()==FreshInstall&&!checked_current(old));
 assert(ensure_disc_catalog()&&opens==2&&disc_state.load()==Ready);
 const auto fresh=bind_a();assert(fresh.value&&fresh.value!=old.value&&checked_current(fresh)&&!checked_current(old));
}
struct Reader {unsigned phase=0,action=0;bool fired=false;};
CatalogRow replacement;Reader nested_reader;
unsigned independent_read(void* opaque,unsigned off,void* dst,unsigned n){
 auto& r=*static_cast<Reader*>(opaque);if(off>file.size()||n>file.size()-off)return 0;
 memcpy(dst,file.data()+off,n);
 const bool trigger=(r.phase==1&&off==0&&n==file.size())||(r.phase==2&&off==0&&n==128)||(r.phase==3&&off==128&&n==112)||(r.phase==4&&n==112);
 if(r.action&&trigger){const unsigned action=r.action;r.action=0;r.fired=true;retire_catalog();
  if(action==2)assert(install(&replacement,1));
  if(action==3){nested_reader={};const auto pin=fingerprint(file.data(),file.size());assert(install_index(independent_read,&nested_reader,file.size(),pin));}
 }
 return n;
}
void core_case(unsigned phase,unsigned action,bool binding,bool describing){
 replacement={"geometry","a",digest(0),PS2};Reader r;
 const auto pin=fingerprint(file.data(),file.size());
 if(binding||describing){assert(install_index(independent_read,&r,file.size(),pin));const auto old=bind_a();assert(old.value);
  r.phase=4;r.action=action;
  if(binding){const auto result=bind_a();assert(r.fired&&!result.value);}
  if(describing){AssetDescription desc;memset(&desc,0xff,sizeof desc);assert(!describe_checked(old,&desc));assert(r.fired&&!desc.kind[0]&&!desc.id[0]);}
  assert(!checked_current(old));
 }else{r.phase=phase;r.action=action;assert(!install_index(independent_read,&r,file.size(),pin));assert(r.fired);}
 if(action==1){assert(!bind_a().value);}
 else{const auto token=bind_a();AssetDescription desc;assert(token.value&&describe_checked(token,&desc));assert(desc.provenance==(action==2?PS2:GameCube));}
}
int main(int argc,char**argv){assert(argc==2);const unsigned test=unsigned(std::stoi(argv[1]));
 if(test>=20){unsigned x=test-20;const unsigned action=x%3+1,phase=x/3+1;core_case(phase,action,false,false);return 0;}
 if(test>=14){unsigned x=test-14;core_case(4,x%3+1,x<3,x>=3);return 0;}
 if(test==8){hook=EnsureOpen;assert(ensure_disc_catalog());assert(nested_failed&&opens==1&&disc_state.load()==Ready);return 0;}
 if(test==9||test==10){hook=test==9?RetireOpen:RetireTotal;assert(!ensure_disc_catalog());assert(live_fd&&disc_state.load()==Retired&&closes==0);explicit_reinstall({});return 0;}
 disc_setup();const auto a=bind_a();other=bind_checked("geometry","b",digest(1));assert(a.value&&other.value);AssetDescription desc;
 if(test==0){assert(describe_checked(a,&desc)&&desc.provenance==GameCube);begin(0x111,1,Required);logs.clear();emitted_checked(SourceGeometry,a);end(1);assert(logs.find("provenance=gc")!=std::string::npos&&logs.find("errors=0")!=std::string::npos);}
 if(test==1){begin(0x112,1,Required);logs.clear();hook=Interleave;emitted_checked(SourceGeometry,a);end(1);assert(nested_failed&&!checked_current(a));assert(logs.find("errors=0")==std::string::npos&&logs.find("catalog_ok=0")!=std::string::npos);assert(disc_state.load()==Failed&&closes==0&&live_fd);explicit_reinstall(a);}
 if(test==2||test==3){hook=test==2?RetireDiscRead:RetireDiscSeek;memset(&desc,0xff,sizeof desc);const unsigned read_before=reads;assert(!describe_checked(a,&desc)&&!desc.kind[0]&&!desc.id[0]);assert(!checked_current(a)&&disc_state.load()==Retired&&closes==0);if(test==3)assert(reads==read_before);explicit_reinstall(a);}
 if(test==4){hook=RetireCoreRead;memset(&desc,0xff,sizeof desc);assert(!describe_checked(a,&desc)&&!desc.kind[0]);assert(!checked_current(a));}
 if(test==5){short_read=true;assert(!describe_checked(a,&desc));short_read=false;assert(disc_state.load()==Failed&&!checked_current(a));explicit_reinstall(a);}
 if(test==6){close_failure=true;const int fd=live_fd;retire_disc_catalog();assert(disc_state.load()==Retired&&live_fd==fd&&closes==1);assert(!ensure_disc_catalog()&&opens==1);close_failure=false;retire_disc_catalog();assert(!live_fd&&closes==2&&disc_state.load()==FreshInstall);assert(ensure_disc_catalog()&&opens==2&&!checked_current(a));}
 if(test==7){const int fd=live_fd;assert(!disc_lock.test_and_set());retire_disc_catalog();assert(live_fd==fd&&closes==0&&disc_state.load()==Retired);disc_lock.clear();assert(!ensure_disc_catalog()&&live_fd==fd&&opens==1&&closes==0);explicit_reinstall(a);}
 if(test==11){short_read=true;retire_disc_catalog();assert(!ensure_disc_catalog());short_read=false;assert(disc_state.load()==Failed&&opens==2&&live_fd);assert(!ensure_disc_catalog()&&opens==2);retire_disc_catalog();assert(ensure_disc_catalog()&&opens==3);}
 if(test==12){assert(!disc_lock.test_and_set());const unsigned before=seeks;assert(!disc_read(nullptr,128,&desc,112));disc_lock.clear();assert(seeks==before&&disc_state.load()==Failed&&!checked_current(a));explicit_reinstall(a);}
 if(test==13){retire_catalog();const auto fresh_pin=fingerprint(file.data(),file.size());Reader r;assert(install_index(independent_read,&r,file.size(),fresh_pin));const auto fresh=bind_a();assert(fresh.value&&fresh.value!=a.value&&!checked_current(a));}
 assert(!io_depth);
}
'''


class DefensiveCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scratch = tempfile.TemporaryDirectory(prefix='gc-catalog24-', dir='/dev/shm')
        cls.work = Path(cls.scratch.name)
        (cls.work / 'kos').mkdir()
        (cls.work / 'kos/fs.h').write_text('#pragma once\n#include <sys/types.h>\nusing file_t=int;\nconstexpr int FILEHND_INVALID=-1;\nint fs_open(const char*,int);int fs_close(int);off_t fs_total(int);off_t fs_seek(int,off_t,int);ssize_t fs_read(int,void*,unsigned);\n')
        rows = [{'kind': 'geometry', 'id': chr(97+i), 'sha256': hashlib.sha256(bytes([17+i])).hexdigest(), 'provenance': 'gc' if not i else 'ps2', 'evidence': 'synthetic reviewed fixture'} for i in range(3)]
        blob, cls.pin = build(rows)
        cls.fixture = FIXTURE.replace('@FILE@', ','.join(str(x) for x in blob))
        cls.exe = cls.compile('current')

    @classmethod
    def tearDownClass(cls):
        cls.scratch.cleanup()

    @classmethod
    def compile(cls, name, gate=None, index=None, disc=None):
        platform = cls.work / name
        platform.mkdir()
        for n in ['gc_asset_gate.cpp', 'gc_asset_disc.cpp']:
            (platform/n).write_text((PLATFORM/n).read_text())
        (platform/'include').symlink_to(PLATFORM/'include', target_is_directory=True)
        if gate is not None:(platform/'gc_asset_gate.cpp').write_text(gate)
        if disc is not None:(platform/'gc_asset_disc.cpp').write_text(disc)
        # A modified include needs an isolated header view, not edits to source.
        if index is not None:
            (platform/'include').unlink();(platform/'include').mkdir()
            for f in (PLATFORM/'include').iterdir():
                if f.name != 'gc_asset_index.inc':(platform/'include'/f.name).symlink_to(f)
            (platform/'include/gc_asset_index.inc').write_text(index)
        cpp = platform/'fixture.cpp';exe=platform/'fixture';cpp.write_text(cls.fixture)
        cmd=['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-DRE4DC_GC_ASSET_GATE=1',f'-DRE4DC_GC_ASSET_CATALOG_SHA256="{cls.pin.hex()}"','-I',str(cls.work),'-I',str(platform),'-I',str(platform/'include'),str(cpp),str(platform/'gc_asset_gate.cpp'),'-o',str(exe)]
        out=subprocess.run(cmd,capture_output=True,text=True)
        if out.returncode:raise AssertionError(out.stderr)
        return exe

    def run_case(self, case, exe=None, success=True):
        def no_core():resource.setrlimit(resource.RLIMIT_CORE,(0,0))
        out=subprocess.run(['/lib64/ld-linux-x86-64.so.2',str(exe or self.exe),str(case)],capture_output=True,text=True,preexec_fn=no_core)
        if success:self.assertEqual(out.returncode,0,out.stderr)
        else:self.assertEqual(out.returncode,-6,out.stderr)

    def test_actual_shared_cursor_busy_retire_and_sticky_retry(self):
        for case in range(14):
            with self.subTest(case=case):self.run_case(case)

    def test_actual_bind_and_describe_reject_callback_retire_replace(self):
        for case in range(14,20):
            with self.subTest(case=case):self.run_case(case)

    def test_actual_install_hash_header_rows_keep_newer_generation(self):
        for case in range(20,29):
            with self.subTest(case=case):self.run_case(case)

    def test_old_and_mutated_bodies_are_caught(self):
        gate=(PLATFORM/'gc_asset_gate.cpp').read_text();index=(PLATFORM/'include/gc_asset_index.inc').read_text();disc=(PLATFORM/'gc_asset_disc.cpp').read_text()
        mutations=[('unowned_cursor',None,None,disc.replace('if(!guard.held){disc_failed();return 0;}','if(!guard.held){}'),1),
                   ('callback_epoch',gate.replace('if(active || !index_generation(epoch))return false;','if(active)return false;'),index.replace('return index_generation(epoch)?count:0;','return count;').replace('if(!read || !index_generation(epoch))return 0;','(void)epoch;if(!read)return 0;').replace('if(!index_generation(epoch))return false;','if(false)return false;').replace('catalog_ok && index_generation(epoch);','true;'),None,20),
                   ('bind_global_epoch',gate.replace('if(!catalog_ok || !index_generation(epoch))return {};','if(!catalog_ok)return {};').replace('return {epoch<<14|index};','return {catalog_epoch<<14|index};').replace('const unsigned epoch=catalog_epoch,rows=catalog_rows;','const unsigned epoch=catalog_epoch,rows=catalog_rows;(void)epoch;'),index.replace('return index_generation(epoch)?count:0;','return count;').replace('if(!read || !index_generation(epoch))return 0;','(void)epoch;if(!read)return 0;').replace('if(!index_generation(epoch))return false;','if(false)return false;').replace('catalog_ok && index_generation(epoch);','true;'),None,15),
                   ('busy_retire_reopens',None,None,disc.replace('if(!guard.held)return; // exact busy fd stays retained; no deferred auto-close','if(!guard.held){disc_state.store(FreshInstall);return;}'),7),
                   ('unsafe_busy_close',None,None,disc.replace('if(!guard.held)return; // exact busy fd stays retained; no deferred auto-close','if(!guard.held){} // mutant closes an owned reader'),2)]
        # Whole old gate/index ensures the reproduced late-description false
        # green remains a negative, in addition to individual new guard mutants.
        old_gate=subprocess.check_output(['git','-C',str(ROOT.parent.parent),'show',BASE+':port/dreamcast/game/platform/gc_asset_gate.cpp'],text=True)
        old_index=subprocess.check_output(['git','-C',str(ROOT.parent.parent),'show',BASE+':port/dreamcast/game/platform/include/gc_asset_index.inc'],text=True)
        mutations.append(('old_epoch_bodies',old_gate,old_index,None,4))
        for name,g,i,d,case in mutations:
            with self.subTest(mutant=name):self.run_case(case,self.compile(name,g,i,d),success=False)

    def test_retirement_at_epoch_exhaustion_never_publishes(self):
        private=self.work/'private_epoch.cpp';exe=self.work/'private_epoch'
        body=self.fixture[:self.fixture.index('int main(int argc')]+r'''
#include "gc_asset_gate.cpp"
int main(){
 constexpr unsigned terminal=(1u<<18)-1;
 // Start an install at the last admissible epoch, then retire while its
 // catalog_ok is already false. Retirement must remain distinguishable.
 catalog_epoch=terminal-2;Reader r;r.phase=1;r.action=1;
 const auto pin=fingerprint(file.data(),file.size());
 assert(!install_index(independent_read,&r,file.size(),pin));
 assert(r.fired&&catalog_epoch==terminal&&!catalog_ok);
 assert(!install_index(independent_read,&r,file.size(),pin));
 const CatalogRow row={"geometry","a",digest(0),PS2};
 assert(!install(&row,1)&&!bind_a().value&&!checked_current({terminal<<14}));
 retire_catalog();assert(catalog_epoch==terminal&&!catalog_ok);
}
'''
        private.write_text(body)
        cmd=['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-DRE4DC_GC_ASSET_GATE=1',f'-DRE4DC_GC_ASSET_CATALOG_SHA256="{self.pin.hex()}"','-I',str(self.work),'-I',str(PLATFORM),'-I',str(PLATFORM/'include'),str(private),'-o',str(exe)]
        out=subprocess.run(cmd,capture_output=True,text=True);self.assertEqual(out.returncode,0,out.stderr)
        out=subprocess.run(['/lib64/ld-linux-x86-64.so.2',str(exe)],capture_output=True,text=True);self.assertEqual(out.returncode,0,out.stderr)

    def test_default_off_empty_and_parent_object_identity(self):
        repo=ROOT.parent.parent
        for name in ['gc_asset_gate.cpp','gc_asset_disc.cpp']:
            parent=subprocess.check_output(['git','-C',str(repo),'show',BASE+':port/dreamcast/game/platform/'+name])
            for encoding in [None,'0']:
                outputs=[]
                for label,data in [('parent',parent),('current',(PLATFORM/name).read_bytes())]:
                    tag=name.replace('.cpp','')+label+str(encoding);src=self.work/(tag+'.cpp');obj=self.work/(tag+'.o');src.write_bytes(data)
                    cmd=['g++','-std=c++17','-Os','-Wall','-Wextra','-Werror','-I',str(PLATFORM),'-c',str(src),'-o',str(obj)]
                    if encoding is not None:cmd.insert(1,'-DRE4DC_GC_ASSET_GATE='+encoding)
                    out=subprocess.run(cmd,capture_output=True,text=True);self.assertEqual(out.returncode,0,out.stderr)
                    syms=subprocess.check_output(['nm','--defined-only',str(obj)],text=True);self.assertFalse(syms.strip())
                    subprocess.run(['objcopy','--strip-all',str(obj)],check=True);outputs.append(obj.read_bytes())
                self.assertEqual(outputs[0],outputs[1])


if __name__=='__main__':unittest.main()
