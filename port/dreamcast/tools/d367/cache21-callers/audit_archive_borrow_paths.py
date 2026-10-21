#!/usr/bin/env python3
"""Pin an immutable source inventory; assertions are static contracts, not runtime tests."""
import argparse, hashlib, json, pathlib, subprocess

PIN = '836a72425d4f753a7b0ef0f3509716621942b461'
FILES = [
 'src/game/event.cpp', 'src/game/emdata.cpp', 'src/game/eff_sys.cpp',
 'src/game/espgen.cpp', 'src/game/espgen00.cpp', 'src/game/game.cpp',
 'src/game/dvd.cpp', 'src/game/scheduler.cpp',
 'port/dreamcast/game/actor_lifetime.inc', 'port/dreamcast/game/model_bridge.cpp',
 'port/dreamcast/game/ui_bridge.cpp',
 'port/dreamcast/game/platform/native_effect.cpp',
 'port/dreamcast/game/platform/native_ui.cpp',
 'port/dreamcast/game/platform/native_model.cpp',
 'port/dreamcast/game/platform/native_draw_plan_owner.cpp',
 'port/dreamcast/game/platform/native_event_file.cpp',
 'port/dreamcast/game/platform/native_movie.cpp',
 'port/dreamcast/game/platform/os.cpp', 'port/dreamcast/game/platform/dvd.cpp',
 'port/dreamcast/game/platform/audio_stub.cpp', 'port/dreamcast/game/platform/mem.cpp',
 'port/dreamcast/game/platform/include/native_io.h',
 'port/dreamcast/room/texture_package.hpp', 'port/dreamcast/room/texture_package.cpp',
 'port/dreamcast/room/room_storage.cpp',
]

def main():
 p=argparse.ArgumentParser(); p.add_argument('--repo',required=True);p.add_argument('--out',required=True);a=p.parse_args()
 out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=False)
 def git(*args):return subprocess.check_output(['git','-C',a.repo,*args])
 src={};manifest=[]
 for name in FILES:
  raw=git('show',PIN+':'+name);src[name]=raw.decode();target=out/'source'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
  manifest.append(dict(path=name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),blob=git('rev-parse',PIN+':'+name).decode().strip()))
 checks=[]
 def check(name,condition):
  assert condition,name
  checks.append(dict(name=name,result='PASS',qualification='static source ordering/presence only'))
 def s(suffix):return next(text for name,text in src.items() if name.endswith(suffix))
 def between(text,start,end):return text.split(start,1)[1].split(end,1)[0]
 effect=s('native_effect.cpp')
 rawread=between(effect,'extern "C" void* re4dc_effect_record_read','extern "C" void re4dc_effect_get_stats')
 check('raw-even-reference returned before binding validation',rawread.index('return reference')<rawread.index('for(const auto& b:bindings)'))
 check('compact reference must match live archive before decode',rawread.index('for(const auto& b:bindings)')<rawread.index('decode('))
 check('compact refusal uses fatal diagnostic', 'fail("effect record outside live qualified archive")' in rawread)
 check('effect unbind clears descriptor, not controller scan','b={};return;' in between(effect,'extern "C" void re4dc_effect_unbind','extern "C" void re4dc_effect_retire_room'))
 tex=s('texture_package.cpp');adopt=between(tex,'bool SourceIdentityTable::adopt','\n#ifndef RE4DC_TEX_RESIDENT')
 check('identity adoption stores direct archive/table pointers','data_=data;bytes_=bytes;table_=native+32;count_=count;' in adopt)
 check('identity record rereads table and backing', 'word(table_+12*index)' in tex and 'const auto* p=data_+start;' in tex)
 check('identity clear releases only metadata','data_ = nullptr; table_ = nullptr; count_ = 0; bytes_ = 0;' in s('texture_package.hpp'))
 ui=s('native_ui.cpp');reserve=between(ui,'extern "C" int re4dc_model_packet_reserve','extern "C" void re4dc_model_packet_commit')
 check('model reserve abort check precedes stream selection',reserve.index('if(stream_aborted)return 0;')<reserve.index('stream_select(list);'))
 after=reserve.split('stream_select(list);',1)[1]
 check('no generic abort recheck after stream selection','stream_aborted' not in after)
 check('successful reserve publishes packet destination after stream selection',after.index('out->vertices=')<after.rindex('return 1;'))
 opening=between(ui,'void stream_open()','void stream_select(pvr_list_t list)')
 check('stream opening can wait for presenter/TA','present_fence();' in opening and 'pvr_scene_begin();' in opening and 'pvr_list_begin(' in opening)
 retirement=between(ui,'extern "C" void re4dc_ui_retire_room()','\n}',)
 check('room retirement resets deferred views','reset_deferred();' in retirement)
 check('room retirement aborts unfinished stream','if(stream_scene){stream_aborted=true;stream_retire=true;}' in retirement)
 check('room retirement clears direct identity views','room_identities.clear()' in retirement and 'e.table.clear();e.archive=nullptr;' in retirement)
 model=s('native_model.cpp');submit=model[model.index('// Source data remains live throughout this synchronous call.'):]
 check('packet reservation precedes source walk',submit.index('re4dc_model_packet_reserve')<submit.index('b.walk(false)'))
 plans=s('native_draw_plan_owner.cpp')
 check('draw-plan reset defers own arena while leased','if(leases) reset_pending=true; else reset_now();' in plans)
 check('owner unbind clears owners despite pending plan lease','re4dc_model_reset_draw_plans();\n    for(auto& o:owners) if(o.key==key) o={};' in plans)
 check('actor archive metadata explicitly borrowed','Metadata borrows real source allocations' in s('actor_lifetime.inc'))
 check('actor archive retirement revokes metadata','if(archives[k].key==key)revoke(k);' in s('actor_lifetime.inc'))
 io=s('native_io.h');os=s('/os.cpp')
 check('native IO is per source-thread counter','nativeIoDepth' in os and 're4dc_io_begin' in io)
 check('ISR skips parking native IO owner','if (re4dc_io_busy(&t->Thread)) return;' in s('scheduler.cpp'))
 native_dvd=src['port/dreamcast/game/platform/dvd.cpp']
 check('DVD nominal async entry performs synchronous host read','DVDReadAsyncPrio' in native_dvd and 'fs_read(' in native_dvd)
 check('storage mutex guards bounce buffer only','mutex_trylock(&reader_mutex)' in s('room_storage.cpp') and 'bounce_busy' in s('room_storage.cpp'))
 cabin=s('native_event_file.cpp')
 check('CABIN DMA readers have exact request/generation decrement','--c.readers;d=CabinCarrierDma{};' in cabin)
 check('CABIN event and DMA counters are distinct','carrier_event_readers,carrier_dma_scope' in cabin)
 missing=s('/mem.cpp');body=between(missing,'void re4dc_missing(', '\n}')
 check('current missing diagnostic loops without returning','for (;;)' in body and 'thd_sleep(1000)' in body)
 receipt=dict(source_commit=PIN,source_tree=git('rev-parse',PIN+'^{tree}').decode().strip(),kind='read-only exact-source inventory/static assertions',checks=checks,files=manifest,not_established=['No compile/link/guest executed','No gameplay UAF or normal interleaving demonstrated','No whole archive/reset lease or acceptance claim'])
 (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
 total=sum(x.stat().st_size for x in out.rglob('*') if x.is_file());assert total<=20*1024*1024,total
 print(json.dumps(dict(source_commit=PIN,checks=len(checks),files=len(manifest),fresh_bytes=total,result='PASS')))
if __name__=='__main__':main()
