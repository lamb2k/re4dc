# Build 27 — recovered weapon modules and clean equip refusal

Branch `codex/wep-modules-27-20261028`, based on newest integration at build
start: `6be0a66ab59fa597a55aae7379fb09777d357bc1`. Build 26 was published
first as `a8861996dd79f32f24da15eb37711399bae3162d`. This integration base
already contains Claude's Build 25 merge, but not the separate Build 26 branch.

## Result

`WEP_MODULES_27=1`, default **0**, links the recovered civilian handgun,
Government/Matilda and Thompson modules through the existing native REL
generator, module-state handling and symbol-localization pipeline. It also
rejects unavailable weapon selections before inventory mutation and returns
from missing-module/native-bind failures without entering the fatal DLL
wrapper or calling a rejected prolog. No release recipe is enabled.

The complete decompiled routines were already in the public source tree.
This build supplies their missing image admission and qualification; it does
not replace them with success stubs or invent weapon behavior. The older
`WEAPON_WEP05` switch is supported: enabling both switches produces one
wep05 module and one table row. The three source modules remain unchanged.

| Module | Native REL ID | Logical weapon number | Item | Object registration |
|---|---:|---:|---|---:|
| wep05 | 67 | 5 (`0x05`) | `0x29` | `ObjInitFunc[0x2e]`, civilian |
| wep06 | 50 | 6 (`0x06`) | `0x2a`, stock variant `0x2b` | `ObjInitFunc[0x31]`, Government |
| wep12 | 56 | 12 (`0x0c`) | `0x34` | `ObjInitFunc[0x25]`, Thompson |

`wep12` is decimal 12; logical/archive index `0x12` is a different entry
used by a Red9 variant. The recovered per-character mapping is preserved.

Source provenance and behavior are detailed in
[the wep05/wep06 audit](BUILD27_WEP05_WEP06_20261028.md) and
[the wep12 audit](BUILD27_WEP12_20261028.md). The manifests are
`config/G4BE08/modules.py` and each module's `splits.txt`; the recovered
object classes and shared handgun/machine routines are compiled directly.
No game data, extracted assets or new production assembly/linker scripts
are included.

## Module integration and size

`wep_modules27.mk` appends the selected modules before the existing module
generator runs. The existing source manifests resolve the shared
`wep/pl_handgun.cpp` and `wep/pl_machine.cpp` separately inside each REL.
The generator partial-links each module, supplies existing import aliases,
and localizes private symbols. This keeps `equipWeapon`, shared routines,
state and class symbols from colliding with wep02/wep11 or another module.

Each generated module exports only its two native entry points and five
state-span symbols. Constructor and common-symbol guards pass. New module
imports are subsets of those already required by baseline wep02 plus wep11:
there are **no new external import names**. This is a precise import-set and
module-link proof, not a claim of a complete private game link.

| Generated module | Executable | Read-only data | Initialized data | BSS | Allocated total | Maximum compiler local frame |
|---|---:|---:|---:|---:|---:|---:|
| wep05 | 6,400 B | 544 B | 0 B | 24 B | 6,968 B | 92 B |
| wep06 | 6,888 B | 544 B | 0 B | 24 B | 7,456 B | 96 B |
| wep12 | 5,788 B | 590 B | 0 B | 28 B | 6,406 B | 96 B |
| All three | 19,076 B | 1,678 B | 0 B | 76 B | **20,830 B** | Not additive |

These are actual generated SH-4 module objects before final linker garbage
collection. The Thompson state span is 25 bytes, rounded to a 28-byte BSS
section. All initialized-data spans are empty, so no pristine-data copy
backing is added. Prolog local frames are 4 bytes and epilogs use zero.
With old `WEAPON_WEP05=1`, that module is already resident; the incremental
module allocation is **13,862 B** for wep06 and wep12. Module-table, guard
and loader code/data are reported separately below.

Actual Make flags retain the existing `GAME_OPT=-O1` for these modules.
The old wep02 hot-module optimization list does not silently apply to them.
`ENEMY_DEMAND` admission is supported by a source audit: these weapon
classes have no direct enemy-slot arithmetic. Their placement construction
uses cObjMgr's established ownership order, with id/serial assigned after
construction; it is not the prewritten cEm metadata hazard.

## Equip admission and failure ownership

