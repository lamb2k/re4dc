# Bounded read admission preflight

`EVD_READ_ADMISSION_PREFLIGHT=1` defaults0 and affects Dreamcast EvtReadSub only.
For a missing read, before DC.setData it checks that the name fits the actual
table limit and one of the first eight table slots is available. A known
impossible registration returnsfailure before file lookup or acquiring an
active descriptor. It does not reserve a slot across later file/logger work.

For an existing read with nonzero swapped metadata, it returnsfailure before
resetting readEm or attempting promotion. The current exchange must be retired
by its owner first. Ordinary unswapped ARAM preloads still promote to direct
MRAM or the requested module, including reuse while all read slots are full.
Count is not used as an Event/DMA lease. No stale unit is deleted after a logger
or other external callback, and no new global generation state is introduced.

## Qualification

test_read_admission_characterization.py --preflight-pair passes10 OFF/25 ON
cases per CABIN0/1 under UBSan. Actual EvtReadSub/Mram, SetRead/table, dataCtrl
setData/getNewUnit and unit command/wait/clear/delete bodies execute. File size,
unit-availability/native policy, transport completion, module/effect/swap are
explicit boundaries. These are synthetic source controls, not target files.

OFF reproduces32 leaked active descriptors after32 initial capacity refusals;
ON makes zero FileExistCheck calls and acquires zero descriptors. Null, negative
capacity, full ordinary table, overlong name and an oversized table whose only
free slot is8 refuse before acquisition. Name47 and slot7 positive controls
succeed. Prior swapped1/2/255 read re-admission modes preserve exact row/unit/
readEm; no transport, exchange or free occurs. Existing unswapped full-table
preloads succeed for em0 and em1. Prior-name lookup therefore remains permitted.

A deliberately changed table during FileExistCheck still leaves its newly
acquired descriptor after SetRead refusal. This remains an explicit negative
control: preflight does not close acquisition identity across callbacks or
yielding work. Other module failure and void-swap false-success controls remain
unchanged. Actual clear-vs-delete characterization remains a separate lifecycle
question, not a reason to replace all clears with deletes.

The existing exact CABIN allocation-retry fixture passes42 cases with this new
guard both OFF/ON, executing real native/source query/install/clear predicates.
Prior outer failed-start regression passes146 OFF per cabin/153 ON cabin0 and
154 ON cabin1 with this new guard off.

Four whole stripped SH4 event.o disabled identities match d21bd80a6 across
CABIN0/1 and EVD_ADMISSION_TXN0/1. Omitted/default and explicit0 commands match.
ON adds301 text bytes in all four objects; data4/BSS640 are unchanged. EvtReadSub
static48-byte frame is unchanged in this guard's objects. This does not replace
the separately reported196-byte frame when CABIN allocation retry is enabled.
Invalid values reject; selected PPC EvtReadSub preprocessing is identical.

Candidate source SHA256:
`ae27d08f41aed2e4715ca28c0cf010d6d33e7a87106c41ef049cb5b3f1e2bb91`.
Exact read-admission-preflight-{host,sh4,cabin,exec}.json receipts and mirrored
raw output retain commands, source identities and boundaries. Fresh source
output floor/budget is checked; final host output is below20MiB. Earlier
scaffolds remain preserved. No full program/stage, asset, guest, release,
physical-console, whole-stack, whole-epoch or performance gate is claimed.
