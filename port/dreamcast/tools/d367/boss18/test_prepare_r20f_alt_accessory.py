"""Asset-free checks of the exact additive header transformation."""
import unittest
from prepare_r20f_alt_accessory import alias_chunk

ROW0 = '{0,3,3,1,1,64,i0_pos,i0_nrm,i0_uv,i0_gx,i0_weights}'
ROW1 = '{1,7,8,2,5,128,i1_pos,i1_nrm,i1_uv,i1_gx,i1_weights}'
PREFIX = '// arrays and source flags remain verbatim\nstatic const unsigned flags=12;\n'
SUFFIX = '\nstatic constexpr unsigned bone_count=37;\n'


def header(rows):
    return PREFIX + 'static Chunk chunks[] = {\n' + ',\n'.join(rows) + ',\n};' + SUFFIX


class AdditiveHeader(unittest.TestCase):
    def test_only_new_record_is_added_and_uses_original_arrays(self):
        before = header([ROW0, ROW1])
        expected = header([ROW0, ROW1, '{2,7,8,2,5,128,i1_pos,i1_nrm,i1_uv,i1_gx,i1_weights}'])
        self.assertEqual(alias_chunk(before, 1, 2), expected)

    def test_alias_can_reference_an_earlier_existing_role(self):
        before = header([ROW0, ROW1])
        expected = header([ROW0, ROW1, '{2,3,3,1,1,64,i0_pos,i0_nrm,i0_uv,i0_gx,i0_weights}'])
        self.assertEqual(alias_chunk(before, 0, 2), expected)

    def test_existing_new_info_is_refused(self):
        with self.assertRaisesRegex(ValueError, 'append next'):
            alias_chunk(header([ROW0, ROW1]), 1, 1)

    def test_a_gap_is_refused(self):
        with self.assertRaisesRegex(ValueError, 'append next'):
            alias_chunk(header([ROW0, ROW1]), 1, 3)

    def test_missing_original_is_refused(self):
        with self.assertRaisesRegex(ValueError, 'source alias'):
            alias_chunk(header([ROW0, ROW1]), 7, 2)

    def test_duplicate_source_identity_is_refused(self):
        with self.assertRaisesRegex(ValueError, 'duplicate source'):
            alias_chunk(header([ROW0, ROW1, ROW1]), 1, 2)

    def test_mixed_array_sources_are_refused(self):
        mixed = ROW1.replace('i1_nrm', 'i0_nrm')
        with self.assertRaisesRegex(ValueError, 'mixed array'):
            alias_chunk(header([ROW0, mixed]), 1, 2)

    def test_multiple_chunk_tables_are_refused(self):
        with self.assertRaisesRegex(ValueError, 'one chunk table'):
            alias_chunk(header([ROW0, ROW1]) * 2, 1, 2)


if __name__ == '__main__':
    unittest.main()
