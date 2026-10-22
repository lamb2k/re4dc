#!/usr/bin/env python3
"""Exact source trace only; no compilation, runtime mutation or UBSan rerun."""
import argparse,hashlib,json,pathlib,re,subprocess,sys
sys.dont_write_bytecode=True
from audit_archive_borrow_boundaries import body
PIN='720b75381a68f51636b17031f82fd762e72e05d3'
FILES=['include/cManager.h','include/em.h','include/em10.h','include/model.h','include/event.h','include/atari.h',
 'port/dreamcast/game/parts_bridge.cpp','src/game/em.cpp','src/game/em_set.cpp','src/game/event.cpp',
 'src/game/objRocket.cpp','src/game/read.cpp','src/game/game.cpp','src/game/scheduler.cpp','src/game/sce_sys.cpp',
 'src/st/em_wrap.cpp','include/em_wrap.h','src/st1/r10c.cpp','src/em12/em12_set.cpp','src/em10/em10.cpp',
 'docs/CACHE21_MAIN_AUDIT_REVIEW_20261021_1959.json']

def native_branches(text):
 # The manager has alternative if-openings around #else. Mask only known
 # __PPC__ alternatives, preserving all offsets/lines; this is not compilation.
 stack=[];out=[]
 for line in text.splitlines(keepends=True):
  directive=line.strip()
  if directive.startswith(('#if ', '#ifdef ', '#ifndef ')):
   known=True if directive=='#if !defined(__PPC__)' else False if directive=='#if defined(__PPC__)' else None
   stack.append(known)
  elif directive.startswith('#else') and stack:
   if stack[-1] is not None:stack[-1]=not stack[-1]
  elif directive.startswith('#endif') and stack:stack.pop()
  if False in stack and not directive.startswith('#'):line=''.join('\n' if x=='\n' else ' ' for x in line)
  out.append(line)
 return ''.join(out)

