# Forward receipt: fatal and returning diagnostic qualification

Read-only follow-up after `fe82efa8b53173a12e55fa85dc82addb3d451341`.
The forward runtime source and all three sealed bf250 fixture files are checked
byte-for-byte against `bf250af8e`; none is edited. Existing receipts stay intact.

`platform/mem.cpp` implements `re4dc_missing` by logging and sleeping forever.
The original native13/expanded120 controls explicitly allowed that diagnostic
to return. A success observed after such a return is source compatibility
evidence, not proof that the current target publishes success after a fatal
native refusal.

## Replay results

The sealed original120 OFF/120 ON returning suites pass again. A new isolated
driver then captures480 observations:120 cases for each forward guard OFF/ON
and returning/strict-stop diagnostic boundary. The strict process records state
at diagnostic entry and exits without unwinding automatic objects. It avoids
incorrectly running MemorySwap's borrow-scope destructor, which the real fatal
loop would never reach. Crash hooks, logging/sleep scheduling and target
hardware are not executed by that host boundary.

| Forward guard | Diagnostic | Halt at native diagnostic | Return0 | Return1 |
| --- | --- | --- | --- | --- |
| OFF | Returning compatibility | 0 | 0 | 120 |
| OFF | Strict nonreturning | 54 | 0 | 66 |
| ON | Returning compatibility | 0 | 104 | 16 |
| ON | Strict nonreturning | 46 | 60 | 14 |

The original native-mode projection0..12, prior read/effect refs1, gives:

| Forward guard | Diagnostic | Halt | Return0 | Return1 |
| --- | --- | --- | --- | --- |
| OFF | Returning | 0 | 0 | 13 |
| OFF | Strict | 11 | 0 | 2 |
| ON | Returning | 0 | 11 | 2 |
| ON | Strict | 10 | 2 | 1 |

That projection uses the expanded sealed bf250 fixture's current module/effect
adapters; it is a mapped review of the earlier13 mode identities, not a claim
that every older adapter was identical. `forward-diagnostic-native13.json`
records the selection and exact480-case file hash.

## Which source publications survive strict native behavior

| Modes | Control | Strict OFF | Strict ON |
| --- | --- | --- | --- |
| 0 | Complete original exchange | Return1 | Return1 |
| 1 | Initial global reader / no prepared epoch | Halt | Halt; initial unsupported path unchanged |
| 2..3 | Backing allocation / provider refusal | Halt before final caller publication | Halt; post-swap caller branch not reached |
| 4..10 | DMA refusal/partial, mid-copy epoch/source/allocation changes | Halt before final caller publication | Halt; partial/current native state retained |
| 11 | Epoch replaced after effect release | Completes under new epoch42 and returns1 | Returns0 before exchange |
| 12 | Module pArc changed after effects | Native admission halts | Returns0 before exchange |
| 13..20 | Module binding/size/heap, row/readEm/unit/table changes after effects | Native exchange returns; caller publishes1 | Returns0 before exchange |
| 21 | Global reader arrives after effects | Native admission halts | Returns0 before exchange |
| 22..24,26 | Row/readEm/unit/module size changes after second copy | Native completes; caller publishes1 | Returns0 after native completion without stale publication or rollback |
| 25,27 | Module binding / heap changed after second copy | Native completion diagnostic halts | Same halt; caller post-check not reached |
| 28..32 | Initial nonmatching rows / real repeated role2 | Return1 | Return1; explicitly outside bounded receipt |

Thus54 original unguarded success observations disappear when native fatal
behavior is respected. They must not be described as current target false
publications. Of the66 strict unguarded returns,52 are injected changed-receipt
callbacks rejected by the new guard, and14 are the complete original exchange
or deliberately unsupported legacy inputs. The guard also turns eight
pre-swap fatal controls into ordinary refusals. These are source-contract
results; the mutation callbacks remain adversarial and have not been proved
reachable in a production effect release or real route. Some mutate a field
without demonstrating a functional native exchange defect. Conservative receipt
rejection does not turn every such field change into a gameplay bug.

## Side effects and output guarantees

Effect Push executes before every tested native failure or post-Push rejection.
The real owner count becomes refs minus one, with final release dispatch for
refs1. No Pop/effect rollback occurs. Strict fatal cases cannot reach later
caller success, error-return or cleanup statements.

EvtReadSub initializes output to zero on entry. Fresh reads subsequently write
the cached module address before the exchange; that value remains nonzero at a
fatal diagnostic. Prior reads retain entry zero at the same boundary. Therefore
the guard's error-return/output-zero guarantee applies when its rejection branch
is reached; it is not cleanup executed while a native diagnostic never returns.

Mode7 preserves native Failed/role1/phase2/readers1, one pending request and the
only displaced module bytes in backing. At the strict stop, MemorySwap's borrow
scope is still active. Other DMA/completion fatal controls likewise preserve
their in-scope state; no host exception unwind fabricates a completed scope.
The actual outer media-borrow implementation is still a fixture boundary.

Modes22/23/24/26 demonstrate a further bounded limit: physical exchange can
complete before the caller rejects changed metadata. It returns0 with output0
and retains the carrier/current state instead of publishing swapped1. This is
refusal to publish, not rollback, reverse eligibility or a recovery guarantee.
Archive effects/controllers/native metadata borrowers remain under main's A11
lifetime contract and are not certified by this replay.

## Identities, evidence and scope

`forward-diagnostic-host.json` records full source hashes, the exact sealed
bf250 comparisons, compiler commands, driver/adapter hashes, aggregate results
and the480-case raw hash. Current fatal diagnostic source is pinned too.

Raw source, binaries, sealed returning controls and cases.json:
`C:/Flycast-Evidence/re4-dreamcast/cache21-callers-20261021/cache21-callers-forward-diagnostic-20261022-02`.
Initial host01 is preserved: its expected prior-output sentinel was corrected
to the source's actual entry zero. No runtime source or sealed test changed.
The unit stays below20MiB and enforces a fresh18GiB plus128MiB compiler floor.

Provider/allocation/software ARQ/module lookup/effect subtable/callback/Host64
projections remain those declared by bf250. No whole program, staged image,
actual hardware ARQ, Flycast, route occurrence, release, physical Dreamcast or
performance acceptance is added. Main owns integration and broad lifetime
implementation; Claude retains production merge/release ownership.
