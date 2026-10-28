#!/usr/bin/env python3
"""Publish audit receipts preserving numeric results and source/artifact hashes.

Only repeated command arrays are omitted; paths are made portable. Raw receipt
SHA256 remains recorded. This is not for target identity artifacts themselves.
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--path-map", action="append", default=[], help="absolute-prefix=portable-name")
    args = ap.parse_args()
    source = args.input.resolve()
    raw = json.loads(source.read_text())
    assert raw["status"] == "PASS"
    replacements = [(str(ROOT), "$TREE"), (str(source.parent), "$RUN")]
    replacements += [pair.split("=", 1) for pair in args.path_map]
    replacements.sort(key=lambda pair: -len(pair[0]))

    def clean(value):
        if isinstance(value, dict):
            return {key: clean(item) for key, item in value.items() if key != "command"}
        if isinstance(value, list):
            return [clean(item) for item in value]
        if isinstance(value, str):
            for before, after in replacements:
                value = value.replace(before, after)
        return value

    result = clean(raw)
    result["raw_receipt_sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    result["compactor_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    result["compaction"] = "Numeric fields and source/object hashes unchanged; repeated command arrays omitted; local path prefixes substituted only in receipt text. No normalization of production source or objects."
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps(dict(status="PASS", input_bytes=source.stat().st_size, output_bytes=args.output.stat().st_size, output=str(args.output))))


if __name__ == "__main__":
    main()
