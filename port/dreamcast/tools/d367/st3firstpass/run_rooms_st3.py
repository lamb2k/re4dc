"""Stage-3 (GC Disc 2 / island) adaptation of Codex's castle worker run_rooms.py
(/root/probe/codex-ps2-castle-a-20261013/run_rooms.py, copied as run_rooms_codex_castle_a.orig.py).

Changes vs Codex (recorded for the report):
  1. ROOT/TREE = this lane (/root/probe/lanes-20261014/st3, tools worktree @ 8bf46efe); ROOMS from argv.
  2. Lighting pin extended to Disc 2: the GC source is the 2004.11.25 review Disc 2 .gcm (header G4BE08, disc
     number 1, same magic), pinned by size + sha256 in worlds.json 'gc_source_disc2'. The pinned Disc 1 check
     (build_ps2_assets.check_gc) is replaced by check_gc_disc2 with the same method (header + record() == pin).
     gc_room_lit.py is unchanged; it already reads any GcIso via --iso.
  3. Flags: GC_disc2_offline_lighting_calibration instead of the Disc 1 one.
Everything else (build(), qualification(), hand-back JSON layout) is Codex's code unchanged.
usage: python run_rooms_st3.py r300 r301 ...
"""
import contextlib, copy, hashlib, importlib.metadata, importlib.util, json, os, struct, sys, tempfile, time, traceback
from pathlib import Path
ROOT=Path('/root/probe/lanes-20261014/st3')
TREE=ROOT/'tools'
sys.path.insert(0,str(TREE/'port/dreamcast/tools'))
import build_ps2_assets as b
from ps2_assets import scenario, tpl
import ps2_room_ids
ROOMS=sys.argv[1:]
legacy_path=Path('/mnt/c/Game Dev/Emulators/re4-assets-private/world-agent-20260926/from-main/ps2-trees/tools/ps2_tpl_decode.py')
spec=importlib.util.spec_from_file_location('legacy_tpl',legacy_path)
legacy=importlib.util.module_from_spec(spec); spec.loader.exec_module(legacy)
EVID=ROOT/'evidence'; EVID.mkdir(exist_ok=True)
GC2=Path('/root/work/re4-dreamcast/orig/G4BE08/re4_review_disc2.gcm')
profile=json.loads(b.PROFILE.read_text())
profile['rooms'] += [r for r in ROOMS if r not in profile['rooms']]
if 'gc_source_disc2' not in profile:
    profile['gc_source_disc2']=b.record(GC2.resolve())
b.PROFILE.write_text(json.dumps(profile,indent=2)+'\n')
(EVID/'candidate-profile.json').write_text(json.dumps(profile,indent=2)+'\n')

def check_gc_disc2(path,pin):
    b.require(path.is_file(),'GC Disc 2 image missing (lighting calibration)')
    with path.open('rb') as f: header=f.read(32)
    b.require(header[:6]==b'G4BE08' and header[6]==1 and header[7]==0 and header[28:32]==b'\xc2\x33\x9f\x3d','not G4BE08 GameCube Disc 2')
    result=b.record(path)
    b.require(result==pin,'GC Disc 2 hash differs from the pinned lighting source')
    return dict(path=str(path),**result)

def save(path, value):
    path.write_text(json.dumps(value,indent=2)+'\n')

def qualification(room,out):
    inp=out/'inputs'/room; result=out/'rooms'/room
    obj=scenario.read_obj(inp/(room+'_004.scenario.obj'))
    smd=scenario.ps2_smd_lines(inp/(room+'_004.SMD'))
    mats=scenario.read_idxmaterial(inp/(room+'_004.scenario.idxmaterial'))
    mtl=scenario.read_mtl(inp/(room+'_004.scenario.mtl'))
    rep=json.loads((result/'ps2-world.json').read_text())
    blob=(inp/(room+'_004.TPL')).read_bytes(); parsed=tpl.parse_tpl(blob)
    source_ids=ps2_room_ids.group_ids(inp/(room+'_004.scenario.obj'))
    _,fields=ps2_room_ids.r4pw(result/'ps2-world.r4pw')
    checks={'smd_rows':len(smd),'obj_groups':len(obj['groups']),'obj_faces':sum(len(g['faces']) for g in obj['groups']),
            'source_ids':source_ids,'placement_fields':fields,'material_count':len(mats),'tpl_base_images':parsed['count']}
    b.require(len(smd)==len(obj['groups'])==rep['groups']==rep['placements'],'source SMD/OBJ/placement count differs')
    b.require(fields==list(range(len(obj['groups']))),'source placement sequence missing or reordered')
    b.require(checks['obj_faces']==rep['source_triangles'],'source triangle count differs')
    ids=(result/'ps2-world.ids').read_bytes()
    b.require(list(ids[16:16+len(source_ids)])==[min(i,255) for i in source_ids],'source IDs differ')
    refs=set()
    for i,g in enumerate(obj['groups']):
        b.require(g['smd']==i and g['smx']==smd[i]['smx'] and g['bin']==smd[i]['bin'],'source group identity differs')
        for face,name in g['faces']:
            b.require(name in mats and name in mtl,'missing source material')
            tid=int(mats[name]['diffuse_map']); refs.add(tid)
            b.require(tid==mtl[name]['tex'] and 0<=tid<parsed['count'],'source texture reference differs')
    checks['referenced_source_textures']=sorted(refs)
    levels=[]
    for i,h in enumerate(parsed['entries']):
        for j,hh in enumerate([h]+h['mips']):
            w,ht,rgba,_=tpl.decode(blob,hh,'jl')
            _,_,jl,_=legacy.decode(blob,hh,'jl')
            _,_,gs,_=legacy.decode(blob,hh,'gs')
            b.require(rgba==jl==gs,f'TPL decoder disagreement entry={i} mip={j}')
            levels.append(dict(entry=i,mip=j,width=w,height=ht,rgba_sha256=hashlib.sha256(rgba).hexdigest(),bitdepth=hh['bitdepth'],interlace=hh['interlace']))
    checks['all_source_images_mips_gs_jl_equal']=True
    checks['decoder_levels']=levels
    checks['legacy_decoder']=dict(path=str(legacy_path),sha256=b.sha(legacy_path))
    return checks

