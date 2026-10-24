import hashlib
import json
import struct
import tempfile
import unittest
from pathlib import Path

import build_catalog
from catalog_index import Reader, Epochs, ORIGINS


def archive(members):
    """Runtime archive table: count, rel, pad, offsets[count], tags[count], payloads."""
    count = len(members)
    at = 16 + count * 8
    offsets, body = [], b''
    for _tag, data in members:
        offsets.append(at + len(body))
        body += data
    head = struct.pack('<4I', count, 0, 0, 0) + b''.join(struct.pack('<I', o) for o in offsets)
    head += b''.join(tag.ljust(4, b'\0') for tag, _ in members)
    return head + body


def texpak(entries):
    count = len(entries)
    index, data = 2048, 4096
    head = b'RE4PAK1\0' + struct.pack('<4I', 1, count, index, data)
    head = head.ljust(2048, b'\0')
    idx, body = b'', b''
    for (crc, fnv), payload in entries:
        idx += struct.pack('<4I', crc, fnv, data + len(body), len(payload))
        body += payload
    return head + idx.ljust(2048, b'\0') + body


class BuildCatalogTests(unittest.TestCase):
    def make(self, root):
        disc = root / 'disc'
        (disc / 'dc/movie').mkdir(parents=True)
        (disc / 'dc/tex/r100').mkdir(parents=True)
        (disc / 'bgm').mkdir()
        (disc / 'st1').mkdir()
        tex = b'RE4DCTX\0' + b'pixels' * 4
        (disc / 'dc/tex.pak').write_bytes(texpak([((0x12, 0x34), tex)]))
        (disc / 'dc/tex/r100/0000abcd-00001234.re4tex').write_bytes(b'RE4DCTX\0loose')
        (disc / 'dc/movie/r101s30.seq').write_bytes(b'movie' * 10)
        (disc / 'dc/movie/r104s00c.seq').write_bytes(b'clip' * 10)
        (disc / 'bgm/aica_str.dat').write_bytes(b'AIS1stream')
        self.bin = b'B' * 80
        (disc / 'st1/r100_00.dat').write_bytes(archive([(b'BIN', self.bin), (b'TPL', b'T' * 32)]))
        manifest = {p.relative_to(disc).as_posix(): {'size': p.stat().st_size}
                    for p in disc.rglob('*') if p.is_file()}
        mpath = root / 'manifest.json'
        mpath.write_text(json.dumps(manifest))
        return disc, mpath

    def run_build(self, root, out, proofs=None):
        disc, mpath = self.make(root) if not (root / 'disc').exists() else (root / 'disc', root / 'manifest.json')
        msha = hashlib.sha256(mpath.read_bytes()).hexdigest()
        args = ['--disc-dir', str(disc), '--manifest', str(mpath), '--manifest-sha256', msha, '--out-dir', str(out)]
        if proofs:
            ppath = root / 'proofs.json'
            ppath.write_text(json.dumps(proofs))
            args += ['--proofs', str(ppath), '--proofs-sha256', hashlib.sha256(ppath.read_bytes()).hexdigest()]
        build_catalog.main(args)
        return json.loads((out / 'catalog.json').read_text())['entries'], (out / 'gc-assets.idx').read_bytes()

    def test_kinds_ids_and_determinism(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            rows, blob = self.run_build(root, root / 'o1')
            keys = {(r['kind'], r['id']) for r in rows}
            self.assertIn(('texture', '00000012-00000034'), keys)
            self.assertIn(('texture', '0000abcd-00001234'), keys)
            self.assertIn(('movie', '10130'), keys)
            self.assertIn(('movie', '1010400'), keys)
            self.assertIn(('sound-stream', 'aica-str-dat'), keys)
            digest = hashlib.sha256(self.bin)
            self.assertIn(('model', digest.hexdigest()[:40]), keys)
            self.assertTrue(all(r['provenance'] == 'unknown' for r in rows))
            _rows2, blob2 = self.run_build(root, root / 'o2')
            self.assertEqual(blob, blob2)
            pin = hashlib.sha256(blob).digest()
            epochs = Epochs()
            epochs.install(Reader(lambda o, c: blob[o:o + c], len(blob), pin))
            token = epochs.bind('model', digest.hexdigest()[:40], digest.digest())
            self.assertEqual(epochs.resolve(token)[3], ORIGINS['unknown'])
            self.assertEqual(epochs.unknown, [])

    def test_proof_sets_provenance_and_unmatched_proof_refused(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            self.make(root)
            movie = hashlib.sha256(b'movie' * 10).hexdigest()
            rows, _ = self.run_build(root, root / 'o1', dict(schema=1, entries=[
                dict(kind='movie', id='10130', sha256=movie, provenance='ps2', evidence='reviewed PS2 FMV')]))
            self.assertEqual([r['provenance'] for r in rows if r['kind'] == 'movie' and r['id'] == '10130'], ['ps2'])
            with self.assertRaises(SystemExit):
                self.run_build(root, root / 'o2', dict(schema=1, entries=[
                    dict(kind='movie', id='10130', sha256='0' * 64, provenance='ps2', evidence='x')]))

    def test_manifest_mismatch_refused(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            disc, _ = self.make(root)
            (disc / 'extra.bin').write_bytes(b'x')
            with self.assertRaises(SystemExit):
                self.run_build(root, root / 'o1')


if __name__ == '__main__':
    unittest.main()
