# Handover: RE4 Dreamcast chapter 1 PS2 asset and rendering POC (2026-10-15)

This is a read-only inventory. Nothing was built, run, changed or deleted to write it. Every path, SHA and hash below was
checked on disk on 2026-10-15 between 19:20 and 20:00. "Doc:" means the claim is quoted from the named document and was
not re-measured. **UNVERIFIED** marks anything not confirmed by looking. Hashes are sha256 prefixes (16 hex) unless
noted. All game data here is converted Capcom data: **local paths only, never upload or publish it.**

## 0. Repositories and branches (read this first)

| What | Value |
|---|---|
| Main checkout (WSL Ubuntu-24.04) | `/root/work/re4-dreamcast`. **It is on branch `cgate` at 070972f8 (2026-09-26) with 75 dirty entries.** Do not build from it or reset it: other sessions share it (memory note re4-dreamcast-shared-checkout). It holds 487 git worktrees. |
| Remotes | origin `https://github.com/lamb2k/re4dc.git`; also bruce, old-fork, upstream (adonis-singh/re4) |
| Public branch | `origin/dreamcast-port` = **5d44dc0d** (2026-10-15 17:25, "Docs: fix a doubled word…"). Test 13 is its newest release (tag `test-05e5ff76-20261015`, image c1ae83dd). |
| Integration branch | `t15/int` = **c5ef4ade** (2026-10-15 19:14), worktree `/root/probe/lanes-20261015/t15int` (clean). It is 112 commits ahead of dreamcast-port, which is its ancestor. It holds tests 14 and 15 (not published). |
| Test 14 candidate (not published) | `C:\Game Dev\Emulators\RE4DC-Test14-Candidate\`: `RE4DC-Console-Test-e2048df6-20261015-GDEMU.zip` (34f3ad7f…) and `RE4DC-Test14-e2048df6-Build-Assets.zip` (0fc5ed95…) |
| Suggested new worktree (not run) | `git -C /root/work/re4-dreamcast worktree add /root/probe/<team>/tree t15/int` (or `origin/dreamcast-port` for the published state) |

Lane-only work (local branches, not merged into t15/int):

| Branch | Head | Worktree |
|---|---|---|
| `lane/worldvert` | 713f9319 (WIP) | `/root/probe/lanes-20261015/worldvert` |
| `lane/worldlod` | 6f3defad | `/root/probe/lanes-20261015/worldlod` |
| `lane/leonlod` | 4988dacb | `/root/probe/lanes-20261015/leonlod` (GANADO_LOD is merged into t15/int) |

Rules that bind this work are in `C:\Game Dev\Emulators\CLAUDE.md`: the optimization, VRAM, enemy cap 6, release, disk
hygiene and approximation rules.

## 1. Chapter 1 inventory and conversion coverage

### 1.1 Rooms
`port/dreamcast/tools/d367/stage_route.py` traces the route (memory note re4-dreamcast-stage1-route; output
`/root/probe/stage1-route-20260930`, not re-run):
- **1-1:** r120 > r100 > r101 > r103 > r106, then r106 door 3 > r104
- **1-2:** r104 > r107 > r105
- **1-3:** r105 > r101 > r102 > r108 > r109 > r10a > r10b, then door 6 > r11b (chapter 2-1)

r120 is the intro movie room and has no world. Rows below come from the **test 14 RC package fixture**
`/root/probe/lanes-20261015/t14rc/fix/pkg-t14grP.json` (1,683 replace / 2,074 remove entries), read on 10-15.
On disc, each room's world is `dc/native/<room>/ps2-world.{re4mesh,r4pw,ids}`.

Columns:
- **Package source.** PRIV = `/mnt/c/Game Dev/Emulators/re4-assets-private` (Windows `C:\Game Dev\Emulators\re4-assets-private`).
  `blackps2` means `PRIV/t11-20261014/blackps2/<room>/`: the PS2 world with its black 0xa0000000 faces lit offline by
  the PS2 rule (test 12.1, T12-DARK-ROOMS-20261015.md).
- **VQ share.** The doc CONVERSION-STATUS-20261015.md, test 10 census.
- **Effects.** The PS2 recipe tables are in code (PS2_FX_ROOMS / STAGE1 / POPULATION / ADDITIONS / ROOMS_EXT, EFFECT_TORCH,
  RAIN_PS2; all in the T11REC recipe). The effect pictures come from FX_PS2_PACK, out of
  `PRIV/ps2lib/effects-tex/<room>`.
- **Enemies.** PS2_ENEMY_ROOMS=0x3f is in every release since test 11. Its bits are r100 0x01, r101 0x02, r104 0x04,
  r108 0x08, r11a 0x10, r11b 0x20 (`tools/d367/ps2rooms/PS2_ENEMY_CH1.md`). PS2_CH1_ENEMY=1 (test 13 on) adds the
  chapter 1 PS2 rules + ALIVE_CAP=6 park/hold + R101_CAP_WAVES (ALIVECAP-20261015.md).

| Room | PS2 world re4mesh: source, sha256, bytes | World textures (all in tex.pak) | Resident list | Strip groups (.r4sg) | Effects pictures dir | PS2 enemy tables | Static obj bake | World vertex level |
|---|---|---|---|---|---|---|---|---|
| r100 | `PRIV/t11-20261014/r100-smx-tr4/` 130bac79… 1,537,920 (+ `interior.cell` 0b68a093…, SMX + tr4 overlays) | PS2; 35/55 VQ (64%) | none | no | yes | 0x01 + CH1; documented exception, s20 peak 9 | no | no |
| r101 | `PRIV/crowd12-bake-20261015/r101-t13/` 500d17da… 1,283,520 (bake13: smx101 f5592282 + strip groups + 14 baked objects) | PS2; 12 large 16-bit -> VQ (`tools/d367/vram/vq16-r101.txt`), Leon atlas VQ | `vram/resident/r101.tsv` (190 keys) | **yes**: r4sg 80da4063… (117,152 B) | yes | 0x02 + CH1, R101_ALIVE_CAP / CAP_WAVES, peak 6 | **yes** (STATIC_OBJ_BAKE, 14 objects) | lane only: wv1 (worldvert, see 7) |
| r103 | blackps2 96d23822… 1,074,688 | 39/52 VQ (75%) | `r103.tsv` (52 keys) | no | yes | CH1 (3 cows + 3 chickens removed), peak 5 | no | no |
| r106 | blackps2 209fe5dd… 991,712 | 27/42 (64%) | none | no | yes | CH1, peak 6 | no | no |
| r104 | blackps2 300f6bac… 648,096 | 41/55 (75%) | none | no | yes | 0x04 + CH1, peak 6 | no | no |
| r107 | blackps2 bbb0fba9… 898,400 | 42/50 (84%) | none | no | yes | CH1, peak 6; PS2_AREA_HIDE (T13) | no | no |
| r105 | blackps2 f96e48b1… 752,448 | 103/147 (70%) | none | no | **no dir** | CH1, peak 6 | no | no |
| r102 | blackps2 7fbf371f… 395,968 | 46/76 (61%) | none | no | yes | no Ganados | no | no |
| r108 | blackps2 555028d0… 912,480 | 42/72 (58%) | none | no | yes | 0x08 + CH1, peak 6 | no | no |
| r109 | blackps2 be246055… 933,152 | 13/35 (37%) | none | no | **no dir** | no Ganados (crows) | no | no |
| r10a | blackps2 c5eafa96… 733,824 | 31/42 (74%) | none | no | yes | CH1 (2 snakes removed), peak 6 | no | no |
| r10b | blackps2 334ca6a4… 696,416 | 41/53 (77%) | none | no | yes | Del Lago, exempt | no | no |
| r11b (2-1) | blackps2 bc24650d… 769,824 | 47/60 (78%) | none | no | yes | 0x20 | no | no |

Notes on the table:
- **Core resident set.** `r000.tsv` (7 rows) is the HUD core set. `resident.bin` packs r000 + r101 + r103 (test 15
  res16, de98da1ec2e75532, 4,096 B).
- **Strip groups.** r101 is the only room with an .r4sg. `ps2lib/world/r101-sg4` (re4mesh 45ef304f…, r4sg 5844096f…) is
  the pre-bake strip-group package; bake13 replaced it.
- **Room archives.** Each room also stages a GameCube-derived `dc/native/<room>/MAINSCENARIO.re4mesh` (the
  Standard/GC scenery fallback). It comes from `/root/probe/c13/rooms`, `/root/probe/lanes/route/pkg-*`,
  `/root/probe/lanes-20261009|10/<room>/rooms` and `/root/probe/d367-agents/w9`. `st1/<room>.arc` is the GC room
  archive, staged from the same route dirs.
- **Room objects.** `st1/<room>.dar` comes from `PRIV/objs-20261014/t13/<room>/` for r102..r11b and from
  `/root/probe/lanes-20261014/t12rc/data/items/r10{0,1}b/` for r100 and r101.
- **2-1 rooms on the same disc:**
  - r11a, r117, r118 are blackps2.
  - **r119's re4mesh comes from D:** `/mnt/d/Flycast-Evidence/re4-dreamcast/i1920-20261011/pkg/all/r119-tr4/ps2-world.re4mesh`
    (9dd036b3…, 1,058,272). Its r4pw is `PRIV/p2pt-cutout-20261012/r119/` (b5a13a92…). Copy it before any D: cleanup.
- **Optional rooms.** r10c, r10d, r10e have PS2 conversions in `PRIV/ps2rooms-20260930/out/r10{c,d,e}-ps2`, but they are
  not staged on any release disc.
- **Converter inputs.** The original PS2 room conversions (all route rooms, `-ps2` and `-ps2-uvg` variants) are in
  `PRIV/ps2rooms-20260930/out/`. Their extraction manifest is `extract-manifest.json` and their hash list is `SHA256SUMS`
  (9,614 lines).
- **Budgets.** The per-room world vertex budgets and cut targets are in `WORLD-BUDGET-BY-ROOM-20261015.md` (MODELLED).
  The rooms over budget include r109, r107, r106, r104, r103, r100 and r101.

### 1.2 Characters
Ganado and Leon render meshes are **compiled into the program** from headers, not loaded from disc:
- `PS2_LEON_DIR=/root/probe/lanes-20261011/pl08/assets/arm-a` (ps2leon_runtime.h, leon_pl08_runtime.h,
  hair runs, leon_pl08_ps2.re4cp).
- `PS2_GANADO_DIR=/root/probe/lanes-20261010/ps2cast-all-assets/pg5/ganado_cast_runtime.h`.

Both are in t15-build.sh. Their textures, the per-room registries (`dc/native/<room>/registry.re4nmr`) and the em
archives are disc data. "Census" = Flycast NMRD admitted / declined counts (doc PS2CAST-20261014.md).

| Character | id | Rooms (ch1 + 2-1) | Source state | LOD | Package / data location |
|---|---|---|---|---|---|
| Leon (jacket / no jacket) | pl00 / pl08 | all | PS2 mesh (arm A). Face and hair leon4k are GC-derived textures. Atlas `ec255e66-76812316` ships as VQ. | LEON_LOD packages exist; user 10-15: **Leon stays at level 0** | Headers above. Disc: `dc/native/pl08/leon_pl08_ps2.re4cp`, `dc/native/pl00/leon_hands_pl00.re4hp` (`/root/probe/lanes-20261013/hands2-work/pkg/`). LOD pack: `/root/probe/lanes-20261015/leonlod-assets/lod/leon_lod.re4lp` (ea72a168…). Source mesh: `C:\Game Dev\Emulators\ps2leon-20261010\arms\a\mesh.json` |
| Ganados (village) | em15 | r101 | PS2 (PS2_GANADO, five appearances ganado-em12-01, em15-00/03/04/0b) + PS2 hats (acc12) | GANADO_LOD (t15 T15REC): levels today / g85 / g70 / g55; boot level 2 = **g70** (3,046 vs 4,965 body+head tris); cutscenes draw level 0 | `/root/probe/lanes-20261015/t15k/data/glod/ganado_lod.re4gl` 465661548f14dddc, 326,880 B (same bytes as `C:\Game Dev\Emulators\ganadolod-20261015\ganado_lod.re4gl`). Store: `PRIV/ps2cast-all-20261010/ganado-*`. Accessories: `PRIV/ps2lib/cast/common/acc12/em1{2,3,5,7}.drs` |
| Ganados | em12 | r100, r11a | PS2 + PS2 hats; APP0_GRIP fixes the declines | same g70 | registry r100 `PRIV/p2a3-crow-20261011/package-r100/…`; T15 cast15 `/root/probe/lanes-20261015/ps2cast/conv-t14/reg-100` |
| Ganados | em13 | r104 | PS2 | same | acc12 em13.drs; cast15 reg-104 |
| Robed merchant-type Ganado (enemy 0x5E) | em13 type 6 | r104 | PS2 in T15 (cast15). GC in test 14. | - | cast15 reg-104 |
| Ganados | em17 | r108, r118 (2-1) | r108 PS2. r118 types 00/01/03/0c: PS2 pool in T15 (NATIVE_MODEL_REGISTRY_POOL) | same | reg-108 `PRIV/p2a5-regblobs-20261011/…`; cast15 reg-118pc |
| Dog | em21 | r100, r101 | PS2 (PS2_ANIMALS) | - | `tools/d367/model-registry/ps2-animals.json`, `ps2-crow.json` (dog-01) |
| Cow / chicken | em26 / em28 | r101, r103 | PS2 (PS2_ANIMALS) | - | ps2-animals.json; registries `PRIV/ps2cast-4-20261011/packages/reg-anf-10{1,3}` |
| Crows | em23 | r100, r105, r109 | PS2 (PS2_CROW) | - | `PRIV/p2a3-crow-20261011/em23-prepared/em23.drs`; reg-crow-105 / reg-crow-109 in `PRIV/p2b-20261011/` |
| Bats | em29 | r106 | GC through test 14. **PS2 in T15** (PS2_CAST_CH1) | - | cast15 `prep14/em29` |
| Crawler, traps, snakes, fish | em2e / em2a / em24 / em27 | r106; r100 r105 r106 r107 r10a; r10a r108 r11a; r10b r11b | GC through test 14. **PS2 in T15** (PS2_CAST_CH1). Traps, snakes, bats and crawler are the same mesh and texels as GC. | - | `/root/probe/lanes-20261015/ps2cast/prep14/<em>/` + conv-t14 regs; registry `model-registry/ps2-ch1-cast.json` |
| Boat | pl0f | r10b, r11b | GC through 14; PS2 in T15 (PS2_CAST_BOAT) | - | prep14/pl0f |
| Del Lago | em2f | r10b | PS2 mesh with a GC-texture atlas (PS2_DELLAGO) | - | registry `/root/probe/lanes-20261010/ps2cast-3-work/reg-dl-gctex`; `PRIV/ps2cast-2-20261010/em2f-textures/em2f.drs` |
| Colmillos (2-1) | em22 | r11b | PS2 (PS2_WOLF) | - | `PRIV/ps2cast-4-20261011/em22-prepared`, reg-wolf-11b |
| El Gigante (2-1) | em2b | r119 | PS2 mesh with a GC-texture atlas (PS2_GIGANTE) | - | `/root/probe/lanes-20261010/ps2cast-3-work/reg-gig-gctex` |
| Merchant | em18 | r102 | PS2 (PS2_CAST_MERCHANT, unlit) | - | `PRIV/ps2lib/cast/r102/merchant-em18/` |
| Ashley (2-1) | pl11 | r117, r118 | PS2 (PS2_ASHLEY=2, rest face) | - | `PRIV/ps2lib/cast/r117|r118/ashley-pl11/` |
| Zealot (2-1) | em11 type 7 | r117 | PS2 pool in T15 | - | cast15 reg-117p |
| Luis | pl14 | - | module not linked; no in-game appearance (ASSET-SOURCE-LEDGER-20261014) | - | - |
| Chief Mendez / cutscene cast | - | movies | Cutscenes are GC movies converted offline (fixture provenance `/root/probe/d367-agents/cutscenes/movies-288x192-full`). **Whether any chapter 1 event draws Mendez as an in-engine model: UNVERIFIED.** | - | - |

The PS2_CAST_CH1 lists are in `game/native_model_registry.mk` (PS2_CAST_CH1, ~line 398) and in the cast15 set of
t11-fix.py (`_C15R` rooms 100 104 105 106 107 108 10a 10b 11a 11b 117p 118pc; archives em2a em24 em27 em29 em2e pl0f).
Per-actor census and gate details are in `PS2CAST-20261014.md`, section "2026-10-15 (afternoon)".

## 2. Private source assets (local only)

**Discs**

| Disc | Path | Hash (recorded) |
|---|---|---|
| GC debug Disc 1 (G4BE08) | `C:\Game Dev\Emulators\Resident Evil 4 Debug (Disc 1)\Resident Evil 4 Debug (Disc 1).iso` (+ `.7z` beside it); WSL link `/root/work/re4-dreamcast/orig/G4BE08/re4_debug_disc1.iso` | `orig/G4BE08/re4_debug_disc1.hashes.txt`: SHA1 3a0925e6e9d86f7c7533b6fab37f740d63630039, SHA256 b7fcbf121cf7c527… |
| GC review-ROM Disc 2 (2004.11.25) | `C:\Game Dev\Emulators\Resident Evil 4 - 2004.11.25 Disc 2 (Resident Evil 4 Review Rom (GC) No Reviews Until March 05 Issues).gcm`; link `orig/G4BE08/re4_review_disc2.gcm` | Whole-disc hash **UNVERIFIED** (not recorded). Its st3 REL SHA1s match build.sha1 (memory note) |
| GC retail USA Disc 2 (data only, keep out of orig/G4BE08) | `C:\Game Dev\Emulators\Resident Evil 4 (USA) (Disc 2)\…iso`; link `orig/usa-retail/re4_usa_disc2.iso` | SHA1 c75f7936814636ffe03277f363fc3427c98602ee (`re4_usa_disc2.hashes.txt`). The `.7z` named in the memory note no longer exists |
| PS2 USA (SLUS_211.34) | `C:\Users\Public\ps2\DVD\Resident Evil 4 (USA).iso` and `C:\Game Dev\Emulators\re4_helpers\Resident Evil 4 (USA)\Resident Evil 4 (USA).iso` (both 4,435,836,928 B) | Whole-ISO hash not recorded. AFS index sha256 a7b0c371… (`ps2rooms-20260930/extract-manifest.json`) |

**Extraction outputs**
- PS2 ELF: `/root/probe/d367-agents/audio/ps2/extract/SLUS_211.34`.
- AFS index: `/root/probe/d367-agents/audio/ps2/afs_entries.json`.
- GC extract: `/root/work/re4-dreamcast/orig/G4BE08/files`.
- PS2 room dats: `PRIV/ps2rooms-20260930` (inputs, out, gc-lit, HANDOFF.md, SHA256SUMS). The tool hashes in
  extract-manifest.json are dat.exe ed7f6fd4… and RE4_PS2_SCENARIO_SMD_TOOL.exe 9fc3d21b….
- Effect and archive caches: `/root/probe/worldfx-cache` (doc PARITY-CENSUS).

**Manifests**
- `PRIV/MANIFEST.tsv`: 89,261 rows (path, size, mtime_ns, sha256), written by `PRIV/manifest.py`.
- `PRIV/ps2lib/INDEX.tsv` + `README.md`: one row per preconverted PS2 asset, including its gate status. Classes: world,
  objects, items, breakables, effects-tex, cast, ui.

**Prepared packages, staged through `tools/d367/test11/t11-fix.py` data sets**
- Composition:
  - `T11_DATA = r119c,em29,fbec,r100tr4,smx101,blackgc14p`
  - `T12_DATA = r119c,em29,fbec,r100tr4,smx101,sg101,t12tex,objs12b,merchant,items12,acc12d`
  - `T121_DATA = T12 + blackps2w,t121tex`
  - `T13_DATA = T121 + objs13d,ashley13,bake13,t13tex`
  - `T14_DATA = T13 + res14r3`
  - `T15_DATA = T14 + cast15,glod,res16`
- Base fixture: `/root/probe/lanes-20261014/t10s/fix/pkg-t10stP.json`.
- **Most staged sources live on WSL ext4 under `/root/probe/lanes-*`, not in re4-assets-private.**

| Set | Key file(s) | Hash |
|---|---|---|
| t13tex (texture pack, used by T13/T14/T15) | `/root/probe/lanes-20261015/t13rc/data/tex-t13v.pak`: 127,219,712 B, 4,817 entries (RE4PAK1 v1) | 9bbe65e631c3de9e (measured) |
| res14r3 | `/root/probe/lanes-20261015/squeeze/rel14r3/resident.bin` | 8a307ffc3770058a |
| res16 | `/root/probe/lanes-20261015/t15k/data/res16/resident.bin` | de98da1ec2e75532 |
| glod | `/root/probe/lanes-20261015/t15k/data/glod/ganado_lod.re4gl` | 465661548f14dddc |
| bake13 | `PRIV/crowd12-bake-20261015/r101-t13/ps2-world.{re4mesh,r4pw,r4sg,ids}` | 500d17da / 2c9deabb / 80da4063 / a845e305 |
| smx101 / sg101 | `PRIV/t11-20261014/r101-smx/` / `PRIV/ps2lib/world/r101-sg4/` | f5592282 / 45ef304f (+r4sg 5844096f) |
| r100tr4 | `PRIV/t11-20261014/r100-smx-tr4/` | re4mesh 130bac79, r4pw be83fed7, ids c4394a5f |
| blackps2w | `PRIV/t11-20261014/blackps2/<room>/` | per room, section 1.1 |
| cast15 | `/root/probe/lanes-20261015/ps2cast/conv-t14/reg-*/` + `prep14/<em>/` | not hashed (UNVERIFIED) |
| objs13d / items12 / acc12d / merchant / ashley13 | `PRIV/objs-20261014/t13`, `/root/probe/lanes-20261014/t12rc/data/items`, `PRIV/ps2lib/cast/...` | t11-fix records each file's sha prefix in the fixture's provenance.t11 at staging |
| Effect pack sources | `PRIV/ps2lib/effects-tex/{common,em11,em18,em23,r100…r11b}` + `KEYS.tsv`, `NOTES.tsv` | - |
| World LOD studies (lane) | `PRIV/worldlod-20261015/{r101,r119}-*`, `PRIV/worldvert-20261015/{r101-v1,r101-v2,r101-scan}` | - |

Other: `PRIV/world-agent-20260926/` holds the external world agent's original r101 PS2 world work
(ps2-world-20260927, ps2-rooms-20260929, continuation-20260927/playability-r11-r1 = the playability harness, whose
programs dir the route builds write).

## 3. Blender

- **Install.** `C:\Program Files\Blender Foundation\Blender 5.2\blender.exe`. It is not on PATH (`where blender` finds
  nothing). User config: `%APPDATA%\Blender Foundation\Blender\5.2`. No portable copy under `C:\Game Dev\Emulators`.
  Add-ons: none found in the repo scripts (all use `--factory-startup`); installed add-ons are **UNVERIFIED**.
- **Not in the shipping asset path.** Runtime meshes are reduced by the repo's own Python half-edge collapse
  (`tools/mesh_lod.py`, `tools/d367/leonlod/lod_mesh.py`), which keeps every surviving vertex an original PS2 vertex.
  Blender does look renders, comparison sheets, AO/preview bakes and one experimental world decimator.
- **Scripts.** Each is invoked as `"<blender.exe>" -b --factory-startup --python <script> -- <args>`.
  - `tools/d367/ps2leon/bl_render.py <job.json>`: Leon look renders.
    - Used for `C:\Game Dev\Emulators\leonlod-20261015\renders` (job files `renders-job-r{1,2,3}.json`, logs
      `renders-r*.log`; a copy of the script is in `leonlod-20261015\tools\bl_render.py`).
    - Example: `"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b --factory-startup --python "C:\Game Dev\Emulators\leonlod-20261015\tools\bl_render.py" -- "C:\Game Dev\Emulators\leonlod-20261015\renders-job-r1.json"`
    - The job lists models (mesh.json), the atlas and the hair PNGs from `PRIV/charbake-20261010/src`. It writes
      `flat-*` and `wire-*` PNGs.
  - `tools/d367/leonlod/bl_ganado.py <job.json>`: Ganado LOD sheets (EEVEE, unlit).
    - Jobs: `C:\Game Dev\Emulators\ganadolod-20261015\jobs\ganado-*.json`, made by `mkjobs.py`.
    - Levels today / g85 / g70 / g55 come from `rung-*` dirs. The store is `PRIV/ps2cast-all-20261010`.
  - `tools/d367/ps2leon/bl_arm_b.py <comparison.blend> <job.json> <out>`: Leon arm B (README line 64).
  - `tools/d367/charbake/blender_ao.py`, `blender_preview.py`: character bakes. `charbake.py` defaults
    `CHARBAKE_BLENDER` to the 5.2 exe.
  - `tools/blender/bl_{decimate,house_shell,house_compare,impostor_bake,impostor_compare,measure,pair_ps2,render_compare}.py`:
    the 09-23 era studies (house shells, tree impostors, GC vs PS2 compare). There are vendor copies in
    `tools/assetpipe/vendor/`.
  - `tools/motion/blender_check.py` (repo root `tools/`).
  - Lane worldlod only: `port/dreamcast/tools/d367/worldlod/blender_decimate.py IN.json OUT.json`. It is Blender
    Decimate (COLLAPSE) as an external far-level reducer for `ps2_world_far_lod.py --export-clusters`. Outputs:
    `PRIV/worldlod-20261015/r101-p4-blender` (far-report.json says `"external": true`, growth +131,776 B) and
    `r119-far-blender`. It was not adopted.

