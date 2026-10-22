#!/usr/bin/env python3
"""Synthetic negative controls for tool identity and selection; no compiler/link."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import tool_closure as c


class ClosureControls(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.driver = self.file('driver', b'driver')
        self.tool = self.file('collect2', b'tool')
        self.plugin = self.file('plugin.so', b'plugin')

    def file(self, name, data):
        path = self.root / name
        path.write_bytes(data)
        path.chmod(0o755)
        return path

    def test_exact_identity_and_order_independence(self):
        a = [c.pin(self.driver, 'driver'), c.pin(self.tool, 'tool')]
        self.assertTrue(c.same_pins(a, list(reversed(a))))

    def test_changed_tool_bytes_rejected(self):
        old = [c.pin(self.tool, 'tool')]
        self.tool.write_bytes(b'changed')
        self.assertFalse(c.same_pins(old, [c.pin(self.tool, 'tool')]))

    def test_changed_plugin_bytes_rejected(self):
        old = [c.pin(self.plugin, 'shared-plugin')]
        self.plugin.write_bytes(b'PLUGIN')
        self.assertFalse(c.same_pins(old, [c.pin(self.plugin, 'shared-plugin')]))

    def test_changed_mode_rejected(self):
        old = [c.pin(self.tool, 'tool')]
        self.tool.chmod(0o644)
        self.assertFalse(c.same_pins(old, [c.pin(self.tool, 'tool')]))

    def test_changed_alias_target_rejected(self):
        alias = self.root / 'alias'
        alias.symlink_to(self.tool)
        old = [c.pin(alias, 'tool')]
        other = self.file('other', b'tool')
        alias.unlink()
        alias.symlink_to(other)
        self.assertFalse(c.same_pins(old, [c.pin(alias, 'tool')]))

    def test_missing_extra_duplicate_pin_refused(self):
        row = c.pin(self.tool, 'tool')
        self.assertFalse(c.same_pins([row], []))
        self.assertFalse(c.same_pins([], [row]))
        with self.assertRaises(ValueError):
            c.same_pins([row, row], [row])

    def test_unknown_execution_path_rejected(self):
        snapshot = dict(pins=[c.pin(self.tool, 'driver-program:collect2')])
        self.assertTrue(c.exec_path_allowed(snapshot, self.tool))
        self.assertFalse(c.exec_path_allowed(snapshot, self.driver))
        self.assertFalse(c.exec_path_allowed(snapshot, 'collect2'))

    def test_library_or_config_cannot_become_executable_tool(self):
        for role in ('host-loader-or-shared-library', 'host-loader-config'):
            self.assertFalse(c.exec_path_allowed(dict(pins=[c.pin(self.plugin, role)]), self.plugin))

    def test_environment_override_rejected(self):
        snapshot = dict(influencing_environment={k: None for k in c.INFLUENCING})
        with patch.dict(os.environ, {'LD_PRELOAD': '/unknown/plugin.so'}):
            with self.assertRaisesRegex(ValueError, 'environment'):
                c.check(snapshot)

    def test_absence_invariant_rejected(self):
        snapshot = dict(influencing_environment={k: os.environ.get(k) for k in c.INFLUENCING},
                        loader_absence_invariants=[str(self.tool)])
        with self.assertRaisesRegex(ValueError, 'absence'):
            c.check(snapshot)

    def test_changed_host_shared_object_rejected(self):
        snapshot = dict(pins=[c.pin(self.plugin, 'controller-loaded-host-ELF')])
        self.assertTrue(c.host_elf_path_allowed(snapshot, self.plugin))
        self.plugin.write_bytes(b'changed')
        self.assertFalse(c.host_elf_path_allowed(snapshot, self.plugin))

    def test_unplanned_controller_mapping_rejected(self):
        snapshot = dict(influencing_environment={k: os.environ.get(k) for k in c.INFLUENCING},
                        loader_absence_invariants=[], pins=[c.pin(self.tool, 'tool')],
                        controller_host_elf_maps=[str(self.tool)])
        with patch.object(c, 'mapped_host_elfs', return_value={str(self.driver)}):
            with self.assertRaisesRegex(ValueError, 'mapping'):
                c.check(snapshot)

    def test_changed_driver_selection_rejected(self):
        prior = dict(argv=[str(self.driver), '-print-prog-name=ld'], stdout=str(self.tool))
        snapshot = dict(influencing_environment={k: os.environ.get(k) for k in c.INFLUENCING},
                        loader_absence_invariants=[], pins=[c.pin(self.tool, 'tool')],
                        program_queries=[prior], plugin_query=prior, driver=str(self.driver))
        with patch.object(c, 'query', return_value=dict(prior, stdout=str(self.driver))):
            with self.assertRaisesRegex(ValueError, 'selection'):
                c.check(snapshot)

    def log(self):
        lto = self.root / 'lto-wrapper'
        return ('COLLECT_GCC=' + str(self.driver) + '\nCOLLECT_LTO_WRAPPER=' + str(lto) + '\n' +
                str(self.tool) + ' -plugin ' + str(self.plugin) + ' -plugin-opt=' + str(lto) + '\n')

    def test_actual_binding_exact(self):
        result = c.bindings(self.log())
        self.assertEqual(result['driver'], str(self.driver))
        self.assertEqual(result['plugin'], str(self.plugin))

    def test_duplicate_driver_binding_rejected(self):
        with self.assertRaises(ValueError):
            c.bindings(self.log() + 'COLLECT_GCC=' + str(self.driver) + '\n')

    def test_duplicate_plugin_binding_rejected(self):
        with self.assertRaises(ValueError):
            c.bindings(self.log().rstrip() + ' -plugin /unknown/plugin.so\n')

    def test_wrapper_disagreement_rejected(self):
        with self.assertRaises(ValueError):
            c.bindings(self.log().replace('-plugin-opt=', '-unknown-opt='))

    def test_relative_binding_rejected(self):
        with self.assertRaises(ValueError):
            c.bindings(self.log().replace('COLLECT_GCC=' + str(self.driver), 'COLLECT_GCC=driver'))

    def test_unresolved_plugin_file_query_uses_only_actual_absolute_binding(self):
        log = self.root / 'driver.log'
        log.write_text(self.log())
        programs = {name: self.file(name, name.encode()) for name in c.PROGRAMS}
        def answer(driver, option):
            value = ('liblto_plugin.so' if option.startswith('-print-file-name=') else
                     str(programs[option.split('=', 1)[1]]))
            return dict(argv=[str(driver), *c.FLAGS, option], stdout=value)
        with patch.object(c, 'query', side_effect=answer):
            snapshot = c.capture(self.driver, log, host_dependencies=False)
        self.assertEqual(snapshot['plugin_resolution'],
                         'unresolved-file-query; selected-absolute-actual-driver-log')
        self.assertIn(str(self.plugin), [row['path'] for row in snapshot['pins']])
        def bad_answer(driver, option):
            value = answer(driver, option)
            if option.startswith('-print-file-name='):
                value['stdout'] = 'another_relative_plugin.so'
            return value
        with patch.object(c, 'query', side_effect=bad_answer):
            with self.assertRaises(ValueError):
                c.capture(self.driver, log, host_dependencies=False)


if __name__ == '__main__':
    unittest.main()