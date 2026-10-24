#!/usr/bin/env python3
"""Expand the real Make-derived Test22 public actor recipes.

The established public-world helper supplies the release recipe and generated
headers; this module asks Make for native_actor_fast.o itself. ACTOR_DIRECT is
selected by NATIVE_ACTOR_DIRECT in its generated header, never by appending a
contradictory compiler definition. Direct-off is a compatibility profile: the
dependent grouped-submit / plan options are explicitly disabled.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
ROOT = DC.parents[1]
spec = importlib.util.spec_from_file_location(
    "actor_public_profile_helpers", HERE.parent / "world_submit_spike/build_profile.py")
helpers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helpers)
Build, sections, sha, stack_usage = helpers.Build, helpers.sections, helpers.sha, helpers.stack_usage

DIRECT_OFF = """COARSE_ONE_SUBMIT COARSE_GATE_ONCE ACTOR_PLAN ACTOR_TRANSACTION
ACTOR_LEON_NATIVE_LOOK ACTOR_APPEARANCE_ALIAS ACTOR_PL08 ACTOR_PL08_PACK
ACTOR_GANADO_APP0_GRIP ACTOR_PROOF_LEAN ACTOR_MATERIAL_RECORD ACTOR_BIND_REUSE
SS_CERT SS_CERT_PARTNER_CAPACITY LEON_HAND_POSES LEON_SOURCE_LIGHT
LEON_LIGHT_HEADROOM LEON_LIGHT_FILL CROWD_CULL CROWD_READOPT CROWD_READOPT_MEMO
CROWD_FOGSKIP CROWD_INVIS_SKIP NATIVE_MODEL_REGISTRY NATIVE_MODEL_REGISTRY_PACK
NATIVE_MODEL_REGISTRY_TX NATIVE_MODEL_REGISTRY_PALBOUND NATIVE_MODEL_REGISTRY_POOL
NATIVE_MODEL_REGISTRY_IMMUTABLE_ALIAS NATIVE_MODEL_REGISTRY_FIRST NATIVE_MODEL_REGISTRY_LOD
RIGID_CHUNK PS2_INTERIOR_ACTORS ENEMY_VIS_CULL ACTOR_PROBE_LIGHT
PS2_GANADO_F PS2_GIGANTE PS2_DELLAGO PS2_ANIMALS PS2_CROW PS2_WOLF
PS2_CAST_MERCHANT PS2_CAST_MERCHANT_LIT PS2_CAST_CH1 PS2_CAST_BOAT
PS2_CH1_ENEMY PS2_ASHLEY PS2_ASHLEY_ROOMS CHARBAKE_TOGGLE""".split()


def derive(output, compiler, kos, sdk, *, direct_values=(0, 1), cone_values=(0, 1, 2), lean=None):
    output.mkdir(parents=True, exist_ok=False)
    seed = output / "public-seed"
    _, shared = helpers.release_profile.derive(seed, compiler, kos, sdk)
    overlay, overlay_receipt = helpers.pvr_overlay(output, kos)
    profiles, receipt = {}, {}
    for direct in direct_values:
        for cone in cone_values:
            name = f"d{direct}-c{cone}"
            destination = output / name
            destination.mkdir()
            changes = [f"NATIVE_ACTOR_DIRECT={direct}", f"ACTOR_BACKFACE_CONE={cone}", "ACTOR_BACKFACE=0"]
            if not direct:
                changes += [name + "=0" for name in DIRECT_OFF]
            if lean is not None:
                changes.append(f"ACTOR_SETUP_LEAN={lean}")
            variant = dict(shared)
            variant["command"] = [word.replace(str(seed), str(destination)) for word in shared["command"]] + changes
            profiles[name], row = helpers.expand(destination, compiler, sdk, overlay,
                variant, "actor", "platform/native_actor_fast.o", "platform/native_actor_fast.cpp")
            row.update(scope="Complete Make-derived Test22 public actor TU; no game link or hardware execution",
                       variant_overrides=changes, direct=direct, cone=cone,
                       compatibility_profile=not bool(direct))
            receipt[name] = row
    result = dict(scope=__doc__, profiles=receipt, pvr_header_overlay=overlay_receipt)
    (output / "actor-profile.json").write_text(json.dumps(result, indent=2) + "\n")
    return profiles, result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--sh4-cxx", required=True, type=Path)
    parser.add_argument("--kos-root", required=True, type=Path)
    parser.add_argument("--sdk-root", required=True, type=Path)
    args = parser.parse_args()
    profiles, _ = derive(args.output.resolve(), args.sh4_cxx.resolve(), args.kos_root.resolve(), args.sdk_root.resolve())
    print(json.dumps(dict(status="PASS", profiles=list(profiles))))


if __name__ == "__main__":
    main()
