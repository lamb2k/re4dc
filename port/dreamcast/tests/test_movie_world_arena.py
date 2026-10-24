#!/usr/bin/env python3
"""Compile actual production helpers with deterministic host device adapters.
No Dreamcast media, SDK changes, or game execution. Temporary products stay out
of the checkout. The extraction hash binds exactly what this test exercised.
"""
from pathlib import Path
import argparse,hashlib,json,re,subprocess,tempfile
G=Path(__file__).resolve().parents[1]/'game'

def function(path,signature):
    text=(G/path).read_text()
    # The cabin integration gives this unchanged body a different name when
    # CABIN_SOURCE=1. This suite exercises MOVIE_WORLD_ARENA with CABIN_SOURCE=0.
    conditional='#if RE4DC_CABIN_SOURCE\nstatic int movie_cabin_ui_try_close_body(){\n#else\nextern "C" int re4dc_ui_movie_try_close(){\n#endif'
    if path=='platform/native_ui.cpp':
        assert text.count(conditional)==1
        text=text.replace(conditional,'extern "C" int re4dc_ui_movie_try_close(){')
    start=text.index(signature);brace=text.index('{',start)
    while ';' in text[start:brace]:
        start=text.index(signature,start+len(signature));brace=text.index('{',start)
    # Ignore braces in literals/comments, while retaining the exact source span.
    token=re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|//[^\n]*|/\*[\s\S]*?\*/|[{}]')
    depth=0
    for match in token.finditer(text,brace):
        if match.group()=='{':depth+=1
        elif match.group()=='}':
            depth-=1
            if not depth:return text[start:match.end()]+'\n'
    raise AssertionError(signature)

def extract():
    groups=[('ui_bridge.cpp',[
        'extern "C" int re4dc_room4_live_generation(',
        'extern "C" int re4dc_room4_cell_valid(']),
      ('platform/native_ui.cpp',['extern "C" int re4dc_ui_movie_try_close(', 'extern "C" int re4dc_ui_movie_handoff_ready(']),
      ('platform/native_static.cpp',[
        'bool ps2_movie_layout(',
        'bool ps2_movie_blocked(', 'bool ps2_movie_current(', 'void ps2_movie_unpublish(',
        'std::uint32_t ps2_crc32(', 'bool ps2_movie_reload(', 'bool ps2_movie_dyn_valid(',
        'extern "C" int re4dc_ps2_mesh_movie_blocked(',
        'extern "C" unsigned re4dc_ps2_mesh_movie_borrow(',
        'extern "C" int re4dc_ps2_mesh_movie_valid(',
        'extern "C" void* re4dc_ps2_mesh_movie_alloc(',
        'extern "C" int re4dc_ps2_mesh_movie_free(',
        'extern "C" int re4dc_ps2_mesh_movie_return(',
        'extern "C" void re4dc_ps2_mesh_retire(',
        'extern "C" int re4dc_movie_world_before_heap_change('])]
    parts=[];pins={}
    for path,signatures in groups:
        pins[path]=hashlib.sha256((G/path).read_bytes()).hexdigest()
        for signature in signatures:parts.append(function(path,signature))
    # The service's actual private allocation adapters use the same ledger.
    for signature in ['static void* re4dc_movie_sep_alloc(', 'static void re4dc_movie_sep_free(']:
        parts.append(function('platform/native_movie_stream.c',signature))
    pins['platform/native_movie_stream.c']=hashlib.sha256((G/'platform/native_movie_stream.c').read_bytes()).hexdigest()
    pins['platform/include/movie_world_arena_lifecycle.inc']=hashlib.sha256((G/'platform/include/movie_world_arena_lifecycle.inc').read_bytes()).hexdigest()
    return '\n'.join(parts),pins

def extract_dynamic_types():
    # Use the production layouts so ROOT_POSE's Slot extension is exercised.
    return '\n'.join(function('platform/native_static.cpp',signature).rstrip()+';'
                     for signature in ['struct PartPose {','struct Slot {'])+'\n'+function('platform/native_static.cpp','constexpr unsigned part_cell_bytes(')

def extract_player():
    path='platform/native_movie.cpp'
    parts=[function(path,'struct Movie {').rstrip()+' m;\n']
    parts.append('unsigned movie_world_token=0,movie_scope=0,movie_epoch=1,movie_readers=0;\nbool movie_full_call=false,movie_retiring=false,movie_finishing=false;\n')
    parts.append(function(path,'struct MovieFinishScope {').rstrip()+';\n')
    for signature in ['bool movie_world_id(', 'extern "C" void re4dc_movie_world_scope(',
                      'bool movie_world_current(', 'void movie_stage_free(', 'int finish(',
                      'extern "C" int re4dc_movie_end(', 'extern "C" int re4dc_movie_cancel(',
                      'extern "C" int re4dc_movie_world_before_room_retire(']:
        parts.append(function(path,signature))
    return '\n'.join(parts)

def extract_heap():
    return '\n'.join(function('../../../src/game/main_mem.cpp',sig) for sig in [
        'int MemDestroyHeap(', 'int MemCreateHeap(', 'int MemReplaceHeap(', 'void MemClearAllHeap('])

