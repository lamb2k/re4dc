# Test 21 dam first-villager crash: executable identity

The report is a real Dreamcast/GDEMU fault. Current QA success cannot close it.
No repair or physical-console acceptance is claimed by this investigation.

## Bound executable

Source: `fe0efcddc736c49861b51988593629ca04ced336`, public tag
`test-fe0efcdd-20261020`. The retained public checksum independently verifies
the recovered GDEMU ZIP:

`0966cfab8f9bb9d47e8b88fa7ad9d52c045478bc9e3e005093e1af3cba300a5e`

The source rebuild uses the Test 21 RR chapter-2 recipe, including
`ROUTE_CH21_FULL=1`. Direct `t15-build.sh rP` alone omits that release's chapter
flags and is rejected. The correct rebuilt raw program and all 14 overlays are
byte-identical to the public package. The original source path is therefore no
longer the only executable-identity evidence.

| Artifact | SHA256 |
| --- | --- |
| Raw public program, 3,291,104 bytes | `bd0970c0f745edee5418d17afde33d138ce2ec3d8ec870ef95a3a17e0439c62e` |
| Rebuilt stripped ELF | `f20db31f4b42f1ef19b6639bc274deb8607ce992b64d89e969af625d1be3cad2` |
| Public st1_2.ovl | `f8a2931d0c7b4c463e28b7f74077fc6b81f89a022d02f77af6d09abad2ba96f4` |
| Rebuilt final pre-strip ELF | `6ec7f52d09ba6f90035b915cfaee031301ede83663b53e0210a0ed6066698fbe` |
| Public r10c.dar | `330ead65e8d05e02da2c89250b3c5db942963d8b5e89eed168323dd53507b1c3` |
| Public em12.drs | `137c4cd20f9941eb0012102f93a7f818173968f6d84f4d462bacf0e599cc43a5` |

The final pre-strip ELF's 14 overlay sections also independently match all
published overlay image bytes. The intermediate `pass1.elf` does **not** match:
the final link moves overlay-only helper functions and changes symbol addresses.
It must not be used to symbolize this crash.

`tools/d367/verify_release_identity.py` verifies the raw program, the complete
overlay filename set and bytes, and optional pre-strip sections. Its report
always leaves runtime relocation verification false. Actual Test 21 inputs
pass 15 files and 14 sections. The t15-only rebuild fails the same verifier.

## Hardware-location constraint, still an inference

The preserved photo reads fault `0e0`, PC `8c890d9a`, PR `8c890d8c`, address
`4328e417`, UI frame `309676`; r1 is `4328e3ff`. The fault address is r1 + 24.

In the exact public st1_2 image, `r10c_EmEvent` calls `EmSetFromList2(2, 1)`;
its return is offset `42ac`. The first virtual `setNoSuspend` dispatch loads
`mov.l @(24,r1),r1` at offset `42ba`. These two positions imply an image base
`8c88cae0` from both photographed PC and PR. That base is an inferred candidate,
not an observed hardware module address.

Enumerating all overlay instructions under the assumptions of a 32-byte-aligned
image base, the photographed r1-relative load and the preceding `jsr` return
finds three sites: this r10c event, `r11d_execEmAppear`, and
`r208_operateCrank`. Only the first agrees with the reported dam room. The
accepted-source-mapping field remains false pending independent relocation
evidence. An older QA log's module base is a different executable and cannot
supply that evidence.

## Source lifetime frontier

`R10cInit` prereads Ganado 0x12. The first event creates list entry 2, clears
its set field, then immediately calls the actor's virtual `setNoSuspend`.
`EmSetFromList2` creates and initializes the actor and calls `em->move()` before
returning it. The entry is explicitly exempt from cap deferral, so cap 4 alone
does not explain a rejected spawn.

`EmSetFromList2` can return `errEm`, initialized to null, after list checks,
pool exhaustion or constructor/read failure. This caller has no failure check.
That is a confirmed source hazard; it does not establish why the photographed
vtable value is malformed. A null check alone would neither explain nor repair
that corruption. Any repair needs the original list/room-flag transaction,
actor identity and safe retry semantics preserved.

The cached `EmReadSearch` path selects by module ID, installs `pInitFunc` and
returns `pArc` without yielding before the constructor call. A cache miss can
sleep during the DVD read. Investigation continues through the first actor
move, possible scheduler yields and owner retirement. event/read changes are
coordinated with the cache caller lane.

## Private receipts and limits

Evidence root:
`C:/Flycast-Evidence/re4-dreamcast/issue52-crash-20261021/`.
Receipts: `public-test21-recovery.json`, `exact-test21-binding.json`,
`final-full-identity-verification.json`, `rejected-t15-only-verification.json`,
`exact-test21-overlay-binding.json`, `hardware-relocation-candidates.json`.
ELFs, disassembly, resolved flags and logs are retained in `exact-test21-build`.
The original three issue photos remain in `issue52-20261021`, unchanged.

This milestone ran source builds and artifact checks. It launched no guest,
staged no disc, changed no runtime or production recipe, and made no release
or physical Dreamcast acceptance claim. Public package identity does not prove
the reporter's SD card bytes.
