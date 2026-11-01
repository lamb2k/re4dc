#!/usr/bin/env python3
"""Retain an OFF proof only when every compiled OFF input is still identical.

After an enabled-only conditional include changes, its OFF translation units
need not be rebuilt. This check compares every actual OFF compiler dependency,
all Make/recipe inputs, generated-header identities and the original gate
script hash. Any changed OFF input refuses reuse. Enabled evidence is removed
and must be supplied by a fresh ON gate. Artifact bytes and hashes are retained
unchanged from the original successful complete compile receipt.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True,
                        help="Keep beside original raw receipt so its unchanged artifacts remain available")
    args = parser.parse_args()
    source = args.input.resolve()
    assert args.output.resolve().parent == source.parent
    raw = json.loads(source.read_text())
    assert raw["status"] == "PASS" and raw["off_identity_comparisons"] > 0
    names = {name for name in raw["artifacts"] if name.endswith(("-baseline", "-absent", "-zero"))}
    current = {name for name in names if not name.endswith("-baseline")}
    closure = {}
    for name in current:
        for dependencies in raw["dependency_sha256"][name].values():
            for path, digest in dependencies.items():
                assert closure.get(path, digest) == digest
                closure[path] = digest
        for row in raw["profiles"][name]["profiles"].values():
            for path, digest in row["recipe_inputs"]["source_sha256"].items():
                assert closure.get(path, digest) == digest
                closure[path] = digest
    gate = "port/dreamcast/tools/cloud/build25/build_controls.py"
    closure[gate] = raw["source_sha256"][gate]
    assert closure == {path: sha(ROOT / path) for path in closure}, "an OFF compiler/build input changed; rebuild OFF"
    for name in names:
        for unit, artifacts in raw["artifacts"][name].items():
            for suffix in ("ii", "o"):
                assert sha(source.parent / f"{name}-{unit}.{suffix}") == artifacts[suffix]["sha256"], "OFF artifact changed"
    result = copy.deepcopy(raw)
    for key in ("artifacts", "profiles", "dependency_sha256", "make_states"):
        result[key] = {name: row for name, row in result[key].items() if name in names}
    result["partial_links"] = {}
    result["enabled_compiles"] = []
    result["gate_half"] = "off"
    result["source_sha256"] = closure
    result["off_closure_revalidation"] = dict(status="PASS", inputs=len(closure),
        original_complete_receipt_sha256=sha(source), checker_sha256=sha(Path(__file__)),
        note="Every actual OFF compiler dependency and Make/recipe input is unchanged. Enabled-only source changes are outside this proof; fresh ON evidence is required.")
    with args.output.open("x") as destination:
        json.dump(result, destination, indent=2)
        destination.write("\n")
    print(json.dumps(dict(status="PASS", off_comparisons=result["off_identity_comparisons"], inputs=len(closure), output=str(args.output))))


if __name__ == "__main__":
    main()
