#!/usr/bin/env python3
"""Coverage and explicit encoding/mip policy for a receipt-bound texture pack.

Consumes the preserved descriptor census and named-resource source probe.
Their input file hashes must agree with the original release receipt. A source
reference proves ownership, not current runtime alias selection or a draw.
No asset conversion, disc staging, game build or runtime changes occur here.
"""
from __future__ import annotations

import argparse
import collections
import datetime
import json
from pathlib import Path
import struct
import sys

TOOLS = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(TOOLS / "d367"))
import compact_native_vq as compact
import convert_tpl as tpl
import texpack
from prepare_native_ui import material_pair_identity
from prepare_inventory_pairs import PAIRS as INVENTORY_PAIRS
from vram.vq_pak import read_pak
from world_candidate import sha

TYPED_SOURCE_OWNERS = {
    "effect", "character-enemy-npc", "character-player-partner", "weapon-model",
    "ui-interface-source", "ui-font-source", "ui-inventory-model-or-image", "world-source",
    "core-common-source",
}


def pair_references(normal,probe,inventory_pairs=None):
    """Exact runtime pair identity, without inventing a selected native binding."""
    targets={key for key,row in normal.items() if row.get('material')=='source-pair'}
    if not targets:
        return {}
    groups=collections.defaultdict(dict)
    matches=collections.defaultdict(list)
    seen=set()
    for key,refs in probe['references'].items():
        for r in refs:
            groups[(r['path'],r['tpl_offset'],r['width'],r['height'])][key]=r
    for group,keys in groups.items():
        for colour,cr in keys.items():
            for mask,mr in keys.items():
                if colour==mask:
                    continue
                pair=material_pair_identity(colour,mask)
                if pair in targets:
                    matches[pair].append(dict(method='same-TPL-equal-dimension-runtime-pair-identity',
                        colour=colour,mask=mask,colour_reference=cr,mask_reference=mr,
                        owner_categories=sorted({cr['owner_category'],mr['owner_category']})))
                    seen.add(pair)
    for pair in INVENTORY_PAIRS if inventory_pairs is None else inventory_pairs:
        key=material_pair_identity(pair['color'],pair['mask'])
        if key not in targets or key in seen:
            continue
        colour=probe['references'].get(pair['color'],[])
        mask=probe['references'].get(pair['mask'],[])
        for cr in colour:
            for mr in mask:
                if (cr['width'],cr['height'])!=(mr['width'],mr['height']):
                    continue
                matches[key].append(dict(method='explicit-source-selected-inventory-pair',
                    producer='port/dreamcast/tools/prepare_inventory_pairs.py:PAIRS',
                    colour=pair['color'],mask=pair['mask'],colour_reference=cr,mask_reference=mr,
                    owner_categories=['ui-inventory-model-or-image']))
    return dict(matches)


def validate_proofs(census, probe, receipt):
    for row in census["selected_files"] + probe["selected_files"]:
        expected = receipt.get(row["path"])
        if not expected or row["size"] != expected["size"] or row["sha256"] != expected["sha256"]:
            raise ValueError("preserved source receipt mismatch: " + row["path"])
    selected = {r["path"]: r for r in probe["selected_files"]}
    for refs in probe["references"].values():
        for ref in refs:
            file = selected.get(ref["path"])
            if (not file or ref["file_sha256"] != file["sha256"] or
                    ref["active_body_offset"] < 0 or ref["header_offset"] < 0 or
                    ref["active_body_offset"] + ref["header_offset"] + 36 > file["size"] or
                    ref["tpl_offset"] < 0 or ref["tpl_offset"] + 12 > file["active_bytes"]):
                raise ValueError("invalid named-resource proof range/hash")


def mip_policy(t, owners, native_world):
    if t[6] & tpl.FLAG_MIPMAP:
        return "preserve-existing-chain"
    if t[1] != t[2]:
        return "rectangular-domain-UV-wrap-edge-budget-contract-required"
    ui = {c for c in owners if c.startswith("ui-")}
    if ui:
        return "shared-UI-and-3D-sampling-review" if len(owners-ui) else "fixed-resolution-UI-or-glyph-source-no-automatic-mips"
    if native_world:
        return "square-world-data-candidate-target-budget-look-gates-pending"
    if "effect" in owners:
        return "sprite-scale-covered-UV-and-alpha-review-before-selective-mips"
    if 'core-common-source' in owners:
        return 'shared-core-resource-no-automatic-mips-before-consumer-sampling-proof'
    if owners & {"character-enemy-npc", "character-player-partner", "native-model-registry", "weapon-model", "known-ganado-atlas"}:
        return "actor-material-atlas-sampling-and-budget-review-preserve-SH4ZAM"
    if "world-source" in owners:
        return "source-world-reference-not-proof-of-native-world-selection"
    return "owner-and-sampling-policy-open"


