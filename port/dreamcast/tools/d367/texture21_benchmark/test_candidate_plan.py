import struct
import unittest
import zlib
import prepare_candidate as candidate
import dwarf_layout

class CandidatePlanAdmission(unittest.TestCase):
    def sidecars(self):
        before=bytearray(128);struct.pack_into('<II',before,32,1,2)
        before[40:48]=b'geometry';after=bytearray(before);struct.pack_into('<II',after,32,3,4)
        struct.pack_into('<I',after,20,zlib.crc32(after[32:])&0xffffffff)
        return bytes(before),bytes(after),[{'part':0,'original_key':'00000001-00000002','scoped_key':'00000003-00000004'}]

    def test_only_selected_keys_and_crc_can_change(self):
        self.assertTrue(candidate.sidecar_proof(*self.sidecars())['all_other_bytes_exact'])
        for offset in [40,70,120]:
            before,after,rows=self.sidecars();bad=bytearray(after);bad[offset]^=1
            struct.pack_into('<I',bad,20,zlib.crc32(bad[32:])&0xffffffff)
            with self.assertRaises(ValueError):candidate.sidecar_proof(before,bytes(bad),rows)

    def test_wrong_remap_or_extent_is_rejected(self):
        before,after,rows=self.sidecars();rows[0]['scoped_key']='00000005-00000006'
        with self.assertRaises(ValueError):candidate.sidecar_proof(before,after,rows)
        with self.assertRaises(ValueError):candidate.sidecar_proof(before,after+b'x',rows)

    def test_duplicate_local_symbol_requires_actual_size(self):
        rows=[{'name':'entries','size':4,'address':0x8c400000},
              {'name':'entries','size':224*448,'address':0x8c2b0000}]
        with self.assertRaises(ValueError):candidate.select_symbol(rows,'entries')
        self.assertEqual(candidate.select_symbol(rows,'entries',224*448)['address'],0x8c2b0000)

    def test_missing_complete_dwarf_type_is_rejected(self):
        lines=[' <1><10>: Abbrev Number: 1 (DW_TAG_structure_type)\n',
               ' <11> DW_AT_name : Entry\n',' <12> DW_AT_declaration : 1\n']
        with self.assertRaises(ValueError):dwarf_layout.parse(lines,['Entry'])

if __name__=='__main__':unittest.main()

class PromotedDwarfTests(unittest.TestCase):
 def test_anonymous_nested_union_promotes_room_id(self):
  text=""" <1><1>: Abbrev Number: 1 (DW_TAG_structure_type)
 DW_AT_name : GlobalWork
 DW_AT_byte_size : 34432
 <2><2>: Abbrev Number: 1 (DW_TAG_union_type)
 DW_AT_byte_size : 4
 <3><3>: Abbrev Number: 1 (DW_TAG_structure_type)
 DW_AT_byte_size : 4
 <4><4>: Abbrev Number: 1 (DW_TAG_member)
 DW_AT_name : room_id
 DW_AT_data_member_location : 2
 <4><5>: Abbrev Number: 0
 <3><6>: Abbrev Number: 1 (DW_TAG_member)
 DW_AT_type : <0x3>
 <3><7>: Abbrev Number: 0
 <2><8>: Abbrev Number: 1 (DW_TAG_member)
 DW_AT_type : <0x2>
 DW_AT_data_member_location : 20380
 <2><9>: Abbrev Number: 0
 <1><a>: Abbrev Number: 0
"""
  from dwarf_layout import parse
  self.assertEqual(parse(text.splitlines(),['GlobalWork'])['GlobalWork']['members']['room_id'],20382)
