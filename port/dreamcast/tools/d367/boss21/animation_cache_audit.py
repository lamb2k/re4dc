#!/usr/bin/env python3
"""Read-only, source-first animation residency inventory. No assets are emitted.

Literal/function-family reachability is NOT a concurrent working set. Only reviewed
recurring_sets are capacity-checked. Dynamic selectors/aliases remain explicit.
Uses actual selected DRS bytes; rejects malformed MTC tables and stale source pins.
"""
import argparse, hashlib, importlib.util, json, re, struct, zlib
from pathlib import Path

MAGIC = b'R4MOTBL\0'
NUMBER = r'(?:0x[0-9a-fA-F]+|[0-9]+)'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    out = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(out)
    return out

def archive(data, identity):
    # Transport slot zero must hold an in-bounds ordinary native archive.
    if len(data) < 64:
        raise ValueError(identity + ': short DRS')
    kind, size, unused, offset = struct.unpack_from('<4I', data, 32)
    if kind != 0 or offset < 0x400 or offset + size > len(data):
        raise ValueError(identity + ': invalid native payload slot')
    body = data[offset:offset + size]
    count, source_extent = struct.unpack_from('<II', body)
    if count > 8192 or 16 + 8 * count > len(body):
        raise ValueError(identity + ': invalid native archive directory')
    offsets = struct.unpack_from('<%dI' % count, body, 16)
    tags = [body[16 + 4*count + 4*i:20 + 4*count + 4*i] for i in range(count)]
    records, mtc = {}, None
    pos = body.find(MAGIC)
    if pos >= 0:
        version, n, stride, crc, native_size, cap = struct.unpack_from('<6I', body, pos + 8)
        raw = body[pos + 32:pos + 32 + n*stride]
        if version not in (2, 3) or stride != 20 or len(raw) != n*20 or zlib.crc32(raw) != crc or native_size != size:
            raise ValueError(identity + ': invalid MTC table')
        rows = [struct.unpack_from('<5I', raw, i*20) for i in range(n)]
        if any(o >= size or f not in (0, 1) or b > cap for o,b,c,h,f in rows):
            raise ValueError(identity + ': invalid MTC record')
        if version == 3 and any(r[4] for r in rows):
            raise ValueError(identity + ': unexpected bounded hot flags')
        for i, (o, b, c, h, f) in enumerate(rows):
            records[o] = dict(entry=i, bytes=b, key='%08x-%08x' % (c,h), state='cached-hot-preload' if f else 'cached-cold')
        mtc = dict(version=version, count=n, cap=cap, table_crc='%08x' % crc,
                   reserved_slots=2, max_cold_slab=max(((r[1]+31)&~31 for r in rows if not r[4]), default=0),
                   hot_preload_bytes=sum(r[1] for r in rows if r[4]),
                   policy='strict two slabs; no spill' if version == 3 else 'two reserved slabs; conditional spill/cold-pool/global pressure',
                   permanent_hot_lease=False)
    clips = {}
    for slot, (o, tag) in enumerate(zip(offsets,tags)):
        if tag == b'FCV\0':
            if o >= size:
                raise ValueError(identity + ': FCV offset outside body')
            clips[str(slot+4)] = dict(arc=slot+4, offset=o, **records.get(o, dict(state='inline-resident')))
    return dict(identity=identity, wrapper_bytes=len(data), wrapper_sha256=sha(data), native_bytes=size,
                native_sha256=sha(body), members=count, mtc=mtc,
                inline_unique=len({c['offset'] for c in clips.values() if c['state']=='inline-resident'}),
                cached_unique=len(records), clips=clips)

def clean(text):
    # Preserve positions/newlines for source evidence. No preprocessing or CFG claim.
    pattern=r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\''
    return re.sub(pattern, lambda m: re.sub(r'[^\n]', ' ', m[0]), text, flags=re.S)

def functions(text):
    c = clean(text)
    pat = r'^[ \t]*(?:(?:static|inline|extern|virtual)\s+)*(?:[\w:*<>]+\s+)+([\w:~]+)\([^;{}]*\)\s*(?:const\s*)?\{'
    for m in re.finditer(pat, c, re.M):
        depth, end = 1, m.end()
        while end < len(c) and depth:
            depth += (c[end]=='{')-(c[end]=='}')
            end += 1
        yield m[1], m.start(), end, c[m.start():end]
    lines=c.splitlines(keepends=True);pos=0;i=0
    while i<len(lines):
        start=pos;line=lines[i];match=re.match(r'^#define\s+(\w+)',line)
        end=i
        if match:
            while lines[end].rstrip().endswith(chr(92)) and end+1<len(lines):end+=1
            block=''.join(lines[i:end+1])
            if 'ARC' in block:yield 'macro:'+match[1],start,start+len(block),block
        pos+=sum(map(len,lines[i:end+1]));i=end+1

