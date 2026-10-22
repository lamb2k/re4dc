#!/usr/bin/env python3
"""ONE root-allocated private link unit; no image/stage/guest. Frozen source only."""
from pathlib import Path
import ast,gzip,lzma,hashlib,json,os,re,shutil,signal,struct,subprocess,sys,time

def main():
    sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    assert len(sys.argv)==3,'freeze receipt and exact controller hash required'
    freeze_path=Path(sys.argv[1]);freeze=json.loads(freeze_path.read_text());this=Path(__file__).resolve()
    assert sha(this)==sys.argv[2]==freeze['controller_sha256'] and this.stat().st_size==freeze['controller_bytes']>=15000
    assert freeze['AST_required_main_tasks_guard_pins'] and freeze['py_compile_pass']
    R=Path('/root/probe/codex-mipmap21-next792');PREP=Path('/root/probe/codex-issue52-objects')
    B=Path('/root/probe/mipmap21-next792-link-20261022-04');E=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/mipmap21-next792-programme-20261022-04')
    OLD=Path('/root/re4data/private/texture-consumers21-next650-programme-plan-20261022');Q=Path('/root/re4data/private/texture-consumers21-next792-runner-20261022')
    CAN=Path('/root/probe/texture-rect21-canonical36-link-20261021-01');CE=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/texture-rect21-20261021/canonical-programme-01')
    NEXT=Path('/root/re4data/private/texture-consumers21-next792-runner04-20261022')
    AL=Path('/mnt/c/Game Dev/Emulators/codex-lanes/cache21/NEXT792-LINK-ROOT-04-ALLOCATION.json');TOOL=Path('/opt/toolchains/dc/sh-elf/bin');SCR=Path('/root/work/kos-re4dc-d367/utils/scramble/scramble')
    allocation=json.loads(AL.read_text());proposal=json.loads((Q/'concrete-qualified-link-proposal.json').read_text());plan=json.loads((OLD/'plan.json').read_text())
    proposal['command']=[arg.replace('/root/probe/mipmap21-next792-link-20261022-01',str(B))for arg in proposal['command']]
    proposal['environment']={key:value.replace('/root/probe/mipmap21-next792-link-20261022-01',str(B))for key,value in proposal['environment'].items()}
    assert sha(AL)==freeze['allocation_sha256']
    assert allocation['source']=='63644457a2251a398de174f47be650e1b2b4c791'
    assert allocation['allocated'] and allocation['allowed_runs']==1 and allocation['output']==str(B)
    MAX=allocation['max_output_bytes'];FLOOR=allocation['runtime_floor_bytes']+allocation['peer_reserved_bytes'];SOURCE=allocation['source'];AUX=131072
    assert MAX==134217728 and not B.exists() and not E.exists(),'fresh unit required; no automatic retry'
    assert os.environ.get('D367_SLOT_HELD')=='1','exactly one lease through pinned helper'
    assert shutil.disk_usage('/mnt/c').free>=FLOOR+MAX
    assert sha(NEXT/'SHA256SUMS.txt')==allocation['plan_seal_sha256']
    for folder in (NEXT,Q,OLD):
        for line in (folder/'SHA256SUMS.txt').read_text().splitlines():
            digest,relative=line.split('  ',1);assert sha(folder/relative)==digest
    assert freeze['source_clean_checked_before_entry'] and freeze['source']=='63644457a2251a398de174f47be650e1b2b4c791'
    expected={}
    approved_rebased={row['new']['path']:row['new']for row in proposal['source_closure']['changed_vs650']}
    def add(row):
        row=dict(row);row['path']=row['path'].replace('/root/probe/codex-mipmap21-next650/','/root/probe/codex-mipmap21-next792/')
        if row['path']in approved_rebased:row=approved_rebased[row['path']]
        p=Path(row['path']);assert sha(p)==row['sha256'],str(p)
        if str(p) in expected:assert expected[str(p)]['sha256']==row['sha256']
        else:expected[str(p)]=dict(path=str(p),bytes=p.stat().st_size,sha256=row['sha256'])
    for file in ['reuse445.json','candidate-dependency-pins.json']:
        for row in json.loads((OLD/file).read_text()):add(row)
    support=json.loads((OLD/'link-support-current-pins.json').read_text())
    for row in support['explicit_support']+support['implicit']:add(row)
    for row in json.loads((Q/'qualified-active-dependencies.json').read_text())['pins']:add(row)
    for row in proposal['qualified_inputs'].values():
        for kind in ('raw','stripped','receipt'):add(row[kind])
    for p in [SCR,SCR.with_suffix('.c'),Path('/root/probe/d367-buildslot.sh'),R/'port/dreamcast/kos-env.sh',AL,this,freeze_path]:add(dict(path=str(p),sha256=sha(p)))
    absent=[R/'port/dreamcast/game/platform/native_static.cpp.gch',R/'port/dreamcast/game/platform/native_ui.cpp.gch',Path('/opt/toolchains/dc/sh-elf/lib/gcc/sh-elf/15.2.0/specs')]
    def source_head():
        dot=R/'.git'
        gitdir=dot if dot.is_dir()else Path(dot.read_text().strip().split('gitdir: ',1)[1])
        if not gitdir.is_absolute():gitdir=(R/gitdir).resolve()
        head=(gitdir/'HEAD').read_text().strip()
        if not head.startswith('ref: '):return head,head
        ref=head[5:];common=(gitdir/(gitdir/'commondir').read_text().strip()).resolve()if(gitdir/'commondir').exists()else gitdir
        path=common/ref
        if path.exists():return path.read_text().strip(),head
        matches=[line.split()[0]for line in(common/'packed-refs').read_text().splitlines()if not line.startswith(('#','^'))and line.split()[1:]==[ref]]
        assert len(matches)==1
        return matches[0],head
    expected_source_head=source_head()
    assert expected_source_head[0]==SOURCE
    def pins():
        # Root entry freeze carries fresh clean-status proof. Keep branch/head + every build input exact without untraced Git children.
        assert source_head()==expected_source_head and source_head()[0]==SOURCE
        for row in expected.values():assert Path(row['path']).stat().st_size==row['bytes'] and sha(row['path'])==row['sha256'],row['path']
        assert not any(p.exists() for p in absent),'absence invariant changed'
        assert sha(OLD/'SHA256SUMS.txt')=='cbc3734ce453d8b5462ea29e0228967566e1b64e5191b95e4abcc65c127862b5'
    ctx=B/'link-context'
    bridge_plan=json.loads(lzma.decompress((NEXT/'runner-plan.json.xz').read_bytes()))
    for row in bridge_plan['source_bridge_pins']:assert sha(row['path'])==row['sha256'] and Path(row['path']).stat().st_size==row['bytes']
    sys.path.insert(0,'/root/probe/codex-mipmap21-alpha-reader/port/dreamcast/tools/d367/link_closure21')
    from runner_trace792_04 import Gate,compare_driver
    gate=Gate(bridge_plan,expected,B,ctx)
    pins();B.mkdir();E.mkdir();(B/'out').mkdir();(B/'objects').mkdir();(B/'temp').mkdir();(B/'empty-pyc').mkdir();(ctx/'obj').mkdir(parents=True)
    peak=0;minimum_free=shutil.disk_usage('/mnt/c').free;owned=[];steps=[]
    def charged_file(path):
        st=path.stat();logical=st.st_size
        return max(logical,getattr(st,'st_blocks',0)*512,((logical+4095)//4096)*4096)
    def used():
        return AUX+sum(charged_file(p)for root in(B,E)for p in root.rglob('*')if p.is_file()and not p.is_symlink())
    def guard(reserve=0):
        nonlocal peak,minimum_free
        u=used();f=shutil.disk_usage('/mnt/c').free;peak=max(peak,u);minimum_free=min(minimum_free,f)
        assert u+reserve<MAX,('hard allocation',u,reserve)
        assert f>=FLOOR,('runtime floor',f,FLOOR)
        assert sum(p.stat().st_size for p in B.glob('*.log.gz'))<8*1024**2,'log cap'
    def write(p,b):
        guard(len(b)+65536);p.parent.mkdir(parents=True,exist_ok=True)
        with p.open('xb') as f:f.write(b)
    def emit(p,x):write(p,(json.dumps(x,indent=2)+chr(10)).encode())
    write(B/'controller.py',this.read_bytes());write(E/'root-allocation.json',AL.read_bytes());write(E/'controller-freeze.json',freeze_path.read_bytes())
    emit(E/'fresh-unit-tool-prepins.json',dict(pins=gate.fresh_pre,controller_maps=gate.pre_maps,scope='Fresh before first allocated child; source snapshot and650prehash gap remain separate.'))
    emit(E/'pre-input-pins.json',list(expected.values()));emit(E/'absence-invariants.json',[str(p) for p in absent])
    emit(E/'initial.json',dict(source=SOURCE,controller_sha256=sha(this),controller_bytes=this.stat().st_size,one_slot=True,PID=os.getpid(),start=Path('/proc/self/stat').read_text().split()[21],max_bytes=MAX,start_free=minimum_free,runtime_floor=FLOOR))
    (ctx/'platform').symlink_to('/root/probe/codex-texture-rect21/port/dreamcast/game/platform',target_is_directory=True)
    write(ctx/'obj/overlay-a.ld',(CAN/'link-context/obj/overlay-a.ld').read_bytes())
    def run(name,command,timeout=55,reserve=4*1024**2,capture_environment=False):
        guard(reserve);task=dict(cwd=str(ctx),environment=proposal['environment'],command=command)
        if capture_environment:task['capture_environment']=str(B/(name+'-environment.json'))
        tp=B/(name+'-task.json');emit(tp,task);log=B/(name+'.log');start=time.monotonic();child=None;failure=None
        try:
            with log.open('xb') as f:
                launch,child_environment=gate.before(name,command)
                if capture_environment:emit(Path(task['capture_environment']),child_environment)
                child=subprocess.Popen(launch,cwd=ctx,env=child_environment,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
                pid=child.pid;birth=Path('/proc/'+str(pid)+'/stat').read_text().split()[21]
                record=dict(name=name,PID=pid,PGID=os.getpgid(pid),SID=os.getsid(pid),start=birth,command=command,timeout=timeout);owned.append(record);emit(E/(name+'-owned.json'),record)
                print(json.dumps(dict(started=name,PID=pid,new_bytes=used(),free_C=shutil.disk_usage('/mnt/c').free)),flush=True)
                while child.poll() is None:
                    try:guard()
                    except BaseException as ex:failure=str(ex)
                    if time.monotonic()-start>timeout:failure='absolute time limit'
                    if log.stat().st_size>8*1024**2:failure='raw log cap'
                    tracepath=B/(name+'.strace')
                    if tracepath.exists()and tracepath.stat().st_size>8*1024**2:failure='raw trace cap'
                    if failure:
                        assert os.getpgid(pid)==pid and Path('/proc/'+str(pid)+'/stat').read_text().split()[21]==birth
                        os.killpg(pid,signal.SIGTERM)
                        try:child.wait(timeout=3)
                        except subprocess.TimeoutExpired:os.killpg(pid,signal.SIGKILL);child.wait(timeout=3)
                        break
                    time.sleep(.2)
                rc=child.wait()
            record.update(returncode=rc,seconds=time.monotonic()-start,guard=failure,log_sha256=sha(log));emit(E/(name+'-result.json'),record)
            if rc or failure:raise RuntimeError('failed '+name+' '+str(record)+' tail '+log.read_text(errors='replace')[-2000:])
            assert b'strace: 'not in log.read_bytes(),'trace inspector warning/error'
            gate.after(name,rc)
            write(log.with_suffix('.log.gz'),gzip.compress(log.read_bytes(),mtime=0));assert log.resolve().parent==B.resolve();log.unlink();steps.append(record);guard();return gzip.decompress(log.with_suffix('.log.gz').read_bytes())
        except BaseException:
            if child is not None and child.poll() is None:
                assert os.getpgid(child.pid)==child.pid and Path('/proc/'+str(child.pid)+'/stat').read_text().split()[21]==birth
                os.killpg(child.pid,signal.SIGTERM);child.wait(timeout=3)
            raise
    # Read only immutable reference function definitions, never execute old controller top-level code.
    tree=ast.parse((CE/'controller.py').read_text());defs=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('elf','section_proof')]
    ns=dict(struct=struct,hashlib=hashlib);exec(compile(ast.Module(body=defs,type_ignores=[]),'pinned-ELF-reader','exec'),ns);parse=ns['elf'];proof=ns['section_proof']
    qualifier=(CE/'independent_qualifier.py').read_text();node=next(n for n in ast.parse(qualifier).body if isinstance(n,ast.FunctionDef) and n.name=='elf')
    inspect_source=ast.get_source_segment(qualifier,node).replace("if name in('_re4dc_image_id','_end','_start'):","if name:")
    inspect_ns=dict(struct=struct);exec(compile(inspect_source,'pinned-independent-ELF-reader','exec'),inspect_ns);inspect=inspect_ns['elf']
    def normalized(path,mapping=None):
        hs,names,data=parse(path);mapping=mapping or {};out={}
        for i,h in enumerate(hs):
            name=names[i];newname=mapping.get(name,name)
            if name=='.shstrtab':continue
            if h[1] in (4,9):
                target=names[h[7]];out['reloc:'+mapping.get(target,target)]=[tuple('@'+mapping.get(v[1:],v[1:]) if isinstance(v,str) and v.startswith('@') else v for v in row) for row in proof(path,target)['relocations']];continue
            if h[1] in (2,3):continue
            out['section:'+newname]=dict(type=h[1],flags=h[2],bytes=h[5],align=h[8],entry=h[9],sha256=hashlib.sha256(data(i)).hexdigest())
        symbols=[]
        for i,h in enumerate(hs):
            if h[1]!=2:continue
            strings=data(h[6]);raw=data(i)
            for off in range(0,len(raw),h[9] or 16):
                at,val,size,info,other,sect=struct.unpack_from('<IIIBBH',raw,off);name=strings[at:strings.find(b'\0',at)].decode();target=mapping.get(names[sect],names[sect]) if sect<len(names) else sect;symbols.append((name,val,size,info,other,target))
        out['symbols']=symbols;return out
    def fnv_words(blob):
        assert len(blob)%4==0;value=2166136261
        for(word,) in struct.iter_unpack('<I',blob):value=((value^word)*16777619)&0xffffffff
        return value
    def allocated(sections):
        return {k:sum(v['bytes'] for v in sections.values() if v['flags']&2 and ((v['flags']&4) if k=='exec' else v['type']==8 if k=='bss' else not(v['flags']&4) and v['type']!=8 and not(v['flags']&1) if k=='rodata' else v['flags']&1 and v['type']!=8)) for k in ('exec','rodata','data','bss')}
    try:
        source=Path(proposal['qualified_inputs']['native_static']['raw']['path']);old='.text.re4dc_ps2_area_flags';new='.ovl_st1_1.h2'
        expected_proof=json.loads((Q/'qualified-area-h2-proof.json').read_text())['actual_new_section'];assert json.loads(json.dumps(proof(source,old)))==expected_proof
        derived=B/'objects/native_static-linked.o';run('derive-static',[str(TOOL/'sh-elf-objcopy'),'--rename-section',old+'='+new,str(source),str(derived)],55,2*1024**2)
        assert json.loads(json.dumps(proof(derived,new)))==expected_proof and old not in parse(derived)[1]
        assert normalized(source)==normalized(derived,{new:old}),'nonrename section/symbol/relocation drift'
        emit(E/'derived-static-proof.json',dict(source_sha256=sha(source),derived_sha256=sha(derived),source_bytes=source.stat().st_size,derived_bytes=derived.stat().st_size,section=expected_proof,all_other_sections_symbols_relocations_exact=True,rename={old:new}))
        pins();command=proposal['command'];assert command.count(str(derived))==1 and len([s for s in command if s.endswith('.o')])==447
        run('driver-pre',command+['-###'],30,2*1024**2,True)
        pre_env=json.loads((B/'driver-pre-environment.json').read_text());assert pre_env['KOS_BASE']=='/root/work/kos-re4dc-d367' and '-lkallisti' in pre_env['KOS_LIBS']
        run('base-link',command,180,34*1024**2);target=B/'out/re4dc-game.elf'
        base_sections,_,_=inspect(target)
        assert [name for name in base_sections if name.startswith('.ovl_')]==bridge_plan['canonical_overlay_section_order'],'new actual overlay order differs from frozen source script'
        emit(E/'base-link-identity.json',dict(ELF_sha256=sha(target),bytes=target.stat().st_size,object_slots=447))
        script=ctx/'obj/overlay-a.ld';shift=B/'shift.elf';shiftld=ctx/'obj/overlay-shift.ld'
        for index,ov in enumerate(plan['overlays14']):
            text=script.read_text();address=int(ov['address'],16);text,count=re.subn(r'('+re.escape(ov['section'])+r'\s+)0x[0-9A-Fa-f]+',lambda m:m.group(1)+('0x%X'%(address+1048576)),text);assert count==1
            if shiftld.exists():assert shiftld.resolve().parent==(ctx/'obj').resolve();shiftld.unlink()
            write(shiftld,text.encode());cmd=list(command);cmd[cmd.index('-o')+1]=str(shift);needle='-Wl,-T,'+str(script);assert cmd.count(needle)==1;cmd[cmd.index(needle)]='-Wl,-T,'+str(shiftld)
            run('shift-'+str(index),cmd,180,34*1024**2)
            outfile=B/'out'/ov['output'];run('seal-'+str(index),['/usr/bin/python3','-I','-S','-B','-X','pycache_prefix='+str(B/'empty-pyc'),'/root/probe/codex-texture-rect21/port/dreamcast/game/tools/gen_overlay.py',str(target),str(shift),ov['section'],str(address),str(address+1048576),str(outfile)],55,5*1024**2)
            assert outfile.stat().st_size<=ov['original_slot_bytes'];emit(E/('overlay-'+str(index)+'.json'),dict(section=ov['section'],bytes=outfile.stat().st_size,sha256=sha(outfile),shift_ELF_sha256=sha(shift)))
            assert shift.resolve().parent==B.resolve() and shift.name=='shift.elf';shift.unlink();guard();pins()
        run('patch-image-id',['/usr/bin/python3','-I','-S','-B','-X','pycache_prefix='+str(B/'empty-pyc'),'/root/probe/codex-texture-rect21/port/dreamcast/game/tools/ovl_id_patch.py',str(target)],55,2*1024**2)
        final=B/'out/re4dc-final.elf';remove=[s for ov in plan['overlays14'] for s in ['-R',ov['section']]]
        run('strip-overlay-sections',[str(TOOL/'sh-elf-objcopy'),*remove,str(target),str(final)],55,34*1024**2)
        assert target.resolve().parent==(B/'out').resolve();target.unlink();final.rename(target)
        raw=B/'out/program.bin';scrambled=B/'out/1ST_READ.BIN';roundtrip=B/'temp/descrambled.bin'
        run('raw-program',[str(TOOL/'sh-elf-objcopy'),'-R','.stack','-O','binary',str(target),str(raw)],55,5*1024**2)
        run('scramble',[str(SCR),str(raw),str(scrambled)],55,5*1024**2);run('descramble-check',[str(SCR),'-d',str(scrambled),str(roundtrip)],55,5*1024**2)
        assert sha(roundtrip)==sha(raw) and roundtrip.stat().st_size==raw.stat().st_size;roundtrip.unlink()
        # Independent raw/overlay/header/relocation/identity qualification from actual new bytes.
        sections,symbols,segments=inspect(target);load=[s for s in segments if s['file_bytes']];low=min(s['address'] for s in load);high=max(s['address']+s['file_bytes'] for s in load);reconstructed=bytearray(high-low)
        for s in load:reconstructed[s['address']-low:s['address']-low+s['file_bytes']]=s['payload']
        assert bytes(reconstructed)==raw.read_bytes();text=sections['.text']['data'];identity=[fnv_words(text[:len(text)&~3]),len(text)&~3];address=symbols['_re4dc_image_id'][0];found=False
        for s in sections.values():
            if s['type']==1 and s['address']<=address<s['address']+s['bytes']:assert list(struct.unpack_from('<2I',s['data'],address-s['address']))==identity;found=True
        assert found and identity!=plan['canonical']['image_id_words'];overlays=[]
        for ov in plan['overlays14']:
            p=B/'out'/ov['output'];blob=p.read_bytes();h=struct.unpack_from('<16I',blob);assert h[:2]==(0x4f344552,1) and list(h[14:])==identity and h[4]==int(ov['address'],16)
            assert len(blob)==64+h[2]+4*h[3] and len(blob)<=ov['original_slot_bytes'] and h[2]%4==0
            payload=blob[64:64+h[2]];relocs=blob[64+h[2]:];assert fnv_words(payload)==h[12] and fnv_words(relocs)==h[13] and all(v<=h[2] for v in h[5:12]);offsets=[v for(v,) in struct.iter_unpack('<I',relocs)]
            assert offsets==sorted(set(offsets)) and all(v%4==0 and v<h[2] for v in offsets) and all(h[4]<=struct.unpack_from('<I',payload,v)[0]<=h[4]+h[2] for v in offsets)
            overlays.append(dict(name=p.name,bytes=len(blob),sha256=sha(p),header=list(h),original_slot_bytes=ov['original_slot_bytes'],new_image_ID_exact=True,all_relocations_in_section=True))
        assert len(overlays)==14 and not any(n.startswith('.ovl_') for n in sections) and not any((B/'temp').iterdir())
        run('driver-post',command+['-###'],30,2*1024**2,True)
        assert (B/'driver-pre-environment.json').read_bytes()==(B/'driver-post-environment.json').read_bytes()
        assert compare_driver(gzip.decompress((B/'driver-pre.log.gz').read_bytes()),gzip.decompress((B/'driver-post.log.gz').read_bytes()),B/'temp');pins()
        oldsections,oldsymbols,_=inspect(CAN/'out/re4dc-game.elf');a,z=allocated(sections),allocated(oldsections);end=symbols['_end'][0];charbytes=symbols['__re4dc_char_data_end'][0]-symbols['__re4dc_char_data_base'][0];assert charbytes==491520
        assert 0x8c010000<=low<=high<=0x8d000000 and low<=end<=0x8d000000,'actual programme RAM/end/tail bound'
        # Old reference image is unavailable and unnecessary for this link-only unit.
        emit(E/'old-PVD-reference.json',dict(status='OLD_REFERENCE_UNAVAILABLE_NOT_ASSESSED',old_reference_available=False,old_reference_assessed=False,new_scrambled_bytes=scrambled.stat().st_size,new_image_created=False,fresh_image_PVD_required=True,limit='Old reference unavailable/not assessed; fresh image PVD and actual growth admission remain required.'))
        result=dict(status='PASS_PRIVATE_ALLOCATED_PROGRAMME_LINK_ONLY',source=SOURCE,preparation=proposal['preparation'],allocation_sha256=sha(AL),programme=dict(path=str(raw),sha256=sha(raw),bytes=raw.stat().st_size),scrambled_boot=dict(path=str(scrambled),sha256=sha(scrambled),bytes=scrambled.stat().st_size,descramble_roundtrip_exact=True),ELF=dict(path=str(target),sha256=sha(target),bytes=target.stat().st_size),image_ID=identity,image_ID_address=address,overlays=overlays,actual447slots=True,all14_newELF_bound=True,all15_qualified=True,raw_PT_LOAD_exact=True,allocated=a,allocated_delta_vs69f={k:a[k]-z[k] for k in a},end=end,end_delta_vs69f=end-oldsymbols['_end'][0],load_tail=high,raw_span=high-low,bss_start=symbols['__bss_start'][0],char_data_reservation_bytes=charbytes,stack_reference=proposal['qualified_inputs'],all_input_source_header_implicit_archive_env_absence_prepost_exact=True,driver_expansion_prepost_exact=True,one_derivation_onebase14shiftlinks=True,no_stage_image_guest=True,new_ELF_ABI_rebind_required=True,limits=['Source/link checks only; no target draw/LOD/look/phase/performance/release/physical acceptance.','Fresh actual ELF/DWARF observer/policy/scene binding required. No old69f memory/state transfer.'])
        for name,args in [('sections',['readelf','-SW']),('segments',['readelf','-lW']),('symbols',['nm','-n','-S']),('size',['size'])]:
            data=run('inspect-'+name,[str(TOOL/('sh-elf-'+args[0])),*args[1:],str(target)],30,2*1024**2);write(E/(name+'.txt.gz'),gzip.compress(data,mtime=0))
        assert len(gate.records)==len(bridge_plan['order'])==41
        emit(E/'fresh-unit-tool-postpins.json',gate.pure_post())
        result['all41_actual_exec_open_traces_qualified']=True
        result['actual_resolved_full_tool_plugin_loader_prepost']=True
        emit(E/'qualification.json',result);emit(E/'post-input-pins.json',list(expected.values()));emit(E/'process-closeout.json',dict(owned=owned,all_children_exited=True,one_slot=True,one_child_at_a_time=True))
        for p in sorted((B/'out').iterdir()):
            assert p.is_file();guard(p.stat().st_size+65536);shutil.copyfile(p,E/p.name);assert sha(p)==sha(E/p.name)
        for tracefile in sorted(B.glob('*trace-contract.json.gz'))+sorted(B.glob('*.strace.gz')):
            guard(tracefile.stat().st_size+65536);shutil.copyfile(tracefile,E/tracefile.name);assert sha(tracefile)==sha(E/tracefile.name)
        write(E/'controller.py',this.read_bytes());pins();guard();emit(E/'resource-final.json',dict(aggregate_new_bytes=used(),peak_new_bytes=peak,limit=MAX,auxiliary_charge=AUX,minimum_C_free=minimum_free,floor=FLOOR,one_unit_no_retry=True,temp_empty=True,all_final_mirrors_exact=True))
        finalfiles=sorted(p for p in E.iterdir() if p.is_file() and p.name!='SHA256SUMS.txt');write(E/'SHA256SUMS.txt',''.join(sha(p)+'  '+p.name+chr(10) for p in finalfiles).encode())
        print(json.dumps(dict(COMPLETE=True,raw=result['programme'],scrambled=result['scrambled_boot'],ELF=result['ELF'],image_ID=identity,aggregate=used(),peak=peak,seal=sha(E/'SHA256SUMS.txt'))),flush=True)
    except BaseException as error:
        try:emit(E/'FAILED.json',dict(error=repr(error),aggregate=used(),peak=peak,steps=steps,source=SOURCE,preserve_outputs=True,no_automatic_retry=True))
        except BaseException:pass
        print('FAILED '+repr(error),flush=True);raise

if __name__=='__main__':
    main()