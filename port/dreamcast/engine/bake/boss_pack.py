"""Bake a boss arena capture (eng-boss, E2) into a NAT3 format-4 pack the native bench draws.

Same pack as native_pack.py (whole-room world, materials, nine logic streams, the actor catalogue) with the boss
changes:
  - the catalogue is Leon + the five Ganado appearances (native_models.py) + the boss from the room's PS2 cast package
    (boss_model.py: dc/native/r<room>/registry.re4nmr, descriptor --boss, e.g. gigante-em2b-00 or the g50 level
    gig2b00-g50) + the room's other enemy-table models (the trees) from their source ModelData in the capture's RAM
    image (native_extra.py, as eng-e0b's props);
  - effect records the source game never draws are not baked: every haze (0x15) and mist sheet (0x48) sprite, the
    release recipe's HAZE_SPRITE_CUT rule (esp_sub.cpp; --keep-haze keeps them);
  - Leon in the room's costume (--leon pl08 from chapter 2: leon_costume.py, the PS2 pl08 package's roles 0, 1, 8);
  - world placements whose scroll (SMD) id the room script hides for the whole capture window are not baked
    (--hide-smd; El Gigante's arena: the destroyed hut and the unbroken / broken roof alternates);
  - the capture's role-3 records (the arena's non-Ganado enemy-table models: pose, caster, model light; index = the
    model's address, identity = id | type << 8) become role-2 records whose identity is the catalogue index; a model
    with no catalogue entry is dropped from the picture and counted.
"""
import argparse
import collections
import json
import struct
import zlib
from pathlib import Path
from native_models import models
from logic_delta import Changes
from native_world import whole_world
from native_extra import build_extra
from pack_scene import Baker, Table, block, pack
from boss_model import boss_model

BOSS_IDS = {0x2b: 'em2b'}      # El Gigante; the package descriptor is chosen with --boss


def hidden_world(directory, hidden_smd, out):
    """A copy of the room's world files without the placements of the hidden scroll (SMD) ids: the room script's
    show / hide state for the capture window (R4ID maps each placement row to its scroll id)."""
    import shutil, tempfile
    ids = (directory / "ps2-world.ids").read_bytes()
    if ids[:4] != b"R4ID": raise ValueError("no placement id table")
    n = struct.unpack_from("<I", ids, 8)[0]; table = ids[16:16 + n]
    side = (directory / "ps2-world.r4pw").read_bytes()
    head = list(struct.unpack_from("<7I", side, 4)); places, parts = head[1], head[2]
    keep = bytearray(); removed = []
    for i in range(places):
        rec = side[32 + 16 * parts + 52 * i:32 + 16 * parts + 52 * (i + 1)]
        row = struct.unpack_from("<HH", rec)[1]
        if row < n and table[row] in hidden_smd: removed.append((i, row, table[row])); continue
        keep += rec
    body = side[32:32 + 16 * parts] + bytes(keep)
    head[1] = places - len(removed); head[4] = zlib.crc32(body)
    tmp = Path(tempfile.mkdtemp(dir=out))
    for f in directory.iterdir():
        if f.is_file(): shutil.copyfile(f, tmp / f.name)
    (tmp / "ps2-world.r4pw").write_bytes(side[:4] + struct.pack("<7I", *head) + body)
    return tmp, removed


