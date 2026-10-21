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
