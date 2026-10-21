# Bounded first-forward exchange receipt

`EVD_FORWARD_RECEIPT=1` repairs false success only for an accepted prepared
first-forward CABIN receipt. Default is zero. Both Make and direct source reject
missing `CABIN_SOURCE=1`, `EVD_ARAM_ALLOC_RETRY=1` or
`EVD_MODULE_VALIDATE_FIRST=1`. No production recipe changes.

Baseline: `0b58098ee9dcb0b2a0ed3f74bfd437fda30ede19`. Candidate event source
SHA256: `c3671a9f6107ae9fa44320609cbb58df69c86d5211deb369d61a5aeb0788aeb2`.

## Source contract

After actual source load/wait and the existing module checks, before
`EspEmDataSwapPush`, capture a positive prepared epoch and the exact ordinary
temporary row, table storage/capacity, unit, readEm, module pointer/pArc/size and
positively identified current source allocation/heap. The initial row must match
the unit, `Etc=0`, `FlagBe8=3`, `Count=1..32767`, `dat2=NULL`, slot below eight,
and unswapped requested module. Count is a registration check, not a reader lease.

Revalidate the full receipt before effects and again after actual effect Push,
before `MemorySwap`. The latter stops an exchange after effect callbacks replace
the epoch, module, table, unit or allocation. After the void exchange, require
the same positive reverse token and exact current identities/allocation/heap
before publishing `swapped=1` and output.

An armed failure returns zero and clears output, including the fresh-path value
already written by `EmReadSearch`. It preserves current source/native metadata,
allocations, partially completed DMA request and displaced module bytes. It does
not Pop, free, delete, restore stale snapshots or reverse effect releases.

An initial zero epoch, repeated role2 or nonmatching initial row does not arm the
repair and deliberately retains legacy behavior. In particular, this switch is
not a generic acquisition, exchange rollback, reverse, reset or whole-epoch
contract. Those paths can still publish success without this receipt.

## Evidence

- `forward-receipt-host.json`: 120 OFF and 120 ON actual-source controls, fresh
  and prior reads, effect references one/two. Actual Controller admission/unit
  load, read caller, source-module predicate, effect owner/count/final dispatch,
  MemorySwap and native owner/DMA protocol execute. Controls include refused and
  partial exchanges, before/after ownership changes, initial zero epoch and
  nonmatching rows, and a real repeated-role2 exchange. Mode7 retains the only
  displaced module bytes plus failed phase2/readers1 request; actual EvtFree
  refuses without changing carrier/request/row. ON stops modes11/12 before
  exchanging replacement epoch/module storage. No effect rollback is asserted.
- `forward-receipt-sh4.json`: four whole stripped event.o OFF identities against
  the baseline across CABIN0/1 and admission transaction0/1. Both CABIN1 ON
  variants add 1236 text bytes; data4/BSS640 unchanged. EvtReadSub static frame
  is 196 to 384 bytes; the helper lambda is inlined. This is static object data,
  not full dynamic stack/high-water acceptance. Default equals explicit zero;
  invalid knob and three missing prerequisites are rejected. Selected PPC
  preprocessing is unchanged, without a PPC whole-object claim.
- `forward-receipt-aram-regression.json`: existing CABIN allocator retry42 cases
  with admission preflight OFF/ON, new forward switch OFF.
- `forward-receipt-module-regression.json`: actual effect/module28 cases in each
  CABIN0/1 and module-validation OFF/ON, admission preflight ON, forward OFF.
- `forward-receipt-exec-regression.json`: outer em0 caller146 OFF per CABIN,
  153 ON CABIN0/154 ON CABIN1, forward OFF.

Each source receipt records extracted bodies and file/test hashes. Fresh controls
execute actual setData/getNewUnit; file existence/size and gap allocation are
controlled services. SearchEmModule, cached EmReadSearch, heap/provider,
software ARQ progress, flush, null DVD queue, returning missing diagnostic,
outer borrow scope and five effect-subtable helpers remain explicit boundaries.
Host64 types and ReadModule pArc/size projection are not native-layout proof.
No private assets, actual hardware ARQ, renderer registry or callback scheduler
are certified by these source controls.

Raw outputs are preserved under
`C:/Flycast-Evidence/re4-dreamcast/cache21-callers-20261021/` in
`cache21-callers-forward-receipt-host-20261022-02`,
`cache21-callers-forward-receipt-sh4-20261022-01` and the three corresponding
`*-regression-20261022-01` directories. Each unit stays below20MiB. Source-only
edits were made during the resource hold; compilers resumed only after root
cleared the hold and fresh guards admitted them. No full build/stage/guest ran.

## Integration limits

Main owns holistic reset/lifetime review and integration preparation; Claude
retains production merge/release ownership. Full program identity, stack and
memory high-water, matched Flycast route, release checks and physical Dreamcast
acceptance are still required separately. This change has no performance claim.
Window restoration remains disabled after its measured extra102 requests and
168032 bytes. No recipe, release, SD or external contact action was performed.
