# Local cleanup for an event whose initialization failed

`EVD_START_CLEANUP=1` is a new default-off switch requiring
`EVD_ADMISSION_TXN=1`. It applies only to `event.o`, and its recovered-source
changes are excluded from `__PPC__`. No recipe/default, class layout or header
changes are made.

The branch starts at current integration
`28b818e5c11cd0bbe7fdc94b973ecea3de0bdd56`, which includes `aafc10f3`.
The independent transaction commit `8ff45d69` was merged without rewriting
history as `35435c7dbb4ed7e98f5eca42f927a822427be320`. That merge is the
matching baseline for this new unit. All prior checkouts and evidence remain.

## Approved runtime unit

Previously a failed `Event::init` called `DelEvt`, although this work had never
begun. That runs normal player/effect/audio/scenario teardown, clears the prior
running name and can delete a reused EVD. Initialization also cleared the global
128-entry `EspEvModList` before packet/frame validation could fail.

With the switch on, failed init instead releases its accepted carrier-event
binding, if present, and calls the existing manager `destroyNow`. Successful
init clears the effect-model view immediately before returning success, after
both frame validations. The original begin-pending publication, successful cabin
callback, running-name assignment and ordinary `DelEvt` remain unchanged.

The actual destruction contract needs no extra model-table end call:

- Manager create clears and constructs a fresh pool slot, then links it.
- `Event::~Event` clears Type. C++ then invokes the actual `DatTbl` member
  destructor, whose `end` releases the allocated table. Init has not registered
  models into it. Allocation refusal leaves pWork null; no model scan is needed.
- Existing `destroyNow` temporarily selects immediate destruction, unlinks the
  slot through the actual manager path, and restores its prior manager flag.
- Carrier admission changes only its exact `c.event` on success. Refusal changes
  no binding and retains the existing direct-destroy/diagnostic path. After
  accepted admission followed by failed init, the existing exact-event deletion
  hook clears only bindings matching this work, before destruction.
- Actual cabin event/audio binding occurs after init succeeds. Failed init does
  not call those event-deleted/audio/end callbacks or close prior media.

`GetFunc` only obtains the room callback pointer. The inspected frame scanners
and native refused host-file path do not consume `EspEvModList`, so delaying its
reset preserves successful initialization and leaves the prior view on failure.
This adds no snapshot/restore or new concurrency policy.

## Actual-source tests

`test_event_start_cleanup.py` extends the exact sealed `5d10f51e` fixture and
records its original hashes. H064's pinned selector/header constructor is reused.
Runtime init/end/delete/table/manager bodies are extracted, not reimplemented.
Actual carrier structures, admission, ownership predicates and exact-event
unbind execute, along with actual cabin binding/deletion/audio-close callbacks.

The state suite passes:

| Configuration | Cases |
| --- | ---: |
| Transaction off, cleanup off, cabin off | 36 |
| Transaction on, cleanup off, cabin off | 36 |
| Transaction on, cleanup on, cabin off | 15 |
| Transaction on, cleanup on, cabin on, completion handoff off | 35 |
| Transaction on, cleanup on, cabin on, completion handoff on | 35 |

OFF controls preserve the earlier ordinary/kept-read characterization. ON tests
call actual registered-name `SetEvt` directly. Four failure boundaries
(model-table allocation before Name, bad packet, missing camera and injected
final-scan mutation) each cover new and reused complete registrations, exact
prior parent/bin contents, prior live work/name/global flags/effect list, table
free count and immediate successful reuse of the failed slot. Success publishes
the begin-pending bit and zeroed effect view. Ordinary explicit `DelEvt` still
performs its original teardown; this is a method-level control, not execution of
a complete source event/movie.

Cabin controls cover both accepted Mram and Ready/source-role states at all
four boundaries, unchanged other carrier bindings/readers, unbind before pool
destruction, successful retry/binding/audio callbacks, and twelve refusals:
fault, invalid unit/allocation/module, wrong data/heap, occupied binding,
Reference/Ready-wrong-role/Preparing/Absent state and wrong unit. Refusal retains
the exact prior carrier/cabin state and does not allocate the model table.

The final-check mutation is deliberately injected after the unchanged actual
total-frame scanner returns. It violates immutable-input assumptions; it is not
claimed as an independent ordinary-content failure or gameplay occurrence.

State observations use UBSan **excluding vptr**. Strict OFF and ON controls
separately reproduce the pre-existing actual pool-lifetime diagnostic at the
manager's post-delete `p->be_flag` write. This remains open; the state suite is
not a clean full-sanitizer result. Negative32 mappings preclude ASan. Host class
projections, pointer-width/cast adapters, unit/allocation/module observers,
transport/final free and external world/audio/movie services are explicit
boundaries. Unselected carrier clear/free/reverse paths abort if reached.

## Object qualification

`qualify_event_start_cleanup_sh4.py` uses the actual selected Make/compiler and
same source path for exact baseline/candidate comparison. It checks whole SH4
`event.o` OFF identity with transaction 0/1 and cabin 0/1, enabled objects with
transaction 1, default/explicit-zero compiler-command agreement, static frames,
invalid values and Make/direct-source prerequisite refusal. Selected edited
methods are also preprocessed with `__PPC__` and the switch off/on; that is not a
PPC object or whole-program identity claim. Final results and hashes are recorded
in `event-start-cleanup-sh4.json` once this qualification completes.

The established small-object preflight is 16 GiB + 128 MiB, with a 16 GiB +
64 MiB stop and 4 MiB bounded logs. Full-build thresholds remain unchanged.

## Explicit remaining caller boundaries

This unit does not roll back an outer `SetEvt(data)` admission or free caller
input. Complete parent/bin registrations may therefore remain after failure.
It does not repair shared-read ownership, generation/reset, the whole EVS bundle
or scenario start/end pairing. `GetEvd` refusal before init retains its existing
failure path; it is not covered by this narrower init-failure repair.

Preserving the prior running name also means existing `EvtReadExec` now observes
and waits for that prior live work after a failed new start. The old fixture does
not advance that work, so ON local-unit tests do not simulate its completion or
claim the outer read/scenario contract accepted. Cabin audio-admission failure
after successful init and general event/media completion are also unchanged.

No linked/overlay build, stage, guest, gameplay/console/I/O/timing acceptance,
recipe enable, release/issue or SD action. Root retains architecture, review and
integration; Claude alone merges production, tags and publishes.
