#!/usr/bin/env python3
"""Host checks for the exact diagnostic helper and preprocessed OFF token identity.
No target compiler, SDK, Make, asset generation or game execution.
"""
import hashlib,json,pathlib,re,resource,subprocess,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[5]
PATH='src/game/espgen45.cpp'
def bounded():
 resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,256*1024*1024))
def run(args,**kw):return subprocess.run(args,check=True,text=True,capture_output=True,timeout=120,preexec_fn=bounded,**kw)
def function(text,signature):
 start=text.index(signature);end=text.index('{',start)+1;depth=1
 while depth:
  depth+=(text[end]=='{')-(text[end]=='}');end+=1
 return text[start:end]
def preprocess(source):
 source=re.sub(r'^\s*#include[^\n]*','',source,flags=re.M)
 return run(['g++','-x','c++','-E','-P','-nostdinc','-DRE4DC_WATER_PS2=1','-DRE4DC_WATER45_NATIVE=1','-DRE4DC_WATER45_LEAN=1','-DRE4DC_WATER_PS2_EXT=1','-'],input=source).stdout

def main():
 old=run(['git','show','140a699f8ead7b406e76581de7075191acf77a96:'+PATH],cwd=ROOT).stdout;new=(ROOT/PATH).read_text()
 before=preprocess(old);after=preprocess(new)
 assert before==after,'default OFF preprocessed tokens differ'
 body=function(new,'static void WaterPs2EarlyDiag(')
 fixture='''#include <cstring>
#include <cstdint>
#include <cstdarg>
using u32=std::uint32_t;
unsigned G_ROOM_ID=0, logs=0;
void re4dc_log(const char*,...){++logs;}
'''+body+'''
int main(){
 u32 m[6]={3,0,0,0,0,3};
 G_ROOM_ID=0x100;WaterPs2EarlyDiag(0,1,0,m);if(logs)return 1;
 G_ROOM_ID=0x107;WaterPs2EarlyDiag(10,1,0,m);if(logs!=1)return 2;
 WaterPs2EarlyDiag(309,1,0,m);if(logs!=1)return 3;
 WaterPs2EarlyDiag(310,1,0,m);if(logs!=2)return 4;
 m[3]=2;WaterPs2EarlyDiag(311,1,0,m);if(logs!=3)return 5;
 G_ROOM_ID=0x10a;WaterPs2EarlyDiag(312,1,0,m);if(logs!=4)return 6;
 WaterPs2EarlyDiag(0xfffffff0u,1,0,m);if(logs!=5)return 7;
 WaterPs2EarlyDiag(0x20u,1,0,m);if(logs!=5)return 8;
 WaterPs2EarlyDiag(0x120u,1,0,m);if(logs!=6)return 9;
 return 0;
}
'''
 with tempfile.TemporaryDirectory(prefix='water-coverage24-',dir='/dev/shm') as td:
  cpp=pathlib.Path(td)/'diag.cpp';exe=pathlib.Path(td)/'diag';cpp.write_text(fixture)
  run(['g++','-std=c++11','-Wall','-Wextra','-Werror','-O2',str(cpp),'-o',str(exe)]);run([str(exe)])
 print(json.dumps({'off_preprocessed_tokens_identical':True,'preprocessed_sha256':hashlib.sha256(before.encode()).hexdigest(),'diagnostic_actual_helper_host_controls':9,'target_object_identity':'NOT RUN','sdk_or_guest':False},indent=2))
if __name__=='__main__':main()