## 4. PS2 extraction, conversion, packing and staging tools
All paths are relative to `port/dreamcast/` in the t15int tree unless a lane is named. Commands run in WSL unless marked
"Windows Python". The examples are taken from each tool's docstring.

| Tool | Purpose | Example |
|---|---|---|
| `tools/ps2_room_extract.py` | PS2 ISO -> AFS `<room>.dat` -> JADERLINK dat.exe + SMD tool -> converter inputs (mono) | see docstring; manifest `PRIV/ps2rooms-20260930/extract-manifest.json` |
| `tools/ps2_room_r4im.py` | JADERLINK OBJ export -> R4IM v3 prelit mesh + R4PW + RE4DCTX textures (any room; NORMAL groups need GC LIT cut-0 from `gc_lit_dump.py`) | `ps2_room_r4im.py <room> <inputs> <out> [--lights a,b]` (Windows Python; work dir `PRIV/world-agent-20260926/ps2-rooms-20260929`) |
| `tools/ps2_world_r4im.py` | the original r101 path (.r4p wrapper -> R4IM v3 + R4PW) | docstring |
| `tools/d367/ps2world/` | `world_registry.py` (validated packages -> `game/platform/include/ps2_world_rooms.inc`), `room_fixture.py`, `bringup_inventory.py`, `ps2_world_check.cpp`, `pvs/`, `interior/` | README.md |
| `tools/d367/ps2ref/ps2dis.py` | SLUS_211.34 + SNR2 .rel disassembler using the ELF's export-name table | docstring |
| `tools/d367/ps2ref/ps2roomdiff.py` | PS2 vs GC room/enemy code diff per room (`--rel-dir`, `--tree`) | used for PS2-ENEMY-CODE-DIFF-20261015.md |
| `tools/d367/stage_route.py` | door graph + required rooms from the GC disc (AEV/ITA) | `python3 tools/d367/stage_route.py --stage 1 --json OUT` |
| `tools/mesh_lod.py` | QEM half-edge collapse LOD (pure Python), used by convert_room_bins.py and the ladders | library |
| `tools/ps2_strip_groups.py` | up to 4 spatial strip groups per meshlet -> re-ordered re4mesh + .r4sg (PS2_STRIP_GROUPS); check with `tools/d367/worldlean/sgcheck.py` | `ps2_strip_groups.py IN.re4mesh IN.r4pw OUT.re4mesh OUT.r4sg --groups 4` |
| `tools/ps2_world_far_lod.py` (lanes worldlod, worldvert) | far-level LOD, one game-wide px floor, 12 m switch + hysteresis (WORLD_LOD) | `ps2_world_far_lod.py IN OUT --sidecar R4PW --table worldlod-rooms.json --room r119` |
| `tools/ps2_world_vert_ladder.py` (lane worldvert) | level-0 replacement ladder (WORLD_VERT) | see section 7 |
| `tools/d367/worldlod/walk.py` (lane) | walkable points from PS2 SAT floors | `python3 tools/d367/worldlod/walk.py <r101_001.SAT> r101.json` |
| `tools/ps2_cast.py`, `ps2_cast_native.sh`, `tools/d367/ps2cast/*` | PS2 character -> cast pack bound to the GC skeleton; merchant/ashley packaging, `prep_archive.sh`, `vq_chroma.py` | PS2CAST-20261014.md |
| `tools/d367/leonlod/{lod_mesh,lod_pack,glod_rung,glod_pack}.py`, `glod_native.sh` | Leon and Ganado LOD rungs and disc packages | `glod_pack.py pack OUT.re4gl <bundle header> today=bundle g85=<dir> …`; `glod_pack.py show <pkg>` |
| `tools/ps2_objects.py`, `ps2_objects_tex.py`, `tools/d367/objs13/*` | PS2 geometry for room objects in GC ModelData (dar) | `tools/d367/objs13/gen13.sh` |
| `tools/ps2_items.py`, `ps2_items_tex.py` | PS2 pickups and debris written in place | `ps2_items.py pack …` |
| `tools/d367/test12fx/fx_ps2_pack.py` | PS2 effect library + tex.pak (FX_PS2_PACK); `fx_pal4_pack.py` (PAL4) | `fx_ps2_pack.py lib <ps2lib root> <tag>`; `fx_ps2_pack.py pack <in.pak> <out.pak> <ps2lib root> --rooms common,r100,…` |
| `tools/d367/texpack.py` | dc/tex/* -> dc/tex.pak (RE4PAK1) and `--verify` | `texpack.py <disc.bin or dc/tex dir> <out tex.pak>` |
| `tools/d367/tex_merge.py`, `tex_wrapsafe.py`, `tex_size_check.py` | merge paks, wrap-safe marking (TEX_WRAP_SAFE) | t12/t13 texpak scripts |
| `tools/d367/vram/vq_pak.py` | re-encode named 16-bit keys as full-codebook VQ (pinned KOS pvrtex) | `vq_pak.py <in.pak> <out.pak> <work> <key>…` (key list e.g. `vram/vq16-r101.txt`) |
| `tools/vq_native_ui.py`, `vq_export.py`, `tools/d367/texture-vq-rooms.sh` | VQ encoder and the room-effects VQ pass | `texture-vq-rooms.sh <fixture-dir> <out-dir> <run-output.txt>…` |
| `tools/d367/vram/resident_keys.py`, `vram_gate.py` | per-room resident lists from VRAM_ROOM_LOG runs -> `dc/resident.bin`; VRAM gate | `resident_keys.py list <room hex> <out.tsv> <run-output.txt>…`; `… pack r000 r101 r103` |
| `tools/d367/route/pack-fixture.sh` | stage a fixture once, pack its dc/tex into tex.pak, write a -pak fixture (refuses to overwrite without `--replace`; see the pack-fixture trap note) | `pack-fixture.sh <fixture> <arm> <out fixture>` |
| `tools/d367/test11/t11-fix.py` | release fixture = base fixture + named data sets (sha prefixes recorded) | `D=$(python3 -c "import importlib.util as u;s=u.spec_from_file_location('t','tools/d367/test11/t11-fix.py');m=u.module_from_spec(s);s.loader.exec_module(m);print(m.T15_DATA)"); python3 tools/d367/test11/t11-fix.py <label> <out.json> --data $D` |
| `/root/probe/lanes-20261011/test8/t8-pkgtree.py` (**outside the repo**) + `tools/d367/mkgdi.sh` | fixture -> pkgtree -> GDI (used by t14-package.sh) | `PKG_K=$R python3 …/t8-pkgtree.py $L fix.json`; `bash mkgdi.sh <elf> <pkgtree> <gdemu dir>` |
| `tools/d367/stage_ext4/stage_scenario.py` (+ `install.sh`) | ext4 + disc-cache staging, drop-in for the harness `stage-scenario.py` (`RE4DC_STAGE_EXT4=0` reverts) | same CLI as the harness: `<scenario> --arm … --fixture …` |
| `tools/d367/fullplay/fp_run.py` (Windows Python), `fp_master.sh`, `fp_check.py`, `segments.conf`, `kos_squeeze.sh` | bounded Flycast run of a GDI + full-play gate | `python fp_run.py --disc <gdi dir> --cap <new evidence dir> --syms "<log> <head> <stage>" --seconds 60` |
| `tools/d367/benchmark/*`, `tools/d367/benchpub/{bench-build,bench-package,bench-zip}.sh` | warp bench scenes; public benchmark disc build -> master -> zip | `bash bench-build.sh B Q K`; `bash bench-package.sh <label>`; `bash bench-zip.sh <label>` |

## 5. Dreamcast / KOS toolchain and builds

**Pins** (`port/dreamcast/toolchain.lock`):
- `KOS_SHA=804b3195ebd1a06a27cc2b3a5eacf7a2429040a3`
- `KOS_PORTS_SHA=f4faacc42faaf552625777b7709e871a827e1055`
- `SH4ZAM_SHA=33fa4850cacb30dd0ad35485ef035526ec4ce782` (v0.9.1)
- `RE4_SOURCE_SHA=9dcd989370be7f083a9b66cfd19907fda627c893`
- Compiler: kos-chain "stable" (GCC 15.2.0, binutils 2.45.1, newlib 4.6.0.20260123). `-m4-single`.

**Installed on this host**

| Tree | State |
|---|---|
| `/root/work/kos` | 804b3195, clean |
| `/root/work/kos-re4dc-d367` | 804b3195 + manual-flip + async-present + vbuf-switch (modified pvr files, new `pvr_vbuf.c`). `tools/d367/build.sh` picks it automatically when `PVR_PIPELINE=2` |
| `/root/work/kos-re4dc-d336` | 804b3195 + manual-flip only (the PVR_STREAM=1 experiment; do not patch it) |
| `/root/work/kos-ports` | f4faacc4 |
| Compiler | `/opt/toolchains/dc/sh-elf` (sh-elf-gcc 15.2.0). There is no `/opt/toolchains/dc/kos` |

`kos-env.sh` defaults to `KOS_BASE=/root/work/kos`; override it with `RE4DC_KOS_BASE`.

**Patches** (`port/dreamcast/patches/`):
- The KOS tree gets 3: manual-flip, async-present, vbuf-switch.
- Two are applied at game build time, only with `KOS_DISC_FIX=1` (set by DISC_COMPAT=1): fs-iso9660-aeee10d9 and
  cdrom-hang-fixes. game/Makefile patches copies of fs_iso9660.o and cdrom.o (patches/README.md).
- Also present: `kos-804b319-cdrom-dma-done.patch` (lane discread-t14fix) and `kos-804b319-mm-sbrk-last-page.patch`
  (KOS_SBRK_LAST_PAGE). How these two are applied is **UNVERIFIED**.

Commands (exact, from the scripts):
- **Toolchain, no Docker:** `bash port/dreamcast/tools/setup-toolchain.sh $HOME/re4dc-toolchain` (about 25-40 min, 6 GB
  while building), then `source $HOME/re4dc-toolchain/env.sh`. Then `bash port/dreamcast/tools/install-sh4zam.sh`, if
  setup did not already install sh4zam.
- **Docker:** `docker build -t re4dc-toolchain -f port/dreamcast/docker/Dockerfile .` then
  `docker run --rm -it -v "$PWD":/src -w /src re4dc-toolchain bash port/dreamcast/build-public.sh`.
- **Public program:** `bash port/dreamcast/build-public.sh [KNOB=v…]`. It reads `RELEASE_KNOBS`, which defaults to
  `tools/d367/test14/release-knobs.txt` (156 lines), and `ASSETS`.
- **Swap onto a release:** `python3 port/dreamcast/tools/swap-program.py <release zip> <OUT> <new disc dir>`.
- **One command from a clone:** `bash port/dreamcast/contrib.sh [--release <tag>] [--out <dir>]`. It downloads the GDEMU
  zip and the Build-Assets zip from lamb2k/re4dc and checks them against SHA256SUMS.
- **Release recipe:**
  - `tools/d367/build-r21.sh` is the base recipe. It sets MESH_DIRECT=1 TA_DIRECT=1 PS2_WORLD_MESH=1 PS2_WORLD_ROOMS=2
    MESH_LOD=1 MESH_VP_SCHED=1 NATIVE_ACTOR_FAST=1 NATIVE_FOG=1 TEX_PACK=1 TEX_RESIDENT=1 PVR_PIPELINE=2
    TA_DOUBLEBUF=1 COARSE=1 ….
  - Layers on top, each in its own script: test13/t13-build.sh, test14/t14-build.sh, test15/t15-build.sh.
- **Build arms:** `bash port/dreamcast/tools/d367/test15/t15-build.sh rP rW mW rT kP kW kT`. The script's default env is
  T=/root/probe/lanes-20261015/t15int, K=/root/probe/lanes-20261015/t15k.
  - Each arm calls `route-build.sh` through `/root/probe/d367-buildslot.sh`, a host-wide build slot outside the repo.
  - Output: `/root/probe/lanes/route/out-<label>` (re4dc-game.elf, resolved-knobs.txt, candidate.txt, stack.txt).
  - `kP` must be byte-identical to test 14's image.
- **Package:** `tools/d367/test14/t14-package.sh` (env L, R, P). It runs release-knobs check -> t11-fix -> t8-pkgtree
  -> mkgdi on ext4, then makes one copy to C:. There is no t15 package script yet (test15/ holds only t15-build.sh).
- **Benchmark disc:**
  - Build file: `game/bench.mk` (BENCHMARK=1 needs DBG_WARP=1 and WARP_AFTER_RESET=1).
  - Build: `BASE=/root/probe/lanes/route/out-<release label> bash tools/d367/benchpub/bench-build.sh B` (arms B, Q
    squeeze twin, K knob-off). Then `bench-package.sh <label>` (IP.BIN product T0002, "NOT THE GAME") and
    `bench-zip.sh <label>`.
  - Discs on disk: `C:\Game Dev\Emulators\RE4DC-Benchmark-Part{1,2}-b7aba292\` (Part 1 zip b6b67804…, gdi
    1bac5c9d…) and `…-76f40d95\`.
- **hw model:**
  - Run: `port/dreamcast/tools/hwmodel/hwproject.sh [--name N] [--count A:B] [--trace A:B:S] <evidence|build dir>`.
  - Defaults: `HWM_BIN=/mnt/d/Flycast-Evidence/re4-dreamcast/hwmodel-bin` and
    `HWM_REF=/mnt/d/Flycast-Evidence/re4-dreamcast/hwmodel-ld2/proj`, both on **D:**.
    `HWM_EVROOT=/mnt/c/Flycast-Evidence/re4-dreamcast`.
  - The "console" column is `hwsim --console-fit` (D fill +6, I fill +5, store miss 0; hwsim.c:49, README line 148).
  - The calibration factors are in `HWMODEL-CALIBRATION-20261015.md`.
  - Modelled numbers are not console numbers (CLAUDE.md).

## 6. Remaining GameCube dependencies (chapter 1)

| Area | What still comes from GC data or the GC code path | Where |
|---|---|---|
| Collision | All of it. SAT/EAT and the collision tables are GC room data. The PS2 world is render-only, and its converters state "collision is a separate file (untouched)" | GC room archives `st1/<room>.arc`, `room/collision_package.cpp`; policy in memory note re4-dreamcast-render-policy |
| Scripts, events, sequencing | Decompiled GC room code (`src/st1/r1xx.cpp`), AEV/ITA door and event records, chapter ends. The PS2 enemy rules are ported into that C++ behind knobs (PS2_ENEMY_ROOMS, PS2_CH1_ENEMY) | `src/st1/`, `src/game/`; `tools/d367/ps2rooms/PS2_ENEMY_CH1.md` |
| Enemy AI, skeletons, motions | GC. PS2 meshes are bound to the GC skeleton exactly (`ps2_cast.py` docstring). Motions are GC archives (`em/*.drs`, MOTION_COLD_POOL) | `em/*.drs` (texture-prepared GC archives), `tools/prepare_enemy_motions.py` |
| Lighting metadata | World: baked offline, but `ps2_room_r4im.py` NORMAL groups use the **GC LIT cut-0** sun and sky (`tools/gc_lit_dump.py`, `gc_room_lit.py`). The black faces of 14 rooms use the PS2 rule (blackps2). Actors: ACTOR_PROBE_LIGHT and LEON_SOURCE_LIGHT evaluate the **GC light set** chosen by `LightSetModel` (room .lit + dynamic lights) | `docs/ACTOR_PROBE_LIGHT.md`, `docs/LEON_SOURCE_LIGHT.md`, `room/source_lighting.cpp` |
| Actor runtime ownership | The game's GC actor objects drive the native draw through the owner, transaction and registry layers. Objects and breakables still draw through the GC model path (`game/model_bridge.cpp`; STATIC_OBJ_BATCH merges the GX lists; breakables stay GC by decision) | `game/coarse_actor.cpp` + `coarse_actor_owner_{leon,ganado,pl08,registry}.inc`, `coarse_actor_transaction.inc`, `coarse_ganado_cast.cpp`, `src/game/trans.cpp` (sourceActorIdentity), `native_model_registry.mk` |
| GX emulation, OT | GX is a sink: `GXBegin` only counts (`game/platform/gx_stub.cpp:101`). GX state getters remain on hot paths; GC_CENSUS_TRIM (t15) inlines some and G1_* trims more. Anything not on a native path is invisible | `gx_stub.cpp`, `docs/lanes/t2exact.md`, `game/t2exact.mk` |
| Effects runtime | GC game code (`src/game/esp_*.cpp`, `eff_sys.cpp`) owns generators, Rnd and timing. Sprites draw natively only if `EspSpriteEligible` accepts them; the rest go to the GX sink. Recipe counts come from PS2 tables in code; frame counts and timing stay GC. Pictures are PS2 via FX_PS2_PACK except the GC-only ids (0x33/0xcb/0xf6 mist) and the "NONE" rows. About 20 classes have no DC path (water surfaces, filters, trails) | PARITY-CENSUS-20261014.md (sections A and D), `docs/lanes/fx12.md`, `game/platform/native_effect.cpp` |
| Screen filters | `FilterTrans` never runs on DC. The exceptions are FILTER00_DC and the Filter09 door freeze | PARITY-CENSUS |
| Sound | GC DSP banks converted to AICA at load. Only the weapon banks are prebuilt. Room banks do not fit from r103 on (silent footsteps and ambience) | ASSET-SOURCE-LEDGER-20261014.md G8, KNOWN_ISSUES.md |
| Movies | GC movies, converted offline | `/root/probe/d367-agents/cutscenes/movies-288x192-full` |
| UI / HUD | GC pictures | ledger |
| Scenery fallback | `MAINSCENARIO.re4mesh` (GC Standard scenery) is still staged per room. A failed PS2 open falls back to it (ledger G10: r104/r11b pre-open at chapter changes) | fixture, `native_ps2_world.cpp:676/701` |

## 7. Renderer changes and assets to reuse

Status key:
- **rel13** = in published test 13 (`tools/d367/test13/release-knobs.txt`) or in the build-r21.sh base.
- **t14** = test 14 candidate (unpublished).
- **t15** = in T15REC on t15/int.
- **t15 off** = merged into t15/int, default 0.
- **lane** = not in t15/int.

| Change | Knob | Main file(s) | Status |
|---|---|---|---|
| Native PS2 world path (R4IM v3 prelit meshes, cluster LOD, transform-once meshlet fast path, direct TA) | PS2_WORLD_MESH=1, PS2_WORLD_ROOMS=2, MESH_DIRECT=1, TA_DIRECT=1, MESH_LOD=1, MESH_CLIP_LEAN=1, PS2_WORLD_LEAN=23 | `game/platform/native_static.cpp` (MeshDraw, ps2_open, ps2_pass), `native_ps2_world.cpp`, `room/mesh_fastpath.hpp`, `room/instanced_mesh.hpp` | rel13 |
| Software-pipelined vertex transform ("vp transform_sched") | MESH_VP_SCHED=1 (2 = compare diagnostic) | `room/mesh_fastpath_sched.hpp`, generated by `tools/mesh_vp_sched.py` | rel13 (build-r21.sh) |
| Strip groups | PS2_STRIP_GROUPS=1 (needs PS2_WORLD_LEAN bit 2, MESH_STRIP_LEAN=1) | `native_static.cpp`; data `.r4sg` | rel13 (r101 only) |
| Native actor path + SH-4 skin kernels | NATIVE_ACTOR=1, NATIVE_ACTOR_FAST=1, _DIRECT, _SKIN, _SKIN_LAZY, _PRELIT, _LOD | `game/platform/native_actor_fast.cpp`, `game/platform/avk_sh4.S`, `game/platform/sk1_sh4.S`, `game/coarse_skin_sh4.S` | rel13 (build-r21.sh) |
| SH4ZAM render-only math | GAME_SH4ZAM=1 GAME_SH4ZAM_RENDER_ONLY=1 | `game/platform/sh4zam_direct.c` | t14 |
| Static object bake | STATIC_OBJ_BAKE=1 + PS2_PLACE_GATE=1 + baked package | `game/crowd.mk`, `model_bridge.cpp`, `native_static.cpp` | rel13 (r101) |
| Static object batch | STATIC_OBJ_BATCH=2 (+ STATIC_OBJ_BATCH_WORDCMP=1) | `game/crowd.mk`, `model_bridge.cpp` (sob::) | rel13 |
| Fog | NATIVE_FOG=1 (rel), HW_FOG_HAZE=1 (haze veil folded into the hardware fog table) | `game/hwfog.cpp`, `hwfog.mk`, `native_static.cpp` re4dc_fog_frame, `docs/HW_FOG_HAZE.md` | rel13 |
| Texture formats | TEX_PAL4_ALPHA=1 (PAL4 + alpha bank), VQ (offline `vq_pak.py`), TEX_WRAP_SAFE=1, FX_PS2_PACK=1, FX_FLIPBOOK=2 | `game30.mk`, `effects30.mk`, `native_ui.cpp` | rel13 |
| Texture pack | TEX_PACK=1 (`dc/tex.pak`) | `native_ui.cpp` texpack::, `tools/d367/texpack.py` | rel13 |
| Resident lists and VRAM | TEX_RESIDENT=1, ROOM_RESIDENT=1 (`dc/resident.bin`), PRELOAD_LARGE_FIRST, ROOM_CHANGE_EVICT=60, UI_FRAG_WINDOW=3, VRAM_ROOM_LOG=1; SS_HOLD_RESTORE + CORE_PIN=2 | `game/Makefile`, `native_ui.cpp`, `vram_pages.cpp` | rel13; CORE_PIN=2 is t15 |
| VRAM map | - | `C:\Game Dev\Emulators\VRAM-MAP-20261014.md`: the 8 MB layout, a texture pool of 2,567,424 B and the per-room sections. It is the only VRAM-MAP file | doc |
| Ganado LOD | GANADO_LOD=1 GANADO_LOD_LEVEL=2 GANADO_LOD_PACK=… | `game/ps2leon.mk`, `game/coarse_ganado_lod.inc` | t15 (lean gates pass; cross -0.65 ms console-fit MODELLED) |
| Leon LOD | LEON_LOD (default 0; user keeps level 0) | `ps2leon.mk`, `coarse_actor_leon_lod.inc` | t15 off |
| PS2 small cast | PS2_CAST_CH1=1 PS2_CAST_BOAT=1 ACTOR_PALETTE_BANK=40 NATIVE_MODEL_REGISTRY_POOL=1 | `game/native_model_registry.mk` | t15 |
| GC census trim | GC_CENSUS_TRIM=1 | `game/t2exact.mk`, `chunk_find.h` | t15 |
| World vertex ladder | WORLD_VERT=1, WORLD_VERT_LEVEL=n | lane worldvert `game/game30.mk:2751`, `native_static.cpp`; data `PRIV/worldvert-20261015/r101-v2` (`ps2-wv1.*` = L2-fixed). Flycast mean world vertices -28% (L2-fixed) | **lane, WIP, no gates run** (`docs/lanes/worldvert.md`, branch 713f9319) |
| World far LOD | WORLD_LOD=1 (+ WORLD_LOD_PROBE test knob) | lane worldlod `game30.mk:2734`; `tools/d367/worldlod/worldlod-rooms.json` | lane, not merged |

The worldvert L2-fixed regeneration commands are in `docs/lanes/worldvert.md`, section "Regenerate L2-fixed" (lane
tree):

```
B="/mnt/c/Game Dev/Emulators/re4-assets-private/crowd12-bake-20261015/r101-t13"; W=/root/probe/lanes-20261015/worldlod-work/walk/r101.json
python3 ps2_world_vert_ladder.py $B/ps2-world.re4mesh L2F.re4mesh --sidecar $B/ps2-world.r4pw --walk $W --protect-bins 0x2d --protect-last 14 --colour-guard 3 --colour-per-m 8 --uv-guard 0.03 --uv-per-m 0.05 --per-vertex --thin-frac 0.5 --thin-mm 2000 --max-error-mm 4000 --px 96 --report L2F.json
python3 ps2_strip_groups.py L2F.re4mesh $B/ps2-world.r4pw ps2-wv1.re4mesh ps2-wv1.r4sg
```

## 8. Where else to look

**Skills**
- `C:\Users\lambd\.claude\skills\re4-dreamcast-d367\` (SKILL.md, agents, references)
- `re4-dreamcast-testing\` (SKILL.md, scripts)
- `re4-room-firstpass\` (the per-room PS2 world first-pass routine)

**Docs in `C:\Game Dev\Emulators\`**
- CONVERSION-STATUS-20261015.md/.csv (per-room status, 15 columns)
- ASSET-SOURCE-LEDGER-20261014.md, PARITY-CENSUS-20261014.md
- PS2CAST-20261014.md, POC101-PLAN-AND-RESULTS.md
- WORLD-BUDGET-BY-ROOM-20261015.md, PERF-BACKLOG-PER-ROOM-20261015.md, PERF-BACKLOG-CH1-2-20261015.md
- ROOM-BUDGET-PROJECTION-20261015.md, HWMODEL-CALIBRATION-20261015.md
- TEST14-SCOPE.md, TEST15-SCOPE.md

**Evidence (`C:\Flycast-Evidence\re4-dreamcast\`)**
- leonlod-20261015, poc101-20261015, t15int-20261015, ps2cast-20261014, fullplay-20261015
- The hw model binaries and reference are on D: (section 5)

**Disk hygiene.** Under the 10-15 rule, raw traces are deleted after 24 h unless they are listed in keep.txt. Never
delete flycast.exe in evidence roots. Staged discs are rebuildable.
