# r100 scenery shading history — Build 20 / issue #32

Date: 2026-10-26. Source baseline: [`714589f6`](https://github.com/lamb2k/re4dc/commit/714589f6dcabb5a2c2f6e90e26ff36d88037d2dc),
`origin/t15/int`. This is a **docs-only investigation**, not a lighting fix or
acceptance of a new look.

## Finding and limits

The reported trees and ground belong first in the **world package / overlay /
fog investigation**. The active PS2 world path draws colours baked offline;
it does not evaluate the actor light probe on those vertices. The most specific
pre-Test-14 change capable of making dark scenery patches softer is r100's
155 vertex-alpha overlay faces moving from opaque to translucent. The r100
SMX colour correction and its re-keyed textures are the other material change
to check against the actual old disc. Fog and the live look preset can change
contrast without changing either package. None is proved to be the cause at
the reporter's exact camera.

Two tempting explanations are excluded by the source history:

- `LIGHT_CUT_HOLD` arrived on October 23, after the October 16 report, and its
  default room list is **11f**, not 100. It cannot explain the original report.
- The Test 12.1 `blackgc14p` → `blackps2w` world-bake switch **does not include
  r100**. Nor does the Test 13 `bake13` object append, which is r101 only.

The evidence below is public source, committed build records and the public
issue discussion. Historical private-run figures, CRCs and visual findings
are attributed to their committed records; this investigation did not
reproduce them. No game data, console, Flycast capture, matched original
image or private package was available here. In particular, the issue's
attached images were not used for pixel measurements.

### What issue #32 actually establishes

The [initial report](https://github.com/lamb2k/re4dc/issues/32) names **r12
Test 14**, real Dreamcast/GDEMU, and the area where the first villagers throw
a rock. The reporter supplied another old/new pair on
[October 21](https://github.com/lamb2k/re4dc/issues/32#issuecomment-6322259157).
The owner's [October 22 correction](https://github.com/lamb2k/re4dc/issues/32#issuecomment-6353588986)
describes dark shading on the old trees and ground becoming evenly bright,
and withdraws the earlier video-output hypothesis. The owner's
[October 19 note](https://github.com/lamb2k/re4dc/issues/32#issuecomment-6269754580)
says the location they thought was intended did not reproduce in Flycast.
That makes exact location/build identification necessary; it does not
disprove the hardware report.

The older photograph's exact program, asset set, look preset, camera cut and
position remain unidentified in that thread. Do not silently equate it to
the September prototype, a GameCube frame, Test 10, or the reviewed October 1
r100 bake.

## Which inputs can affect which pixels?

| Path | Source of colour / shading | What a changed light cut can do |
| --- | --- | --- |
| Original/source-rendered scenery | Source material, CLR0, selected GX light set and TEV state | Change live lighting and fog. |
| Early native GC scenery (`NATIVE_STATIC` / normal encoding) | Light each part on its first draw, then retain ARGB1555; instances share the result | The first-view light state matters; later light changes do not automatically re-bake it. |
| PS2 world (`PS2_WORLD_MESH`) | Offline prelit R4IM colours, texture gains and R4PW material/pass data | Does **not** re-light the stored world colours. Live fog and post effects can still change their final appearance. |
| Leon / Ganados / other actor paths | Their source-selected light records, actor kernels/probes, texture headroom and optional flat tiers | Can alter characters, some source-rendered objects, and probe-driven caster footprints. This is separate from baked world tree/ground colour. |

The contracts are explicit in
[`native_static.cpp`](../../game/platform/native_static.cpp) (`PS2_WORLD_MESH`,
`open`, `light_part`, `ps2_pass`),
[`instanced_mesh.hpp`](../../room/instanced_mesh.hpp) (`kColorArgb1555`,
`adopt_by_encoding`), and
[`ps2_room_r4im.py`](../../tools/ps2_room_r4im.py) (`light_world`, colour modes).
`SCENERY_ENCODING=1` adopts an already prelit package with parts marked lit;
it is not permission to run GX lighting on ARGB1555 as if it were a normal.
The live cut still selects environment fog/blur/contrast in
[`src/game/light.cpp`](../../../../src/game/light.cpp). Thus a cut-correlated
scenery change alone does not establish that the world was re-lit.

## History: source light sets and renderer changes

Dates below are commit author dates; cherry-pick/merge dates can be later.
Related exact-path changes are grouped. “Off” denotes the make default,
not the release recipe, which is recorded separately below.

| Date / commit | Switch or path | Change and relevance to the reported flat area |
| --- | --- | --- |
| Sep 19 — [`02f7f520`](https://github.com/lamb2k/re4dc/commit/02f7f520) | Early r100 room viewer | Translated r100 source lighting. This is ancestry of the room prototype, not evidence that the Test 14 PS2 world still evaluates that light loop. |
| Sep 20 — [`facc1954`](https://github.com/lamb2k/re4dc/commit/facc1954) | Source-model light selection | Restored per-model masks, source-order light selection, radius/box tests and the eight-light limit; included scenery light 19. The old checkpoint explicitly says source selection darkened much of the cabin versus the all-lights prototype, with a matched original trace still required. A real look change in that prototype; relevant only if the “old” image is traced to it. |
| Sep 20 — [`23bacfae`](https://github.com/lamb2k/re4dc/commit/23bacfae), [`d72f7dee`](https://github.com/lamb2k/re4dc/commit/d72f7dee), [`dafab55f`](https://github.com/lamb2k/re4dc/commit/dafab55f), [`000bdb4f`](https://github.com/lamb2k/re4dc/commit/000bdb4f), [`577c8ee0`](https://github.com/lamb2k/re4dc/commit/577c8ee0) | Fixed-room cache, dynamic-light specialization, actor light preparation | Reorganized lighting work and selected-light storage; the final prepared-actor-list commit records bit-identical evaluation. Do not present the preparation/cache work as a new source-light formula. These are prototype-era paths. |
| Sep 20 — [`dc9b6589`](https://github.com/lamb2k/re4dc/commit/dc9b6589) | Scene LIT selection | r101 obtained its own environment. r100 deliberately retained the hand transcription because the generated table included an additional slot-17 light. Commit records r100 unchanged. It did **not** silently enable that extra r100 light. |
| Sep 21–22 — [`d75144cf`](https://github.com/lamb2k/re4dc/commit/d75144cf), [`8bdb4dd7`](https://github.com/lamb2k/re4dc/commit/8bdb4dd7) | Source camera/LIT conversion and integrated selected-light renderer | Preserved camera cuts, per-type light work, byte colours, source brightness paths and source lighting authority. Conversion is an endian/layout operation, not a replacement light-selection policy. A malformed private conversion would need data evidence; this history does not establish one. |
| Sep 23 — [`ed9393c2`](https://github.com/lamb2k/re4dc/commit/ed9393c2) | `NATIVE_STATIC`, `NATIVE_MESH` (off) | Instanced GC scenery lit once at first draw, then stored as ARGB1555. Camera-relative lights are frozen at that first view and instances share a bake: an acknowledged visual compromise. Could explain a comparison with this old path, not an actor-probe regression in the current PS2 world. |
| Sep 28–29 — [`8745fac9`](https://github.com/lamb2k/re4dc/commit/8745fac9), [`09e61751`](https://github.com/lamb2k/re4dc/commit/09e61751), [`ad0c59d0`](https://github.com/lamb2k/re4dc/commit/ad0c59d0) | `PS2_WORLD_KERNEL`, `PS2_WORLD_MESH`, `PS2_WORLD_ROOMS`, `PS2_WORLD_COLOR_ALL` (off; recipe rooms=2) | Kernel selection preceded the R4IM prelit world route; r100/r103 were added Sep 29. NORMAL groups were baked with GC cut-0 sun/sky (r100 lights 0 and 4); COLOR groups used authored PS2 colours. `ROOMS=2` opens at first scenery bind and avoids loading displaced Standard scenery. **A genuine change of geometry/lighting representation**, potentially important if the older photo predates it. COLOR_ALL caches more packed colours in the older scalar/kernel consumer; it is not a new all-world lighting formula and is not selected in the release overrides. |
| Oct 4 — [`3bbf8966`](https://github.com/lamb2k/re4dc/commit/3bbf8966) | `SCENERY_ENCODING` (off; base recipe=1) | Honour normal, prelit, or oct-normal-plus-CLR0 encodings. Prelit parts are already lit; normal parts retain first-draw lighting. Prevents interpreting different colour formats as the same data, without changing the default converter outputs. |

### r100 world colours, texture gains and alpha — the material lineage

| Date / commit | Switch or data | Change and possible effect |
| --- | --- | --- |
| Oct 1 — [`3adf0d19`](https://github.com/lamb2k/re4dc/commit/3adf0d19) | Converter `--color-light gc` (default stays `authored`) | Optional GC light-set evaluation on PS2 COLOR geometry using derived normals and SMX LightSwitch. This was a review arm, not proof it shipped in r100. |
| Oct 1 — [`2e40bd4d`](https://github.com/lamb2k/re4dc/commit/2e40bd4d), [`7cc5b893`](https://github.com/lamb2k/re4dc/commit/7cc5b893) | `--color-light ps2`, `--tev-scale`, `--vc-clamp` | Optional `min(VC, clamp) × SMX colour × TEV scale`; above-unit light carried by per-texture gain. r100's x2/GX-clamp and GS-clamp bakes were compared. The historical notes describe the original bright hedge/silver birches and the effects of both material colour and fog. |
| Oct 1 — [`6023e3a8`](https://github.com/lamb2k/re4dc/commit/6023e3a8) | r100 **KEEP CURRENT** | The user's explicit decision retained the landed r100 package. Those October 1 r100 alternatives stayed review-only. Do not label them the Test 14 world. [Lane record](../lanes/ps2rooms.md). |
| Oct 11 — [`83c0a60d`](https://github.com/lamb2k/re4dc/commit/83c0a60d) | `PS2_VERTEX_ALPHA=1`; converter `--vertex-alpha tr4` (both off by default) | Moves non-blend-material faces with partial vertex alpha to TR and decodes marked parts as ARGB4444. Previously they were forced opaque, producing hard/dark shadow or ground layers. **r100 was initially excluded** because its interior-cell identity had to be rebuilt. The reported softer/gone r106 fence shadows in this commit concern r106, not proof of the r100 location. |
| Oct 12 — [`2f227605`](https://github.com/lamb2k/re4dc/commit/2f227605) | `--cutout-max-alpha 224`, `PS2_PT_CUTOUT` (off) | Binary-alpha cutouts such as PS2 textures with maximum alpha 239 become opaque-at-the-top ARGB1555 and move TR → PT. Changes pass/texture keys, not baked light evaluation. The r100 knob selects a matching cell identity. Potential silhouette/coverage difference, especially foliage. |
| Oct 13 — [`91e4dbf4`](https://github.com/lamb2k/re4dc/commit/91e4dbf4) | `PS2_R100_SMX` (off; requires PT cutouts), private `r100-smx` | Uses `--color-light ps2 --tev-scale 1 --vc-clamp 2.0`: PS2 vertex colour up to ~1.99 × SMX ColorRGB/255. The previous authored-only bake omitted this material multiplier; low-SMX groups were overbright. Re-keys 19/55 textures and separates two groups with differing placement SMX colours. **Intended to restore material shade**, not a global brightness increase. [Look record](../lanes/look.md). |
| Oct 14 — [`9391fe5a`](https://github.com/lamb2k/re4dc/commit/9391fe5a) | `PS2_R100_TR4` (off; requires SMX=1 and VERTEX_ALPHA=1), `r100tr4` data set | Stages the SMX package plus the **155 r100 vertex-alpha overlay faces** moved opaque → TR. Geometry/placements otherwise follow the SMX package. Directly capable of softening formerly solid dark patches; whether these faces cover the rock-throw view is unknown without the source data. |
| Oct 14–15 — [`ef9e659d`](https://github.com/lamb2k/re4dc/commit/ef9e659d), [`eae90009`](https://github.com/lamb2k/re4dc/commit/eae90009), [`3ea9d631`](https://github.com/lamb2k/re4dc/commit/3ea9d631), [`a41d0266`](https://github.com/lamb2k/re4dc/commit/a41d0266) | `--a0-ambient`, `--a0-light gc/ps2`; black-world sets | Added ambient/GC/PS2 bake rules for 0xa0000000 groups, then Test 12.1 selected PS2-formula worlds. **The staged sets exclude r100 and r101.** The formula history matters for other rooms but cannot by itself change this r100 package. [Black-world record](../lanes/t11-bk.md). |
| Oct 15 — [`12c0ce4b`](https://github.com/lamb2k/re4dc/commit/12c0ce4b), data definitions below | `STATIC_OBJ_BAKE`, `bake13` | Baked source objects can be appended to a world and remove actor-path draws. The actual `bake13` definition appends objects to **r101 only**. `objs12b` includes r100's separate object archive; do not conflate that archive with the native trees/ground world. |

**The r100 SMX/TR4 knobs select package identities, not an on-the-fly colour
formula.** Turning `PS2_R100_SMX` off while retaining the new world and textures
does not recreate the old bake. Turning `PS2_VERTEX_ALPHA` off against marked
TR4 colours misinterprets the data. Any comparison must carry the matching
mesh, R4PW, `.ids`, `interior.cell`, textures and relevant policy sidecars.
The bindings are part of correctness; do not bypass their checks to make an
old/new combination load.

The public staging script
[`test11/t11-fix.py`](../../tools/d367/test11/t11-fix.py) provides the useful
release chain:

| Recorded set | r100 consequence |
| --- | --- |
| `r100tr4` | Stages `ps2-world.re4mesh`, `.r4pw`, `.ids`, `interior.cell`, and new textures together from `r100-smx-tr4`. Historical mesh file CRC32 `4257dff0`; distinct R4IM header CRC `fb35ea9c`, R4PW body CRC `14118acd`; mesh 1,537,920 bytes. These are historical identifiers, not a claim that today's mip-adjusted sidecars retain them. |
| `T12_DATA` | Explicitly includes `r100tr4`. |
| `T121_DATA = T12_DATA + blackps2w + t121tex` | Black-world list is r102–r10b, r117–r118, r11a–r11b; r100 stays on its dedicated package. The shared texture archive also changes, so verify each referenced r100 key, not just its filename. |
| `T13_DATA = T121_DATA + objs13d + ashley13 + bake13 + t13tex` | `bake13` touches r101. r100 still needs its complete `r100tr4` lineage. |
| `T14_DATA = T13_DATA + res14r3` | Adds the resident list, not a new r100 colour formula. The first report naming Test 14 does not prove the regression first appeared in Test 14. |

### Actor lighting and light-cut retention

| Date / commit | Knob / default | Effect and r100 interpretation |
| --- | --- | --- |
| Sep 23–24 — [`520e8a0e`](https://github.com/lamb2k/re4dc/commit/520e8a0e), [`9547dc85`](https://github.com/lamb2k/re4dc/commit/9547dc85) | `NATIVE_ACTOR_PRELIT`, `CROWD_LOD`, `CROWD_FLAT` (off) | Actor prelit/LOD tiers; `CROWD_FLAT=1` makes Ganado near parts use a folded colour too. Leon, weapons and objects remain separately lit. “Flat Ganados” is not “flat world.” |
| Oct 7 — [`abd0853b`](https://github.com/lamb2k/re4dc/commit/abd0853b) | Shared prelit actor path / weapon beam | Shares actor lighting and restores the weapon beam; does not rewrite PS2 world colours. |
| Oct 13–14 — [`644e7545`](https://github.com/lamb2k/re4dc/commit/644e7545), [`c0e185c7`](https://github.com/lamb2k/re4dc/commit/c0e185c7) | `LEON_SOURCE_LIGHT` (off) | Restores source light records and per-part normal basis for Leon's native owner path. Character change. |
| Oct 14 — [`329759a3`](https://github.com/lamb2k/re4dc/commit/329759a3), [`da104d9d`](https://github.com/lamb2k/re4dc/commit/da104d9d) | `ACTOR_PROBE_LIGHT=0/1/2` (0) | Fits selected lights once per actor per frame to ambient plus one dominant direction. 1 covers Leon; 2 adds Ganados. Shared API supplies direction/coherence to shadows. Does not sample or overwrite prelit world vertices. |
| Oct 14 — [`25cc619d`](https://github.com/lamb2k/re4dc/commit/25cc619d), [`dc03da35`](https://github.com/lamb2k/re4dc/commit/dc03da35), [`885e9183`](https://github.com/lamb2k/re4dc/commit/885e9183) | `LEON_LIGHT_HEADROOM`, `LEON_LIGHT_FILL` (0) | Matched 2× Leon textures and 0.5× vertex light permit highlights above PVR's 1× colour cap; compensation also reaches non-owner Leon draws. Camera-side fill brightens Leon. A mismatched texture/binary pair can change Leon, but this is not a tree/ground bake. |
| Oct 14 — [`2296ef6c`](https://github.com/lamb2k/re4dc/commit/2296ef6c) | `MV_SHADOWS` / `SHADOW_MV` (off) | Cheap-shadow footprints stretch away from each actor's probe direction. Can change local ground shadows under characters; cannot reconstruct authored tree shading over the whole forest. Test 14 has MV_SHADOWS=1. |
| Oct 16 — [`de25aabe`](https://github.com/lamb2k/re4dc/commit/de25aabe), [`bc258800`](https://github.com/lamb2k/re4dc/commit/bc258800) | `GANADO_LIT` (off), recipe probe=2 / nearest=0 | Villager colours follow the room probe while remaining flat per part at `GANADO_LIT_NEAREST=0`; optional nearest actors can be per-vertex lit. Later than Test 14, and still actor scope. |
| Oct 23 — [`dfc6e53a`](https://github.com/lamb2k/re4dc/commit/dfc6e53a), [`58b65faa`](https://github.com/lamb2k/re4dc/commit/58b65faa), [`eb1fe953`](https://github.com/lamb2k/re4dc/commit/eb1fe953) | `LIGHT_CUT_LOG=0`, `LIGHT_CUT_HOLD=0`, `LIGHT_CUT_HOLD_ROOMS=11f`; recipe HOLD=1 | Diagnostic logs cuts, environment and camera areas. HOLD retains the last cut when Leon leaves all camera areas instead of selecting cut 0, addressing r11f loft/crate lighting. It does not affect r100 under the default room mask and postdates the initial report. Extending the mask to r100 would be a new approximation, not this investigation. |
| Oct 23–25 — [`cb682b07`](https://github.com/lamb2k/re4dc/commit/cb682b07), [`bc9585e8`](https://github.com/lamb2k/re4dc/commit/bc9585e8) | `FLASHLIGHT_POOL` (off; later recipe on) | Adds an additive pool only when room light data attaches a qualifying torch to Leon (night-room examples r11d/r11e). A later local light patch, not the original loss of broad daytime scenery shading. |

Current definitions:
[`crowd.mk`](../../game/crowd.mk),
[`mendezfx.mk`](../../game/mendezfx.mk),
[`native_actor_fast.cpp`](../../game/platform/native_actor_fast.cpp),
[`cam_ctrl.cpp`](../../../../src/game/cam_ctrl.cpp).

### Fog, mist and final colour

| Date / commit | Knob / default | Effect and whether it can flatten the view |
| --- | --- | --- |
| Sep 23 — [`64b25dd3`](https://github.com/lamb2k/re4dc/commit/64b25dd3) | `NATIVE_FOG=0`, `FOG_FAR=0`, scenery LOD | Converts captured GX fog to the PVR fog table and ramps to the draw far plane; recipe later caps at 25,000 mm. Yes: a pale near-ending fog ramp can lift dark distant pixels and reduce contrast. LOD changes distant detail, not the light formula. |
| Oct 4 — [`44985fb7`](https://github.com/lamb2k/re4dc/commit/44985fb7) | `PS2_WORLD_FOG_SOURCE=0`; base recipe=1 | Latches whether source GX fog was enabled at scenery draw and applies that to OP/PT/TR headers. Off always used the table, causing flat fog-colour worlds in fog-disabled rooms. r100 outdoor fog is normally enabled; a camera-cut/state bug needs a log, not assumption from another room. |
| Oct 5–6 — [`88f30aaf`](https://github.com/lamb2k/re4dc/commit/88f30aaf), [`11dea6e2`](https://github.com/lamb2k/re4dc/commit/11dea6e2) | `EFFECT_PS2_HAZE`, `EFFECT_PS2_STREAK`, `EFFECT_FADE_CLAMP` (off; recipe haze=1, streak=2) | PS2-sized/coloured haze subset; replaces r100 house streaks with light shafts. Near-fade clamp fixes wrapped negative alpha. Haze can alter contrast; indoor window shafts are not direct evidence about an outdoor tree. Generators/RNG remain source-owned. |
| Oct 10–11 — [`702c0bfb`](https://github.com/lamb2k/re4dc/commit/702c0bfb), [`7ab6bd2f`](https://github.com/lamb2k/re4dc/commit/7ab6bd2f), [`9a497fcf`](https://github.com/lamb2k/re4dc/commit/9a497fcf) | `FOG_CURVE`, `FOG_RGB_PCT`, `FOG_FAR_CAP`, `SKY_FAR`, `LOOK_TOGGLE`, `FILTER00_DC` (off; FOG_CAP defaults 100) | Adds alternate fog/sky/grade and then two test presets. A boots current fog; B uses source curve, 70% fog RGB, far sky and a separate r100 outdoor RGB multiply. The latter uses `0xffdee3d7`, about 0.87/0.89/0.84. `FILTER00_DC` follows room blur/contrast: r100's own data does **not** enable it. A/B still differ in r100 because of fog and the explicit grade. An unrecorded preset is a credible comparison confound. |
| Oct 12 — [`cd45a475`](https://github.com/lamb2k/re4dc/commit/cd45a475), [`0744d53a`](https://github.com/lamb2k/re4dc/commit/0744d53a) | `EFFECT_HAZE_LEAN=0`, diagnostic toggle=0; Test 14=3 | Bit 1 suppresses GC-only mist sheets. Bit 2/M3 transfers a mean haze veil into the table and reduces sprites; r100 table veil 0.034 over 1–5 m, with an indoor fade, while a 1-in-16 subset remains at adjusted alpha. Replacing patchy sprites with a broad veil can reduce local contrast. |
| Oct 14 — [`404e20f4`](https://github.com/lamb2k/re4dc/commit/404e20f4), [`005f333f`](https://github.com/lamb2k/re4dc/commit/005f333f) | `HW_FOG_HAZE=0`; Test 14=1 | r100 row replaces the remaining distant M3 subset beyond 3 m; box depth 5 m, additional mean veil 0.010. M3's existing veil remains. A possible atmospheric contributor, but this small extra row alone is weak evidence for severe uniform loss of near-surface shade. |
| Oct 15 — [`4f130362`](https://github.com/lamb2k/re4dc/commit/4f130362), [`c897acb0`](https://github.com/lamb2k/re4dc/commit/c897acb0) | Night-room HW-fog rows; `FOG_OFF_CLEAR=0` | Removed r119/r11b fog replacements after a hardware look discrepancy; no r100 row removed. FOG_OFF_CLEAR initializes a clear table before the first fog-on frame, motivated by castle entry. Useful evidence that emulator stills do not settle every fog issue, not an identified r100 fix. |
| Oct 16 — [`5744c9a5`](https://github.com/lamb2k/re4dc/commit/5744c9a5), [`b16464df`](https://github.com/lamb2k/re4dc/commit/b16464df), [`ce87185f`](https://github.com/lamb2k/re4dc/commit/ce87185f) | `VIEW_DIST_OPTION=0`, `FAR_SHELL=0` | Player Full/Near/Short distance choices; stops the shortened-distance fog inside houses and preserves lake horizons. Far-shell prototype draws simplified distant geometry. All later than Test 14. Current view setting must be logged because it changes fog/culling; it is not a diagnosis of the initial report. |
| Oct 16–19 — [`0a4ef1b4`](https://github.com/lamb2k/re4dc/commit/0a4ef1b4), [`563694a0`](https://github.com/lamb2k/re4dc/commit/563694a0), [`72702244`](https://github.com/lamb2k/re4dc/commit/72702244) | `HAZE_SPRITE_CUT=0`, `FX_MIST_PS2=0` | Cut haze/mist sprite draws while retaining the table veil; later avoid work for already-undrawn GC mist sheets while preserving dormant pool slots. `HAZE_SPRITE_CUT=1` does **not** mean fog-free. Later release comparisons need these states pinned. |

Fog/grade source:
[`post30.mk`](../../game/post30.mk),
[`effects30.mk`](../../game/effects30.mk),
[`hwfog.cpp`](../../game/hwfog.cpp),
[`hwfog.mk`](../../game/hwfog.mk),
[`native_static.cpp`](../../game/platform/native_static.cpp) (`re4dc_looks`,
`re4dc_look_grade_argb`, `re4dc_fog_frame`), and
[`native_ui.cpp`](../../game/platform/native_ui.cpp) (`re4dc_look_grade_post`,
`re4dc_post_filter00`). The grade tests the characteristic r100 outdoor fog
colour/start; the house cuts do not get that same multiply.

### World selection, pass ownership and later optimizations

These can remove or move a surface, change its pass, or select a different
LOD. They are not additional diffuse-light models.

| Date / commit | Knob family / default | Relevance and chronology |
| --- | --- | --- |
| Oct 4 — [`4f1fb522`](https://github.com/lamb2k/re4dc/commit/4f1fb522), [`4b3966e5`](https://github.com/lamb2k/re4dc/commit/4b3966e5) | `PS2_WORLD_REGISTRY`, `PS2_OPEN_READ` (off; base recipe=1) | Select validated room-package listings and use the aligned whole-file reader. A failed open can leave a different scenery path or an undrawn world, so retain open/identity logs. These switches do not calculate colours. |
| Oct 5 — [`7482db7b`](https://github.com/lamb2k/re4dc/commit/7482db7b) | `PS2_WORLD_HDR_CACHE`, `MESH_CLIP_ACCEPT`, `PS2_PASS_MASK` (off), `PS2_FOLIAGE_FAR=0` | First three aim to preserve drawing with less setup; last deliberately cuts PT/TR beyond a distance. If an overlay is missing, inspect the pass/header/placement path, but do not infer a lighting change from caching alone. |
| Oct 5–7 — [`0133849f`](https://github.com/lamb2k/re4dc/commit/0133849f), [`9b871f26`](https://github.com/lamb2k/re4dc/commit/9b871f26) | `PS2_INTERIOR_CULL` (off), owner integration | Reject hidden outside world while the camera is inside r100's first house; bound to the package and cell. The reported outside area should not use an interior cell. Check inside/outside state at the exact view if geometry vanishes. |
| Oct 6 — [`98ef215d`](https://github.com/lamb2k/re4dc/commit/98ef215d), [`c36a08cc`](https://github.com/lamb2k/re4dc/commit/c36a08cc) | `PS2_WORLD_DYNAMIC`, `PS2_WORLD_PARTS` (off; base recipe=1) | `.ids` connects placements to live scenery hide/root transforms; child-animation fallback uses source hierarchy. r100 gate swaps can change visibility. This is a possible **missing-surface** mechanism, not a bake brightness change. The `.ids` CRC must match R4PW. |
| Oct 9 / 13 — [`63681d91`](https://github.com/lamb2k/re4dc/commit/63681d91), [`72879767`](https://github.com/lamb2k/re4dc/commit/72879767) | `WORLD_AUTOSORT` (on for PS2-world + ordered-UI profile), `PT_BLEND_FIX=0` | Correct world transparency ordering while preserving UI/planar layers; fix PT headers to use SRCALPHA/INVSRCALPHA rather than ONE/ZERO. The latter addresses **r100 branch tips drawn as solid cards on real PVR hardware**. Test 14 explicitly enables it. Both affect layer/coverage appearance, not prelit RGB; include blend/list state in overlay receipts. |
| Oct 13–14 — [`f9362b85`](https://github.com/lamb2k/re4dc/commit/f9362b85), [`68060836`](https://github.com/lamb2k/re4dc/commit/68060836) | `PS2_WORLD_SOURCE_OWNER`, source texture preparation (off) | Bounded r200 event/world ownership, UV phases and late texture prep. Not a general r100 light-set change. |
| Oct 14 — [`78c03a11`](https://github.com/lamb2k/re4dc/commit/78c03a11), [`25b51519`](https://github.com/lamb2k/re4dc/commit/25b51519), [`5faaf9e7`](https://github.com/lamb2k/re4dc/commit/5faaf9e7) | `PS2_WORLD_LEAN=0`, `PS2_STRIP_GROUPS=0`; recipe 23 / 1 | World-space pretests, inside propagation, prime reuse, dynamic lookup shortcut and crossed-plane lists. Intended to preserve selected strips/colours; diagnostics compare skipped tests. `sg101` data is r101. An implementation defect would need a matched emitted-part/strip difference; the knob names do not imply relighting. |
| Oct 14 — [`c9f68834`](https://github.com/lamb2k/re4dc/commit/c9f68834) | `WORLD_HOLE_DIAG=0`, `WORLD_HOLE_FIX=0`; Test 14 FIX=1 | Logs refused world parts. Queue-full translucent model parts are dropped individually instead of aborting the frame and refusing all later world PT/TR. The motivating evidence is r117/r119, not r100. Any missing overlay at the reported view needs actual refusal/drop counts; the existing diagnostic supplies them. |
| Oct 15 — [`dfc4199d`](https://github.com/lamb2k/re4dc/commit/dfc4199d), [`77d8be2a`](https://github.com/lamb2k/re4dc/commit/77d8be2a) | `PS2_PLACE_GATE`, `PS2_AREA_HIDE` (off) | Gate appended game-owned placements; hide r107's specified area groups. The latter is room-specific and does not rewrite r100 shading. |
| Oct 16 — [`af1f46d3`](https://github.com/lamb2k/re4dc/commit/af1f46d3), [`afb98788`](https://github.com/lamb2k/re4dc/commit/afb98788), [`85128754`](https://github.com/lamb2k/re4dc/commit/85128754) | `MIST_CUT` / `FOLIAGE_TRIM` (unset) | Diagnostic MIST_CUT bit 16 removes **all TR world**, including shadow/ground overlays: never a safe “mist only” fix. Initial Foliage Off did that too; corrected Off cuts only listed card classes 1–4 and retains surfaces/unlisted keys. These changes postdate the Test 14 program. |
| Oct 17 — [`58986f82`](https://github.com/lamb2k/re4dc/commit/58986f82), [`410ba515`](https://github.com/lamb2k/re4dc/commit/410ba515) | `FOLIAGE_NEAR_FIX=0`, `TRANS_POLICY` unset/0 | Fixed cards moved TR → PT being skipped by the placement pass mask; r100 woods evidence is recorded. TRANS_POLICY binds per-part alpha classes to R4PW and changes qualifying flat/card passes. Current mask 3 is FLAT + CARD, **not** the reserved vertex-alpha bit. Relevant to later appearance, not original Test 14. |
| Oct 19 — [`ead3c5fa`](https://github.com/lamb2k/re4dc/commit/ead3c5fa) | `SCENERY_FAR_LOD=0`; later recipe=4 | Permits coarser world LODs. Can remove distant geometric/colour detail; cannot be the original Test 14 regression. |
| Oct 21–23 — [`42c1c32e`](https://github.com/lamb2k/re4dc/commit/42c1c32e), [`f22e9c9e`](https://github.com/lamb2k/re4dc/commit/f22e9c9e), [`849f98ac`](https://github.com/lamb2k/re4dc/commit/849f98ac), [`a5de753a`](https://github.com/lamb2k/re4dc/commit/a5de753a) | `PS2_WORLD_ROOT_POSE`, `PS2_WORLD_NONEMPTY_LOD`, `PS2_WORLD_SOURCE_TEX_MIP` (off; Test 24=1) | Keeps one-root animated scenery on PS2 geometry and guards empty levels; root-pose recipe was removed after an r100 s30 movie-cell problem, then reintroduced with corrected sizing. Source mip prep fixes r200 late texture admission. Later visibility/lifetime work, not an original forest colour edit. |
| Oct 22–24 — [`48f71838`](https://github.com/lamb2k/re4dc/commit/48f71838), [`4687e643`](https://github.com/lamb2k/re4dc/commit/4687e643) | `WORLD_RECT21`, texture mip gates, `FOLIAGE_MIP24` (off; Test 24 enabled) | `mip22/b` re-keys R4PW material textures and remaps resident keys; `fol24` adds coverage-preserving foliage/cutout mip chains. The data definitions do not replace r100's mesh colour stream. They can change distant texture/alpha detail and require current sidecar bindings, but postdate Test 14. Do not assume a historical R4PW CRC still identifies today's complete bundle. |
| Oct 19–26 — [`de39771e`](https://github.com/lamb2k/re4dc/commit/de39771e), [`2747f928`](https://github.com/lamb2k/re4dc/commit/2747f928), [`b8077972`](https://github.com/lamb2k/re4dc/commit/b8077972), [`451bed6f`](https://github.com/lamb2k/re4dc/commit/451bed6f), [`54f1ddd3`](https://github.com/lamb2k/re4dc/commit/54f1ddd3) | `SCENERY_CHUNK`, select/replay/submit trims, `SCENERY_STREAM` (off) | Reorganize the same world work and traffic; stream check compares corner/screens against the old path. No intentional colour change. All later than the original report. Package-binding fixes and world-census experiments are likewise not evidence of new baked lighting. |

## Recorded recipe state: avoid comparing labels alone

The release files are **ordered make overrides**; last value wins. They are
not complete dumps of all inherited defaults.
[`test14/release-knobs.txt`](../../tools/d367/test14/release-knobs.txt) names
source `e2048df6`, tag `test-e2048df6-20261015`.
[`test24/release-knobs.txt`](../../tools/d367/test24/release-knobs.txt) names
tag `test-608abf36-20261025` and is the latest committed release-knob record
found in this checkout. Test 25 recipe work on the branch is not a substitute
for an exact released-disc manifest.

| Setting | Test 14 recorded override | Test 24 recorded override |
| --- | --- | --- |
| `PS2_R100_SMX`, `PS2_R100_TR4`, `PS2_VERTEX_ALPHA`, `PS2_PT_CUTOUT` | 1 / 1 / 1 / 1 | 1 / 1 / 1 / 1 |
| `PT_BLEND_FIX`, `WORLD_HOLE_FIX` | 1 / 1 | 1 / 1 |
| `PS2_WORLD_LEAN`, `PS2_STRIP_GROUPS` | 23 / 1 | 23 / 1 |
| `ACTOR_PROBE_LIGHT`, `LEON_SOURCE_LIGHT`, `LEON_LIGHT_HEADROOM`, `LEON_LIGHT_FILL` | 1 / 1 / 1 / 45 | 2 / 1 / 1 / 45 |
| `GANADO_LIT`, `GANADO_LIT_NEAREST` | Not listed | 1 / 0 |
| `MV_SHADOWS` | 1 | 1 |
| `LOOK_TOGGLE`, `FILTER00_DC` | 1 / 1 | 1 / 1; runtime preset still matters |
| `EFFECT_HAZE_LEAN`, `HW_FOG_HAZE` | 3 / 1 | 3 / 1 |
| `HAZE_SPRITE_CUT`, `FX_MIST_PS2` | Not listed | 1 / 1 |
| `VIEW_DIST_OPTION`, `VIEW_DIST_BOOT` | Not listed | 1 / 1; read the live choice |
| `FOLIAGE_TRIM`, `FOLIAGE_NEAR_FIX`, `TRANS_POLICY` | Not listed | 2 / 1 / 3; read the live foliage choice |
| `SCENERY_FAR_LOD` | Not listed | 4 |
| `LIGHT_CUT_HOLD` | Not listed; not yet implemented | 1; no room override, so `11f` default |

The inherited [`build-r21.sh`](../../tools/d367/build-r21.sh) base selects
`NATIVE_FOG=1`, `FOG_FAR=25000`, `PS2_WORLD_DRAW=1`, `PS2_WORLD_KERNEL=0`,
`PS2_WORLD_MESH=1`, `PS2_WORLD_ROOMS=2`, `SCENERY_ENCODING=1`,
`PS2_WORLD_FOG_SOURCE=1`, `PS2_WORLD_DYNAMIC=1`, and `PS2_WORLD_PARTS=1`.
For a historical reproduction use that release's source/build chain, not
today's base script with an old override list. A packaged source commit and
its private files together define the comparison.

## Search and verification scope

This history followed commits reachable from the pinned base above, from
the September 19 source-light translation through October 26. The search
used non-merge commit subjects for `light`, `fog`, `prelit`, `shad`, `r100`,
`haze`, `mist`, `SMX`, `TR4`, `bake13`, and `LIGHT_CUT`, then path histories
and targeted full diffs for the actual implementations. Relevant paths:

- `src/game/light.cpp`, `cam_ctrl.cpp`, `scroll.cpp`, `trans.cpp`, `esp_sub.cpp`;
- `port/dreamcast/game/platform/native_static.cpp`, `native_ps2_world.cpp`,
  `native_ui.cpp`, `native_actor_fast.cpp`, `mv_shadow.cpp`, plus the make files;
- `port/dreamcast/room` lighting/mesh readers, `tools/ps2_room_r4im.py`,
  `convert_room_bins.py`, `ps2_room_ids.py`, release scripts/data definitions;
- committed `lanes/look.md`, `lanes/ps2rooms.md`, `lanes/t11-bk.md`,
  `ACTOR_PROBE_LIGHT.md`, `HW_FOG_HAZE.md`, `MIST_CUT.md`, and release-knob files.

This is a catalogue of the relevant semantic changes found by that search,
not a claim to audit every renderer instruction, every private export or
every historical release asset. Duplicate cherry-picks, purely mechanical
refactors, and unrelated room-only lighting changes are grouped or excluded
with their scope stated. Old lane notes describe their date's state; where a
later patch supersedes them, this report follows the patch and current code.

Build 20 modifies this document and its queue handback only. **Target heap-4
delta 0 B; target traffic delta 0 bytes; target cycles/frame delta 0; expected
frame-time delta 0 ms by docs-only scope.** These are change-scope facts, not
hardware measurements. No binary, data package, recipe, default or new knob
is changed. Local validation is limited to source/commit/reference checks
and `git diff --check`; a docs-only change does not need synthetic gameplay
tests or imply that the rendering issue passed.

## Three leading causes and the owner's discriminating runs

### 1. Changed or missing world shadow/ground overlays

**Why this leads the list:** the r100 TR4 transition predates Test 14 and
explicitly changes 155 partial-alpha faces from solid opaque patches to soft
blends. That mechanism directly fits “old dark patches are less dark now.”
It could be the intended correction of over-opaque shadows, a bad package /
decoder pairing, or missing submitted overlays. The history cannot choose
between these possibilities, nor show that those 155 faces cover the exact
reported patch. Later Foliage/TRANS changes can compound it but cannot cause
the first Test 14 report.

**Run:** first recover the reporter's exact fixed camera/position and older
build. Use that build and original Test 14 as matched references, with
identical look preset A, rendering resolution, camera cut, simulation tick
and actors. On the owner's local assets, identify the BIN/placement/parts
covering the affected trees/ground and list their old/new OP/PT/TR pass,
vertex-alpha range and texture keys. In a Test-14-source comparison, stage
the complete **SMX-only** bundle with its original cell/IDs/textures and
`PS2_R100_SMX=1 PS2_R100_TR4=0`, then the complete **SMX+TR4** bundle with
`PS2_R100_SMX=1 PS2_R100_TR4=1 PS2_VERTEX_ALPHA=1`; keep
`PS2_PT_CUTOUT=1` and the same remaining recipe. Keep VERTEX_ALPHA=1 in the
SMX-only arm too; unmarked parts retain their normal decoding. Record image,
disc manifest and emitted part/pass counts. Use `WORLD_HOLE_DIAG=1` in both
diagnostic arms and retain `WHD`/`WHDSUM` refusals and `WHFIX` drops, together
with texture-load and interior-cell/ID acceptance logs. A restored dark patch mapping
exactly to those overlays identifies the mechanism; compare its alpha to
the PS2 source before deciding whether “restore opaque” would be correct.

If only a current release reproduces, add a same-source run with the live
Foliage choice **Full**, `TRANS_POLICY=0`, `SCENERY_FAR_LOD=0`, and Full view
distance, then restore one setting at a time. That is a diagnostic arm,
not a new default. Do not use MIST_CUT bit 16 as a mist-only comparison.

### 2. Different baked material colour or mismatched texture gain/package

**Why:** the prelit world owns the static tree/ground shade; the SMX fix
changed its colour bytes and 19 texture keys. A missing SMX term, clipping
of above-unit light, wrong texture for a gain, or a different old bake can
flatten material contrast. However, the documented SMX84 example should
**darken** authored 1.99 to about 0.66, so the correct SMX correction alone
is not evidence for a broad brightening bug. The October 1 x2 bake was not
adopted, and `blackps2w` is not an r100 candidate.

**Run:** hash and inventory the actual old, Test 14 and current r100 bundles,
including `.re4mesh`, `.r4pw`, `.ids`, `interior.cell`, optional policy files,
and every referenced texture payload inside the archive. Check all existing
identity validators; do not reseal a mismatched bundle just to force it to
load. Compare corresponding parts' pre-quantized RGB, ARGB1555 values,
SMX ColorRGB, colour mode/TEV/clamp arguments, per-texture gain and clipped
corner counts. Keep those measurements separate from screenshot brightness.
Then make a local matched **PT-cutout authored** versus **PT-cutout SMX-only**
pair, using their correct complete data/cell bundles and identity knobs,
with `PS2_PT_CUTOUT=1 PS2_R100_TR4=0 PS2_VERTEX_ALPHA=1` in both, and
`PS2_R100_SMX=0` for authored versus `1` for SMX, before adding TR4 as in
run 1. This isolates material colour from alpha.
Retain camera, fog and textures appropriate to each recorded bake. If colour
and gain-adjusted texels agree at the affected parts, this candidate falls
behind pass coverage and atmosphere. No runtime actor-light rewrite is needed
to perform this test.

### 3. Fog/haze replacement or a different live look/view state

**Why:** the code contains a broad M3 fog-table veil, an additional r100 HW
fog veil and explicit A/B fog/grade differences. These can wash contrast out
while baked RGB is identical. Their screen/depth footprint differs from a
missing fixed shadow patch. The small HW row alone should not be assumed
responsible for a large near-ground loss.

**Run:** on the same Test 14 source/assets and fixed view, log preset, camera
cut, source fog enable/colour/start/end, effective far plane and table/haze
state. Capture A and B with `LOOK_TOGGLE=1` and its on-screen label, then
return to A. B changes several things at once and is a look check, not an
isolation of one fog term. For the HW replacement alone, use the existing
`HW_FOG_HAZE_TOGGLE=1 HW_FOG_HAZE=1 LOOK_TOGGLE=1
EFFECT_HAZE_LEAN_TOGGLE=0`; the X + D-pad up + START chord selects off/on.
Wait for the fog state to settle and compare the same tick/camera in repeated
runs. This removes only the HW replacement, **not M3**. If unresolved,
compare otherwise identical binaries with `EFFECT_HAZE_LEAN=3` versus `1`
and `HW_FOG_HAZE=0` in both; that isolates M3 while retaining the GC-sheet
suppression bit. Do not combine both diagnostic toggles on their shared chord.

Add `LIGHT_CUT_LOG=1` to these owner diagnostic builds if needed; leave
`LIGHT_CUT_HOLD` and its room list at the release settings. A logged cut change
can explain fog or actor changes without re-lighting the world. Record
surface-local contrast at near and far depths, not just whole-frame mean
brightness. A depth-dependent wash that follows the table and leaves the
same world parts submitted supports atmosphere; missing fixed patches with
stable fog supports run 1. The result and exact disc/knob hashes belong back
in the queue before any rendering change is proposed.
