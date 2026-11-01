#!/usr/bin/env python3
"""Bounded SH-4 cost of the actual SCCN/SCPS format-validation helpers.

Uses Make-derived native_static flags and synthetic records produced by the
existing public builder. These are one-time room-open costs, not draw costs.
Warm/cold-I models assume perfect D-cache; reported 32-byte data lines are
address footprints, not measured cache misses. Geometric validity is unproved.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import struct
import sys
from types import SimpleNamespace

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
ROOT = DC.parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


# Build32 reuses Build29's measured-instruction interpreter and adds only its
# qualified DIV0U control. Unsupported instructions still fail closed.
cost = module('scn34_machine', HERE.parent / 'build32/uv16_cost.py')
host = module('scn34_host', HERE / 'scn21_host.py')
profile, kernel = cost.profile, cost.kernel
LAYOUT = ('version', 'section', 'section_bytes', 'words', 'words_bytes')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('output', 'sh4-cxx', 'kos-root', 'sdk-root'):
        parser.add_argument('--' + name, required=True, type=Path)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    cxx, kos, sdk = args.sh4_cxx.resolve(), args.kos_root.resolve(), args.sdk_root.resolve()
    helper = DC / 'game/platform/include/scn21_validate34.hpp'
    files = [Path(__file__), HERE / 'scn21_cost_fixture.cpp.in', HERE / 'scn21_host.py', helper,
             DC / 'game/platform/native_static.cpp', DC / 'game/scenery19.mk', host.BUILDER,
             Path(cost.__file__), Path(profile.__file__)]
    frozen = {str(p.relative_to(ROOT)): profile.sha(p) for p in files}
    options = ['NMR_POOL_LOD=0', 'SCENERY_CONE=1', 'SCENERY_CONE_SIGN=1', 'SCENERY_PIECE_STATE=1',
               'PS2_WORLD_HDR_CACHE=1', 'PS2_PVS_BATCH_COMPOSE=0',
               'DRAW_FALLBACK_AUDIT=0', 'DRAW_SETUP_AUDIT=0', 'QA_LINK=0']
    flags, receipt, _ = profile.derive(out / 'profile', cxx, kos, sdk, options, units=('native_static',))
    builder = profile.Build(out)
    cpp, obj, elf = out / 'fixture.cpp', out / 'fixture.o', out / 'fixture.elf'
    data = host.builder_bytes()
    cpp.write_text((HERE / 'scn21_cost_fixture.cpp.in').read_text()
                   .replace('@HEADER@', str(helper)).replace('@BUILDER_BYTES@', ','.join(map(str, data))))
    builder.run([*flags['native_static'], '-fstack-usage', '-c', cpp, '-o', obj], label='fixture')
    script = out / 'fixture.ld'
    script.write_text('SECTIONS { /DISCARD/ : { *(.ctors*) *(.dtors*) *(.init_array*) *(.fini_array*) } '
        '. = 0x100000; .text : { *(.text*) } .rodata : { *(.rodata*) } .data : { *(.data*) } .bss : { *(.bss*) *(COMMON) } }\n')
    roots = ('fixture_prepare', 'fixture_cone', 'fixture_piece', 'fixture_layout')
    builder.run([cxx, '-m4-single', '-ml', '-nostartfiles', '-Wl,--gc-sections', '-Wl,-T,' + str(script),
        '-Wl,-e,_fixture_cone', *['-Wl,-u,_' + name for name in roots], obj, '-o', elf], label='link')
    prefix = str(cxx).removesuffix('g++')
    (out / 'disassembly.txt').write_bytes(builder.run([prefix + 'objdump', '-d', '-C', elf], label='disassembly'))
    program, symbols = kernel.target_machine.scalar.load_elf(elf)
    model = kernel.pipeline_cost.Model(out / 'model', elf)

    def machine():
        value = cost.Machine()
        for address, content, _ in program:
            value.map(address, content)
        return value

    seed = machine()
    layout = dict(zip(LAYOUT, struct.unpack('<' + 'I' * len(LAYOUT),
        seed.bytes_at(symbols['_fixture_layout'][0], 4 * len(LAYOUT)))))
    cases = []
    work = [('cone-short', 0, 'cone', 0, 0), ('cone-four-records', 1, 'cone', 1, 4),
            ('cone-128-records', 2, 'cone', 1, 128), ('cone-final-index-refusal', 3, 'cone', 0, 128),
            ('piece-128-slots', 4, 'piece', 1, 0), ('piece-short', 5, 'piece', 0, 0),
            ('piece-count-overflow', 6, 'piece', 0, 0), ('cone-stale', 7, 'cone', 0, 0)]
    for name, config, phase, expected, records in work:
        m = machine()
        m.execute(symbols['_fixture_prepare'][0], config)
        before = m.bytes_at(layout['section'], layout['section_bytes'])
        m.minimum_sp = m.reg[15]
        m.observe_start()
        m.execute(symbols['_fixture_' + phase][0], 0)
        m.observe_stop()
        assert m.reg[0] == expected, (name, m.reg[0], expected)
        assert before == m.bytes_at(layout['section'], layout['section_bytes']), 'validation mutated section'
        trace = SimpleNamespace(instruction_pcs=list(m.instruction_pcs), steps=m.steps, read=m.read)
        cases.append(dict(case=name, result=m.reg[0], records=records, instructions=m.steps,
            peak_stack_bytes=m.initial_regs[15] - m.minimum_sp,
            traffic=kernel.traffic_details(m.memory_events, m.prefetch_events),
            **kernel.price_helpers.price(model, name, trace)))
        print('PASS', name, flush=True)
    assert frozen == {name: profile.sha(ROOT / name) for name in frozen}, 'source changed during cost gate'
    report = dict(status='PASS', scope=__doc__, source_sha256=frozen, options=options,
        profile_receipt=receipt, layout=layout, cases=cases, fixture_sections=profile.sections(elf),
        fixture_sha256=profile.sha(elf), local_frames=profile.stack_usage(obj.with_suffix('.su')),
        kernel_symbols={name: dict(address=symbols['_' + name][0], bytes=symbols['_' + name][1]) for name in roots},
        model=model.metadata(), arithmetic_control=cost.division_controls(),
        sensitivity=dict(label='MODELLED', cpu_mhz=200,
            per_room_open_ms={row['case']: row['model_cycles'] / 200000 for row in cases},
            note='Helpers run at section open. Do not multiply by rendered parts or claim a frame gain. Cold-I experiments are isolated, not additive.'),
        limitations='Excludes section I/O, package opening, GC asset auditing, log output, original SCPS slot clearing, '
                    'source geometric certificate validation, runtime cone tests, D-cache misses and GPU work. '
                    'A public synthetic section does not establish private asset safety or console benefit.')
    (out / 'scn21-cost.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(status='PASS', cases=len(cases))))


if __name__ == '__main__':
    main()
