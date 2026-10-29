#!/usr/bin/env python3
"""Host tests for the fixture's evidence parser; no SH-4 execution is claimed."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('cloth_xm14_target', HERE / 'cloth_xm14_target.py')
DRIVER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DRIVER)
DEFINES = {name: '1' for name in ('__sh__', '__SH4_SINGLE__', '__LITTLE_ENDIAN__',
           '__DREAMCAST__', '_arch_dreamcast', '_arch_sub_pristine',
           'RE4DC_CLOTH_XM_BATCH14', 'RE4DC_FX_STRIP21')}
DEFINES['__FINITE_MATH_ONLY__'] = '0'
DEFINES_BODY = '\n'.join(f'#define {key} {value}' for key, value in DEFINES.items())
LINK_INPUTS = {'/synthetic-sdk/lib/dreamcast/libkallisti.a': 'd' * 64,
               '/synthetic-sdk/lib/dreamcast/_kos_startup.o': 'f' * 64}
BINDING = dict(version='bound-kos-v1', input_sha256=LINK_INPUTS,
               sdk_headers_sha256={'/synthetic-sdk/include/kos.h': 'e' * 64},
               effective_defines=dict(c=DEFINES, cxx=DEFINES))
IDENTITY = dict(toolchain_binding=BINDING)
BUILD = DRIVER.sha(json.dumps(IDENTITY, sort_keys=True).encode())
LOG = (
    'CLOTH_XM14_FPSCR entry=00040000 pr=0 sz=0 fr=0\n'
    'CLOTH_XM14_CLIP cases=16 empty=1 complete=1 clipped=14 vertices=108\n'
    'CLOTH_XM14_IRQ irqs=17 ftrv_hits=4 rounds=120 errors=0 output_errors=0 '
    'saved=00040000 handler=00000000 entry=00040000 exit=00040000\n'
    'CLOTH_XM14_TARGET PASS checks=1500 source=bbfd3254 sh4zam=33fa4850 '
    f'fixture=irq1 build={BUILD}\n'
)


class DriverTest(unittest.TestCase):
    def verify(self, body=LOG, **overrides):
        with tempfile.TemporaryDirectory(prefix='cloth-xm14-driver-') as scratch:
            root = Path(scratch)
            log, receipt = root / 'run.log', root / 'receipt.json'
            log.write_text(body)
            fields = dict(status='BUILT_NOT_EXECUTED', fixture_version='irq1',
                          fixture_build_id=BUILD, kos=DRIVER.KOS_PIN,
                          sh4zam=DRIVER.SH4ZAM_PIN,
                          toolchain_binding=BINDING, build_identity_inputs=IDENTITY,
                          link_inputs_sha256=LINK_INPUTS)
            fields.update(overrides)
            receipt.write_text(json.dumps(fields))
            with contextlib.redirect_stdout(io.StringIO()) as output:
                DRIVER.verify_run(log, receipt)
            return json.loads(output.getvalue())

    def test_complete_evidence_parser(self):
        self.assertEqual(self.verify()['ftrv_irq_hits'], 4)
        self.assertEqual(self.verify(LOG.replace('\n', '\r\n'))['status'], 'TARGET_LOG_PASS')

    def test_stale_fixture_cannot_pass(self):
        for body in (LOG.replace('fixture=irq1 ', ''),
                     LOG.replace(BUILD, 'a' * 64),
                     LOG.replace('checks=1500', 'checks=15')):
            with self.subTest(body=body), self.assertRaises(AssertionError):
                self.verify(body)

    def test_missing_irq_or_non_ftrv_irq_is_not_a_skip(self):
        for body in (LOG.replace('ftrv_hits=4', 'ftrv_hits=0'),
                     LOG.replace('ftrv_hits=4', 'ftrv_hits=3'),
                     LOG.replace('irqs=17', 'irqs=0'),
                     '\n'.join(line for line in LOG.splitlines() if '_IRQ' not in line)):
            with self.subTest(body=body), self.assertRaises(AssertionError):
                self.verify(body)

    def test_missing_real_clipper_coverage_is_rejected(self):
        for body in (LOG.replace('clipped=14', 'clipped=0'),
                     LOG.replace('vertices=108', 'vertices=0'),
                     '\n'.join(line for line in LOG.splitlines() if '_CLIP' not in line)):
            with self.subTest(body=body), self.assertRaises(AssertionError):
                self.verify(body)

    def test_numeric_or_fpscr_error_is_rejected(self):
        for old, new in [('output_errors=0', 'output_errors=1'),
                         ('errors=0 output', 'errors=8 output'),
                         ('saved=00040000', 'saved=00000000'),
                         ('exit=00040000', 'exit=00240000'),
                         ('handler=00000000', 'handler=00100000'),
                         ('pr=0', 'pr=1'), ('sz=0', 'sz=1'), ('fr=0', 'fr=1')]:
            with self.subTest(old=old), self.assertRaises(AssertionError):
                self.verify(LOG.replace(old, new))

    def test_duplicate_or_failed_run_is_rejected(self):
        for body in (LOG + LOG,
                     LOG + 'CLOTH_XM14_TARGET PASS checks=1500 source=bbfd3254 sh4zam=33fa4850\n',
                     LOG + 'CLOTH_XM14_TARGET FAIL line=25 expr=bad\n'):
            with self.assertRaises(AssertionError):
                self.verify(body)

    def test_wrong_receipt_is_rejected(self):
        for key, value in [('status', 'SOURCE_PIN_PASS'), ('fixture_version', 'intercall'),
                           ('kos', '0' * 40), ('sh4zam', '1' * 40)]:
            with self.subTest(key=key), self.assertRaises(AssertionError):
                self.verify(**{key: value})

    def test_unbound_sdk_receipt_is_rejected(self):
        for fields in (dict(toolchain_binding={}), dict(link_inputs_sha256={}),
                       dict(build_identity_inputs={}),
                       dict(link_inputs_sha256={name: '0' * 64 for name in LINK_INPUTS})):
            with self.subTest(fields=fields), self.assertRaises(AssertionError):
                self.verify(**fields)

    def test_effective_abi_and_math_controls(self):
        self.assertEqual(DRIVER.effective_defines(DEFINES_BODY), DEFINES)
        for old, new in [('__SH4_SINGLE__ 1', '__SH4_SINGLE_ONLY__ 1'),
                         ('__LITTLE_ENDIAN__ 1', '__BIG_ENDIAN__ 1'),
                         ('__FINITE_MATH_ONLY__ 0', '__FINITE_MATH_ONLY__ 1'),
                         ('RE4DC_CLOTH_XM_BATCH14 1', 'RE4DC_CLOTH_XM_BATCH14 0'),
                         ('_arch_sub_pristine 1', '_arch_sub_naomi 1')]:
            with self.subTest(old=old), self.assertRaises(AssertionError):
                DRIVER.effective_defines(DEFINES_BODY.replace(old, new))
        with self.assertRaises(AssertionError):
            DRIVER.effective_defines(DEFINES_BODY + '\n#define __FAST_MATH__ 1\n')

    def test_sourced_sdk_cannot_redirect_selected_wrappers(self):
        # Synthetic tools exercise only environment/wrapper routing. They never
        # pass validate_sdk(), compile an SH ELF, or produce a target receipt.
        with tempfile.TemporaryDirectory(prefix='cloth-xm14-env-') as scratch:
            root = Path(scratch)
            kos, sdk, binary = root / 'kos', root / 'sh4zam', root / 'toolchain/bin'
            wrappers = kos / 'utils/build_wrappers'
            wrappers.mkdir(parents=True)
            binary.mkdir(parents=True)
            for name in ('gcc', 'g++'):
                path = binary / ('sh-elf-' + name)
                path.write_text('#!/bin/sh\nprintf "%s\\n" "' + name + '" "$@"\n')
                path.chmod(0o755)
            (wrappers / 'kos-cc').write_text('#!/bin/sh\nexec ${KOS_CC} "$@"\n')
            (wrappers / 'kos-c++').write_text('#!/bin/sh\nexec ${KOS_CCPLUS} "$@"\n')
            for path in wrappers.iterdir():
                path.chmod(0o755)
            (kos / 'environ_base.sh').write_text('''
export KOS_CC="$KOS_CC_BASE/bin/$KOS_CC_PREFIX-gcc"
export KOS_CCPLUS="$KOS_CC_BASE/bin/$KOS_CC_PREFIX-g++"
export KOS_INC_PATHS="-isystem $KOS_BASE/include -isystem $KOS_PORTS/include"
export KOS_CFLAGS="$KOS_CFLAGS $KOS_INC_PATHS"
export KOS_LIB_PATHS="-L$KOS_BASE/lib/dreamcast -L$KOS_PORTS/lib"
export KOS_LDFLAGS="-T$KOS_BASE/utils/ldscripts/shlelf.xc $KOS_LIB_PATHS"
''')
            inherited = {name: '/wrong-sdk' for name in
                         ('KOS_CC', 'KOS_CCPLUS', 'KOS_CFLAGS', 'KOS_LDFLAGS',
                          'KOS_LIBS', 'CPATH', 'CPLUS_INCLUDE_PATH', 'LIBRARY_PATH',
                          'COMPILER_PATH', 'GCC_EXEC_PREFIX', 'MAKEFILES', 'MAKEFLAGS',
                          'BASH_ENV', 'ENV')}
            with patch.dict(os.environ, inherited):
                env = DRIVER.bound_environment(kos, sdk, binary / 'sh-elf-g++')
            for name in inherited:
                self.assertNotIn('/wrong-sdk', env.get(name, ''))
            for name in ('KOS_CFLAGS', 'KOS_LDFLAGS'):
                self.assertNotIn('unused-cloth-xm14-ports', env[name])
            for wrapper, expected in (('kos-cc', 'gcc'), ('kos-c++', 'g++')):
                result = subprocess.run([str(wrappers / wrapper), 'probe'], env=env,
                                        text=True, capture_output=True, check=True)
                self.assertEqual(result.stdout.splitlines(), [expected, 'probe'])

    @staticmethod
    def commit_headers(root, paths):
        subprocess.run(['git', 'init', '-q', str(root)], check=True)
        for relative in paths:
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('// synthetic binding test header\n')
        subprocess.run(['git', '-C', str(root), 'add', '.'], check=True)
        subprocess.run(['git', '-C', str(root), '-c', 'user.name=Fixture',
                        '-c', 'user.email=fixture@example.invalid', 'commit', '-qm',
                        'synthetic header baseline'], check=True)

    def test_actual_dependency_paths_and_dirty_headers_are_refused(self):
        with tempfile.TemporaryDirectory(prefix='cloth-xm14-deps-') as scratch:
            root = Path(scratch)
            out, kos, sdk, toolchain = (root / name for name in ('out', 'kos', 'sdk', 'toolchain'))
            out.mkdir()
            headers = ('include/kos.h', 'include/kos/irq.h',
                       'kernel/arch/dreamcast/include/arch/irq.h',
                       'kernel/arch/dreamcast/include/arch/timer.h')
            self.commit_headers(kos, headers)
            self.commit_headers(sdk, ('include/sh4zam/shz_xmtrx.h',))
            deps = [kos / name for name in headers] + [sdk / 'include/sh4zam/shz_xmtrx.h']
            depfile = out / 'probe.o.d'
            good = 'probe.o: ' + ' '.join(map(str, deps)) + '\n'
            depfile.write_text(good)
            cxx = toolchain / 'bin/sh-elf-g++'
            self.assertEqual(len(DRIVER.verify_dependencies(out, kos, sdk, cxx)), 5)
            depfile.write_text(good.replace(str(deps[0]), str(root / 'other-kos/include/kos.h')))
            with self.assertRaises(AssertionError):
                DRIVER.verify_dependencies(out, kos, sdk, cxx)
            depfile.write_text(good)
            deps[-1].write_text('// changed in place at the same HEAD\n')
            with self.assertRaises(AssertionError):
                DRIVER.verify_dependencies(out, kos, sdk, cxx)

    def test_link_map_refuses_another_archive_or_changed_input(self):
        with tempfile.TemporaryDirectory(prefix='cloth-xm14-link-') as scratch:
            root = Path(scratch)
            kos, out, toolchain = (root / name for name in ('kos', 'out', 'toolchain'))
            library = kos / 'lib/dreamcast/libkallisti.a'
            startup = kos / 'lib/dreamcast/_kos_startup.o'
            library.parent.mkdir(parents=True)
            library.write_bytes(b'synthetic archive')
            startup.write_bytes(b'synthetic startup')
            binding = dict(input_sha256={str(p): DRIVER.sha(p.read_bytes()) for p in (library, startup)})
            body = f'LOAD {library}\nLOAD {startup}\n'
            cxx = toolchain / 'bin/sh-elf-g++'
            self.assertEqual(DRIVER.verify_link_inputs(body, out, kos, cxx, binding),
                             binding['input_sha256'])
            with self.assertRaises(AssertionError):
                DRIVER.verify_link_inputs(body.replace(str(library), str(root / 'other/libkallisti.a')),
                                          out, kos, cxx, binding)
            library.write_bytes(b'changed after the executable build ID was formed')
            with self.assertRaises(AssertionError):
                DRIVER.verify_link_inputs(body, out, kos, cxx, binding)

    def test_ftrv_offset_binding_uses_opcode_addresses(self):
        example = ('00000000 <_re4dc_zam_xm_points14>:\n'
                   '  14: fd f3       frchg\n'
                   '  32: fd f1       ftrv xmtrx,fv0\n')
        self.assertEqual(DRIVER.ftrv_offsets(example), [0x32])
        linked = example.replace('00000000 <', '8c010000 <').replace('  32:', '8c010032:')
        self.assertEqual(DRIVER.ftrv_offsets(linked), [0x32])
        for bad in (example.replace('ftrv', 'nop'), example.replace('32:', '33:'),
                    example.replace('_re4dc_zam_xm_points14', '_unrelated')):
            with self.assertRaises(AssertionError):
                DRIVER.ftrv_offsets(bad)

    def test_target_clipping_case_inputs_on_host(self):
        # Validate the executable's 16 masks and output bounds through the real
        # production clipper. This host-only scalar shim has no FTRV/IRQ proof.
        body = (HERE / 'cloth_xm14_main.cpp').read_text()
        case = body[body.index('int run_clipped_cells()'):body.index('\nint reject(')]
        prefix = r'''
#include <cstdint>
#include <cstdio>
#include <cstring>
#include "cloth_strip_geometry11.hpp"
using std::memcpy;
unsigned checks;
#define CHECK(value) do { ++checks; if(!(value)) { \
 printf("HOST_CLIP_CASE_FAIL line=%u expr=%s\n",unsigned(__LINE__),#value); return 1; } } while(0)
struct Vec {float x,y,z;};
uint32_t fpscr_controls(){return 0;}
double absolute(double x){return x<0?-x:x;}
int re4dc_zam_xm_points14_scalar(const float (*m)[4],const void* source,unsigned,
 unsigned stride,void* output,unsigned,unsigned out_stride,unsigned count){
 for(unsigned i=0;i<count;++i){
  const auto& p=*reinterpret_cast<const Vec*>(static_cast<const char*>(source)+i*stride);
  auto& q=*reinterpret_cast<Vec*>(static_cast<char*>(output)+i*out_stride);
  q={m[0][0]*p.x+m[0][1]*p.y+m[0][2]*p.z+m[0][3],
     m[1][0]*p.x+m[1][1]*p.y+m[1][2]*p.z+m[1][3],
     m[2][0]*p.x+m[2][1]*p.y+m[2][2]*p.z+m[2][3]};
 }return 1;}
#define re4dc_zam_xm_points14 re4dc_zam_xm_points14_scalar
'''
        stub = r'''#pragma once
#include <stdint.h>
#include <stddef.h>
#define PVR_CMD_VERTEX 0xe0000000u
#define PVR_CMD_VERTEX_EOL 0xf0000000u
struct pvr_vertex_t{uint32_t flags;float x,y,z,u,v;uint32_t argb,oargb;};
struct pvr_poly_hdr_t{uint32_t words[8];};
inline void pvr_prim(const void*,size_t){}
'''
        with tempfile.TemporaryDirectory(prefix='cloth-xm14-case-') as scratch:
            root = Path(scratch)
            (root / 'dc').mkdir()
            (root / 'dc/pvr.h').write_text(stub)
            cpp, exe = root / 'case.cpp', root / 'case'
            cpp.write_text(prefix + case + '\nint main(){return run_clipped_cells();}\n')
            flags = ['-fsanitize=address,undefined', '-fno-omit-frame-pointer'] if \
                os.environ.get('SANITIZE') == '1' else []
            result = subprocess.run(['g++', '-std=c++20', '-O2', '-ffp-contract=off',
                '-DRE4DC_FX_STRIP21=1', '-I' + str(root),
                '-I' + str(DRIVER.ROOT / 'port/dreamcast/game/platform/include'),
                *flags, str(cpp), str(DRIVER.ROOT / 'port/dreamcast/room/pvr_geometry.cpp'),
                '-o', str(exe)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            result = subprocess.run([str(exe)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('cases=16 empty=1 complete=1 clipped=14', result.stdout)


if __name__ == '__main__':
    unittest.main()
