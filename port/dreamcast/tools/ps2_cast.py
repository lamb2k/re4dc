#!/usr/bin/env python3
"""PS2 character converter (lane ps2cast): a PS2 RE4 character appearance (the em archive's model BINs and
TPL on the PS2 disc) -> the external cast's pack layout that tools/cast_bundle.py (the cl lane's bundle
maker) and coarse_ganado_cast.cpp consume. No runtime code changes; derived assets are private.

The game keeps the GameCube skeleton and motions, so the PS2 mesh is bound to the GC skeleton exactly: every
section's PS2 bone table must equal the GC BIN's (bone id == GC part attach id, parent, rest translation
within --bone-tol mm); PS2 weight bone ids are then GC part indices (identity map, checked per bone). The
appearance's signatures stay the GC source infos' (the runtime identifies the game's loaded GC model by them
and draws the converted mesh in its place).

Stage 1, `convert` (Windows Python: numpy, PIL):
  inputs/        emXX.dat from the PS2 disc (ISO9660 -> BIO4DAT.AFS) and emXX.drs from the GC debug disc,
                 sha256-recorded
  source.json    GC skeleton (rest = capture = accumulated part translations) + GC section infos
  mesh.json      re4dc-approved-render-mesh-1 (the cast's Blender exchange schema): PS2 positions (mm),
                 PS2 weights on GC bone indices, per corner PS2 normal and atlas UV, section = source info
  atlas.png      the appearance TPL's images (PS2 4/8-bit CLUT, GS-unswizzled by ps2_tpl_decode.py, the
                 decoder validated pixel-exact against JADERLINK) in 256 x 256 cells of one power-of-two atlas
  native/        character-prototype pack_coarse_actor.pack() output (GX triangle lists, arrays, report)
                 + host-fixture.bin for the cast agent's host check
  source-bindings.json, manifest.json (cast layout; levels filled by stage 2)
  validation.json skeleton / weights / winding / normals / rest and posed surface distance to the GC mesh
Stage 2, `native` (WSL; ps2_cast_native.sh): host check (check-dynamic, the unchanged native_actor_fast.cpp
converter), fastpath build_blob.py (strips) + verify_blob.py + patch_header.py -> runtime header; pvrtex VQ
+ vq_export.py --pack-existing -> <key>.re4tex. Stage 3, `castdir`: assembles a cast dir for cast_bundle.py.

usage:
  ps2_cast.py convert <preset> <out dir> [--ps2-iso P] [--gc-iso G] [--poses pose-samples.json]
  ps2_cast.py finish <out dir>              (after stage 2: fills manifest levels from fit-report / header)
  ps2_cast.py castdir <cast dir> <out dir>...   (writes/extends a cast dir for cast_bundle.py)
  ps2_cast.py list                          (presets)
Env: RE4_CAST_PROTO (character-prototype-20260925, pack_coarse_actor.py), RE4_WORLD_AGENT (ps2_tpl_decode.py).
"""
import argparse, hashlib, importlib.util, json, math, os, re, shutil, struct, sys, zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path[:0] = [str(HERE), str(REPO / 'tools')]
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402
import ps2_bin as pb  # noqa: E402
import convert_character as cc  # noqa: E402
import drs  # noqa: E402
from motion import modelbin  # noqa: E402

PRIV = Path(os.environ.get('RE4_PRIVATE', 'C:/Game Dev/Emulators/re4-assets-private'))
PROTO = Path(os.environ.get('RE4_CAST_PROTO', PRIV / 'character-prototype-20260925'))
WA = Path(os.environ.get('RE4_WORLD_AGENT', PRIV / 'world-agent-20260926'))
PS2_ISO = 'C:/Game Dev/Emulators/re4_helpers/Resident Evil 4 (USA)/Resident Evil 4 (USA).iso'
GC_ISO = 'C:/Game Dev/Emulators/Resident Evil 4 Debug (Disc 1)/Resident Evil 4 Debug (Disc 1).iso'
ROLES = ['body', 'head', 'right-hand', 'left-hand']
CELL = 256


def _ganado(archive, base, rooms, types, hands=(0x1c0, 0x1c5)):
    return dict(archive=archive, sections=[(base, 'body'), (base + 2, 'head'), (hands[0], 'right-hand'), (hands[1], 'left-hand')],
                tpl=base + 1, rooms=rooms, types=types, category='human')


def _soldier(archive, body, head, rooms, types):
    """Stage-3 soldier (em10.cpp class 2; src/<em>/<em>_set.cpp): body BIN mot[1] / TPL mot[0] (0x22F / 0x230 or
    0x247 / 0x248), head BIN mot[2] / TPL mot[5] (0x231 / 0x232, 0x249 / 0x24A, 0x24B / 0x24C, 0x24D / 0x24E),
    relaxed hands (em10HandSet type 0) BIN mot[6] 0x234 and mot[11] 0x238 with TPL mot[0]."""
    return dict(archive=archive, sections=[(body, 'body'), (head, 'head'), (0x234, 'right-hand'), (0x238, 'left-hand')],
                tpl=body + 1, section_tpls={head: head + 1}, rooms=rooms, types=types, category='registry',
                model_id=int(archive[2:], 16), lit=True, subset_bones=True)


def _soldier_pool(archive, body, rooms, types, heads=(0x231, 0x249, 0x24b, 0x24d), skip=(), no_stump=(0x24d,)):
    """NATIVE_MODEL_REGISTRY_POOL (lane ps2cast 2026-10-15): a stage-3 soldier body's whole section pool, so every
    spawn of the body binds whatever head, hit head, hand pose and accessory it shows. One pool per body BIN (mot[1]
    0x22F / TPL mot[0] 0x230, or 0x247 / 0x248): every em10HeadSet head mot[2] with its TPL mot[5] (0x231 / 0x232,
    0x249 / 0x24A, 0x24B / 0x24C, 0x24D / 0x24E) and the hit head mot[3] 0x233 under each of those TPLs; em10HandSet
    right mot[6..9] 0x234..0x237 and left mot[11..15] 0x238..0x23C, TPL mot[0]; em10SetAccesory (em10.cpp case
    0xE..0x18) 0x24F / 0x250 (flag 0x200), 0x243 / 0x244 (0x100), 0x245 / mot[0] (flag 2), hoods 0x23D / 0x23E
    (0x40000), 0x23F / 0x240 (0x4000), 0x241 / 0x242 (0x1000). Caps (0x262 / 0x265) are separate Obj12 objects.
    `heads`: only the heads the archive's Set table pairs with this body (em1e / em1f heads carry a body-specific
    bone 31; the converter refuses a head on a body it is never set on). `skip`: accessory BINs whose GC skeleton
    does not fit this body (em1f's hood 0x23D is a 37-part section; em1f body 0x247 has 34 bones), or whose PS2
    materials index past the body TPL (em1e 0x245 / mot[0] under TPL 0x248: image 2 of 2)."""
    tpl = body + 1
    heads = [(h, n) for h, n in [(0x231, 'head-a'), (0x249, 'head-b'), (0x24b, 'head-c'), (0x24d, 'head-d')] if h in heads]
    sections = [(body, 'body')]
    sections += [(h, n, h + 1) for h, n in heads]
    # `no_stump`: heads whose stump 0x233 is left out: its GC material names image 1 of that head's one-image GC TPL
    # (em1d / em1f 0x24E, em1e 0x24A), so the source certificate refuses the info (Error::Material) and no role row
    # can prove it (the PS2 TPLs have two images)
    sections += [(0x233, 'hit-' + n[5:], h + 1) for h, n in heads if h not in no_stump]
    sections += [(0x234, 'right-hand', tpl), (0x235, 'right-open', tpl), (0x236, 'right-point', tpl), (0x237, 'right-grip', tpl),
                 (0x238, 'left-hand', tpl), (0x239, 'left-open', tpl), (0x23a, 'left-point', tpl), (0x23b, 'left-grip', tpl),
                 (0x23c, 'left-grip2', tpl)]
    sections += [(0x24f, 'acc-mask', 0x250), (0x243, 'acc-vest', 0x244), (0x245, 'acc-pack', tpl)]
    sections += [(0x23d, 'hood-a', 0x23e), (0x23f, 'hood-b', 0x240), (0x241, 'hood-c', 0x242)]
    sections = [x for x in sections if x[0] not in skip]
    return dict(archive=archive, sections=sections, tpl=tpl, rooms=rooms, types=types, category='registry',
                model_id=int(archive[2:], 16), lit=True, subset_bones=True, body_bone_extras=True)


