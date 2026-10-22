#!/usr/bin/env python3
"""Read-only native DVD request/callback inventory. Static checks, no target execution."""
import argparse,hashlib,json,pathlib,re,subprocess,sys
sys.dont_write_bytecode=True
from audit_archive_borrow_boundaries import body

PIN='edfe8f1765fbbd418235537e7b2f0b3b6aeab25d'
FILES=['src/game/dvd.cpp','src/game/read.cpp','src/game/roomdata.cpp','src/game/stage.cpp',
 'src/game/game.cpp','src/game/main.cpp','src/game/datactrl.cpp','src/game/scheduler.cpp',
 'src/game/snd_str0.cpp','src/game/snd_str1.cpp','src/game/snd_str2.cpp','src/game/snd_ram.cpp',
 'port/dreamcast/game/platform/dvd.cpp','port/dreamcast/game/platform/os.cpp',
 'port/dreamcast/game/platform/audio_strm.cpp','port/dreamcast/game/platform/audio_stub.cpp',
 'port/dreamcast/game/platform/audio_aica.cpp','port/dreamcast/game/platform/include/native_io.h',
 'port/dreamcast/game/Makefile','port/dreamcast/game/game30.mk','include/dvd.h','include/datactrl.h','include/snd_drv.h']

def main():
 p=argparse.ArgumentParser();p.add_argument('--repo',required=True);p.add_argument('--out',required=True);a=p.parse_args();out=pathlib.Path(a.out);out.mkdir(exist_ok=False,parents=True)
 def git(*args):return subprocess.check_output(['git','-C',a.repo,*args])
 src={};manifest=[]
 for f in FILES:
  raw=git('show',PIN+':'+f);src[f]=raw.decode();dest=out/'source'/f;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
  manifest.append(dict(path=f,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),blob=git('rev-parse',PIN+':'+f).decode().strip()))
 census=git('grep','-n','-E',r'DVD_READ_N\(|DVD_READ\(|DvdReadN\(|DvdRead\(|EmReadSearch\(',PIN,'--','src')
 (out/'request-callsite-census.txt').write_bytes(census)
 checks=[];functions=[]
 def b(f,sig):
  # Ignore forward declarations; a signature must lead to its own opening brace.
  match=re.search(re.escape(sig)+r'[^;{]*\{',src[f]);assert match,(f,sig)
  offset=src[f][:match.start()].count('\n')
  code,start,end=body(src[f][match.start():],sig);functions.append(dict(path=f,signature=sig,start=start+offset,end=end+offset));return code
 def c(name,value):assert value,name;checks.append(dict(name=name,result='PASS',qualification='static source assertion only'))
 dvd='src/game/dvd.cpp';native='port/dreamcast/game/platform/dvd.cpp';read='src/game/read.cpp';audio='port/dreamcast/game/platform/audio_strm.cpp'
 init=b(dvd,'void cDvdQueue::Initialize()');watch=b(dvd,'void cDvd::Watcher()');step=b(dvd,'int cDvdQueue::Read()')
 c('sync request bit wins over ISR bit',init.index('if (w->mode & 0x1)')<init.index('else if (w->mode & 0x100)'))
 c('watcher dispatches native ISR request','if (pQueue_list->chk(0x100) == 1)' in watch and 'iTaskExec(DvdReadProc)' in watch)
 c('request heap index captured at initialization','m_HeapNo = MemGetCurrentHeap();' in init)
 c('each source step owns DVD/nativeIO scope',step.index('re4dc_dvd_step_begin')<step.index('(this->*func_tbl[m_Rno0])();')<step.index('re4dc_dvd_step_end'))
 fileio=b(native,'s32 DVDReadAsyncPrio(')
 c('generic read holds nativeIO through callback',fileio.index('Re4dcIoScope io;')<fileio.index('fs_read(')<fileio.index('callback(result, fi)'))
 c('generic callback happens before function return',fileio.index('callback(result, fi)')<fileio.rindex('return 1;'))
 callback=b(dvd,'void dvdread_callback(')
 c('source DVD callback changes flags only','m_be_flag' in callback and 'memcpy' not in callback and 'Read(' not in callback)
 mainread=b(dvd,'void cDvdQueue::readMain()')
 c('final MRAM transfer uses copied staging payload','(this->*trans_proc_tbl[(*ph)->type])(DVD_BUFF, m_TransAddr, m_DivReadSize);' in mainread)
 c('cancel checked before staging transfer',mainread.index('if (chk(0x100000))')<mainread.index('(this->*trans_proc_tbl'))
 c('resident budget checks span before transfer','re4dc_resident_read_fits((u32) pBuff' in mainread)
 cancelall=b(dvd,'void cDvd::ReadCancelAll()')
 c('cancel all kills worker before clearing slots',cancelall.index('iTaskKill();')<cancelall.index('memclr_asm(DvdQueue'))
 c('platform cancel all has no native read drain',b(native,'s32 DVDCancelAll(void)').strip()=='return 0;')
 oscancel=b('port/dreamcast/game/platform/os.cpp','void OSCancelThread(')
 c('task cancellation waits nativeIO before destruction',oscancel.index('while (thread->nativeIoDepth')<oscancel.index('thd_destroy(thread->kt)'))
 cancel=b(native,'int DVDCancelAsync(')
 c('platform single cancellation callback is synchronous','callback(0, block)' in cancel and cancel.index('callback(0, block)')<cancel.index('return 1;'))
 rearm=b(dvd,'void cDvd::ReadNblk2Blk(')
 c('blocking takeover kills worker then pumps source',rearm.index('iTaskKill();')<rearm.index('readProcMain(q);'))
 block=b(dvd,'void cDvd::blockRead(')
 c('blockread carries source pump borrow through saved slot','Re4dcDvdBorrowScope native_borrow;' in block and 'save->m_Id != save_id' in block and 'save->chk(0x800)' in block)
 area=b(read,'void ReadAreaData()');player=b(read,'void ReadPlayerData(');enemy=b(read,'int readEmData(ReadModule* m, int id, void* addr, u32 size)')
 c('native room allocates via ISR mode8104','0x8104)' in area)
 c('old decode is in branch preceding native DAR','iTaskExec(decodeData);' in area and area.index('iTaskExec(decodeData);')<area.index('Native room containers contain an already-decoded'))
 c('player retires old owner before fixed ISR destination',player.index('ReleasePlData();')<player.index('(void*) PL_DATA_ADDR, 0, 0, 0, 0x8100'))
 c('enemy enables ISR only during room setup','mode = 1;' in enemy and 'if (pG->Rno0 == 2)' in enemy and 'mode = 0x100;' in enemy)
 c('enemy binds metadata only after completion',enemy.index('while ((ret = Dvd.ReadCheckInfo')<enemy.index('re4dc_ui_bind_enemy(pArc, len)'))
 c('REL requested into current heap by mode104','DvdRead(m_RelNo, 0, 0, 0, 0, 0x104' in src['src/game/roomdata.cpp'])
 c('actual enemy list call is sync','readEmList(1);' in src['src/game/stage.cpp'])
 c('datactrl wait cannot hold bit100','u8 wait;' in src['include/datactrl.h'])
 wrapped=b(audio,'s32 __wrap_DVDReadAsyncPrio(')
 c('audio wrapper matches exact stream callback','if (cb != cb_dvd_read_end) return __real_DVDReadAsyncPrio' in wrapped)
 c('matched stream queues completion and never reads destination','pend_push(Pend{ cb, nullptr, fi, length });' in wrapped and 'fs_read' not in wrapped and 'memcpy' not in wrapped)
 c('audio wrap flags apply unconditionally','GAME_LDFLAGS += -Wl,--wrap=DVDReadAsyncPrio -Wl,--wrap=ARQPostRequest' in src['port/dreamcast/game/Makefile'])
 pending=b(audio,'void re4dc_audio_pend_run(void)')
 c('audio pending batch detached before callbacks',pending.index('g_pendN = 0;')<pending.index('run[i].dvd(run[i].res, run[i].obj)'))
 c('source stream rearm waits callback-owned busy','if (str->dvd_busy != 0)' in b('src/game/snd_str1.cpp','void str_abort_wait('))
 receipt=dict(source_commit=PIN,kind='native DVD/ISR destination lifetime source graph',files=manifest,functions=functions,checks=checks,not_established=['No runtime execution/compile/build/stage/guest','No old live archive overlap demonstrated for actual flag100 producer','Native IO protects executing scope/thread stack, not entire queued destination epoch','Audio deferred callback is distinct from generic synchronous service'])
 (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');size=sum(p.stat().st_size for p in out.rglob('*') if p.is_file());assert size<20*1024*1024
 print(json.dumps(dict(result='PASS',checks=len(checks),files=len(manifest),fresh_bytes=size,callsite_lines=len(census.splitlines()))))
if __name__=='__main__':main()