The new admission lookup uses the recovered character/variant tables and
their REL filename against the actual compiled module table. It does not
load an archive, allocate memory, reset module state, change inventory or
run a callback. Inputs outside the 46-entry weapon tables are refused.
Configured overlay rows count as present; their real load can still fail
later and must pass native binding. Existing overlay-file corruption,
missing-file and overlay-allocation fatal paths inside `routeOverlayLoad`
are unchanged; they do not return an `OSLink` failure. The three added
weapon modules are static. This build's recovery covers absent compiled
module IDs and a native binder that returns failure, rather than every
possible asset-loader error.

`cItemMgr::arm` checks a non-null weapon item before changing `pArm`,
`m_wep_id`, ammunition attributes or tuning levels. The debug weapon path
checks before granting/selecting an item. The normal inventory and quick
weapon callers therefore receive a clean refusal while retaining the
previous selection when the requested module is absent.

`ReadWepData` repeats admission before retiring any existing archive. After
reading, it checks the descriptor's actual module ID. An unknown ID returns
through explicit cleanup before the old fatal link path. The enabled path
calls the real `OSLink` and checks its result; it publishes the linked bit
and calls the prolog only after success. Other stage/enemy/system DLL
callers retain their existing policy.

`cPlayer::weaponLoad` handles a refused load by restoring a previous weapon
that is still owned and loadable. Its inventory, logical number, type and
ammunition attribute are restored together. The existing subscreen/quick
weapon reverted flag is propagated even when `WEAPON_HEAP4=0`. If no valid
previous item remains, the code requests the real bare-hands module when
present. If that module is also unavailable, it publishes an explicit
no-weapon selection and clears weapon callbacks, preview motions and the
archive pointer. It never calls the missing module or fabricates a model.

An actual late bind refusal retires the newly admitted texture/archive
ownership and any weapon heap-4 block before recovery. Because the linked
bit was never published, cleanup does not call an invalid epilog. The
common heap-shortage path also uses this guarded recovery in the enabled
composition, so it cannot fall back into an unavailable bare-hands DLL.
The debug option menu also honors the reverted flag instead of reselecting
the original failed request after recovery. Restoring an old archive
reinstalls its sound bank through the existing DVD transfer path. In the
terminal no-weapon case an unused sound bank can remain resident; this
change does not claim to unload those bytes.

## Output changes and acceptance boundary

For the three newly admitted weapons, the build executes their existing
decompiled init/move/fire/reload, sound/effect, cartridge and motion-table
behavior. This is not a render approximation or a new tuning scheme.
Unavailable equip requests intentionally change from a halt/invalid load
to a refusal and, for a late failure, explicit recovery. That behavioral
change is limited to the enabled composition and must be checked locally.

The synthetic source fixtures exercise real weapon functions against
recorded model/motion/sound/effect services. They do not emulate Dreamcast
PVR/audio, validate private archive contents, or establish visual/gameplay
equivalence in Flycast. The owner still needs equip/fire/reload and repeated
switching checks for items `0x29`, `0x2a`/`0x2b` and `0x34`, including room
transitions, archive reuse, inventory exit and quick weapon selection.

## Verification, numerical costs and whole-frame model

**Authoritative target gates PASS:** 192 comparisons cover six changed
existing translation units, eight old-WEP05 × heap-4 × archive-reuse
compositions, the new knob absent/explicitly zero, and complete preprocessed
source/target object bytes. Debug records and preprocessor line markers are
consistently excluded; compared bytes are not normalized or stripped.
Make flags and object lists match when off. Eight enabled compositions
compile and partially link the new APIs and all three real module entries.
IDs 67/50/56 and their generated module objects appear exactly once.
Final OFF/ON source/dependency closures contain 151/152 current hashes;
module and entry receipts also match their current inputs.

The target profile uses the pinned public GCC/KOS/SDK toolchain and the
actual public `prepare.py` KOS-cache header, retaining `KOS_CACHE_P2=1`.
Private chapter-2 LOD is disabled symmetrically by `NMR_POOL_LOD=0` solely
for public qualification. These gates prove complete changed-TU identity
and module composition, not a full private game image or gameplay run.

Combined additions below include the native modules and six changed game/
platform objects. They are measured before final linking/garbage collection.
Archive reuse does not change these deltas.

| Old WEAPON_WEP05 | WEAPON_HEAP4 | Added executable | Added allocated sections including BSS | Added BSS |
|---|---|---:|---:|---:|
| 0 | 1 | 20,464 B | 22,811 B | 152 B |
| 0 | 0 | 20,560 B | 22,911 B | 156 B |
| 1 | 1 | 14,064 B | 15,775 B | 104 B |
| 1 | 0 | 14,160 B | 15,875 B | 108 B |

