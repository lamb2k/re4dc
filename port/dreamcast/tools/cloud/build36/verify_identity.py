#!/usr/bin/env python3
"""Compare the real baseline scanner CLI with absent/zero Build36 controls.

Only standard-library Python and Git are needed. Public fixture writers and
the baseline CLI are extracted from the requested Git commit into temporary
storage. Each CLI runs against identical inputs and the same output pathname;
all nine artifact bytes, exit status, stdout and stderr must match exactly.
Input bytes and candidate source hashes must remain unchanged. No runtime,
recipe, game data, target executable or disc image is built or modified.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile


sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
BASE = "bb5f18e0e3b3fac4c76bd42d0c9d8107385c568c"
SCANNER = "port/dreamcast/tools/d367/fallback_scan"
HAND_BACK = "port/dreamcast/docs/cloud/handbacks/build-36.md"
OWN_TOOLS = "port/dreamcast/tools/cloud/build36"
OUTPUTS = {"details.tsv", "by-model.tsv", "by-room.tsv", "barn.tsv", "spawns.tsv",
           "coverage.tsv", "report.json", "context-template.json", "REPORT.md"}


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_hash(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def git(*arguments):
    return subprocess.check_output(["git", *arguments], cwd=ROOT)


def paths_from_git(*arguments):
    return sorted(p.decode() for p in git(*arguments).split(b"\0") if p)


def allowed(path):
    return path == HAND_BACK or path.startswith(SCANNER + "/") or path.startswith(OWN_TOOLS + "/")


def repository_scope(base):
    changed = paths_from_git("diff", "--name-only", "-z", base, "--")
    untracked = paths_from_git("ls-files", "--others", "--exclude-standard", "-z")
    committed = paths_from_git("diff", "--name-only", "-z", base, "HEAD", "--")
    require(all(allowed(path) for path in changed + committed + untracked),
            "out-of-scope repository changes: " + repr([p for p in changed + untracked if not allowed(p)]))
    checkpoint = ("none" if not committed else "docs-only" if set(committed) <= {HAND_BACK}
                  else "scanner-and-documentation")
    return dict(tracked_changed_paths=changed, untracked_paths=untracked,
                committed_since_base=committed, checkpoint_scope=checkpoint,
                allowed_prefixes=[SCANNER + "/", OWN_TOOLS + "/"], allowed_handback=HAND_BACK,
                production_build_inputs_changed=False,
                production_identity_scope="Tracked diff scope contains only offline scanner/checker files and the Build36 handback; no target rebuild or binary comparison.")


def source_hashes(extra=()):
    paths = {p for prefix in (SCANNER, OWN_TOOLS) for p in (ROOT / prefix).rglob("*.py") if p.is_file()}
    paths.update(ROOT / path for path in extra)
    return {p.relative_to(ROOT).as_posix(): file_hash(p) for p in sorted(paths)}


def input_hashes(folder):
    result = {}
    for path in sorted(folder.rglob("*")):
        require(not path.is_symlink(), "fixture contains unexpected symlink")
        if path.is_file():
            result[path.relative_to(folder).as_posix()] = dict(bytes=path.stat().st_size, sha256=file_hash(path))
    return result


# Runs in an independent interpreter to keep archived imports isolated from the
# candidate and from this checker. This invokes the unchanged public writers.
FIXTURE_SCRIPT = r'''
import contextlib, hashlib, importlib.util, io, json, pathlib, struct, sys
sys.dont_write_bytecode = True
base, work = map(pathlib.Path, sys.argv[1:])
folder = base / "port/dreamcast/tools/d367/fallback_scan"
sys.path.insert(0, str(folder))
observed = set()
original_spec = importlib.util.spec_from_file_location
def tracked_spec(name, location, *args, **kwargs):
    if location is not None:
        observed.add(pathlib.Path(location).resolve())
    return original_spec(name, location, *args, **kwargs)
importlib.util.spec_from_file_location = tracked_spec
import test_scan as fixtures
import formats
import scan

inputs = work / "inputs"
inputs.mkdir()
cases = []
def add(name, kind, tree, args=(), exit_code=1):
    cases.append(dict(name=name, kind=kind, args=[tree.relative_to(work).as_posix(), "--out", "out",
        "--rooms", "r103", "--strict", *args], expected_exit=exit_code))
def mixed(name):
    return fixtures.make_tree(inputs / name)

tree = mixed("mixed")
add("mixed", "mixed", tree, exit_code=0)

tree = mixed("pack-loose-conflict")
loose = tree / "dc/tex/0/11223344-99aabbcc.re4tex"
loose.parent.mkdir(parents=True)
loose.write_bytes(fixtures.texture(False))
add("pack-loose-conflict", "duplicate", tree)

tree = mixed("missing-modern-policy")
(tree / "dc/native/r103/ps2-world.r4pw").unlink()
add("missing-modern-policy", "missing-policy", tree)

tree = mixed("malformed-present-policy")
policy = tree / "dc/native/r103/ps2-world.r4pw"
broken = bytearray(policy.read_bytes()); broken[-1] ^= 1; policy.write_bytes(broken)
add("malformed-present-policy", "bad-policy", tree)

tree = inputs / "global-esl-drs/disc"
(tree / "etc").mkdir(parents=True); (tree / "em").mkdir()
(tree / "etc/emleon00.esl").write_bytes(fixtures.esl())
archive = formats.DRS_MAGIC + fixtures.dar(fixtures.model_bin())[32:]
(tree / "em/em12.drs").write_bytes(archive)
add("global-esl-drs", "global", tree)

tree = mixed("context-list-extra")
(tree / "em").mkdir(); (tree / "em/em12.drs").write_bytes(archive)
support = tree.parent / "support"; support.mkdir()
with contextlib.redirect_stdout(io.StringIO()):
    _, header = fixtures.glod(support)
extra = support / "ganado_runtime.h"
assert extra.read_bytes() == header
key = formats.parse_room_archive(archive, "em/em12.drs")["models"][0]["key"]
room_list = dict(schema=scan.ROOM_LIST_SCHEMA, rooms={"r103": [dict(path="em/em12.drs",
    model=key, sha256=formats.sha(archive), instances=2, label="synthetic explicit member")]})
listed = support / "rooms.json"; listed.write_text(json.dumps(room_list, sort_keys=True))
knobs = support / "resolved-knobs.txt"
knobs.write_text("\n".join(k + "=" + v for k, v in sorted(fixtures.BASE_KNOBS.items())) + "\n")
template = scan.scan_tree(tree, ["r103"], room_list=room_list, extra_inputs=[extra])["context_template"]
source = next(s for s in template["sources"] if s["path"] == "st1/r103.dar")
source["models"][0]["parts"][0]["lighting"] = dict(enabled=True, ambient_vertex=False,
    material_vertex=False, diffuse=2, material_rgb=[100,255,255], tev_scale=1, leon_marker=False)
context = support / "context.json"; context.write_text(json.dumps(template, sort_keys=True))
add("context-list-extra", "context", tree, ["--knobs", knobs.relative_to(work).as_posix(),
    "--context", context.relative_to(work).as_posix(), "--room-list", listed.relative_to(work).as_posix(),
    "--input", extra.relative_to(work).as_posix()], exit_code=0)

tree = mixed("legacy-without-policy")
fixture_path = base / "port/dreamcast/tests/test_room_bins.py"
spec = importlib.util.spec_from_file_location("identity36_old_bin_fixture", fixture_path)
old = importlib.util.module_from_spec(spec); spec.loader.exec_module(old)
legacy = old.package([old.fixture()])
(tree / "dc/native/r103/legacy.re4mesh").write_bytes(legacy)
add("legacy-without-policy", "legacy", tree)

for mod in list(sys.modules.values()):
    filename = getattr(mod, "__file__", None)
    if filename:
        observed.add(pathlib.Path(filename).resolve())
sources = {p.relative_to(base).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
           for p in sorted(observed) if p.is_file() and p.is_relative_to(base)}
(work / "fixture-manifest.json").write_text(json.dumps(dict(cases=cases, source_sha256=sources),
    sort_keys=True, indent=2) + "\n")
'''


def assert_fixture(kind, report):
    """Prevent two equally empty/failed CLI runs from qualifying the gate."""
    coverage = report["coverage"]
    messages = "\n".join(row["message"] for row in coverage)
    if kind == "mixed":
        require((report["status"], report["models"], report["textures"]) == ("SCANNED", 3, 3), "mixed fixture not exercised")
    elif kind == "duplicate":
        require("duplicate texture key with different payload" in messages, "duplicate refusal not exercised")
    elif kind in ("missing-policy", "legacy"):
        require("missing matching R4PW sidecar" in messages, "missing-policy refusal not exercised")
    elif kind == "bad-policy":
        require("R4PW" in messages and ("CRC" in messages or "checksum" in messages), "present bad policy not exercised")
    elif kind == "global":
        require(report["models"] == 1 and len(report["spawn_inventory"]) == 1
                and {row["room"] for row in report["rows"]} == {"unassigned"}, "global ESL/DRS fixture not exercised")
    elif kind == "context":
        require(report["status"] == "SCANNED" and any(m["source"].startswith("@input/") for m in report["model_inventory"]),
                "external cast header not exercised")
        global_model = next(m for m in report["model_inventory"] if m["source"] == "em/em12.drs")
        require(global_model["memberships"] == [dict(room="r103", instances=2, origin="explicit room list")],
                "explicit room list not exercised")
        require(any(row["reason"] == "a_lit_scale" and row["status"] == "predicted"
                    and row["source"] == "st1/r103.dar" for row in report["rows"]), "bound lighting context not exercised")
    else:
        raise RuntimeError("unknown fixture kind: " + kind)


def run_cli(script, args, work, environment):
    destination = work / "out"
    require(not destination.exists(), "internal output destination must be new")
    command = [sys.executable, "-B", str(script), *args]
    process = subprocess.run(command, cwd=work, env=environment, capture_output=True)
    require(destination.is_dir(), "CLI did not produce its reports: " + process.stderr.decode(errors="replace"))
    require({p.name for p in destination.iterdir()} == OUTPUTS, "CLI artifact set changed")
    artifacts = {name: (destination / name).read_bytes() for name in sorted(OUTPUTS)}
    shutil.rmtree(destination)
    return dict(exit=process.returncode, stdout=process.stdout, stderr=process.stderr, artifacts=artifacts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default=BASE, help="Git commit containing the original scanner")
    parser.add_argument("--out", type=Path, required=True, help="new receipt JSON; never overwrite an existing file")
    args = parser.parse_args()
    require(not args.out.exists(), "receipt already exists; choose a new --out")
    base = git("rev-parse", "--verify", args.base + "^{commit}").decode().strip()
    scope_before = repository_scope(base)
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONHASHSEED="0")
    evidence = []
    with tempfile.TemporaryDirectory(prefix="re4dc-scan36-identity-") as temporary:
        work = Path(temporary)
        archive, baseline = work / "baseline.tar", work / "baseline"
        subprocess.run(["git", "archive", "--format=tar", "-o", str(archive), base,
                        "port/dreamcast/tools", "port/dreamcast/tests"], cwd=ROOT, check=True)
        archive_sha = file_hash(archive)
        baseline.mkdir()
        with tarfile.open(archive) as handle:
            handle.extractall(baseline, filter="data")
        archive.unlink()
        fixture = subprocess.run([sys.executable, "-B", "-c", FIXTURE_SCRIPT, str(baseline), str(work)],
                                 cwd=work, env=environment, capture_output=True)
        require(fixture.returncode == 0, "fixture generation failed: " + fixture.stderr.decode(errors="replace"))
        manifest = json.loads((work / "fixture-manifest.json").read_text())
        baseline_sources = manifest["source_sha256"]
        for path, value in baseline_sources.items():
            require(digest(git("show", base + ":" + path)) == value, "archived fixture source differs from Git: " + path)
        frozen_sources = source_hashes(baseline_sources)
        before = input_hashes(work / "inputs")
        for case in manifest["cases"]:
            reference = run_cli(baseline / SCANNER / "scan.py", case["args"], work, environment)
            require(reference["exit"] == case["expected_exit"], "baseline exit changed for " + case["name"])
            require(reference["stderr"] == b"", "baseline fixture emitted stderr")
            report = json.loads(reference["artifacts"]["report.json"])
            assert_fixture(case["kind"], report)
            comparisons = []
            for label, controls in (("absent", []), ("zero", ["--scan36=0"])):
                candidate = run_cli(ROOT / SCANNER / "scan.py", [*case["args"], *controls], work, environment)
                for field in ("exit", "stdout", "stderr"):
                    require(candidate[field] == reference[field], case["name"] + "/" + label + " differs: " + field)
                for name in sorted(OUTPUTS):
                    require(candidate["artifacts"][name] == reference["artifacts"][name],
                            case["name"] + "/" + label + " raw bytes differ: " + name)
                comparisons.append(dict(control=label, process_equal=True, raw_artifacts_equal=True, artifacts=len(OUTPUTS)))
            evidence.append(dict(name=case["name"], argv=case["args"], expected_exit=case["expected_exit"],
                result_status=report["status"], models=report["models"], texture_keys=report["textures"],
                stdout_sha256=digest(reference["stdout"]), stdout=reference["stdout"].decode(),
                stderr_sha256=digest(reference["stderr"]),
                artifacts={name: dict(bytes=len(raw), sha256=digest(raw)) for name, raw in reference["artifacts"].items()},
                comparisons=comparisons))
            print("PASS baseline/absent/zero:", case["name"], flush=True)
        after = input_hashes(work / "inputs")
        require(before == after, "scanner changed the fixture input set or bytes")
        require(source_hashes(baseline_sources) == frozen_sources, "candidate sources changed during identity gate")
        scope_after = repository_scope(base)
        require(scope_after["tracked_changed_paths"] == scope_before["tracked_changed_paths"],
                "tracked diff scope changed during identity gate")
    receipt = dict(status="PASS", schema="re4dc.scan36.off-identity/1", scope=__doc__, base=base,
        candidate_head=git("rev-parse", "HEAD").decode().strip(), python=sys.version,
        git_version=git("--version").decode().strip(), baseline_archive_sha256=archive_sha,
        baseline_fixture_source_sha256=baseline_sources, candidate_source_sha256=frozen_sources,
        repository_scope=scope_after, input_files=before, input_bytes_unchanged=True,
        scenarios=evidence, cli_runs=len(evidence) * 3, raw_artifact_comparisons=len(evidence) * 2 * len(OUTPUTS),
        process_result_comparisons=len(evidence) * 2,
        comparison="Exact bytes; same relative output path out for every sequential invocation; no normalization.",
        limits=["Public synthetic files only; no private assets or complete-disc scanner census.",
                "No target runtime, ELF, overlays or ISO was built; their zero delta is a source-scope deduction.",
                "Only absent and explicit-zero behavior is qualified here; enabled behavior has separate tests."])
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x") as handle:
        handle.write(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps(dict(status="PASS", scenarios=len(evidence), cli_runs=receipt["cli_runs"],
                          raw_artifact_comparisons=receipt["raw_artifact_comparisons"],
                          receipt=str(args.out), sha256=file_hash(args.out))))


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, subprocess.CalledProcessError, tarfile.TarError) as exc:
        raise SystemExit("verify_identity: " + str(exc)) from exc