def family(name):
    if re.search(r'Die|Death|Dm_|Damage|Yarare|_Dm|DmSet|Hurt',name,re.I): return 'damage-death'
    if re.search(r'Atk|Attack|Catch|Hug|Spear|Reload|Ready|Shoot|Knife|Aim',name,re.I): return 'attack-aim-reload'
    if re.search(r'Wait|Idle|Walk|Run|Dash|Back|Turn|Goto|Foot|MoveNormal|Near|Find|Threat',name,re.I): return 'idle-locomotion-nearby'
    return 'initialization-transition-other'

def source_audit(root, archive_map):
    paths = []
    for folder in ['em10','em11','em12','em13','em14','em15','em16','em17','em1b','em1c','em2b','em2f','em35','em2c','em38','em32','em39','em31','pl11']:
        paths.extend((root/'src'/folder).glob('*.cpp'))
    for name in ['emwep.cpp','pl_npc.cpp','player.cpp','pl_leon.cpp','pl_class.cpp','pl_wep.cpp','pl_neck.cpp','pl_body.cpp','motion.cpp','shape.cpp','read.cpp']:
        p=root/'src/game'/name
        if p.exists(): paths.append(p)
    paths.extend(p for p in (root/'src').glob('wep*/*.cpp'))
    output=[]
    for p in sorted(set(paths)):
        text=p.read_text(errors='replace'); rel=p.relative_to(root).as_posix()
        folder=p.parent.name; owner=folder+'.drs' if folder.startswith(('em','wep')) else None
        aliases={m[1]:m[2].strip() for m in re.finditer(r'^#define\s+(\w+)\([^\n]*?\)\s+PL_ARC_PTR\(([^,\n]+),',text,re.M)}
        refs=[]; dynamics=[]; summaries={}; consumers=[]; work_aliases=[]
        for name,start,end,body in functions(text):
            cat=family(name)
            for number,line in enumerate(body.splitlines()):
                lineno=text.count('\n',0,start)+number+1
                if number and re.search(r'MotionSetCore|MOT_SET\(|ShapeSet\(|BlendMotSet\w*\(|(?:->|\b)motionSet\(|Neck->init\(',line):
                    consumers.append(dict(line=lineno,function=name,family=cat,call=line.strip(),
                        unresolved_selector=not bool(re.search(r'\b(?:ARC|SUB_MOT|PL_ARC|EM_ARC|PL_ARC_PTR|WEP_ARC_PTR)\(',line))))
                if re.search(r'(?:w->mot\[|pMotTbl\[|blendM[0-3]\s*=|subArc\s*=)',line):
                    work_aliases.append(dict(line=lineno,function=name,assignment_or_use=line.strip()))
            for m in re.finditer(r'\b(PL_ARC_PTR|WEP_ARC_PTR|SUB_MOT|ARC|PL_ARC|EM_ARC|[A-Z0-9_]+_ARC)\(([^()\n]*)\)',body):
                macro,args=m[1],m[2].split(','); expr=args[-1].strip()
                line=text.count('\n',0,start+m.start())+1
                if macro=='PL_ARC_PTR': binding=args[0].strip()
                elif macro=='WEP_ARC_PTR': binding='pG->pWep'
                elif macro=='SUB_MOT': binding='pl->subArc'
                else: binding=aliases.get(macro,'unresolved macro '+macro)
                targets=[]
                if binding=='pG->pPlayer': targets=['pl00.drs','pl08.drs']
                elif binding=='pG->pWep' and folder.startswith('wep'): targets=[folder+'.drs']
                elif folder=='em10' and 'subArc' in binding: targets=['em%02x.drs'%i for i in list(range(0x11,0x18))+[0x1b,0x1c]]
                elif folder.startswith('em') and 'subArc' in binding: targets=[owner]
                elif folder=='pl11' or (p.name=='pl_npc.cpp' and 'subArc' in binding): targets=['pl11.drs']
                # A borrowed player subArc in a boss is recorded; this mapping is a candidate
                # until its assignment is reviewed. Only concrete recurring rules certify it.
                record=dict(line=line,function=name,family=cat,macro=macro,binding=binding,expression=expr)
                if not re.fullmatch(NUMBER,expr):
                    dynamics.append(record); continue
                ai=int(expr,0); record['arc']=ai; record['mapped']=[]
                for target in targets:
                    variants=[(k,a) for k,a in archive_map.items() if Path(a['identity']).name==target]
                    for key,a in variants:
                        clip=a['clips'].get(str(ai))
                        if clip: record['mapped'].append(dict(archive=key,**clip))
                refs.append(record)
            # Known macro family expands source indices, not a concurrency assertion.
            if folder=='em10':
                for m in re.finditer(r'EM10_WALK_MOT\(\s*('+NUMBER+r')\s*\)|EM10_BACK_MOT\(\s*('+NUMBER+r')\s*,\s*('+NUMBER+r')\s*\)',body):
                    ids=range(int(m[1],0),int(m[1],0)+6) if m[1] else [int(m[2],0),int(m[3],0)]
                    for ai in ids:
                        mapped=[dict(archive=k,**a['clips'][str(ai)]) for k,a in archive_map.items() if Path(a['identity']).name in ['em%02x.drs'%i for i in list(range(0x11,0x18))+[0x1b,0x1c]] and str(ai) in a['clips']]
                        refs.append(dict(line=text.count('\n',0,start+m.start())+1,function=name,family=cat,macro='reviewed EM10 macro expansion',binding='em->subArc',expression=str(ai),arc=ai,mapped=mapped))
        for cat in ['idle-locomotion-nearby','attack-aim-reload','damage-death','initialization-transition-other']:
            r=[r for r in refs if r['family']==cat]
            summaries[cat]=dict(functions=sorted({x['function'] for x in r}),literal_indices=sorted({x['arc'] for x in r}),
                                mapped_unique=len({(c['archive'],c['offset']) for x in r for c in x['mapped']}))
        if refs or dynamics or consumers or work_aliases:
            output.append(dict(source=rel,sha256=sha(p.read_bytes()),families=summaries,literal_references=refs,
                               dynamic_references=dynamics,motion_consumers=consumers,work_aliases=work_aliases,concurrent_working_set_inferred=False))
    return output

