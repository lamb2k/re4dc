#!/usr/bin/env python3
"""Actual EspDataLoad/Release regression for first-admission validation."""
import argparse, ast, hashlib, json, pathlib, subprocess
p=argparse.ArgumentParser();p.add_argument('--source',type=pathlib.Path,required=True);p.add_argument('--out',type=pathlib.Path,required=True);a=p.parse_args()
a.out.mkdir(parents=True,exist_ok=False)
repo=a.source;rel='src/game/eff_sys.cpp';reference='07527f7e75c746c6d9ce938b0327dfba77726387'
old=subprocess.check_output(['git','-C',str(repo),'show',reference+':'+rel],text=True);new=(repo/rel).read_text()
def extract(text,signature):
 start=text.index(signature+'\n{');brace=text.index('{',start);depth=1;end=brace+1
 while depth:
  if text[end]=='{':depth+=1
  elif text[end]=='}':depth-=1
  end+=1
 return text[start:end]
def functions(text):return '\n'.join(extract(text,s)for s in ('int EspDataLoad(u32 addr, u32 owner, int flag)','int EspDataRelease(u32 owner, int flag, int warn)'))
strings={}
for node in ast.parse((pathlib.Path(__file__).parent/'test_effect_registration_failure.py').read_text()).body:
 if isinstance(node,ast.Assign)and len(node.targets)==1 and isinstance(node.targets[0],ast.Name)and node.targets[0].id in ('prefix','body'):strings[node.targets[0].id]=ast.literal_eval(node.value)
