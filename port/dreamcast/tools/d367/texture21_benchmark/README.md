# Texture benchmark preparation

These tools prepare immutable farm/woods scene and source/build/data identities.
They do not derive FPS from texture sizes. No production recipe is changed.

`bench.py scene farm-midfight NEW_DIR` retains the scenario19/rigid20 farm fixture:
Leon at (-47609,12,7084), angle1.8890, one scheduled id0x12 kill at source room
frame150. `farm-wide` reuses actorplan's wide farm view and `woods-bridge` reuses
the retained r100 bridge view. The original input files are hashed. All preserve
pad-neutral play after entry. None proves the screenshot's corpse pile identity.

Each prepared short window settles room frames0..299 and requests300..419,
120 inclusive frames. A50-second guest budget takes precedence: if the source
window does not finish, report incomplete and do not widen or silently replace
it with a host-time window. Longer historical console windows300..1199 remain
a different benchmark. Camera, actual drawn pictures, logic ticks, active enemies,
VRAM/KOS and drive counters must be captured before timing is comparable.

The historical farm fixture says animals are present. Retained October21 QA
actually resolves ANIMALS_OFF=1. Record that real configuration as animals-off;
an animals-on run is a separate controlled variant. ALIVE_CAP and ALIVE_CAP_N
must both equal4. SS_WINDOW_HOLD_RESTORE stays0: its inventory traffic result
was negative, and it is not an accepted performance change.

`bench.py seal --repo SOURCE_TREE --build BUILD_DIR --scene scene.json --out NEW.json
--preprocessed ACTUAL_PREPROCESSOR_OUTPUT` hashes all target objects, ELF, program,
overlays, resolved knobs, actual preprocessing and source dirty identity.
Missing preprocessing stays explicitly unresolved. Sealing alone does not prove
that these objects came from this source; retain the build invocation/log and
verify preprocessing at the actual selected translation units. Root may provide
the frozen qualified build; do not point --repo at the tools tree for another
branch's build. No label such as OFF or ap0 establishes a control.

`bench.py image TRACK03 NEW.json` reuses fullplay/fp_iso.py to hash every staged
file without extraction, plus the whole track identity. `bench.py compare A B
IMAGE_A IMAGE_B --allow-file dc/tex.pak --out NEW.json` rejects source, object,
preprocessing, knob, scene or unexpected staged differences for an asset-only
pair and binds every image's program/overlays to its build. A separately reviewed
source/adapter candidate requires its own qualified comparison, not a wider
allow-list. Retain texture-member proofs, complete geometry/registry identities,
and the exact actual loaded candidate keys from component lanes.

WSL `capture.sh WINDOWS_PYTHON_EXE ...` holds the existing trace_lock slot and
invokes Windows `capture.py`, which reuses fullplay/fp_run.py with a frozen base's existing
fixture slots, PID-scoped controls, periodic screenshots, disk guards and a
49-second pinned-handle watchdog (under the50-second guest limit). The Windows
watchdog is source-reviewed and compile-checked, not live-qualified yet. Root supplies an expiring guest resource receipt:
`{"owner":"texture21-benchmark","guest_slot":true,"expires_unix":UNIX_SECONDS}`.
This reservation coordinates resources; it is not a new user permission flow.
No guest is launched by scene/seal/image/compare. A base is immutable and its
source/program/data must first match the intended arm. Screenshots every five
host seconds are evidence of appearance, not tick-aligned pixel comparisons.

Corpse-pile visibility, animals, offscreen rendering and pause presentation stay
separate variables. Run active room views; paused views do not establish gameplay
render cost. Report source tests, Flycast, MODELLED hardware timing, release checks
and physical Dreamcast independently. The latter two remain Claude/user owned.

Run focused source tests: `python3 -m unittest discover -s
port/dreamcast/tools/d367/texture21_benchmark -p test_bench.py -v`.

`preprocess.py --repo SOURCE --build BUILD --out NEW_DIR --source
platform/native_actor_fast.cpp --source platform/native_static.cpp --source
../room/texture_package.cpp` finds each exact logged `kos-c++` compilation,
replays its flags with the pinned SH target compiler in `-E -dM` mode, and records
compiler/source/object/command/macro identities. It preserves the original
objects and ELF. It rejects source paths outside the selected repository and
ambiguous or absent compile commands. This establishes the actual translation
unit definitions; it does not turn a source receipt into a gameplay test.

Existing unchanged QA discs can also run through `capture.sh --disc DISC_DIR
--keys MENU_KEYS --image-receipt STAGED_RECEIPT ...`. This path requires the
prepared fixture to match the exact already-staged QA preset and rehashes the
entire original track before launch. It changes no image bytes and restores no
old guest state. Source room-frame markers and the selected QA preset govern the
run; an earlier prepared custom warp is not silently installed. Retain the menu
input script with the capture lineage.

Woods continuation can use `--checkpoint` with unchanged QA mode. The isolated
checkpoint_run.py adapter reuses Flycast AutoSaveState and the established
PID-owned SDL close method from the castle harness; shared fp_run.py is untouched.
Before accepting a checkpoint, require a fresh FLYSAVE1 file and the actual
Saved-state log receipt. `--state-seed OWN_PREVIOUS_CAPTURE` rejects a different
lineage folder, staged program/image, emulator binary, modified state hash or
still-running owner. Restore only this same unchanged program and image; never
transfer a state to a new candidate program. The adapter is compile/source-tested
but its first live checkpoint save/restore is still pending the disk floor.

Capture now requires C to retain18GiB+128MiB and limits owned capture growth to
100,000,000 bytes, counting the private emulator and state while excluding
hard-linked disc tracks. An independent49-second pinned-handle watchdog caps the
guest. When a cold woods route does not fit, preserve its incomplete result and
continue an authenticated same-program checkpoint rather than changing the
camera or borrowing a foreign state. The initial cold QA normal-boot attempt
reached title exit, not playable woods, before its watchdog bound.
