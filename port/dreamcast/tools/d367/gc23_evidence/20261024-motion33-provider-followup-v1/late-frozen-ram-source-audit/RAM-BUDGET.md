# GC work-RAM budget — source-bound audit, no runtime measurement

2026-10-24. Read-only audit of the exact full normal static1d63 OFF/ON catalog0
ELFs, retained section/segment/symbol maps and receipts, then current allocator
sources in `/root/work/lanes/gc-motion24`. No reserves, arenas, recipes, SDK,
objects, guest, assets or game source changed. Old scratch/backface work stays
parked. READBACK.json pins the inputs and arithmetic; audit_budget.py reproduces
it with streamed hashes and direct ELF-table reads, without target tools.

## Finding and next gate

The known 60,384B `_end` growth is real resident-image growth and a credible
source-heap capacity risk. **It is not measured loss from the production93,920B
H2 datum.** Under a coherent, otherwise identical early allocation trace, the
active4KiB fit formula can make that growth cost57,344 or61,440B of source arena.
It does not follow that KOS free bytes also lose60,384B, or that a particular
movie/room allocation fails.

No safe mandatory metadata reduction is established by this audit. First obtain
the exact current linked image price, then a separately admitted matched H2 and
source/KOS heap-shape observation. If that fails or changes source guards/spawns,
reduce genuinely resident code/metadata in a separately reviewed unit and rerun.
Do not change reserves, move the same live bytes into another scarce heap, shrink
detector capacity, or use fallback/absent geometry as proof of acceptance.

## Exact known binary, not the current combined full-programme price

Linked source `1d63cffe3a232c402418f2f2d919e7abae476957`, normal profile
`/root/probe/lanes/route/out-rrfb254e8rP`, baseline fb254e82. Exact ELF hashes
were freshly reread and matched the retained receipt:

| | OFF | ON, catalog0 |
|---|---:|---:|
| ELF SHA256 | `9d199189e9326a089e61a1a76077dc98308e8f0b831694e368ef9cb51ca0de57` | `2f7e505e7a1002f863c5dad3864530c80a68b69c51af2b972d767ca412426d45` |
| `_end` | `0x8c4320b4` | `0x8c440c94` |
| size-tool text | 2,693,812 | 2,737,180 |
| size-tool data | 675,588 | 676,324 |
| BSS | 962,900 | 979,828 |

Text+43,368/data+736/BSS+16,928 sum61,032B; actual end displacement is60,384B
because section placement/alignment is not a plain sum. ELF disk lengths/debug
growth are not RAM price. Raw programme hashes are OFF49a4173a...6090b and
ON0c5c530d...f5636. Parent's OFF production/all14 identity proof is retained;
this audit did not redo every overlay/asset comparison. No separate linker.map
was found here: actual ELF section/program/symbol tables were read and cross-
checked with the retained maps, rather than inventing a map-file readback.

Current gc-motion24 allocator files mem.cpp/os.cpp/ui_bridge.cpp/main_mem.cpp/
game.cpp/OSAlloc.c/Makefile are byte-identical to linked1d63. Current catalog a132
and Motion UNKNOWN source are newer than this full image. Catalog's selected-
object pricing1395B (or synthetic-pin1502B) and Motion's raw24B state are not a
current full-programme `_end` price: they do not include all link placement,
retention, strings, runtime handles, stack, or a real installed catalog. Do not
add selected-object figures to the old H2 datum and call it a measurement.

## Actual normal allocator selection

Both exact resolved files select:

| Setting | Value |
|---|---:|
| ARENA_FIT | 1 |
| ARENA_FIT_KOS_BYTES | 196,608 |
| ARENA_KOS_BYTES | 32,768 |
| SOUND_REGION_BYTES | 393,216 |
| CORE / OPTION / PLAYER / WEAPON | 1,360,608 /149,920 /869,728 /275,424 |
| IMAGE_PAD_BYTES / KOS_SQUEEZE | 0 /0 |
| SS_FREEZE_RESERVE_BYTES | 16,384, already part of image/BSS |
| LINK_TIGHT / LINK_OVL_HELPERS / KOS_SBRK_LAST_PAGE | 1 /1 /1 |

The fixed sound/archive carve is **3,048,896B**. Native static reserve is81,920B
plus its declared allocation/header allowance; parts reserve73,728B, actor palette
bank40KiB and existing motion backing/reserves remain selected and unchanged.
These have distinct owners/lifetimes; do not add them as interchangeable spare
RAM. LINK_TIGHT removes the historical empty8KiB-aligned .sub padding, so an old
8KiB linker cliff is not the normal selection here.

The real KOS archive is freshly pinned
`5e2d867fb5825e7825e1843f2542446288e18c383341a58426e452a0b620daaf`.
Its source tree HEAD804b3195 has existing unrelated dirty PVR changes; this audit
did not mutate or certify those. Relevant allocator files are individually
pinned. Importantly, both builds explicitly link their private `kosmm/mm.o` from
the patched mm.c. It uses `new_base > limit`, not stock `>=`. OFF/ON private source
bytes and allocated object-section bytes match; whole object hashes differ in
non-allocated metadata. The last4KiB page recovery is **already enabled** and
cannot be counted again as a mitigation.

## Source formula and its limits

