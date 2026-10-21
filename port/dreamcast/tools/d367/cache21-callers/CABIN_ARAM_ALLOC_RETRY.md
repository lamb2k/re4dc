# Exact cabin preload retry after allocation refusal

`EVD_ARAM_ALLOC_RETRY=1` defaults zero and requires `CABIN_SOURCE=1`.
Make applies it to event.o and native_event_file.o. It adds a read-only query of
the existing carrier generation and a bounded direct-read failure repair;
there is no second generation table, lock across callbacks, recipe change or
general reset implementation.

The query accepts only the exact current immutable prepared CarrierReference:
unit/logical range/size, valid published generation, role/phase zero, no backing,
installed MRAM, module, Event, DMA reader or retirement in progress. Actual
source-unit validity and retirement-readiness predicates must agree. It never
changes a carrier, unit, counter or admission state.

EvtReadSub captures that epoch only for a pre-existing em0/ARAM-to-MRAM read
whose original unit is condition4 with no owned MRAM, fixed destination, pending
command/error or swap role. It also snapshots the exact ReadTbl row and readEm.
After real allocation refusal, the accepted epoch and every unchanged unit/row
byte must still match. Only this attempt's command, arg, wait, m_wait, error and
dest fields are restored. The original logical source, Count, metadata and
carrier survive for retry. The unique error1 pattern precedes installation/DMA;
partial installation or another error cannot satisfy it. A captured receipt
that later changes is retained as current state and returns failure without a
stale restore or fallback clear. Initial no-epoch/non-cabin contexts keep their
existing path and remain outside this repair.

## Actual-source qualification

`test_cabin_aram_alloc_retry.py` passes33 OFF and42 ON cases under UBSan. Actual
EvtReadSub/Mram, cDataUnit setLoadToMram/command/condition/wait/allocation
metadata/clear, source-unit validity/retirement/release, and native carrier
query/install/clear/retirement/before-free bodies execute.

Original command wait0/1 and ReadTbl Count1/2 cases retain complete unit,
ReadTbl, readEm, EVD/bin, carrier and synthetic source-data bytes after the two
real refused allocation attempts. A subsequent successful allocation executes
actual carrier installation, source metadata publication and normal final
clear/release. There are26 observational query refusal contexts, null/range
controls, and nine allocation-boundary changes to epoch, read row/metadata,
unit identity, accepted readers or DMA ownership. A changed receipt receives
neither restoration nor destructive cleanup. Actual native clear still refuses
an existing reader. No accepted epoch keeps the old destructive caller path as
an explicit negative control.

Allocator success/refusal, certified provider bytes, source allocation/free and
module services are explicit exact-pointer/size/heap boundaries. Provider input
is synthetic. Native source-unit and carrier refusal predicates execute rather
than being replaced with a boolean model. Adversarial allocator mutations do
not prove absence of every possible reset/callback interleaving. Host64
projections and native32 cast adapters remain documented; target layout and
real allocator/recovery/KOS scheduling are not accepted by this test.

The actual query body is independently exported for observational tests in
both host arms. Disabled native object identity separately proves the query is
absent with the switch off. SetEvt/create/scenario/reverse bodies in the inherited
fixture compile closure are not newly exercised by this allocation unit.
Prior outer-failure tests also pass146 OFF cases per cabin and153/154 ON cases
with this new switch off after the fixture extension.

Existing successful EvtFree on Count2 still clears a unit while Count1 remains
registered. Initial no-epoch read cleanup can still drop ReadTbl after native
clear refuses. These are separate open shared-release/acquisition contracts;
this bounded retry does not certify or repair them. Module exchange and whole
reset retirement remain main's architecture work.

## Object qualification

`qualify_cabin_aram_alloc_retry_sh4.py` checks whole actual event.o and
native_event_file.o against `06f598ba5`, in CABIN0/1 arms. All four disabled
identities pass, and default/explicit-zero compiler commands match. Enabled
commands define the guard for both translation units; the event reference and
native query definition are present. Invalid values and absent CABIN
prerequisites reject in Make and selected direct source contracts. Selected
PPC EvtReadSub preprocessing is unchanged.

ON event text grows776B and native text grows472B. Data/BSS remain unchanged:
event4/640, native0/929. EvtReadSub's static frame grows48 to196B; the query's
static frame is40B. These are partial static frames, not dynamic high-water,
whole-call-chain maxima or a remaining-stack guarantee. No linked-program or
overlay identity is implied by these object checks.

Exact source identities:

- event.cpp: `d9b88f7d8ca201a0a59bee6801711c001a0dcf725da219ea481f10481ae6694e`
- native_event_file.cpp: `ab5f2f85b530e9237cb4eb60acd49a332400351f9e066aab2e675179f9e37db2`
- native_cabin.h: `d47467dfb29a17dd344c03cb45f77408ba89914343499edd03646844bada5660`

Receipts `cabin-aram-alloc-retry-host.json` and
`cabin-aram-alloc-retry-sh4.json`. Raw mirrors are in
`C:/Flycast-Evidence/re4-dreamcast/cache21-callers-20261021/cabin-aram-retry-{host-07,sh4-01}`;
earlier scaffolds remain preserved. No full build, guest/screenshot, gameplay
traffic/timing, physical Dreamcast, production recipe, release or SD action is
included. Main owns review/integration; Claude owns production publication.