def build(disc, capture, room, tables, boss, extra_ids=(0x43,), report=None, haze_cut=True, hide_smd=(), tmp=Path("/tmp"),
          leon="pl00", rigid=None):
    assets = Baker(disc, capture, room)

    def world_material(key, phase, cull):
        return assets.header(key, (0, 2, 3)[phase], cull, world=True, fog=True)
    world_dir, removed = disc / f"native/r{room:x}", []
    if hide_smd:
        world_dir, removed = hidden_world(world_dir, set(hide_smd), tmp)
    world = whole_world(world_dir, world_material)
    if hide_smd:
        import shutil; shutil.rmtree(world_dir)
    actor_models = models(disc, tables, (capture / "leon-bind.bin").read_bytes(),
                          lambda key, phase: assets.header(key, phase, fog=True))
    leon_stats = {}
    if leon == "pl08":
        from leon_costume import leon_model
        actor_models[0], leon_stats = leon_model(disc, tables, (capture / "leon-bind.bin").read_bytes(),
                                                 lambda key, phase: assets.header(key, phase, fog=True),
                                                 (disc / "native/pl08/leon_pl08_ps2.re4cp").read_bytes())
    stats = {}
    package = (disc / f"native/r{room:x}/registry.re4nmr").read_bytes()
    actor_models.append(boss_model(package, boss, assets.lookup, lambda key, phase: assets.header(key, phase, fog=True), stats,
                                   rigid=rigid))
    boss_index = len(actor_models) - 1
    # role-3 models seen in the capture: identity -> model addresses
    seen = collections.defaultdict(set)
    for picture in range(1, 301):
        b = (capture / f"picture-{picture:03}.bin").read_bytes()
        offset = 16
        while offset < len(b):
            kind, size = struct.unpack_from("<2I", b, offset); offset += 8
            if kind == 2:
                role, index, identity, bone = struct.unpack_from("<4I", b, offset)
                if role == 3 and bone == 0:
                    seen[identity & 255].add(index)
            offset += size
    catalogue = {}      # model address -> catalogue index
    extra_report = {}
    for ident, addresses in sorted(seen.items()):
        if ident in BOSS_IDS:
            for addr in addresses:
                catalogue[addr] = boss_index
            continue
        if ident not in extra_ids:
            extra_report[hex(ident)] = 'not baked'
            continue
        built = {}
        for addr in sorted(addresses):
            try:
                raw = build_extra(assets, capture, [addr & 0xffffff])[0]
            except (ValueError, IndexError, KeyError) as e:
                extra_report[hex(ident)] = f'source model refused: {e}'
                break
            if raw not in built:
                actor_models.append(raw); built[raw] = len(actor_models) - 1
            catalogue[addr] = built[raw]
        else:
            extra_report[hex(ident)] = f'{len(addresses)} models, {len(built)} catalogue entries'
    samples = [Table() for _ in range(9)]
    missing = collections.Counter()
    dropped = collections.Counter()
    cut = collections.Counter()
    material_cache = {}

    def sprite_header(data, offset, phase):
        key = struct.unpack_from("<2I", data, offset)
        if key == (0, 0): return 0xffffffff
        tag = key, phase
        if tag not in material_cache:
            if key in assets.lookup:
                material_cache[tag] = assets.header(key, phase, fog=phase == 4)
            else:
                missing[tag] += 1
                material_cache[tag] = 0xffffffff
        return material_cache[tag]

    def effect_header(data, offset, pair):
        key = struct.unpack_from("<2I", data, offset)
        if key == (0, 0): return 0xffffffff
        tag = key, 4, pair
        if tag not in material_cache:
            if key in assets.lookup: material_cache[tag] = assets.header(key, 4, blend=pair, fog=True)
            else: missing[tag] += 1; material_cache[tag] = 0xffffffff
        return material_cache[tag]
    import numpy as np, dctex

    def masked_header(data, offset, phase):
        key = struct.unpack_from("<2I", data, offset); mask = struct.unpack_from("<2I", data, offset + 8)
        tag = key, mask, phase
        if tag not in material_cache:
            if mask not in assets.lookup:
                missing[tag] += 1; material_cache[tag] = sprite_header(data, offset, phase); return material_cache[tag]

            def img(k):
                off, size = assets.lookup[k]; return dctex.decode(assets.texpack[off:off + size])
            m = img(mask); t = img(key) if key in assets.lookup and key != (0, 0) else np.full_like(m, 255)
            if m.shape != t.shape:
                ys = (np.arange(t.shape[0]) * m.shape[0] // t.shape[0]); xs = (np.arange(t.shape[1]) * m.shape[1] // t.shape[1])
                m = m[ys][:, xs]
            out = t.copy(); out[..., 3] = (t[..., 3].astype(np.uint32) * m[..., 3] // 255).astype(np.uint8)
            pkg = dctex.encode_4444(out, b"hud-masked")
            ck = (zlib.crc32(pkg), 0x4b53414d)
            if ck not in assets.lookup:
                assets.lookup[ck] = (len(assets.texpack), len(pkg)); assets.texpack += pkg
            material_cache[tag] = assets.header(ck, phase, fog=False)
        return material_cache[tag]
    frames = []
    changes = [Changes() for _ in samples]
    previous = None
    ticks = []
    for picture in range(1, 301):
        path = capture / f"picture-{picture:03}.bin"
        b = path.read_bytes()
        magic, r, seq, tick = struct.unpack_from("<4s3I", b)
        if (magic, r, seq) != (b"LOG3", room, picture) or (previous is not None and tick != previous + 1):
            raise ValueError(f"logic discontinuity in {path}")
        previous = tick; ticks.append(tick)
        groups = collections.defaultdict(bytearray)
        offset = 16
        while offset < len(b):
            kind, size = struct.unpack_from("<2I", b, offset)
            offset += 8
            if kind not in range(1, 10) or offset + size > len(b):
                raise ValueError(f"invalid logic record in {path}")
            record = bytearray(b[offset:offset + size])
            offset += size
            if kind in (2, 5, 9) and struct.unpack_from("<I", record)[0] == 3:
                addr = struct.unpack_from("<I", record, 4)[0]
                if addr not in catalogue:
                    if kind == 2 and struct.unpack_from("<I", record, 12)[0] == 0:
                        dropped[hex(struct.unpack_from("<I", record, 8)[0] & 255)] += 1
                    continue
                struct.pack_into("<I", record, 0, 2)
                if kind == 2:
                    struct.pack_into("<I", record, 8, catalogue[addr])
            if kind == 4 and size == 152 and haze_cut and struct.unpack_from("<I", record, 4)[0] in (0x15, 0x48):
                cut[hex(struct.unpack_from("<I", record, 4)[0])] += 1
                continue
            if kind == 4 and size == 152:
                blend = struct.unpack_from("<I", record, 148)[0]
                bt, bs, bd = blend & 255, blend >> 8 & 255, blend >> 16 & 255
                pair = (bs & 7, bd & 7) if bt == 1 else (4, 5)
                struct.pack_into("<I", record, 128, effect_header(record, 128, pair))
            if kind == 7:
                if size != 60: raise ValueError("glyph source format")
                struct.pack_into("<I", record, 28, sprite_header(record, 28, 5))
            if kind == 6 and size == 96:
                masked = struct.unpack_from("<2I", record, 24) != (0, 0)
                hdr = masked_header(record, 16, 5) if masked else sprite_header(record, 16, 5)
                struct.pack_into("<I", record, 16, hdr)
                struct.pack_into("<2I", record, 24, int(masked), 0)
            groups[kind].extend(record)
        if len(groups[1]) != 104 or not groups[2] or not groups[6] or not groups[8]:
            raise ValueError(f"missing logic output in {path}: {[(k, len(v)) for k, v in groups.items()]}")
        frames.append(pack("10I", tick, *(table.add(changes[i].encode(groups[i + 1])) for i, table in enumerate(samples))))
    sections = [block(t.rows) for t in [assets.textures, assets.headers]]
    sections += [world, block(frames), *(block(t.rows) for t in samples)]
    sections.append(block(actor_models))
    sections.append(pack("2f", assets.top, assets.bottom))
    data = block(sections)
    if report is not None:
        report.update(room=hex(room), ticks=[ticks[0], ticks[-1]], leon=dict(costume=leon, **leon_stats), boss=stats, boss_index=boss_index,
                      catalogue_models=len(actor_models), extra=extra_report, dropped_pictures=dict(dropped), haze_cut=dict(cut), hidden_placements=[(i, r, hex(m)) for i, r, m in removed],
                      missing_textures=len(missing), texture_count=len(assets.textures.rows), resident_pack=len(data) + 20,
                      sections=list(map(len, sections)))
    return pack("4s4I", b"NAT3", 4, room, len(data), zlib.crc32(data)) + data


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("disc", type=Path)
    p.add_argument("capture", type=Path)
    p.add_argument("room", type=lambda s: int(s, 16))
    p.add_argument("out", type=Path)
    p.add_argument("tables", type=Path)
    p.add_argument("--boss", default="gigante-em2b-00", help="registry descriptor of the boss body (full or a level)")
    p.add_argument("--no-extra", action="store_true", help="bake no source props (the trees)")
    p.add_argument("--leon", default="pl00", choices=["pl00", "pl08"], help="Leon's costume (pl08: chapter 2, no jacket)")
    p.add_argument("--rigid", type=float, help="content step: skin rows with a weight >= this become one bone (others to 1/4)")
    p.add_argument("--hide-smd", default="", help="comma list of scroll (SMD) ids hidden in the capture window")
    p.add_argument("--keep-haze", action="store_true", help="keep the haze and mist sprites (ids 0x15, 0x48) the source never draws")
    a = p.parse_args()
    rep = {}
    a.out.write_bytes(build(a.disc, a.capture, a.room, a.tables, a.boss, () if a.no_extra else (0x43,), rep, not a.keep_haze,
                            [int(x, 0) for x in a.hide_smd.split(",") if x], leon=a.leon, rigid=a.rigid))
    print(json.dumps(rep))
