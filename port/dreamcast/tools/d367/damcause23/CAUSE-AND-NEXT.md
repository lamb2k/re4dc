# Dam first-villager cause investigation, October 22

Status: **hardware cause open**. The exact Test21 source contains an unchecked actor-creation refusal in this event, and the integrated source already protects it. The photograph does not establish why actor creation failed, or even establish that the photographed actor pointer was NULL. No runtime change is justified by this source-only unit. Existing EM_READ_RETRY and NULL guards are unchanged.

This is an actionable continuation of issue #52, not closure of the hardware report. The next unit below separates the remaining alternatives without removing the current protection.

## Exact identities and scope

New isolated branch `codex/damcause23` starts at `origin/t15/int` **f047721fb138b9d7c1a4bf2edf217f76beda4d6c**. Root owns the independent `native_static.cpp` root-pose repair. This unit claims only `port/dreamcast/tools/d367/damcause23/`; it changes no game/runtime files and does not overlap allocator, texture, recipe, backface or inventory lanes.

The retained public Test21 programme **bd0970c0f745edee5418d17afde33d138ce2ec3d8ec870ef95a3a17e0439c62e** and all fourteen overlays match the reconstructed release. Its stripped ELF is **f20db31f4b42f1ef19b6639bc274deb8607ce992b64d89e969af625d1be3cad2**; the matching pre-strip ELF is **6ec7f52d09ba6f90035b915cfaee031301ede83663b53e0210a0ed6066698fbe**. Original source is **fe0efcddc736c49861b51988593629ca04ced336**. `st1_2.ovl` is **f8a2931d0c7b4c463e28b7f74077fc6b81f89a022d02f77af6d09abad2ba96f4**. These are executable bindings, not merely a source-path pin.

Original asset identities remain `st1/r10c.dar` **330ead65e8d05e02da2c89250b3c5db942963d8b5e89eed168323dd53507b1c3** and `em/em12.drs` **137c4cd20f9941eb0012102f93a7f818173968f6d84f4d462bacf0e599cc43a5**. The original area1 geometry and event-route receipt remain in `C:/Flycast-Evidence/re4-dreamcast/issue52-crash-20261021/dam-first-event-trigger-plan.json`. Old chain6/kill2 switch-and-ambush fixtures do not establish first-villager coverage.

`source-receipt.json` pins sixteen source blobs at the two revisions, the original photo and the existing exact-release/relocation/asset/trigger receipts. `exact-dispatch.txt` is a small excerpt of the retained disassembly, not a fresh disassembly or build. `audit-test21.py` reproduces the source/evidence checks without a compiler, emulator or process query. Original evidence remains untouched.

## Corrected photograph interpretation

Photo `issue52-01.png` shows fault0e0, PC **8c890d9a**, PR **8c890d8c**, address **4328e417**, r0 **00000000**, r1 **4328e3ff**, UI frame **309676**. It crops out r8.

With the previously inferred, independently unobserved module base **8c88cae0**, exact `st1_2` code places PC at offset42ba and PR at42ac in `r10c_EmEvent`. Other conditional candidates remain in the prior receipt; source mapping is still `accepted=false`. The reported dam scene makes r10c the relevant candidate, but does not turn the inferred relocation base into a captured hardware observation.

The exact instructions resolve an important ambiguity:

```
42a8  jsr @r0                  ; EmSetFromList2
42aa  mov #2,r4                ; delay slot: entry2
42ac  mov r0,r8                ; returned actor saved in r8
42b2  mov #0,r9
42b4  mov r9,r0                ; r0 overwritten with zero
42b6  mov.b r0,@(3,r1)         ; entry2.set = 0
42b8  mov.l @r8,r1             ; actor's first word
42ba  mov.l @(24,r1),r1        ; photographed fault candidate
42be  jsr @r1
42c0  mov r8,r4                ; delay slot: this argument
```

Therefore visible r0=0 cannot prove that `EmSetFromList2` returned0. Visible r1 is the loaded first word, not the actor address: nonzero r1 cannot prove a non-NULL actor either. Address4328e417 is exactly4328e3ff+24 and is misaligned, consistent with the candidate instruction failing before virtual dispatch.

**Correction to older inference:** the old admission report described an unexplained "photographed nonnull vtable fault" as separate from NULL refusal. The photograph establishes a nonzero loaded word, not a non-NULL actor pointer. Preserve that report's original bytes as historical evidence; this explicit note supersedes that stronger interpretation. Source-proven ordinary refusal and the hardware failure remain distinct until the missing actor value is established.

The retained literal-word search found4328e3ff once in the exact main programme as the two instructions `mov #-1,r3; shll16 r3` in KOS `tlb_miss_hnd`. That is a coincidence of bytes until a read origin is established. It is not overwrite evidence. If the physical console's mapped word at address0 were that value, NULL would be compatible with the photograph; **no console BIOS/low-address identity or value has been established**. A local Flycast BIOS would not answer that question and was not substituted.