# arc numbers (PL_ARC = entry index + 4), from the source's Em15Set / Em12Set tables (cast recover_cast.py)
PRESETS = {
    'ganado-em15-00': _ganado('em15', 0x1bc, ['r101'], [0x00]),
    'ganado-em15-0b': _ganado('em15', 0x1c9, ['r101'], [0x0b]),
    'ganado-em15-03': _ganado('em15', 0x1dc, ['r101'], [0x03]),
    'ganado-em15-04': _ganado('em15', 0x1e0, ['r101'], [0x04]),
    'ganado-em12-01': dict(archive='em12', sections=[(0x1d8, 'body'), (0x1da, 'head'), (0x1c0, 'right-hand'), (0x1c5, 'left-hand')],
                           tpl=0x1d9, rooms=['r100', 'r103'], types=[1], category='human'),
    # not in the external cast (ps2_cast_inventory.py): Em17Set / Em16Set type 0xc, Em13Set type 6 (own hands)
    # model_id: the registry descriptor's enemy id (regcast; lane ps2cast-2 draws em17 type 0xc through a registry pack)
    'ganado-em17-0c': dict(_ganado('em17', 0x1cd, ['r108', 'r118', 'r111', 'r113', 'r11d'], [0x0c]), model_id=0x17),
    'ganado-em13-06': dict(archive='em13', sections=[(0x1e7, 'body'), (0x1e9, 'head'), (0x1f4, 'right-hand'), (0x1f8, 'left-hand')],
                           tpl=0x1e8, rooms=['r104', 'r11c', 'r10f'], types=[6], category='human'),
    # em10HeadSet's type-3 lost-head source variant. Keep all four source roles
    # while converting so its PS2 image0 uses exactly the normal app2 atlas.
    'ganado-em13-03-stump': dict(archive='em13',
        sections=[(476, 'body'), (479, 'head'), (448, 'right-hand'), (453, 'left-hand')],
        tpl=477, rooms=['r11c'], types=[3], category='human'),
    # non-Ganado models for NATIVE_MODEL_REGISTRY packs (ps2_cast.py regcast; lane ps2cast-all): src/em2b em2b.cpp
    # type 0 (TYPE_A) modelInit(ARC 5, ARC 7) + ModInfoMgr.create(ARC 6, ARC 7): body + head, one 64-bone skeleton
    'gigante-em2b-00': dict(archive='em2b', sections=[(5, 'body'), (6, 'head')], tpl=7, rooms=['r119'], types=[0],
                            category='boss', model_id=0x2b, shift=2),
    # src/em2f em2f.cpp type 0 (the r10b Del Lago fight): modelInit(ARC 4, ARC 5); type 1 (ARC 6 / 7) is the same
    # model on GC and PS2 (no geometry change), so only type 0 converts (lane ps2cast-2)
    'dellago-em2f-00': dict(archive='em2f', sections=[(4, 'body')], tpl=5, rooms=['r10b'], types=[0],
                            category='boss', model_id=0x2f, shift=2),
    # lane ps2cast-4 (PS2_ANIMALS): the stage-1 animals, the cast's registry descriptors (stage1-animals.json) re-pointed
    # at the PS2 meshes. Same BIN / TPL arcs as the cast's source-bindings (type 0 TPL ARC 5, type 1 ARC 6; the crow's
    # body BIN 5 + wing BIN 6 (folded) or 7 (spread), TPL 8: em23SetWing). The crow's PS2 wing BINs carry reduced bone
    # tables (subset_bones).
    'dog-00': dict(archive='em21', sections=[(4, 'body')], tpl=5, rooms=['r103', 'r119'], types=[0], category='animal', model_id=0x21),
    'dog-01': dict(archive='em21', sections=[(4, 'body')], tpl=6, rooms=['r100', 'r103'], types=[1], category='animal', model_id=0x21),
    'cow-00': dict(archive='em26', sections=[(4, 'body')], tpl=5, rooms=['r101', 'r103'], types=[0], category='animal', model_id=0x26),
    'cow-01': dict(archive='em26', sections=[(4, 'body')], tpl=6, rooms=['r103'], types=[1], category='animal', model_id=0x26),
    'chicken-00': dict(archive='em28', sections=[(4, 'body')], tpl=5, rooms=['r101', 'r103'], types=[0], category='animal', model_id=0x28),
    'chicken-01': dict(archive='em28', sections=[(4, 'body')], tpl=6, rooms=['r101', 'r103'], types=[1], category='animal', model_id=0x28),
    'crow-folded': dict(archive='em23', sections=[(5, 'body'), (6, 'folded-wings')], tpl=8, rooms=['r100', 'r105', 'r108', 'r109'],
                        types=[], category='animal', model_id=0x23, subset_bones=True),
    'crow-spread': dict(archive='em23', sections=[(5, 'body'), (7, 'spread-wings')], tpl=8, rooms=['r100', 'r105', 'r108', 'r109'],
                        types=[], category='animal', model_id=0x23, subset_bones=True),
    # lane ps2cast-4 (PS2_WOLF): the parasite dog (Colmillos) em22, src/em22 em22_R0_Init modelInit(ARC 4, ARC 5): one
    # 42-bone body BIN (the back parasites are cObj16 objects, ARC 0x39 / 0x47, not part of this model)
    'wolf-em22-00': dict(archive='em22', sections=[(4, 'body')], tpl=5, rooms=['r11b', 'r118'], types=[0], category='animal', model_id=0x22, lit=True),
    # CH23: exact source info selections (em10ModelInit / Em13Set / em10_R1_Trade).
    # The 61-bone merchant uses three TPLs and seven infos, including the hidden
    # goods info. Open/closed coat changes the cloth BIN; both retain base hands.
    'merchant13-c0': dict(archive='em13', sections=[(0x1e7, 'body'), (0x1f0, 'robe'), (0x1ee, 'cloth'),
                            (0x1ef, 'goods'), (0x1e9, 'head'), (0x1f4, 'right-hand'), (0x1f8, 'left-hand')],
                         tpl=0x1e8, section_tpls={0x1f0: 0x1f1, 0x1ee: 0x1f1, 0x1e9: 0x1ea},
                         rooms=['r10f'], types=[6], category='registry', model_id=0x13, lit=True),
    'merchant13-o0': dict(archive='em13', sections=[(0x1e7, 'body'), (0x1f0, 'robe'), (0x1ed, 'cloth'),
                            (0x1ef, 'goods'), (0x1e9, 'head'), (0x1f4, 'right-hand'), (0x1f8, 'left-hand')],
                         tpl=0x1e8, section_tpls={0x1f0: 0x1f1, 0x1ed: 0x1f1, 0x1e9: 0x1ea},
                         rooms=['r10f'], types=[6], category='registry', model_id=0x13, lit=True),
    # Standalone merchant em18 uses a different archive and source info order.
    # em18_R0_Init appends robe, head, both hands, cloth, then hidden goods.
    # lane ps2cast 2026-10-14: Ashley (pl11, r117 ...). Converted by ps2_ashley.py (141 GC joints, draw slots, PS2 cloth
    # weights moved onto the GC cloth links); this entry only carries the finish / regcast metadata.
    'ashley11': dict(archive='pl11', sections=[(4, 'body'), (7, 'head'), (6, 'hair'), (9, 'extra9'), (0xA, 'extraA'),
                                               (0xC, 'right-hand'), (0xF, 'left-hand')],
                     tpl=5, section_tpls={7: 0xB, 6: 8}, rooms=['r117'], types=[], category='registry', model_id=3,
                     converter='ps2_ashley.py'),
    'ashley11-h1': dict(archive='pl11', sections=[(4, 'body'), (7, 'head'), (6, 'hair'), (9, 'extra9'), (0xA, 'extraA'),
                                                  (0xD, 'right-hand'), (0x10, 'left-hand')],
                        tpl=5, section_tpls={7: 0xB, 6: 8}, rooms=['r117'], types=[], category='registry', model_id=3,
                        converter='ps2_ashley.py --hands 1'),
    'ashley11-h3': dict(archive='pl11', sections=[(4, 'body'), (7, 'head'), (6, 'hair'), (9, 'extra9'), (0xA, 'extraA'),
                                                  (0xE, 'right-hand'), (0xF, 'left-hand')],
                        tpl=5, section_tpls={7: 0xB, 6: 8}, rooms=['r117'], types=[], category='registry', model_id=3,
                        converter='ps2_ashley.py --hands 3'),
    'merchant18-c0': dict(archive='em18', sections=[(5, 'body'), (14, 'robe'), (7, 'head'),
                            (18, 'right-hand'), (19, 'left-hand'), (12, 'cloth'), (13, 'goods')],
                         tpl=6, section_tpls={14: 15, 7: 8, 12: 15},
                         rooms=['r10d', 'r112'], types=[], category='registry', model_id=0x18, lit=True),
    'merchant18-o0': dict(archive='em18', sections=[(5, 'body'), (14, 'robe'), (7, 'head'),
                            (18, 'right-hand'), (19, 'left-hand'), (11, 'cloth'), (13, 'goods')],
                         tpl=6, section_tpls={14: 15, 7: 8, 11: 15},
                         rooms=['r10d', 'r112'], types=[], category='registry', model_id=0x18, lit=True),
    # em3b_R0_Init: cart type 2 (r11d) and truck type 0 (r200).
    'cart-em3b-02': dict(archive='em3b', sections=[(0xb, 'body')], tpl=0xc, rooms=['r11d'], types=[2],
                         category='registry', model_id=0x3b, lit=True, repeat_uvs=True),
    'truck-em3b-00': dict(archive='em3b', sections=[(4, 'body')], tpl=5, rooms=['r200'], types=[0],
                          category='registry', model_id=0x3b, lit=True, shift=3),
    # em35_R0_Init: whole body + extra, divided upper body, and separated legs.
    # All use the original GC skeleton/animation; the PS2 bone tables match it.
    'mendez35-full': dict(archive='em35', sections=[(4, 'body'), (6, 'extra')], tpl=5, rooms=['r11f'], types=[0],
                          category='boss', model_id=0x35, shift=2, lit=True),
    'mendez35-upper': dict(archive='em35', sections=[(7, 'body')], tpl=5, rooms=['r11f'], types=[1],
                           category='boss', model_id=0x35, shift=2, lit=True),
    'mendez35-legs': dict(archive='em35', sections=[(8, 'body')], tpl=5, rooms=['r11f'], types=[2],
                          category='boss', model_id=0x35, lit=True),
    # stage-3 soldiers (lane ps2cast-st3, 2026-10-15): one descriptor per Em1dSet / Em1eSet / Em1fSet (body, head) pair
    # em1d type 2 (the gatling gunner): modelInit(mot[1] 0x22B, mot[0] 0x22C); em10 skips its head and hands
    'soldier-em1d-02': dict(archive='em1d', sections=[(0x22b, 'body')], tpl=0x22c, rooms=['r300', 'r320', 'r327'], types=[2], category='registry',
                            model_id=0x1d, lit=True),
    'soldier-em1d-0e': _soldier('em1d', 0x22f, 0x231, ['r300', 'r320', 'r327'], [14]),
    'soldier-em1d-12': _soldier('em1d', 0x247, 0x231, ['r320', 'r327'], [18]),
    'soldier-em1d-0f': _soldier('em1d', 0x22f, 0x249, ['r300', 'r320', 'r327'], [15]),
    'soldier-em1d-13': _soldier('em1d', 0x247, 0x249, ['r320', 'r327'], [19]),
    'soldier-em1d-10': _soldier('em1d', 0x22f, 0x24b, ['r300', 'r320', 'r327'], [16]),
    'soldier-em1d-14': _soldier('em1d', 0x247, 0x24b, ['r320', 'r327'], [20]),
    'soldier-em1d-11': _soldier('em1d', 0x22f, 0x24d, ['r300', 'r320', 'r327'], [17]),
    'soldier-em1d-15': _soldier('em1d', 0x247, 0x24d, ['r320', 'r327'], [21]),
    'soldier-em1e-0e': _soldier('em1e', 0x22f, 0x231, ['r301', 'r305', 'r30e', 'r316', 'r31d'], [14]),
    'soldier-em1e-0f': _soldier('em1e', 0x22f, 0x249, ['r301', 'r30e', 'r316', 'r31d'], [15]),
    'soldier-em1e-17': _soldier('em1e', 0x247, 0x24d, ['r301', 'r305', 'r30e', 'r316'], [23]),
    'soldier-em1e-19': _soldier('em1e', 0x247, 0x24b, ['r301', 'r303', 'r305', 'r30e', 'r316'], [25]),
    'soldier-em1f-0e': _soldier('em1f', 0x22f, 0x231, ['r304', 'r30b', 'r30c', 'r30f', 'r311', 'r321', 'r334'], [14]),
    'soldier-em1f-0f': _soldier('em1f', 0x22f, 0x249, ['r304', 'r30b', 'r30c', 'r30f', 'r311', 'r321', 'r330', 'r334'], [15]),
    'soldier-em1f-10': _soldier('em1f', 0x22f, 0x24b, ['r304', 'r30b', 'r30c', 'r30f', 'r311', 'r321', 'r330', 'r334'], [16]),
    'soldier-em1f-18': _soldier('em1f', 0x247, 0x24d, ['r304', 'r30c', 'r311', 'r330'], [24]),
    # NATIVE_MODEL_REGISTRY_POOL: one pool per (archive, body BIN); rooms / types from the stage-3 enemy lists
    'soldier-em1d-ap': _soldier_pool('em1d', 0x22f, ['r300', 'r320', 'r327'], [14, 15, 16, 17]),
    'soldier-em1d-bp': _soldier_pool('em1d', 0x247, ['r320', 'r327'], [18, 19, 20, 21]),
    'soldier-em1e-ap': _soldier_pool('em1e', 0x22f, ['r301', 'r305', 'r30e', 'r316', 'r31d'], [14, 15], (0x231, 0x249), no_stump=(0x249,)),
    'soldier-em1e-bp': _soldier_pool('em1e', 0x247, ['r301', 'r303', 'r305', 'r30e', 'r316'], [23, 25], (0x24b, 0x24d), skip=(0x245,), no_stump=()),
    'soldier-em1f-ap': _soldier_pool('em1f', 0x22f, ['r304', 'r30b', 'r30c', 'r30f', 'r311', 'r321', 'r330', 'r334'], [14, 15, 16], (0x231, 0x249, 0x24b)),
    'soldier-em1f-bp': _soldier_pool('em1f', 0x247, ['r304', 'r30c', 'r311', 'r330'], [24], (0x24d,), skip=(0x23d,)),
    # lane ps2cast2 (2026-10-14): the chapter-1 non-Ganado actors still drawn from the GC source (CH1 audit fix 5).
    # Each is one modelInit(BIN, TPL) of its module's R0 init; lit (normals kept) like the source path draws them.
    # em2a_R0_Init: type 0 bear trap modelInit(ARC 4, ARC 5), type 1 (6, 7), type 2 (8, 9) (types 1 / 2 scale
    # parts 1 / 2 pos.z by hp at init: the wire / bomb models)
    'trap-em2a-00': dict(archive='em2a', sections=[(4, 'body')], tpl=5, rooms=['r100', 'r105', 'r106', 'r107', 'r10a'],
                         types=[0], category='registry', model_id=0x2a, lit=True),
    'trap-em2a-02': dict(archive='em2a', sections=[(8, 'body')], tpl=9, rooms=['r100', 'r105', 'r106', 'r107', 'r10a'],
                         types=[2], category='registry', model_id=0x2a, lit=True, shift=2),   # 4.2 m long: GC shift 2
    # em29_R0_Init: the bat, modelInit(ARC 4, ARC 5); 7 PS2 corners sit one texel past a GX_REPEAT image edge
    'bat-em29-00': dict(archive='em29', sections=[(4, 'body')], tpl=5, rooms=['r106', 'r10e'], types=[],
                        category='registry', model_id=0x29, lit=True, uv_edge_texels=1),
    # em2e_R0_Init: the wall crawler, type 0 modelInit(ARC 4, ARC 5), type 1 (ARC 4, ARC 6)
    'crawler-em2e-00': dict(archive='em2e', sections=[(4, 'body')], tpl=5, rooms=['r106'], types=[0],
                            category='registry', model_id=0x2e, lit=True),
    'crawler-em2e-01': dict(archive='em2e', sections=[(4, 'body')], tpl=6, rooms=['r106'], types=[1],
                            category='registry', model_id=0x2e, lit=True),
    # em27_R0_Init: the lake fish, modelInit(ARC 4, ARC 5) for every type (type 1 only scales x3)
    'fish-em27-00': dict(archive='em27', sections=[(4, 'body')], tpl=5, rooms=['r107', 'r10b', 'r11b', 'r10e'], types=[0, 1],
                         category='registry', model_id=0x27, lit=True),
    # em24_R0_Init: the snake, modelInit(ARC 5, ARC 6) (ARC 0x19 + 0x1A..0x1C are the dropped item models, SetWeapon)
    'snake-em24-00': dict(archive='em24', sections=[(5, 'body')], tpl=6, rooms=['r10a', 'r108', 'r11a'], types=[],
                          category='registry', model_id=0x24, lit=True),
    # pl0f_R0_Init: the boat, modelInit(ARC 5, ARC 6) for every type / set
    'boat-pl0f-00': dict(archive='pl0f', sections=[(5, 'body')], tpl=6, rooms=['r10b', 'r11b', 'r10e'], types=[],
                         category='registry', model_id=0x0f, lit=True, shift=3),   # 2.7 m: positions beyond +-2048 mm
    # Em11Set type 7 + em10ModelInit: body BIN mot[1] 0x1FC / TPL mot[0] 0x1FD, head (em10HeadSet) BIN mot[2] 0x1FE /
    # TPL mot[5] 0x201, relaxed hands (em10HandSet type 0) BIN mot[6] 0x204 and mot[11] 0x208, both with TPL mot[0]
    'zealot-em11-07': dict(archive='em11', sections=[(0x1fc, 'body'), (0x1fe, 'head'), (0x204, 'right-hand'), (0x208, 'left-hand')],
                           tpl=0x1fd, section_tpls={0x1fe: 0x201}, rooms=['r117'], types=[7], category='registry',
                           model_id=0x11, lit=True, subset_bones=True),
    # NATIVE_MODEL_REGISTRY_POOL (lane ps2cast 2026-10-15): Em17Set type 0xc's whole section pool (body mot[1] 0x1CD /
    # TPL mot[0] 0x1CE; head mot[2] 0x1CF and hit head mot[3] 0x1D0 with TPL mot[5] 0x1CE; em10HandSet right mot[6..10]
    # 0x1C0..0x1C4 and left mot[11..14] 0x1C5..0x1C8, TPL mot[0]; em10SetAccesory whood mot[23] 0x1D3 with TPL mot[24]
    # 0x1D4 (flag 0x400000) or mot[25] 0x1D5 (flag 0x40000)). Caps / glasses are separate Obj12 objects.
    'ganado-em17-0cp': dict(archive='em17', sections=[
        (0x1cd, 'body'), (0x1cf, 'head'), (0x1d0, 'head-hit'),
        (0x1c0, 'right-hand'), (0x1c1, 'right-open'), (0x1c2, 'right-point'), (0x1c3, 'right-grip'), (0x1c4, 'right-scythe'),
        (0x1c5, 'left-hand'), (0x1c6, 'left-open'), (0x1c7, 'left-point'), (0x1c8, 'left-grip'),
        (0x1d3, 'whood', 0x1d4), (0x1d3, 'whood-b', 0x1d5)],
        tpl=0x1ce, rooms=['r108', 'r113', 'r118'], types=[12], category='registry', model_id=0x17, lit=True,
        subset_bones=True),
    # NATIVE_MODEL_REGISTRY_POOL (lane ps2cast 2026-10-15): the type 7 zealot's whole section pool, so every spawn's
    # source infos bind (em10ModelInit order: body, em10HeadSet head mot[2] / hit heads mot[3] / mot[4] with TPL mot[5];
    # em10HandSet right mot[6..9] and left mot[11..15], TPL mot[0]; em10SetAccesory hoods mot[26] / mot[27] with TPL
    # mot[0] and accessories mot[28..39] in BIN / TPL pairs). Not listed: the subArc TPL 0x220 accessory and the
    # Wep_type 12 subArc hand (the actor then keeps its source path).
    'zealot-em11-07p': dict(archive='em11', sections=[
        (0x1fc, 'body'), (0x1fe, 'head'), (0x1ff, 'head-hit'), (0x200, 'head-hit2'),
        (0x204, 'right-hand'), (0x205, 'right-open'), (0x206, 'right-point'), (0x207, 'right-grip'),
        (0x208, 'left-hand'), (0x209, 'left-open'), (0x20a, 'left-point'), (0x20b, 'left-grip'), (0x20c, 'left-grip2'),
        (0x202, 'hood'), (0x203, 'hood-up'),
        (0x20d, 'acc0'), (0x20f, 'acc1'), (0x211, 'acc2'), (0x213, 'acc3'), (0x215, 'acc4'), (0x217, 'acc5')],
        tpl=0x1fd, section_tpls={0x1fe: 0x201, 0x1ff: 0x201, 0x200: 0x201, 0x20d: 0x20e, 0x20f: 0x210, 0x211: 0x212,
                                 0x213: 0x214, 0x215: 0x216, 0x217: 0x218},
        rooms=['r117'], types=[7], category='registry', model_id=0x11, lit=True, subset_bones=True),
}


