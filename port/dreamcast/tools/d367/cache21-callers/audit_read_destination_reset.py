#!/usr/bin/env python3
"""Pinned source ordering/precondition audit only; no C++ or target execution."""
import argparse, hashlib, json, pathlib, re, subprocess, sys
sys.dont_write_bytecode=True
from audit_archive_borrow_boundaries import body
PIN='f3149dfc7a8e9bbf317eae6d192d9665b9568ce5'
SPECS={
 'include/datactrl.h':[],
 'port/dreamcast/game/platform/mem.cpp':['void re4dc_missing('],
 'src/game/datactrl.cpp':['void cDataUnit::setLoadToMram()','int cDataUnit::setClear()','void cDataUnit::checkMallocRelease()','void cDataCtrl::initDataUnit()','void cDataCtrl::check()'],
 'src/game/game.cpp':['void gameDoordemo()','void gameRoomInit()','void gameRoomMemInit()','void gameEnding()'],
 'src/game/main.cpp':['void systemSoftReset()','void systemResetCommon()'],
 'src/game/stage.cpp':['void StageSet()'],
 'src/game/dvd.cpp':['void cDvd::ReadCancelAll()','int cDvd::ReadCancel(','void cDvdQueue::readMain()','int cDvdQueue::Read()','void cDvd::readProcMain(','void cDvd::Watcher()','void cDvdQueue::Initialize()'],
 'src/game/scheduler.cpp':['void TaskSchedulerMain(TASK* t)','void TaskSleep(int frames)','void TaskKill(TASK* t)'],
 'src/game/main_mem.cpp':['int MemDestroyHeap(','int MemReplaceHeap(','void MemClearAllHeap()'],
 'src/game/read.cpp':['void EmReadInit()','void InitModule(ReadModule* m)','void ReadAreaData()','void ReadPlayerData(','int readEmData(ReadModule* m, int id, void* addr, u32 size)'],
 'src/game/roomdata.cpp':['void cRoomData::linkRelData('],
 'port/dreamcast/game/platform/os.cpp':['void OSCancelThread('],
 'port/dreamcast/game/platform/dvd.cpp':['s32 DVDReadAsyncPrio(','int DVDCancelAsync(','s32 DVDCancelAll(void)'],
 'port/dreamcast/game/platform/native_event_file.cpp':['bool carrier_can_retire(','extern "C" int re4dc_cabin_carriers_reset()','extern "C" int re4dc_cabin_carriers_before_heap(','extern "C" int re4dc_cabin_carriers_retire_heap('],
 'port/dreamcast/game/platform/native_cabin.cpp':['extern "C" int re4dc_cabin_before_heap_change('],
 'port/dreamcast/game/ui_bridge.cpp':['extern "C" void re4dc_room_leave()'],
}
def main():
 p=argparse.ArgumentParser();p.add_argument('--repo',required=True);p.add_argument('--out',required=True);a=p.parse_args()
 out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=False)
 def git(*args):return subprocess.check_output(['git','-C',a.repo,*args])
 fs={};objects=[];manifest=[]
 for path,sigs in SPECS.items():
  raw=git('show',PIN+':'+path);src=raw.decode();fs[path]=src
  current=git('show','HEAD:'+path)
  manifest.append(dict(path=path,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),blob=git('rev-parse',PIN+':'+path).decode().strip(),same_as_observed_head=raw==current))
  for sig in sigs:
   match=re.search(re.escape(sig)+r'[^;{]*\{',src);assert match,(path,sig)
   code,start,end=body(src[match.start():],sig);offset=src[:match.start()].count('\n')
   objects.append(dict(path=path,signature=sig,start=start+offset,end=end+offset,sha256=hashlib.sha256(code.encode()).hexdigest(),body=code))
 def b(sig):return next(x['body'] for x in objects if x['signature']==sig)
 checks=[]
 def c(name,condition):assert condition,name;checks.append(dict(name=name,result='PASS',kind='static source condition, not runtime proof'))
 door=b('void gameDoordemo()');reset=b('void cDataCtrl::initDataUnit()');clear=b('int cDataUnit::setClear()')
 c('door descriptor reset precedes DVD and ARAM cancellation',door.index('DC.initDataUnit();')<door.index('Dvd.ReadCancelAll();')<door.index('Aram.DmaCancelAll();'))
 c('no explicit task sleep between door reset and read cancellation','TaskSleep' not in door[door.index('DC.initDataUnit();'):door.index('Dvd.ReadCancelAll();')])
 c('unit reset preflights carriers before descriptor erase',reset.index('re4dc_cabin_carriers_reset()')<reset.index('memclr_asm(u, sizeof(cDataUnit))'))
 c('unit reset is not ordinary queue cancel or owned allocation release','ReadCancel' not in reset and 'checkMallocRelease' not in reset)
 c('single unit clear cancels before owned allocation release',clear.index('Dvd.ReadCancel(m_id, 0x40)')<clear.index('Dvd.ReadCheck(')<clear.index('checkMallocRelease();'))
 c('single unit clear is one poll without local task wait','while (' not in clear and 'TaskSleep' not in clear)
 soft=b('void systemSoftReset()');c('soft reset cancels before all heap destruction',soft.index('Dvd.ReadCancelAll();')<soft.index('MemClearAllHeap();'))
 cancel=b('void cDvd::ReadCancelAll()');c('cancel all kills either worker before queue erase',cancel.index('iTaskKill();')<cancel.index('memclr_asm(DvdQueue') and cancel.index('TaskKill(3);')<cancel.index('memclr_asm(DvdQueue'))
 c('platform cancel all itself is no-op',b('s32 DVDCancelAll(void)').strip()=='return 0;')
 os=b('void OSCancelThread(');c('actual cancellation waits native IO then destroys thread',os.index('while (thread->nativeIoDepth')<os.index('thd_destroy(thread->kt)'))
 dvd=b('s32 DVDReadAsyncPrio(');c('generic filesystem read scope spans callback',dvd.index('Re4dcIoScope io;')<dvd.index('fs_read(')<dvd.index('callback(result, fi)'))
 step=b('int cDvdQueue::Read()');c('whole source pump step enters native guard before source call',step.index('re4dc_dvd_step_begin()')<step.index('(this->*func_tbl[m_Rno0])();')<step.index('re4dc_dvd_step_end(native_step)'))
 main=b('void cDvdQueue::readMain()');c('destination transfer follows cancellation check',main.index('if (chk(0x100000))')<main.index('(this->*trans_proc_tbl[(*ph)->type])(DVD_BUFF'))
 c('readMain source data comes through staging','fileReadAsync(DVD_BUFF' in main)
 proc=b('void cDvd::readProcMain(');c('ordinary queue worker sleeps outside individual guarded Read steps','while (q->Read() == 1)' in proc and 'if (!q->chk(0x100))' in proc and 'TaskSleep(1);' in proc)
 task=b('void TaskSchedulerMain(TASK* t)');c('ordinary scheduler requires yielded acknowledgement','if (t != &Task[TASK_ISR])' in task and 'OSWaitSemaphore(&nativeTaskYielded[t - Task])' in task)
 c('ordinary TaskSleep requires resume token','OSWaitSemaphore(&nativeTaskResume[t - Task]);' in b('void TaskSleep(int frames)'))
 load=b('void cDataUnit::setLoadToMram()');c('ordinary DataCtrl request mode derives from u8 wait','wait | 0x10' in load and 'u8 wait;' in fs['include/datactrl.h'])
 init=b('void cDvdQueue::Initialize()');c('ISR bit is request mode100 after sync bit','else if (w->mode & 0x100)' in init)
 room=b('void gameRoomInit()');c('room reset precedes player and area loads',room.index('gameRoomMemInit();')<room.index('ReadPlayerData(')<room.index('ReadAreaData();')<room.index('DC.initDataUnit();'))
 c('room command hold begins before heap reset',room.index('DC.m_nblock_read_stop = 1;')<room.index('gameRoomMemInit();'))
 c('native DAR loader awaits request','0x8104)' in b('void ReadAreaData()') and 'while ((status = Dvd.ReadCheckInfo(req, &roomInfo)) == 0)' in b('void ReadAreaData()'))
 c('player ISR loader awaits completion','0x8100)' in b('void ReadPlayerData(') and 'while ((ret = Dvd.ReadCheckInfo(req, &info)) != 1)' in b('void ReadPlayerData('))
 enemy=b('int readEmData(ReadModule* m, int id, void* addr, u32 size)');c('enemy ISR load during room init awaits completion','if (pG->Rno0 == 2)' in enemy and 'mode = 0x100;' in enemy and 'while ((ret = Dvd.ReadCheckInfo(req, &info)) != 1)' in enemy)
 rel=b('void cRoomData::linkRelData(');c('REL ISR load awaits completion','0x104,' in rel and 'while ((ret = Dvd.ReadCheck(' in rel)
 ending=b('void gameEnding()');c('ending directly resets heap without a local blanket drain','gameRoomMemInit();' in ending and 'ReadCancel' not in ending)
 retire=b('void gameRoomMemInit()');c('room reset itself contains no DVD or ordinary DataCtrl drain','ReadCancel' not in retire and 'initDataUnit' not in retire)
 stage=b('void StageSet()');c('stage native retirement precedes heap replacement',stage.index('re4dc_room_leave();')<stage.index('MemReplaceHeap(1, 2);'))
 carriers=b('bool carrier_can_retire(');c('carrier retirement covers own readers and event/DMA scopes','!c.readers' in carriers and '!carrier_event_readers' in carriers and '!carrier_dma_scope' in carriers)
 mr=b('int MemReplaceHeap(');c('CABIN heap replacement revalidates after media yielding hook',mr.index('re4dc_cabin_carriers_before_heap')<mr.index('re4dc_movie_world_before_heap_change')<mr.rindex('re4dc_cabin_carriers_before_heap'))
 c('heap destroy has carrier retirement before OS destruction',b('int MemDestroyHeap(').index('re4dc_cabin_carriers_retire_heap')<b('int MemDestroyHeap(').index('OSDestroyHeap('))
 c('normal door drains before archive unregister',door.index('Dvd.ReadCancelAll();')<door.index('EmReadInit();'))
 module=b('void InitModule(ReadModule* m)');c('module guard precedes unbind unlink free and row erase',module.index('re4dc_cabin_carrier_before_free(m->pArc)')<module.index('re4dc_motion_unbind')<module.index('DLL_Unlink')<module.index('re4dc_effect_unbind')<module.index('Mem_free(m->pArc)')<module.index('memclr_asm(m, sizeof(ReadModule))'))
 common=b('void systemResetCommon()');c('common reset clears tasks before archive unregister',common.index('TaskAllClear();')<common.index('EmReadInit();'))
 c('soft reset reaches common cleanup after heap clear',soft.index('MemClearAllHeap();')<soft.index('systemResetCommon();'))
 c('fatal service is nonreturning', 'for (;;) {' in b('void re4dc_missing(') and 'thd_sleep(1000);' in b('void re4dc_missing('))
 result=dict(pin=PIN,observed_head=git('rev-parse','HEAD').decode().strip(),files=manifest,objects=objects,checks=checks,conclusion='No new normal source-reachable pending-write/heap-reuse counterexample established. Contracts and open entries described in review; static assertions do not prove task quiescence or destination epoch.',not_executed=['No compiler/C++ lifecycle fixture','No runtime edits','No build/stage/guest','No old Event or window test rerun'])
 (out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n')
 size=sum(f.stat().st_size for f in out.rglob('*') if f.is_file());assert size<800000
 print(json.dumps(dict(result='PASS',static_checks=len(checks),source_objects=len(objects),files=len(manifest),fresh_bytes=size)))
if __name__=='__main__':main()