# Whole-enemy runtime redesign, 2026-10-18

Owner: main Codex lane (/root), codex/logic18. Status: implementation plan; no replacement or speedup measured yet.

## Objective

Make additional active, visible enemies substantially cheaper in r101 and r103 while retaining RE4 combat quality. Scope: decisions, movement, collision, animation, bones, hit attachments, skinning, lighting and submission. The user authorizes a simpler custom Dreamcast implementation and bounded approximations. Identical numerical results and RNG sequences are not mandatory acceptance criteria.

Preserve responsive controls/reactions, correct damage and hit volumes, convincing pursuit/crowding, comparable attack pressure, and working kills/waves/doors/events. A win cannot come from a lower cap, inactive attackers or hidden actors. Defaults and releases remain unchanged pending integration review.

## Use the measurements we already have

Retained logic18 profiles at source baseline 7d7c05ab, with host tools through 63d67eb2, are sufficient to begin. r101/r103 each have 16 qualified samples with four Ganado move calls. Mendez, Castle and Island supply additional context. Owner attribution is partial; four move calls do not prove four visible enemies.

Do not repeat the broad profiling campaign before implementation. The prepared l18s1rW diagnostic supports runtime count controls. The 1/2/3/4 count comparison and isolated 10-enemy stress case validate the replacement alongside development; they are not a prerequisite to designing it. Report whole-frame time, waits and actual updating/drawn identities separately. MODELLED and Flycast results are not console acceptance.

## Architecture decision

Build a small native enemy runtime behind the existing actor, room/event and save interfaces. Replace expensive services while initially retaining the action state machines. Compact service records carry stable actor identity/generation, clip/pose versions and only hot data. Synchronization with source actors occurs at explicit boundaries. Destruction and room swaps retire these records.

Target flow: advance individual action clocks/events; obtain local poses from a shared pose service; apply individual root/contact/aim corrections; publish final bones and hit attachments; skin/light/submit through the native renderer. A shared neighbor service supports contacts. Introduce this under existing per-actor ordering before considering a phased scheduler. Do not build a generic ECS/job framework first.

## Ordered implementation

### 1. Compact pose service: first replacement slice

Start with village/farm Ganado locomotion. Separate pure local clip sampling from clocks, root movement, sequence events and actor-specific IK/corrections. Use contiguous joint/channel data and a compact hierarchy; retain current clip assets initially. Cache pure sampled channels by immutable clip identity, skeleton layout, phase, looping/mirror semantics and sampling flags. Reuse existing fast math where useful.

Keep attacks, grabs, damage reactions, parasites and room-scripted motions on the original evaluator initially. They remain active and visible; the slice cannot skip their clocks or events. This bounds implementation rather than claiming those costs are solved.

Exact-phase sharing is the initial mode. If encounters offer too few matching phases, add a separate approximate locomotion sampling mode with measured pose error and independent action clocks. Do not synchronize the crowd to manufacture hits. Blends, camera channels, part overrides and source history need explicit treatment: MotionMoveCore is not currently a pure sampler.

Use a fixed bounded workspace, initially targeting a ceiling of 32 KiB for new pose scratch/cache, subject to the existing heap ledger. No per-frame heap allocation. Eviction recomputes correctly and introduces no gameplay disc reads. Measure hit rate, copy cost, sampling, matrix passes, RAM and whole-frame effect. Poor sharing must lead to a bounded decision, not indefinite cache tuning.

### 2. Shared contact and environment queries

Use compact live collision-body data and local-neighbor queries instead of all-candidate sweeps per actor. Start with dynamic contacts and retain original narrow-phase shapes and push priorities. Update moved/pushed bodies before subsequent queries; handle swept bounds, doors, destruction, teleports and room swaps explicitly.

Small crowds may favor scanning over a grid; compare total maintenance plus query cost. GAME_ATCHK/CACHE/LIST already cache eligibility, but atchkPasses still revisits the candidates for each mover. Static scenery already has spatial traversal: audit it before adding a competing index. Ordinary route planning is already staggered eight ways.

### 3. Bones, skinning and lighting

Use compact hierarchy traversal and dirty dependencies to avoid rebuilding unaffected transforms. Intermediate matrices consumed by IK, hit volumes and attachments cannot simply disappear. Map consumers and combine passes only where their inputs remain available.

Test shared object-space deformation for compatible mesh/pose groups, retaining per-instance placement, projection and lighting. The current renderer fuses skinning with projection and already uses SH4 kernels. Extra object-space buffers/transforms can lose, so require a bounded measured arm before adoption. No GPU-compute or PC-SIMD assumptions transfer automatically.

### 4. Preparation and submission

Retain existing immutable geometry proof, bind reuse, material records, lazy palettes and one-submit path. Remove remaining repeated setup across compatible actors/materials only where evidence identifies it. Preserve alpha ordering and individual visibility. This engine plan does not authorize new mesh reductions.

### 5. Pursuit/decision service if remaining cost warrants it

Consider shared pursuit goals, bounded perception refresh and a compact common locomotion controller after the service costs are addressed. Keep urgent reactions responsive and preserve special interactions through adapters. Do not rewrite 110 action pairs solely to remove old classes. Broader state-machine replacement needs evidence of substantial additional value.

## First milestone and validation

Deliver a default-off native locomotion pose arm in r101/r103, retaining original actor updates and rendering. Its first result is a measured whole-enemy improvement or a documented rejection and next ranked slice. Service boundaries and bounded memory are part of that deliverable.

Run existing cap-4 fight controls immediately. Add matched 1/2/3/4 count arms with verified visibility, then an isolated 10-enemy stress case. Record clip/phase/weapon/distance diversity because it determines sharing opportunities. Held entries and invisible actors are not performance credit.

Check control response, attacks/damage, head/weapon/hand alignment, slopes/doorways, crowd separation/surround pressure, hit reactions/deaths, waves/exits, repeated entry/retirement, memory squeeze and gameplay I/O. Exact comparisons apply where exactness is promised; approximation is judged on behavior and appearance. Longer encounters test drift consequences. A changed trace alone is not failure. No speedup is promised in advance.

## Source anchors and references

- Whole actor lifecycle: src/game/em.cpp, emMove; src/em10/em10.cpp, cEm10::move.
- Pose/clock/IK coupling: src/game/motion.cpp, MotionMove and MotionMoveCore.
- Contact sweeps: src/game/at_mod.cpp, atchkPasses and EmAtCheck.
- Skin/projection: port/dreamcast/game/platform/native_actor_fast.cpp, Frame, prepare_frame, avk_positions and avk_lights_n16.
- [ozz runtime layout and sampling](https://guillaumeblanc.github.io/ozz-animation/documentation/animation_runtime/).
- [Epic state/pose sharing](https://dev.epicgames.com/documentation/unreal-engine/animation-sharing-plugin-in-unreal-engine).
- [DetourCrowd neighbor/path separation](https://github.com/recastnavigation/recastnavigation/blob/main/DetourCrowd/Source/DetourCrowd.cpp).

These are design precedents, not Dreamcast speed evidence or a proposal to import an entire modern engine.
