#!/usr/bin/env python3
"""Actual SH4 selection/replay setup plus a bounded 16-byte metadata probe.

The complete native_static.cpp translation unit is compiled with Make-derived
flags. Only emit_pick's geometry body is an observed boundary: transform,
clipping, TA and cache-miss latency are excluded. The separate metadata probe
consumes every logical emit field using the production reader, then writes four
test-only observation words. Its cycles are probe cycles, not renderer time.
Combined metadata lines are the union of actual selector reads and that full
16-byte consumption; they are neither cache fills nor a 43% world-byte saving.
The established Build 5 test-only return stubs/linker layout are reused. No
runtime SH4 assembly or linker change is introduced.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import sys
import zlib

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
ROOT = DC.parents[1]
D367 = DC / 'tools/d367'
SOURCE = DC / 'game/platform/native_static.cpp'


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


sys.path.insert(0, str(D367 / 'world_replay_lean'))
import pipeline_cost
import target_machine
from memory_trace import summarize
old = module('split_cost_replay', D367 / 'world_replay_lean/target_run.py')
prior = module('split_cost_build5', DC / 'tools/cloud/build5/target_cost.py')
profile = prior.profile
generate_fixture = prior.generate_fixture
selection_cases = prior.selection_cases
extractor = prior.check_runtime
sys.path.insert(0, str(DC / 'tools'))
import scenery_record_split as split_tool


class Machine(prior.Machine):
    def step(self,pc,delay=False):
        if self.fetch(pc)==0x0019: # DIV0U: Renesas SH4 manual9.18, M/Q/T=0.
            # GCC's small-stride unsigned division uses this in untimed v4
            # admission. DIV1 remains unsupported/fail-closed. This is an
            # interpreter control, not new target/runtime assembly.
            self.sr&=~0x301;self.t=0
            self.instruction_pcs.append(pc);self.steps+=1
            return pc+2
        return super().step(pc,delay)


def division_init_controls():
    for bits in range(8):
        machine=Machine();machine.map(0x100000,struct.pack('<H',0x0019))
        machine.sr=0x700080f2|((bits&1)<<9)|((bits&2)<<7)|((bits&4)>>2)
        machine.t=(bits>>2)&1
        before_sr=machine.sr;before_regs=list(machine.reg);before_fp=[list(x) for x in machine.fp]
        before_other=(machine.pr,machine.fpul,machine.mach,machine.macl)
        machine.observe_start();next_pc=machine.step(0x100000);traffic=machine.observe_stop()
        assert next_pc==0x100002 and machine.steps==1 and machine.instruction_pcs==[0x100000]
        assert machine.sr==(before_sr&~0x301) and machine.t==0
        assert machine.reg==before_regs and machine.fp==before_fp
        assert (machine.pr,machine.fpul,machine.mach,machine.macl)==before_other
        assert not machine.memory_events and traffic['cached']['unique_data_lines']==0
    return dict(status='PASS',cases=8,opcode='DIV0U 0x0019',
        scope='All M/Q/T inputs, other state preserved, one retired instruction, no data traffic; DIV1 not implemented.',
        manual='https://www.renesas.com/en/document/mas/sh-4-software-manual',section='9.18, printed page238')


def load(path):
    program,symbols=target_machine.scalar.load_elf(path)
    machine=Machine()
    for address,data,_ in program:machine.map(address,data)
    layout=[machine.word(symbols['_fixture_layout'][0]+4*i) for i in range(22)]
    replay=[machine.word(symbols['_fixture_replay_layout'][0]+4*i) for i in range(36)]
    assert layout[:4]==[1,164,252,8] and replay[0]==1
    machine.attach(symbols,replay)
    return machine,symbols,layout


def source_hashes():
    paths = [SOURCE, HERE / 'target_cost.py', HERE / 'cost_fixture.cpp.in',
             DC / 'room/scenery_record_split.hpp', DC / 'tools/scenery_record_split.py',
             *sorted((SOURCE.parent / 'include').glob('scenery_*'))]
    return {str(p.relative_to(ROOT)): profile.sha(p) for p in paths}


def build(args):
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    compiler = args.sh4_cxx.resolve()
    flags, receipt = profile.derive(output / 'release-profile', compiler,
        args.kos_root.resolve(), args.sdk_root.resolve(), cost_dependencies=True)
    builder = profile.Build(output)
    hashes = source_hashes()
    source = SOURCE.read_text()
    emit = extractor.function(source, 'int emit_pick(const Pick& pk){')
    controlled = source.replace(emit,
        'int emit_pick(const Pick& pk){return fixture_emit_control(this,&pk);}')
    modified = output / 'native_static.cpp'
    modified.write_text('extern "C" int fixture_emit_control(void*,const void*);\n' + controlled)
    generated = output / 'selection_fixture.cpp'
    extraction = generate_fixture.generate_source(generated, SOURCE)
    text = generated.read_text().replace(str(SOURCE.resolve()), str(modified))
    text = text.replace('static Re4dcModelPart fixture_part;', '''
extern "C" { unsigned fixture_material_key[4]={0x12345678U,0x87654321U,32,32}; }
static Re4dcModelPart fixture_part;
''')
    original_meta='Ps2Part meta{0x12345678U,0x87654321U,32,32,'
    assert text.count(original_meta)==2
    text=text.replace(original_meta,'Ps2Part meta{fixture_material_key[0],fixture_material_key[1],'
        'std::uint16_t(fixture_material_key[2]),std::uint16_t(fixture_material_key[3]),')
    text = text.replace('static re4dc::room::MeshPackage fixture_package;', '''
#if defined(RE4DC_SCENERY_RECORD_SPLIT) && RE4DC_SCENERY_RECORD_SPLIT
static re4dc::record_split::WorldPackage fixture_package;
#else
static re4dc::room::MeshPackage fixture_package;
#endif
''')
    extra = (HERE / 'cost_fixture.cpp.in').read_text()
    extra = extra.replace('@CHUNK_PART@', extractor.function(source, 'struct ChunkPart {'))
    extra = extra.replace('@CHUNK_FLUSH@', extractor.function(source, 'auto chunk_flush=[&]()->int{'))
    fixture = output / 'target_fixture.cpp'
    fixture.write_text(text + '\n' + extra)
    one = ('fixture_emit_control', 're4dc_model_packet_streaming', 're4dc_ui_frame')
    void = ('mat_load', 're4dc_model_result', 're4dc_model_direct_end',
            're4dc_ps2_world_direct_end_batch', 're4dc_ps2_world_batch_close', 're4dc_model_packet_abort')
    traps = ('re4dc_model_packet_commit', 're4dc_log', 're4dc_missing')
    asm = []
    for name in (*one, *void, *traps):
        symbol = '_' + name
        asm += [f'.section .text.{symbol},"ax"', '.align 1', f'.global {symbol}',
                f'.type {symbol},@function', symbol + ':']
        if name in traps:
            asm += ['trapa #255']
        else:
            if name in one:
                asm += ['mov #1,r0']
            asm += ['rts', 'nop']
        asm += [f'.size {symbol},.-{symbol}']
    for name, value in (('re4dc_screen_wf', 0x44200000), ('re4dc_screen_hf', 0x43f00000),
                        ('re4dc_screen_half_wf', 0x43a00000), ('re4dc_screen_half_hf', 0x43700000)):
        symbol = '_' + name
        asm += [f'.section .data.{symbol},"aw"', '.align 2', f'.global {symbol}',
                f'.type {symbol},@object', symbol + ':', f'.long {value}', f'.size {symbol},4']
    edges = output / 'edges.S'
    edges.write_text('\n'.join(asm) + '\n')
    edge_obj = output / 'edges.o'
    prefix = str(compiler).removesuffix('g++')
    builder.run([prefix + 'gcc', '-m4-single', '-ml', '-c', edges, '-o', edge_obj], label='edges')
    geometry = output / 'pvr_geometry.o'
    builder.run([*flags['pvr_geometry'], '-c', DC / 'room/pvr_geometry.cpp', '-o', geometry], label='geometry')
    linker = output / 'fixture.ld'
    linker.write_text('''SECTIONS {
 /DISCARD/ : { *(.ctors*) *(.dtors*) *(.init_array*) *(.fini_array*) }
 . = 0x100000;
 .text : { *(.text*) }
 .rodata : { *(.rodata*) }
 .data : { *(.data*) }
 .bss : { *(.bss*) *(COMMON) }
}
''')
    roots = ('fixture_layout', 'fixture_adopt', 'fixture_configure', 'fixture_reset',
             'fixture_snapshot', 'fixture_select_full', 'fixture_select_light',
             'fixture_replay_layout', 'fixture_prepare_replay', 'fixture_replay',
             'fixture_metadata_probe', 'fixture_metadata_layout')
    common = ['SCENERY_SELECT_ONLY=1', 'SCENERY_REPLAY_LEAN=1', 'SCENERY_SUBMIT_BATCH=1',
              'SCENERY_UV_SNAPSHOT=1', 'SCENERY_SELECT_LEAN2=1', 'PREF_WALK=0',
              'SCENERY_EMIT_PREFETCH=0', *args.override]
    arms = {}
    for on in (0, 1):
        name = f'q{on}'
        expanded, arm_receipt = profile.expand_existing(output / 'release-profile', compiler,
            args.sdk_root.resolve(), receipt, [*common, f'SCENERY_RECORD_SPLIT={on}'], prefix=name)
        arm_flags = [*expanded['native_static'], '-iquote', str(SOURCE.parent)]
        obj, elf = output / (name + '.o'), output / (name + '.elf')
        builder.run([*arm_flags, '-fstack-usage', '-c', fixture, '-o', obj], label=name)
        builder.run([compiler, '-m4-single', '-ml', '-nostartfiles', '-Wl,--gc-sections',
            '-Wl,-T,' + str(linker), '-Wl,-e,_fixture_replay', *('-Wl,-u,_' + x for x in roots),
            obj, geometry, edge_obj, '-lm', '-o', elf], label=name + '-link')
        (output / (name + '.disassembly.txt')).write_bytes(builder.run(
            [prefix + 'objdump', '-d', '-C', elf], label=name + '-disassembly'))
        arms[name] = dict(elf=str(elf), sha256=profile.sha(elf), object_sha256=profile.sha(obj),
            sections=profile.sections(elf), stack_usage=profile.stack_usage(obj.with_suffix('.su')),
            flags=arm_flags, profile=arm_receipt)
    assert source_hashes() == hashes, 'source changed while building target fixture'
    report = dict(status='PASS', scope=__doc__, base=subprocess.check_output(
        ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(), arms=arms,
        profile=receipt, extraction=extraction, paired_overrides=common,
        emit_pick_replaced_sha256=hashlib.sha256(emit.encode()).hexdigest(),
        source_sha256=hashes, fixture_sha256=profile.sha(fixture))
    (output / 'cost-build.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def canonical_case(case):
    """32-byte-align source-free selector tables; the real split tool follows.

    This does not claim to be the production exporter. The production CLI's
    four-limit fixtures are an additional input set in the same target run.
    """
    old_data = case['package']
    h = list(struct.unpack_from('<4s19I', old_data))
    l = list(struct.unpack_from('<8I', old_data, 80))
    sizes = [(10,h[4],68),(11,h[5],36),(12,h[6],28),(13,h[7],12),
             (14,h[8],1),(15,h[9],4)]
    result = bytearray(112)
    def append(data):
        result.extend(bytes(-len(result) % 32)); offset=len(result)
        result.extend(data); return offset
    for index, count, size in sizes:
        data = bytearray(old_data[h[index]:h[index]+count*size])
        if index == 10:
            for at in range(0,len(data),68):
                data[at+3]=0x50
        h[index]=append(data)
    for index,count,size in ((2,h[5],8),(3,l[0],20),(4,l[1],12)):
        l[index]=append(old_data[l[index]:l[index]+count*size])
    result.extend(bytes(-len(result) % 32))
    h[1]=3;h[2]=len(result);h[3]=0
    struct.pack_into('<4s19I',result,0,*h)
    struct.pack_into('<8I',result,80,*l)
    struct.pack_into('<I',result,12,zlib.crc32(result[80:])&0xffffffff)
    split_tool.Package(result)
    return bytes(result)


def synthetic_cases():
    wanted={'whole-inside','whole-tested','partial-groups','zero-retained-groups-pick',
            'many-meshlets','repeated-plane-cache','scalar-box-fallback'}
    cases=[c for c in selection_cases.cases() if c['name'] in wanted]
    for indexed in (False,True):
        lets=[selection_cases.meshlet() for _ in range(64)]
        package,groups,cones=selection_cases.package([[[(0.,lets)]]],indexed=indexed)
        config=selection_cases.defaults();config['inside']=1
        for pattern,ids in (('dense',list(range(32))),('sparse',list(range(0,64,2))),
                            ('reverse',list(reversed(range(32))))):
            cases.append(dict(name=f"{'indexed' if indexed else 'plain'}-{pattern}-32",
                config=config,package=package,groups=groups,cones=cones,probe_ids=ids))
    return [dict(c,ordinary=canonical_case(c)) for c in cases]


def pack_case(case, package):
    config=selection_cases.input_bytes(case['config'])
    groups=case.get('groups',b'');cones=case.get('cones',b'')
    return struct.pack('<5I',0x31505357,len(config),len(package),len(groups),len(cones))+config+package+groups+cones


def storage(machine,layout,events):
    base=layout[7]
    h=struct.unpack('<4s19I',machine.bytes_at(base,80))
    l=struct.unpack('<8I',machine.bytes_at(base+80,32))
    ranges={'emit':(h[12],h[12]+(16 if h[1]==4 else 28)*h[6])}
    if h[1]==4:ranges['bounds']=(h[17],h[17]+12*h[6])
    ranges.update(parts=(h[11],h[11]+36*h[5]),lod=(l[2],l[2]+8*h[5]),
        clusters=(l[3],l[3]+20*l[0]),levels=(l[4],l[4]+12*l[1]),
        vertices=(h[13],h[13]+12*h[7]),strips=(h[14],h[14]+h[8]))
    result={};metadata=[]
    for name,(lo,hi) in ranges.items():
        selected=[e for e in events if base+lo<=e[3] and e[3]+e[4]<=base+hi]
        result[name]=summarize(selected)
        if name in ('emit','bounds'):metadata.extend(selected)
    result['metadata_union']=summarize(metadata)
    result['all']=summarize(events)
    result['table_offsets']={name:[base+lo,hi-lo] for name,(lo,hi) in ranges.items()}
    result['scope']='Architectural demand accesses; ordinary emit region includes its interleaved bounds. Region line counts can overlap; use metadata_union/all for unions.'
    return result


def production_cases(manifest):
    """Read the real builder sweep's path manifest (schema frozen with it)."""
    values=json.loads(manifest.read_text())
    result=[]
    for entry in values['fixtures']:
        limit=entry['limit'];ordinary=Path(entry['ordinary']).read_bytes()
        split=Path(entry['split']).read_bytes()
        pkg=split_tool.Package(ordinary)
        split_pkg=split_tool.Package(split,allow_split=True)
        split_tool.verify_identity(pkg,split_pkg)
        for file in (Path(entry['ordinary']),Path(entry['split'])):
            assert profile.sha(file)==entry['file_hashes'][file.name],(file,'fixture hash changed')
        group_data=Path(entry['ordinary_groups']).read_bytes()[entry['r4sg_record_offset']:]
        policy=Path(entry['policy']).read_bytes()
        split_tool.validate_groups(Path(entry['ordinary_groups']).read_bytes(),pkg,policy)
        split_groups=Path(entry['split_groups']).read_bytes()
        split_tool.validate_groups(split_groups,split_pkg,policy)
        assert group_data==split_groups[entry['r4sg_record_offset']:],'record split changed group payload'
        for part in range(pkg.h[5]):
            config=selection_cases.defaults()
            material=struct.unpack_from('<IIHHBBBB',policy,32+16*part)
            config.update(part_index=part,inside=1,groups=entry['r4sg_group_count'],
                lod_scale=1.e20,pass_=material[4],cull=material[5],marked=int(bool(material[7]&1)))
            result.append(dict(name=f'exporter-{limit}-part{part}',ordinary=ordinary,split=split,
                groups=group_data,cones=b'',config=config,material_key=material[:4],
                limit=limit,part=part,production=True))
    return result


