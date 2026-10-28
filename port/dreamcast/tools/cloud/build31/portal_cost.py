#!/usr/bin/env python3
"""Price real SH4 pc::grid_hidden and new portal receipt pieces, synthetic only.

The production native_static translation unit compiles with Make-derived flags.
Only bounded kernels are retained in the fixture ELF. Cold-I means isolated
instruction-cache cold with perfect D-cache; data lines are address footprint,
not measured cache misses. Loader, proof/source scans, setup and GPU omitted.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import shutil
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


controls = module('portal31_controls', HERE / 'build_controls.py')
profile = controls.profile
cost = module('portal31_machine', HERE.parent / 'build29/light_cost.py')
kernel = cost.kernel
LAYOUT = ('version', 'frustum_bytes', 'state_bytes', 'receipts_bytes', 'count', 'tests', 'frustums')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('output', 'sh4-cxx', 'kos-root', 'sdk-root'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    cxx, kos, sdk = args.sh4_cxx.resolve(), args.kos_root.resolve(), args.sdk_root.resolve()
    production = DC / 'game/platform/native_static.cpp'
    files = [Path(__file__), HERE / 'portal_cost_fixture.cpp.in', production,
             DC / 'game/platform/include/world_portal29.hpp',
             DC / 'game/platform/include/world_portal29_cells.inc',
             DC / 'game/platform/include/world_portal29_runtime.inc']
    frozen = {str(p.relative_to(ROOT)): profile.sha(p) for p in files}
    options = controls.QA + controls.PREREQUISITES + [
        'PS2_INTERIOR_CULL=1', 'PS2_PVS=1', 'PS2_PVS_BATCH_COMPOSE=0',
        'SCENERY_SUBMIT_BATCH=0', 'SCENERY_STREAM=0', 'WORLD_PORTAL29=1',
        'WORLD_PART_PLAN29=0', 'DRAW_FALLBACK_AUDIT=0', 'DRAW_SETUP_AUDIT=0', 'QA_LINK=0']
    flags, receipt, sources = profile.derive(out / 'profile', cxx, kos, sdk, options, units=('native_static',))
    builder = profile.Build(out)
    for value in flags['native_static']:
        if value.endswith('/koscache-p2/require_p2.h'):
            target = Path(value).parent
            if not target.exists():
                prepared = out / 'cache-header'
                builder.run([sys.executable, DC / 'tools/d367/kos_cache_audit/prepare.py',
                             '--kos-root', kos, '--output', prepared, '--patch',
                             DC / 'patches/kos-804b319-cache-p2.patch'], label='prepare-cache')
                shutil.copytree(prepared, target)
    cpp, obj, elf = out / 'fixture.cpp', out / 'fixture.o', out / 'fixture.elf'
    cpp.write_text('#include "' + str(production) + '"\n' + (HERE / 'portal_cost_fixture.cpp.in').read_text())
    builder.run([*flags['native_static'], '-fstack-usage', '-c', cpp, '-o', obj], label='fixture')
    script = out / 'fixture.ld'
    script.write_text('SECTIONS { /DISCARD/ : { *(.ctors*) *(.dtors*) *(.init_array*) *(.fini_array*) } '
                      '. = 0x100000; .text : { *(.text*) } .rodata : { *(.rodata*) } '
                      '.data : { *(.data*) } .bss : { *(.bss*) *(COMMON) } }\n')
    roots = ('fixture_prepare', 'fixture_grid', 'fixture_commit', 'fixture_sync_same', 'fixture_sync_new', 'fixture_layout')
    builder.run([cxx, '-m4-single', '-ml', '-nostartfiles', '-Wl,--gc-sections', '-Wl,-T,' + str(script),
                 '-Wl,-e,_fixture_grid', *['-Wl,-u,_' + r for r in roots], obj, '-o', elf], label='link')
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
    work = [('portal1-visible', 0, 'grid', 0, 0), ('portal1-hidden', 2, 'grid', 0, 1),
            ('portal24-hidden', 3, 'grid', 0, 1), ('house-intersection', 4, 'grid', 0, 0xffffffff),
            ('receipt-first', 0, 'commit', 0, 1), ('receipt-last256', 255 << 4, 'commit', 255, 256),
            ('receipt-repeat', 256 << 4, 'commit', 255, 256), ('receipt-same-image', 256 << 4, 'sync_same', 0, 256),
            ('receipt-new-image', 256 << 4, 'sync_new', 0, 0)]
    for name, config, phase, argument, expected in work:
        m = machine()
        m.execute(symbols['_fixture_prepare'][0], config)
        m.minimum_sp = m.reg[15]
        m.observe_start()
        m.execute(symbols['_fixture_' + phase][0], argument)
        m.observe_stop()
        assert m.reg[0] == expected, (name, m.reg[0], expected)
        trace = SimpleNamespace(instruction_pcs=list(m.instruction_pcs), steps=m.steps, read=m.read)
        row = dict(case=name, result=m.reg[0], instructions=m.steps,
                   peak_stack_bytes=m.initial_regs[15] - m.minimum_sp,
                   traffic=kernel.traffic_details(m.memory_events, m.prefetch_events),
                   **kernel.price_helpers.price(model, name, trace))
        cases.append(row)
        print('PASS', name, flush=True)
    assert frozen == {p: profile.sha(ROOT / p) for p in frozen}, 'production source changed during gate'
    report = dict(status='PASS', scope=__doc__, source_sha256=frozen, options=options,
                  profile_receipt=receipt, layout=layout, cases=cases, fixture_sections=profile.sections(elf),
                  fixture_sha256=profile.sha(elf), local_frames=profile.stack_usage(obj.with_suffix('.su')),
                  kernel_symbols={name: dict(address=symbols['_' + name][0], bytes=symbols['_' + name][1])
                                  for name in roots}, model=model.metadata(),
                  limitations='Not full portal runtime or frame. Omits current-source/material proof scans, begin/numeric setup, '
                              'allocator/I/O/geometry savings/GPU/D-cache misses. Same normalized synthetic frustum is repeated '
                              '24 times for the conservative worst admitted count; cold-I not additive as a whole frame.')
    (out / 'portal-cost.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(status='PASS', cases=len(cases), layout=layout)))


if __name__ == '__main__':
    main()
