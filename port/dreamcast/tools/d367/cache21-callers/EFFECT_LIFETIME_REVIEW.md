# Post-forward effect lifetime source review

Review baseline `bf250af8e8719516b2048ce502ed06370d10efed`. No runtime edits in
this characterization. `effect-lifetime-host.json` pins seven complete source
files, every executed method/type, compiler command and fixture identities.

## Ownership transition

| Operation | Actual source behavior | Remaining contract |
| --- | --- | --- |
| EspDataLoad first valid owner | Registers archive-relative pointers, including estRegist data/list | No archive lease stored by this registration |
| EspDataLoad shared owner | Increments ownerCnt; returns success before registration | Existing first archive remains the registry source |
| Push enemy0x13 | Maps enemies0x11..0x20 to shared owner0x10; decrements once | Count greater than one leaves all registrations live |
| Forward MemorySwap | Overwrites module archive with event bytes | Native carrier receipt does not certify effect range retirement |
| SetEvt publication | Requires carrier current/event binding; actual init may still fail | Event publication is separate from forward receipt |
| EvtFree reverse | Positive native reverse receipt before swapped0 and Pop | Pop has a void interface and no accepted registration result |
| Pop | Gets EFF from current module; calls EspDataLoad | Missing EFF/invalid version cannot be reported to EvtFree |

## Confirmed source defects and boundaries

Ten actual-source controls pass. For valid synthetic EFF archives, actual
EspDataLoad/estRegist/EspDataRelease/Push/Pop and EspGetEstAddr execute. Actual
non-CABIN MemorySwap executes against controlled software ARAM; no native
generation, Event publication, callback scheduling or private asset acceptance
is inferred from this separate unit.

With first registration inside the exchanged archive and refs2 or200, Push
leaves refs1 or199 and live EST data/list pointers. Actual MemorySwap replaces
the archive; actual lookup then returns the same pointer with the event's
changed record marker. First registration in a different archive is a negative
control and retains its marker. Final release refs1 marks EST unused, so lookup
refuses during the exchange. Reverse plus Pop restores current module data;
for a previously final-released outside archive, Pop intentionally registers
the current module archive, not the original outside source.

This establishes a source-callable shared archive ownership gap. It does not
establish that a tested gameplay route has refs greater than one with the first
registration in the borrowed module. The sealed forward fixture already tested
effect count transitions with explicit registry boundaries; it did not certify
effect retirement. A real fix needs exact registered ranges plus active effect
borrowers/retirement, rather than interpreting ownerCnt or ReadTbl Count as a
lease. Main owns that holistic contract.

Separately, EspDataLoad increments ownerCnt before checking version0xB. A
wrong-version initial load returns0 with count1 and no EST registration. After
correcting the version, immediate retry returns1 with count2 but still no EST
registration. NULL input is a negative control and leaves count0. This is a
bounded confirmed count-poison defect suitable for validating version before
the owned count mutation; shared valid input behavior must remain unchanged.

Actual Pop missing EFF returns void with owner still unregistered; invalid
version Pop leaves the poisoned count with no registration. Current EvtFree
sets swapped0 before Pop, has no Pop result to inspect, then clears the unit and
read row. This caller consequence is source review, not an executed EvtFree
case in this fixture. No blind effect Pop/rollback or stale metadata restore is
proposed.

## Evidence

Raw source/compile/run output and receipt:
`C:/Flycast-Evidence/re4-dreamcast/cache21-callers-20261021/cache21-callers-effect-lifetime-host-20261022-02`.
Output below20MiB; fresh C floor18GiB plus128MiB enforced. The initial host01
assertion is preserved too: the fixture incorrectly expected Pop to restore an
outside archive after final release. Actual source correctly registers its
current module. Corrected assertion verifies exact inside/outside pointers.

No runtime source, knob, object, linked program, target image, Flycast, release,
physical Dreamcast or performance acceptance is added by this review. Main
retains holistic lifetime/integration and Claude production merge/release.