def evaluate_set(a, indices):
    clips=[a['clips'].get(str(i),dict(arc=i,state='not-FCV-or-absent')) for i in indices]
    cold={c['key'] for c in clips if c['state']=='cached-cold'}
    missing=[c['arc'] for c in clips if c['state']=='not-FCV-or-absent']
    v=a['mtc']['version'] if a['mtc'] else None
    cached={c['key'] for c in clips if c['state'].startswith('cached-')}
    return dict(clips=clips,distinct_cold=len(cold),distinct_cached=len(cached),missing=missing,
                exceeds_two_reserved_if_preload_or_spill_lost=(v is not None and len(cached)>2),
                strict_two_slab_overflow=(v==3 and len(cold)>2),
                conclusion='unresolved mapping' if missing else 'demonstrable recurring cold working set exceeds two slots' if v==3 and len(cold)>2 else 'specific set fits/inline; not all-state closure')

def reviewed_rules(root, archives):
    # Fail closed on source drift in reviewed anchors. References remain in report.
    anchors={
      'src/game/pl_npc.cpp':['back = SUB_MOT(subSelf, 0x18)','setFace(4)','ShapeMove(subShape)','blendMot = &subBackMot'],
      'src/pl11/pl11.cpp':['case 4:','data = ARC(0x6D)','ShapeSet'],
      'src/game/motion.cpp':['MotionMoveCore(m, MOTION(m), 0)','MotionMoveCore(m, MOTION(m)->blend, 0)'],
      'src/game/shape.cpp':['Re4dcMotionLease'],
      'src/em39/em39.cpp':['MotionSetCore(w->pMachineGun, MOTION(w->pMachineGun), ARC(0x2F)','em39BlendMotSet(em, ARC(0x7F), ARC(0x80), ARC(0x81)'],
      'src/game/emwep.cpp':['MotionMove(this, 0)'],
      'src/em35/em35.cpp':['em35BlendMotSet(em, ARC(0x6A), ARC(0x6D), ARC(0x6C), ARC(0x6B)','pl->subArc = PL_EM_G->subArc','if (w->blendRate < 0.0f)'],
    }
    proof=[]
    for file, needles in anchors.items():
        t=(root/file).read_text()
        for needle in needles:
            # Whitespace and case normalization supports source spelling only.
            norm=re.sub(r'\s+','',t).lower(); wanted=re.sub(r'\s+','',needle).lower()
            if wanted not in norm: raise ValueError('reviewed anchor missing: '+file+' '+needle)
            line=next((i for i,l in enumerate(clean(t).splitlines(),1) if wanted in re.sub(r'\s+','',l).lower()),None)
            if line is None: raise ValueError('anchor is not active source: '+needle)
            proof.append(dict(source=file,anchor=needle,line=line))
    face_source=clean((root/'src/pl11/pl11.cpp').read_text())
    face=re.search(r'case\s+4:\s*data\s*=\s*ARC\(\s*('+NUMBER+r')\s*\);\s*type\s*=\s*6\s*;',face_source)
    if face is None: raise ValueError('held face4 source rule changed')
    face_arc=int(face[1],0)
    results=[]
    for key,a in archives.items():
        if Path(a['identity']).name=='pl11.drs':
            results.append(dict(rule='Ashley healthy body + look-back blend + held face4',archive=key,
                recurrence='moveFootwork main12 + backCheckSet18; face4 survives return to footwork; ShapeMove evaluates held6d each tick',
                reviewed_source=proof,**evaluate_set(a,[0x12,0x18,face_arc])))
        if Path(a['identity']).name=='em39.drs':
            results.append(dict(rule='Krauser MG positive-pitch body + blend + attached gun',archive=key,
                recurrence='MG source case4/5 sets attached gun2f and main7f+positive-pitch81; child cEmWep moveCloth evaluates gun each tick',
                **evaluate_set(a,[0x2f,0x7f,0x81])))
        if Path(a['identity']).name=='em35.drs':
            for secondary in [0x6d,0x6c]:
                results.append(dict(rule='Mendez spear sign-selected pair',archive=key,
                    recurrence='spear sets blendRate once before repeated case1;6b is SEQ, other sign branch is exclusive',
                    **evaluate_set(a,[0x6a,secondary])))
    return results