Selected mm_init starts its break at `align4(end)`. `_sbrk_r` delegates to mm_sbrk;
dlmalloc uses sbrk,4KiB pages and no mmap. Exact ELF words give normal stack top
`0x8d000000` (32MiB alternative `0x8e000000` also exists); with normal16MiB and
64KiB kernel stack, `L=0x8cff0000`. Patched mm_sbrk permits a break equal to L.
This audit did not observe which memory mode a guest selected.

mem.cpp:61-107 computes:

    Wmax = 13*1048576 - 32768 = 13,598,720
    B = sbrk(0)
    T = mallinfo().keepcost                  # top chunk, not all free holes
    R = max(L-B,0) + T
    Ffit = floor4096(max(R-196608-64,0))
    W0 = min(Wmax,Ffit)
    Wsuccess = W0 - 4096*k                  # k>=0, actual memalign failures

It stops/fails if the request falls below fixed carve+3MiB. The32KiB ceiling
adjustment and192KiB fit target are **not additive reservations**. With a coherent
snapshot, even the optimistic fit bounds using R<=L-align4(end) are OFF12,111,872
and ON12,054,528B, both below Wmax. Under that model the fit clamp is active.
For equal translated pre-arena allocation trace, `R_on=R_off-60384`; all possible
4KiB residues give a fit reduction of57,344 or61,440B. The script enumerates all
4096 residues to check this arithmetic, not to simulate runtime allocation.

The fit reserve is a target, not a protected pool/guarantee. mallinfo and sbrk
are separate snapshots; memalign later takes its own allocator lock. KOS threads,
free/reuse/trim state, page-growth corrections, alignment padding and retries can
change the actual request/pointer/headroom. dlmalloc memalign requests padded
space, can free leading/trailing fragments, and may grow the break in pages.
Consequently the coherent bounds and two conditional deltas above are not a
universal run-to-run inequality or an assertion of actual successful arena size.

## How capacity reaches source heaps

OSInit calls re4dc_mem_init, then sets SDK arena bounds. SystemMemInit uses
`heap_start=arena_lo+3,048,896`, aligns32, and OSInitAlloc places13 normal12B heap
descriptors there (156 rounded to160B). The selected release SDK shims do not
enable the debug descriptor expansion. Initial heap0 capacity, before individual
cells, is therefore `Wsuccess-3,048,896-160`; it is not initial free payload.

MemReplaceHeap shrinks a parent to its **highest ending live cell**, then creates
the next heap over the tail. Stage/game/DLL paths create heaps1/2/3; normal
gameRoomMemInit replaces3→4 and selects4. Thus Heap4.start is a lifetime/high-
address result, not merely a fixed subtraction. Native room cells carry their
own32B headers; tagged source allocations and OSAlloc alignment/headers add cost.
OSCheckHeap's exact successful result is:

    free_payload = heap_range - sum(allocated_cell_sizes) - 32*free_cell_count

Largest contiguous allocation is different again. Equal requested byte totals
do not prove equal free-list shape. Under unchanged prior allocations an arena
capacity reduction can carry into the room tail; changed reserves/guard outcomes,
loads, reclaim/loans or spawn choices can change that trace.

KOS is a different allocator. Its observed aggregate headroom helper reports
`mallinfo.fordblks + max(L-sbrk(0),0)`; top-contiguous capacity instead needs
keepcost+break room, with other holes separately counted. Fixed fit budgeting
usually charges image growth to source arena rather than subtracting the same
growth again from KOS free bytes. GC catalog file handles/transient reads can
consume KOS separately: KOS fs_open wraps handles with malloc; current catalog
keeps one exact handle across failure/retirement until safely closable. Catalog0
does not exercise the valid-pin open branch. Streaming validation uses bounded
scratch, not a heap copy of the full index; configured branch and exact IO/stack
cost still require the actual candidate.

## H2 and apparent savings

The retained qualification says s30 `heap_before=93920` under H2,340/340 and
restored1. It is **not Heap[2] capacity**. native_movie samples
re4dc_ui_heap_free(), which queries the **current source heap**, after selected
motion/cell/far-shell loans/releases and before file/header/staging work. A room
normally selects Heap4, but that counter alone does not name its handle. Stage
allocation may use the movie-world arena token instead of the current heap; it
can lend/reclaim other blocks. The93,920B value is not a promised staging block,
a contiguous maximum, or a safe budget to subtract60,384 from.

The exact ON ELF exposes members4,608B, seen2,048B, audio queue1,664B,
banks1,176B, unknown-assets800B, tickets384B, archives320B, among other state.
Reducing those capacities needs new adequacy/overflow/ownership proof. The UI
texture Entry adds two4B fields in source, but **actual entries[] stays100,352B
in BOTH ELFs** (448x224): alignment absorbs them here. Shrinking those fields
alone cannot be advertised as3,584B linked savings. This corrected an initial
nominal-field estimate during the audit. The larger contributor is linked code/
rodata, not just the16,928B BSS increase. No reduction is implemented/proven here.

Before memory acceptance root should bind the current full OFF/ON/pin/profile
price, existing reserve selection, actual arena/base/size, KOS free/top/holes,
source current-heap handle/range/free/largest at relevant phases, and matched H2
completion/restoration plus source allocations/spawns/fallback outcomes. Keep
configured-catalog costs distinct from catalog0. If a diagnostic image prevents
a package from loading or alters admitted source allocations, a clean/no-fault
guest is not equivalent coverage or a performance gain.
