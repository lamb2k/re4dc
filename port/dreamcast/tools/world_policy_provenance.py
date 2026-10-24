#!/usr/bin/env python3
"""Inspect WORLD_RECT21 lineage or prepare a separate original-policy control.

Inspection is the default and writes nothing. --prepare-original-policy=1
requires the exact committed runtime certificate before reversing material
keys through the committed runtime origin map. No caller certificate/hash can
authorize a file, and no source asset, certificate or sidecar is rewritten.
The output is policy preparation, not a complete or qualified control disc.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct

import scenery_data_variants as layout

RECT = Path(__file__).resolve().parent / "d367/texture_rect21"
CERT_FIELDS = ("room", "world_bytes", "placements", "parts", "meshes",
               "physical_body_crc", "physical_file_fnv", "mesh_crc",
               "mesh_bytes", "source_crc")
SOURCE_FIELDS = ("room", "world_bytes", "placements", "parts", "meshes",
                 "mesh_crc", "mesh_bytes", "source_crc")
TABLE_FILES = ("world_rect_provenance.h", "provenance_certificates.inc",
               "scoped_origin.h", "scoped_origins.inc", "provenance_certificate.json")
LIMITS = [
    "Policy control only: original textures and a matched original pack/recipe are still required.",
    "No texture reconstruction, whole DATA/pack/resident-state identity, look or performance qualification.",
    "Input geometry is unchanged; no mesh/cell/PVS proof is borrowed or regenerated.",
    "Only an existing source-bound R4SG may be preserved byte for byte; no sidecar binding is repaired.",
    "Build12's WORLD_RECT21=0 gate and the owner's SLI1-wash/SDS1-rejected decision remain unchanged.",
]


def require(ok, why):
    if not ok:
        raise ValueError(why)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def fnv(data):
    value = 2166136261
    for byte in data:
        value = ((value ^ byte) * 16777619) & 0xffffffff
    return value


def _rows(data, count, name):
    """Parse only the existing integer-row include grammar, never evaluate C++."""
    result = []
    for number, line in enumerate(data.decode("ascii").splitlines(), 1):
        line = line.split("//", 1)[0].strip()
        if not line:
            continue
        require(re.fullmatch(r"\{(?:\s*(?:0x[0-9a-fA-F]+|[0-9]+)U\s*,){%d}"
                             r"\s*(?:0x[0-9a-fA-F]+|[0-9]+)U\s*\}," % (count-1), line),
                f"unsupported committed table syntax: {name}:{number}")
        row = tuple(int(word, 0) for word in re.findall(r"(0x[0-9a-fA-F]+|[0-9]+)U", line))
        require(all(word <= 0xffffffff for word in row), f"table integer extent: {name}:{number}")
        result.append(row)
    require(result, "empty committed table: " + name)
    return result


def _load_tables():
    """Production has one repository-owned trust source and no override option."""
    raw = {name: (RECT / name).read_bytes() for name in TABLE_FILES}
    certs = [dict(zip(CERT_FIELDS, row)) for row in
             _rows(raw["provenance_certificates.inc"], 10, "provenance_certificates.inc")]
    count = re.search(rb"sizeof\(certificates\[0\]\)\s*==\s*(\d+)U", raw["world_rect_provenance.h"])
    require(count is not None and len(certs) == int(count[1]), "committed certificate count contract")
    origins = _rows(raw["scoped_origins.inc"], 4, "scoped_origins.inc")
    keys = [row[:2] for row in origins]
    require(keys == sorted(set(keys)), "committed origin keys must be unique and sorted")
    pins = json.loads(raw["provenance_certificate.json"])
    require(pins.get("schema") == 1 and isinstance(pins.get("rooms"), list),
            "unsupported original-policy receipt schema")
    return dict(certificates=certs, origins={row[:2]: row[2:] for row in origins},
                originals=pins["rooms"], hashes={name: sha(data) for name, data in raw.items()})


def _context(mesh, policy, room, tables):
    require(isinstance(room, int) and 0 <= room <= 0xffff, "room must be an explicit uint16 ID")
    package = layout.Package(mesh)
    head = layout.policy_header(policy, package, policy_diagnostics=True)
    actual = dict(room=room, world_bytes=len(policy), placements=head[2], parts=head[3],
                  meshes=head[4], physical_body_crc=head[5], physical_file_fnv=fnv(policy),
                  mesh_crc=package.h[3], mesh_bytes=len(mesh))
    # These are exactly the tuple/header/FNV predicates in the committed C++
    # helper. Package/policy structure and genuine CRCs were validated above.
    checks = []
    matched = []
    for cert in tables["certificates"]:
        if cert["room"] != room:
            continue
        differences = [{"field": name, "actual": value, "expected": cert[name]}
                       for name, value in actual.items() if value != cert[name]]
        checks.append(dict(source_crc=cert["source_crc"], mismatches=differences))
        if not differences:
            matched.append(cert)
    require(len(matched) <= 1, "ambiguous committed policy certificates")
    cert = matched[0] if matched else None
    report = dict(schema="re4dc-original-policy-control-1", room=f"r{room:03x}",
                  physical=actual, source_mesh_sha256=sha(mesh), physical_policy_sha256=sha(policy),
                  certificate_matched=cert is not None, certificate_checks=checks,
                  authenticated_source_policy_crc=cert["source_crc"] if cert else None,
                  committed_sources_sha256=tables["hashes"], limits=LIMITS)
    return package, head, cert, report


def _original_pin(cert, tables):
    # Old candidate hashes are deliberately not current-input authority. The
    # historical record contributes only an exactly matching source lineage.
    matches = [row for row in tables["originals"]
               if all(row.get(name) == cert[name] for name in SOURCE_FIELDS)]
    if not matches:
        return None
    for row in matches:
        require(all(isinstance(row.get(name), str) and re.fullmatch(r"[0-9a-f]{64}", row[name])
                    for name in ("source_world_sha256", "mesh_sha256")),
                "incomplete pinned original-policy SHA evidence")
    pins = {(row["source_world_sha256"], row["mesh_sha256"]) for row in matches}
    require(len(pins) == 1, "conflicting pinned original-policy SHA evidence")
    return dict(source_world_sha256=matches[0]["source_world_sha256"],
                mesh_sha256=matches[0]["mesh_sha256"],
                source="d367/texture_rect21/provenance_certificate.json")


def _restore(mesh, policy, package, head, cert, tables, original_policy=None):
    require(cert is not None, "original-policy preparation requires an exact committed runtime certificate")
    pin = _original_pin(cert, tables)
    if pin:
        require(sha(mesh) == pin["mesh_sha256"], "pinned source mesh SHA256 mismatch")
    out = bytearray(policy)
    changed_parts = []
    for part in range(head[3]):
        offset = 32+16*part
        key = struct.unpack_from("<II", policy, offset)
        original = tables["origins"].get(key, key)  # Same one-step lookup as scoped_origin.h.
        if original != key:
            struct.pack_into("<II", out, offset, *original)
            changed_parts.append(part)
    restored_crc = layout.crc(out[32:])
    require(restored_crc == cert["source_crc"],
            f"restored policy body CRC mismatch: actual={restored_crc:08x} certified={cert['source_crc']:08x}")
    struct.pack_into("<I", out, 20, restored_crc)
    out = bytes(out)
    require(out[:20] == policy[:20] and out[24:32] == policy[24:32], "restored policy header changed")
    require(all(out[32+16*i+8:32+16*(i+1)] == policy[32+16*i+8:32+16*(i+1)]
                for i in range(head[3])), "non-key material fields changed")
    require(out[32+16*head[3]:] == policy[32+16*head[3]:], "policy placements changed")
    layout.policy_header(out, package, policy_diagnostics=True)
    if pin:
        require(sha(out) == pin["source_world_sha256"], "pinned original policy SHA256 mismatch")
    if original_policy is not None:
        require(bytes(original_policy) == out, "supplied original policy is not byte-identical to restored control")
    evidence = ("runtime certificate + exact inverse-map restoration + pinned original policy/mesh SHA256"
                if pin else "runtime certificate + exact inverse-map restoration; original archive SHA unavailable")
    report = dict(policy_bytes=len(out), policy_body_crc=restored_crc, policy_sha256=sha(out),
                  changed_key_parts=changed_parts,
                  changed_byte_offsets=[i for i, (a, b) in enumerate(zip(policy, out)) if a != b],
                  unchanged_non_key_material_bytes=True, unchanged_placements=True,
                  archived_source_byte_identity=pin is not None, pinned_original=pin,
                  supplied_original_byte_equal=True if original_policy is not None else None,
                  evidence=evidence,
                  required_original_texture_keys=sorted({f"{a:08x}-{b:08x}" for a, b in
                      (struct.unpack_from("<II", out, 32+16*i) for i in range(head[3])) if a or b}),
                  original_texture_availability="UNVERIFIED", whole_pack_identity="UNVERIFIED")
    return out, report


def _groups_check(groups, package, policy):
    require(32 <= len(groups) <= 262144, "R4SG runtime file-size limit (32..262144 bytes)")
    layout.parse_groups(groups, package, policy, policy_diagnostics=True)


def inspect(mesh, policy, room, groups=None):
    """Read-only field inspection; never relax the ordinary Build12 parser."""
    tables = _load_tables()
    package, head, cert, report = _context(mesh, policy, room, tables)
    report["mode"] = "INSPECT_ONLY_NO_FILES_WRITTEN"
    restored = None
    try:
        restored, report["restored_control"] = _restore(mesh, policy, package, head, cert, tables)
        report["preparation_available"] = True
    except ValueError as error:
        report.update(preparation_available=False, preparation_refusal=str(error))
    if groups is not None:
        report["source_groups_sha256"] = sha(groups)
        for label, candidate in (("physical_policy_groups", policy), ("original_policy_groups", restored)):
            if candidate is None:
                report[label] = dict(status="UNAVAILABLE")
                continue
            try:
                _groups_check(groups, package, candidate)
                report[label] = dict(status="PASS")
            except ValueError as error:
                report[label] = dict(status="REFUSED", reason=str(error))
    return report


def prepare(mesh, policy, room, groups=None, original_policy=None):
    """Return control policy and exact source-bound groups; never mutate inputs."""
    tables = _load_tables()
    package, head, cert, report = _context(mesh, policy, room, tables)
    restored, recovery = _restore(mesh, policy, package, head, cert, tables, original_policy)
    if groups is not None:
        _groups_check(groups, package, restored)  # Physical-only binding refuses; no header repair.
    report.update(mode="ORIGINAL_POLICY_CONTROL_ONLY", restored_control=recovery,
                  input_geometry_unchanged=True, groups_byte_identical=groups is not None,
                  groups_sha256=sha(groups) if groups is not None else None,
                  runtime_policy_requirement="Use this same restored policy and original textures in both WORLD_RECT21=0 arms.",
                  full_control_disc_qualified=False)
    return restored, bytes(groups) if groups is not None else None, report


def _room(text):
    return int(text[1:], 16) if text.lower().startswith("r") else int(text, 0)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("mesh", type=Path)
    ap.add_argument("policy", type=Path)
    ap.add_argument("--room", type=_room, required=True, help="explicit room, e.g. r101 or 0x101")
    ap.add_argument("--source-groups", type=Path, help="optional original-policy-bound R4SG; never repaired")
    ap.add_argument("--original-policy", type=Path, help="optional original bytes for exact equality, not certificate authority")
    ap.add_argument("--prepare-original-policy", type=int, choices=(0, 1), nargs="?", const=1, default=0)
    ap.add_argument("--out", type=Path, help="new directory, required only for explicit preparation")
    args = ap.parse_args()
    require(bool(args.prepare_original_policy) == (args.out is not None),
            "--out requires --prepare-original-policy=1; inspection writes no files")
    require(args.prepare_original_policy or args.original_policy is None,
            "--original-policy equality is a preparation check")
    mesh, policy = args.mesh.read_bytes(), args.policy.read_bytes()
    groups = args.source_groups.read_bytes() if args.source_groups else None
    if not args.prepare_original_policy:
        print(json.dumps(inspect(mesh, policy, args.room, groups), indent=2, sort_keys=True))
        return
    restored, out_groups, report = prepare(mesh, policy, args.room, groups,
                                          args.original_policy.read_bytes() if args.original_policy else None)
    report.update(source_mesh=str(args.mesh), source_policy=str(args.policy),
                  source_groups=str(args.source_groups) if args.source_groups else None,
                  supplied_original=str(args.original_policy) if args.original_policy else None)
    files = {"ps2-world.r4pw": restored}
    if out_groups is not None:
        files["ps2-world.r4sg"] = out_groups
    # Validate everything before creating the new output. Existing directories
    # and input assets are never overwritten, even when the conversion refuses.
    args.out.mkdir(parents=True, exist_ok=False)
    for name, data in files.items():
        (args.out / name).write_bytes(data)
    (args.out / "policy-report.json").write_text(json.dumps(report, indent=2, sort_keys=True)+"\n")
    (args.out / "SHA256SUMS").write_text("".join(sha(data)+"  "+name+"\n" for name, data in files.items()))
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
