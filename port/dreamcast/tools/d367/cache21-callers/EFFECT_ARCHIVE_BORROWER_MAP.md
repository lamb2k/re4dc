# Effect archive borrowers after forward publication

Read-only source follow-up to `bf250af8e` forward receipt and `b228da0ea`
selected effect admission qualification. `effect-borrower-matrix.json` pins ten
complete files and exact executed methods. No runtime change or new claim.

| Producer or transition | Borrowed identity | Consumer / retirement |
| --- | --- | --- |
| eff_sys.cpp estRegist | SstTbl.data/list point inside first EFF archive | EspGetEstAddr reads list and returns an archive head; final estRelease marks owner unused without clearing pointers |
| est.cpp EstSet(cModel*,...) | Espgen10Work.head stores that sequence head across frames | espgen10_Update reads head and records; model pointer/serial validation is independent of archive ownership |
| espgen.cpp EspgenSeqSet | Passes archive-owned record reference to SetFreeWork | generator00 retains it in p->rec; scratch is temporary decode storage |
| espgen00.cpp Espgen00_SetFreeWork | p->rec retains compact/raw record reference | Later emissions pass retained reference to EspSeqSet |
| native_effect.cpp bind_archive | Binding.archive/entries borrow archive metadata; count stored separately | record_ref/read search those entries; no generation or active-reader pin stored in Binding |
| native_effect.cpp record_read raw path | Even pointer returned directly | No live-binding check occurs on the raw-return path |
| native_effect.cpp record_ref | Reads half(head) before searching a live binding | Model rejection ordering repair avoids one dead-model read; valid/model-less borrowers still require archive lifetime |
| event.cpp EvtReadSub forward | Captures unit/row/module/allocation/native carrier epoch | Accepted receipt does not inspect effect registry/controller/native effect Binding borrowers |
| event.cpp SetEvt | Native carrier Event binding before Event init and publication | Failed init uses existing local start cleanup; archive effects remain a separate lifetime |
| event.cpp EvtFree | Native reverse token/completion before clearing swapped and Pop | Does not acquire an effect registration receipt; Pop remains void |
| read.cpp InitModule | REL epilog then re4dc_effect_unbind before archive free | Binding is cleared; no controller scan/lease check in native effect unbind itself |
| game.cpp gameRoomMemInit | retire_room clears room Binding before heap replacement | Assumes suspended source updates; broader preflight/retirement order belongs to main audit |

## Deletion is selective; suspension is not retirement

SceEventStart runs EffectEventDelete only for a first, non-nested mode0 event.
Nested starts return earlier; mode1 skips it. EffectEventDelete dispatches the
source sprite/controller/model deletion services. EspgenDeleteEvent deliberately
keeps permanent/no-suspend Core_flg bit0 and event-owned bit0x800 controllers.
EspgenIsActive during an event enables surviving controllers with Core_flg bit0.

The exact EspgenIsActive, PushEspgen and EspgenDeleteEvent bodies pass64 source
controls: eight Core_flg values, four pool flags and event status OFF/ON. Actual
Push uses an empty optional destruct table in the fixture. Results for a live
controller during an event:

| Core_flg | Event deletion requested | Still active |
| --- | --- | --- |
| 0 / 0x2000 / 0x3000 | Yes | No |
| 1 / 0x801 / 0x2001 / 0x3001 | No | Yes |
| 0x800 | No | No (suspended, retained) |

The fixture's retained_head is an observational marker; actual EstSet storage is
source-reviewed, not executed here. Thus this proves the selective source
policy, not a gameplay instance of a surviving controller in a borrowed module.
It also does not execute the complete source SceEventStart or active effect
scheduler. Source byte identities and boundaries are explicit in the receipt.

## Concrete remaining contract

Neither ownerCnt=1 nor successful EffectEventDelete implies no archive borrower.
Even final registry release can leave retained heads/records; shared release can
leave registered archive pointers as separately reproduced by the ten-case
effect lifetime fixture. The first-forward receipt and existing admission guard
must keep their bounded claims.

A repair must attribute both registrations and retained controller/record/native
metadata to the exact current archive range, capture that ownership before the
first effect release/exchange side effect, and prevent new admission while
retiring or replacing those bytes. It must span yields/callbacks and preserve
partial native request ownership. A short query, registration count, blanket
Pop or deleting every effect is not a demonstrated complete contract. The
sprite/model and UI/motion archive consumers also need the main holistic map
before approving a whole archive replacement preflight.

Root's separate `EFFECT_CONTROLLER_VALIDATE_FIRST` change in espgen10_Update
addresses model rejection before record access. This map does not duplicate or
replace that repair and claims no failure in its live-model behavior. Main
retains architecture/integration; all runtime files remain read-only here.

Raw matrix output/source/receipt is mirrored at
`C:/Flycast-Evidence/re4-dreamcast/cache21-callers-20261021/cache21-callers-effect-borrower-matrix-20261022-01`.
Output below20MiB with fresh18GiB plus128MiB compiler guard. No full build,
stage, Flycast session, release, physical-console or performance acceptance.
