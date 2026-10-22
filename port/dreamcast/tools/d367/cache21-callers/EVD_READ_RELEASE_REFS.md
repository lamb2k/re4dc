# Preserve other logical read registrations on release

`EVD_READ_RELEASE_REFS=1` defaults zero. It changes only Dreamcast `EvtFree`.
Actual `DatTbl::DelDat` decrements Count, while the old caller clears the unit
even when a registration remains. The reproduced Count2 control leaves a
Count1 row pointing to a cleared unit.

Before any wait, module reversal or carrier mutation, the guard accepts only
the exact returned unit and slot within both the eight readEm slots and table,
an ordinary temporary read row (Etc0, Flag3, dat2 null), and Count2..32767.
It calls actual DelRead once and returns its result. Remaining registrations
retain all unit, carrier, backing and readEm state. No operation yields between
lookup and this decrement. Count is a logical registration count, not a native
Event/DMA reader lease. Last release follows the original checks unchanged.
Malformed, permanent and other row forms retain existing behavior.

## Qualification

`test_event_start_rollback.py --release-refs-pair` passes24 OFF/25 ON cases.
Actual table/GetRead/DelRead/EvtFree bodies execute. OFF reproduces premature
clear; ON changes only Count for a non-final release, then final release runs.
The metadata control preserves nonzero em/swapped bytes without entering module
reversal. Four ineligible row/count controls retain the prior path. Input,
allocator, unit-clear and module services in this focused fixture are explicit
boundaries; this does not qualify a target module exchange.

`test_cabin_aram_alloc_retry.py --release-refs-pair` passes42 OFF/45 ON cases.
Actual source data-unit commands/allocation metadata/clear and native carrier
installation, Event binding, retirement/refusal/free predicates execute.
Count2/3/32767 non-final releases retain byte-exact unit/carrier/readEm and
decrement only the row count. Final release refuses while the actual native
Event binding is present. Actual unbind then final retry frees exactly once.
Original allocation-refusal and changed-receipt cases remain. Synthetic mapped
input, provider, heap/module services and Host64 adapters retain the boundaries
documented in the exact receipts. Count32767 is a table boundary control, not a
claim that gameplay acquires that many registrations.

The preceding failed-start suite still passes146 OFF/153 ON cabin0 and146 OFF/
154 ON cabin1 cases with the new switch off.

Four whole stripped SH4 event.o OFF identities match868b43448 across CABIN0/1
and EVD_ADMISSION_TXN0/1. Omitted/default and explicit zero commands match.
All four ON objects add144 text bytes, unchanged4 data/640 BSS. EvtFree static
frame is unchanged:36 bytes CABIN0 and64 bytes CABIN1. Invalid knob values are
rejected. Selected PPC EvtFree preprocessing is identical OFF/ON; this is not a
whole PPC object result. No new native/header definition is added in this unit.
Candidate event.cpp SHA256:
`177f46842cb81a9c96c647feb7fa9f3db23cc07af6a6cebc5edec1ef034b6b37`.

Exact receipts: read-release-refs-host.json, read-release-refs-cabin.json,
read-release-refs-sh4.json and read-release-refs-exec-regression.json.
Raw evidence is mirrored in the cache21-callers-20261021 evidence directory.
An early cabin fixture incorrectly expected Event unbind to retire a separately
fabricated reader; that failed scaffold remains preserved. The final fixture
uses actual Event bind/unbind and separately retains the prior real reader-clear
refusal control. The small-object qualifier completed successfully; its shell
tail used a CRLF filename and failed afterwards, without changing its receipt.

No linked program, asset bundle, Flycast run, release check, physical Dreamcast
acceptance, full-stack bound or performance improvement is claimed. General
last-reader lifetime, no-epoch acquisition refusal, module reversal and whole
reset remain separate integration/audit work. Recipes and production defaults
are unchanged.
