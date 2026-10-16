# RE4 Dreamcast implementation instructions

## Outside contributors start here

The rest of this file is the maintainers' own notes. It names folders on their machine
(`/root/probe`, `/root/work`, `re4-assets-private`, `D:\Flycast-Evidence`) that you do not have and do
not need.

* **Public, in this repository:** all port code, build recipes, knobs and tools, the toolchain script
  and Dockerfile, and the documents. Start with `port/dreamcast/CONTRIBUTING-PORT.md`, then
  `port/dreamcast/docs/D367_THIRTY_FPS_ROUTE.md` (goals and decisions) and
  `port/dreamcast/tools/d367/README.md` (build recipe and knobs).
* **From the test release:** the disc (GDEMU zip) and the Build-Assets zip with the generated
  character data. `bash port/dreamcast/contrib.sh` downloads both and gives you a bootable disc.
* **Maintainers only:** the recorded play sessions and trace harness, the hardware timing model runs,
  the asset conversion work folders and the original game discs. You never need them.
* **A pull request needs:** the change behind a build knob whose default is 0; the same program bytes
  with the knob at 0 (knob off identity); the gain in milliseconds with the room, the view and the
  enemies on screen; and no change to collision, events, game state or AI. The maintainers then check
  that the gameplay stays identical tick by tick (STRICT) before it goes into a test build.
  Approximations are the exception: default-off knob, judged by look (render) or by the same kills,
  triggers, doors, waves and cutscenes (logic); see "Send a patch" in `port/dreamcast/CONTRIBUTING-PORT.md`,
  which also covers the system memory (KOS squeeze) check and the one-minute emulator runs.
* Never commit game data, disc images or extracted files.

## Current direction (D367): supersedes the sections below where they conflict

- **Targets:** the route target is unchanged: normal menu/New Game -> r100 -> r101 -> r103 playable. The frame-time target is now 30 fps (per tick: gameplay G <= 24 + render R <= 6 + a 3.33 margin; the 2026-09-25 rethink, a coarse complete square first) on real NTSC Dreamcast hardware via GDEMU + VMU; 20 fps and a 15 fps fight fallback were the earlier targets. The SH-4 hardware model (`tools/hwmodel/hwproject.sh`) is the hardware estimate; Flycast is a proxy.
- **Rendering:** the user dropped GameCube rendering tech in favour of Dreamcast-native approaches and allows new offline assets.
- **Never altered:** collision, event sequencing, game state and AI. Render-only changes must keep the logic trace STRICT.
- **Decisions and work order:** every option is chosen by its hw ms impact. Since 2026-09-25 performance work runs in parallel, non-overlapping agent lanes, each change measured by one cost arm and one STRICT gate; the main session lands every patch (lane map: `port/dreamcast/docs/D367_SQUARE_PERF_PLAN.md`, "Current order and status"; every standing user decision: `port/dreamcast/docs/D367_THIRTY_FPS_ROUTE.md`).
- **How to resume:** use the shared skill `re4-dreamcast-d367`, which covers the harness, commit recipe, state files and decisions.
- **Historical:** the Astra/Sol (GPT-6) assignment and the D349-cutover milestone below are history. Current work is user-directed through that skill. Codex sessions follow the same lane, rules and commit procedure.

## Objective and architecture

Deliver normal boot/main menu/New Game and consecutive playable r100 -> r101 ->
r103, including required combat/events, HUD/audio, inventory, transitions, death
and retry. Cutscene presentation may be skipped through its qualified source
completion path. Room initialization or a scripted picture is not acceptance.

The north star is to beat D349's visual workload cost with the real recovered
game, while retaining source simulation/state and the proven native architecture.
The active milestone is [the r100 native cutover](port/dreamcast/docs/R100_NATIVE_CUTOVER_GOAL.md):
recovered GameCube source owns simulation/state; the existing D349 converter,
`.re4room` packages and native renderer own presentation. The live GX/ModelPart
bridge is fallback for unconverted content. GC and PS2 are first-class offline
visual inputs. D362 ends lossless scavenging; continue the complete cutover,
not bridge-cache tuning or another converter architecture.

## Context routing

Use [CLAUDE.md](CLAUDE.md) when resuming for current paths, baseline and active work.
Read supporting documents when the task touches their contracts:

- Rendering/asset cutover: [R100_NATIVE_CUTOVER_GOAL.md](port/dreamcast/docs/R100_NATIVE_CUTOVER_GOAL.md).
- Route, source systems and outstanding integration: [PLAYABLE_PATH.md](port/dreamcast/docs/PLAYABLE_PATH.md).
- Measurements: [REALTIME_PATH.md](port/dreamcast/docs/REALTIME_PATH.md).
- Resource ownership/loading: [R4_ASSET_RESIDENCY_PLAN.md](port/dreamcast/docs/R4_ASSET_RESIDENCY_PLAN.md).
- Visual candidates: [PS2_INSPIRED_DREAMCAST_PROFILE.md](port/dreamcast/docs/PS2_INSPIRED_DREAMCAST_PROFILE.md).
- A specific prior result: its checkpoint and implementation, not every historical log.

