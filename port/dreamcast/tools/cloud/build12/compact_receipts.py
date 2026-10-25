#!/usr/bin/env python3
"""Losslessly intern repeated receipt text/structures; never discard metrics.

Each {"$ref": "rNNNN"} names an entry in the document's pool. Expand with
expand_receipt(document) to recover the original parsed JSON exactly. The
original full file's SHA256/extent binds formatting and all unmodified values.
This removes repeated assumptions, flags, zero-region structures and stacks
without dropping traffic regions, build commands, source hashes or results.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def compact_receipt(raw, source):
    value = json.loads(raw)
    counts = Counter()

    def count(node):
        if isinstance(node, dict):
            if set(node) == {"$ref"}:
                raise ValueError("input uses the compact receipt reserved key")
            for child in node.values():
                count(child)
        elif isinstance(node, list):
            for child in node:
                count(child)
        if isinstance(node, (str, dict, list)):
            key = canonical(node)
            if len(key) >= 96:
                counts[key] += 1

    count(value)
    names, pool = {}, {}

    def encode(node, allow_reference=True):
        if isinstance(node, (str, dict, list)):
            key = canonical(node)
            if allow_reference and counts[key] > 1:
                if key not in names:
                    name = names[key] = "r%04d" % len(names)
                    pool[name] = encode(node, False)
                return {"$ref": names[key]}
        if isinstance(node, dict):
            return {key: encode(child) for key, child in node.items()}
        if isinstance(node, list):
            return [encode(child) for child in node]
        return node

    document = dict(format="RE4DC_COMPACT_RECEIPT1",
        full_receipt=dict(path=str(source), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()),
        encoding="Lossless repeated-subtree interning; $ref names pool entries. Every original metric and command is retained.",
        value=encode(value), pool=pool)
    assert expand_receipt(document) == value, "receipt expansion is not identical"
    return document


def expand_receipt(document):
    if document.get("format") != "RE4DC_COMPACT_RECEIPT1":
        raise ValueError("unknown receipt format")
    pool, active, cache = document["pool"], set(), {}

    def expand(node):
        if isinstance(node, dict) and set(node) == {"$ref"}:
            name = node["$ref"]
            if name in active:
                raise ValueError("cyclic receipt reference")
            if name not in cache:
                active.add(name); cache[name] = expand(pool[name]); active.remove(name)
            return cache[name]
        if isinstance(node, dict):
            return {key: expand(value) for key, value in node.items()}
        if isinstance(node, list):
            return [expand(value) for value in node]
        return node

    return expand(document["value"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", action="append", required=True, help="output-name=full-receipt.json")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    summaries = []
    for item in args.receipt:
        name, filename = item.split("=", 1)
        if not name or Path(name).name != name:
            raise ValueError("receipt name must be one filename stem")
        source, target = Path(filename), args.output/(name+".json")
        if source.resolve() == target.resolve():
            raise ValueError("output aliases the source receipt")
        raw = source.read_bytes()
        document = compact_receipt(raw, source)
        target.write_text(json.dumps(document, indent=2)+"\n")
        summaries.append(dict(path=str(target), full_bytes=len(raw), compact_bytes=target.stat().st_size,
                              interned=len(document["pool"]), full_sha256=document["full_receipt"]["sha256"],
                              compact_sha256=hashlib.sha256(target.read_bytes()).hexdigest()))
    print(json.dumps(dict(status="PASS", lossless_expansion=True, receipts=summaries), indent=2))


if __name__ == "__main__":
    main()
