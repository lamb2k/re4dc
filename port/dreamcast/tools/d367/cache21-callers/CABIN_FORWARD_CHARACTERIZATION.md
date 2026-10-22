# Native forward exchange refusal and partial states

At41494aadc, test_cabin_forward_characterization.py passes13 UBSan cases.
Production source is unchanged by this unit. The fixture starts from an idle
descriptor and explicit logical destination0x1000. Actual command/setLoadToAram,
file-name/range/unit checks and native prepare publish condition4/generation41;
the actual prepared-epoch query is captured after that source load, before the
effect boundary or MemorySwap. The ordinary ARAM gap allocator is unexecuted.

Actual EvtReadMram/Sub and full MemorySwap bodies execute, with actual native
swap begin/scope, DMA admit/copy/callback/release/end and reverse-token query.
Provider certificate/input, module/heap allocation, effect Push/Pop, software
ARQ progression, flush, inactive DVD queue and outer borrow scope are explicit
boundaries. Real source effect owner-count/final-dispatch tests are separately
sealed in read-admission-effects-host.json; the new native fixture does not
requalify those registries or pretend to undo an effect release.

| Mode | Injected boundary/state | Native end state | MRAM / backing | Post token |
| --- | --- | --- | --- | --- |
| 0 | Complete exchange | Ready, role1, phase0, readers0, gen41 | event / displaced module | 41 |
| 1 | Reader arrives before swap admission | Reference, role0 | original module / no backing | 0 |
| 2 | Backing allocation refuses | Failed, role0, phase0 | original module / no backing | 0 |
| 3 | Provider refuses | Failed, role0, phase0 | original module / retained allocation | 0 |
| 4 | First transfer refuses before copy | Failed, role0, phase0 | original module / event | 0 |
| 5 | First copy completes, request release refuses | Failed, role0, phase1, readers1 | original module / event | 0 |
| 6 | Second transfer refuses before copy | Failed, role0, phase1, readers0 | original module restored / event | 0 |
| 7 | Second copy completes, request release refuses | Failed, role1, phase2, readers1 | event / displaced module | 0 |
| 8 | Epoch changes after first transfer | Swap, role0, phase1, readers0, gen42 | event / event; current owner retained | 0 |
| 9 | Source identity changes after first transfer | Failed, role0, phase1 | event / event | 0 |
| 10 | Module allocation ceases to be current after first transfer | Failed, role0, phase1 | event / event; no stale restore | 0 |
| 11 | Epoch changes at effect boundary, new exchange completes | Ready, role1, phase0, readers0, gen42 | event / displaced module | 42 |
| 12 | Module pArc changes at effect boundary | Reference, role0 | original module / no backing | 0 |

The current outer caller reports success, publishes output and sets swapped1
in all13 cases. It called Push once and never Pop. Thus reverse_token positivity
alone is insufficient: mode11 has a positive new token42 while the captured
operation owned41. Mode7 retains the only displaced module bytes and a real
pending native request lease; actual retirement predicates refuse it. A failure
must not clear these allocations or restore an old descriptor over them.

Source unit/read-table snapshots remain exact except the explicitly changed
source-identity mode; native owner/data states are asserted. The source rollback
after a phase1 refusal restores original MRAM only while its exact module/source
allocation remains valid. The effect state is not restored by that byte copy.
Epoch/module/source mutation cases are adversarial controls, not evidence that
every target callback/reset interleaving has been enumerated.

## Contract input for main

A bounded first-forward receipt can reuse prepared_epoch captured after the
actual source load and before effects, then require the same generation from
reverse_token after MemorySwap. Capture exact current unit, read row, module
pointer/pArc/size and allocation heap before side effects; validate current
identities again before allowing swapped/output success publication. A failed,
changed or partial native state must returnfailure with output0 and retain
current carrier/allocations without blind Pop, deletion or stale restoration.

The prepared query intentionally excludes repeated role2 forward exchanges;
non-cabin/no-epoch handling and actual effect rollback remain open. Requiring
the existing EVD_ARAM_ALLOC_RETRY query feature for a separate default-off forward
guard could avoid any new native/header code, but main owns that prerequisite
and integration decision. No forward runtime repair is included here.

cabin-forward-characterization-host.json pins all sources/extracted bodies,
commands, adapters and the under20MiB/fresh-floor source resource checks. Raw
mirror: cabin-forward-host-05. Earlier seeded-resident and intermediate controls
remain preserved. Existing actual cabin allocation retry42 cases per preflight
OFF/ON still passes after the shared fixture extension. No program/stage, private
asset, guest, release, physical Dreamcast, whole-stack or whole-epoch acceptance.