def run(args):
    output=args.output.resolve();output.mkdir(parents=True,exist_ok=False)
    receipt=json.loads(args.build.read_text())
    assert source_hashes()==receipt['source_sha256'],'target sources changed since build'
    paths={k:Path(v['elf']) for k,v in receipt['arms'].items()}
    machines={k:load(p) for k,p in paths.items()}
    models={k:pipeline_cost.Model(output/('model-'+k),p,args.host_cc) for k,p in paths.items()}
    cases=synthetic_cases()
    if args.fixtures:cases+=production_cases(args.fixtures)
    rows=[]
    for case in cases:
        ordinary=case['ordinary'];split=case.get('split') or split_tool.split_package(ordinary)
        collected={};semantics={};replay_semantics={}
        for arm,elf_key,package in (('ordinary','q0',ordinary),('enabled_fallback','q1',ordinary),('split','q1',split)):
            machine,symbols,layout=machines[elf_key]
            assert profile.sha(paths[elf_key])==receipt['arms'][elf_key]['sha256']
            data=pack_case(case,package)
            machine.map(symbols['_fixture_material_key'][0],struct.pack('<4I',
                *case.get('material_key',(0x12345678,0x87654321,32,32))))
            old.prepare(machine,symbols,layout,data)
            row,trace,semantic=old.selection(machine,symbols,layout,'light')
            row['pipeline']=old.price(models[elf_key],case['name']+'-'+arm+'-select',trace)
            selection_events=list(machine.memory_events)
            row['storage']=storage(machine,layout,selection_events)
            semantics[arm]=semantic
            selected=row['count']
            if 'probe_ids' in case:
                ids=case['probe_ids']
                for i,li in enumerate(ids):machine.map(layout[13]+8*i,struct.pack('<H6B',li,255,0,0,0,0,0))
                selected=len(ids)
            machine.putword(symbols['_fixture_metadata_count'][0],selected)
            probe,trace=old.timed(machine,symbols,'fixture_metadata_probe')
            probe['pipeline']=old.price(models[elf_key],case['name']+'-'+arm+'-metadata',trace)
            probe_events=list(machine.memory_events)
            probe['storage']=storage(machine,layout,probe_events)
            raw=machine.bytes_at(symbols['_fixture_metadata_words'][0],selected*16)
            probe['logical_words_sha256']=hashlib.sha256(raw).hexdigest()
            machine.execute(symbols['_fixture_prepare_replay'][0],1)
            machine.edge_records=[];machine.result_records=[];machine.end_records=[]
            machine.emit_instruction_boundaries=[];machine.streaming_calls=0
            replay,trace=old.timed(machine,symbols,'fixture_replay')
            replay['pipeline']=old.price(models[elf_key],case['name']+'-'+arm+'-replay',trace)
            replay['storage']=storage(machine,layout,list(machine.memory_events))
            assert len(machine.edge_records)==selected,(case['name'],arm,'replay geometry edges')
            assert machine.end_records==([7*selected] if selected else [])
            state=list(struct.unpack('<8I',machine.bytes_at(machine.layout[5],32)))
            assert state[:6]==[1,1,0,0,0,0],state
            replay.update(state=state,geometry_edges=selected)
            replay_semantics[arm]=(state,list(machine.edge_records),list(machine.result_records),
                list(machine.end_records),machine.streaming_calls)
            # Each entry resets the retired-instruction ordinal. Rebase the
            # second trace before summarizing so a selector load and probe
            # load at the same local ordinal remain two instructions.
            probe_base=1+max((e[0] for e in selection_events),default=-1)
            combined_events=selection_events+[(e[0]+probe_base,*e[1:]) for e in probe_events]
            combined=storage(machine,layout,combined_events)
            collected[arm]=dict(selection=row,metadata_probe=probe,replay_setup=replay,
                selection_plus_metadata=combined,selected=selected,package_bytes=len(package))
        assert semantics['ordinary']==semantics['enabled_fallback']==semantics['split'],(case['name'],'selector changed')
        assert replay_semantics['ordinary']==replay_semantics['enabled_fallback']==replay_semantics['split'],(case['name'],'replay inputs/state changed')
        assert len({r['metadata_probe']['logical_words_sha256'] for r in collected.values()})==1,(case['name'],'logical emit fields changed')
        rows.append(dict(name=case['name'],production=case.get('production',False),
            meshlet_limit=case.get('limit'),part=case.get('part'),arms=collected))
        print(json.dumps(dict(name=case['name'],status='PASS')),flush=True)
        (output/'progress.json').write_text(json.dumps(rows,indent=2)+'\n')
    report=dict(status='PASS',scope=__doc__,build=str(args.build.resolve()),build_sha256=profile.sha(args.build),
        source_sha256=receipt['source_sha256'],models={k:v.metadata() for k,v in models.items()},
        memory_controls=target_machine.memory_controls(),division_init_controls=division_init_controls(),rows=rows,
        fixtures_sha256=profile.sha(args.fixtures) if args.fixtures else None,
        whole_frame='See report for explicitly MODELLED setup-only scenario; no geometry, D-cache stalls, console or r101 prediction.')
    (output/'target-costs.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    bp=sub.add_parser('build')
    for flag in ('output','sh4-cxx','kos-root','sdk-root'):bp.add_argument('--'+flag,type=Path,required=True)
    bp.add_argument('--override',action='append',default=[])
    rp=sub.add_parser('run')
    rp.add_argument('--output',type=Path,required=True);rp.add_argument('--build',type=Path,required=True)
    rp.add_argument('--fixtures',type=Path);rp.add_argument('--host-cc',default='gcc')
    args=parser.parse_args();report=build(args) if args.command=='build' else run(args)
    print(json.dumps(dict(status=report['status'],output=str(args.output))))


if __name__=='__main__':main()