print('PREFLIGHT_START',flush=True)
start=time.monotonic()
toolchain=b.host_tools()
versions={n:importlib.metadata.version(n) for n in profile['python_packages']}
b.require(versions==profile['python_packages'],'pinned package versions mismatch')
ps2=Path('/mnt/c/Users/Public/ps2/DVD/Resident Evil 4 (USA).iso')
sources=dict(ps2=b.check_ps2(ps2,profile['source']),gc=check_gc_disc2(GC2.resolve(),profile['gc_source_disc2']))
fingerprint=dict(sources={k:v['sha256'] for k,v in sources.items()},scripts=b.source_hashes(),packages=versions,rooms=[],platform=sys.platform,python=sys.version,recipe=profile,host_tools=toolchain)
status=json.loads((EVID/'status.json').read_text()) if (EVID/'status.json').exists() else {}
with tempfile.TemporaryDirectory(prefix='re4dc-st3-check-') as scratch:
    checker=b.runtime_checker(Path(scratch))
    preflight=dict(seconds=round(time.monotonic()-start,3),sources=sources,fingerprint=fingerprint,checker=b.record(checker),runner=b.record(Path(__file__)))
    save(EVID/'preflight.json',preflight)
    print('PREFLIGHT_OK '+str(preflight['seconds']),flush=True)
    for room in ROOMS:
        started=time.monotonic(); out=TREE/'.assets'/('rooms-'+room)
        log=EVID/(room+'-build.log')
        print('ROOM_START '+room,flush=True)
        try:
            fp=copy.deepcopy(fingerprint); fp['rooms']=[room]
            args=type('Args',(),dict(out=out,tools=TREE/'.assets/tools'))()
            with log.open('w') as handle,contextlib.redirect_stdout(handle),contextlib.redirect_stderr(handle):
                b.build(args,profile,sources,fp,checker)
                qualified=qualification(room,out)
            manifest=json.loads((out/'manifest.json').read_text())
            result=out/'rooms'/room
            packages={p.name:b.record(p) for p in b.runtime_files(result) if p.suffix!='.re4tex'}
            textures={p.name:b.record(p) for p in b.runtime_files(result) if p.suffix=='.re4tex'}
            report=dict(room=room,status='ready',out=str(out),runtime_dir=str(result),manifest_path=str(out/'manifest.json'),
                        packages=packages,textures=textures,sources=sources,source_hashes=fp['scripts'],qualification=qualified,
                        validation=manifest['rooms'][room]['validation'],elapsed_seconds=round(time.monotonic()-started,3),
                        flags=['candidate_asset_only','PS2_geometry_and_textures','GC_disc2_offline_lighting_calibration','no_retained_baseline_for_new_room',
                               'world_only_heap_and_unique_texture_payload_not_whole_heap4_or_VRAM_headroom','current_conversion_texture_bytes_no_extra_VQ',
                               'packed_keys_win_use_exact_provided_bytes','integration_visual_STRICT_texchk_memory_and_Flycast_gates_owned_by_Claude'])
            save(EVID/(room+'-handback.json'),report)
            status[room]={'status':'ready','handback':str(EVID/(room+'-handback.json'))}
            print('ROOM_READY '+json.dumps({k:report[k] for k in ('room','validation','elapsed_seconds')}),flush=True)
        except (Exception,SystemExit) as exc:
            failure=dict(room=room,status='blocked',exception=repr(exc),traceback=traceback.format_exc(),out=str(out),log=str(log),elapsed_seconds=round(time.monotonic()-started,3))
            save(EVID/(room+'-failure.json'),failure)
            status[room]={'status':'blocked','failure':str(EVID/(room+'-failure.json'))}
            print('ROOM_BLOCKED '+json.dumps({k:failure[k] for k in ('room','exception')}),flush=True)
        save(EVID/'status.json',status)
print('ALL_DONE '+json.dumps(status),flush=True)