def section_specs(spec):
    """Source BIN/role/TPL selections; old single-TPL presets keep their order."""
    overrides = spec.get('section_tpls', {})
    bins = {x[0] for x in spec['sections']}
    if set(overrides) - bins:
        raise ValueError('section_tpls names a BIN outside the selected sections')
    # a section may name its own TPL as a third element (the same BIN under two TPLs: em10SetAccesory's whood colours)
    return [(x[0], x[1], x[2] if len(x) > 2 else overrides.get(x[0], spec['tpl'])) for x in spec['sections']]


def tpl_wrap_modes(data, image):
    """Read the original GC TPL's wrap modes before normalizing repeated UVs."""
    if len(data) < 12:
        raise ValueError('truncated source TPL header')
    magic, count, table = struct.unpack_from('>3I', data)
    if magic != 0x20af30 or image < 0 or image >= count or table + count * 8 > len(data):
        raise ValueError('invalid source TPL image')
    offset = struct.unpack_from('>I', data, table + image * 8)[0]
    if offset < 12 or offset + 20 > len(data):
        raise ValueError('truncated source TPL sampler')
    return struct.unpack_from('>2I', data, offset + 12)


def repeat_triangle_uv(uvs, wrap):
    """Shift each complete triangle by integer texture periods; never wrap corners.

    This preserves interpolation and sample phase for GX_REPEAT. A triangle
    crossing a period edge cannot be represented inside one atlas cell and is
    refused. Existing presets do not request this transform.
    """
    result = [list(uv) for uv in uvs]
    for axis in range(2):
        lo, hi = min(uv[axis] for uv in uvs), max(uv[axis] for uv in uvs)
        if 0 <= lo and hi <= 256:
            continue
        if wrap[axis] != 1:
            raise ValueError('UV normalization needs GX_REPEAT on the shifted axis')
        shift = -(lo // 256) * 256
        if lo + shift < 0 or hi + shift > 256:
            raise ValueError('repeated UV triangle crosses an atlas cell boundary')
        for uv in result:
            uv[axis] += shift
    return result


def sha(b):
    return hashlib.sha256(b).hexdigest()


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ------------------------------------------------------------------------------------------ inputs


# disc extracts are rebuildable: cached on ext4 (lane evidence), not in the private store
INPUTS = Path(os.environ.get('PS2CAST_INPUTS', '//wsl.localhost/Ubuntu-24.04/root/probe/lanes/ps2cast/inputs'))


def inputs(archive, out, ps2_iso, gc_iso):
    d = INPUTS
    d.mkdir(parents=True, exist_ok=True)
    p, g = d / f'{archive}.dat', d / f'{archive}.drs'
    if not p.exists():
        p.write_bytes(pb.afs_read(ps2_iso, f'{archive}.dat'))
    if not g.exists():
        sys.path.insert(0, str(HERE))
        from assetpipe.rooms import GcIso
        g.write_bytes(GcIso(gc_iso).read(f'em/{archive}.drs'))
    pd, gd = p.read_bytes(), g.read_bytes()
    rec = dict(ps2=dict(iso=str(ps2_iso), afs_entry=f'{archive}.dat', bytes=len(pd), sha256=sha(pd), cache=str(p)),
               gc=dict(iso=str(gc_iso), file=f'em/{archive}.drs', bytes=len(gd), sha256=sha(gd), cache=str(g)))
    ps2 = {i: (t, b) for i, t, b in pb.dat_entries(pd)}
    gc = drs.Drs(gd)
    return ps2, gc, rec


def gc_entry(gc, arc, tag):
    t, b = gc.entries[arc - 4]
    assert drs.tag_name(t) == tag, (hex(arc), t, tag)
    return b


def ps2_entry(ps2, arc, tag):
    t, b = ps2[arc - 4]
    assert t == tag, (hex(arc), t, tag)
    return b


# ------------------------------------------------------------------------------------------ GC side


def gc_skeleton(bin_bytes):
    mdl = modelbin.parse(bin_bytes)
    try:
        mdl.check_tree()
    except ValueError:
        # the stage-3 soldier bodies list some parents after their children (em1d BIN 0x22F: part 8 -> parent 27);
        # the rest pose is the same accumulation, resolved parent first (acyclic checked)
        return _gc_skeleton_any_order(mdl)
    bones = []
    for p in mdl.parts:
        m = np.eye(4)
        m[:3, 3] = p.pos
        if p.parent >= 0:
            m = np.asarray(bones[p.parent]['rest']) @ m
        bones.append(dict(id=p.no, parent=p.parent, attach=p.attach, translation=list(p.pos), rest=m.tolist(), capture=m.tolist()))
    return bones


def _gc_skeleton_any_order(mdl):
    # a section BIN with a partial skeleton (stage-3 soldier heads: 12 parts, attach ids 0-4 / 27-33) names its
    # parents by attach id (the body's part number), so parts are resolved by attach
    parts = {p.attach: p for p in mdl.parts}
    assert len(parts) == len(mdl.parts), 'GC section parts share an attach id'
    rest = {}

    def resolve(a, depth=0):
        if a in rest:
            return rest[a]
        assert depth <= len(parts) and a in parts, ('GC part parent not in the section', a)
        p = parts[a]
        m = np.eye(4)
        m[:3, 3] = p.pos
        if p.parent >= 0:
            m = resolve(p.parent, depth + 1) @ m
        rest[a] = m
        return m
    return [dict(id=p.no, parent=p.parent, attach=p.attach, translation=list(p.pos), rest=resolve(p.attach).tolist(),
                 capture=resolve(p.attach).tolist()) for p in mdl.parts]


def gc_mesh(bin_bytes):
    positions, pal, ws, norm, normpal, ds, dn, nc, uv, indices, batches, bindings, *_ = cc.parse_geometry(bin_bytes)
    weights = []
    for ids, pct in ws:
        rates, total = [], 0.0
        for k, b in enumerate(ids):
            f = pct[k] * .01 if k < len(ids) - 1 else 1 - total
            rates.append((b, f)); total += f
        weights.append(rates)
    tris = [[ds[j] for j in indices[k:k + 3]] for k in range(0, len(indices), 3)]
    nrm = [np.asarray(norm[dn[j]], float) for j in range(len(dn))]
    corner_normals = [[nrm[j] / (np.linalg.norm(nrm[j]) or 1) for j in indices[k:k + 3]] for k in range(0, len(indices), 3)]
    return dict(positions=np.asarray(positions, float), weights=[weights[p] for p in pal], triangles=np.asarray(tris, int),
                corner_normals=corner_normals, palettes=len(ws), normals=len(norm))


def gc_signature(d):
    """source_bindings.py's signature of a GC BIN: counts + FNV-1a of the first 64 bytes of the vertex
    array converted to little-endian s16 (what coarse_ganado_cast.cpp fingerprints on the loaded model)."""
    vo = struct.unpack_from('>I', d, 0x30)[0]
    raw = b''.join(struct.pack('<4h', *struct.unpack_from('>4h', d, vo + k)) for k in range(0, 64, 8))
    fnv = 2166136261
    for x in raw:
        fnv = ((fnv ^ x) * 16777619) & 0xffffffff
    mdl = modelbin.parse(d)
    return dict(part_bindings=[dict(id=p.no, parent=p.parent, attach=p.attach, translation=list(p.pos)) for p in mdl.parts],
                positions=struct.unpack_from('>H', d, 0x38)[0], normals=struct.unpack_from('>H', d, 0x3a)[0],
                palettes=d[0x18], parts=d[0x19], shift=d[0x28], flags=hex(struct.unpack_from('>I', d, 0x20)[0]),
                shape_offset=struct.unpack_from('>I', d, 0x2c)[0], source_vertex_fnv64_le=f'{fnv:08x}', bin_sha256=sha(d))


# ------------------------------------------------------------------------------------------ geometry checks


def closest_on_triangles(p, a, b, c):
    """closest points on triangles (a, b, c: (..., 3)) to points p (..., 3) (Ericson, vectorised)."""
    ab, ac, ap = b - a, c - a, p - a
    d1, d2 = (ab * ap).sum(-1), (ac * ap).sum(-1)
    bp = p - b
    d3, d4 = (ab * bp).sum(-1), (ac * bp).sum(-1)
    cp = p - c
    d5, d6 = (ab * cp).sum(-1), (ac * cp).sum(-1)
    va, vb, vc = d3 * d6 - d5 * d4, d5 * d2 - d1 * d6, d1 * d4 - d3 * d2
    den = np.where(np.abs(va + vb + vc) < 1e-20, 1e-20, va + vb + vc)
    v, w = vb / den, vc / den
    res = a + ab * v[..., None] + ac * w[..., None]
    with np.errstate(divide='ignore', invalid='ignore'):
        # edge regions
        cond = (vc <= 0) & (d1 >= 0) & (d3 <= 0)
        t = np.clip(np.nan_to_num(d1 / (d1 - d3)), 0, 1); res = np.where(cond[..., None], a + ab * t[..., None], res)
        cond = (vb <= 0) & (d2 >= 0) & (d6 <= 0)
        t = np.clip(np.nan_to_num(d2 / (d2 - d6)), 0, 1); res = np.where(cond[..., None], a + ac * t[..., None], res)
        cond = (va <= 0) & ((d4 - d3) >= 0) & ((d5 - d6) >= 0)
        t = np.clip(np.nan_to_num((d4 - d3) / ((d4 - d3) + (d5 - d6))), 0, 1); res = np.where(cond[..., None], b + (c - b) * t[..., None], res)
    # vertex regions
    res = np.where(((d1 <= 0) & (d2 <= 0))[..., None], a, res)
    res = np.where(((d3 >= 0) & (d4 <= d3))[..., None], b, res)
    res = np.where(((d6 >= 0) & (d5 <= d6))[..., None], c, res)
    return res


def surface_distance(points, verts, tris, cand=None, k=24):
    """distance from each point to the triangle mesh (verts, tris); cand = candidate triangle ids per point
    (default: the k nearest by centroid)."""
    A, B, C = verts[tris[:, 0]], verts[tris[:, 1]], verts[tris[:, 2]]
    if cand is None:
        cen = (A + B + C) / 3
        dd = ((points[:, None, :] - cen[None]) ** 2).sum(-1)
        cand = np.argsort(dd, axis=1)[:, :k]
    q = closest_on_triangles(points[:, None, :], A[cand], B[cand], C[cand])
    return np.sqrt(((q - points[:, None, :]) ** 2).sum(-1)).min(1), cand


def skin(verts, weights, mats):
    out = np.zeros_like(verts)
    h = np.c_[verts, np.ones(len(verts))]
    for i, w in enumerate(weights):
        m = sum(v * mats[b] for b, v in w)
        out[i] = (m @ h[i])[:3]
    return out


def winding_agreement(verts, tris, corner_normals):
    a, b, c = verts[tris[:, 0]], verts[tris[:, 1]], verts[tris[:, 2]]
    fn = np.cross(b - a, c - a)
    vn = np.asarray([sum(n) for n in corner_normals])
    s = (fn * vn).sum(1)
    return float((s > 0).mean())


# ------------------------------------------------------------------------------------------ convert


def convert(preset, out, ps2_iso=PS2_ISO, gc_iso=GC_ISO, poses=None, bone_tol=0.001):
    spec = PRESETS[preset]
    if spec.get('converter'):
        raise SystemExit(f'{preset} is converted by {spec["converter"]}, not ps2_cast.py convert')
    out.mkdir(parents=True, exist_ok=True)
    ps2, gc, rec = inputs(spec['archive'], out, ps2_iso, gc_iso)
    ptd = load_module('ps2_tpl_decode', WA / 'from-main/ps2-trees/tools/ps2_tpl_decode.py')
    val = dict(preset=preset, inputs=rec, sections=[])
    # GC skeleton from the body BIN; every section (PS2 and GC) must carry the same one
    gbody = gc_entry(gc, spec['sections'][0][0], 'BIN')
    bones = gc_skeleton(gbody)
    assert all(b['attach'] == b['id'] for b in bones), 'GC body parts with attach != index'
    id_to_index = {b['attach']: b['id'] for b in bones}
    rest = np.asarray([b['rest'] for b in bones])
    # Texture atlas: every section keeps its own source TPL identity. Image
    # indices from different TPLs occupy distinct atlas slots. Single-TPL
    # presets retain their original indices, metadata, and output bytes.
    selections = section_specs(spec)
    tpl_arcs = list(dict.fromkeys(tpl_arc for _, _, tpl_arc in selections))
    images, tpl_bases, tpl_records = [], {}, []
    for tpl_arc in tpl_arcs:
        tpl = ps2_entry(ps2, tpl_arc, 'TPL')
        tp = ptd.parse_tpl(tpl)
        tpl_bases[tpl_arc] = len(images)
        tpl_records.append(dict(arc=hex(tpl_arc), bytes=len(tpl), sha256=sha(tpl)))
        for h in tp['entries']:
            w, ht, rgba, st = ptd.decode(tpl, h)
            images.append(dict(index=len(images), width=w, height=ht, rgba=bytes(rgba), format=ptd.describe(h)['format'],
                               alpha_raw=sorted(st['alpha_raw_hist'])))
    sections, used = [], []
    for si, (arc, role, tpl_arc) in enumerate(selections):
        assert spec['category'] != 'human' or role == ROLES[si]
        pbin = ps2_entry(ps2, arc, 'BIN')
        gbin = gc_entry(gc, arc, 'BIN')
        m = pb.parse_bin(pbin)
        gsk = gc_skeleton(gbin)
        # skeleton identity: PS2 (id, parent, translation) == GC (attach, parent, translation)
        if len(gsk) != len(bones):
            # a partial GC section skeleton (stage-3 soldier head / hands: the parts they weight, by attach id):
            # each part must be the body bone of its attach id (parent, translation; a section root has parent -1);
            # PS2 ids are attach ids too
            # (em11 type 7 hands: 41 parts on the 37-bone body, two hand roots repeated by attach id)
            assert spec.get('subset_bones'), (role, len(gsk), len(bones))
            by_attach = {}
            for g in gsk:
                by_attach.setdefault(g['attach'], g)
            # body_bone_extras: a part no PS2 vertex weights (the soldier hit head 0x233's bone 31, set on both bodies,
            # whose bone 31 differ) is not drawn through, so its translation is recorded, not required
            weighted = ({b_ for _, cs in pb.triangles(m) for c in cs for b_, v in c['w'] if v > 0}
                        if spec.get('body_bone_extras') else None)
            for g in gsk:
                b = bones[id_to_index[g['attach']]]
                # a section root (parent -1) carries the body bone's rest position (model space)
                want = b['translation'] if g['parent'] >= 0 else [r[3] for r in b['rest'][:3]]
                if weighted is not None and g['attach'] not in weighted and g['parent'] >= 0 and \
                        max(abs(x - y) for x, y in zip(g['translation'], want)) > bone_tol:
                    assert g['parent'] == b['parent'], (role, 'unweighted GC section part parent', g['id'])
                    val.setdefault('unweighted_parts_off_body', {}).setdefault(role, []).append(g['attach'])
                    continue
                assert g['parent'] in (b['parent'], -1) and max(abs(x - y) for x, y in zip(g['translation'], want)) <= bone_tol,                     (role, 'GC section part', g['id'], 'attach', g['attach'], 'differs from the body bone', g['translation'], want)
            extra = sorted(set(pb_['id'] for pb_ in m.bones) - set(by_attach))
            # body_bone_extras (the stage-3 soldier accessory pool: 0x24F / 0x245 carry PS2 bones their GC section
            # drops): such a PS2 bone is checked against the BODY bone of its id instead (parent, translation); the
            # weights name body bones either way
            assert not extra or spec.get('body_bone_extras'), (role, 'PS2 bones outside the GC section attach ids')
            # a PS2 bone takes the GC part of its id with the same parent (a repeated hand root: parent -1)
            cands = {}
            for g in gsk:
                cands.setdefault(g['attach'], []).append(g)
            for x in extra:
                if x not in id_to_index:
                    # a PS2 bone past the body's (0x245's 37-bone table on the 34-bone body 0x247): never weighted
                    assert x not in weighted, (role, 'a weighted PS2 bone outside the body', x)
                    pb_ = next(q for q in m.bones if q['id'] == x)
                    cands[x] = [dict(id=x, attach=x, parent=pb_['parent'], translation=list(pb_['pos']))]
                    val.setdefault('unweighted_bones_past_body', {}).setdefault(role, []).append(x)
                    continue
                b = bones[id_to_index[x]]
                t = b['translation']
                if x not in weighted:  # an unweighted extra bone: parent checked, translation recorded only
                    t = list(next(pb_['pos'] for pb_ in m.bones if pb_['id'] == x))
                    if max(abs(p - q) for p, q in zip(t, b['translation'])) > bone_tol:
                        val.setdefault('unweighted_parts_off_body', {}).setdefault(role, []).append(x)
                cands[x] = [dict(id=x, attach=x, parent=b['parent'], translation=t)]
            if extra:
                val.setdefault('body_bone_extras', {})[role] = extra
            pairs = [(pb_, dict(next((g for g in cands[pb_['id']] if g['parent'] == pb_['parent']), cands[pb_['id']][0]),
                                attach=pb_['id'])) for pb_ in m.bones]
            id_parent = all((pb_['id'], pb_['parent']) == (g['attach'], g['parent']) for pb_, g in pairs)
            dt = max(max(abs(x - y) for x, y in zip(pb_['pos'], g['translation'])) for pb_, g in pairs)
            dt_body = 0.0
        elif len(m.bones) == len(gsk):
            pairs = list(zip(m.bones, gsk))
        else:
            # a reduced PS2 bone table (lane ps2cast-4: the crow's wing BINs carry only the bones they weight): each
            # PS2 bone is matched to the GC part of the same id (GC attach == index), parent and rest translation
            # checked per bone; weight ids are GC part ids either way
            assert spec.get('subset_bones') and len(m.bones) < len(gsk), (role, len(m.bones), len(gsk))
            pairs = [(pb_, gsk[pb_['id']]) for pb_ in m.bones]
        if len(gsk) == len(bones):
            id_parent = all((pb_['id'], pb_['parent']) == (g['attach'], g['parent']) for pb_, g in pairs)
            dt = max(max(abs(x - y) for x, y in zip(pb_['pos'], g['translation'])) for pb_, g in pairs)
            dt_body = max(max(abs(x - y) for x, y in zip(g['translation'], b['translation'])) for g, b in zip(gsk, bones))
        assert id_parent and dt <= bone_tol, (role, id_parent, dt)
        tris = pb.triangles(m)
        for mat in m.materials:
            image_index = tpl_bases[tpl_arc] + mat['diffuse']
            next_base = (tpl_bases[tpl_arcs[tpl_arcs.index(tpl_arc) + 1]]
                         if tpl_arcs.index(tpl_arc) + 1 < len(tpl_arcs) else len(images))
            assert tpl_bases[tpl_arc] <= image_index < next_base, (role, tpl_arc, mat['diffuse'])
            if image_index not in used:
                used.append(image_index)
        sections.append(dict(arc=arc, role=role, tpl=tpl_arc, image_base=tpl_bases[tpl_arc],
                             bin=m, tris=tris, gbin=gbin, gmesh=gc_mesh(gbin),
                             check=dict(arc=hex(arc), role=role, ps2_bin_bytes=len(pbin), ps2_bin_sha256=sha(pbin),
                                        gc_bin_bytes=len(gbin), gc_bin_sha256=sha(gbin), bones=len(m.bones),
                                        bone_id_parent_equal=id_parent, bone_translation_max_diff_mm=dt,
                                        gc_section_vs_body_translation_max_diff_mm=dt_body,
                                        ps2_materials=[dict(flag=x['flag'], diffuse=x['diffuse'], opacity=x['opacity']) for x in m.materials],
                                        ps2_triangles=len(tris), ps2_strip_vertices=sum(len(s['verts']) for n in m.nodes for s in n['segments']),
                                        ps2_segments=sum(len(n['segments']) for n in m.nodes))))
    used.sort()
    cells, (aw, ah) = pack_atlas([(k, images[k]['width'], images[k]['height']) for k in used])
    atlas = Image.new('RGBA', (aw, ah), (0, 0, 0, 255))
    for k in used:
        im = images[k]
        atlas.paste(Image.frombytes('RGBA', (im['width'], im['height']), im['rgba']), cells[k][:2])
    opaque = all(a >= 128 for im in images for a in im['alpha_raw'] if im['index'] in used)
    atlas_rgb = atlas.convert('RGB').convert('RGBA')  # opaque: PS2 alpha 0x80 = 1.0; RGB565 VQ has no alpha
    atlas_rgb.save(out / 'atlas.png')
    val['texture'] = dict(tpl_arc=tpl_records[0]['arc'], tpl_bytes=tpl_records[0]['bytes'], tpl_sha256=tpl_records[0]['sha256'],
                          images=[{k: v for k, v in im.items() if k != 'rgba'} for im in images], used=used,
                          atlas=[aw, ah], cells={str(k): v for k, v in cells.items()}, opaque=opaque,
                          uv_rule='PS2 s16 / 256 (ps2_room_r4im.py: JADERLINK vt x 255/256), cell offset in the atlas')
    if len(tpl_records) > 1:
        val['texture']['tpls'] = tpl_records
        val['texture']['section_tpls'] = [hex(tpl_arc) for _, _, tpl_arc in selections]
        val['texture']['image_bases'] = {hex(arc): base for arc, base in tpl_bases.items()}
    # mesh json (PS2 geometry, GC bone indices)
    vert_index, positions, weights, triangles = {}, [], [], []
    zero_normals = 0
    for si, s in enumerate(sections):
        gm = s['gmesh']
        for mat_i, corners in s['tris']:
            cx, cy, cw, ch = cells[s['image_base'] + s['bin'].materials[mat_i]['diffuse']]
            raw_uvs = [c['raw']['uv'] for c in corners]
            if spec.get('repeat_uvs'):
                wrap = tpl_wrap_modes(gc_entry(gc, s['tpl'], 'TPL'), s['bin'].materials[mat_i]['diffuse'])
                normalized = repeat_triangle_uv(raw_uvs, wrap)
                if any(tuple(a) != tuple(b) for a, b in zip(raw_uvs, normalized)):
                    val['repeat_uv_triangles_shifted'] = val.get('repeat_uv_triangles_shifted', 0) + 1
                raw_uvs = normalized
            if spec.get('uv_edge_texels'):
                # lane ps2cast2: a PS2 corner up to uv_edge_texels texels outside its 256 image (the bat: 7 corners at
                # 257 on a GX_REPEAT image) is clamped to the image edge (counted); anything farther is refused.
                k = spec['uv_edge_texels']
                if any(not -k <= x <= 256 + k for uv in raw_uvs for x in uv):
                    raise ValueError('PS2 UV beyond uv_edge_texels')
                clamped = [[min(256, max(0, x)) for x in uv] for uv in raw_uvs]
                n = sum(tuple(a) != tuple(b) for a, b in zip(raw_uvs, clamped))
                if n:
                    val['uv_edge_corners_clamped'] = val.get('uv_edge_corners_clamped', 0) + n
                raw_uvs = clamped
            cs = []
            fa, fb, fc = (np.asarray(c['p']) for c in corners)
            face = np.cross(fb - fa, fc - fa)
            if not np.linalg.norm(face):  # a degenerate strip triangle draws nothing
                val['degenerate_triangles_dropped'] = val.get('degenerate_triangles_dropped', 0) + 1
                continue
            face = face / np.linalg.norm(face)
            for c, (raw_u, raw_v) in zip(corners, raw_uvs):
                if not any(c['n']):  # a zero PS2 normal: the face normal (winding as read)
                    c = dict(c, n=tuple(face)); zero_normals += 1
                w = [(id_to_index[b], float(v)) for b, v in c['w'] if v > 0]
                if not w:
                    raise ValueError(f'{s["role"]}: an unweighted PS2 vertex')
                wk = tuple(sorted(w))
                key = (tuple(round(x, 5) for x in c['p']), wk)
                if key not in vert_index:
                    vert_index[key] = len(positions)
                    positions.append([float(x) for x in c['p']])
                    weights.append([[b, v] for b, v in w])
                u = (cx + raw_u * cw / 256.0) / aw  # PS2 UVs are normalised to the image (s16 / 256)
                v = (cy + raw_v * ch / 256.0) / ah
                assert 0 <= u <= 1 and 0 <= v <= 1
                cs.append(dict(vertex=vert_index[key], normal=[float(x) for x in c['n']], uv=[u, v]))
            triangles.append(dict(source_info=si, corners=cs))
    P = np.asarray(positions)
    val['zero_normals_replaced_by_face_normal'] = zero_normals
    # winding: the GC convention (face normal vs vertex normals) must hold for the PS2 triangles too
    flip = None
    for si, s in enumerate(sections):
        gm = s['gmesh']
        g_ok = winding_agreement(gm['positions'], gm['triangles'], gm['corner_normals'])
        ts = [t for t in triangles if t['source_info'] == si]
        pt = np.asarray([[c['vertex'] for c in t['corners']] for t in ts])
        p_ok = winding_agreement(P, pt, [[np.asarray(c['normal']) for c in t['corners']] for t in ts])
        s['check'].update(gc_winding_agreement=g_ok, ps2_winding_agreement_as_read=p_ok)
        want = g_ok > .5
        f = (p_ok > .5) != want
        assert flip in (None, f), 'sections disagree on the winding flip'
        flip = f
    if flip:
        for t in triangles:
            t['corners'] = t['corners'][::-1]
    val['winding_flipped'] = bool(flip)
    # source.json (GC side) + mesh.json
    infos = []
    for si, s in enumerate(sections):
        gm = s['gmesh']
        infos.append(dict(id=si, address=f'{spec["archive"]}:arc:{s["arc"]:03x}', source_data_address=f'{spec["archive"]}:arc:{s["arc"]:03x}',
                          source_bin_arc=s['arc'], source_tpl_arc=s['tpl'], source_sha256=sha(s['gbin']), role=s['role'],
                          gc_positions=len(gm['positions']), gc_normals=gm['normals'], gc_palettes=gm['palettes'],
                          gc_triangles=len(gm['triangles'])))
    source = dict(name=preset, schema='ps2cast-source-1', source_units='millimetres', source_archive=spec['archive'],
                  source_archive_sha256=rec['gc']['sha256'], ps2_archive_sha256=rec['ps2']['sha256'],
                  bones=[dict(id=b['id'], parent=b['parent'], address=f'{spec["archive"]}:part:{b["id"]}', rest=b['rest'], capture=b['capture'])
                         for b in bones], infos=infos, category=spec['category'], rooms=spec['rooms'], types=spec['types'])
    sp = out / 'source.json'
    sp.write_text(json.dumps(source))
    mesh = dict(schema='re4dc-approved-render-mesh-1', source_sha256=sha(sp.read_bytes()), mesh=preset.replace('-', '_') + '_ps2',
                positions_mm=positions, weights=weights, bones=source['bones'], triangles=triangles,
                policy='PS2 source geometry, normals, UVs (atlas cells) and skin weights, bound to the GC skeleton '
                       '(identical bone table); no reduction or refit.')
    mp = out / 'mesh.json'
    mp.write_text(json.dumps(mesh))
    # skin checks: weights, rest and posed surface distance to the GC mesh
    for si, s in enumerate(sections):
        gm = s['gmesh']
        ts = [t for t in triangles if t['source_info'] == si]
        vids = sorted({c['vertex'] for t in ts for c in t['corners']})
        pv = P[vids]
        d0, cand = surface_distance(pv, gm['positions'], gm['triangles'])
        # GC -> PS2 too (holes / missing parts show here)
        pt = np.asarray([[c['vertex'] for c in t['corners']] for t in ts])
        remap = {v: i for i, v in enumerate(vids)}
        ptl = np.vectorize(remap.get)(pt)
        g0, _ = surface_distance(gm['positions'], pv, ptl)
        ws = [weights[v] for v in vids]
        s['check'].update(
            ps2_unique_positions=len(vids), gc_positions=len(gm['positions']), gc_triangles=len(gm['triangles']),
            ps2_palettes=len({tuple(map(tuple, w)) for w in ws}), gc_palettes=gm['palettes'],
            max_influences=max(len(w) for w in ws), weight_sum_range=[min(sum(x for _, x in w) for w in ws), max(sum(x for _, x in w) for w in ws)],
            bones_used=sorted({b for w in ws for b, _ in w}),
            rest_ps2_to_gc_surface_mm=dict(median=float(np.median(d0)), p95=float(np.percentile(d0, 95)), max=float(d0.max())),
            rest_gc_to_ps2_surface_mm=dict(median=float(np.median(g0)), p95=float(np.percentile(g0, 95)), max=float(g0.max())))
        # normals vs the GC's at coincident positions (< 0.5 mm)
        angs = []
        for t in ts:
            for c in t['corners']:
                p = P[c['vertex']]
                dd = np.linalg.norm(gm['positions'] - p, axis=1)
                j = int(dd.argmin())
                if dd[j] < .5:
                    gn = [gm['corner_normals'][ti][k] for ti, tri in enumerate(gm['triangles']) for k in range(3) if tri[k] == j]
                    best = max(float(np.dot(c['normal'], n)) for n in gn)
                    angs.append(math.degrees(math.acos(max(-1, min(1, best)))))
        if angs:
            s['check']['normal_angle_vs_gc_deg_at_shared_positions'] = dict(n=len(angs), median=float(np.median(angs)), p95=float(np.percentile(angs, 95)))
        S = json.loads(Path(poses).read_text())['samples'] if poses else None
        if S and len(S[0]['world']) != len(bones):
            s['check']['posed_ps2_to_gc_surface_mm'] = f'skipped: the pose file has {len(S[0]["world"])} bones, the model {len(bones)}'
        elif S:
            worst = []
            for k, smp in enumerate(S[::4]):
                mats = np.asarray(smp['world']) @ np.linalg.inv(rest)
                pp = skin(pv, ws, mats)
                gp = skin(gm['positions'], gm['weights'], mats)
                dk, _ = surface_distance(pp, gp, gm['triangles'], cand)
                worst.append((float(np.percentile(dk, 95)), float(dk.max())))
            s['check']['posed_ps2_to_gc_surface_mm'] = dict(poses=len(worst), source=str(poses),
                                                          p95_max=max(w[0] for w in worst), max=max(w[1] for w in worst),
                                                          p95_median=float(np.median([w[0] for w in worst])))
    val['sections'] = [s['check'] for s in sections]
    # pack (the cast's packer, unchanged) + host fixture
    pk = load_module('pack_coarse_actor', PROTO / 'tools/pack_coarse_actor.py')
    native = out / 'native'
    if native.exists():
        shutil.rmtree(native)
    # The packer stores positions as s16 at 1/16 mm (+-2048 mm). A larger model (spec 'shift', the GC BIN's own
    # position shift: El Gigante 2) packs positions / 2^(4 - shift) (normals, weights and binds unchanged) and its
    # registry descriptor carries the shift (NATIVE_MODEL_REGISTRY_SHIFT); mesh.json keeps millimetres.
    shift = spec.get('shift', 4)
    val['position_shift'] = shift
    # flat_normals (PS2CAST_FLAT_NORMALS=1, Ganado cast bundles only): every packed corner normal is one constant
    # vector, so each chunk keeps a single normal and records merge on (position, uv). The cast Ganados draw unlit in
    # the play recipe (ACTOR_GANADO_SOURCE_LIGHT=0: a constant-colour SourceLighting, normals never read), so the image
    # is unchanged while the static data shrinks (the s30 heap-4 gate). A lit-Ganado image needs the normal bundle.
    flat = os.environ.get('PS2CAST_FLAT_NORMALS') == '1'
    val['flat_normals'] = flat
    # lane ps2cast-4: the registry animals (dog, cow, chicken) draw flat too (the constant actor light, as today's cast
    # animals); a preset marked lit (em22: the source lighting record) keeps its normals
    if flat and (spec['category'] not in ('human', 'animal') or spec.get('lit')):
        raise ValueError('PS2CAST_FLAT_NORMALS is for the unlit Ganado cast and the flat registry animals only')
    if shift != 4 or flat:
        pm = dict(mesh)
        if shift != 4:
            pm['positions_mm'] = [[x / (1 << (4 - shift)) for x in p] for p in positions]
            pm['policy'] += f' Positions / {1 << (4 - shift)} for the s16 range (drawn at shift {shift}).'
        if flat:
            pm['triangles'] = [dict(t, corners=[dict(c, normal=[0.0, 1.0, 0.0]) for c in t['corners']]) for t in triangles]
            pm['policy'] += ' Normals flattened to one constant vector (unlit cast; PS2CAST_FLAT_NORMALS=1).'
        mpk = out / 'mesh-pack.json'
        mpk.write_text(json.dumps(pm))
        mp = mpk
    pk.pack(mp, sp, native, 'castmodel')
    host_fixture(native, source)
    report = json.loads((native / 'native-report.json').read_text())
    val['native'] = {k: v for k, v in report.items() if k != 'chunks'}
    val['native']['chunks'] = [{k: v for k, v in c.items() if k != 'palette_weights'} for c in report['chunks']]
    # cast layout files (GC signatures; texture key from the atlas identity)
    binds = []
    for s in sections:
        binds.append(dict(bin=s['arc'], tpl=s['tpl'], role=s['role'], **gc_signature(s['gbin']),
                          binding_scope='GC source array signature (the loaded model the PS2 mesh replaces)'))
    (out / 'source-bindings.json').write_text(json.dumps(binds, indent=2))
    key = texture_key(out / 'atlas.png')
    val['texture'].update(key=key)
    (out / 'validation.json').write_text(json.dumps(val, indent=1))
    print(json.dumps(dict(preset=preset, triangles=report['triangles'], winding_flipped=val['winding_flipped'], key=key,
                          sections=[{k: s[k] for k in ('role', 'ps2_triangles', 'gc_triangles', 'ps2_palettes', 'gc_palettes',
                                                       'rest_ps2_to_gc_surface_mm', 'rest_gc_to_ps2_surface_mm',
                                                       'posed_ps2_to_gc_surface_mm', 'normal_angle_vs_gc_deg_at_shared_positions',
                                                       'gc_winding_agreement', 'ps2_winding_agreement_as_read') if k in s}
                                    for s in val['sections']]), indent=1))


def pack_atlas(items):
    """Guillotine packing of power-of-two images (k, w, h) into the smallest power-of-two atlas (square or 2:1
    wide) that holds them, largest first, deterministic. -> ({k: (x, y, w, h)}, (atlas w, atlas h))."""
    area = sum(w * h for _, w, h in items)
    side = max(max(w for _, w, _ in items), max(h for _, _, h in items))
    cands = []
    # from side / 2 (lane ps2cast-4): a single wide image (em22's 512 x 256 TPL) takes a 2:1 atlas of its own size
    # instead of a square one twice as large (a too small candidate simply fails to pack)
    s = max(side // 2, 8)
    while s <= 2048:
        cands += [(s, s), (2 * s, s)]
        s *= 2
    for aw, ah in sorted(set(cands), key=lambda c: (c[0] * c[1], c[0])):
        if aw * ah < area or aw > 2048:
            continue
        free, out, ok = [(0, 0, aw, ah)], {}, True
        for k, w, h in sorted(items, key=lambda t: (-t[1] * t[2], -t[1], t[0])):
            fit = [f for f in free if f[2] >= w and f[3] >= h]
            if not fit:
                ok = False
                break
            f = min(fit, key=lambda f: (f[2] * f[3], f[1], f[0]))
            free.remove(f)
            out[k] = (f[0], f[1], w, h)
            if f[2] > w:
                free.append((f[0] + w, f[1], f[2] - w, h))
            if f[3] > h:
                free.append((f[0], f[1] + h, f[2], f[3] - h))
        if ok:
            return out, (aw, ah)
    raise ValueError('atlas does not fit 2048')


def host_fixture(n, source):
    """prepare_dynamic_native_check.py's host-fixture.bin (the cast agent's check-dynamic input)."""
    rest = np.asarray([b['rest'] for b in source['bones']]); cap = np.asarray([b['capture'] for b in source['bones']])
    sk = cap @ np.linalg.inv(rest); sk[:, :3, 3] += rest[0, :3, 3] - cap[0, :3, 3]
    r = json.loads((n / 'native-report.json').read_text())
    buf = bytearray(struct.pack('<I', len(r['chunks'])))
    for c in r['chunks']:
        i = c['info']
        parts = [(n / f'info{i}.{ext}').read_bytes() for ext in ['pos', 'nrm', 'uv', 'gx']]
        poses = np.asarray([sum(w * sk[b] for b, w in ws)[:3, :4].T.flatten() for ws in c['palette_weights']], dtype='<f4').tobytes()
        buf.extend(struct.pack('<10I', i, c['positions'], c['normals'], c['palettes'], c['triangles'], *[len(x) for x in parts], len(poses)))
        for p in parts + [poses]:
            buf.extend(p)
    (n / 'host-fixture.bin').write_bytes(buf)


def texture_key(png):
    """package_coarse_texture.py's identity: CRC32 / FNV-1a of the image as GX RGBA8 (format 6) tiles."""
    image = Image.open(png).convert('RGBA'); w, h = image.size
    px = np.asarray(image, dtype=np.uint8)
    enc = bytearray()
    for y in range(0, h, 4):
        for x in range(0, w, 4):
            blk = px[y:y + 4, x:x + 4].reshape(16, 4)
            enc.extend(bytes(np.stack([blk[:, 3], blk[:, 0]], 1).reshape(-1)))
            enc.extend(bytes(np.stack([blk[:, 1], blk[:, 2]], 1).reshape(-1)))
    ident = struct.pack('<5I', w, h, 6, 0xffffffff, 0) + bytes(enc)
    crc = zlib.crc32(ident) & 0xffffffff
    fnv = 2166136261
    for b in ident:
        fnv = ((fnv ^ b) * 16777619) & 0xffffffff
    return f'{crc:08x}-{fnv:08x}'


# ------------------------------------------------------------------------------------------ finish / castdir


def blob_stats(header):
    cb = load_module('cast_bundle', os.environ.get('RE4_CAST_BUNDLE', '//wsl.localhost/Ubuntu-24.04/root/probe/d367-agents/coarse-actors-4k/tools/cast_bundle.py'))
    # cast_bundle.py is fixed at the Ganado's 34 bones; the stats themselves are bone-count independent
    cb.BONES = int(re.search(r'bone_count=(\d+);', Path(header).read_text()).group(1))
    chunks, arrays, weights, blobs = cb.parse_header(str(header), 0)
    return cb.blob_stats(blobs, arrays, chunks), cb.skin_stream_bytes(weights, [c[3] for c in chunks], str(header))


def finish(out):
    """after ps2_cast_native.sh: manifest.json with the runtime header's counts (cast manifest keys)."""
    val = json.loads((out / 'validation.json').read_text())
    hdr = out / 'runtime' / 'castmodel_runtime.h'
    s, skin_bytes = blob_stats(hdr)
    tex = json.loads((out / 'texture' / 'package.json').read_text())
    preset = val['preset']
    spec = PRESETS[preset]
    level = dict(runtime_header='runtime/castmodel_runtime.h', header_sha256=sha(hdr.read_bytes()), triangles=s['triangles'],
                 transformed_records=s['records'], records_per_triangle=s['records'] / s['triangles'],
                 strip_vertices=s['corners'], strip_vertices_per_triangle=s['corners'] / s['triangles'], palettes=s['palettes'],
                 palette_runs=s['palette_runs'], meshlets=s['meshlets'], skin_stream_bytes=skin_bytes)
    man = dict(name=preset, revision='ps2-v1', source=dict(name=preset, archive=spec['archive'], rooms=spec['rooms'], types=spec['types'],
               sections=[dict(bin=a, tpl=t, role=r) for a, r, t in section_specs(spec)]),
               status='PS2 conversion; needs user look review', bones=val['sections'][0]['bones'], sections=len(val['sections']),
               source_palette_sum=sum(x['gc_palettes'] for x in val['sections']),
               ps2_palette_sum=sum(x['ps2_palettes'] for x in val['sections']),
               levels=dict(conservative=level, lean=level),
               texture_package=dict(package='texture/' + tex['key'] + '.re4tex', package_sha256=tex['package_sha256'], key=tex['key'],
                                    width=tex['width'], height=tex['height'], format=tex['format'], vram_bytes=tex['vram_bytes']))
    (out / 'manifest.json').write_text(json.dumps(man, indent=1))
    print(json.dumps(level, indent=1))


def castdir(cast, outs, hand_arcs=range(0x1c0, 0x1c9)):
    """A cast dir for cast_bundle.py: <cast>/<name>/{manifest,source-bindings,source}.json + header + texture,
    source/candidate-revisions.json, and em<archive>-hand-<i>/source-bindings.json (GC hand-pose signatures)."""
    cast.mkdir(parents=True, exist_ok=True)
    (cast / 'source').mkdir(exist_ok=True)
    revs = {}
    archives = set()
    for o in outs:
        man = json.loads((o / 'manifest.json').read_text())
        name = man['name']
        d = cast / name
        if d.exists():
            shutil.rmtree(d)
        d.mkdir()
        for f in ('source-bindings.json', 'validation.json'):
            shutil.copy2(o / f, d / f)
        # cast_bundle.py resolves manifest paths against the cast root
        m2 = json.loads(json.dumps(man))
        for L in m2['levels'].values():
            L['runtime_header'] = f'{name}/{L["runtime_header"]}'
        m2['texture_package']['package'] = f'{name}/{man["texture_package"]["package"]}'
        (d / 'manifest.json').write_text(json.dumps(m2, indent=1))
        src = json.loads((o / 'source.json').read_text())
        (d / 'source.json').write_text(json.dumps(dict(src, bones=[dict(b) for b in src['bones']])))
        (d / 'runtime').mkdir()
        shutil.copy2(o / 'runtime' / 'castmodel_runtime.h', d / 'runtime' / 'castmodel_runtime.h')
        (d / 'texture').mkdir()
        shutil.copy2(o / man['texture_package']['package'], d / man['texture_package']['package'])
        revs[name] = dict(revision=man['revision'], reason='PS2 conversion (ps2_cast.py)')
        archives.add((man['source']['archive'], o))
    (cast / 'source' / 'candidate-revisions.json').write_text(json.dumps(revs, indent=1))
    for archive, o in sorted(archives):
        gin = json.loads((o / 'validation.json').read_text())['inputs']['gc']
        gd = Path(gin['cache']).read_bytes()
        assert sha(gd) == gin['sha256'], 'GC archive cache changed'
        gc = drs.Drs(gd)
        for i, arc in enumerate(hand_arcs):
            d = cast / f'{archive}-hand-{i}'
            d.mkdir(exist_ok=True)
            b = gc_entry(gc, arc, 'BIN')
            (d / 'source-bindings.json').write_text(json.dumps([dict(bin=arc, role='hand-pose', **gc_signature(b))], indent=1))
    print('cast dir', cast, sorted(revs))


def to_wsl(p):
    s = str(p).replace('\\', '/')
    m = re.match(r'^//wsl\.localhost/[^/]+(/.*)$', s)
    if m:
        return m.group(1)
    m = re.match(r'^([A-Za-z]):(/.*)$', s)
    return f'/mnt/{m.group(1).lower()}{m.group(2)}' if m else s


def regcast(cast, overlay, outs):
    """A cast dir in the external cast's registry layout for tools/d367/model_registry.py (NATIVE_MODEL_REGISTRY):
    <cast>/<overlay>/integration-bundle/catalog.json, <cast>/<name>/{manifest,source,source-bindings}.json,
    <cast>/<name>/ps2-v1/{revision-manifest.json, header, texture}, <cast>/source/{candidate-revisions,
    archive-audit}.json. Paths inside are WSL paths (the generator runs in WSL). One atlas per model: every chunk
    (source_info) binds the same package. em12 joins archive-audit.json for the generator's self-check."""
    cast.mkdir(parents=True, exist_ok=True)
    (cast / 'source').mkdir(exist_ok=True)
    ib = cast / overlay / 'integration-bundle'
    ib.mkdir(parents=True, exist_ok=True)
    base_audit = json.loads((PRIV / 'cast-20260925' / 'source' / 'archive-audit.json').read_text())
    audit = {'em12': {k: base_audit['em12'][k] for k in ('source', 'sha256')}}
    catalog, revs = [], {}
    for o in outs:
        man = json.loads((o / 'manifest.json').read_text())
        val = json.loads((o / 'validation.json').read_text())
        name, preset = man['name'], val['preset']
        spec = PRESETS[preset]
        d = cast / name
        if d.exists():
            shutil.rmtree(d)
        (d / 'ps2-v1' / 'texture').mkdir(parents=True)
        hdr = d / 'ps2-v1' / 'castmodel_runtime.h'
        shutil.copy2(o / 'runtime' / 'castmodel_runtime.h', hdr)
        tp = man['texture_package']
        pkg = d / 'ps2-v1' / 'texture' / Path(tp['package']).name
        shutil.copy2(o / tp['package'], pkg)
        fmt = 'VQ RGB565' if 'VQ' in tp['format'] else tp['format']
        tex = dict(key=tp['key'], package=to_wsl(pkg), package_sha256=tp['package_sha256'], format=fmt,
                   rectangle=[0, 0, tp['width'], tp['height']], vram_bytes=tp['vram_bytes'])
        level = dict(runtime_header=f'{name}/ps2-v1/castmodel_runtime.h', header_sha256=sha(hdr.read_bytes()))
        packages = {str(i): tex for i in range(man['sections'])}
        entry = dict(name=name, revision='ps2-v1', previous_revision=None, rooms=spec['rooms'], category=spec['category'],
                     levels=dict(conservative=level), texture_packages=packages, position_shift=val.get('position_shift', 4),
                     status='PS2 conversion (ps2_cast.py); render-only replacement of the GC source mesh')
        catalog.append(entry)
        (d / 'ps2-v1' / 'revision-manifest.json').write_text(json.dumps(dict(entry, levels=dict(conservative=level)), indent=1))
        (d / 'manifest.json').write_text(json.dumps(dict(name=name, revision='ps2-v1'), indent=1))
        shutil.copy2(o / 'source-bindings.json', d / 'source-bindings.json')
        src = json.loads((o / 'source.json').read_text())
        src['source_model_id'] = spec['model_id']
        (d / 'source.json').write_text(json.dumps(src))
        gin = val['inputs']['gc']
        assert sha(Path(gin['cache']).read_bytes()) == gin['sha256'], 'GC archive cache changed'
        audit[spec['archive']] = dict(source=to_wsl(gin['cache']), sha256=gin['sha256'])
        revs[name] = dict(revision='ps2-v1', reason='PS2 conversion (ps2_cast.py)')
    (ib / 'catalog.json').write_text(json.dumps(catalog, indent=1))
    (cast / 'source' / 'candidate-revisions.json').write_text(json.dumps(revs, indent=1))
    (cast / 'source' / 'archive-audit.json').write_text(json.dumps(audit, indent=1))
    print('registry cast dir', cast, sorted(revs))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    c = sp.add_parser('convert'); c.add_argument('preset', choices=sorted(PRESETS)); c.add_argument('out', type=Path)
    c.add_argument('--ps2-iso', default=PS2_ISO); c.add_argument('--gc-iso', default=GC_ISO); c.add_argument('--poses')
    c.add_argument('--bone-tol', type=float, default=0.001)
    f = sp.add_parser('finish'); f.add_argument('out', type=Path)
    d = sp.add_parser('castdir'); d.add_argument('cast', type=Path); d.add_argument('outs', type=Path, nargs='+')
    r = sp.add_parser('regcast'); r.add_argument('cast', type=Path); r.add_argument('overlay'); r.add_argument('outs', type=Path, nargs='+')
    sp.add_parser('list')
    a = ap.parse_args()
    if a.cmd == 'convert':
        convert(a.preset, a.out, a.ps2_iso, a.gc_iso, a.poses, a.bone_tol)
    elif a.cmd == 'finish':
        finish(a.out)
    elif a.cmd == 'castdir':
        castdir(a.cast, a.outs)
    elif a.cmd == 'regcast':
        regcast(a.cast, a.overlay, a.outs)
    else:
        for k, v in sorted(PRESETS.items()):
            print(k, v['archive'], [(hex(x[0]), x[1]) for x in v['sections']], 'tpl', hex(v['tpl']), v['rooms'])


if __name__ == '__main__':
    main()
