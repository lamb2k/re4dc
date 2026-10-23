#!/usr/bin/env python3
"""Bind a pinned historical texture-load audit to immutable full RE4TEX bytes.

This offline helper never reads new guest logs, scans a store, or changes assets.
The generated exceptions record historical LOAD evidence, not accepted emissions.
"""
import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import re
import stat
import struct


KEY = re.compile(r"[0-9a-f]{8}-[0-9a-f]{8}\Z")
SHA = re.compile(r"[0-9a-f]{64}\Z")
ROOM = re.compile(r"r([0-9a-f]{3})\Z")
CLASSES = {"PS2-native", "PS2-fx(GC key)", "PS2-lib(GC key)",
           "store-other", "GC-fx(no PS2)", "GC/unknown"}
OMISSIONS = ["source models/props", "weapon geometry", "fonts/UI sheets",
             "sample banks", "streams", "movies", "non-texture effects",
             "unobserved rooms/scenes", "emitted-use evidence"]


def require(ok, message):
    if not ok:
        raise ValueError(message)


def unique_object(pairs):
    out = {}
    for key, value in pairs:
        require(key not in out, "duplicate JSON key: " + key)
        out[key] = value
    return out


def decode_json(raw):
    return json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def pinned(path, expected):
    require(isinstance(expected, str) and SHA.fullmatch(expected), "invalid pinned SHA256")
    raw = Path(path).read_bytes()
    require(digest(raw) == expected, "pinned input SHA256 mismatch: " + str(path))
    return raw


def fingerprint(st):
    return (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns)


def contained(path, roots):
    path = Path(path).resolve(strict=True)
    require(any(path.is_relative_to(root) for root in roots), "payload outside intended store: " + str(path))
    require(stat.S_ISREG(path.stat().st_mode), "payload is not a regular file")
    return path


def hash_file(fp):
    fp.seek(0)
    result = hashlib.sha256()
    for block in iter(lambda: fp.read(1 << 20), b""):
        result.update(block)
    return result.hexdigest()


def read_audit(raw):
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8")), delimiter="\t")
    require(reader.fieldnames == ["key", "bytes", "class", "in_use_rooms", "resident", "evidence"],
            "unexpected old audit columns")
    rows = {}
    for line, row in enumerate(reader, 2):
        require(None not in row and all(v is not None for v in row.values()), "malformed audit row")
        key = row["key"]
        require(KEY.fullmatch(key), "invalid texture identity")
        require(key not in rows, "duplicate audit texture identity")
        require(row["class"] in CLASSES, "unreviewed audit class")
        require(row["bytes"].isdigit() and int(row["bytes"]) >= 8, "invalid audit member size")
        require(row["resident"] in ("0", "1"), "invalid resident flag")
        rooms = row["in_use_rooms"].split(",") if row["in_use_rooms"] else []
        require(len(rooms) == len(set(rooms)), "duplicate audit room")
        require(all(ROOM.fullmatch(room) for room in rooms), "invalid audit room; no wildcards")
        row.update(line=line, rooms=sorted(rooms))
        rows[key] = row
    require(rows, "empty old audit")
    return rows


def pak_index(fp, size):
    fp.seek(0)
    head = fp.read(24)
    require(len(head) == 24 and head[:8] == b"RE4PAK1\0", "invalid RE4PAK header")
    version, count, index, data = struct.unpack_from("<4I", head, 8)
    require(version == 1 and 0 < count <= 100000, "unsupported RE4PAK version/count")
    require(24 <= index and index + count * 16 <= data <= size, "invalid RE4PAK index bounds")
    fp.seek(index)
    entries = {}
    for _ in range(count):
        crc, fnv, off, length = struct.unpack("<4I", fp.read(16))
        key = f"{crc:08x}-{fnv:08x}"
        require(key not in entries, "duplicate RE4PAK texture identity")
        require(length >= 8 and data <= off <= size - length, "invalid RE4PAK member bounds")
        entries[key] = (off, length)
    end = data
    for off, length in sorted(entries.values()):
        require(off >= end, "overlapping RE4PAK members")
        end = off + length
    return entries


def reviewed_proofs(raw):
    if raw is None:
        return {}
    obj = decode_json(raw)
    require(set(obj) == {"schema", "entries"} and type(obj["schema"]) is int and obj["schema"] == 1,
            "invalid reviewed proof envelope")
    require(isinstance(obj["entries"], list), "invalid reviewed proof entries")
    proofs = {}
    for row in obj["entries"]:
        require(isinstance(row, dict) and set(row) == {"kind", "id", "sha256", "provenance", "evidence", "source"},
                "invalid reviewed proof fields")
        require(all(isinstance(v, str) and v.strip() == v and v for v in row.values()), "empty proof field")
        require(row["kind"] == "texture" and KEY.fullmatch(row["id"]) and SHA.fullmatch(row["sha256"]),
                "invalid reviewed proof identity")
        require(row["provenance"] in ("ps2", "authored", "gc"), "invalid reviewed source origin")
        require(row["id"] not in proofs, "duplicate reviewed proof identity")
        proofs[row["id"]] = row
    return proofs


