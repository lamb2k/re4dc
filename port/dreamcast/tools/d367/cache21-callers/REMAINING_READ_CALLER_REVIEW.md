# Remaining acquisition and reversal review

Read-only source review at a22ac26b5201f2c39cb1654c1237d75315278d20.
This extends READ_ACQUISITION_RECEIPT_MAP.md after the five bounded default-off
repairs. Main owns the remaining architecture and integration contract.

| Source path | Observed branch | Required ownership decision |
| --- | --- | --- |
| event.cpp EvtReadSub2467; datactrl.cpp setData911/getNewUnit930 | Fresh setData marks a free descriptor active and fills size/name; a failed SetRead returns without deleting it. | Retire only this exact still-unpublished allocation admission. Logging/recovery or reset between acquire and refusal must not allow a stale descriptor to be deleted. No generic generation producer is added yet. |
| event.cpp EvtReadSub2499 | Every prior read resets readEm.em and swapped before selecting ARAM/MRAM/module action. A previously swapped owner loses its role metadata even before this attempt can succeed. | A current owner receipt must distinguish reuse, promotion, new exchange and refusal before metadata publication. Existing Count does not encode these roles. |
| event.cpp EvtReadSub2521; emdata.cpp79 | EspEmDataSwapPush executes before SearchEmModule NULL/undersized checks. Push releases effect data; it is not merely an incremented counter. Failure branches delete the read and do not pop. | Validate the exact module/size/current allocation before releasing effects. A failure must retain prior role and effect ownership. Blind Pop is unsafe: Pop itself dereferences SearchEmModule(id)->pArc and can fail. |
| event.cpp EvtReadSub2533; dvd.cpp517 | MemorySwap is void; caller publishes swapped1 and output even if native swap admission returns early after a diagnostic. | Forward exchange needs an accepted completion receipt for the exact source generation, module allocation, range and role, as reverse already does. Do not treat the input pointer or void return as success. |
| event.cpp EvtFree2792; native_event_file.cpp528 | Cabin reverse uses existing reverse_token plus reverse_complete before metadata Pop/clear. Generic non-cabin path calls void MemorySwap then clears swapped. | Preserve existing cabin receipt. Generic reverse admission, actual effect restoration and last-reader lifetime remain unresolved. |
| event.cpp EvtFree2808; datactrl.cpp561/600/728 | CMND_CLEAR_DATA3 frees backing/clears address and condition but retains descriptor active bit1. Only setDelete/command4 clears bit1 and size. getNewUnit accepts only descriptors without bit1. | Backing retirement and descriptor reuse are different lifecycles. Determine whether the per-room retention is intended before replacing clear with delete. No gameplay exhaustion has been proved. |

## Production call and occurrence limits

The source tree has one SetRead call, inside fresh EvtReadSub after GetRead
misses. Ordinary repeated EvtReadSub calls reuse the existing registration
without increasing Count. Therefore EVD_READ_RELEASE_REFS repairs a reproduced
actual table/caller contract defect; its Count2/3/32767 fixtures do not establish
a gameplay occurrence or a need for thousands of registrations.

Actual preload-to-use pairs include r11c.cpp620 then723/768 (em0, flags2),
r304.cpp71 then140 (em from the room list, flags0x200), and r310.cpp106 then816
(module with synchronous preload). These are source call examples, not evidence
that an allocation/module failure occurred in a guest. The cabin retry fixture
uses synthetic r11cs00 bytes; it does not qualify r11cs20 or any private asset.

SetClear retains active bit1 by construction; this is source evidence and has
not been elevated to a reported route failure. Earlier source fixtures prove
backing free and exact table/carrier state under their documented boundaries.
No full allocator epoch, KOS callback/preemption, whole reset, real module
exchange, guest/release or physical-console acceptance is added here.

The bounded cabin retry remains based on the existing generation producer and
read-only query. Whole reset must freeze admission/preflight before its first
destructive action and preserve that contract across callbacks/yields; a local
descriptor comparison or short lock is insufficient. read.cpp remains read-only.

review-source-identities.json pins the exact inspected source bytes. No program
or asset is built or staged by this review.
