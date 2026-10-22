#!/usr/bin/env python3
"""Read-only pinned motion/archive/UI lifecycle source trace. No compile/model runtime."""
import argparse,hashlib,json,pathlib,re,subprocess,sys
sys.dont_write_bytecode=True
from audit_archive_borrow_boundaries import body
PIN='ef23404565c43af2cb9a1532cc386bbf876a6f4f';RUNTIME='f3149dfc7a8e9bbf317eae6d192d9665b9568ce5'
SPECS={
'port/dreamcast/game/platform/native_motion.cpp':['extern "C" int re4dc_motion_bind(','extern "C" unsigned re4dc_motion_forget_dead_heaps()','extern "C" void re4dc_motion_hold(','extern "C" void re4dc_motion_unbind(','extern "C" void re4dc_motion_retire_all()','void release_binding(','const unsigned char* record('],
'port/dreamcast/game/motion_bridge.cpp':['extern "C" void* re4dc_motion_alloc(','extern "C" int re4dc_motion_owner_live(','extern "C" void re4dc_motion_free('],
'port/dreamcast/game/sscrn_bridge.cpp':['extern "C" void re4dc_subscreen_swap_open(','extern "C" void re4dc_subscreen_swap_close('],
'port/dreamcast/game/parts_bridge.cpp':['template<class T> void thaw_type()'],
'src/game/read.cpp':['int readEmData(ReadModule* m, int id, void* addr, u32 size)','void InitModule(ReadModule* m)','void EmReadInit()'],
'src/game/sscrn.cpp':['void SubScreenExitCore('],
'src/game/game.cpp':['void gameRoomMemInit()','void gameEnding()','void gameDiedemo(DiedemoWork* w)'],
'src/game/main.cpp':['void systemSoftReset()','void systemResetCommon()','int systemResetCheck()'],
'src/game/main_mem.cpp':['void MemSuspendHeap(','void MemSignalHeap(','int MemDestroyHeap(','void MemClearAllHeap()'],
'src/lib/OSAlloc.c':['int OSCreateHeap(','void OSDestroyHeap(','void OSFreeToHeap('],
'src/game/snd.cpp':['void SndSystemReset()'],
'port/dreamcast/game/platform/subscreen_backing.cpp':['void re4dc_ssb_get(','void re4dc_ssb_close()'],
'port/dreamcast/game/platform/mem.cpp':['void re4dc_missing('],
'port/dreamcast/game/ui_bridge.cpp':['extern "C" void re4dc_room_leave()']}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--repo',required=True);ap.add_argument('--out',required=True);a=ap.parse_args();out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=False)
 def git(*args):return subprocess.check_output(['git','-C',a.repo,*args])
 sources={};manifest=[];objects=[]
 for path,sigs in SPECS.items():
  raw=git('show',PIN+':'+path);text=raw.decode();sources[path]=text;manifest.append(dict(path=path,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),blob=git('rev-parse',PIN+':'+path).decode().strip(),same_as_runtime_f314=raw==git('show',RUNTIME+':'+path)))
  for sig in sigs:
   m=re.search(re.escape(sig)+r'[^;{]*\{',text);assert m,(path,sig);code,start,end=body(text[m.start():],sig);offset=text[:m.start()].count('\n');objects.append(dict(path=path,signature=sig,start=start+offset,end=end+offset,body=code))
 checks=[]
 def b(sig):return next(o['body']for o in objects if o['signature']==sig)
 def ck(name,value):assert value,name;checks.append(dict(name=name,result='PASS',kind='static source condition; no observed normal failure proof'))
 bind=b('extern "C" int re4dc_motion_bind(');forget=b('extern "C" unsigned re4dc_motion_forget_dead_heaps()');live=b('extern "C" int re4dc_motion_owner_live(');close=b('extern "C" void re4dc_subscreen_swap_close(');opening=b('extern "C" void re4dc_subscreen_swap_open(');bridge=sources['port/dreamcast/game/motion_bridge.cpp'];motion=sources['port/dreamcast/game/platform/native_motion.cpp']
 ck('binding records borrow archive MTC not owned copy','*b={a,bytes,mtc+32,count,slots,' in bind)
 ck('MTC binding admitted only currentheap4',bind.index('if(!mtc)return 1')<bind.index('if(re4dc_motion_current_heap()!=4)return 0;')<bind.index('re4dc_motion_alloc(meta)'))
 ck('slot allocation captures current OS handle','const int owner=Heap[MemGetCurrentHeap()].handle;' in bridge and 'p->heap=owner;return p+1;' in bridge)
 ck('owner_live is integer handle equality not generation','for(int h=0;h<MEM_HEAP_NUM;++h)if(Heap[h].handle==handle)return 1;' in live)
 ck('owner_live reads custom prefix before pointer','((const MotionAllocation*)p-1)->heap' in live)
 ck('recount does not validate archive ownership', 're4dc_motion_owner_live(b.archive)' not in forget and 're4dc_motion_owner_live(b.records)' not in forget)
 ck('recount checks slots then resident data then borrowed records',forget.index('re4dc_motion_owner_live(b.slots)')<forget.index('re4dc_motion_owner_live(s.data)')<forget.index('b.resident+=aligned(word(record(b,i)+4))'))
 ck('recount lock spans operation and unhold',forget.index('Locked guard')<forget.index('word(record(b,i)+4)')<forget.index('hold=false'))
 ck('miss outside4 refuses before allocation','if(re4dc_motion_current_heap()!=4)fail("motion miss outside owning room heap");' in motion)
 ck('native UI hold before pool freeze before clear',opening.index('re4dc_motion_hold(1)')<opening.index('re4dc_parts_freeze(')<opening.index('memset(wk->pBuf, 0, kSsAramSize)'))
 ck('heap suspension retains live handle', 'HeapHead[h].free = NULL;' in b('void MemSuspendHeap(') and 'Heap[no].status = 1;' in b('void MemSuspendHeap(') and 'Heap[no].handle = -1' not in b('void MemSuspendHeap('))
 ck('heap signal restores same backed descriptor','h * sizeof(OSHeapDescriptor)' in b('void MemSignalHeap('))
 core=b('void SubScreenExitCore(');ck('normal core destroys12 restores4 before swapclose',core.index('MemDestroyHeap(12)')<core.index('MemSignalHeap(4)')<core.index('MemSetCurrentHeap(4)')<core.index('re4dc_subscreen_swap_close(wk)')<core.index('RoomData.restartRelData()'))
 ck('restored spans hash before source consumers',close.index('h = hash_words(')<close.index('re4dc_parts_thaw()')<close.index('re4dc_motion_forget_dead_heaps()'))
 ck('hash mismatch fatal is after recount',close.index('re4dc_motion_forget_dead_heaps()')<close.index('if (h != open_hash) re4dc_missing('))
 ck('backing freed and swappedfalse before hash decision',close.index('re4dc_ssb_close()')<close.index('swapped = false;')<close.index('if (h != open_hash)'))
 ck('plain backing copy checks capacity but not content hash','subscreen backing underrun' in b('void re4dc_ssb_get(') and 'hash' not in b('void re4dc_ssb_get('))
 ck('closed backing discarded before diagnosis','free_blocks();' in b('void re4dc_ssb_close()') and 'store = Store{};' in b('void re4dc_ssb_close()'))
 ck('fatal missing actually does not return','for (;;) {' in b('void re4dc_missing(') and 'thd_sleep(1000)' in b('void re4dc_missing('))
 read=b('int readEmData(ReadModule* m, int id, void* addr, u32 size)');ck('normal fresh read requests currentheap allocation','mode | 0x8004' in read and 'm->flag |= 4;' in read)
 ck('external borrowed archive path exists but does not own free','BitOff16(m->flag, 4);' in read and 'pArc = addr;' in read)
 module=b('void InitModule(ReadModule* m)');ck('module unbind precedes archive free',module.index('re4dc_motion_unbind(m->pArc)')<module.index('Mem_free(m->pArc)'))
 ck('room heap reset retires motions before replacing4',b('void gameRoomMemInit()').index('re4dc_motion_retire_all()')<b('void gameRoomMemInit()').index('MemReplaceHeap(3, 4)'))
 ck('stage native leave retires motion owners','re4dc_motion_retire_all();' in b('extern "C" void re4dc_room_leave()'))
 ck('ending uses normal retirement wrapper','gameRoomMemInit();' in b('void gameEnding()'))
 ck('softreset heaps destroyed before common close',b('void systemSoftReset()').index('MemClearAllHeap()')<b('void systemSoftReset()').index('systemResetCommon()'))
 ck('common reset closes UI before clearingtasks and modules',b('void systemResetCommon()').index('SubScreenExitCore(&SubScreenWk)')<b('void systemResetCommon()').index('TaskAllClear()')<b('void systemResetCommon()').index('EmReadInit()'))
 ck('destroyed heap clears game handle','Heap[no].handle = -1;' in b('int MemDestroyHeap('))
 ck('OS heap handles reused by firstfree descriptor','if (hd->size < 0)' in b('int OSCreateHeap(') and 'return heap;' in b('int OSCreateHeap(') and 'hd->size = -1;' in b('void OSDestroyHeap('))
 ck('sound reset body does not create source heaps',all(x not in b('void SndSystemReset()')for x in ['MemCreateHeap','OSCreateHeap','MemSetCurrentHeap']))
 census=git('grep','-n','EmReadSearch(',PIN,'--','src').decode();(out/'EmReadSearch-census.txt').write_text(census)
 # Raw callsite census retained; do not treat declarations/comments as invocations.
 ck('normal diedemo refusal selects soft reset', 'BitOn(pG->System_flg, 0x4000000);' in b('void gameDiedemo(DiedemoWork* w)'))
 ck('source reset dispatch invokes softreset for that bit','if (pG->System_flg & 0x4000000)' in b('int systemResetCheck()') and 'systemSoftReset();' in b('int systemResetCheck()'))
 ck('allheapclear destroys each active heap without motion retirement','MemDestroyHeap(i);' in b('void MemClearAllHeap()') and 'motion_retire' not in b('void MemClearAllHeap()'))
 ck('release_binding frees slots even no clip data','re4dc_motion_free(b.slots);b={};' in b('void release_binding('))
 ck('motion_free bypasses ModuleMemFree and targets captured handle','OSFreeToHeap(allocation->heap,allocation)' in b('extern "C" void re4dc_motion_free('))
 ck('allocator free requires still valid heap','HeapArray[heap].size >= 0' in b('void OSFreeToHeap('))
 invocations=[];declarations=[]
 paths=git('grep','-l','EmReadSearch(',PIN,'--','src').decode().splitlines()
 for prefixed in paths:
  path=prefixed.split(':',1)[1];text=git('show',PIN+':'+path).decode();masked=re.sub(r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"',lambda m:' '*len(m[0]),text)
  for match in re.finditer(r'\bEmReadSearch\(',masked):
   start=match.end();depth=0;args=[];last=start
   for i in range(start,len(masked)):
    ch=masked[i]
    if ch=='(':depth+=1
    elif ch==')':
     if depth==0:args.append(text[last:i].strip());break
     depth-=1
    elif ch==',' and depth==0:args.append(text[last:i].strip());last=i+1
   entry=dict(path=path,line=text[:match.start()].count('\n')+1,args=args)
   assert len(args)==3,entry
   if re.search(r'\b(?:int|void)\b',args[1]):declarations.append(entry)
   else:invocations.append(entry)
 ck('all actual source EmReadSearch caller destinations zero',bool(invocations) and all(x['args'][1]=='0' for x in invocations))
 (out/'EmReadSearch-classified.json').write_text(json.dumps(dict(invocations=invocations,declarations=declarations),indent=2)+'\n')
 receipt=dict(source_pin=PIN,runtime_pin=RUNTIME,files=manifest,objects=objects,checks=checks,normal_conclusion='No normal live-slots/dead-archive recount path established. Fresh source callers use addr0; current4/admission and matched retirement are preconditions, not archive epoch proof.',fault_containment=dict(confirmed_order='Restore hash computed, backing closed, swapped false/thaw/message restore/recount then hash mismatch fatal.',conditional_witness='If bad restored Slot.data is nonzero invalid while slot allocation header still matches a live handle, actual owner_live reads custom prefix at invalid data-32 before planned hash fatal. Alternatively changed archive record length is consumed before mismatch diagnosis.',not_claimed=['No observed restore corruption','No normal root cause or issue52 cause','No target/compiler execution']),reset_contract='Normal diedemo softreset with UI closed and any live MTC binding reaches heap destruction before motion_unbind; release_binding ultimately OSFreeToHeap captured dead handle. OSFREE_CHECK/assert build behavior differs; no target failure observed. ActiveUI requires restore before any retire_all, so no blanket post-clear owner test.',minimum_proposal='Main-owned default0 hash-validate-first guard immediately after all restore/hash loops and before backing close/thaw/recount/unhold; preserve actual nonreturning failure and OFF tokens. No generic archive owner_live header probe.')
 (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');size=sum(p.stat().st_size for p in out.iterdir()if p.is_file());assert size<150000;print(json.dumps(dict(result='PASS',checks=len(checks),objects=len(objects),files=len(manifest),fresh_bytes=size)))
if __name__=='__main__':main()