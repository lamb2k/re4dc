#!/usr/bin/env python3
"""Synthetic native room lists, exact archive identities and refusal fixtures."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import struct
import tempfile
import unittest

import formats as F
import room_lists36 as R
from test_scan import dar, model_bin


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]


def esl(records):
    out = bytearray(32 * max(1, len(records)))
    for index, row in enumerate(records):
        room, enemy, typ, alive = row
        at = index * 32
        out[at:at + 4] = bytes((alive, enemy, typ, 7))
        struct.pack_into("<IH", out, at + 4, 0x80000000, 500)
        struct.pack_into("<3h3hHh", out, at + 12, index, 2, 3, 4, 5, 6, room, 7)
    return bytes(out)


class Tree:
    def __init__(self, root):
        self.root = root
        self.sources = {}
        self.models = []
        self.spawns = []

    def put(self, name, data, kind):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        self.sources[name] = dict(path=name, sha256=F.sha(data), bytes=len(data), format=kind)

    def add_list(self, name="etc/emleon00.esl", records=((0x103, 0x12, 0, 1),)):
        data = esl(records)
        self.put(name, data, "ESL")
        self.spawns.extend(dict(s, source=name, source_sha256=F.sha(data)) for s in F.parse_esl(data, name))

    def add_archive(self, name="em/em12.drs"):
        data = dar(model_bin())
        self.put(name, data, "archive")
        self.models.extend(dict(m, source=name, file_sha256=F.sha(data))
                           for m in F.parse_room_archive(data, name)["models"])

    def scan(self, rooms=("r103",), repo=None):
        return R.build_memberships(self.root, self.models, self.sources, self.spawns, rooms, repo)


class LoaderTableTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tables = R.loader_tables(REPO)

    def test_actual_current_source_contract(self):
        t = self.tables
        self.assertEqual(len(t["files"]), 254)
        self.assertEqual({k: len(v) for k, v in t["tables"].items()}, {
            "EmFileTbl": 64, "EmFileTbl_Ada": 64, "EmFileTbl_Wesker": 64, "EmFileTbl_Klauser": 64})
        self.assertEqual(t["lists"], [f"etc/emleon{i:02d}.esl" for i in range(8)]
                         + [f"etc/omake{i:02d}.esl" for i in range(3)])
        self.assertEqual(t["players"]["EmFileTbl"]["player_types"], [0, 1])
        self.assertTrue(t["players"]["EmFileTbl"]["default_player_type"])
        self.assertEqual(t["players"]["EmFileTbl_Wesker"]["player_types"], [3, 5])
        for source in t["source_inputs"]:
            self.assertEqual(F.sha((REPO / source["path"]).read_bytes()), source["sha256"])

    def test_actual_alias_is_not_id_filename(self):
        self.assertEqual({r["path"] for r in R.archive_alternatives(self.tables, 6)}, {"em/em10.drs"})
        self.assertEqual({r["path"] for r in R.archive_alternatives(self.tables, 0x12)}, {"em/em12.drs"})

    def test_actual_ashley_costume_alternatives(self):
        for ident in (3, 5):
            rows = R.archive_alternatives(self.tables, ident)
            self.assertEqual(len(rows), 8)
            self.assertEqual({r["path"] for r in rows}, {"em/pl11.drs", "em/pl15.drs"})
            self.assertEqual({r["mapped_id"] for r in rows}, {3, 5})
            self.assertEqual({r["costume_condition"] for r in rows}, {"game_costume == 0", "game_costume != 0"})

    def test_actual_player_variants_remain_separate(self):
        rows = R.archive_alternatives(self.tables, 0x16)
        self.assertEqual(len(rows), 4)
        self.assertEqual(len({r["path"] for r in rows}), 4)
        self.assertEqual({r["table"] for r in rows}, set(self.tables["tables"]))

    def test_dll_not_flag_selects_drs(self):
        t = deepcopy(self.tables)
        for table in t["tables"].values():
            file, dll, _ = table[0x12]
            table[0x12] = (file, dll, 0)
        self.assertEqual({r["path"] for r in R.archive_alternatives(t, 0x12)}, {"em/em12.drs"})
        self.assertTrue(all(r["binding_supported"] for r in R.archive_alternatives(t, 0x12)))
        for table in t["tables"].values():
            file, _, _ = table[0x12]
            table[0x12] = (file, 0, 1)
        self.assertEqual({r["path"] for r in R.archive_alternatives(t, 0x12)}, {"em/em12.das"})
        self.assertFalse(any(r["binding_supported"] for r in R.archive_alternatives(t, 0x12)))

    def test_core_and_unknown_ids_do_not_guess(self):
        for ident in (0x40, 0x41, 0x80, 0xff):
            self.assertEqual(R.archive_alternatives(self.tables, ident), [])
        for ident in (-1, 256, True, "12"):
            with self.assertRaises(F.Invalid):
                R.archive_alternatives(self.tables, ident)

    def test_changed_source_syntax_refuses(self):
        mutations = (
            ("src/game/read.cpp", "ReadFile EmFileTbl[64]", "ReadFile EmFileTbl[63]"),
            ("src/game/read.cpp", "if (pG->game_costume == 0)", "if (pG->game_costume == 1)"),
            ("src/game/read.cpp", "e = &EmFileTbl_Wesker[id];", "e = &EmFileTbl_Wesker[id + 1];"),
            ("src/game/dvd.cpp", '{"em/em12.das", 0}', '{"em/em12.das", 1}'),
            ("src/game/stage.cpp", "emlist_name[11]", "emlist_name[12]"),
            ("src/game/read.cpp", "id = checkAshleyId(id);\n    m = SearchEmModule(id);",
             "m = SearchEmModule(id);\n    id = checkAshleyId(id);"),
            ("src/game/read.cpp", "while (*(p) != '.')", "while (*(p) != '/')"),
            ("port/dreamcast/game/platform/dvd.cpp", "out[i++] = (char) tolower((unsigned char) c);",
             "(char) tolower((unsigned char) c); out[i++] = c;"),
        )
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for source in self.tables["source_inputs"]:
                dest = root / source["path"]
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(REPO / source["path"], dest)
            for filename, old, new in mutations:
                with self.subTest(filename=filename, mutation=new):
                    original = (REPO / filename).read_text()
                    self.assertIn(old, original)
                    (root / filename).write_text(original.replace(old, new))
                    with self.assertRaises(F.Invalid):
                        R.loader_tables(root)
                    (root / filename).write_text(original)


class NativeMembershipTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.tree = Tree(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def test_exact_candidate_has_full_provenance_and_no_count(self):
        self.tree.add_list()
        self.tree.add_archive()
        result = self.tree.scan()
        key = ("em/em12.drs", self.tree.models[0]["key"])
        member, = result["memberships"][key]
        self.assertEqual(member["room"], "r103")
        self.assertIsNone(member["instances"])
        self.assertEqual(member["status"], "candidate")
        self.assertEqual(member["evidence"], [0])
        row, = result["inventory"]
        self.assertEqual((row["list_number"], row["list_index"], row["record_offset"]), (0, 0, 0))
        self.assertEqual(row["source_sha256"], self.tree.sources["em/em12.drs"]["sha256"])
        self.assertEqual(row["list_sha256"], self.tree.sources["etc/emleon00.esl"]["sha256"])
        self.assertEqual(row["model_keys"], [key[1]])
        self.assertEqual(len(row["loader_alternatives"]), 4)
        self.assertIn("selected or retained", member["selection"])
        self.assertEqual(len(result["source_inputs"]), 4)
        json.dumps({k: v for k, v in result.items() if k != "memberships"})

    def test_two_story_lists_preserve_both_alternatives(self):
        self.tree.add_list(records=((0x103, 0x12, 0, 1), (0x103, 0x12, 1, 0)))
        self.tree.add_list("etc/emleon01.esl", ((0x103, 0x12, 2, 1),))
        self.tree.add_archive()
        result = self.tree.scan()
        members, = result["memberships"].values()
        self.assertEqual(len(members), 1)
        self.assertIsNone(members[0]["instances"])
        self.assertEqual(members[0]["evidence"], [0, 1, 2])
        self.assertEqual([r["type"] for r in result["inventory"]], [0, 1, 2])
        self.assertEqual([r["be_flag"] for r in result["inventory"]], [1, 0, 1])
        self.assertEqual({r["list_number"] for r in result["inventory"]}, {0, 1})

    def test_omake_and_ashley_costume_candidates(self):
        self.tree.add_list("etc/omake00.esl", ((0x403, 3, 2, 1),))
        self.tree.add_archive("em/pl11.drs")
        self.tree.add_archive("em/pl15.drs")
        result = self.tree.scan(("r403",))
        self.assertEqual(len(result["memberships"]), 2)
        self.assertEqual(len(result["inventory"]), 2)
        self.assertEqual({r["list_number"] for r in result["inventory"]}, {8})
        self.assertEqual({a["mapped_id"] for r in result["inventory"] for a in r["loader_alternatives"]}, {3, 5})

    def test_requested_rooms_only_and_no_empty_entry_binding(self):
        self.tree.add_list(records=((0x103, 0, 0, 1), (0x101, 0x12, 1, 1)))
        self.tree.add_archive()
        self.assertFalse(self.tree.scan()["memberships"])
        self.assertEqual(len(self.tree.scan(("r101",))["memberships"]), 1)

    def test_filename_alone_and_wrong_alias_do_not_bind(self):
        self.tree.add_list(records=((0x103, 6, 0, 1),))
        self.tree.add_archive("em/em06.drs")
        result = self.tree.scan()
        self.assertFalse(result["memberships"])
        self.assertEqual(result["inventory"][0]["target_path"], "em/em10.drs")
        self.assertEqual(result["inventory"][0]["status"], "missing")
        self.tree.add_archive("em/em10.drs")
        self.assertEqual({k[0] for k in self.tree.scan()["memberships"]}, {"em/em10.drs"})

    def test_non_dll_initial_name_is_unresolved(self):
        self.tree.add_list(records=((0x103, 1, 0, 1),))
        self.tree.add_archive("em/pl00.drs")
        result = self.tree.scan()
        self.assertFalse(result["memberships"])
        self.assertEqual(result["inventory"][0]["target_path"], "em/pl00.das")
        self.assertEqual(result["inventory"][0]["status"], "unresolved")
        self.assertEqual({a["filename_state"] for a in result["inventory"][0]["loader_alternatives"]},
                         {"mutable-unresolved"})

    def test_non_dll_initial_das_file_does_not_authorize_binding(self):
        self.tree.add_list(records=((0x103, 1, 0, 1),))
        self.tree.add_archive("em/pl00.das")
        result = self.tree.scan()
        self.assertFalse(result["memberships"])
        self.assertEqual(result["inventory"][0]["status"], "unresolved")
        self.assertIsNone(result["inventory"][0]["instances"])

    def test_missing_and_rejected_archive_are_distinct(self):
        self.tree.add_list()
        result = self.tree.scan()
        self.assertEqual(result["inventory"][0]["status"], "missing")
        self.tree.put("em/em12.drs", b"broken", "archive")
        result = self.tree.scan()
        self.assertFalse(result["memberships"])
        self.assertEqual(result["inventory"][0]["status"], "unresolved")
        self.assertIn("ModelData", result["inventory"][0]["message"])

    def test_unsupported_list_and_embedded_list_stay_unresolved(self):
        self.tree.add_list("etc/unknown.esl")
        self.tree.add_archive()
        result = self.tree.scan()
        self.assertFalse(result["memberships"])
        self.assertEqual(result["inventory"][0]["status"], "unresolved")
        self.tree = Tree(self.root)
        self.tree.add_list()
        self.tree.spawns[0]["location"] += "/DVD[0]/ARC[0x4]"
        self.tree.add_archive()
        self.assertFalse(self.tree.scan()["memberships"])

    def test_core_props_are_unresolved_not_guessed(self):
        self.tree.add_list(records=((0x103, 0x41, 0, 1),))
        self.tree.add_archive("em/em41.drs")
        result = self.tree.scan()
        self.assertFalse(result["memberships"])
        self.assertEqual(result["inventory"][0]["status"], "unresolved")

    def test_missing_player_alternatives_are_retained(self):
        self.tree.add_list(records=((0x103, 0x16, 0, 1),))
        self.tree.add_archive("em/em16.drs")
        result = self.tree.scan()
        self.assertEqual(len(result["memberships"]), 1)
        self.assertEqual([r["status"] for r in result["inventory"]].count("missing"), 3)

    def test_case_normalization_single_source_and_ambiguous_sources(self):
        self.tree.add_list("ETC/EMLEON00.ESL")
        self.tree.add_archive("EM/EM12.DRS")
        result = self.tree.scan()
        self.assertEqual({k[0] for k in result["memberships"]}, {"EM/EM12.DRS"})
        self.tree.add_archive("em/em12.drs")
        result = self.tree.scan()
        self.assertFalse(result["memberships"])
        self.assertEqual(result["inventory"][0]["status"], "ambiguous")
        self.assertTrue(any(c["status"] == "rejected" for c in result["coverage"]))

    def test_ambiguous_list_case_refuses(self):
        self.tree.add_list()
        self.tree.add_list("ETC/EMLEON00.ESL")
        self.tree.add_archive()
        result = self.tree.scan()
        self.assertFalse(result["memberships"])
        self.assertEqual({r["status"] for r in result["inventory"]}, {"ambiguous"})

    def test_stale_list_and_model_hashes_refuse(self):
        self.tree.add_list()
        self.tree.add_archive()
        self.tree.spawns[0]["source_sha256"] = "0" * 64
        self.assertFalse(self.tree.scan()["memberships"])
        self.tree.spawns[0]["source_sha256"] = self.tree.sources["etc/emleon00.esl"]["sha256"]
        self.tree.models[0]["file_sha256"] = "0" * 64
        self.assertFalse(self.tree.scan()["memberships"])

    def test_duplicate_model_key_and_source_less_kind_refuse(self):
        self.tree.add_list()
        self.tree.add_archive()
        self.tree.models.append(deepcopy(self.tree.models[0]))
        self.assertFalse(self.tree.scan()["memberships"])
        self.tree.models.pop()
        self.tree.models[0]["kind"] = "GLP1"
        self.assertFalse(self.tree.scan()["memberships"])

    def test_global_replacements_do_not_gain_guessed_rooms(self):
        self.tree.add_list()
        self.tree.add_archive()
        self.tree.models.append(dict(source="dc/ganado.re4gl", key="appearance[0]", kind="GLP1",
                                     file_sha256="0" * 64, actor_class="ganado"))
        result = self.tree.scan()
        self.assertNotIn(("dc/ganado.re4gl", "appearance[0]"), result["memberships"])

    def test_native_extent_and_record_range_refuse(self):
        self.tree.add_list()
        self.tree.add_archive()
        for size in (0, 31, 8193, 8224):
            with self.subTest(size=size):
                self.tree.sources["etc/emleon00.esl"]["bytes"] = size
                self.assertFalse(self.tree.scan()["memberships"])
        self.tree.sources["etc/emleon00.esl"]["bytes"] = 32
        self.tree.spawns[0]["index"] = 1
        self.assertFalse(self.tree.scan()["memberships"])
        for data in (b"", bytes(31), bytes(8193), bytes(8224)):
            with self.assertRaises(F.Invalid):
                F.parse_esl(data)

    def test_no_lists_is_an_explicit_coverage_gap(self):
        self.tree.add_archive()
        result = self.tree.scan()
        self.assertFalse(result["memberships"])
        self.assertTrue(any(r["source"] == "native-room-lists" and r["status"] == "missing"
                            for r in result["coverage"]))
        self.tree.add_list(records=())
        self.assertFalse(any(r["source"] == "native-room-lists" for r in self.tree.scan()["coverage"]))

    def test_symlink_escape_refuses(self):
        self.tree.add_list()
        self.tree.add_archive()
        with tempfile.TemporaryDirectory() as d:
            outside = Path(d) / "data"
            outside.write_bytes(b"fixture")
            for path in (self.root / "etc/emleon00.esl", self.root / "em/em12.drs"):
                original = path.read_bytes()
                path.unlink()
                path.symlink_to(outside)
                self.assertFalse(self.tree.scan()["memberships"])
                path.unlink()
                path.write_bytes(original)

    def test_missing_source_tables_fail_closed(self):
        self.tree.add_list()
        self.tree.add_archive()
        result = self.tree.scan(repo=self.root)
        self.assertFalse(result["memberships"])
        self.assertEqual(result["coverage"][0]["status"], "rejected")

    def test_inputs_not_mutated_and_result_deterministic(self):
        self.tree.add_list(records=((0x103, 3, 2, 1), (0x101, 0x12, 0, 1)))
        self.tree.add_archive("em/pl11.drs")
        self.tree.add_archive("em/pl15.drs")
        self.tree.add_archive()
        original = deepcopy((self.tree.models, self.tree.sources, self.tree.spawns))
        before = self.tree.scan(("r103", "r101"))
        self.assertEqual(original, (self.tree.models, self.tree.sources, self.tree.spawns))
        self.tree.models.reverse()
        self.tree.spawns.reverse()
        self.tree.sources = dict(reversed(list(self.tree.sources.items())))
        self.assertEqual(before, self.tree.scan(("r101", "r103")))


if __name__ == "__main__":
    unittest.main()
