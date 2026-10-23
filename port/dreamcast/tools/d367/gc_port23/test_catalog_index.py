import unittest
from catalog_index import build, Reader, Epochs, sha, HEADER, RECORD, ORIGINS


class IndexedCatalogTests(unittest.TestCase):
    def setUp(self):
        self.rows = [{'kind': 'texture', 'id': 'gc-key', 'sha256': sha(b'PS2 pixels').hex(), 'provenance': 'ps2', 'evidence': 'reviewed exact proof'},
                     {'kind': 'model', 'id': 'member-a', 'sha256': sha(b'GC BIN').hex(), 'provenance': 'unknown', 'evidence': 'unproved original'}]
        self.blob, self.pin = build(self.rows)

    def reader(self, blob=None, pin=None):
        data = self.blob if blob is None else blob
        return Reader(lambda offset, count: data[offset:offset+count], len(data), self.pin if pin is None else pin)

    def test_exact_full_payload_and_generation(self):
        epochs = Epochs();epochs.install(self.reader())
        good = epochs.bind('texture', 'gc-key', sha(b'PS2 pixels'))
        self.assertEqual(epochs.resolve(good)[3], ORIGINS['ps2'])
        changed = epochs.bind('texture', 'gc-key', sha(b'changed pixels'))
        self.assertEqual(epochs.resolve(changed)[3], ORIGINS['unknown'])
        self.assertEqual(len(epochs.unknown), 1)
        epochs.install(self.reader())
        with self.assertRaisesRegex(ValueError, 'stale'):epochs.resolve(good)
        with self.assertRaisesRegex(ValueError, 'stale'):epochs.resolve(changed)

    def test_pinned_record_and_file_mutation_rejected(self):
        with self.assertRaisesRegex(ValueError, 'pin'):self.reader(pin=bytes(32))
        mutated = bytearray(self.blob);mutated[HEADER.size+96] = ORIGINS['ps2']
        with self.assertRaisesRegex(ValueError, 'pin'):self.reader(mutated)
        mutated = bytearray(self.blob);mutated[-1] ^= 1
        with self.assertRaisesRegex(ValueError, 'pin'):self.reader(mutated)

    def test_reordered_record_short_bounds_and_index_rejected(self):
        swapped = self.blob[:HEADER.size]+self.blob[HEADER.size+RECORD.size:HEADER.size+2*RECORD.size]+self.blob[HEADER.size:HEADER.size+RECORD.size]+self.blob[HEADER.size+2*RECORD.size:]
        with self.assertRaisesRegex(ValueError, 'pin'):self.reader(swapped)
        with self.assertRaises(ValueError):self.reader(self.blob[:-1])
        with self.assertRaisesRegex(ValueError, 'range'):self.reader().record(2)
        with self.assertRaises(ValueError):build(self.rows+self.rows[:1])
        bad=[dict(self.rows[0],id='*')]
        with self.assertRaises(ValueError):build(bad)

    def test_unknown_capacity_retirement_and_epoch_exhaustion(self):
        epochs=Epochs();epochs.install(self.reader())
        for i in range(8):
            token=epochs.bind('sound','bank-'+str(i),sha(bytes([i])))
            self.assertEqual(epochs.resolve(token)[3],ORIGINS['unknown'])
        with self.assertRaisesRegex(ValueError,'overflow'):epochs.bind('sound','bank-8',sha(b'8'))
        epochs.install(self.reader())
        with self.assertRaisesRegex(ValueError,'stale'):epochs.resolve(token)
        epochs.epoch=(1<<18)-2
        with self.assertRaisesRegex(ValueError,'exhausted'):epochs.install(self.reader())

    def test_nontexture_consumers_and_no_origin_inference(self):
        epochs=Epochs();epochs.install(self.reader())
        for kind in ('model','geometry','layout','font','ui','sound','stream','movie'):
            token=epochs.bind(kind,'ps2-looking-name',sha(kind.encode()))
            self.assertEqual(epochs.resolve(token)[3],ORIGINS['unknown'])
        self.assertEqual(len(epochs.unknown),8)
        self.assertEqual(build(list(reversed(self.rows))), (self.blob,self.pin))


if __name__ == '__main__':unittest.main()
