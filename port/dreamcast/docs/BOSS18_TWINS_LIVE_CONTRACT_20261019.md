# r224 live detail and auxiliary contracts — 2026-10-19 (H-038)

The user-approved selection stays unchanged: protected type1, full type3 and both full parents. The source audit identifies what the remaining full-grab, material and auxiliary gates must establish. No model, selector, runtime, recipe, guard, game build or Flycast run was changed.

## Full strangle detail is not the whole grab

The current registry_lod_want function selects the full parent only when global Status_flg[1] has bit 0x10000000. Otherwise it selects the matching gameplay level after proving its source roles. The original pGS macro aliases pG; its struct-view spelling does not create another game state.

Original em2b source:

- Catch, routine 0x11, detects hand contact and calls SetPlDamage with plem2b_CatchHand (em2b.cpp2436). That player callback holds Leon on hand part 0xA and sets global bit 0x8000 (2570..2613).
- SetPlDamage installs custom player routine 4 (pl_sub.cpp301). beginDamage interrupts the player; it does not request the selector's 0x10000000 bit (pl_class.cpp1037/1125).
- Strangle, routine 0x12, explicitly sets 0x10000000 and runs the button-mash escape (em2b.cpp2470..2559). The parasite climb/attack QTE also sets it (3290..3437). Those full-detail requests match the current predicate.

Therefore the predicate **does not guarantee full detail for the preceding hand-held callback** when only 0x8000 is set. Ten checks execute the actual unchanged function, extracted verbatim, with source-role proof stubbed explicitly. Under ASan/UBSan, gameplay and hand-only states select type1's protected level; strangle/event states select full; type3 stays full. Unproved roles and incompatible info counts keep full. All ten pass with clean sanitizer stderr.

This is a source-level policy gap and host predicate observation, not a captured reduced grab or a whole-game regression claim. H-020's opening full-to-gameplay transition remains valid. Actual normal grab entry, hold, QTE, release and death still require a state-bound native draw check. The existing renderer owner must route full detail from the original live interaction, without changing AI, damage, callbacks or game flags merely to satisfy a render selector. No broad custom-damage rule was implemented here.

The same em2b callback family is shared by the settled r119/r11e bodies. Their choices remain settled; retaining full parents does not alone establish every live transition. Partner-catching code is also recorded in the pinned source, but no partner is assumed present in r224.

## r224 hole texture effect remains active

em2bTexrenderInit (6521) obtains Ctrl12GetTexRenderEm2b, sets a 64×64 render target and source table entry 0xF7. HoleAtk (2955..2980) installs that table on body and added head, with blend ratio 255 and blend type 2 when its manager exists.

The current certificate permits an installed table only while idle: flagsDC 4, ratio 0, type 0. coarse_actor_material.inc292..293 refuses nonzero ratio/type as LiveModifier. The hole's active state cannot be certified by the earlier idle-table/body window. This is an explicit material contract for the existing P2 owner, not permission to bypass the modifier check or bake a fixed replacement. Actual source effect, lighting, phases and source hide/death ordering remain required.

## Separate owners and complete source support

| Source object | Original creation and identity | Required qualification |
|---|---|---|
| Three chains | ObjMgr.createBack(0x1d), BIN13/TPL14, nine parts; parent parts 0x3b/0x40/0x41 | Original cloth, attachment, fade/lifetime, lighting, complete flag7 diffuse0/opacity1/bump2 behavior |
| Parasite | SetObj16 D6/D7, object16/type8, 25 parts, attached to part3e | Source growth, hit/weak/motion/effect and owner lifetime |
| Ten appendages | SetObj16 E0/E1, object16/type9, ten parts, source creates up to ten | Source placements, scales, phases and lifetime; no concurrency assumed from maximum count |
| Temporary player weapon | ObjMgr.create(0xB), player BIN18/TPL17 during strangle/parasite callbacks | Existing weapon draw and source attachment/lifetime must qualify independently of the giant body |

The current separate object-kind table covers core16/type4/14parts and flyinghead01. Those rows do not cover chain1d, parasite16/type8/25parts or ten16/type9/10parts. Body descriptor ownership cannot confer their ownership. The weapon's existing route also requires actual qualification; no absence of every other weapon path is inferred from this table.

Full auxiliary source geometry is already retained in H-018; no replacement was rebuilt. Chain diffuse alpha alone does not implement its separate opacity/blend contract. An old restored GC texture pair is diagnostic data, not native-chain approval. No instance costs are obtained by dividing aggregate draw cost, and no maximum instance sum is labelled simultaneous.

## Unchanged approval and handoff

The sealed H-030 private set was rehashed completely. Its approved package is still `70a81b2638e9283f023958061490b55b61f03a609be312aff135fd5e75cdec03`; canonical r224 spec still contains only the type1 protected child and both full parents. No type3 reduction, second model set or user choice was introduced.

Coordinator routes the live-detail predicate and active Ctrl12/object contracts to the existing character renderer owner. The room owner retains original fight progression. Whole-fight materials/audio/residency, actual auxiliary native draws, grab/QTE/release/death/cart/lava/clear, 48 KiB KOS, STRICT/decisions, route and release/off-image gates remain open. No fresh timing or look acceptance is claimed.

Private `boss18-twins-live-contract-20261019`: 22 files / 539020 bytes, SHA256SUMS `86a94a4c2955cbf963418f1159666612fb38dced816860af9584da07dd0d065f`. Immediate C mirror byte-verified. Owned host executable was pruned after recording its hash; source, checks and logs remain.

Evidence: `C:/Flycast-Evidence/re4-dreamcast/boss18-20261018/twins-live-contract-20261019/`. Public hash-only reference: `tools/d367/boss18/twins-live-contract-20261019.json`. No game assets or generated model/texture/media enter Git.
