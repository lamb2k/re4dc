#!/usr/bin/env python3
"""Prepare and build the public EF14 SH-4 executable against pinned sources.

`check-source` needs no SDK. `build` requires a built KOS and the pinned SH4ZAM
checkout; it never substitutes a host implementation of either SH-4 routine.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import shlex
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[5]
BATCH_SOURCE = ROOT / 'port/dreamcast/game/platform/sh4zam_direct.c'
SCALAR_SOURCE = ROOT / 'port/dreamcast/game/platform/mtx_sh4.S'
API_HEADER = ROOT / 'include/re4dc_xm.h'
KOS_PIN = '804b3195ebd1a06a27cc2b3a5eacf7a2429040a3'
SH4ZAM_PIN = '33fa4850cacb30dd0ad35485ef035526ec4ce782'
SOURCE_HEAD = 'bbfd3254fe4d94299a4bdbc869dbae92bb5ff978'
BATCH_HASH = '320be560017cbc2d470af1273b7f735c35486d31a0174c9a57abaabed77cf86f'
SCALAR_HASH = '5772f23246a2570f11a10e4848346509d0525dcb74230cf75fb8086227306996'
API_HASH = 'ba21710229f1233aa597ea30bce98468db10718e07a354be4b5c6db466e1cd37'
GEOMETRY_HASHES = {
    'port/dreamcast/room/pvr_geometry.cpp': '1f3bb880101796e0ecb2ee7ac2dc5c0f3990421c6dc06617f7c86d2a64390136',
    'port/dreamcast/room/pvr_geometry.hpp': '0e7d6a83bff8a5e76794aea8e4da75a7adfc9c497f9b5ccb815a79a4e3d75d3c',
    'port/dreamcast/room/native_draw_plan.hpp': '951dffb90793f7afa8a6191720425ea14c49a65be46bb490bc288a6cf95f9405',
    'port/dreamcast/game/platform/include/native_ui.h': '7490e37bbe989399aa75108cf880027a4943da89ffa4999f272b0eccf4ffb882',
    'port/dreamcast/game/platform/include/cloth_strip_geometry11.hpp': '490b0d8bc3f79284c522721f7ce13ffb20faef67b12cad2d357f71077f0d2b17',
    'port/dreamcast/game/platform/include/effect_strip_geometry21.hpp': 'c86f8f5942f18ecb53c489a6089bd30a4a96c376a120525bd15b180159990481',
    'port/dreamcast/game/platform/include/native_render_profile.hpp': '0776aa713d3e4e0c608b3d847e04b528a60d13005ab72966f91927560f149bf3',
    'port/dreamcast/game/platform/include/re4dc_screen.h': '34688a35cd9592ac9c77f8298ae1ba6cca1f2d51e9de30d27f8c4f532138cb8f',
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def command(args, *, cwd=None, env=None):
    result = subprocess.run([str(x) for x in args], cwd=cwd, env=env,
                            text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(f'command failed ({result.returncode}): {args}\n'
                           f'{result.stdout}{result.stderr}')
    return result.stdout + result.stderr


def exact_slice(source, begin, end=None):
    assert source.count(begin) == 1, f'expected one source anchor: {begin}'
    body = source[source.index(begin):]
    if end is not None:
        assert body.count(end) == 1, f'expected one end anchor: {end}'
        body = body[:body.index(end) + len(end)] + '\n'
    return body


def source_inputs():
    batch = exact_slice(BATCH_SOURCE.read_text(),
                        '#if defined(RE4DC_CLOTH_XM_BATCH14) && RE4DC_CLOTH_XM_BATCH14')
    scalar = exact_slice(SCALAR_SOURCE.read_text(),
                         '        .align  2\n        .global _re4dc_sh4_MTXMultVec\n',
                         '        .size   _re4dc_sh4_MTXMultVec, . - _re4dc_sh4_MTXMultVec')
    assert sha(batch.encode()) == BATCH_HASH, 'production batch changed; review and repin'
    assert sha(scalar.encode()) == SCALAR_HASH, 'production scalar SH-4 body changed; review and repin'
    assert sha(API_HEADER.read_bytes()) == API_HASH, 'public batch API changed; review and repin'
    for name, expected in GEOMETRY_HASHES.items():
        assert sha((ROOT / name).read_bytes()) == expected, f'geometry input changed; review and repin: {name}'
    for name in ('re4dc_zam_xm_points14(', 're4dc_zam_xm_points14_scalar(',
                 'shz_xmtrx_load_rows_3x4(', 'shz_xmtrx_transform_point3('):
        assert name in batch, f'missing actual batch entry/API: {name}'
    return batch, scalar


def git_head(path, expected):
    actual = command(['git', '-C', path, 'rev-parse', 'HEAD']).strip()
    assert actual == expected, f'{path}: expected {expected}, got {actual}'


def validate_sdk(kos, sdk, cxx):
    for path in (kos / 'Makefile.rules', sdk / 'include/sh4zam/shz_xmtrx.h', cxx):
        assert path.is_file(), f'missing pinned build input: {path}'
    git_head(kos, KOS_PIN)
    git_head(sdk, SH4ZAM_PIN)
    assert cxx.name.endswith('-g++'), 'expected the selected SH-4 cross g++ executable'
    prefix = str(cxx).removesuffix('g++')
    for binary in (cxx, Path(prefix + 'gcc')):
        assert binary.is_file(), f'missing compiler: {binary}'
        assert '15.2.0' in command([binary, '--version']).splitlines()[0], 'requires GCC 15.2.0'
        assert 'Thread model: kos' in command([binary, '-v']), 'requires the KOS SH-4 compiler'
    for name in ('ld', 'objdump', 'nm', 'readelf'):
        binary = Path(prefix + name)
        assert binary.is_file(), f'missing binutils tool: {binary}'
        assert '2.45.1' in command([binary, '--version']).splitlines()[0], f'{name} must be 2.45.1'
    newlib = cxx.parent.parent / 'sh-elf/include/_newlib_version.h'
    assert newlib.is_file(), f'missing pinned newlib header: {newlib}'
    assert sha(newlib.read_bytes()) == 'be2a4d2763fd9f409369fc62a741dff6722b71ca56050b7c6469581c81fd2420', \
        'newlib header differs from pinned 4.6.0.20260123 receipt'
    return prefix


def pinned_file(root, relative):
    """A checkout HEAD alone does not identify the bytes used by a build."""
    path = (root / relative).resolve()
    assert path.is_file() and path.is_relative_to(root), f'missing/outside SDK input: {path}'
    expected = command(['git', '-C', root, 'rev-parse', f'HEAD:{relative}']).strip()
    actual = command(['git', '-C', root, 'hash-object', path]).strip()
    assert actual == expected, f'modified pinned SDK input: {path}'
    return sha(path.read_bytes())


def bound_environment(kos, sdk, cxx):
    """Recreate this SDK's environment; never reuse another sourced KOS setup.

    KOS wrappers execute KOS_CC/KOS_CCPLUS, not the first compiler on PATH.
    Their inherited -I/-L/-T flags also survive a mere KOS_BASE reassignment.
    """
    env = os.environ.copy()
    overrides = {'CPATH', 'C_INCLUDE_PATH', 'CPLUS_INCLUDE_PATH', 'OBJC_INCLUDE_PATH',
                 'LIBRARY_PATH', 'COMPILER_PATH', 'GCC_EXEC_PREFIX', 'MAKEFLAGS',
                 'MFLAGS', 'MAKEFILES', 'GNUMAKEFLAGS', 'CFLAGS', 'CXXFLAGS',
                 'CPPFLAGS', 'LDFLAGS', 'BASH_ENV', 'ENV'}
    for name in tuple(env):
        if name.startswith(('KOS_', 'DC_')) or name in overrides:
            del env[name]
    wrappers = kos / 'utils/build_wrappers'
    env.update(KOS_BASE=str(kos), KOS_ARCH='dreamcast', KOS_SUBARCH='pristine',
               KOS_CC_BASE=str(cxx.parent.parent), KOS_CC_PREFIX=cxx.name[:-4],
               KOS_PORTS=str(kos / 'unused-cloth-xm14-ports'),
               KOS_CFLAGS='-O2 -fno-PIC -fno-PIE -fomit-frame-pointer',
               KOS_CPPFLAGS='', KOS_INC_PATHS='', KOS_INC_PATHS_CPP='',
               KOS_LDFLAGS='', KOS_AFLAGS='', KOS_SH4_PRECISION='-m4-single',
               DC_TOOLS_BASE=str(cxx.parent))
    env['PATH'] = os.pathsep.join((str(wrappers), str(cxx.parent), env['PATH']))
    # Only KOS build settings are returned, never the caller's credentials.
    script = ('set -e; . "$1/environ_base.sh" >&2; exec "$2" -c '
              + shlex.quote('import json,os; print(json.dumps({k:v for k,v in '
                            'os.environ.items() if k.startswith("KOS_")}))'))
    result = subprocess.run(['bash', '-c', script, 'cloth-xm14-sdk', str(kos), sys.executable],
                            env=env, text=True, capture_output=True)
    assert result.returncode == 0, f'pinned KOS environment failed: {result.stderr}'
    env.update(json.loads(result.stdout))
    assert Path(env['KOS_CC']).resolve() == Path(str(cxx).removesuffix('g++') + 'gcc').resolve(), \
        'KOS C compiler does not match --sh4-cxx'
    assert Path(env['KOS_CCPLUS']).resolve() == cxx, 'KOS C++ compiler does not match --sh4-cxx'
    # This fixture needs no kos-ports inputs. Remove even the unused search path.
    for key in ('KOS_INC_PATHS', 'KOS_CFLAGS', 'KOS_LIB_PATHS', 'KOS_LDFLAGS'):
        env[key] = env[key].replace(' -isystem ' + env['KOS_PORTS'] + '/include', '')
        env[key] = env[key].replace(' -L' + env['KOS_PORTS'] + '/lib', '')
    env['KOS_WRAPPERS_VERBOSE'] = '1'
    for name in ('kos-cc', 'kos-c++'):
        expected = (wrappers / name).resolve()
        actual = shutil.which(name, path=env['PATH'])
        assert actual and Path(actual).resolve() == expected, f'wrong KOS wrapper: {name}'
    return env


def binding_inputs(kos, sdk, cxx):
    paths = [kos / 'utils/build_wrappers/kos-cc', kos / 'utils/build_wrappers/kos-c++',
             kos / 'environ_base.sh', kos / 'environ_dreamcast.sh',
             kos / 'Makefile.rules', kos / 'utils/ldscripts/shlelf.xc']
    source_hashes = {str(path.relative_to(kos)): pinned_file(kos, path.relative_to(kos))
                     for path in paths}
    # Pin the source contract whose actual linked implementation is exercised.
    for relative in ('kernel/arch/dreamcast/kernel/entry.s',
                     'kernel/arch/dreamcast/kernel/timer.c',
                     'kernel/arch/dreamcast/kernel/irq.c'):
        source_hashes[relative] = pinned_file(kos, relative)
    inputs = [cxx, Path(str(cxx).removesuffix('g++') + 'gcc'),
              kos / 'lib/dreamcast/libkallisti.a', kos / 'lib/dreamcast/_kos_startup.o',
              kos / 'utils/ldscripts/shlelf.xc']
    for path in inputs:
        assert path.is_file(), f'missing built SDK input: {path}'
        assert path.resolve().is_relative_to(kos if path.is_relative_to(kos) else cxx.parent.parent), \
            f'build input resolves outside selected SDK: {path}'
    return dict(version='bound-kos-v1', kos_sources_sha256=source_hashes,
                input_sha256={str(path.resolve()): sha(path.read_bytes()) for path in inputs})


def effective_defines(body):
    values = dict(re.findall(r'^#define (\w+) (.*)$', body, re.MULTILINE))
    for name in ('__sh__', '__SH4_SINGLE__', '__LITTLE_ENDIAN__', '__DREAMCAST__',
                 '_arch_dreamcast', '_arch_sub_pristine',
                 'RE4DC_CLOTH_XM_BATCH14', 'RE4DC_FX_STRIP21'):
        assert values.get(name) == '1', f'effective target define missing/wrong: {name}'
    assert '__FAST_MATH__' not in values and values.get('__FINITE_MATH_ONLY__') == '0', \
        'unsafe effective floating-point compile mode'
    assert '__SH4_SINGLE_ONLY__' not in values and '__BIG_ENDIAN__' not in values, \
        'incompatible effective SH-4 ABI'
    return values


def verify_dependencies(out, kos, sdk, cxx):
    dependencies = set()
    for path in out.glob('*.o.d'):
        body = path.read_text().replace('\\\n', ' ')
        assert ':' in body, f'malformed compiler dependency evidence: {path}'
        dependencies.update(Path(name).resolve() for name in shlex.split(body.split(':', 1)[1]))
    required = {kos / 'include/kos.h', kos / 'include/kos/irq.h',
                kos / 'kernel/arch/dreamcast/include/arch/irq.h',
                kos / 'kernel/arch/dreamcast/include/arch/timer.h',
                sdk / 'include/sh4zam/shz_xmtrx.h'}
    assert required <= dependencies, 'actual compiler dependencies do not bind the selected SDK headers'
    hashes = {}
    for path in sorted(dependencies):
        assert any(path.is_relative_to(root) for root in (ROOT, out, kos, sdk, cxx.parent.parent)), \
            f'compiler consumed an input outside selected roots: {path}'
        for root in (kos, sdk):
            if path.is_relative_to(root):
                hashes[str(path)] = pinned_file(root, path.relative_to(root))
    return hashes


def verify_link_inputs(body, out, kos, cxx, binding):
    paths = {Path(name).resolve() for name in re.findall(r'^LOAD (.+)$', body, re.MULTILINE)}
    required = {kos / 'lib/dreamcast/libkallisti.a', kos / 'lib/dreamcast/_kos_startup.o'}
    assert required <= paths, 'link map does not bind the selected KOS archive/startup'
    for path in paths:
        assert path.is_file() and any(path.is_relative_to(root) for root in
                                     (out, kos, cxx.parent.parent)), \
            f'linker consumed an input outside selected roots: {path}'
    for name, expected in binding['input_sha256'].items():
        assert sha(Path(name).read_bytes()) == expected, f'SDK input changed during build: {name}'
    return {str(path): sha(path.read_bytes()) for path in sorted(paths)}


def ftrv_offsets(disassembly):
    """Bind IRQ evidence to actual linked FTRV instruction boundaries."""
    symbol = re.search(r'^\s*([0-9a-f]+) <_re4dc_zam_xm_points14>:',
                       disassembly, re.MULTILINE)
    assert symbol, 'missing production batch disassembly symbol'
    start = int(symbol[1], 16)
    offsets = [int(match[1], 16) - start for match in re.finditer(
        r'^\s*([0-9a-f]+):\s+(?:[0-9a-f]{2,4}\s+)+ftrv\b',
        disassembly, re.MULTILINE)]
    assert offsets and all(0 <= value < 0x10000 and value % 2 == 0 for value in offsets), \
        'missing or invalid FTRV instruction offsets'
    return offsets


def build(args, batch, scalar):
    kos, sdk, cxx, out = (p.resolve() for p in
                           (args.kos_root, args.sdk_root, args.sh4_cxx, args.output))
    for path in (kos, sdk, cxx, out, ROOT, HERE):
        assert re.fullmatch(r'[A-Za-z0-9_./+-]+', str(path)), \
            f'KOS wrapper/Make paths must use plain shell-safe characters: {path}'
    prefix = validate_sdk(kos, sdk, cxx)
    binding = binding_inputs(kos, sdk, cxx)
    env = bound_environment(kos, sdk, cxx)
    assert not out.exists(), f'output already exists: {out}'
    out.mkdir(parents=True)
    generated_c = ('#include <stdint.h>\n#include <sh4zam/shz_xmtrx.h>\n'
                   '#include <sh4zam/shz_vector.h>\n#include <sh4zam/shz_scalar.h>\n'
                   '#include <sh4zam/shz_trig.h>\n'
                   'typedef struct { float x, y, z; } zvec_t;\n' + batch)
    (out / 'production_batch.c').write_text(generated_c)
    (out / 'production_scalar.S').write_text('        .text\n' + scalar)
    # Include only the pinned public batch API. Adding the recovered game's
    # entire include/ directory shadows standard C++ <new> in the KOS fixture.
    (out / 're4dc_xm.h').write_bytes(API_HEADER.read_bytes())
    (out / 'sdk_probe.cpp').write_text('#include <kos.h>\n#include <arch/irq.h>\n'
                                     '#include <arch/timer.h>\n#include <sh4zam/shz_xmtrx.h>\n')
    make = ['make', '--no-print-directory', '-f', HERE / 'cloth_xm14_target.mk',
            f'KOS_BASE={kos}', f'SH4ZAM_DIR={sdk}', f'SOURCE_ROOT={ROOT}',
            f'TEST_DIR={HERE}', f'OUT={out}',
            f'XM14_CC={kos}/utils/build_wrappers/kos-cc',
            f'XM14_CXX={kos}/utils/build_wrappers/kos-c++']
    # Compile the production body unchanged. Then derive interruption PCs from
    # its actual FTRV opcodes before compiling the fixture main. No injected
    # callback, labels or synthetic transform is needed in the production loop.
    first_log = command(make + ['production_objects', 'inspect_inputs'], cwd=out, env=env)
    binding['effective_defines'] = {
        name: effective_defines((out / f'effective-{name}-defines.txt').read_text())
        for name in ('c', 'cxx')}
    binding['sdk_headers_sha256'] = verify_dependencies(out, kos, sdk, cxx)
    object_disassembly = command([prefix + 'objdump', '-d',
                                  '--disassemble=_re4dc_zam_xm_points14',
                                  out / 'production_batch.o'])
    offsets = ftrv_offsets(object_disassembly)
    fixture_hashes = {path.name: sha(path.read_bytes()) for path in
                      (Path(__file__), HERE / 'cloth_xm14_target.mk',
                       HERE / 'cloth_xm14_main.cpp', HERE / 'cloth_xm14_xm_probe.c')}
    identity = dict(fixture=fixture_hashes, batch=BATCH_HASH, scalar=SCALAR_HASH,
                    api=API_HASH, geometry=GEOMETRY_HASHES, kos=KOS_PIN, sh4zam=SH4ZAM_PIN,
                    toolchain_binding=binding,
                    production_object=sha((out / 'production_batch.o').read_bytes()),
                    ftrv_offsets=offsets)
    build_id = sha(json.dumps(identity, sort_keys=True).encode())
    (out / 'cloth_xm14_offsets.h').write_text(
        '#pragma once\nstatic constexpr unsigned kFixtureFtrvOffsets[] = {' +
        ', '.join(f'{value}u' for value in offsets) + '};\n' +
        f'static constexpr char kFixtureBuildId[] = "{build_id}";\n')
    (out / 'batch-object-disassembly.txt').write_text(object_disassembly)
    make += ['all']
    (out / 'make-command.json').write_text(json.dumps([str(x) for x in make], indent=2) + '\n')
    (out / 'build.log').write_text(first_log + command(make, cwd=out, env=env))
    elf = out / 'cloth_xm14.elf'
    assert elf.is_file() and elf.stat().st_size > 0, 'KOS target executable missing'
    # The linked program must use the same archive/startup that entered its ID.
    link_inputs = verify_link_inputs((out / 'cloth_xm14.map').read_text(),
                                     out, kos, cxx, binding)
    all_sdk_headers = verify_dependencies(out, kos, sdk, cxx)
    for name, expected in binding['sdk_headers_sha256'].items():
        assert all_sdk_headers.get(name) == expected, f'SDK header changed during build: {name}'
    nm = command([prefix + 'nm', '-g', elf])
    disassembly = command([prefix + 'objdump', '-d', elf])
    batch_disassembly = command([prefix + 'objdump', '-d',
                                 '--disassemble=_re4dc_zam_xm_points14', elf])
    elf_header = command([prefix + 'readelf', '-h', elf])
    for symbol in ('_re4dc_zam_xm_points14', '_re4dc_zam_xm_points14_scalar',
                   '_re4dc_sh4_MTXMultVec', '_PSMTXMultVec', '_fixture_seed_xm', '_main'):
        assert re.search(r'\b' + symbol + r'\b', nm), f'missing linked symbol: {symbol}'
    assert 'Renesas / SuperH SH' in elf_header or 'SuperH' in elf_header, 'not an SH ELF'
    assert 'little endian' in elf_header, 'wrong target byte order'
    assert 'ftrv' in batch_disassembly.lower() and batch_disassembly.lower().count('frchg') >= 2, \
        'XMTRX/FTRV codegen missing; inspect compiler or SH4ZAM pin'
    assert ftrv_offsets(batch_disassembly) == offsets, \
        'linked FTRV offsets differ; IRQ address binding is invalid'
    (out / 'symbols.txt').write_text(nm)
    (out / 'disassembly.txt').write_text(disassembly)
    (out / 'batch-disassembly.txt').write_text(batch_disassembly)
    (out / 'elf-header.txt').write_text(elf_header)
    receipt = dict(status='BUILT_NOT_EXECUTED', source_head=SOURCE_HEAD,
                   batch_sha256=BATCH_HASH, scalar_sha256=SCALAR_HASH, api_sha256=API_HASH,
                   geometry_sha256=GEOMETRY_HASHES,
                   kos=KOS_PIN, sh4zam=SH4ZAM_PIN, compiler='GCC 15.2.0 KOS',
                   binutils='2.45.1', newlib='4.6.0.20260123',
                   scalar_assembly_profile='GAME_FP_CONTRACT=off GAME_MULTVEC_SCHED=1',
                   fixture_version='irq1', fixture_build_id=build_id,
                   build_identity_inputs=identity,
                   fixture_sha256=fixture_hashes, ftrv_offsets=offsets,
                   toolchain_binding=binding, link_inputs_sha256=link_inputs,
                   all_sdk_headers_sha256=all_sdk_headers,
                   irq_contract='TMU1 async IRQ; actual FTRV PC hits; handler clobbers XMTRX',
                   generated_sha256={name: sha((out / name).read_bytes()) for name in
                                     ('production_batch.c', 'production_scalar.S', 're4dc_xm.h')},
                   elf_sha256=sha(elf.read_bytes()), make_command=make,
                   runtime_verdict='Requires actual SH-4 run; expect CLOTH_XM14_TARGET PASS')
    (out / 'receipt.json').write_text(json.dumps(receipt, indent=2, default=str) + '\n')
    print(json.dumps(dict(status=receipt['status'], elf=str(elf), sha256=receipt['elf_sha256'])))


def verify_run(path, receipt_path):
    receipt = json.loads(receipt_path.read_text())
    assert receipt.get('status') == 'BUILT_NOT_EXECUTED' and \
        receipt.get('fixture_version') == 'irq1', 'not a built IRQ fixture receipt'
    build_id = receipt.get('fixture_build_id', '')
    assert re.fullmatch(r'[0-9a-f]{64}', build_id), 'invalid fixture build identity'
    assert receipt.get('kos') == KOS_PIN and receipt.get('sh4zam') == SH4ZAM_PIN, \
        'receipt uses different KOS/SH4ZAM pins'
    binding = receipt.get('toolchain_binding', {})
    assert binding.get('version') == 'bound-kos-v1' and binding.get('input_sha256') and \
        binding.get('sdk_headers_sha256') and receipt.get('link_inputs_sha256'), \
        'receipt lacks verified compiler/header/library binding'
    identity = receipt.get('build_identity_inputs', {})
    assert identity.get('toolchain_binding') == binding and \
        sha(json.dumps(identity, sort_keys=True).encode()) == build_id, \
        'recorded SDK binding does not match the executable build identity'
    for suffix in ('/lib/dreamcast/libkallisti.a', '/lib/dreamcast/_kos_startup.o'):
        names = [name for name in binding['input_sha256'] if name.endswith(suffix)]
        assert len(names) == 1 and receipt['link_inputs_sha256'].get(names[0]) == \
            binding['input_sha256'][names[0]], 'linked KOS input differs from the bound input'
    for name in ('c', 'cxx'):
        values = binding.get('effective_defines', {}).get(name, {})
        effective_defines('\n'.join(f'#define {key} {value}' for key, value in values.items()))
    body = path.read_text().replace('\r\n', '\n').replace('\r', '\n')
    assert body.count('CLOTH_XM14_TARGET PASS') == 1, 'duplicated or missing target completion'
    matches = re.findall(r'CLOTH_XM14_TARGET PASS checks=(\d+) source=bbfd3254 '
                         r'sh4zam=33fa4850 fixture=irq1 build=([0-9a-f]{64})', body)
    assert len(matches) == 1 and int(matches[0][0]) >= 1000 and matches[0][1] == build_id, \
        'missing, stale or malformed target PASS line'
    assert 'CLOTH_XM14_TARGET FAIL' not in body, 'target reported a failed assertion'
    clipped = re.findall(r'CLOTH_XM14_CLIP cases=16 empty=1 complete=1 clipped=14 vertices=(\d+)', body)
    assert len(clipped) == 1 and 6 < int(clipped[0]) <= 16 * 12, \
        'missing, duplicated or malformed actual production clipper evidence'
    mode = re.findall(r'CLOTH_XM14_FPSCR entry=([0-9a-f]{8}) pr=(\d+) sz=(\d+) fr=(\d+)', body)
    assert len(mode) == 1, 'missing or duplicated FPSCR entry evidence'
    entry = int(mode[0][0], 16)
    assert not entry & 0x00180000 and mode[0][1:3] == ('0', '0') and \
        int(mode[0][3]) == ((entry >> 21) & 1), 'invalid PR/SZ/FR entry mode'
    irqs = re.findall(r'CLOTH_XM14_IRQ irqs=(\d+) ftrv_hits=(\d+) rounds=(\d+) '
                      r'errors=(\d+) output_errors=(\d+) saved=([0-9a-f]{8}) '
                      r'handler=([0-9a-f]{8}) entry=([0-9a-f]{8}) exit=([0-9a-f]{8})', body)
    assert len(irqs) == 1, 'missing or duplicated asynchronous IRQ evidence'
    irq = irqs[0]
    assert int(irq[0]) >= int(irq[1]) >= 4 and 0 < int(irq[2]) <= 12288 and \
        irq[3:5] == ('0', '0'), 'insufficient actual FTRV IRQ coverage or failed output'
    assert int(irq[5], 16) == int(irq[7], 16) == int(irq[8], 16) == entry and \
        not int(irq[6], 16) & 0x00380000, 'IRQ FPSCR bank/control restoration failed'
    print(json.dumps(dict(status='TARGET_LOG_PASS', checks=int(matches[0][0]), log=str(path),
                          fixture_build_id=build_id, ftrv_irq_hits=int(irq[1]),
                          log_sha256=sha(path.read_bytes()))))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='task', required=True)
    sub.add_parser('check-source')
    verdict = sub.add_parser('verify-run')
    verdict.add_argument('--log', type=Path, required=True)
    verdict.add_argument('--receipt', type=Path, required=True)
    target = sub.add_parser('build')
    for name in ('output', 'kos-root', 'sdk-root', 'sh4-cxx'):
        target.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    if args.task == 'verify-run':
        verify_run(args.log, args.receipt)
        return
    batch, scalar = source_inputs()
    if args.task == 'check-source':
        print(json.dumps(dict(status='SOURCE_PIN_PASS', source_head=SOURCE_HEAD,
                              batch_sha256=BATCH_HASH, scalar_sha256=SCALAR_HASH,
                              api_sha256=API_HASH, geometry_sha256=GEOMETRY_HASHES)))
    else:
        build(args, batch, scalar)


if __name__ == '__main__':
    try:
        main()
    except (AssertionError, RuntimeError, OSError, ValueError) as exc:
        print(f'CLOTH_XM14_TARGET_REFUSED: {exc}', file=sys.stderr)
        raise SystemExit(2)
