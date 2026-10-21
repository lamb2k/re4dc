"""Malformed checkpoint and input-identity guards, using synthetic bytes only."""
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import zlib

import checkpoint


class CheckpointTests(unittest.TestCase):
    def test_container_decode_and_reject_truncation_or_trailing_bytes(self):
        raw = bytes(16*1024**2)
        compressed = zlib.compress(raw)
        blob = b'FLYSAVE1' + bytes(12) + struct.pack('<I', 0)
        blob += b'#RZIPv\x01#' + struct.pack('<IQ', len(raw), len(raw))
        blob += struct.pack('<I', len(compressed)) + compressed
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'synthetic.state'
            path.write_bytes(blob)
            self.assertEqual(checkpoint.decode(path), raw)
            for invalid in (blob[:-1], blob+b'x', b'unknown!'+blob[8:]):
                path.write_bytes(invalid)
                with self.assertRaises((ValueError, zlib.error)):
                    checkpoint.decode(path)

    def test_seed_rejects_changed_disc_emulator_and_serialized_data(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root/'data').mkdir()
            (root/'data'/'disc.state').write_bytes(b'synthetic only')
            exe = root/'flycast.exe'
            exe.write_bytes(b'emulator identity')
            audit = dict(qa_flags=0)
            row = dict(input={'disc': 'bound'}, emulator_sha256=checkpoint.sha(exe),
                       data=checkpoint.files(root/'data'), audit=audit)
            (root/'checkpoint.json').write_text(json.dumps(row))
            with patch.object(checkpoint, 'audit', return_value=audit):
                self.assertEqual(checkpoint.verify(root, None, None, None, {'disc':'bound'}, exe), row)
                with self.assertRaises(ValueError):
                    checkpoint.verify(root, None, None, None, {'disc':'other'}, exe)
                exe.write_bytes(b'other emulator')
                with self.assertRaises(ValueError):
                    checkpoint.verify(root, None, None, None, {'disc':'bound'}, exe)
                exe.write_bytes(b'emulator identity')
                (root/'data'/'disc.state').write_bytes(b'changed')
                with self.assertRaises(ValueError):
                    checkpoint.verify(root, None, None, None, {'disc':'bound'}, exe)

    def test_all_four_code_anchors_must_match(self):
        ram = bytearray(16*1024**2)
        code = bytearray(0x180100)
        va = 0x8c100000
        for index, offset in enumerate((0x4000, 0x40000, 0x100000, 0x180000)):
            value = bytes(range(256))[index:] + bytes(range(256))[:index]
            code[offset:offset+256] = value
            ram[va+offset-0x8c000000:va+offset-0x8c000000+256] = value
        symbols = dict(pG='0x8c000100', pPL='0x8c000104', head='0x8c000108',
                       SceSys='0x8c00010c', qa_flags='0x8c000110')
        struct.pack_into('<II', ram, 0x100, 0x8c001000, 0x8c002000)
        fields = {'GlobalWork': [('room_id',0),('Frame_cnt',4),('Stop_flg',8),('pl_life',12),('pl_life_max',14)],
                  'cModel': [('pos',0),('r_no_0',12)], 'cSceSys':[('event_start_cnt',0)]}
        shape = dict(elf_sha256='bound', found={kind:dict(members=[dict(name=n,offset=o) for n,o in rows])
                                               for kind,rows in fields.items()})
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            state=root/'synthetic.state'; state.write_bytes(b'fake container')
            binding=root/'binding.json'; binding.write_text(json.dumps(dict(elf_sha256='bound',symbols=symbols)))
            layout=root/'layout.json'; layout.write_text(json.dumps(shape))
            with patch.object(checkpoint,'sha',return_value='bound'), patch.object(checkpoint,'text_section',return_value=(va,code)):
                with patch.object(checkpoint,'decode',return_value=b'x'*1024+ram):
                    self.assertEqual(checkpoint.audit(state,None,binding,layout)['ram_serialization_offset'],1024)
                ram[va+0x180000-0x8c000000] ^= 1
                with patch.object(checkpoint,'decode',return_value=b'x'*1024+ram):
                    with self.assertRaises(ValueError):
                        checkpoint.audit(state,None,binding,layout)


if __name__ == '__main__':
    unittest.main()
