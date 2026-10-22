"""Frozen differential admission controls plus independent core/own semantic oracles."""
from pathlib import Path
import argparse,ast,hashlib,json,os,shutil,signal,struct,subprocess,time
T=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--ref',required=True);p.add_argument('--working-ui',type=Path);p.add_argument('--expect-fixed',action='store_true');p.add_argument('--out',type=Path,required=True);a=p.parse_args()
assert not a.out.exists();start_free=shutil.disk_usage('/mnt/c').free;assert start_free>=18*1024**3+128*1024**2;a.out.mkdir()
sha=lambda b:hashlib.sha256(b).hexdigest()
def blob(path,ref=None):return subprocess.check_output(['git','-C',str(a.source),'show',(ref or a.ref)+':'+path])
def text(raw):return raw.decode('utf-8-sig').replace('\r\n','\n')
path='port/dreamcast/game/platform/native_ui.cpp';raw= a.working_ui.read_bytes()if a.working_ui else blob(path);source=text(raw);old=text(blob(path,'c7e0358a44677a15123a7f4233c4115eba627694'))
def functions(s):
 first=s.index('void preload_select(');start=s.rfind('#if defined(RE4DC_TEX_PKG_SKIP)',0,first);end=s.index('\n#if RE4DC_ROOM_RESIDENT',first)
 begin=s.index('unsigned resident_listed,resident_picked;');stop=s.index('#endif\n#if RE4DC_IO_PROBE',begin)
 return s[start:end]+'\n'+s[begin:stop]
original_test=blob('port/dreamcast/tools/d367/cache21/test_resident_list_cache.py');tree=ast.parse(text(original_test));strings={}
for item in tree.body:
 if isinstance(item,ast.Assign)and len(item.targets)==1 and isinstance(item.targets[0],ast.Name)and isinstance(item.value,ast.Constant)and isinstance(item.value.value,str):strings[item.targets[0].id]=item.value.value
header=blob('port/dreamcast/game/platform/include/resident_list_cache.h');(a.out/'resident_list_cache.h').write_bytes(header)
prefix=strings['prefix'];common=strings['common'];wrapper=strings['wrapper'];main=strings['main']
if a.expect_fixed:
 signature=r'''std::string admission_signature(const std::string&s){unsigned commas=0;std::size_t end=0;for(;end<s.size();++end)if(s[end]==','&&++commas==5)break;std::string out=s.substr(0,end);std::istringstream in(s);std::string word;while(in>>word)if(word[0]=='P')out+=' '+word;return out;}'''
 if 'std::string admission_signature(' not in main:main=main.replace('unsigned step(const char*name',signature+'\nunsigned step(const char*name')
 main=main.replace('if(expected!=actual)', 'if(admission_signature(expected)!=admission_signature(actual))')
else:
 main=main.replace('if(admission_signature(expected)!=admission_signature(actual))','if(expected!=actual)')
cpp=prefix+'\nnamespace ref {\n#define RE4DC_RESIDENT_LIST_CACHE 0\n'+common+functions(old)+wrapper+'\n}\n#undef RE4DC_RESIDENT_LIST_CACHE\nnamespace on {\n#define RE4DC_RESIDENT_LIST_CACHE 1\n'+common+functions(source)+wrapper+'\n}\n'+main
(a.out/'existing-controls.cpp').write_text(cpp)
# Exact CORE_PIN2 lookup body from selected source. Service Entry/Package are projected fixtures.
sig='inline bool core_pinned(const Entry& e)';first=source.index(sig);end=source.index('\n',first);core_pinned=source[first:end]
custom=r'''
void reset(){entries={};missing_keys={};std::memset(preload_picks,0,sizeof(preload_picks));std::memset(core_keys,0,sizeof(core_keys));core_nkeys=0;core_room_on=false;frame=0;
#if RE4DC_RESIDENT_LIST_CACHE
resident_list_cache={};
#endif
}
Snapshot pass(unsigned n,unsigned resident,unsigned limit,unsigned budget,unsigned owner,bool seed){
 ++frame;unsigned bytes=0,before=active_fs->calls;
 if(seed){for(unsigned i=0;i<core_rows.size();++i){auto r=core_rows[i];entries[i]={true,{r.crc,r.fnv},frame-1,{preload_least(r.width,r.height)}};}}
 if(owner){re4dc::texture::SourceIdentityTable table;for(unsigned i=0;i<owner;++i)table.rows.push_back({0xf0000000U+i,0xdead0000U+i,8,8,1});preload_select(table,n,resident,bytes,limit,budget);}
 preload_resident(n,resident,bytes,limit,budget);
 Entry e{};if(!core_rows.empty())e.key={core_rows[0].crc,core_rows[0].fnv};
 bool valid=false;
#if RE4DC_RESIDENT_LIST_CACHE
 valid=resident_list_cache.matches(active_room);
#endif
 return{n,resident,bytes,resident_listed,resident_picked,core_nkeys,core_room_on,core_pinned(e),active_fs->calls-before,valid};
}
'''
common16=common.replace('entries{}','entries{}').replace('std::array<Entry,512>','std::array<Entry,448>').replace('preload_picks[512]','preload_picks[448]').replace('kCoreKeys=64','kCoreKeys=16')
pre=prefix+'\n#include <fstream>\n#include <iterator>\nstruct Snapshot{unsigned n,resident,bytes,listed,picked,core;bool room_on,pinned;unsigned reads;bool cache_valid;};\nstatic std::vector<Rec>core_rows;\n'
semantic=pre+'\nnamespace direct {\n#define RE4DC_RESIDENT_LIST_CACHE 0\n'+common16+core_pinned+'\n'+functions(source)+custom+'\n}\n#undef RE4DC_RESIDENT_LIST_CACHE\nnamespace cached {\n#define RE4DC_RESIDENT_LIST_CACHE 1\n'+common16+core_pinned+'\n'+functions(source)+custom+'\n}\n'+(T/'oracles.inc').read_text()
(a.out/'semantic-oracles.cpp').write_text(semantic)
rows=[];metadata={}
for room in [0,0x101]:
 name='port/dreamcast/tools/d367/vram/resident/r%03x.tsv'%room;data=blob(name);metadata[name]={'sha256':sha(data),'bytes':len(data)}
 for line in text(data).splitlines()[1:]:
  if not line.strip():continue
  key,w,h,fmt,_=line.split('\t');crc,fnv=(int(x,16)for x in key.split('-'));rows.append((room,int(w),int(h),int(fmt),crc,fnv))