def main():
 p=argparse.ArgumentParser();p.add_argument('--repo',required=True);p.add_argument('--out',required=True);a=p.parse_args();out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=False)
 src={};files=[];trace=[];checks=[]
 def git(*args):return subprocess.check_output(['git','-C',a.repo,*args])
 for f in FILES:
  raw=git('show',PIN+':'+f);src[f]=raw.decode();files.append(dict(path=f,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),blob=git('rev-parse',PIN+':'+f).decode().strip()))
 def extract(f,sig):
  text=native_branches(src[f]);match=re.search(re.escape(sig)+r'[^;{]*\{',text);assert match,(f,sig)
  offset=text[:match.start()].count('\n');code,start,end=body(text[match.start():],sig)
  trace.append(dict(path=f,signature=sig,line=start+offset,end=end+offset,source_body_native_PPC_alternatives_masked=code));return code
 def c(name,value):assert value,name;checks.append(dict(name=name,result='PASS',kind='static source condition only'))
 mgr='include/cManager.h';pool='port/dreamcast/game/parts_bridge.cpp';em='src/game/em.cpp'
 die=extract(mgr,'int cManager<T>::dieCheck()');create=extract(mgr,'T* cManager<T>::create(int id)');indexed=extract(mgr,'T* cManager<T>::create(int id, u32 no)');back=extract(mgr,'T* cManager<T>::createBack(int id)');destroy=extract(mgr,'inline void cManager<T>::destroy(T* p)');count=extract(mgr,'u32 cManager<T>::countActiveWork()')
 c('deferred destroy uses typed post-destructor flag store','delete p;\n                p->be_flag = 0;' in die)
 c('immediate destroy uses typed post-destructor flag store','delete p;\n        p->be_flag = 0;' in destroy)
 c('fresh/reused scan occurs before construction',create.index('p->be_flag')<create.index('memClear(p, size)')<create.index('construct(p, id)'))
 c('back allocator also scans before construction',back.index('p->be_flag')<back.index('construct(p, id)'))
 c('indexed create scans before construction',indexed.index('p->be_flag')<indexed.index('construct(p, id)'))
 c('indexed overload ignores construct refusal','if (construct' not in indexed and 'construct(p, id);' in indexed)
 c('count scan includes raw/reused flags','p->be_flag & 0x601' in count)
 c('deferred stages remain two-step','p->be_flag & 0x400' in die and 'p->be_flag |= 0x400;' in die and 'p->be_flag |= 0x200;' in destroy)
 c('pool operator delete is intentionally empty','void operator delete(void*, unsigned int) {}' in src[mgr])
 c('base destructor clears601 before storage retained','virtual ~cUnit() { be_flag &= ~0x601; }' in src[mgr])
 alloc=extract(pool,'template<class T> int array_alloc(');prepare=extract(pool,'template<class T> bool prepare_work(');free=extract(pool,'template<class T> int array_free(');alive=extract(pool,'template<class T> bool alive(');discard=extract(pool,'template<class T> void discard(')
 c('pool headers and physical runs start as byte-cleared storage','memclr_asm(p,bytes)' in alloc and 'memclr_asm(c,bytes)' in prepare)
 c('pool chunks reclaim test typed flags without constructor proof','c->parts()[i].be_flag & 0x601' in alive)
 c('enemy and object slot addresses retained','retain_slots<cObj> = true' in src[pool] and 'retain_slots<cEm> = true' in src[pool])
 c('ordinary sparse teardown frees backing using captured heap handle','while(p->chunks) discard(p,&p->chunks)' in free and 'OSFreeToHeap(p->handle,p)' in free and 'OSFreeToHeap(p->handle,c)' in discard)
 ctor=extract(em,'int cEmMgr::construct(');move=extract(em,'void cEmMgr::move()');emdestroy=extract(em,'void cEmMgr::destroy(')
 c('enemy constructor prewrites subArc before placement constructor',ctor.index('p->subArc = (PlArc*)EmReadSearch')<ctor.index('EmInitFunc(p);'))
 c('enemy creation serial assigned after constructor',ctor.index('EmInitFunc(p);')<ctor.index('p->serial = Guid;'))
 c('enemy manager deferred policy is2','cEmMgr::cEmMgr() : cManager<cEm>(sizeof(cEm), 2)' in src[em])
 c('enemy manager cleanup precedes deferred mark',emdestroy.index('p->push();')<emdestroy.index('cManager<cEm>::destroy(p);'))
 c('enemy move checks deferred deletion before active traversal',move.index('dieCheck();')<move.index('p = pAlive;'))
 set2=extract('src/game/em_set.cpp','cEm* EmSetFromList2(')
 c('first enemy move occurs before returning handle',set2.index('em->move();')<set2.rindex('return em;'))
 init=extract('src/st1/r10c.cpp','void R10cInit()');event=extract('src/st1/r10c.cpp','static void r10c_EmEvent()')
 c('r10c preloads12 before event registration',init.index('EmReadSearch(0x12, 0, 0);')<init.index('r10c_EmEvent'))
 c('r10c first virtual follows list creation without explicit sleep',event.index('EmSetFromList2(2, 1);')<event.index('em->setNoSuspend(1);') and 'Sleep' not in event[:event.index('em->setNoSuspend(1);')])
 search=extract('src/game/read.cpp','void* EmReadSearch(int id, void* addr, u32 size)');load=extract('src/game/read.cpp','int readEmData(ReadModule* m, int id, void* addr, u32 size)')
 c('existing enemy module returns without read caller',search.index('return m->pArc;')<search.index('return readEm('))
 c('missing enemy load can yield before module publication','TaskSleep(1);' in load and load.index('TaskSleep(1);')<load.index('m->pArc = pArc;'))
 wrap=extract('src/st/em_wrap.cpp','static int emWrapLive(')
 c('raw wrapper checks flag but no serial or current-pool receipt','w->pEm->be_flag' in wrap and 'serial' not in wrap and 'EmMgr' not in wrap)
 c('native em12 default initialization preserves prewritten bytes','new (em) cEm10;' in src['src/em12/em12_set.cpp'])
 c('custom SAT alive predicate must not be flattened','(m_Flag & 4)' in src['include/atari.h'])
 c('ordinary scenario loop dispatches EventMgr scans','EvtMgr.Run();' in extract('src/game/sce_sys.cpp','void ScenarioMove()'))
 trace.append(dict(path='src/em10/em10.cpp',line=2716,qualification='move marks destroy onr_no_0FF; deferred policy2 above applies',source_lines='\n'.join(src['src/em10/em10.cpp'].splitlines()[2713:2722])))
 result=dict(kind='manager storage/object lifetime exact source trace, not target bug proof',source_commit=PIN,files=files,checks=checks,trace=trace,limits=['No compiler/runtime/build/guest','No new normal ABA or issue52 crash trigger established','Raw byte metadata repair still requires current live allocation and constructor-phase proof','No whole archive/reset closure; no manager layout/default change proposed'])
 (out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');size=sum(p.stat().st_size for p in out.rglob('*') if p.is_file());assert size<2*1024*1024
 print(json.dumps(dict(result='PASS',checks=len(checks),source_objects=len(files),fresh_bytes=size)))
if __name__=='__main__':main()
