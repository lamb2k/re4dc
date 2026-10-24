#!/usr/bin/env python3
"""Read explicit SDO3 captures and pins; report observations, never a gate verdict.

No build, staging, emulator, image editing or screenshot comparison is executed.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re


def hostpath(value):
    value=str(value)
    if os.name=='nt':
        if value.startswith('/mnt/c/'):return Path('C:/'+value[7:])
        if value.startswith('/root/'):return Path('//wsl.localhost/Ubuntu-24.04'+value)
    else:
        if re.match(r'^[Cc]:[\\/]',value):return Path('/mnt/c/'+value[3:].replace('\\','/'))
        prefix='//wsl.localhost/Ubuntu-24.04'
        normalized=value.replace('\\','/')
        if normalized.startswith(prefix+'/'):return Path(normalized[len(prefix):])
    return Path(value)


def pin(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return dict(path=str(path),bytes=Path(path).stat().st_size,sha256=h.hexdigest())


def text_bytes(raw):
    return raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig',errors='replace').replace('\0','')


def fields(line):
    result={}
    for key,value in re.findall(r'\b([A-Za-z_][A-Za-z_0-9]*)=([^\s]+)',line):
        result[key]=int(value) if re.fullmatch(r'-?\d+',value) and key not in ('room','r','id','source_crc','actual_crc') else value
    return result


def rows(lines,pattern):
    return [dict(line=n,raw=line,fields=fields(line)) for n,line in enumerate(lines,1) if re.search(pattern,line,re.I)]


def numeric_max(records,key):
    values=[r['fields'][key] for r in records if isinstance(r['fields'].get(key),int)]
    return max(values) if values else None


def diagnostic(knobs,names,records,trusted):
    flags={name:knobs.get(name,'ABSENT') for name in names}
    if not trusted:state='UNVERIFIED_PROGRAMME'
    elif any(name not in knobs for name in names):state='FLAG_ABSENT'
    elif any(not str(knobs[name]).isdigit() or int(knobs[name])<1 for name in names):state='NOT_INSTRUMENTED'
    elif not records:state='INSTRUMENTED_NO_TELEMETRY'
    else:state='INSTRUMENTED_OBSERVATIONS_ONLY'
    return dict(state=state,resolved_flags=flags,row_count=len(records),rows=records,gate_verdict='NOT_EVALUATED')


def summarize(text,knobs,trusted=True):
    lines=text.splitlines();dedup=rows(lines,r'\bSCNDEDUP3\s')
    terminal=rows(lines,r'^route movie terminal=');cadence=rows(lines,r'^route movie cadence ')
    borrows=rows(lines,r'^MOVIEARENA borrow ');returns=rows(lines,r'^MOVIEARENA return ')
    movies=[]
    for row in terminal:
        f=row['fields'];match=re.fullmatch(r'(\d+)/(\d+)',str(f.get('frames','')))
        done,total=(int(match[1]),int(match[2])) if match else (None,None)
        pictures=bool(total and done==total and f.get('terminal')==1 and f.get('uploaded')==total and f.get('presented')==total)
        prior=[b for b in borrows if b['line']<row['line'] and b['fields'].get('id')==f.get('id')]
        loan=prior[-1] if prior else None
        matching=[r for r in returns if loan and loan['line']<r['line']<row['line'] and r['fields'].get('token')==loan['fields'].get('token')]
        returned=matching[-1] if matching else None
        reload_rows=[d for d in dedup if loan and returned and loan['line']<d['line']<returned['line']]
        movies.append(dict(terminal=row,complete_picture_counts_observed=pictures,
                           frames_done=done,frames_total=total,uploaded=f.get('uploaded'),presented=f.get('presented'),heap_before=f.get('heap_before'),heap_active=f.get('heap_active'),
                           wall_us=f.get('wall_us'),media_us=f.get('media_us'),
                           loan=loan,matching_return=returned,restored_observed=bool(returned and returned['fields'].get('restored')==1),
                           dedup_rows_between_borrow_and_return=reload_rows,
                           cadence=[c for c in cadence if c['fields'].get('id')==f.get('id')]))
    squeeze=rows(lines,r'^kos squeeze:');watch=rows(lines,r'^kos watch:')
    kos=diagnostic(knobs,('KOS_WATCH','KOS_SQUEEZE'),squeeze+watch,trusted)
    kos.update(squeeze_rows=squeeze,watch_row_count=len(watch),held_values=sorted({r['fields']['held'] for r in squeeze if isinstance(r['fields'].get('held'),int)}),
               minimum_headroom=min((r['fields']['headroom'] for r in watch if isinstance(r['fields'].get('headroom'),int)),default=None),
               minimum_top=min((r['fields']['top'] for r in watch if isinstance(r['fields'].get('top'),int)),default=None))
    texrows=rows(lines,r'\btexchk:|\bTEXCHK\b');tex=diagnostic(knobs,('TEX_CHECK',),texrows,trusted)
    tex.update(explicit_failure_rows=[r for r in texrows if re.search(r'\bFAIL\b|\b(?:META|VRAM) CHANGED\b',r['raw'])],
               maximum_fails=numeric_max(texrows,'fails'),maximum_changes=numeric_max(texrows,'changes'))
    castrows=rows(lines,r'^NMRS |^NMRD |^NMRU2? |^NMRPACK |\bCAST-GC\b')
    nmrs=[r for r in castrows if r['raw'].startswith('NMRS ')]
    cast=diagnostic(knobs,('NATIVE_MODEL_REGISTRY_CENSUS',),nmrs,trusted)
    cast.update(context_rows=castrows,gc_fallback_rows=[r for r in nmrs if any(isinstance(r['fields'].get(k),int) and r['fields'][k]>0 for k in ('declined','registry_declined','absent'))],
                alive_rows=rows(lines,r'^warp: alivelist '),official_checker='cast_gc.py --not-drawn with source allowlists; not run by this auditor')
    leonrows=rows(lines,r'^LEONGC |\bLEON-GC\b');leon=diagnostic(knobs,('MCHECK_LEONGC',),leonrows,trusted)
    leon.update(armed_observed=any(r['raw'].startswith('LEONGC armed') for r in leonrows),fallback_rows=[r for r in leonrows if r['raw'].startswith('LEONGC f=')])
    vramrows=rows(lines,r'^vram (?:gaps|room|map)|^native UI VRAM:|no contiguous|vram.*refus')
    vram=diagnostic(knobs,('VRAM_ROOM_LOG',),vramrows,trusted)
    gaprows=[r for r in vramrows if r['raw'].lower().startswith('vram gaps:')]
    vram.update(maximum_counters={key:numeric_max(gaprows,key) for key in ('refusals','guard','guard_p','nocontig','latched','absent','dropped','fx_dropped','tex_rej','snd_fail')},
                refusal_or_no_contiguous_rows=[r for r in vramrows if re.search('no contiguous',r['raw'],re.I) or any(isinstance(r['fields'].get(k),int) and r['fields'][k]>0 for k in ('refusals','nocontig','guard_p','tex_rej'))])
    fault_pattern=r'\bHALT\b|\bFAULT\b|\bMISSING\b|Out of memory|alloc(?:ation)? failed|malloc failed|BAD-READ|DISC READ FAILED'
    fault_candidates=rows(lines,fault_pattern);faults=[];zero_counters=[];informational=[]
    for row in fault_candidates:
        if row['raw'].startswith('CRASH_SCREEN: ready'):
            informational.append(row);continue
        remainder=re.sub(r'\b(?:HALT|FAULT|MISSING)=0\b','',row['raw'],flags=re.I)
        if re.search(fault_pattern,remainder,re.I):faults.append(row)
        else:zero_counters.append(row)
    return dict(dedup=dedup,movies=movies,kos=kos,texchk=tex,cast_gc=cast,leon_gc=leon,vram=vram,
                faults=dict(count=len(faults),rows=faults,zero_counter_rows=zero_counters,informational_marker_rows=informational,absence_is_not_a_gate_pass=True),
                freeze_rows=rows(lines,r'warp:.*freeze|^freeze\b'),
                pixel_identity='NOT_EVALUATED; wall-time screenshots are not matched-frame evidence')


def screenshot_inventory(capture):
    result=[];warnings=[];root=capture.resolve();shots=capture/'shots'
    if shots.is_dir():
        for p in sorted(shots.rglob('*')):
            if not p.is_file() or p.suffix.lower() not in ('.png','.jpg','.jpeg','.bmp','.webp'):continue
            if not p.resolve().is_relative_to(root):warnings.append('Skipped screenshot outside explicit capture: '+str(p));continue
            result.append(dict(relative_path=p.relative_to(capture).as_posix(),**pin(p)))
    return result,warnings


def audit(args):
    capture=hostpath(args.capture);errors=[];planpath=hostpath(args.program_plan)
    plan=json.loads(planpath.read_text(encoding='utf-8-sig'));programme=plan['arms'][args.arm]['program']
    verified={};knobs={}
    for name,expected in programme.get('files',{}).items():
        try:
            path=hostpath(expected['path']);actual=pin(path);verified[name]=actual
            if (actual['bytes'],actual['sha256'])!=(expected['bytes'],expected['sha256']):errors.append('Programme pin mismatch: '+name)
            if name=='resolved-knobs.txt':knobs=dict(line.split('=',1) for line in path.read_text().splitlines() if '=' in line)
        except OSError as e:errors.append('Programme file unavailable: '+name+' '+str(e))
    if set(verified)!=set(('re4dc-game.elf','candidate.txt','stack.txt','resolved-knobs.txt','syms.txt')):errors.append('Complete programme pins not supplied/available')
    if knobs.get('SCENERY_DEDUP')!=('3' if args.arm=='on' else '0'):errors.append('Resolved SCENERY_DEDUP differs from selected arm')
    trusted=not errors
    fixture=hostpath(args.fixture);fixturepin=pin(fixture);raw=fixture.read_bytes();wire=raw.replace(b'\r',b'')
    if fixturepin['sha256']!=args.fixture_sha256.lower():errors.append('Explicit source fixture SHA mismatch')
    resultpath=capture/'run-result.json';result=json.loads(resultpath.read_text(encoding='utf-8-sig'))
    logged=result.get('fixtures',{}).get('warp',{})
    wirepin=dict(bytes=len(wire),sha256=hashlib.sha256(wire).hexdigest())
    if (logged.get('bytes'),logged.get('sha256'))!=(wirepin['bytes'],wirepin['sha256']):errors.append('Run-result fixture does not match normalized source fixture')
    captured=capture/'fixture-warp.txt';captured_pin=None
    if captured.is_file():
        captured_pin=pin(captured);cw=captured.read_bytes().replace(b'\r',b'')
        if hashlib.sha256(cw).hexdigest()!=wirepin['sha256']:errors.append('Captured fixture differs from normalized source')
    base_pin=None;programme_capture_binding='UNVERIFIED: no explicit --base-json'
    if args.base_json:
        basepath=hostpath(args.base_json);base=json.loads(basepath.read_text(encoding='utf-8-sig'));base_pin=pin(basepath)
        elf=programme.get('files',{}).get('re4dc-game.elf',{}).get('path')
        if not elf or hostpath(base.get('elf','')).resolve()!=hostpath(elf).resolve():errors.append('Base manifest ELF differs from programme pin')
        else:
            disc=result.get('tracks',{}).get('base',result.get('disc',''))
            if not disc or hostpath(disc).resolve()!=basepath.parent.resolve():errors.append('Capture disc path differs from explicit base manifest directory')
            else:programme_capture_binding='BASE_AND_CAPTURE_METADATA_PATH_MATCH; actual ELF pin verified; not disc-byte readback'
    track_match=None
    if args.track_sha256:
        track_match=result.get('tracks',{}).get('track03_sha256')==args.track_sha256.lower()
        if not track_match:errors.append('Captured track03 hash differs from explicit stage pin')
    logpath=capture/'run-output.txt';summary=summarize(text_bytes(logpath.read_bytes()),knobs,trusted)
    screenshots,notes=screenshot_inventory(capture)
    observed=result.get('emu','ABSENT');emu_match=observed==args.expected_emu
    if not emu_match:notes.append('Expected emulator '+args.expected_emu+'; captured result reports '+observed)
    if result.get('status')!='RUN_COMPLETE':notes.append('Capture status is not RUN_COMPLETE')
    if result.get('errors'):notes.append('Run-result contains errors; inspect before any gate decision')
    if isinstance(result.get('seconds'),(int,float)) and result['seconds']>60:notes.append('Requested capture duration exceeds the current 60-second limit')
    return dict(kind='EVIDENCE AUDIT ONLY; main owns gate decisions',capture=str(capture),identity_errors=errors,warnings=notes,
                auditor_source=pin(Path(__file__)),programme_plan=pin(planpath),programme_files=verified,programme_pins_verified=trusted,
                programme_capture_binding=programme_capture_binding,base_metadata=base_pin,explicit_track_pin_match=track_match,
                fixture_source=fixturepin,fixture_wire=wirepin,captured_fixture=captured_pin,
                capture_files={'run-result.json':pin(resultpath),'run-output.txt':pin(logpath)},
                run=dict(status=result.get('status'),name=result.get('name'),seconds=result.get('seconds'),elapsed_s=result.get('elapsed_s'),emulator_exited=result.get('emulator_exited'),reader_exit=result.get('reader_exit'),
                         stop=result.get('stop'),stopped=result.get('stopped'),errors=result.get('errors'),
                         emulator_observed=observed,emulator_expected=args.expected_emu,emulator_matches=emu_match,tracks=result.get('tracks')),
                observations=summary,screenshots=screenshots,screenshot_count=len(screenshots),gate_verdict='NOT_EVALUATED')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--capture',required=True)
    p.add_argument('--program-plan',required=True);p.add_argument('--arm',choices=('off','on'),required=True)
    p.add_argument('--fixture',required=True);p.add_argument('--fixture-sha256',required=True)
    p.add_argument('--base-json');p.add_argument('--track-sha256');p.add_argument('--expected-emu',choices=('console','harness'),default='console')
    p.add_argument('--output',type=Path);a=p.parse_args();report=audit(a);value=json.dumps(report,indent=2)+'\n'
    if a.output:
        with a.output.open('x',encoding='utf-8') as f:f.write(value)
    else:print(value,end='')
    return 1 if report['identity_errors'] else 0

if __name__=='__main__':raise SystemExit(main())