#!/usr/bin/env python3
"""Small synthetic negatives; opt-in exact historical pack acceptance test."""
import importlib.util
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

spec = importlib.util.spec_from_file_location("seed", Path(__file__).with_name("build_reviewed_seed.py"))
s = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s)
K1, K2, K3 = "00000001-00000002", "00000003-00000004", "00000005-00000006"


class SeedTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="gc-seed-test-", dir="/dev/shm" if Path("/dev/shm").is_dir() else None)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = self.root / "readonly-store"
        self.store.mkdir()
        self.path = self.store / "tex.pak"
        self.payloads = [b"RE4DCTX\0" + b"header-a" + b"pixels", b"RE4DCTX\0" + b"header-b" + b"other"]
        data = 64
        first, second = self.payloads
        pak = struct.pack("<8s4I", b"RE4PAK1\0", 1, 2, 24, data)
        pak += struct.pack("<4I", 1, 2, data, len(first))
        pak += struct.pack("<4I", 3, 4, data + len(first), len(second))
        pak += b"\0" * (data - len(pak)) + first + second
        self.path.write_bytes(pak)
        self.audit = ("key\tbytes\tclass\tin_use_rooms\tresident\tevidence\n"
                      f"{K1}\t{len(first)}\tPS2-native\tr100,r111\t0\tdc/native/claimed-ps2\n"
                      f"{K2}\t{len(second)}\tstore-other\t\t1\tlocal-vq-made\n").encode()
        self.manifest = {"dc/tex.pak": dict(sha256=s.digest(pak), size=len(pak))}
        self.package = {"replace": {"dc/tex.pak": str(self.path)}}

    def generate(self, proofs=None):
        return s.generate(self.audit, s.encode(self.manifest), s.encode(self.package),
                          [self.store], "historical-audit.tsv", s.encode(proofs) if proofs is not None else None)

    def update_pack_manifest(self):
        raw = self.path.read_bytes()
        self.manifest["dc/tex.pak"] = dict(sha256=s.digest(raw), size=len(raw))

    def proof(self, provenance="ps2"):
        return dict(schema=1, entries=[dict(kind="texture", id=K1, sha256=s.digest(self.payloads[0]),
                    provenance=provenance, source="independently reviewed source receipt", evidence="reviewed receipt digest")])

    def test_full_member_hash_and_determinism(self):
        before = self.path.stat()
        a, b = self.generate(), self.generate()
        self.assertEqual({k: s.encode(v) for k, v in a.items()}, {k: s.encode(v) for k, v in b.items()})
        row = a["catalog.json"]["entries"][0]
        self.assertEqual(row["sha256"], s.digest(self.payloads[0]))
        self.assertNotEqual(row["sha256"], s.digest(b"pixels"))
        self.assertEqual(s.fingerprint(before), s.fingerprint(self.path.stat()))

    def test_old_ps2_and_local_conversion_are_unknown(self):
        docs = self.generate()
        self.assertEqual([r["provenance"] for r in docs["catalog.json"]["entries"]], ["unknown", "unknown"])
        self.assertEqual(docs["seed-report.json"]["unproven_old_ps2_rows"], 1)

    def test_loaded_rooms_only_no_resident_expansion(self):
        docs = self.generate()
        self.assertEqual([r["room"] for r in docs["reviewed-seed.json"]["entries"]], ["0100", "0111"])
        self.assertTrue(all(r["id"] == K1 for r in docs["reviewed-seed.json"]["entries"]))
        self.assertEqual(docs["seed-report.json"]["history"][0]["emitted_rooms"], [])
        self.assertTrue(docs["seed-report.json"]["no_emission_or_gate_pass_claim"])

    def test_exact_reviewed_proof_removes_only_matching_exceptions(self):
        docs = self.generate(self.proof())
        self.assertEqual(docs["catalog.json"]["entries"][0]["provenance"], "ps2")
        self.assertEqual(docs["reviewed-seed.json"]["entries"], [])
        self.assertEqual(len(docs["catalog.json"]["entries"]), 2)

    def test_reviewed_gc_remains_gc(self):
        docs = self.generate(self.proof("gc"))
        self.assertEqual({r["provenance"] for r in docs["reviewed-seed.json"]["entries"]}, {"gc"})

    def test_stale_wrong_unknown_or_duplicate_proofs_rejected(self):
        for mutate in (lambda r: r.update(sha256="a" * 64), lambda r: r.update(id=K3),
                       lambda r: r.update(room="0111"), lambda r: r.update(provenance="store-made")):
            proof = self.proof()
            mutate(proof["entries"][0])
            with self.assertRaises(ValueError):
                self.generate(proof)
        proof = self.proof()
        proof["entries"] *= 2
        with self.assertRaisesRegex(ValueError, "duplicate reviewed"):
            self.generate(proof)

    def test_duplicate_json_key_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate JSON"):
            s.decode_json(b'{"schema":1,"schema":1,"entries":[]}')

    def test_audit_duplicate_wildcard_and_bad_rooms_rejected(self):
        original = self.audit
        bad = [original + original.splitlines(keepends=True)[1],
               original.replace(b"r100,r111", b"r100,*"),
               original.replace(b"r100,r111", b"r100,r100"),
               original.replace(b"r100,r111", b"0100"),
               original.replace(b"store-other", b"authored")]
        for raw in bad:
            self.audit = raw
            with self.assertRaises(ValueError):
                self.generate()

    def test_stale_manifest_hash_rejected(self):
        self.path.write_bytes(self.path.read_bytes()[:-1] + b"!")
        with self.assertRaisesRegex(ValueError, "SHA256/size"):
            self.generate()

    def test_mid_read_mutation_and_path_replacement_rejected(self):
        original = self.path.read_bytes()
        real_hash = s.hash_file
        for replace in (False, True):
            self.path.write_bytes(original)
            first_call = True

            def changing_hash(fp):
                nonlocal first_call
                result = real_hash(fp)
                if first_call:
                    first_call = False
                    if replace:
                        other = self.store / "replacement.pak"
                        other.write_bytes(original)
                        other.replace(self.path)
                    else:
                        self.path.write_bytes(original[:-1] + b"!")
                return result

            with mock.patch.object(s, "hash_file", changing_hash):
                with self.assertRaisesRegex(ValueError, "mutated|changed"):
                    self.generate()

    def test_member_set_and_size_mismatch_rejected(self):
        self.audit = self.audit.replace(K2.encode(), K3.encode())
        with self.assertRaisesRegex(ValueError, "identity set"):
            self.generate()
        self.audit = self.audit.replace(K3.encode(), K2.encode()).replace(
            f"{len(self.payloads[0])}\tPS2".encode(), b"8\tPS2")
        with self.assertRaisesRegex(ValueError, "member size"):
            self.generate()

    def test_duplicate_overlapping_and_out_of_bounds_pack_rejected(self):
        original = self.path.read_bytes()
        for offset, values in ((40, (1, 2, 90, 21)), (40, (3, 4, 64, 21)), (40, (3, 4, 9999, 21))):
            raw = bytearray(original)
            struct.pack_into("<4I", raw, offset, *values)
            self.path.write_bytes(raw)
            self.update_pack_manifest()
            with self.assertRaises(ValueError):
                self.generate()

    def test_invalid_member_header_rejected(self):
        raw = self.path.read_bytes().replace(b"RE4DCTX\0", b"RE4FAKE\0", 1)
        self.path.write_bytes(raw)
        self.update_pack_manifest()
        with self.assertRaisesRegex(ValueError, "RE4TEX member"):
            self.generate()

    def test_private_store_escape_and_symlink_escape_rejected(self):
        outside = self.root / "outside.pak"
        outside.write_bytes(self.path.read_bytes())
        self.package["replace"]["dc/tex.pak"] = str(outside)
        with self.assertRaisesRegex(ValueError, "outside intended store"):
            self.generate()
        link = self.store / "escape.pak"
        link.symlink_to(outside)
        self.package["replace"]["dc/tex.pak"] = str(link)
        with self.assertRaisesRegex(ValueError, "outside intended store"):
            self.generate()

    def test_pinned_input_change_rejected(self):
        path = self.root / "audit.tsv"
        path.write_bytes(self.audit)
        self.assertEqual(s.pinned(path, s.digest(self.audit)), self.audit)
        path.write_bytes(self.audit + b"\n")
        with self.assertRaisesRegex(ValueError, "pinned input"):
            s.pinned(path, s.digest(self.audit))

    def test_cli_new_output_only_and_readback(self):
        args = [sys.executable, str(Path(s.__file__))]
        for name, raw in (("audit", self.audit), ("manifest", s.encode(self.manifest)), ("package", s.encode(self.package))):
            path = self.root / (name + ".input")
            path.write_bytes(raw)
            args += ["--" + name, str(path), "--" + name + "-sha256", s.digest(raw)]
        output = self.root / "new-output"
        args += ["--store-root", str(self.store), "--out-dir", str(output)]
        result = subprocess.run(args, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads((output / "reviewed-seed.json").read_text()), self.generate()["reviewed-seed.json"]
                         | {"entries": [dict(row, evidence=row["evidence"].replace("historical-audit.tsv", str((self.root / "audit.input").resolve())))
                                        for row in self.generate()["reviewed-seed.json"]["entries"]]})
        before = {p.name: p.read_bytes() for p in output.iterdir()}
        self.assertNotEqual(subprocess.run(args, capture_output=True).returncode, 0)
        self.assertEqual(before, {p.name: p.read_bytes() for p in output.iterdir()})