The active cutover contract supersedes dated next-task/gate language in historical
checkpoints. Keep their evidence and rejected results. Do not repeatedly read
all backlogs before routine edits or turn history labels into execution order.

## Implementation boundaries

Preserve source gameplay/AI/collision/camera, activation, progression, current
pose and attachments, material/texture animation, required alpha/depth/cull,
changing lights, audio, owner generations and retirement. Maintain one PVR/frame
owner and corrected actor facing. The historical prototype loop, sampled poses,
fixed camera and reduced encounter logic are not the recovered game's state.

Before designing a new Dreamcast rendering structure, converter, cache, package
or lifecycle mechanism, inspect the preserved D349 implementation and existing
port/dreamcast/tools, port/dreamcast/room, native texture/storage/lifecycle code,
and isolated completed experiments. Reuse or extend the proven mechanism unless
a documented source semantic or measured budget makes it unsuitable. Record why
an existing mechanism cannot be used before introducing a replacement.

Work through implementation, relevant checks, target execution and routine fixes
until the defined milestone works. A first patch, passing host tests or a commit
is not a stop instruction. Sol and Astra use the same contracts. Current user
assignment: Astra locks architecture/handoff, then GPT-6 Sol at Max implements.
This does not authorize additional agents (historical: the D367 parallel lanes of 2026-09-25 are user-authorized). Assigned parallel work needs isolated
ownership and an exclusive emulator window.

Astra decides architecture; Sol executes the approved architecture. Follow the
[Astra/Max escalation rule](port/dreamcast/docs/R100_NATIVE_CUTOVER_GOAL.md#astramax-escalation-rule)
when new evidence invalidates a contract or requires a new budget/architecture.
Preserve evidence and hand off before designing a replacement. Ordinary bugs,
compatible format extensions and tuning stay with Sol. Every resolution must
be written into the durable handoff before Sol resumes implementation.

Guard shared PowerPC behavior when changing recovered source; use its existing
comparison procedure where affected. Keep incomplete required conversions and
module bindings explicitly rejected. Required native REL entry points cannot
execute disc PPC bytes or success stubs. Off-screen render rejection cannot stop
required gameplay. ARAM contracts are not spare AICA memory.

Judge the complete cutover against the retained baseline. Report source-state
and visual checks, fallback coverage, actual replaced backing and peak overlap,
CPU/PVR/presentation costs, and unresolved acceptance. Host fixtures, Flycast and
physical Dreamcast are distinct evidence. Hardware unavailability does not stop
useful implementation. Candidate visual changes already authorized by the user
may be built and measured; record quality acceptance before changing defaults.

## Workspace and preservation

Use `/root/work/re4-dreamcast` in WSL Ubuntu-24.04, branch `dreamcast-port`.
`re4-dreamcast-WINDOWS-INCOMPLETE` cannot preserve case-sensitive source names.
Inspect live HEAD, dirty work and active processes before changing shared state.
Never reset/clean, overwrite inherited edits or broadly stage. Private source and
derived assets, discs and captures stay outside Git. Keep the selected toolchain
and accepted evidence immutable; use new generated-output directories.

lamb2k/re4dc is a public repository (it also publishes the play builds): every push is a
publication. The user authorizes reviewed commits/pushes to origin/dreamcast-port. Stage owned
changes only, inspect the diff and verify the remote SHA. A docs commit does not
accept uncommitted runtime changes. Use script files for complex Windows/WSL
commands; inspect a stalled process before restarting it.

## Play / record machine (SteamOS Desktop Mode)

An agent asked to set up a Steam Deck (or other SteamOS machine) to play and record the port's builds
follows [STEAMOS_PLAY.md](port/dreamcast/docs/STEAMOS_PLAY.md): run
`port/dreamcast/tools/steamos/setup-play.sh` (newest `play-*` release of
`lamb2k/re4dc`, sha256-checked; Flathub Flycast + GPU Screen Recorder, user installs, no sudo; a Steam
shortcut), then `record.sh` to record. The user signs in to GitHub themselves (`gh auth login`); never
upload discs, logs or recordings anywhere unless the user asks. The GitHub account was renamed from
stevedamnvan to lamb2k on 2026-09-29 (old URLs redirect).

## Follow-up after first-room acceptance

Once normal menu/New Game and the complete first room are manually playable,
save the proven workflow as an Astra low (`gpt-6-astra`, low reasoning) skill using
skill-creator. Capture paths, reusable mechanisms, commands, ownership contracts,
evidence and known failure boundaries; validate the recipe against the working
room. This is a follow-up, not a prerequisite or proof of three-room acceptance.
