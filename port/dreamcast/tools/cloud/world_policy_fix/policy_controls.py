#!/usr/bin/env python3
"""Public policy recovery/diagnostic controls; no private asset certificate PASS.

Positive recovery uses an in-process TEST-ONLY table substitution. The CLI has
no table override. The actual C++ predicate is compiled both with its committed
table (public fixtures must refuse) and with a separate synthetic include (unit
predicate checks only); its header bytes are identical in both compilations.
"""
import argparse
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
from unittest import mock

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
TOOLS = HERE.parents[1]
ROOT = TOOLS.parents[2]
sys.path.insert(0, str(TOOLS))
from cloud.build12.fixtures import package
from d367.visibility23 import metadata
from d367.texture_rect21.qualify792_provenance import DRIVER
import scenery_data_variants as layout
import world_policy_provenance as policy

BASE = "dd6b66b9523300181df8e0af8cbe8ece3bdc4be0"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load_module(path):
    spec = importlib.util.spec_from_file_location("policy_baseline_layout", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def repaired_policy(blob):
    out = bytearray(blob)
    struct.pack_into("<I", out, 20, layout.crc(out[32:]))
    return bytes(out)


def fixture_tables(mesh, original, physical):
    mh, ph = layout.Package(mesh).h, struct.unpack_from("<4s7I", physical)
    original_crc = struct.unpack_from("<I", original, 20)[0]
    row = dict(zip(policy.CERT_FIELDS, (0x701, len(physical), ph[2], ph[3], ph[4], ph[5],
                                      policy.fnv(physical), mh[3], len(mesh), original_crc)))
    certs = [row] + [dict(zip(policy.CERT_FIELDS, (0x702+i, 0, 0, 0, 0, 0, 0, 0, 0, 0))) for i in range(26)]
    origins = {struct.unpack_from("<II", physical, 32+16*i):
               struct.unpack_from("<II", original, 32+16*i) for i in range(ph[3])}
    return dict(certificates=certs, origins=origins, originals=[],
                hashes={"scope": "TEST_ONLY_SYNTHETIC_TABLES_NOT_RUNTIME_AUTHORITY"})


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--receipt", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    checks = []

    def check(ok, name):
        if not ok:
            raise AssertionError(name)
        checks.append(name)

    def refused(call, text, name):
        try:
            call()
        except ValueError as error:
            check(text in str(error), name)
            return str(error)
        raise AssertionError("accepted: " + name)

    baseline_path = args.out / "baseline_scenery_data_variants.py"
    baseline_path.write_bytes(subprocess.check_output([
        "git", "show", BASE+":port/dreamcast/tools/scenery_data_variants.py"], cwd=ROOT))
    baseline = load_module(baseline_path)
    # All existing public shapes/versions/variants, including splitting, compare
    # full returned package/group/report bytes to the committed old converter.
    compared = 0
    for kind in ("compact", "limit", "reuse", "unused"):
        for version in (2, 3):
            mesh, original = package(kind, version)
            groups = metadata.build(mesh, original, 4)[0] if version == 3 else None
            for variant in layout.MARKERS:
                old = baseline.convert(mesh, variant, original, groups)
                for options in ({}, {"policy_diagnostics": False}, {"policy_diagnostics": True}):
                    check(layout.convert(mesh, variant, original, groups, **options) == old,
                          f"converter identity {kind}/v{version}/{variant}/{options}")
                    compared += 1

    mesh, original = package()
    physical = bytearray(original)
    for i in range(3):
        struct.pack_into("<II", physical, 32+16*i, 0xa1000000+i, 0xb1000000+i)
    physical = repaired_policy(physical)
    groups, _ = metadata.build(mesh, original, 4)
    package_view = layout.Package(mesh)
    fixture = fixture_tables(mesh, original, physical)
    production = policy._load_tables()
    check(len(production["certificates"]) == 27 and len(production["origins"]) == 798,
          "committed table parser actual cohort")
    check([c["room"] for c in production["certificates"] if policy._original_pin(c, production)] == [0x100, 0x103],
          "historical SHA pins selected by exact source lineage")

    # The default header errors stay exact. Diagnostics identify the precise
    # offset/semantics without admitting any formerly refused input.
    sg_fields = ((0, "magic@0"), (4, "version@4"), (8, "meshlet_count@8"),
                 (12, "groups_per_meshlet@12"), (16, "mesh_body_crc@16"),
                 (20, "mesh_file_bytes@20"), (24, "physical_policy_crc@24"),
                 (28, "record_crc@28"))
    for offset, label in sg_fields:
        bad = bytearray(groups)
        if offset == 12:
            struct.pack_into("<I", bad, offset, 0)
        else:
            bad[offset] ^= 1
        old_error = refused(lambda: baseline.parse_groups(bad, package_view, original),
                            "R4SG identity/CRC", "baseline refuses " + label)
        check(refused(lambda: layout.parse_groups(bad, package_view, original), old_error,
                      "default refuses " + label) == old_error, "default error exact " + label)
        refused(lambda: layout.parse_groups(bad, package_view, original, policy_diagnostics=True),
                label, "diagnostic " + label)
    refused(lambda: layout.parse_groups(groups+bytes(16), package_view, original, policy_diagnostics=True),
            "file_bytes", "group file extent diagnostics")
    for offset, label in ((0, "magic@0"), (4, "version@4"), (12, "part_count@12"),
                          (16, "mesh_count@16"), (20, "body_crc@20"),
                          (24, "reserved@24"), (28, "reserved@28")):
        bad = bytearray(original); bad[offset] ^= 1
        old_error = refused(lambda: baseline.policy_header(bad, package_view), "R4PW", "old policy " + label)
        check(refused(lambda: layout.policy_header(bad, package_view), old_error,
                      "default policy " + label) == old_error, "default policy error exact " + label)
        refused(lambda: layout.policy_header(bad, package_view, policy_diagnostics=True), label,
                "policy diagnostic " + label)

    # Real production authority rejects these public data for every listed room.
    check(not policy.inspect(mesh, physical, 0x101, groups)["certificate_matched"],
          "public policy cannot claim real r101 certificate")
    refused(lambda: policy.prepare(mesh, physical, 0x101, groups), "exact committed runtime certificate",
            "production preparation refuses synthetic policy")
    with mock.patch.object(policy, "_load_tables", return_value=fixture):
        restored, kept, report = policy.prepare(mesh, physical, 0x701, groups, original)
        check(restored == original and kept == groups, "synthetic authenticated exact recovery and SG preservation")
        check(not report["restored_control"]["archived_source_byte_identity"] and
              report["restored_control"]["supplied_original_byte_equal"] and
              "SHA unavailable" in report["restored_control"]["evidence"], "no invented archive SHA")
        check(not report["full_control_disc_qualified"], "no whole pack/control acceptance")
        allowed = set(range(20, 24)) | {32+16*i+j for i in range(3) for j in range(8)}
        check(set(report["restored_control"]["changed_byte_offsets"]) <= allowed, "only key/header CRC bytes change")
        for variant in layout.MARKERS:
            check(layout.convert(mesh, variant, restored, kept) == baseline.convert(mesh, variant, original, groups),
                  "prepared control feeds unchanged converter " + variant)
        refused(lambda: policy.prepare(mesh, physical, 0x702, groups, original), "exact committed runtime certificate",
                "supplied original never authorizes unknown tuple")
        bad_policy = bytearray(physical); bad_policy[32] ^= 1
        refused(lambda: policy.prepare(mesh, bad_policy, 0x701), "body_crc@20", "physical body CRC before provenance")
        refused(lambda: policy.prepare(mesh, repaired_policy(bad_policy), 0x701), "exact committed runtime certificate",
                "recomputed foreign policy refuses certificate")
        refused(lambda: policy.prepare(mesh, physical, 0x701, original_policy=original[:-1]),
                "not byte-identical", "optional original must be exact")
        physical_groups = bytearray(groups)
        struct.pack_into("<I", physical_groups, 24, struct.unpack_from("<I", physical, 20)[0])
        refused(lambda: policy.prepare(mesh, physical, 0x701, physical_groups), "physical_policy_crc@24",
                "physical-bound SG is never rebound")
        bad_groups = bytearray(groups); bad_groups[16] ^= 1
        refused(lambda: policy.prepare(mesh, physical, 0x701, bad_groups), "mesh_body_crc@16", "stale SG refuses")
        bad_groups = bytearray(groups)
        struct.pack_into("<H", bad_groups, 32, 65535)
        struct.pack_into("<I", bad_groups, 28, layout.crc(bad_groups[32:]))
        refused(lambda: policy.prepare(mesh, physical, 0x701, bad_groups), "R4SG bounds",
                "recomputed SG CRC cannot authorize wrong enclosure")

    for field in ("physical_file_fnv", "mesh_crc", "mesh_bytes", "source_crc"):
        modified = copy.deepcopy(fixture)
        modified["certificates"][0][field] ^= 1
        with mock.patch.object(policy, "_load_tables", return_value=modified):
            refused(lambda: policy.prepare(mesh, physical, 0x701),
                    "restored policy body CRC mismatch" if field == "source_crc" else "exact committed runtime certificate",
                    "certificate field refusal " + field)
    modified = copy.deepcopy(fixture)
    key = next(iter(modified["origins"]))
    modified["origins"][key] = (0, 0)
    with mock.patch.object(policy, "_load_tables", return_value=modified):
        refused(lambda: policy.prepare(mesh, physical, 0x701), "restored policy body CRC mismatch",
                "incomplete or wrong inverse map cannot restamp source CRC")
    pinned = copy.deepcopy(fixture)
    row = {name: fixture["certificates"][0][name] for name in policy.SOURCE_FIELDS}
    row.update(source_world_sha256=sha(original), mesh_sha256=sha(mesh))
    pinned["originals"] = [row]
    with mock.patch.object(policy, "_load_tables", return_value=pinned):
        check(policy.prepare(mesh, physical, 0x701)[2]["restored_control"]["archived_source_byte_identity"],
              "matching historical SHA pin enforced")
    for field in ("source_world_sha256", "mesh_sha256"):
        bad_pin = copy.deepcopy(pinned); bad_pin["originals"][0][field] = "0"*64
        with mock.patch.object(policy, "_load_tables", return_value=bad_pin):
            refused(lambda: policy.prepare(mesh, physical, 0x701), "SHA256 mismatch", "wrong pin refuses " + field)
    ambiguous = copy.deepcopy(pinned)
    ambiguous["originals"].append(dict(row, source_world_sha256="1"*64))
    with mock.patch.object(policy, "_load_tables", return_value=ambiguous):
        refused(lambda: policy.prepare(mesh, physical, 0x701), "conflicting pinned", "ambiguous source SHA refuses")

    # Reuse the existing runtime-helper driver verbatim. Only the fixture
    # include differs for positive unit cases; production tables are immutable.
    cpp = args.out / "runtime_predicate.cpp"
    cpp.write_text(DRIVER)
    synthetic_include = args.out / "synthetic-include"
    synthetic_include.mkdir()
    helper_bytes = (policy.RECT / "world_rect_provenance.h").read_bytes()
    (synthetic_include / "world_rect_provenance.h").write_bytes(helper_bytes)
    table_text = "// TEST ONLY: public synthetic certificate rows, never runtime authority.\n" + "".join(
        "{"+",".join(f"0x{row[name]:x}U" for name in policy.CERT_FIELDS)+"},\n"
        for row in fixture["certificates"])
    (synthetic_include / "provenance_certificates.inc").write_text(table_text)
    commands, predicate_cases = [], []
    params = [0x701, len(physical), package_view.h[3], len(mesh), package_view.h[5], package_view.h[4]]
    actual_crc = struct.unpack_from("<I", physical, 20)[0]
    source_crc = struct.unpack_from("<I", original, 20)[0]
    for label, include in (("committed", policy.RECT), ("synthetic", synthetic_include)):
        exe = args.out / ("predicate-"+label)
        command = ["g++", "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror", "-I"+str(include), str(cpp), "-o", str(exe)]
        subprocess.run(command, check=True); commands.append(command)
        cases = []
        if label == "committed":
            cases = [(physical, [c["room"], *params[1:]], actual_crc, "unknown-public-"+hex(c["room"]))
                     for c in production["certificates"]]
        else:
            cases.append((physical, params, source_crc, "exact-synthetic-predicate"))
            for index in (0, 2, 3, 4, 5):
                altered = params.copy(); altered[index] ^= 1
                cases.append((physical, altered, actual_crc, "tuple-"+str(index)))
            for offset in (0, 4, 8, 12, 16, 20, 24, 28, 32, len(physical)-1):
                altered = bytearray(physical); altered[offset] ^= 1
                cases.append((altered, params, struct.unpack_from("<I", altered, 20)[0], "byte-"+str(offset)))
            altered = params.copy(); altered[1] -= 1
            cases.append((physical[:-1], altered, actual_crc, "short-file"))
        for blob, values, expected, name in cases:
            packet = struct.pack("<8I", *values, expected, 0)+blob
            subprocess.run([str(exe)], input=packet, check=True, capture_output=True)
            predicate_cases.append(label+":"+name)
    check((synthetic_include / "world_rect_provenance.h").read_bytes() == helper_bytes,
          "C++ predicate header bytes unchanged in fixture build")

    # Actual committed origin helper, all current rows plus unknown keys.
    origin_cpp = args.out / "origin.cpp"
    origin_cpp.write_text('#include <cstdio>\n#include "scoped_origin.h"\nint main(){std::uint32_t x[2];'
                          'while(std::fread(x,4,2,stdin)==2){re4dc::rect21::origin::original(x[0],x[1]);'
                          'if(std::fwrite(x,4,2,stdout)!=2)return 1;}}\n')
    origin_exe = args.out / "origin"
    command = ["g++", "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror", "-I"+str(policy.RECT), str(origin_cpp), "-o", str(origin_exe)]
    subprocess.run(command, check=True); commands.append(command)
    keys = list(production["origins"]) + [(0, 0), (0x12345678, 0x87654321)]
    actual = subprocess.check_output([str(origin_exe)], input=b"".join(struct.pack("<II", *key) for key in keys))
    expected = b"".join(struct.pack("<II", *production["origins"].get(key, key)) for key in keys)
    check(actual == expected, "Python inverse map matches actual C++ origin helper")

    # Exercise the actual preparation main with test-only in-process table
    # replacement. No public CLI parameter can inject that test authority.
    inputs = args.out / "inputs"; inputs.mkdir()
    for name, raw in (("world.re4mesh", mesh), ("physical.r4pw", physical),
                      ("original.r4pw", original), ("world.r4sg", groups)):
        (inputs / name).write_bytes(raw)
    before_hashes = {p.name: sha(p.read_bytes()) for p in inputs.iterdir()}
    argv = [str(TOOLS / "world_policy_provenance.py"), str(inputs / "world.re4mesh"), str(inputs / "physical.r4pw"),
            "--room", "r701", "--source-groups", str(inputs / "world.r4sg")]
    with mock.patch.object(policy, "_load_tables", return_value=fixture):
        outputs = []
        for extra in ([], ["--prepare-original-policy", "0"]):
            stdout = io.StringIO()
            with mock.patch.object(sys, "argv", argv+extra), contextlib.redirect_stdout(stdout):
                policy.main()
            outputs.append(stdout.getvalue())
        check(outputs[0] == outputs[1], "preparation absent/zero inspection identity")
        out = args.out / "prepared"
        with mock.patch.object(sys, "argv", argv+["--prepare-original-policy", "1", "--out", str(out),
                                                 "--original-policy", str(inputs / "original.r4pw")]), contextlib.redirect_stdout(io.StringIO()):
            policy.main()
        check((out / "ps2-world.r4pw").read_bytes() == original and (out / "ps2-world.r4sg").read_bytes() == groups,
              "explicit preparation files exact")
        try:
            with mock.patch.object(sys, "argv", argv+["--prepare-original-policy", "1", "--out", str(out)]), contextlib.redirect_stdout(io.StringIO()):
                policy.main()
        except FileExistsError:
            check(True, "existing output refused without overwrite")
        else:
            raise AssertionError("existing output accepted")
    check(before_hashes == {p.name: sha(p.read_bytes()) for p in inputs.iterdir()}, "all source input bytes unchanged")
    refused_out = args.out / "unknown-output"
    with mock.patch.object(sys, "argv", argv+["--prepare-original-policy", "1", "--out", str(refused_out)]):
        refused(policy.main, "exact committed runtime certificate", "CLI unknown certificate refuses")
    check(not refused_out.exists(), "failed CLI validation creates no output directory")
    with mock.patch.object(sys, "argv", argv+["--prepare-original-policy", "0", "--out", str(refused_out)]):
        refused(policy.main, "--out requires", "disabled preparation cannot write")
    try:
        with mock.patch.object(sys, "argv", argv+["--certificate", "caller.json"]), contextlib.redirect_stderr(io.StringIO()):
            policy.main()
    except SystemExit as error:
        check(error.code == 2, "CLI has no caller certificate override")
    else:
        raise AssertionError("caller certificate option accepted")

    # CLI default/explicit-zero output files match the old committed CLI.
    environment = dict(os.environ, PYTHONPATH=str(TOOLS), PYTHONDONTWRITEBYTECODE="1")
    cli_variants = []
    for label, script, extra in (("baseline", baseline_path, []), ("absent", TOOLS / "scenery_data_variants.py", []),
                                 ("zero", TOOLS / "scenery_data_variants.py", ["--policy-diagnostics", "0"]),
                                 ("one", TOOLS / "scenery_data_variants.py", ["--policy-diagnostics", "1"])):
        directory = args.out / ("layout-cli-"+label)
        cmd = [sys.executable, str(script), str(inputs / "world.re4mesh"), str(inputs / "original.r4pw"),
               "--source-groups", str(inputs / "world.r4sg"), "--scenery-direct-strips", "--out", str(directory), *extra]
        subprocess.run(cmd, check=True, env=environment, capture_output=True)
        cli_variants.append({p.name: sha(p.read_bytes()) for p in directory.iterdir()})
    check(all(x == cli_variants[0] for x in cli_variants[1:]), "CLI complete output identity baseline/absent/zero/one")

    sources = [TOOLS / "world_policy_provenance.py", TOOLS / "scenery_data_variants.py", Path(__file__)]
    result = dict(status="PASS_PUBLIC_HOST_ONLY", base=BASE, checks=len(checks), checks_passed=checks,
                  converter_full_return_comparisons=compared, cli_output_sha256=cli_variants[0],
                  actual_cpp_predicate=dict(committed_header_sha256=sha(helper_bytes),
                    fixture_header_sha256=sha((synthetic_include / "world_rect_provenance.h").read_bytes()),
                    fixture_table_sha256=sha(table_text.encode()), cases=predicate_cases,
                    null_and_short_pointer_checks=2*len(predicate_cases),
                    scope="Production table public-data refusal; synthetic table positive predicate tests only"),
                  actual_cpp_origin_rows=len(keys), compiler=subprocess.check_output(["g++", "--version"], text=True).splitlines()[0],
                  compiler_commands=commands, committed_sources_sha256=production["hashes"],
                  sources_sha256={str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in sources},
                  private_assets_used=False, private_certificate_positive_controls=0,
                  target_runtime_changes_in_this_lane=False,
                  limits=policy.LIMITS+["No real r101/r103 recovery run; fixture certificates exist only in tests."])
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(result, indent=2, sort_keys=True)+"\n")
    print(json.dumps({"status": result["status"], "checks": len(checks), "cpp_predicate_cases": len(predicate_cases),
                      "receipt": str(args.receipt)}))


if __name__ == "__main__":
    main()