def coverage(pack, census, probe, receipt):
    if probe.get("schema") != "re4dc-source-owner-probe-1":
        raise ValueError("unsupported source-owner probe")
    validate_proofs(census, probe, receipt)
    if sha(pack) != receipt["dc/tex.pak"]["sha256"] or len(pack) != receipt["dc/tex.pak"]["size"]:
        raise ValueError("pack differs from release receipt")
    if probe["source_pack_sha256"] != sha(pack):
        raise ValueError("source probe describes another texture pack")
    texpack.verify(pack)
    packages = read_pak(pack)
    normal = {r["key"]: r for r in census["textures"] if r["container"].startswith("dc/tex.pak:")}
    if set(normal) != {"%08x-%08x" % k for k in packages}:
        raise ValueError("descriptor census does not cover exactly the packed winners")
    worlds, registries = census.get("world_keys", {}), census.get("registry_keys", {})
    pairs=pair_references(normal,probe)
    ganado = {r["key"] for r in census.get("proven_ganado_atlases", [])}
    rows, selection, owners_count, plans_count = [], [], collections.Counter(), collections.Counter()
    for key, blob in sorted(packages.items()):
        name = "%08x-%08x" % key
        old = normal[name]
        t = tpl.TEXTURE.unpack_from(blob, 48)
        if (t[1],t[2],t[3],t[5],t[6],t[7]) != (old["width"],old["height"],old["format"],old["payload_bytes"],old["flags"],old["payload"]):
            raise ValueError("descriptor census disagrees with actual packed winner: " + name)
        refs = probe["references"].get(name, [])
        owners = {r["owner_category"] for r in refs}
        core=any(r['path']=='etc/core.das' for r in refs)
        if core:
            owners.add('core-common-source')
        pair_refs=pairs.get(name,[])
        owners.update(c for r in pair_refs for c in r['owner_categories'])
        native_world = name in worlds
        if native_world:
            owners.add("native-world")
        if name in registries:
            owners.add("native-model-registry")
        if name in ganado:
            owners.add("known-ganado-atlas")
        typed = bool(owners & (TYPED_SOURCE_OWNERS | {"native-world", "native-model-registry", "known-ganado-atlas"}))
        proof = []
        if refs:
            proof.append(dict(kind="named-source-reference-not-runtime-draw", references=refs))
        if core:
            proof.append(dict(kind='source-core-common-resource-binding',
                resource='etc/core.das',file_table='src/game/dvd.cpp',
                binding='src/game/read.cpp:re4dc_ui_bind_core',
                adapter='port/dreamcast/game/platform/native_ui.cpp:core_identities',
                scope='Common archive source ownership; no individual consumer or draw claim.'))
        if pair_refs:
            proof.append(dict(kind='runtime-source-colour-mask-pair-identity-not-native-draw',references=pair_refs))
        if native_world:
            proof.append(dict(kind="selected-native-world-sidecar-reference", references=worlds[name]))
        if name in registries:
            proof.append(dict(kind="selected-native-model-registry-reference", references=registries[name]))
        if name in ganado:
            proof.append(dict(kind="previously-proven-Ganado-atlas", key=name))
        plan = dict(reason="rectangular-domain-contract-required")
        if t[1] == t[2]:
            try:
                _, plan = compact.compact(blob, enabled=False)
            except ValueError as error:
                plan = dict(reason="native-family-refused", detail=str(error))
        lossless = plan["reason"] == "disabled"
        selected = lossless and typed
        if selected:
            selection.append(dict(key=name, package_sha256=sha(blob), owner_evidence=proof))
        owners_count.update(owners or ["unclassified"])
        plans_count[plan["reason"]] += 1
        rows.append(dict(key=name, package_sha256=sha(blob), material=t[0].split(b"\0")[0].decode("utf8", "replace"),
            width=t[1],height=t[2],native_format=t[3],flags=t[6],layout=t[7],
            payload_bytes=t[5],alloc32_bytes=compact.rounded32(t[5]),
            owner_categories=sorted(owners), typed_owner_reference=typed,
            source_references=refs,derived_pair_references=pair_refs,native_world_references=worlds.get(name,[]),
            native_registry_references=registries.get(name,[]),
            encoding_plan=plan, lossless_vq_candidate=lossless,
            source_owned_lossless_vq_selection=selected,
            mip_policy=mip_policy(t,owners,native_world),
            original_mipmapped=bool(t[6]&tpl.FLAG_MIPMAP),
            evidence_scope="Source/native references and stored-format feasibility; not proof of runtime alias selection/draw or live residency."))
    loose = [dict(r, winner_scope="normal-pack-wins" if r["key"] in normal else
        "conditional-standard-quality-texlow" if "texlow" in r["container"] else "loose-fallback-only",
        mip_policy="assess-selected-quality-owner-and-sampler-separately")
        for r in census["textures"] if not r["container"].startswith("dc/tex.pak:")]
    report = dict(schema="re4dc-whole-pack-source-coverage-1", source_pack_sha256=sha(pack),
        normal_packed_winners=len(rows), stored_loose_descriptors=len(loose),
        source_pair_reference_keys=len(pairs),
        normal_rows=rows, loose_and_quality_rows=loose,
        owner_category_counts=dict(owners_count), encoding_plan_counts=dict(plans_count),
        keys_with_any_owner_reference=sum(bool(r["owner_categories"]) for r in rows),
        typed_owner_keys=sum(r["typed_owner_reference"] for r in rows),
        owner_unclassified_keys=sum(not r["owner_categories"] for r in rows),
        lossless_vq_format_opportunities=sum(r["lossless_vq_candidate"] for r in rows),
        source_owned_lossless_vq_keys=len(selection),
        source_owned_lossless_vq_saved_payload_bytes=sum(r["encoding_plan"]["before_payload_bytes"]-r["encoding_plan"]["candidate_payload_bytes"] for r in rows if r["source_owned_lossless_vq_selection"]),
        owner_category_count_caution="Categories overlap and are not additive; template references may be redirected, unused or conditional.",
        fixed_UI_policy="Preserve fixed-resolution UI/text and glyph-sheet sampling; exact base-only encoding may shrink bytes without adding mips.",
        runtime_generated_exclusions=["Glyph-cache tiles, BIOS diagnostics/HUD labels and other runtime-generated textures are not normal packed winners."],
        limits=["The preserved probe verified named source file SHA/size and active-body references, not SourceIdentityTable admission/draw.",
            "The source track is no longer present; pack recovery is separately hash-bound.",
            "No blanket resampling, lossy quantization, palette expansion, mip generation or asset conversion here.",
            "No actual VRAM peaks, sampler look, game test, frame timing or console acceptance."])
    selected = dict(schema="re4dc-lossless-vq-selection-1", source_pack_sha256=sha(pack),
        scope="Source-owned base-only exact native VQ; dimensions/UVs/alpha retained; no automatic mip levels.", keys=selection)
    return report, selected


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source-pack",type=Path,required=True)
    ap.add_argument("--release-manifest",type=Path,required=True)
    ap.add_argument("--census",type=Path,required=True)
    ap.add_argument("--owner-probe",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    args=ap.parse_args(argv)
    if args.output.exists() or not args.output.parent.is_dir():
        ap.error("output must be a new private directory")
    manifest=args.release_manifest.read_bytes()
    census_bytes,probe_bytes=args.census.read_bytes(),args.owner_probe.read_bytes()
    census,probe=json.loads(census_bytes),json.loads(probe_bytes)
    if census["manifest_sha256"]!=sha(manifest) or probe["input_manifest_sha256"]!=sha(manifest):
        raise ValueError("preserved source evidence describes another release receipt")
    report,selection=coverage(args.source_pack.read_bytes(),census,probe,json.loads(manifest))
    report.update(updated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        release_manifest_sha256=sha(manifest),census_sha256=sha(census_bytes),
        owner_probe_sha256=sha(probe_bytes),source_pack_path=str(args.source_pack),
        tool_sha256=sha(Path(__file__).read_bytes()))
    args.output.mkdir()
    for name,value in (("coverage.json",report),("lossless-vq-selection.json",selection)):
        (args.output/name).write_text(json.dumps(value,indent=2)+"\n")
    (args.output/"SHA256SUMS").write_text("".join("%s  %s\n"%(sha(p.read_bytes()),p.name)
        for p in sorted(args.output.iterdir())),encoding="ascii")
    print(json.dumps({k:report[k] for k in ("normal_packed_winners","typed_owner_keys",
        "owner_unclassified_keys","lossless_vq_format_opportunities","source_owned_lossless_vq_keys",
        "source_owned_lossless_vq_saved_payload_bytes")},sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
