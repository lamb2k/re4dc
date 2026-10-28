#!/usr/bin/env python3
"""Bounded SH-4 cost of the exact Build33 final-header receipt helper.

This measures the new guard's CPU overhead with Make-derived native_ui flags.
It does not price removed TA transfers, KOS calls, texture work, geometry or a
whole game frame. Warm/cold-I models assume perfect D-cache; reported 32-byte
data lines are address footprints, not measured cache misses.
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


controls = module('header33_controls', HERE / 'build_controls.py')
profile = controls.profile
cost = module('header33_machine', HERE.parent / 'build29/light_cost.py')
kernel = cost.kernel
LAYOUT = ('version', 'run_bytes', 'stats_bytes', 'header_bytes')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('output', 'sh4-cxx', 'kos-root', 'sdk-root'):
        parser.add_argument('--' + name, required=True, type=Path)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    cxx, kos, sdk = args.sh4_cxx.resolve(), args.kos_root.resolve(), args.sdk_root.resolve()
    helper = DC / 'game/platform/include/static_obj_batch33.hpp'
    files = [Path(__file__), HERE / 'header_cost_fixture.cpp.in', HERE / 'build_controls.py', helper,
             DC / 'game/platform/native_ui.cpp', DC / 'game/model_bridge.cpp']
    frozen = {str(p.relative_to(ROOT)): profile.sha(p) for p in files}
    options = controls.QA + ['STATIC_OBJ_BATCH33=1', 'DRAW_FALLBACK_AUDIT=0', 'DRAW_SETUP_AUDIT=0', 'QA_LINK=0']
    profile.UNITS.update({name: tuple(value) for name, value in controls.DEFAULT['units'].items()})
    flags, receipt, _ = profile.derive(out / 'profile', cxx, kos, sdk, options, units=('native_ui',))
    builder = profile.Build(out)
    cpp, obj, elf = out / 'fixture.cpp', out / 'fixture.o', out / 'fixture.elf'
    cpp.write_text((HERE / 'header_cost_fixture.cpp.in').read_text().replace('@HEADER@', str(helper)))
    builder.run([*flags['native_ui'], '-fstack-usage', '-c', cpp, '-o', obj], label='fixture')
    script = out / 'fixture.ld'
    script.write_text('SECTIONS { /DISCARD/ : { *(.ctors*) *(.dtors*) *(.init_array*) *(.fini_array*) } '
        '. = 0x100000; .text : { *(.text*) } .rodata : { *(.rodata*) } .data : { *(.data*) } .bss : { *(.bss*) *(COMMON) } }\n')
    roots = ('fixture_prepare', 'fixture_begin', 'fixture_finish', 'fixture_sequence', 'fixture_layout')
    builder.run([cxx, '-m4-single', '-ml', '-nostartfiles', '-Wl,--gc-sections', '-Wl,-T,' + str(script),
        '-Wl,-e,_fixture_begin', *['-Wl,-u,_' + name for name in roots], obj, '-o', elf], label='link')
    prefix = str(cxx).removesuffix('g++')
    (out / 'disassembly.txt').write_bytes(builder.run([prefix + 'objdump', '-d', '-C', elf], label='disassembly'))
    program, symbols = kernel.target_machine.scalar.load_elf(elf)
    model = kernel.pipeline_cost.Model(out / 'model', elf)

    def machine():
        value = cost.previous.Machine()
        for address, data, _ in program:
            value.map(address, data)
        return value

    seed = machine()
    layout = dict(zip(LAYOUT, struct.unpack('<' + 'I' * len(LAYOUT),
        seed.bytes_at(symbols['_fixture_layout'][0], 4 * len(LAYOUT)))))
    cases = []
    work = [('begin-first', 0, 'begin', 0, 0), ('begin-reuse', 1, 'begin', 0, 1),
            ('begin-header', 2, 'begin', 0, 5), ('begin-frame', 3, 'begin', 0, 4),
            ('begin-foreign-bytes', 4, 'begin', 0, 4), ('begin-unmarked', 5, 'begin', 0, 2),
            ('begin-unsupported-format', 6, 'begin', 0, 3),
            ('finish-first', 0, 'finish', 3, 1), ('finish-reuse', 1, 'finish', 3, 1),
            ('finish-incomplete-strip', 7, 'finish', 3, 0), ('finish-empty', 1, 'finish', 0, 0),
            ('sequence-singles-12', 0, 'sequence', 12, 11), ('sequence-over16-65', 0, 'sequence', 65, 64),
            ('sequence-same-200', 0, 'sequence', 200, 199),
            ('sequence-alternating-200', 0, 'sequence', (1 << 16) | 200, 0)]
    for name, config, phase, argument, expected in work:
        m = machine()
        m.execute(symbols['_fixture_prepare'][0], config)
        if phase == 'finish':
            m.execute(symbols['_fixture_begin'][0], 0)
        m.minimum_sp = m.reg[15]
        m.observe_start()
        m.execute(symbols['_fixture_' + phase][0], argument)
        m.observe_stop()
        assert m.reg[0] == expected, (name, m.reg[0], expected)
        trace = SimpleNamespace(instruction_pcs=list(m.instruction_pcs), steps=m.steps, read=m.read)
        cases.append(dict(case=name, result=m.reg[0], instructions=m.steps,
            peak_stack_bytes=m.initial_regs[15] - m.minimum_sp,
            traffic=kernel.traffic_details(m.memory_events, m.prefetch_events),
            **kernel.price_helpers.price(model, name, trace)))
        print('PASS', name, flush=True)
    assert frozen == {name: profile.sha(ROOT / name) for name in frozen}, 'source changed during cost gate'
    by = {row['case']: row for row in cases}
    report = dict(status='PASS', scope=__doc__, source_sha256=frozen, options=options,
        profile_receipt=receipt, layout=layout, cases=cases, fixture_sections=profile.sections(elf),
        fixture_sha256=profile.sha(elf), local_frames=profile.stack_usage(obj.with_suffix('.su')),
        kernel_symbols={name: dict(address=symbols['_' + name][0], bytes=symbols['_' + name][1]) for name in roots},
        model=model.metadata(),
        scenario=dict(label='MODELLED', cpu_mhz=200, assumed_other_ms=30, parts=200, vertices_per_part=3,
            helper_only_frame_ms={name: 30 + by['sequence-' + name + '-200']['model_cycles'] / 200000
                                  for name in ('same', 'alternating')},
            same_header_bytes_removed=199 * 32,
            note='Added guard cost only; removed TA transfers are unpriced. The 30 ms term is an explicit sensitivity assumption. '
                 'This is neither a measured frame nor a net performance or FPS prediction. Cold-I cases are isolated, not additive.'),
        limitations='Excludes UI wrapper counters/barriers, header construction, texture pinning, KOS locks/waits, SQ transfers, '
                    'source bridge, transformation/lighting, D-cache misses and GPU. Existing vertices/locks are unchanged. '
                    'Private asset coverage and a console matched A/B remain required.')
    (out / 'header-cost.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(status='PASS', cases=len(cases), layout=layout)))


if __name__ == '__main__':
    main()