class HistoricalPackTest(unittest.TestCase):
    @unittest.skipUnless(os.environ.get("GC_SEED_REAL_EVIDENCE"), "set GC_SEED_REAL_EVIDENCE for readonly old audited texture acceptance")
    def test_exact_historical_texture_sample(self):
        root = Path(os.environ["GC_SEED_REAL_EVIDENCE"])
        audit = s.pinned(root / "texpak-provenance.tsv", "e8de763caefc275493cc528aae6f9dad2eb14b8fb9a88dce7acc415e24f7ac02")
        manifest = s.pinned(root / "manifest-rre17af64rP.json", "99b84279afca69be7fc755a970456548b19eb728f3d9e9252a2eb35a56287b8d")
        package = s.pinned(root / "pkg-rre17af64rP.json", "c3eaa42015af9f1be44484f340006f03b1ccb7653ddc5ea2a457d6a1e65d0d37")
        docs = s.generate(audit, manifest, package, ["/root/re4data/private"], str(root / "texpak-provenance.tsv"))
        self.assertEqual(docs["seed-report.json"]["pack_sha256"], "5bba464a1175d8ebe153d5aecb629ea9637807c2bf4fc438a32c17148d0729da")
        # Full real member, including the immutable header, pinned in the receipt.
        sample = next(r for r in docs["catalog.json"]["entries"] if r["id"] == "001c0ae3-f6006faa")
        self.assertEqual(sample["provenance"], "unknown")
        self.assertEqual(sample["sha256"], "f9583d532b4dbe5f78a7bb2d4a068a0df5cd792623ca063abfd802b68d00f766")


if __name__ == "__main__":
    unittest.main(verbosity=2)
