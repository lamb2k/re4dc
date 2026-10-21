#!/usr/bin/env python3
"""Corrected function-bounded source checks. No C++ execution or target acceptance."""
import argparse, hashlib, json, pathlib, re, subprocess

OLD='836a72425d4f753a7b0ef0f3509716621942b461'
NEW='c57ff60f0f462fdd2c419883b0258963504d756a'
FILES=['port/dreamcast/game/platform/native_ui.cpp','port/dreamcast/game/platform/native_model.cpp',
 'port/dreamcast/game/platform/native_draw_plan_owner.cpp','src/game/scheduler.cpp','src/game/main.cpp',
 'src/game/game.cpp','src/game/read.cpp','src/game/dvd.cpp','port/dreamcast/room/texture_package.cpp',
 'port/dreamcast/room/room_storage.cpp']

def body(text,signature):
 # Preserve offsets while removing comments/literals before balancing braces.
 masked=re.sub(r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|\x27(?:\\.|[^\x27\\])*\x27',lambda m:' '*len(m[0]),text)
 start=text.index(signature);op=masked.index('{',start);depth=1
 for i in range(op+1,len(masked)):
  depth+=(masked[i]=='{')-(masked[i]=='}')
  if not depth:return text[op+1:i],text[:start].count('\n')+1,text[:i].count('\n')+1
 raise AssertionError(signature)

def main():
 p=argparse.ArgumentParser();p.add_argument('--repo',required=True);p.add_argument('--out',required=True);a=p.parse_args()
 out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=False)
 def git(*args):return subprocess.check_output(['git','-C',a.repo,*args])
 src={};manifest=[]
 for f in FILES:
  old=git('show',OLD+':'+f);new=git('show',NEW+':'+f);assert old==new,f
  src[f]=new.decode();target=out/'source'/f;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(new)
  manifest.append(dict(path=f,old_commit=OLD,new_commit=NEW,identical=True,blob=git('rev-parse',NEW+':'+f).decode().strip(),sha256=hashlib.sha256(new).hexdigest(),bytes=len(new)))
 checks=[];functions=[]
 def s(suffix):return next(t for f,t in src.items() if f.endswith(suffix))
 def b(text,sig):
  code,start,end=body(text,sig);functions.append(dict(signature=sig,start=start,end=end));return code
 def c(name,condition):assert condition,name;checks.append(dict(name=name,result='PASS',kind='static function-bounded source condition'))
 ui=s('native_ui.cpp');model=s('native_model.cpp');scheduler=s('scheduler.cpp')
 reserve=b(ui,'extern "C" int re4dc_model_packet_reserve(')
 begin=b(ui,'extern "C" int re4dc_model_packet_begin(')
 opening=b(ui,'void stream_open()');retire=b(ui,'extern "C" void re4dc_ui_retire_room()')
 c('reserve includes slab allocation','ensure_model_storage()' in reserve)
 c('reserve has no stream_select or texture load','stream_select(' not in reserve and 'load(' not in reserve and 'resolve(' not in reserve)
 c('begin calls reserve before texture resolution',begin.index('re4dc_model_packet_reserve(')<begin.index('load('))
 c('begin resolves texture before abort check',begin.index('load(')<begin.index('if(stream_aborted)return 0;'))
 c('begin abort check precedes stream_select',begin.index('if(stream_aborted)return 0;')<begin.index('stream_select(list);'))
 c('no generic abort recheck after begin stream_select','stream_aborted' not in begin.split('stream_select(list);',1)[1])
 c('TA open includes present and scene/list admission','present_fence();' in opening and 'pvr_scene_begin();' in opening and 'pvr_list_begin(' in opening)
 c('retire abort is conditional on existing stream','if(stream_scene){stream_aborted=true;stream_retire=true;}' in retire and retire.count('stream_aborted')==1)
 c('no-stream retire fences then clears identities',retire.index('present_fence()')<retire.index('room_identities.clear()'))
 bind=b(model,'    bool bind()');flush=b(model,'    bool flush()')
 c('first bind may load/wait then marks bound',bind.index('re4dc_model_packet_begin')<bind.index('bound=true;'))
 c('later binds short-circuit','if(bound)return true;' in bind)
 c('first flush binds before commit',flush.index('bind()')<flush.index('re4dc_model_packet_commit'))
 c('flush leaves builder bound for later chunks','bound=false' not in flush)
 walk=b(model,'    bool walk(bool emit)');planned=b(model,'    bool walk_plan(')
 c('stream walk reads source on loop continuation','while(offset<p.stream_bytes)' in walk and 'p.stream[offset++]' in walk)
 c('planned walk still refers to source corners','p.stream+part.corner_offset' in planned)
 submit=model[model.index('// Source data remains live throughout this synchronous call.'):]
 c('initial validation walk precedes emit and final bind',submit.index('b.walk(false)')<submit.index('bool okay=emit()')<submit.index('if(okay && b.used)okay=b.bind()'))
 c('UV-scale changed bind can restart source walk','restart_uv=true' in bind and 'okay=emit();' in submit)
 taskmain=b(scheduler,'void TaskSchedulerMain(TASK* t)');sleep=b(scheduler,'void TaskSleep(int frames)')
 c('ordinary source task handshake blocks scheduler','OSWaitSemaphore(&nativeTaskYielded[t - Task])' in taskmain)
 c('ordinary task sleep requires resume token','NativeYieldTask(t);' in sleep and 'OSWaitSemaphore(&nativeTaskResume[t - Task]);' in sleep)
 c('ISR task excluded from ordinary wait','if (t != &Task[TASK_ISR])' in taskmain)
 main=s('main.cpp');c('frame scheduler precedes Trans then ISR work',main.index('TaskScheduler();')<main.index('            Trans();')<main.index('iTaskScheduler();'))
 room=s('game.cpp');c('room reset call sites restricted in game.cpp',len(re.findall(r'(?m)^\s+gameRoomMemInit\(\);',room))==2)
 read=s('read.cpp');native=read.split('iTaskExec(decodeData);',1)[1]
 c('room decode iTask site belongs to PPC branch','#else' in native and 'Native room containers contain an already-decoded LE type-0 payload' in native)
 result=dict(kind='supersedes ca2ea function-boundary labels, not its immutable receipt',source_old=OLD,source_current=NEW,files=manifest,functions=functions,checks=checks,limitations=['No compiler/build/guest','No source task retirement during draw wait demonstrated','Abort flag is not archive epoch ownership','Native room decode iTask is PPC-only; source DVD ISR remains separate'])
 (out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');size=sum(p.stat().st_size for p in out.rglob('*') if p.is_file());assert size<20*1024*1024
 print(json.dumps(dict(result='PASS',checks=len(checks),files_identical=len(manifest),fresh_bytes=size)))
if __name__=='__main__':main()
