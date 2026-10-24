#!/usr/bin/env python3
"""Public exact-layout, sidecar, malformed-input and real builder OFF controls."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import unittest
import zlib

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
TOOLS = HERE.parents[1]
ROOT = TOOLS.parents[2]
sys.path.insert(0, str(TOOLS))
import scenery_data_variants as layout
from d367.visibility23 import metadata
from fixtures import package, wrapper, capacity

BASELINE = "057e00a248c9ed473d0b3377a0ce14b0b2f5186d"


def repaired(blob):
    out = bytearray(blob)
    struct.pack_into("<I", out, 12, zlib.crc32(out[80:]))
    return bytes(out)


def ordered_geometry(raw):
    """Independent strip decoder: exact raw corner records in part/LOD order."""
    h = struct.unpack_from("<4s19I", raw)
    lod = struct.unpack_from("<8I", raw, 80)
    strips = []
    for i in range(h[6]):
        fv, fs, size, count, bits, *bounds = struct.unpack_from("<IIIHH6H", raw, h[12]+28*i)
        indices = struct.unpack_from("<%dH" % count, raw, h[14]+fs) if bits & 0x8000 else range(count)
        table = [raw[h[13]+12*(fv+k):h[13]+12*(fv+k+1)] for k in indices]
        start = h[14]+fs+(2*count if bits & 0x8000 else 0)
        end, stream = start+size, []
        while start < end:
            n = raw[start]
            stream.append(tuple(table[k] for k in raw[start+1:start+1+n])); start += 1+n
        strips.append(tuple(stream))
    result = []
    for first, count, _ in struct.iter_unpack("<IIf", raw[lod[4]:lod[4]+12*lod[1]]):
        result.append(tuple(s for chunk in strips[first:first+count] for s in chunk))
    return result


class LayoutTests(unittest.TestCase):
    def test_absolute_meshlet_id_capacity(self):
        raw, side = capacity(65537)
        with self.assertRaisesRegex(ValueError, "meshlet id capacity"):
            layout.convert(raw, "local-indexed", side)
        raw, side = capacity(65536, split_first=True)
        with self.assertRaisesRegex(ValueError, "expanded meshlet id capacity"):
            layout.convert(raw, "direct-strips", side)

    def test_cluster_pick_reservation_before_and_after_expansion(self):
        def duplicated_clusters(count, selected, split=False):
            raw, side = capacity(count, split_first=split)
            source = layout.Package(raw)
            sections = dict(source.sections)
            sections["cluster"] *= 2
            sections["part_lod"] = layout.fmt.PART_LOD.pack(0, 2)
            sections["level"] = layout.fmt.LEVEL.pack(0, selected, 0)
            head, body = layout.pack(source, sections, source.h[6:9])
            struct.pack_into("<I", body, 0, 2)
            head[3] = layout.crc(body)
            return bytes(layout.fmt.HEADER.pack(*head)+body), side

        # Overlap is not itself forbidden; its maximum simultaneous picks
        # must fit the part-sized reservation used by the actual selector.
        safe, side = duplicated_clusters(161, 80)
        for variant in layout.MARKERS:
            layout.convert(safe, variant, side)
        unsafe, side = duplicated_clusters(161, 161)
        for variant in layout.MARKERS:
            with self.assertRaisesRegex(ValueError, "pick capacity"):
                layout.convert(unsafe, variant, side)
        # A valid source can exceed the reservation after SDS1 splits a
        # repeatedly referenced parent; validate the output too.
        split, side = duplicated_clusters(2, 1, split=True)
        layout.convert(split, "local-indexed", side)
        with self.assertRaisesRegex(ValueError, "pick capacity"):
            layout.convert(split, "direct-strips", side)

    def test_all_public_shapes_preserve_every_ordered_corner(self):
        for kind in ("compact", "limit", "reuse", "unused"):
            for version in (2, 3):
                before, side = package(kind, version)
                original = ordered_geometry(before)
                for variant in layout.MARKERS:
                    with self.subTest(kind=kind, version=version, variant=variant):
                        after, groups, report = layout.convert(before, variant, side)
                        self.assertEqual(ordered_geometry(after), original)
                        self.assertIsNone(groups)
                        self.assertEqual(layout.convert(before, variant, side), (after, groups, report))
                        self.assertEqual(report["source_sha256"], hashlib.sha256(before).hexdigest())
                        self.assertEqual(report["retained_gather_scratch_bytes"], 3072)
                        a, b = layout.Package(before), layout.Package(after, variant)
                        self.assertEqual(b.sections["mesh"], a.sections["mesh"])
                        self.assertEqual(b.h[17:19], (len(before), a.h[3]))
                        if variant == "local-indexed":
                            self.assertEqual(a.h[6], b.h[6])
                            for x, y in zip(a.lets, b.lets):
                                self.assertEqual(x["vertices"], y["vertices"])
                                self.assertEqual(x["strips"], y["strips"])
                                self.assertEqual(x["row"][5:], y["row"][5:])
                        else:
                            self.assertEqual(report["split_children"], 6 if kind in ("reuse", "limit") else 0)
                            for old, (first, count) in zip(a.lets, report["meshlet_remap"]):
                                self.assertTrue(all(new["row"][5:] == old["row"][5:] for new in b.lets[first:first+count]))

    def test_groups_keep_source_selection_bounds_and_strip_membership(self):
        for kind in ("compact", "reuse", "limit"):
            before, side = package(kind)
            for count in (1, 4, 8):
                sg, _ = metadata.build(before, side, count)
                source = layout.Package(before)
                _, src_groups = layout.parse_groups(sg, source, side)
                for variant in layout.MARKERS:
                    after, out, report = layout.convert(before, variant, side, sg)
                    target = layout.Package(after, variant)
                    _, dst_groups = layout.parse_groups(out, target, side)
                    if variant == "local-indexed":
                        self.assertEqual(out[32:], sg[32:])
                    # For every original group, concatenate mapped child strips.
                    for old_li, (first, nchild) in enumerate(report["meshlet_remap"]):
                        for gi, (a, b, rec) in enumerate(src_groups[old_li]):
                            expected = [[source.lets[old_li]["vertices"][k] for k in s]
                                        for s in source.lets[old_li]["strips"][a:b]]
                            actual = []
                            for child in range(first, first+nchild):
                                x, y, row = dst_groups[child][gi]
                                if x < y:
                                    self.assertEqual(row[:6], rec[:6])
                                actual.extend([[target.lets[child]["vertices"][k] for k in s]
                                               for s in target.lets[child]["strips"][x:y]])
                            self.assertEqual(actual, expected)

    def test_refuse_malformed_or_unhandled_source(self):
        raw, side = package()
        h = struct.unpack_from("<4s19I", raw)
        variants = []
        for label, offset, value, form in (
            ("v1", 4, 1, "I"), ("wrong extent", 8, len(raw)-32, "I"),
            ("oct vertex", 64, 3, "I"), ("unknown provenance", 68, 1, "I"),
            ("SDO3", 76, 0x334f4453, "I"), ("unknown runtime tables", 108, 128, "I"),
            ("overlap", 48, h[11], "I"), ("short vertex section", 52, len(raw), "I"),
            ("zero vertices", h[12]+12, 0, "H"), ("local index", h[14]+1, 255, "B"),
            ("strip byte limit", h[12]+8, 0xffffffff, "I"),
            ("short strip", h[14], 2, "B"), ("part partition", h[11]+12, 1, "I"),
            ("bounds exclude data", h[12]+16, 65535, "H")):
            data = bytearray(raw); struct.pack_into("<"+form, data, offset, value)
            variants.append((label, repaired(data)))
        corrupt = bytearray(raw); corrupt[-1] ^= 1; variants.append(("CRC", bytes(corrupt)))
        junk = bytearray(raw); junk[112] = 42; variants.append(("unknown padding", repaired(junk)))
        variants.append(("truncated", raw[:100]))
        for name, data in variants:
            for variant in layout.MARKERS:
                with self.subTest(name=name, variant=variant):
                    with self.assertRaises(ValueError):
                        layout.convert(data, variant, side)

    def test_foreign_policy_groups_and_provenance_refused(self):
        raw, side = package()
        sg, _ = metadata.build(raw, side, 4)
        for blob, is_group in ((side, False), (sg, True)):
            for offset in ((12, 20, 28, len(blob)-1) if is_group else (12, 16, 20, len(blob)-1)):
                changed = bytearray(blob); changed[offset] ^= 1
                with self.subTest(groups=is_group, offset=offset):
                    with self.assertRaises(ValueError):
                        layout.convert(raw, "direct-strips", side if is_group else bytes(changed),
                                       bytes(changed) if is_group else sg)
        after, _, _ = layout.convert(raw, "direct-strips", side)
        changed = bytearray(raw); changed[layout.Package(raw).h[13]+6] ^= 1
        with self.assertRaisesRegex(ValueError, "provenance"):
            layout.validate_pair(repaired(changed), after, "direct-strips", side)
        with self.assertRaises(ValueError):
            layout.convert(after, "local-indexed", side)

    def test_sds_sequential_contract_refused_when_reordered(self):
        raw, side = package()
        after, _, _ = layout.convert(raw, "direct-strips", side)
        p = layout.Package(after, "direct-strips")
        changed = bytearray(after)
        i = p.h[14]+1; changed[i], changed[i+1] = changed[i+1], changed[i]
        with self.assertRaisesRegex(ValueError, "sequential"):
            layout.Package(repaired(changed), "direct-strips")


def builder_controls(output, baseline):
    script = TOOLS/"ps2_world_r4im.py"
    base = output/"baseline/ps2_world_r4im.py"; base.parent.mkdir(parents=True)
    base.write_bytes(subprocess.check_output(["git", "show", baseline+":"+str(script.relative_to(ROOT))], cwd=ROOT))
    mesh, inc = wrapper(output/"source")
    env = dict(os.environ, PYTHONPATH=str(TOOLS), PYTHONDONTWRITEBYTECODE="1")
    records = {}
    for name, command, flags in (("baseline", base, []), ("absent", script, []),
          ("local-indexed", script, ["--scenery-local-indexed"]),
          ("direct-strips", script, ["--scenery-direct-strips"])):
        folder = output/name; folder.mkdir(exist_ok=True)
        stem = folder/"ps2-world"
        argv = [sys.executable, str(command), str(mesh), str(inc), str(stem), *flags]
        run = subprocess.run(argv, cwd=ROOT, env=env, text=True, capture_output=True)
        (folder/"run.log").write_text(run.stdout+run.stderr)
        require = layout.require
        require(run.returncode == 0, name+" builder failed: "+run.stderr)
        report = json.loads(stem.with_suffix(".json").read_text())
        report["args"]["out"] = "<OUT>"
        records[name] = dict(command=argv, mesh_sha256=layout.sha(stem.with_suffix(".re4mesh").read_bytes()),
                             policy_sha256=layout.sha(stem.with_suffix(".r4pw").read_bytes()), report=report,
                             normalized_report_bytes_sha256=layout.sha(stem.with_suffix(".json").read_bytes().replace(str(stem).encode(), b"<OUT>")))
        if name != "baseline":
            require(records[name]["mesh_sha256"] == records["baseline"]["mesh_sha256"], "normal mesh changed")
            require(records[name]["policy_sha256"] == records["baseline"]["policy_sha256"], "normal policy changed")
        if name == "absent":
            require(report == records["baseline"]["report"], "absent JSON report changed")
            require(records[name]["normalized_report_bytes_sha256"] == records["baseline"]["normalized_report_bytes_sha256"],
                    "absent normalized JSON bytes changed")
        if flags:
            candidate = folder/(layout.STEMS[name]+".re4mesh")
            layout.validate_pair(stem.with_suffix(".re4mesh").read_bytes(), candidate.read_bytes(), name,
                                 stem.with_suffix(".r4pw").read_bytes())
    run = subprocess.run([sys.executable, str(script), str(mesh), str(inc), str(output/"conflict"),
                         "--scenery-local-indexed", "--scenery-direct-strips"], env=env, capture_output=True)
    layout.require(run.returncode != 0, "conflicting CLI flags accepted")
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--baseline", default=BASELINE)
    args = parser.parse_args()
    out = args.output.resolve(); out.mkdir(parents=True, exist_ok=False)
    inputs = [Path(__file__), HERE/"fixtures.py", TOOLS/"scenery_data_variants.py", TOOLS/"ps2_world_r4im.py",
              TOOLS/"convert_room_bins.py", TOOLS/"d367/visibility23/metadata.py"]
    hashes = {str(p.relative_to(ROOT)): layout.sha(p.read_bytes()) for p in inputs}
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(LayoutTests)
    with (out/"unit-tests.txt").open("w") as log:
        result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    layout.require(result.wasSuccessful(), (out/"unit-tests.txt").read_text())
    builders = builder_controls(out/"builders", args.baseline)
    fixtures = {}
    folder = out/"fixtures"; folder.mkdir()
    for kind in ("compact", "reuse", "limit", "unused"):
        raw, side = package(kind)
        sg, _ = metadata.build(raw, side, 4)
        (folder/(kind+".re4mesh")).write_bytes(raw)
        (folder/(kind+".r4pw")).write_bytes(side)
        (folder/(kind+".r4sg")).write_bytes(sg)
        fixtures[kind] = {}
        for variant in layout.MARKERS:
            after, groups, stats = layout.convert(raw, variant, side, sg)
            stem = kind+"-"+layout.STEMS[variant]
            (folder/(stem+".re4mesh")).write_bytes(after)
            (folder/(stem+".r4sg")).write_bytes(groups)
            fixtures[kind][variant] = stats
    for path, expected in hashes.items():
        layout.require(layout.sha((ROOT/path).read_bytes()) == expected, "source changed: "+path)
    report = dict(status="PASS", scope=__doc__, baseline=args.baseline, source_sha256=hashes,
        unit_tests=result.testsRun, exact_corner_cases=16, groups_cases=18,
        capacity_controls=dict(meshlet_id="Reject source count65537 and SDS1 expansion65536 to65537; valid boundary admission is checked by actual C++ reader.",
            picks="Admit overlapping160 of161 reserved Picks; reject322 of161; reject source-valid SDS1 expansion selecting4 with reservation3."),
        builders=builders, fixtures=fixtures,
        occlusion_identity=dict(
            readers=["game/platform/room_occl.c", "game/platform/native_static.cpp::re4dc_ps2_world_intact",
                     "game/platform/native_static.cpp::re4dc_ps2_placements_intact"],
            runtime_inputs="OCCL v2 policy CRC at byte12, independent slab/cell/list records, u16 source placement indices and live placement state; no R4IM meshlet/corner IDs.",
            preserved="Exact ordered corner records at every LOD, mesh decode/UV tables, source part identities, LOD errors, material pass/cull, placement order/affines/IDs, parent bounds and supplied group selection bounds/membership.",
            proof_scope="Existing unremapped-policy OCCL geometry/placement meaning is unchanged; no fresh occluder proof or source fingerprint is substituted.",
            excluded="WORLD_RECT21 certificate remaps and mesh-bound PVS/interior/SCCN/SCPS/SDO3 metadata require separate qualification; candidate Make rejects these modes."),
        limitations="Synthetic layout/CLI/metadata proof only; actual renderer gate and target timing are separate.")
    (out/"layout-controls.json").write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps(dict(status="PASS", tests=result.testsRun, report=str(out/"layout-controls.json"))))


if __name__ == "__main__":
    main()