With heap-4 on and old WEP05 off, the guard/table portion is **1,388 B
executable / 1,981 B allocated including 76 B BSS**, in addition to the
20,830 B module allocation. Compiler local frames in that composition:
`ReadWepData` stays **568 B**, `weaponLoad` **20 B** and `arm` **28 B**;
`debugWeapon` grows **12 → 20 B**. New availability/id/file helpers use
**4 B** each and the recovery function uses **48 B**. Whole-TU maximum
frames do not increase. Local frames are not summed into a claimed runtime
stack peak.

Exact controls, dependency hashes, sections and frames are in
[target-off.json](../../tools/cloud/build27/receipts/target-off.json),
[target-on.json](../../tools/cloud/build27/receipts/target-on.json),
[production-metrics.json](../../tools/cloud/build27/receipts/production-metrics.json)
and [VALIDATION.md](../../tools/cloud/build27/VALIDATION.md).

The complete-source weapon fixtures pass **38 cases for wep05/wep06** and
**24 for wep12**, both normally and with ASan/UBSan. The actual equip-contract
fixture passes all four `WEAPON_HEAP4 × WEAPON_ARCHIVE_REUSE` compositions:
**7,840 selector/bounds comparisons and 138 control-flow cases per run**,
again normally and sanitized. It executes the actual load/release/cleanup,
admission, restoration and affected caller bodies against explicit synthetic
DVD, allocator, module, inventory and rendering-service boundaries. Unknown
descriptors/returned bind failures never execute `DLL_Link` or an unbound
prolog; the post-rollback debug caller retains the restored item.

The target costs below execute instructions from the actual generated module
objects. Registration timing ends immediately before `OSReport`; logging and
the prolog return tail are excluded. Epilog timing covers the full function.
There are six execution cases, with output registration stores verified.

| Executed piece | Warm cycles | Cold-I cycles | Loads | Stores | Unique 32-B lines | Observed peak stack |
|---|---:|---:|---:|---:|---:|---:|
| wep05 registration prefix | 20 | 52 | 8 | 4 | 5 | 4 B |
| wep06 registration prefix | 20 | 51 | 8 | 4 | 5 | 4 B |
| wep12 registration prefix | 20 | 52 | 8 | 4 | 5 | 4 B |
| Each complete epilog | 4 | 26 | 1 | 1 | 2 | 0 B |

Loads/stores include stack and literal-pool reads. Line counts are distinct
32-byte architectural addresses, not physical cache misses or bus traffic.
Warm costs use perfect I/D caches; cold-I costs start the instruction cache
cold for that individual sequence while keeping perfect D-cache. External
registration slots and callback addresses are synthetic and verified, not
addresses from a private game image.

**Whole-frame MODELLED accounting, 200 MHz:** assume 30.000000 ms of all
other CPU work in a frame containing one complete epilog and one registration
prefix. Their 24 warm cycles add 0.000120 ms, for **30.000120 ms MODELLED**.
The 30 ms remainder and event frequency are assumptions. DVD waits, module
binding, initialization, logging, render/audio/gameplay services and actual
cache behavior are not estimated by the prefix fixture. This is accounting
for a bounded control window, not an equip-latency prediction or a claimed
frame-rate gain over the formerly missing module. A steady frame with no
equip/relink does not execute these entry functions; image/cache/heap effects
still require local measurement.

Receipts and reproducible fixtures are under
[`tools/cloud/build27`](../../tools/cloud/build27), including
[module-build.json](../../tools/cloud/build27/receipts/module-build.json),
[entry-cost.json](../../tools/cloud/build27/receipts/entry-cost.json), and
[the equip contract](../../tools/cloud/build27/receipts/equip-contract.json).

## Questions back to Claude

1. Please package and run the enabled image with the current sound-bank fix
   and real weapon archives. Do all three weapons equip, aim, fire, reload,
   switch away/back and survive room transitions in Flycast?
2. Exercise an unsupported weapon from inventory, quick select and debug;
   retain the refusal log and verify the previous item remains selected.
   Also exercise native-bind failure, heap shortage and the case with no
   previous loadable item. The latter clears callbacks explicitly and needs
   the owner's gameplay check.
3. Check full knob-off image identity, steady/peak heap-4 and KOS headroom,
   and code/stack overlap with the private route recipe. Generated module
   allocation is real; final image garbage collection and real archive/body
   overlap are not inferred from it. Claude owns merge and enablement.