def telemetry(roots):
    """Retained logs only. Missing markers are not a zero-I/O certificate."""
    report=dict(files_scanned=0,roots=[str(p) for p in roots],files=[])
    for root in roots:
        for path in sorted(root.rglob('run-output.txt')):
            report['files_scanned']+=1
            lines=path.read_text(errors='replace').splitlines()
            miss=[];ws=[];bind=[]
            for number,line in enumerate(lines,1):
                if 'motion miss #' in line:
                    m=re.search(r'archive=(\d+) entry=(\d+) bytes=(\d+) wait_us=(\d+).*evictions=(\d+)',line)
                    if m:miss.append(dict(line=number,archive_bytes=int(m[1]),entry=int(m[2]),bytes=int(m[3]),wait_us=int(m[4]),global_evictions=int(m[5])))
                elif 'MOTWS:' in line:ws.append(dict(line=number,text=line))
                elif 'motion bind:' in line:bind.append(dict(line=number,text=line))
            if miss or ws or bind:
                report['files'].append(dict(path=str(path),sha256=sha(path.read_bytes()),misses=miss,working_set_samples=ws,binds=bind))
    return report
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-root',type=Path,required=True);p.add_argument('--tools-root',type=Path,required=True)
    p.add_argument('--iso',type=Path,required=True);p.add_argument('--manifest',type=Path)
    p.add_argument('--resolved-knobs',type=Path)
    p.add_argument('--baseline-iso',type=Path);p.add_argument('--later-tree',type=Path)
    p.add_argument('--archive',action='append',default=[],help='prepared-label=DRS-path')
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--log-root',action='append',default=[],type=Path)
    a=p.parse_args(); archives={}; inputs=[]; ancillary={}
    iso=module(a.tools_root/'port/dreamcast/tools/d367/fullplay/fp_iso.py','fp_iso')
    manifest=json.loads(a.manifest.read_text()) if a.manifest else None
    for label,path in [('qa-fixed',a.iso),('qa-original',a.baseline_iso)]:
        if not path: continue
        track=iso.Track(path,45000)
        entries={name.lstrip('/'):(e,n) for name,e,n in iso.files(track)}
        if label=='qa-fixed':
            for name,(e,n) in entries.items():
                if name=='1ST_READ.BIN' or name.startswith(('dc/native/pl00/','dc/native/pl08/')):
                    digest=sha(track.read_bytes(e,n))
                    if manifest is not None and (name not in manifest or manifest[name]['sha256']!=digest or manifest[name]['size']!=n):
                        raise ValueError('ancillary manifest mismatch: '+name)
                    ancillary[name]=dict(bytes=n,sha256=digest)
        for name,(e,n) in sorted(entries.items()):
            if not(name.startswith('em/') and name.endswith('.drs')):continue
            if label=='qa-original' and name!='em/pl11.drs': continue
            parsed=archive(track.read_bytes(e,n),name)
            if label=='qa-fixed' and manifest is not None:
                expected=manifest.get(name)
                if expected is None or expected['size']!=n or expected['sha256']!=parsed['wrapper_sha256']:
                    raise ValueError('selected manifest mismatch: '+name)
                parsed['selected_manifest_match']=True
            archives[label+':'+name]=parsed
        track.f.close(); inputs.append(dict(label=label,path=str(path)))
    if a.later_tree:
        for name in ['em1b','em1c','em2b','em2c','em38']:
            f=a.later_tree/'em'/(name+'.drs')
            if f.exists(): archives['later-castle:em/'+f.name]=archive(f.read_bytes(),'em/'+f.name)
        inputs.append(dict(label='later-castle-retained-diagnostic-tree',path=str(a.later_tree)))
    for item in a.archive:
        label,path=item.split('=',1);f=Path(path)
        archives['prepared-'+label+':em/'+f.name]=archive(f.read_bytes(),'em/'+f.name)
        inputs.append(dict(label='prepared-'+label,path=path))
    # Existing em10 audit is retained, not silently upgraded to a CFG proof.
    em10=module(a.tools_root/'port/dreamcast/tools/audit_enemy_motion_prefetch.py','em10_prefetch')
    selected=archives.get('qa-fixed:em/em12.drs')
    grouped={}
    for arc,c in selected['clips'].items():
        if c['state']=='inline-resident': continue
        grouped.setdefault(c['key'],dict(key=c['key'],bytes=c['bytes'],slots=[]))['slots'].append(int(arc)-4)
    legacy=em10.audit(a.source_root/'src/em10/em10.cpp',dict(entries=list(grouped.values())))
    report=dict(schema='re4-source-animation-cache-audit-v1',inputs=inputs,
                scope='read-only selected bytes + literal/function families + explicitly reviewed recurring rules; no CFG/all-state closure',
                manifest_sha256=sha(a.manifest.read_bytes()) if a.manifest else None,
                selected_ancillary=ancillary,
                runtime_sources=[dict(source=f,sha256=sha((a.source_root/f).read_bytes())) for f in ['port/dreamcast/game/platform/native_motion.cpp','port/dreamcast/game/platform/include/native_motion.h','port/dreamcast/game/platform/native_motion_r11f_profiles.inc','port/dreamcast/tools/prepare_enemy_motions.py','port/dreamcast/tools/audit_enemy_motion_prefetch.py','port/dreamcast/game/coarse_actor_leon_hands.inc','port/dreamcast/game/coarse_actor_pl08_pack.inc']],
                compiled_knobs=dict(path=str(a.resolved_knobs),sha256=sha(a.resolved_knobs.read_bytes()),values=[l for l in a.resolved_knobs.read_text().splitlines() if l.startswith(('MOTION_','LEON_HAND_','ACTOR_PL08_PACK='))]) if a.resolved_knobs else None,
                archives=archives,source=source_audit(a.source_root,archives),reviewed_recurring_sets=reviewed_rules(a.source_root,archives),
                existing_em10_audit=legacy,retained_telemetry=telemetry(a.log_root),
                limitations=['total reachable indices never imply simultaneous streams',
                   'MTC v2 hot flags preload; global pressure can evict; spill/pool require actual compiled knobs',
                   'inline FCV removes this cache read path after archive admission, not archive-switch/texture/hand/renderpack I/O',
                   'dynamic selector/Work alias and encounter concurrency closure remains explicit; historic render/STRICT gates are not cache closure'])
    baseline=[x for x in report['reviewed_recurring_sets'] if x['archive'].startswith('qa-original:')]
    fixed=[x for x in report['reviewed_recurring_sets'] if x['archive']=='qa-fixed:em/pl11.drs']
    if baseline:
        assert len(baseline)==1 and baseline[0]['strict_two_slab_overflow'] and [c['entry'] for c in baseline[0]['clips']]==[0,6,61]
        assert len(fixed)==1 and not fixed[0]['strict_two_slab_overflow'] and all(c['state']=='inline-resident' for c in fixed[0]['clips'])
    report['known_failure_regression']=dict(baseline_flags=bool(baseline),fixed_specific_rule_clears=bool(fixed and not fixed[0]['strict_two_slab_overflow']))
    a.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(archives=len(archives),sources=len(report['source']),regression=report['known_failure_regression'],output=str(a.output))))

if __name__=='__main__': main()