rows.sort(key=lambda r:(r[0],r[4],r[5]));fixture=b''.join(struct.pack('<4H2I',*r)for r in rows);fixture+=b'\0'*(-len(fixture)%512);(a.out/'selected-core-room-metadata.bin').write_bytes(fixture)
def guarded(command,name):
 log=a.out/(name+'.log');start=time.time()
 with log.open('xb')as output:
  child=subprocess.Popen(command,stdout=output,stderr=subprocess.STDOUT,start_new_session=True);proc_start=Path(f'/proc/{child.pid}/stat').read_text().split()[21]
  (a.out/(name+'-owned-process.json')).write_text(json.dumps({'pid':child.pid,'pgid':os.getpgid(child.pid),'proc_start':proc_start,'command':command},indent=2)+'\n')
  while child.poll()is None:
   if shutil.disk_usage('/mnt/c').free<18*1024**3+64*1024**2 or time.time()-start>55 or log.stat().st_size>512*1024 or sum(p.stat().st_size for p in a.out.rglob('*')if p.is_file())>=4*1024**2:
    assert os.getpgid(child.pid)==child.pid and Path(f'/proc/{child.pid}/stat').read_text().split()[21]==proc_start;os.killpg(child.pid,signal.SIGTERM);child.wait(timeout=5);raise RuntimeError('owned source-host4MiB resource guard')
   time.sleep(.1)
 assert child.returncode==0,(name,log.read_text()[-4500:])
 return log.read_text()
runs=[]
for pin in [0,1,2]:
 exe=a.out/('existing'+str(pin));cmd=['bash','/root/probe/d367-buildslot.sh','g++','-std=c++17','-O1','-fsanitize=undefined','-fno-sanitize-recover=all','-DRE4DC_CORE_PIN='+str(pin),'-I'+str(a.out),str(a.out/'existing-controls.cpp'),'-o',str(exe)];guarded(cmd,'compile-existing'+str(pin));output=guarded([str(exe)],'run-existing'+str(pin));runs.append({'suite':'existing47','pin':pin,'comparison':'admission_only'if a.expect_fixed else'exact_full_metadata','command':cmd,'output':output})
exe=a.out/'semantic';cmd=['bash','/root/probe/d367-buildslot.sh','g++','-std=c++17','-O1','-fsanitize=undefined','-fno-sanitize-recover=all','-DRE4DC_CORE_PIN=2','-DEXPECT_FIXED='+str(int(a.expect_fixed)),'-I'+str(a.out),str(a.out/'semantic-oracles.cpp'),'-o',str(exe)];guarded(cmd,'compile-semantic');output=guarded([str(exe),str(a.out/'selected-core-room-metadata.bin')],'run-semantic');runs.append({'suite':'independent_semantics','command':cmd,'results':[json.loads(x)for x in output.splitlines()]})
inputs={name:{'sha256':sha(blob(name)),'bytes':len(blob(name))}for name in ['port/dreamcast/game/Makefile','port/dreamcast/game/subscreen.mk','port/dreamcast/tools/d367/test21/release-knobs.txt','port/dreamcast/tools/d367/build-r21.sh']}
record={'scope':'Actual source preload_select/preload_resident and core_pinned with synthetic FS/identities; selected checked-in core+r101 TSV metadata only, not staged target file or normal saturation proof.','ref':a.ref,'working_ui':str(a.working_ui)if a.working_ui else None,'source_raw_sha256':sha(raw),'source_normalized_sha256':sha(source.encode()),'functions_sha256':sha(functions(source).encode()),'helper_sha256':sha(header),'existing_test_sha256':sha(original_test),'oracle_sha256':sha((T/'oracles.inc').read_bytes()),'runner_sha256':sha(Path(__file__).read_bytes()),'recipe_inputs':inputs,'TSV_inputs':metadata,'selected_rows':len(rows),'selected_fixture_sha256':sha(fixture),'expect_fixed':a.expect_fixed,'runs':runs,'output_bytes_before_receipt':sum(p.stat().st_size for p in a.out.rglob('*')if p.is_file()),'C_start':start_free,'C_end':shutil.disk_usage('/mnt/c').free,'limits':'No runtime/recipe/asset edits, no target trigger/performance, SH4/full program/Flycast/release/hardware qualification.'}
(a.out/'receipt.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps({'raw_sha256':record['source_raw_sha256'],'normalized_sha256':record['source_normalized_sha256'],'rows':len(rows),'existing':[r['output'].strip()for r in runs if'output'in r],'semantics':runs[-1]['results'],'output_bytes':record['output_bytes_before_receipt']},indent=2))
