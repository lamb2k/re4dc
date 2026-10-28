#!/usr/bin/env python3
"""Bounded SH-4 costs for current-source UV validation, admission and packing.

The complete production actor TU uses Make-derived flags, and the fixture
retains its actual checked_certificate, pack_uv16 and uv_decide helpers. Costs are added
CPU work relative to UV32, which has no pack loop. Cold-I is one isolated
initially cold 8 KiB instruction cache with perfect D-cache. Reported 32-byte
data lines are address footprints, not measured cache misses. No GPU saving
or whole-actor gain is inferred from PVR internal 24-to-20-byte vertex fields.
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


controls = module('uv32_controls', HERE / 'build_controls.py')
profile = controls.profile
cost = module('uv32_machine', HERE.parent / 'build29/light_cost.py')
kernel = cost.kernel
LAYOUT = ('version', 'cache', 'vertex_bytes', 'binding_fixture_bytes',
          'stream', 'source_uv', 'scanned_records')


class Machine(cost.previous.Machine):
    def step(self, pc, delay=False):
        if self.fetch(pc) == 0x0019:
            # Reuse Build13 target_cost.py's qualified DIV0U semantics:
            # Renesas SH-4 Software Manual 9.18, M/Q/T clear. The compiler's
            # division by record stride takes its small-divisor path; DIV1
            # remains unsupported and fails closed if that premise changes.
            self.sr &= ~0x301
            self.t = 0
            self.instruction_pcs.append(pc)
            self.steps += 1
            return pc + 2
        return super().step(pc, delay)


def division_controls():
    for bits in range(8):
        value = Machine()
        value.map(0x100000, struct.pack('<H', 0x0019))
        value.sr = 0x700080f2 | ((bits & 1) << 9) | ((bits & 2) << 7) | ((bits & 4) >> 2)
        value.t = (bits >> 2) & 1
        sr, regs, fp = value.sr, list(value.reg), [list(x) for x in value.fp]
        other = value.pr, value.fpul, value.mach, value.macl
        value.observe_start()
        pc = value.step(0x100000)
        value.observe_stop()
        assert pc == 0x100002 and value.steps == 1 and value.instruction_pcs == [0x100000]
        assert value.sr == sr & ~0x301 and value.t == 0 and value.reg == regs and value.fp == fp
        assert (value.pr, value.fpul, value.mach, value.macl) == other and not value.memory_events
    return dict(status='PASS', cases=8, opcode='DIV0U 0x0019',
        reused_from='port/dreamcast/tools/cloud/build13/target_cost.py',
        scope='All M/Q/T inputs; preserves remaining state; one instruction; no data traffic; DIV1 unsupported.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('output', 'sh4-cxx', 'kos-root', 'sdk-root'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    cxx, kos, sdk = args.sh4_cxx.resolve(), args.kos_root.resolve(), args.sdk_root.resolve()
    actor = DC / 'game/platform/native_actor_fast.cpp'
    helper = DC / 'game/platform/include/actor_format32_uv.hpp'
    files = [Path(__file__), HERE / 'uv16_cost_fixture.cpp.in', helper, actor,
             DC / 'game/platform/include/actor_format32_uv_source.inc']
    frozen = {str(path.relative_to(ROOT)): profile.sha(path) for path in files}
    options = controls.QA + ['ACTOR_LIGHT_FAST_ONLY=1', 'ACTOR_BACKFACE=0', 'ACTOR_BACKFACE_CONE=1',
        'ACTOR_FORMAT32=1', 'NATIVE_ACTOR_UV16=1', 'ACTOR_MOVCA=0', 'LEON_NATIVE_PIPE=0',
        'COARSE_ONE_SUBMIT=1', 'DRAW_FALLBACK_AUDIT=0', 'DRAW_SETUP_AUDIT=0', 'QA_LINK=0']
    flags, receipt, _ = profile.derive(out / 'profile', cxx, kos, sdk, options, units=('native_actor_fast',))
    builder = profile.Build(out)
    for value in flags['native_actor_fast']:
        if value.endswith('/koscache-p2/require_p2.h'):
            target = Path(value).parent
            if not target.exists():
                prepared = out / 'cache-header'
                builder.run([sys.executable, DC / 'tools/d367/kos_cache_audit/prepare.py',
                    '--kos-root', kos, '--output', prepared, '--patch', DC / 'patches/kos-804b319-cache-p2.patch'],
                    label='prepare-cache')
                shutil.copytree(prepared, target)
    cpp, obj, elf = out / 'fixture.cpp', out / 'fixture.o', out / 'fixture.elf'
    cpp.write_text('#include "' + str(actor) + '"\n' + (HERE / 'uv16_cost_fixture.cpp.in').read_text())
    builder.run([*flags['native_actor_fast'], '-fstack-usage', '-c', cpp, '-o', obj], label='fixture')
    script = out / 'fixture.ld'
    # The established instruction-cache model uses a low code map. Source
    # arrays use real cached SH-4 RAM addresses so production ram() executes.
    script.write_text('PHDRS { code PT_LOAD FLAGS(5); data PT_LOAD FLAGS(6); } '
        'SECTIONS { /DISCARD/ : { *(.ctors*) *(.dtors*) *(.init_array*) *(.fini_array*) } '
        '. = 0x100000; .text : { *(.text*) } :code .rodata : { *(.rodata*) } :code '
        '. = 0x8c100000; .data : { *(.data*) } :data .bss : { *(.bss*) *(COMMON) } :data }\n')
    roots = ('fixture_prepare', 'fixture_decide', 'fixture_source', 'fixture_checked_decide',
             'fixture_pack_cache', 'fixture_pack_clip', 'fixture_layout')
    builder.run([cxx, '-m4-single', '-ml', '-nostartfiles', '-Wl,--gc-sections', '-Wl,-T,' + str(script),
        '-Wl,-e,_fixture_decide', *['-Wl,-u,_' + name for name in roots], obj, '-lm', '-o', elf], label='link')
    prefix = str(cxx).removesuffix('g++')
    (out / 'disassembly.txt').write_bytes(builder.run([prefix + 'objdump', '-d', '-C', elf], label='disassembly'))
    program, symbols = kernel.target_machine.scalar.load_elf(elf)
    # The shared loader intentionally admits only its low instruction map.
    # Add the ELF's bounded RAM data segment without relocating instructions
    # or overriding the production ram() check.
    binary = elf.read_bytes()
    phoff = struct.unpack_from('<I', binary, 28)[0]
    phsize, phnum = struct.unpack_from('<HH', binary, 42)
    for i in range(phnum):
        kind, offset, address, _, filesz, memsz, access, _ = struct.unpack_from('<8I', binary, phoff + i * phsize)
        if kind == 1 and 0x8c000000 <= address < 0x8d000000:
            assert access == 6 and filesz <= memsz <= 1024 * 1024 and address + memsz <= 0x8d000000
            assert offset + filesz <= len(binary)
            program.append((address, binary[offset:offset + filesz] + bytes(memsz - filesz), access))
    model = kernel.pipeline_cost.Model(out / 'model', elf)

    def machine():
        value = Machine()
        for address, data, _ in program:
            value.map(address, data)
        return value

    seed = machine()
    layout = dict(zip(LAYOUT, struct.unpack('<' + 'I' * len(LAYOUT),
        seed.bytes_at(symbols['_fixture_layout'][0], 4 * len(LAYOUT)))))
    assert layout['vertex_bytes'] == 32
    work = [('admit-256', 0, 'decide', 0, 0), ('decline-1024', 1, 'decide', 0, 3),
            ('decline-legacy', 2, 'decide', 0, 1), ('decline-binding', 3, 'decide', 0, 2),
            ('decline-nonfinite', 4, 'decide', 0, 4), ('admit-native-scale', 5, 'decide', 0, 0),
            ('admit-scroll-64', 6, 'decide', 0, 0), ('decline-raw1036', 7, 'decide', 0, 3)]
    work += [(f'pack-cache-{n}', 0, 'pack_cache', n, n) for n in (1, 32, 128)]
    work += [(f'pack-clip-{n}', 0, 'pack_clip', n, n) for n in (3, 6)]
    work += [(f'source-{n}', n << 8, 'source', 0, 23) for n in (1, 32, 128)]
    work += [('source-legacy', 2, 'source', 0, 1),
             ('source-mutated-first', 8, 'source', 0, 32),
             ('source-mutated-last', 9, 'source', 0, 32),
             ('source-signedness-flip', 10, 'source', 0, 32),
             ('source-record-range', 11, 'source', 0, 32),
             ('source-admit-128', 128 << 8, 'checked_decide', 0, 0)]
    cases = []
    for name, config, phase, argument, expected in work:
        value = machine()
        value.execute(symbols['_fixture_prepare'][0], config)
        before = value.bytes_at(layout['cache'], 128 * 32)
        value.minimum_sp = value.reg[15]
        value.observe_start()
        value.execute(symbols['_fixture_' + phase][0], argument)
        value.observe_stop()
        assert value.reg[0] == expected, (name, value.reg[0], expected)
        if phase.startswith('pack_'):
            after = value.bytes_at(layout['cache'], 128 * 32)
            for i in range(128):
                old = list(struct.unpack_from('<8I', before, i * 32))
                actual = list(struct.unpack_from('<8I', after, i * 32))
                if i < argument:
                    u, v = old[4], old[5]
                    if phase == 'pack_cache':
                        old[7] = u
                    old[4] = (((u + 0x8000) & 0xffff0000) | (((v + 0x8000) & 0xffffffff) >> 16))
                assert actual == old, (name, i, actual, old)
        trace = SimpleNamespace(instruction_pcs=list(value.instruction_pcs), steps=value.steps, read=value.read)
        traffic = kernel.traffic_details(value.memory_events, value.prefetch_events)
        traffic['scope'] = ('Actual opcode operand accesses; source/cache/globals use cached SH-4 RAM addresses, '
            'code/literals and the interpreter stack use the established low synthetic map. Instruction fetches '
            'are excluded; PC-relative literals count as data. Distinct 32-byte lines are address footprints, '
            'not measured cache fills or hardware bus transactions.')
        regions = traffic.get('regions', {})
        if 'literal_or_table' in regions:
            regions['source_cache_globals_or_literals'] = regions.pop('literal_or_table')
        cases.append(dict(case=name, result=value.reg[0], instructions=value.steps,
            peak_stack_bytes=value.initial_regs[15] - value.minimum_sp,
            source_records_scanned=value.read(layout['scanned_records'],4),
            traffic=traffic,
            **kernel.price_helpers.price(model, name, trace)))
        print('PASS', name, flush=True)
    assert frozen == {name: profile.sha(ROOT / name) for name in frozen}, 'costed production source changed during gate'
    by = {row['case']: row for row in cases}
    local = [row for row in profile.stack_usage(obj.with_suffix('.su'))
             if any(name in row['function'] for name in ('fixture_', 'uv_axis', 'uv_decide', 'pack_uv16',
                                                          'checked_certificate', 'uv_record_range'))]
    report = dict(status='PASS', scope=__doc__, source_sha256=frozen, options=options,
        division_controls=division_controls(),
        profile_receipt=receipt, layout=layout, cases=cases, fixture_sections=profile.sections(elf),
        fixture_sha256=profile.sha(elf), local_frames=local,
        kernel_symbols={name: dict(address=symbols['_' + name][0], bytes=symbols['_' + name][1]) for name in roots},
        source_helper_symbols={name:dict(address=value[0],bytes=value[1]) for name,value in symbols.items()
            if 'checked_certificate' in name or 'uv_record_range' in name},
        model=model.metadata(), scenario=dict(label='MODELLED', cpu_mhz=200, assumed_other_ms=30,
            assumed_parts=40, assumed_vertices_per_part=128,
            whole_frame_ms=30 + 40 * (by['source-admit-128']['model_cycles'] + by['pack-cache-128']['model_cycles']) / 200000,
            note='Added current-source validation, admission and cache-pack CPU work only; ignores all GPU benefit and any saved geometry.'),
        limitations='Excludes conversion-time certificates, UI binding/handshake, counter logging, window splits and new headers, '
            'clipper interpolation, source transforms/lights, D-cache misses and GPU. Cache and SQ packet remain 32 bytes/vertex. '
            'The PVR internal relevant vertex fields change 24 to 20 bytes; no hardware throughput gain is claimed.')
    (out / 'uv16-cost.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(status='PASS', cases=len(cases), scenario=report['scenario'])))


if __name__ == '__main__':
    main()
