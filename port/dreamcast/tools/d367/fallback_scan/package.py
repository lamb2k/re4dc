#!/usr/bin/env python3
"""Extract/graft source ModelData in an existing converted DAR/DRS/tagged archive.

Grafting is same-sized and restricted to converter-receipted stream ranges.
The existing native NTR/ESQ table checker verifies every referenced byte still
matches. No registry/GC-source certificate is changed or generated here.
"""
import argparse
import json
from pathlib import Path
import struct

from convert import decode, require
from formats import CONTAINER_MAGIC, DRS_MAGIC, parse_model_bin, parse_room_archive, sha, span
from ps2_objects import remap_native_tables  # existing converter's offset/sidecar proof

SCHEMA = "re4dc.fallback29.member/1"


def inventory(data):
    result = parse_room_archive(data, source="package")
    return result["models"]


def select(data, key):
    matches = [m for m in inventory(data) if m["key"] == key]
    require(len(matches) == 1, "member key must identify exactly one native ModelData")
    return matches[0]


def extract(data, key):
    model = select(data, key)
    at, length = model["source_offset"], model["source_length"]
    member = span(data, at, length, "source ModelData member")
    return member, dict(schema=SCHEMA, package_sha256=sha(data), package_bytes=len(data),
        key=key, offset=at, length=length, member_sha256=sha(member),
        ownership="source-model", source_kind="PS2-converted-ModelData")


def native_payloads(data):
    if data[:32] not in (CONTAINER_MAGIC, DRS_MAGIC):
        return [(0, len(data))]
    result = []
    for at in range(32, 0x400, 32):
        kind, size, dest, offset = struct.unpack_from("<4I", data, at)
        if kind == 0xffffffff:
            break
        if kind == 0:
            require(not dest, "unexpected native destination")
            span(data, offset, size, "native archive payload")
            require(all(offset+size <= a or a+n <= offset for a,n in result), "overlapping native payloads")
            result.append((offset, size))
    return result


def graft(data, member, extracted, converted):
    require(extracted.get("schema") == SCHEMA and extracted.get("package_sha256") == sha(data) and
        extracted.get("package_bytes") == len(data), "source package receipt/hash mismatch")
    before, actual = extract(data, extracted.get("key"))
    require(extracted == actual, "member receipt/extent mismatch")
    require(converted.get("schema") == "re4dc.fallback29.convert/1" and
        converted.get("input_sha256") == sha(before) and converted.get("output_sha256") == sha(member),
        "conversion receipt/member hash mismatch")
    require(len(member) == len(before), "replacement must fit the identical member extent")
    original = parse_model_bin(before)
    parse_model_bin(member)  # actual FE adapter, including CI/bake extents
    ranges, seen = [], set()
    for row in converted.get("parts", []):
        if not row.get("changed"):
            continue
        index = row.get("index")
        require(type(index) is int and 0 <= index < len(original["parts"]) and index not in seen,
                "conversion receipt part index")
        seen.add(index)
        part = original["parts"][index]
        a, n = part["stream_offset"], part["stream_bytes"]
        require(row.get("stream_sha256") == sha(member[a:a+n]), "conversion stream hash mismatch")
        ranges.append((a, n))
    cursor = 0
    for a,n in sorted(ranges):
        require(cursor <= a and before[cursor:a] == member[cursor:a], "nonstream source data changed")
        cursor = a+n
    require(before[cursor:] == member[cursor:], "nonstream source data changed")
    at, length = actual["offset"], actual["length"]
    for model in inventory(data):
        if model["key"] == actual["key"]:
            continue
        other, size = model["source_offset"], model["source_length"]
        require(all(at+a+n <= other or other+size <= at+a for a,n in ranges),
                "selected stream aliases another model member")
    output = data[:at]+member+data[at+length:]
    tables = []
    for offset, size in native_payloads(data):
        old = data[offset:offset+size]
        new = output[offset:offset+size]
        checked, report = remap_native_tables(old, new)
        require(checked == new, "same-size replacement would alter a native sidecar")
        tables.append(dict(offset=offset, bytes=size, unchanged_tables=report))
    # Re-discover the archive after replacement. Every member remains at its
    # original boundary; unrelated native models retain exactly the same hash.
    old_models, new_models = inventory(data), inventory(output)
    require(len(old_models) == len(new_models), "archive model count changed")
    for old,new in zip(old_models,new_models):
        require(all(old[k] == new[k] for k in ("key","source_offset","source_length")), "archive member boundary changed")
        if old["key"] != actual["key"]:
            require(old["source_sha256"] == new["source_sha256"], "unrelated source model changed")
    return output, dict(schema="re4dc.fallback29.graft/1", input_sha256=sha(data), output_sha256=sha(output),
        bytes=len(data), key=actual["key"], offset=at, length=length,
        input_member_sha256=sha(before), output_member_sha256=sha(member), changed=output != data,
        native_tables=tables, unchanged_outside_member=True, unchanged_nonstream_member_bytes=True,
        ownership="source-model; external NMR/GC-source certificates are unsupported")


def write_new(path, content):
    with path.open("xb") as handle:
        handle.write(content)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    modes = ap.add_subparsers(dest="mode", required=True)
    listing = modes.add_parser("list")
    listing.add_argument("input", type=Path)
    extraction = modes.add_parser("extract")
    extraction.add_argument("input", type=Path)
    extraction.add_argument("output", type=Path)
    extraction.add_argument("--key", required=True)
    extraction.add_argument("--receipt", required=True, type=Path)
    replacement = modes.add_parser("graft")
    replacement.add_argument("input", type=Path)
    replacement.add_argument("member", type=Path)
    replacement.add_argument("output", type=Path)
    replacement.add_argument("--member-receipt", required=True, type=Path)
    replacement.add_argument("--conversion-receipt", required=True, type=Path)
    replacement.add_argument("--receipt", required=True, type=Path)
    args = ap.parse_args(argv)
    try:
        require(args.input.suffix.lower() in (".dar", ".drs", ".arc"),
                "use an existing converted DAR/DRS/tagged ARC; certified packs/events are unsupported")
        data = args.input.read_bytes()
        if args.mode == "list":
            print(json.dumps(dict(package_sha256=sha(data), bytes=len(data), models=[
                {k:m[k] for k in ("key","source_offset","source_length","source_sha256")}
                for m in inventory(data)]), indent=2, sort_keys=True))
            return
        require(not args.output.exists() and not args.receipt.exists() and
                args.output.resolve() != args.receipt.resolve(), "output/receipt must be distinct new files")
        if args.mode == "extract":
            output, report = extract(data, args.key)
        else:
            output, report = graft(data, args.member.read_bytes(), decode(args.member_receipt.read_bytes()),
                                   decode(args.conversion_receipt.read_bytes()))
        write_new(args.output, output)
        write_new(args.receipt, (json.dumps(report, indent=2, sort_keys=True)+"\n").encode())
        print(json.dumps(report, sort_keys=True))
    except (OSError, ValueError, KeyError, TypeError, struct.error) as exc:
        ap.exit(2, "package operation refused: "+str(exc)+"\n")


if __name__ == "__main__":
    main()