The photographed `er` and `rdy` rows are also not disc-read evidence. Exact `native_ui.cpp:1294-1363` formats PVR latch state, SB_ISTERR bits since boot, graphics timeout/recovery counters and closed-scene sizes. They do not record `ReadCheckInfo`, queue admission, enemy module identity or an asset-read result. Their presence cannot establish a GDEMU read failure.

## Source-confirmed path and remaining alternatives

At original `src/st1/r10c.cpp:122`, room initialization calls `EmReadSearch(0x12,0,0)` but ignores its result; at146 it registers area1 until scenario bit1. The event sets scenario bit1 and clears the lower-bank flag before requesting entry2 at406. At407 it overwrites `entry2.set`; at409 it dispatches `setNoSuspend` without checking the actor. Event actor ownership, effects, motion and cancel-handler ownership follow that dispatch. Calling the normal event exit on admission refusal would release ownership that this prefix never acquired.

Original `EmSetFromList2` can return `errEm=0` for entry/list/death/duplicate filters and actual creation failure. Entry2 is explicitly exempt from the ordinary alive cap. A full raw game pool or failed sparse-slot preparation returns0 from `cManager::create`; a failed `EmReadSearch` returns0 from `cEmMgr::construct` before the initializer. None is distinguished in the original caller or the photograph.

Successful room preload also matters: cached `EmReadSearch` selects by module ID, installs the cached initializer and returns its archive (`read.cpp:750-760`). There is no DVD operation or yield on that cached path before constructor dispatch. A claim that the *event* read failed must first show that the room preload failed, the module was subsequently released/replaced, or this creation actually took the miss path. A package containing em12.drs proves availability in the package, not a successful read on the reporter's console.

On the miss path, original `readEmData` returns0 for absent file or any negative poll result. `src/game/dvd.cpp:1573-1587` returns **-2** when queue admission finds no free slot. `readCheckMain:1815-1859` distinguishes a negative request result, cancellation(-4), missing request(-5) and the queue's error result. The later synthetic -3 injection exercises a negative result; it does not prove that the original failure was queue exhaustion or match its actual -2 admission code.

On successful creation, `EmSetFromList2` executes the actor's first `move()` before returning (`em_set.cpp:870-884`). A returned actor can therefore need a separate lifetime check if initial movement retires it. The current source review has not established such a retirement or a mutation of its vptr for this entry. Likewise it has not established an invalid cached initializer, corrupt archive, low-address read or reused pool epoch. No new speculative guard or retry policy is proposed.

## Concrete next unit and fix decision

Keep the integrated retry/NULL protections exactly as they stand. Do not reopen the guard's gameplay choice in this cause investigation. Before any source mutation, claim exact files with root; allocator/texture diagnostics stay with their current owner.

1. Reuse the existing entry2-only `ISSUE52_ACTOR_DIAG` phase notes and trusted module registry. The current compact snapshot records phase/frame/room/module base/actor; it does not record a reason for failure. Propose a small extension only after root allocates it: record admission outcome (filter/full pool/preparation/asset miss), pool generation, module0x12 cached-versus-miss identity, actual request and final poll result. Preserve room/module/pool generation across a yielding miss, rather than treating room number alone as owner identity.
2. At safe live-owner points immediately before and after initial move and before virtual dispatch, copy the actor address and its first word only after validating that it is the currently allocated entry2 slot in the same pool generation. Do not dereference a candidate pointer in the crash handler. Do not scan all actors. Crash display reads copied telemetry only. Preserve full existing fault context and display r8 in the visible fault rows, so a future photograph captures the actual actor register.
3. Bind any future diagnostic programme/ELF/all overlays and r10c/em12 assets before runtime evidence is accepted. A trusted module registry snapshot supplies the actual relocated base. If root later allocates a hardware observation, capture the mapped low-address word only through a separately reviewed, safe mechanism and bind the console identity; no low-address read is authorized by this unit.
4. Follow one consolidated ordinary-input dam entry1 combat/event attempt. A later Flycast attempt can check route and telemetry plumbing, but cannot disprove this physical-console failure. No guest, image or hardware run has been allocated here.
5. Choose the repair from the observed boundary: repair the actual read/queue failure if the miss failed; repair pool admission/lifetime if its same-generation slot was unavailable or retired; repair a proved archive/initializer publication defect if that identity is wrong. A non-NULL vptr mismatch needs a valid slot epoch and its producer history before any cleanup can safely act. Retain current guards throughout and qualify the resulting ordinary success route as well as the observed refusal. Report a physical-console acceptance separately from source tests, Flycast checks and release checks.

No build, image, staging, guest, native-process query, production recipe edit, release, SD copy or third-party communication occurred. This unit is under1MiB including its sparse source checkout, new source/metadata, Git overhead, mirrors and reserve. Hardware cause and acceptance remain open.