def generate(audit_raw, manifest_raw, package_raw, roots, audit_label, proofs_raw=None):
    """Return deterministic documents; roots are explicit readonly private stores.

    Metadata must first be pinned by the CLI (or by a reviewed calling fixture).
    No naming convention, old class, VQ/mip conversion or source path proves origin.
    """
    audit = read_audit(audit_raw)
    manifest = decode_json(manifest_raw)
    package = decode_json(package_raw)
    roots = [Path(root).resolve(strict=True) for root in roots]
    require(roots and all(root.is_dir() for root in roots), "missing intended store roots")
    record = manifest["dc/tex.pak"]
    require(set(record) == {"sha256", "size"} and SHA.fullmatch(record["sha256"])
            and type(record["size"]) is int and record["size"] >= 24, "invalid audit pack manifest")
    source = contained(package["replace"]["dc/tex.pak"], roots)
    proofs = reviewed_proofs(proofs_raw)
    # Catalog historical loads, resident-only identities and old native references.
    selected = {k: row for k, row in audit.items()
                if row["rooms"] or row["resident"] == "1" or row["class"] == "PS2-native"}
    require(set(proofs) <= set(selected), "reviewed proof outside historical audit scope")
    catalog, exceptions, history = [], [], []
    with source.open("rb") as fp:
        before = fingerprint(source.stat())
        require(before == fingerprint(os.fstat(fp.fileno())), "payload path changed while opening")
        require(before[2] == record["size"] and hash_file(fp) == record["sha256"], "audit pack SHA256/size mismatch")
        index = pak_index(fp, before[2])
        require(set(audit) == set(index), "audit/pack identity set mismatch")
        for key in sorted(audit):
            require(index[key][1] == int(audit[key]["bytes"]), "audit/pack member size mismatch")
        for key, row in sorted(selected.items()):
            off, length = index[key]
            fp.seek(off)
            raw = fp.read(length)
            require(len(raw) == length and raw[:8] == b"RE4DCTX\0", "invalid immutable RE4TEX member")
            sha = digest(raw)  # Entire member, including the exact immutable header.
            provenance = "unknown"
            evidence = (f"{audit_label}:line={row['line']}; audit_sha256={digest(audit_raw)}; "
                        f"pack_sha256={record['sha256']}; offset={off}; bytes={length}; historical_load_only")
            proof = proofs.get(key)
            if proof:
                require(proof["sha256"] == sha, "reviewed proof payload mismatch")
                provenance = proof["provenance"]
                evidence += (f"; reviewed_proofs_sha256={digest(proofs_raw)}; "
                             f"source_origin={proof['source']}; proof={proof['evidence']}")
            catalog.append(dict(kind="texture", id=key, sha256=sha, provenance=provenance,
                                evidence=evidence, source=f"{source}#offset={off}&bytes={length}"))
            history.append(dict(id=key, audit_class=row["class"], loaded_rooms=row["rooms"],
                                resident=row["resident"] == "1", emitted_rooms=[]))
            if provenance in ("unknown", "gc"):
                for room in row["rooms"]:
                    exceptions.append(dict(room="0" + room[1:], kind="texture", id=key, sha256=sha,
                                           provenance=provenance, owner="gc-port23",
                                           reason=f"Historical texture load, not emission; source origin {provenance}; old audit class {row['class']}.",
                                           evidence=evidence))
        # Rehash the unchanged open file after reading members; detect replacement too.
        require(hash_file(fp) == record["sha256"], "payload mutated while reading")
        require(before == fingerprint(os.fstat(fp.fileno())) == fingerprint(source.stat()),
                "payload changed while reading")
    exceptions.sort(key=lambda row: (row["room"], row["kind"], row["id"], row["sha256"]))
    report = dict(schema=1, audit_sha256=digest(audit_raw), manifest_sha256=digest(manifest_raw),
                  package_sha256=digest(package_raw), pack_sha256=record["sha256"],
                  proofs_sha256=digest(proofs_raw) if proofs_raw is not None else None,
                  audit_rows=len(audit), catalog_rows=len(catalog), exceptions=len(exceptions),
                  loaded_rooms=sorted({r for row in history for r in row["loaded_rooms"]}),
                  unproven_old_ps2_rows=sum(row["audit_class"].startswith("PS2") and
                      catalog[i]["provenance"] == "unknown" for i, row in enumerate(history)),
                  historical_loads_only=True, no_emission_or_gate_pass_claim=True,
                  payload_scope="Historical audit tex.pak members only; loose overrides are not separately bound",
                  unbound_loose_overrides=sorted(name for name in package["replace"]
                      if name.endswith(".re4tex") and name.startswith("dc/tex/")),
                  omissions=OMISSIONS, history=history)
    return {"catalog.json": dict(schema=1, entries=catalog),
            "reviewed-seed.json": dict(schema=1, entries=exceptions), "seed-report.json": report}


def encode(obj):
    return (json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode("utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("audit", "manifest", "package"):
        parser.add_argument("--" + name, required=True, type=Path)
        parser.add_argument("--" + name + "-sha256", required=True)
    parser.add_argument("--store-root", action="append", required=True, type=Path)
    parser.add_argument("--proofs", type=Path)
    parser.add_argument("--proofs-sha256")
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    require(bool(args.proofs) == bool(args.proofs_sha256), "proofs and pinned proofs SHA256 must be supplied together")
    require(not args.out_dir.exists(), "output directory must be new; never overwrite a reviewed baseline")
    output = args.out_dir.resolve()
    roots = [root.resolve(strict=True) for root in args.store_root]
    require(not any(output.is_relative_to(root) for root in roots), "output must stay outside readonly stores")
    docs = generate(pinned(args.audit, args.audit_sha256), pinned(args.manifest, args.manifest_sha256),
                    pinned(args.package, args.package_sha256), roots, str(args.audit.resolve()),
                    pinned(args.proofs, args.proofs_sha256) if args.proofs else None)
    # All validation completes before creating outputs; no guest data is copied.
    args.out_dir.mkdir(parents=True, exist_ok=False)
    for name, doc in docs.items():
        (args.out_dir / name).write_bytes(encode(doc))
    print(json.dumps({k: docs["seed-report.json"][k] for k in
                      ("catalog_rows", "exceptions", "unproven_old_ps2_rows", "pack_sha256")}, sort_keys=True))


if __name__ == "__main__":
    main()