def contracts():
    s=(G/'platform/native_static.cpp').read_text()
    assert function('platform/native_static.cpp','bool ps2_open(').index('ps2_movie_blocked()')<function('platform/native_static.cpp','bool ps2_open(').index('ps2_free()')
    for name in ['re4dc_ps2_mesh_camera','re4dc_ps2_mesh_draw','re4dc_ps2_mesh_preload','re4dc_ps2_mesh_source','re4dc_ps2_mesh_texture','re4dc_ps2_mesh_select','re4dc_ps2_mesh_failed']:
        match=re.search(r'extern "C" [^\n]*\b'+name+r'\(',s);assert match,name
        body=function('platform/native_static.cpp',match.group())
        assert body.index('ps2_movie_blocked()')<body.index('#endif'),name
    for name in ['re4dc_ps2_world_draw','re4dc_ps2_world_source_draw','re4dc_ps2_world_pending','re4dc_ps2_world_flush']:
        text=(G/'platform/native_ps2_world.cpp').read_text();match=re.search(r'extern "C" [^\n]*\b'+name+r'\(',text);assert match,name
        body=function('platform/native_ps2_world.cpp',match.group());assert body.index('re4dc_ps2_mesh_movie_blocked()')<body.index('using namespace'),name
    leave=function('ui_bridge.cpp','extern "C" void re4dc_room_leave(')
    assert leave.index('re4dc_movie_world_before_room_retire()')<leave.index('re4dc_motion_retire_all()')<leave.index('re4dc_room4_close()')
    reload=function('platform/native_static.cpp','bool ps2_movie_reload(')
    for forbidden in ['dyn::reset','re4dc_static_alloc','re4dc_static_free','SmdSet','StageSet','RouteMoviePlay']:
        assert forbidden not in reload,forbidden
    assert 'MovieWorldRead read' in reload and 'Re4dcIoScope io' in reload
    assert all(x in reload for x in ['files.mesh_crc','files.mesh_fnv','files.side_crc','files.side_fnv','package.adopt'])
    destroy=function('../../../src/game/main_mem.cpp','int MemDestroyHeap(')
    replace=function('../../../src/game/main_mem.cpp','int MemReplaceHeap(')
    clear=function('../../../src/game/main_mem.cpp','void MemClearAllHeap(')
    assert destroy.index('re4dc_movie_world_before_heap_change')<destroy.index('OSDestroyHeap')
    assert replace.index('re4dc_movie_world_before_heap_change')<replace.index('return MemCreateHeap')
    assert clear.index('re4dc_movie_world_before_heap_change')<clear.index('MemDestroyHeap(i)')
    retire=function('platform/native_ui.cpp','extern "C" void re4dc_ui_retire_room(')
    assert retire.index('re4dc_movie_world_before_room_retire')<retire.index('re4dc_actor_archive_retire_transient')
    close=function('platform/native_ui.cpp','extern "C" int re4dc_ui_movie_try_close(')
    assert all(x not in close for x in ['present_fence','quiesce','wait_clear','thd_sleep'])
    alloc=function('platform/native_movie.cpp','void* stage_alloc(')
    assert alloc.index('if(movie_world_token)return')<alloc.index('re4dc_ui_stage_alloc')
    until=function('platform/native_movie.cpp','extern "C" int re4dc_movie_play_until(')
    assert 'MovieReader reader;st=start(id,mask)' in until and 'MovieReader reader;st=iterate(tick,false)' in until
    alloc=function('platform/native_static.cpp','extern "C" void re4dc_ps2_dyn_parts(')
    valid=function('platform/native_static.cpp','bool ps2_movie_dyn_valid(')
    assert 'part_cell_bytes(count)' in alloc and 're4dc_static_alloc(part_bytes)' in alloc
    assert 'part_cell_bytes(dyn::slots[i].nparts)' in valid
    return 27

def main():
    a=argparse.ArgumentParser();a.add_argument('--output');a.add_argument('--root-pose',choices=['0','1','both'],default='both');args=a.parse_args()
    source,pins=extract();dynamic=extract_dynamic_types();player=extract_player();heap=extract_heap();checks=contracts()
    pins['../../../src/game/main_mem.cpp']=hashlib.sha256((G/'../../../src/game/main_mem.cpp').read_bytes()).hexdigest()
    pins['platform/native_movie.cpp']=hashlib.sha256((G/'platform/native_movie.cpp').read_bytes()).hexdigest()
    with tempfile.TemporaryDirectory(prefix='re4dc-movie-world-')as temp:
        out=Path(temp);(out/'production_dynamic_types.inc').write_text(dynamic);(out/'production_helpers.inc').write_text(source);(out/'production_player.inc').write_text(player);(out/'production_heap.inc').write_text(heap)
        exe=out/'test';cmd=['g++','-std=c++20','-O1','-g','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-fsanitize=undefined','-fno-sanitize-recover=all','-I'+str(out),'-I'+str(G/'platform/include'),str(Path(__file__).with_name('movie_world_arena_test.cpp')),'-o',str(exe)]
        arms=[]
        for mode in (['0','1'] if args.root_pose=='both' else [args.root_pose]):
            actual=cmd[:1]+['-DRE4DC_PS2_WORLD_ROOT_POSE='+mode]+cmd[1:]
            subprocess.run(actual,check=True)
            result=subprocess.run([str(exe)],text=True,capture_output=True)
            print('ROOT_POSE='+mode+': '+result.stdout+result.stderr,flush=True)
            result.check_returncode()
            arms.append(dict(root_pose=int(mode),compiler_argv=actual,stdout=result.stdout,stderr=result.stderr))
    report={'status':'PASS','production_source_pins':pins,'extracted_helpers_sha256':hashlib.sha256(source.encode()).hexdigest(),'extracted_player_sha256':hashlib.sha256(player.encode()).hexdigest(),'extracted_heap_sha256':hashlib.sha256(heap.encode()).hexdigest(),'source_contract_checks':checks,'dynamic_types_sha256':hashlib.sha256(dynamic.encode()).hexdigest(),'arms':arms,'limits':'Host device/filesystem/package-validator adapters; no linked target or game execution.'}
    if args.output:Path(args.output).write_text(json.dumps(report,indent=2)+'\n')
    print(result.stdout,end='');print('source integration contracts:',checks)
if __name__=='__main__':main()
