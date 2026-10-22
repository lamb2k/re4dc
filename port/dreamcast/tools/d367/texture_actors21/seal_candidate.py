#!/usr/bin/env python3
"""Independently decode every candidate level and seal sparse pack replacements.

Runs with standard-library Linux Python and the separately pinned KOS pvrtex
oracle. No game, build, guest, staging or release actions.
"""
from __future__ import annotations

import argparse
import ctypes
import json
from pathlib import Path
import shutil

import actor_candidate as actor


def seal(directory, pack_blob, oracle_path, oracle_sha256):
    receipt = directory / "independent-decode.json"
    if receipt.exists():
        raise ValueError("sealed candidate already exists; do not rewrite it")
    oracle_blob = oracle_path.read_bytes()
    if actor.sha(oracle_blob) != oracle_sha256:
        raise ValueError("independent decoder binary hash differs from pin")
    contract = json.loads((directory / "contract.json").read_text())
    report = json.loads((directory / "report.json").read_text())
    if actor.sha(pack_blob) != contract["source_pack_sha256"] or actor.sha(pack_blob) != report["source_pack_sha256"]:
        raise ValueError("exact source pack differs from candidate and contract")
    for proof in contract["proofs"]:
        if actor.sha((directory / proof["path"]).read_bytes()) != proof["sha256"]:
            raise ValueError("copied consumer proof changed: " + proof["id"])
    actor.texpack.verify(pack_blob)
    original = actor.read_pak(pack_blob)
    if actor.texpack.build(original)[0] != pack_blob:
        raise ValueError("source pack is not canonical")
    lib = ctypes.CDLL(str(oracle_path.resolve()))
    call = lib.mipmap_oracle_decode
    call.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_uint, ctypes.c_uint,
                     ctypes.c_int, ctypes.c_uint, ctypes.c_void_p, ctypes.c_size_t]
    call.restype = ctypes.c_int

    def decode(native, side):
        source = ctypes.create_string_buffer(native.payload)
        output = ctypes.create_string_buffer(side * side * 4)
        got = call(source, len(native.payload), native.texture[3], native.size,
                   native.mipmapped, side.bit_length() - 1, output, len(output))
        if got != len(output):
            raise ValueError(f"pinned oracle decode failed: {side}, return {got}")
        expected = bytes(c for p in actor.mip.decode_level(native, side) for c in p)
        if output.raw != expected:
            raise ValueError("independent decoded pixels differ at level " + str(side))
        return output.raw

    candidate, rows, selected = dict(original), [], set()
    for item in contract["textures"]:
        name, key = item["key"], actor.parse_key(item["key"])
        before_blob = (directory / "originals" / (name + ".re4tex")).read_bytes()
        after_blob = (directory / "replacements" / (name + ".re4tex")).read_bytes()
        if before_blob != original[key] or actor.sha(before_blob) != item["source_package_sha256"]:
            raise ValueError("private original no longer equals source normal-pack winner")
        before, after = actor.mip.read_native_vq(before_blob), actor.mip.read_native_vq(after_blob)
        if before.codebook != after.codebook or before.base_indices != after.base_indices:
            raise ValueError("base or codebook changed")
        base = decode(before, before.size)
        levels = []
        for power in range(after.size.bit_length() if after.mipmapped else 1):
            side = 1 << power if after.mipmapped else after.size
            rgba = decode(after, side)
            if side == before.size and rgba != base:
                raise ValueError("independent original and candidate base pixels differ")
            levels.append(dict(side=side, rgba_bytes=len(rgba), rgba_sha256=actor.sha(rgba)))
        candidate[key], selected = after_blob, selected | {key}
        rows.append(dict(key=name, source_package_sha256=actor.sha(before_blob),
                         candidate_package_sha256=actor.sha(after_blob),
                         codebook_sha256=actor.sha(before.codebook), base_indices_sha256=actor.sha(before.base_indices),
                         base_rgba_sha256=actor.sha(base), codebook_exact=True, base_indices_exact=True,
                         base_pixels_exact=True, levels=levels))
    unchanged = {k: actor.sha(v) for k, v in original.items() if k not in selected}
    fingerprint = actor.sha("\n".join("%08x-%08x %s" % (*k, v) for k, v in sorted(unchanged.items())).encode())
    if fingerprint != report["unselected_identity_sha256"] or len(unchanged) != report["unselected_packages"]:
        raise ValueError("unselected package identity receipt differs")
    for name, expected in report["protected_existing_ganado"].items():
        key = actor.parse_key(name)
        if candidate[key] != original[key] or actor.sha(candidate[key]) != expected:
            raise ValueError("protected existing Ganado mip changed")
    combined, count = actor.texpack.build(candidate)
    actor.texpack.verify(combined)
    if actor.read_pak(combined) != candidate or count != len(original):
        raise ValueError("candidate pack reconstruction changed an unrelated entry")
    out = dict(schema="re4dc-actor-mip-independent-seal-1", oracle_sha256=oracle_sha256,
               oracle="KOS pvrtex independent decoder; actual pinned C implementation",
               source_pack_sha256=actor.sha(pack_blob), source_pack_bytes=len(pack_blob),
               reconstructed_candidate_pack_sha256=actor.sha(combined), reconstructed_candidate_pack_bytes=len(combined),
               candidate_pack_archive_delta=len(combined) - len(pack_blob), candidate_pack_written=False,
               normal_pack_entries=count, unselected_packages_unchanged=len(unchanged),
               protected_ganado_packages_unchanged=len(report["protected_existing_ganado"]),
               independent_decoded_levels=sum(len(r["levels"]) for r in rows), textures=rows,
               independent_all_levels_pass=True, base_codebook_indices_pixels_exact=True,
               runtime_vram_look_gameplay_and_hardware_acceptance=False)
    (directory / "oracle").mkdir()
    shutil.copy2(oracle_path, directory / "oracle" / oracle_path.name)
    receipt.write_text(json.dumps(out, indent=2) + "\n")
    files = [p for p in sorted(directory.rglob("*")) if p.is_file() and p.name != "SHA256SUMS"]
    (directory / "SHA256SUMS").write_text("".join(actor.sha(p.read_bytes()) + "  " + p.relative_to(directory).as_posix() + "\n" for p in files))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("candidate", type=Path)
    ap.add_argument("--source-pack", type=Path, required=True)
    ap.add_argument("--oracle", type=Path, required=True)
    ap.add_argument("--oracle-sha256", required=True)
    a = ap.parse_args()
    result = seal(a.candidate, a.source_pack.read_bytes(), a.oracle, a.oracle_sha256)
    print(json.dumps({k: result[k] for k in ("normal_pack_entries", "independent_decoded_levels", "candidate_pack_archive_delta", "independent_all_levels_pass")}))


if __name__ == "__main__":
    main()
