import io
import unittest

import pycdlib
from cx_iso_names import iso_primary_name, ensure_free_primary


class PrimaryAliases(unittest.TestCase):
    def test_existing_single_extension_aliases_unchanged(self):
        for name in ('ps2-world.re4mesh', 'abcd1234-00112233.re4tex', 'em18.drs', '1ST_READ.BIN'):
            self.assertEqual(iso_primary_name(name), name.upper().replace('-', '_'))

    def test_double_extension_roundtrip_in_both_runtime_namespaces(self):
        iso = pycdlib.PyCdlib()
        iso.new(interchange_level=3, joliet=3, rock_ridge='1.09')
        name = 'e113.evd.evq'
        stream = io.BytesIO(b'qualified event certificate')
        iso.add_fp(stream, len(stream.getvalue()), iso_path='/' + iso_primary_name(name) + ';1',
                   rr_name=name, joliet_path='/' + name)
        binary = io.BytesIO()
        iso.write_fp(binary)
        iso.close()
        binary.seek(0)
        check = pycdlib.PyCdlib()
        check.open_fp(binary)
        for namespace in ('rr_path', 'joliet_path'):
            extracted = io.BytesIO()
            check.get_file_from_iso_fp(extracted, **{namespace: '/' + name})
            self.assertEqual(extracted.getvalue(), stream.getvalue())
        self.assertEqual(check.get_record(iso_path='/E113_EVD.EVQ;1').file_identifier(), b'E113_EVD.EVQ;1')
        check.close()

    def test_alias_collision_fails_instead_of_replacing_payload(self):
        iso = pycdlib.PyCdlib()
        iso.new(interchange_level=3, joliet=3, rock_ridge='1.09')
        streams = [io.BytesIO(b'a'), io.BytesIO(b'b')]
        for i, name in enumerate(('e113.evd.evq', 'e113_evd.evq')):
            if i:
                with self.assertRaisesRegex(ValueError, 'collides'):
                    ensure_free_primary(iso, '/' + iso_primary_name(name) + ';1')
            else:
                ensure_free_primary(iso, '/' + iso_primary_name(name) + ';1')
                iso.add_fp(streams[i], 1, iso_path='/' + iso_primary_name(name) + ';1',
                           rr_name=name, joliet_path='/' + name)
        iso.close()


if __name__ == '__main__':
    unittest.main()
