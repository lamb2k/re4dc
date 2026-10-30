#!/usr/bin/env python3
"""Host tests for the fixture's evidence parser; no SH-4 execution is claimed."""
import base64
import contextlib
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import zlib
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
BINDING = dict(version='bound-kos-v2', input_sha256=LINK_INPUTS,
               sdk_profile=DRIVER.sdk_profile(DRIVER.PRISTINE_PROFILE),
               kos_sources_sha256={DRIVER.PVR_HEADER: DRIVER.PVR_BASE_SHA256},
               sdk_headers_sha256={'/synthetic-sdk/include/kos.h': 'e' * 64,
                    '/synthetic-sdk/' + DRIVER.PVR_HEADER: DRIVER.PVR_BASE_SHA256},
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
                          sdk_profile=BINDING['sdk_profile'],
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
                       'kernel/arch/dreamcast/include/arch/timer.h', DRIVER.PVR_HEADER)
            self.commit_headers(kos, headers)
            self.commit_headers(sdk, ('include/sh4zam/shz_xmtrx.h',))
            deps = [kos / name for name in headers] + [sdk / 'include/sh4zam/shz_xmtrx.h']
            depfile = out / 'probe.o.d'
            good = 'probe.o: ' + ' '.join(map(str, deps)) + '\n'
            depfile.write_text(good)
            cxx = toolchain / 'bin/sh-elf-g++'
            self.assertEqual(len(DRIVER.verify_dependencies(out, kos, sdk, cxx)), 6)
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

    @staticmethod
    def public_pvr_header():
        fixture = json.loads((HERE / 'cloth_xm14_pvr_fixture.json').read_text())
        data = zlib.decompress(base64.b85decode(fixture['data']))
        assert fixture['encoding'] == 'zlib-base85' and DRIVER.sha(data) == DRIVER.PVR_BASE_SHA256
        return data

    def patched_header_repo(self, root):
        # Real public header/patch bytes in a tiny synthetic Git repository.
        # This is not a substitute KOS compiler/library or target build.
        headers = ('include/kos.h', 'include/kos/irq.h',
                   'kernel/arch/dreamcast/include/arch/irq.h',
                   'kernel/arch/dreamcast/include/arch/timer.h', DRIVER.PVR_HEADER)
        self.commit_headers(root, headers)
        header = root / DRIVER.PVR_HEADER
        header.write_bytes(self.public_pvr_header())
        subprocess.run(['git', '-C', str(root), 'add', DRIVER.PVR_HEADER], check=True)
        subprocess.run(['git', '-C', str(root), '-c', 'user.name=Fixture',
                        '-c', 'user.email=fixture@example.invalid', 'commit', '-qm',
                        'exact public pinned PVR header'], check=True)
        profile = DRIVER.sdk_profile(DRIVER.REVIEWED_PROFILE)
        for path in DRIVER.reviewed_patches(profile['manifest']):
            DRIVER.command(['git', 'apply', '--include=' + DRIVER.PVR_HEADER, path], cwd=root)
        return profile, header, headers

    def test_actual_reviewed_header_patch_chain_is_explicit_and_read_only(self):
        with tempfile.TemporaryDirectory(prefix='cloth-xm14-reviewed-header-') as scratch:
            root = Path(scratch)
            profile, header, _ = self.patched_header_repo(root / 'kos')
            selected = header.read_bytes()
            rule = profile['manifest']['headers'][DRIVER.PVR_HEADER]
            self.assertEqual(DRIVER.git_blob(self.public_pvr_header()), rule['base_git_blob'])
            self.assertEqual(DRIVER.git_blob(selected), rule['selected_git_blob'])
            self.assertEqual(DRIVER.sha(selected), rule['selected_sha256'])
            with self.assertRaises(AssertionError):
                DRIVER.pinned_file(root / 'kos', DRIVER.PVR_HEADER)  # pristine is separate
            foreign = root / 'foreign-worktree' / DRIVER.PVR_HEADER
            foreign.parent.mkdir(parents=True)
            foreign.write_bytes(b'unrelated checkout must remain untouched')
            with patch.dict(os.environ, {'GIT_WORK_TREE': str(root / 'foreign-worktree')}):
                evidence = DRIVER.reviewed_header_evidence(root / 'kos', profile)
            self.assertEqual(evidence, {DRIVER.PVR_HEADER: rule['selected_sha256']})
            self.assertEqual(header.read_bytes(), selected)
            self.assertEqual(foreign.read_bytes(), b'unrelated checkout must remain untouched')
            header.write_bytes(self.public_pvr_header())
            with self.assertRaises(AssertionError):  # do not label pristine as maintained
                DRIVER.pinned_file(root / 'kos', DRIVER.PVR_HEADER, profile)

    def test_reviewed_header_unknown_modifications_foreign_path_and_base_refused(self):
        with tempfile.TemporaryDirectory(prefix='cloth-xm14-reviewed-refuse-') as scratch:
            root = Path(scratch)
            kos = root / 'kos'
            profile, header, _ = self.patched_header_repo(kos)
            selected = header.read_bytes()
            header.write_bytes(selected + b'\n/* unknown local change */\n')
            with self.assertRaises(AssertionError):
                DRIVER.pinned_file(kos, DRIVER.PVR_HEADER, profile)
            header.write_bytes(selected)
            other = kos / 'include/kos.h'
            other.write_bytes(other.read_bytes() + b'/* a different dirty header */\n')
            with self.assertRaises(AssertionError):
                DRIVER.pinned_file(kos, 'include/kos.h', profile)
            external = root / 'external-pvr.h'
            external.write_bytes(selected)
            header.unlink()
            header.symlink_to(external)
            with self.assertRaises(AssertionError):
                DRIVER.pinned_file(kos, DRIVER.PVR_HEADER, profile)
            header.unlink()
            header.write_bytes(selected)
            subprocess.run(['git', '-C', str(kos), 'add', DRIVER.PVR_HEADER], check=True)
            subprocess.run(['git', '-C', str(kos), '-c', 'user.name=Fixture',
                            '-c', 'user.email=fixture@example.invalid', 'commit', '-qm',
                            'wrong base now records the maintained blob'], check=True)
            with self.assertRaises(AssertionError):
                DRIVER.pinned_file(kos, DRIVER.PVR_HEADER, profile)
            # validate_sdk still requires the actual KOS commit, before any
            # compiler command; a header-only fixture cannot masquerade as it.
            (kos / 'Makefile.rules').write_text('')
            sdk = root / 'sdk';(sdk / 'include/sh4zam').mkdir(parents=True)
            (sdk / 'include/sh4zam/shz_xmtrx.h').write_text('')
            cxx = root / 'sh-elf-g++';cxx.write_text('')
            with self.assertRaisesRegex(AssertionError, 'expected ' + DRIVER.KOS_PIN):
                DRIVER.validate_sdk(kos, sdk, cxx)

    def test_reviewed_header_scratch_stops_before_malformed_ancestor(self):
        real_temporary_directory = tempfile.TemporaryDirectory
        with real_temporary_directory(prefix='cloth-xm14-git-ceiling-') as scratch:
            root = Path(scratch)
            kos = root / 'kos'
            profile, header, _ = self.patched_header_repo(kos)
            selected = header.read_bytes()
            ancestor = root / 'unrelated-ancestor'
            ancestor.mkdir()
            metadata = ancestor / '.git'
            # Like a stale linked-worktree/submodule gitfile in an ancestor.
            malformed = b'gitdir: ../../missing-checkout/.git/worktrees/stale\n'
            metadata.write_bytes(malformed)
            foreign = root / 'foreign-worktree' / DRIVER.PVR_HEADER
            foreign.parent.mkdir(parents=True)
            foreign.write_bytes(b'unrelated checkout must remain untouched')

            def proof_directory(**kwargs):
                return real_temporary_directory(dir=ancestor, **kwargs)

            # Establish that this controlled ancestor reproduces Git discovery's
            # failure, independently of any malformed metadata on the host.
            clean_env = {key: value for key, value in os.environ.items()
                         if not key.startswith('GIT_')}
            clean_env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull)
            with proof_directory(prefix='unprotected-') as unprotected:
                result = subprocess.run(['git', 'apply', '--check',
                    '--include=' + DRIVER.PVR_HEADER,
                    str(DRIVER.reviewed_patches(profile['manifest'])[0])],
                    cwd=unprotected, env=clean_env, capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('not a git repository', result.stderr)

            inherited = dict(GIT_WORK_TREE=str(root / 'foreign-worktree'),
                             GIT_CEILING_DIRECTORIES=str(root / 'wrong-ceiling'),
                             GIT_CONFIG_COUNT='0', GIT_TRACE='0')
            with patch.object(DRIVER.tempfile, 'TemporaryDirectory', side_effect=proof_directory), \
                 patch.dict(os.environ, inherited), \
                 patch.object(DRIVER, 'command', wraps=DRIVER.command) as commands:
                evidence = DRIVER.reviewed_header_evidence(kos, profile)
            rule = profile['manifest']['headers'][DRIVER.PVR_HEADER]
            self.assertEqual(evidence, {DRIVER.PVR_HEADER: rule['selected_sha256']})
            applies = [call for call in commands.call_args_list if call.args[0][:2] == ['git', 'apply']]
            self.assertEqual(len(applies), 2 * len(profile['manifest']['patches']))
            for index, call in enumerate(applies):
                args, env = call.args[0], call.kwargs['env']
                self.assertEqual('--check' in args, index % 2 == 0)
                self.assertEqual(env['GIT_CEILING_DIRECTORIES'], str(call.kwargs['cwd'].resolve().parent))
                self.assertEqual({key for key in env if key.startswith('GIT_')},
                                 {'GIT_CEILING_DIRECTORIES', 'GIT_CONFIG_NOSYSTEM', 'GIT_CONFIG_GLOBAL'})
                self.assertEqual(env['GIT_CONFIG_NOSYSTEM'], '1')
                self.assertEqual(env['GIT_CONFIG_GLOBAL'], os.devnull)
            self.assertEqual(header.read_bytes(), selected)
            self.assertEqual(metadata.read_bytes(), malformed)
            self.assertEqual(foreign.read_bytes(), b'unrelated checkout must remain untouched')
            self.assertEqual(list(ancestor.iterdir()), [metadata])

            # The ceiling cannot turn an incomplete derivation into evidence.
            with patch.object(DRIVER.tempfile, 'TemporaryDirectory', side_effect=proof_directory), \
                 patch.object(DRIVER, 'reviewed_patches', return_value=[]), \
                 self.assertRaisesRegex(AssertionError, 'do not derive the selected header'):
                DRIVER.reviewed_header_evidence(kos, profile)
            self.assertEqual(header.read_bytes(), selected)
            self.assertEqual(metadata.read_bytes(), malformed)

    def test_reviewed_manifest_and_patch_changes_are_not_an_allowlist(self):
        original = DRIVER.REVIEWED_MANIFEST.read_bytes()
        manifest = DRIVER.reviewed_manifest(original)
        for field, value in (('kos_base', '0' * 40), ('profile', 'arbitrary'),
                             ('headers', {'unknown.h': {'selected_sha256': '0' * 64}})):
            changed = copy.deepcopy(manifest);changed[field] = value
            with self.assertRaises(AssertionError):
                DRIVER.reviewed_manifest(json.dumps(changed).encode())
        with self.assertRaises(AssertionError):
            DRIVER.sdk_profile('caller-provided-allowlist')
        with tempfile.TemporaryDirectory(prefix='cloth-xm14-reviewed-manifest-') as scratch:
            root = Path(scratch)
            reviewed = root / 'cloth_xm14_sdk_reviewed.json';reviewed.write_bytes(original)
            # Read again after the first validated snapshot: changing a manifest
            # in place cannot survive the post-link profile check.
            with patch.object(DRIVER, 'HERE', root), patch.object(DRIVER, 'REVIEWED_MANIFEST', reviewed):
                self.assertEqual(DRIVER.sdk_profile(DRIVER.REVIEWED_PROFILE)['manifest'], manifest)
                reviewed.write_bytes(original + b' ')
                with self.assertRaises(AssertionError):
                    DRIVER.sdk_profile(DRIVER.REVIEWED_PROFILE)
            for entry in manifest['patches']:
                target = root / entry['path'];target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((DRIVER.ROOT / entry['path']).read_bytes())
            self.assertEqual(len(DRIVER.reviewed_patches(manifest, root)), 3)
            target.write_bytes(target.read_bytes() + b'\n# unknown patch change\n')
            with self.assertRaises(AssertionError):
                DRIVER.reviewed_patches(manifest, root)

    def test_reviewed_archive_startup_hashes_are_exact_selected_inputs(self):
        profile = DRIVER.sdk_profile(DRIVER.REVIEWED_PROFILE)
        expected = {'/selected-kos/' + key: value
                    for key, value in profile['manifest']['built_inputs_sha256'].items()}
        DRIVER.reviewed_binary_hashes(profile, expected)
        for name in expected:
            for changed in ({**expected, name: '0' * 64},
                            {key: value for key, value in expected.items() if key != name},
                            {**expected, '/another-kos/' + name.split('/selected-kos/')[1]: expected[name]}):
                with self.assertRaises(AssertionError):
                    DRIVER.reviewed_binary_hashes(profile, changed)
        # These are manifest/hash-policy unit controls, not fabricated binary
        # preimages or a claim that the installed local binaries were executed.

    def test_reviewed_dependencies_rechecked_after_midbuild_header_change(self):
        with tempfile.TemporaryDirectory(prefix='cloth-xm14-reviewed-midbuild-') as scratch:
            root = Path(scratch);kos, sdk, out = (root / name for name in ('kos', 'sdk', 'out'))
            profile, header, headers = self.patched_header_repo(kos)
            self.commit_headers(sdk, ('include/sh4zam/shz_xmtrx.h',))
            out.mkdir()
            deps = [kos / name for name in headers] + [sdk / 'include/sh4zam/shz_xmtrx.h']
            (out / 'probe.o.d').write_text('probe.o: ' + ' '.join(map(str, deps)) + '\n')
            cxx = root / 'toolchain/bin/sh-elf-g++'
            before = DRIVER.verify_dependencies(out, kos, sdk, cxx, profile)
            self.assertEqual(before[str(header)], profile['manifest']['headers'][DRIVER.PVR_HEADER]['selected_sha256'])
            header.write_bytes(header.read_bytes() + b'/* changed after build identity */\n')
            with self.assertRaises(AssertionError):
                DRIVER.verify_dependencies(out, kos, sdk, cxx, profile)

    def test_patched_receipt_binding_and_rehashed_tampering(self):
        profile = DRIVER.sdk_profile(DRIVER.REVIEWED_PROFILE)
        binding = copy.deepcopy(BINDING)
        binding['sdk_profile'] = profile
        binding['input_sha256'] = {'/synthetic-sdk/' + key: value
                                  for key, value in profile['manifest']['built_inputs_sha256'].items()}
        selected = profile['manifest']['headers'][DRIVER.PVR_HEADER]['selected_sha256']
        binding['sdk_headers_sha256']['/synthetic-sdk/' + DRIVER.PVR_HEADER] = selected
        binding['kos_sources_sha256'][DRIVER.PVR_HEADER] = selected
        def verify(value, top_profile=None):
            identity = dict(toolchain_binding=value)
            identifier = DRIVER.sha(json.dumps(identity, sort_keys=True).encode())
            return self.verify(LOG.replace(BUILD, identifier), fixture_build_id=identifier,
                sdk_profile=value['sdk_profile'] if top_profile is None else top_profile,
                toolchain_binding=value, build_identity_inputs=identity,
                link_inputs_sha256=value['input_sha256'])
        self.assertEqual(verify(binding)['kos_profile'], DRIVER.REVIEWED_PROFILE)
        mutations = []
        for relative in profile['manifest']['built_inputs_sha256']:
            changed = copy.deepcopy(binding);changed['input_sha256']['/synthetic-sdk/' + relative] = '0' * 64;mutations.append(changed)
        changed = copy.deepcopy(binding);changed['sdk_profile']['kos_base'] = '0' * 40;mutations.append(changed)
        changed = copy.deepcopy(binding);changed['sdk_profile']['manifest_sha256'] = '0' * 64;mutations.append(changed)
        changed = copy.deepcopy(binding);changed['sdk_profile']['manifest']['headers'] = {};mutations.append(changed)
        changed = copy.deepcopy(binding);changed['sdk_headers_sha256']['/synthetic-sdk/' + DRIVER.PVR_HEADER] = DRIVER.PVR_BASE_SHA256;mutations.append(changed)
        changed = copy.deepcopy(binding);changed['kos_sources_sha256'][DRIVER.PVR_HEADER] = DRIVER.PVR_BASE_SHA256;mutations.append(changed)
        changed = copy.deepcopy(binding);changed['version'] = 'bound-kos-v1';mutations.append(changed)
        for changed in mutations:
            with self.assertRaises(AssertionError):
                verify(changed)  # even a recomputed ID/log cannot broaden the reviewed profile
        with self.assertRaises(AssertionError):
            verify(binding, DRIVER.sdk_profile(DRIVER.PRISTINE_PROFILE))

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