prefix=strings['prefix'];fixture=strings['body'].split('int main(){')[0];structs=new[new.index('struct EffIdTbl {'):new.index('extern "C" {')]
main=r'''
int main(){constexpr u32 o=0x36;u32 x;
// NULL does not publish a reference, even after valid admission.
x=fixture(11);CHECK(!EspDataLoad(0,o,0));CHECK(!system_data.ownerCnt[o]&&!regs);
CHECK(EspDataLoad(x,o,0)==1);CHECK(regs==3&&system_data.ownerCnt[o]==1);
CHECK(!EspDataLoad(0,o,0));CHECK(system_data.ownerCnt[o]==1&&regs==3);
// Valid duplicate/release rules, including strict duplicate failure, remain source-identical.
CHECK(EspDataLoad(x,o,1)==0);CHECK(system_data.ownerCnt[o]==2&&regs==3);
CHECK(EspDataRelease(o,1,1)==1);CHECK(system_data.ownerCnt[o]==1&&!rels);
CHECK(EspDataRelease(o,1,1)==1);CHECK(!system_data.ownerCnt[o]&&rels==5);
// Bad first -> corrected retry is the actual defect/repair acceptance case.
x=fixture(10);CHECK(!EspDataLoad(x,o,0));CHECK(system_data.ownerCnt[o]==(FIXED?0:1));CHECK(!regs);
reinterpret_cast<EffData*>(blob)->version=11;CHECK(EspDataLoad(x,o,0)==1);
CHECK(system_data.ownerCnt[o]==(FIXED?1:2));CHECK(regs==(FIXED?3:0));
CHECK(EspDataRelease(o,1,1)==1);CHECK(system_data.ownerCnt[o]==(FIXED?0:1));CHECK(rels==(FIXED?5:0));
// Strict first-load retry must be possible after invalid first admission.
x=fixture(10);CHECK(!EspDataLoad(x,o,1));reinterpret_cast<EffData*>(blob)->version=11;
CHECK(EspDataLoad(x,o,1)==(FIXED?1:0));CHECK(system_data.ownerCnt[o]==(FIXED?1:2));CHECK(regs==(FIXED?3:0));
// Persistent invalid files neither latch a fake success nor consume references with the guard on.
x=fixture(10);CHECK(!EspDataLoad(x,o,0));
for(unsigned i=0;i<300;++i)CHECK(EspDataLoad(x,o,0)==(FIXED?0:1));
CHECK(system_data.ownerCnt[o]==(FIXED?0:200));CHECK(!regs);
CHECK(EspDataRelease(o,0,0)==(FIXED?0:1));CHECK(!system_data.ownerCnt[o]);
// Existing duplicate semantics ignore a changed supplied file while a valid registration exists.
x=fixture(11);CHECK(EspDataLoad(x,o,0)==1);reinterpret_cast<EffData*>(blob)->version=10;
CHECK(EspDataLoad(x,o,0)==1);CHECK(system_data.ownerCnt[o]==2&&regs==3);
CHECK(EspDataRelease(o,0,1)==1);CHECK(!system_data.ownerCnt[o]&&rels==5);
// One owner's failed first admission must not poison a distinct owner.
x=fixture(10);CHECK(!EspDataLoad(x,o,0));reinterpret_cast<EffData*>(blob)->version=11;
CHECK(EspDataLoad(x,o+1,0)==1);CHECK(system_data.ownerCnt[o+1]==1&&regs==3);
CHECK(system_data.ownerCnt[o]==(FIXED?0:1));
// Valid admission still registers nonempty texture and effect-model tables.
x=fixture(11);auto*d=reinterpret_cast<EffData*>(blob);
d->ofsEfmId=256;d->ofsEfm=320;d->ofsTexId=128;d->ofsTpl=160;d->ofsAnm=192;
auto*ids=reinterpret_cast<EffIdTbl*>(blob+128);ids->num=1;ids->ent[0].id=7;
auto*tpl=reinterpret_cast<EffOfsTbl*>(blob+160);tpl->num=1;tpl->ofs[0]=16;
auto*anm=reinterpret_cast<EffOfsTbl*>(blob+192);anm->num=1;anm->ofs[0]=16;
auto*models=reinterpret_cast<EffIdTbl*>(blob+256);models->num=1;models->ent[0].id=9;
auto*mt=reinterpret_cast<EffOfsTbl*>(blob+320);mt->num=1;mt->ofs[0]=16;
auto*entry=reinterpret_cast<EffEfmEnt*>(blob+336);entry->ofsModel=32;entry->ofsTpl=36;entry->ofsMot=40;entry->ofsX=44;
CHECK(EspDataLoad(x,o,0)==1);CHECK(regs==5&&system_data.ownerCnt[o]==1);
CHECK(EspDataLoad(x,o,0)==1);CHECK(regs==5&&system_data.ownerCnt[o]==2);
std::printf("PASS FIXED=%d assertions=%u\n",FIXED,checks);
}
'''
rows=[]
for label,text,enabled in [('baseline',old,0),('off',new,0),('on',new,1)]:
 cpp=a.out/(label+'.cpp');exe=a.out/label;cpp.write_text(prefix+structs+functions(text)+fixture+main)
 cmd=['g++','-std=c++17','-O1','-g','-fno-omit-frame-pointer','-fsanitize=address,undefined','-fno-pie','-no-pie','-DFIXED='+str(enabled),'-DRE4DC_EFFECT_ADMISSION_GUARD='+str(enabled),str(cpp),'-o',str(exe)]
 cp=subprocess.run(cmd,capture_output=True,text=True);(a.out/(label+'-compile.log')).write_text(cp.stdout+cp.stderr);cp.check_returncode()
 cp=subprocess.run([str(exe)],capture_output=True,text=True);(a.out/(label+'-run.log')).write_text(cp.stdout+cp.stderr);print(cp.stdout,end='');cp.check_returncode();rows.append({'arm':label,'result':cp.stdout.strip(),'command':cmd})
def preprocess(text):return subprocess.check_output(['g++','-E','-P','-x','c++','-DRE4DC_EFFECT_ADMISSION_GUARD=0','-'],input=functions(text),text=True)
before=preprocess(old);after=preprocess(new);assert before==after,'OFF extracted source identity failed'
receipt={'reference':reference,'source_sha256':hashlib.sha256(new.encode()).hexdigest(),'source_diff':subprocess.check_output(['git','-C',str(repo),'diff','--',rel],text=True),'arms':rows,'off_extracted_preprocessor_identity':True,'off_projection_sha256':hashlib.sha256(after.encode()).hexdigest(),'scope':'Actual source function bodies; registration/release boundaries instrumented. Synthetic low-address EFF fixtures. No full-TU/linked/gameplay/console acceptance; partial downstream registration remains open.'}
(a.out/'effect-admission-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print('OFF extracted-source preprocessing exact; receipt sealed')