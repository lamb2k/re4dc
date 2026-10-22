# Original r202 extra wave residency

The original area23 callback sets room-save bit6 and sends ESL49/4A while the
four-enemy budget is full. The preserved diagnostic starts inside that source
area, then uses the existing source-damage hook for ten deaths. Both the old
cap4/nonbinding16 mechanism check and the current matched data check retain all
queued entries; no cap deletion or parking is used.

Current c18oemW compares the same executable, initial inputs and every disc
payload except resident.bin. V7 has31 late uploads. V8 preloads those31 existing
winning packages (150224B including headers), and has zero late uploads,
evictions, retries, refusals, TEXCHK failures or sound-fit failures. CAST-GC and
NOT-DRAWN pass. Both arms peak at4 physical enemies, complete ten source-damage
death cycles and finish with no held enemies. This is not normal player combat
or a full room/route completion claim.

V8's last observed VRAM is396992 pinned /1356480 dynamic /723840 free /
671744 largest block. Peak pinned is1753472. KOS minimum33360B with49152B held.
The resident union has5562 records: all5531 prior records remain exact, onlyr202
gains31, and its public list grows72→103. Existing package bytes, source image
metadata, meshes and audio remain unchanged. The data set and SHA256SUMS are
mirrored onC as castle18-front-resident-v8-20261019; manifest:
6e8f422d7e363fa717e16fee6e061184f54eabafdb09c56ac09f5bf962f676a3.

The local-wrapper alert command was audited before adding a replay patch.
Both exact source entries are type7/set0xE. Em11Init constructs the common
cEm10; EmSetFromList2 calls em->move synchronously; em10InitRtnSet case0xE
sets ACTIVE and calls setFindPL before returning. The script's later wrapper
setFindPL duplicates that state. Delayed creation therefore establishes the
same alert without a pending-command mechanism. This conclusion applies only
to these two audited entries/initializer paths.

Private matched proof:
r202-wave-v8-matched-qualification-v2-20261019.json, SHA256
b83169e626bbbc6004e9ce6a9a724c242e3054db898c58ef9d2a6a3bd977a8f7.
V2 corrects the initializer function name in the source attribution; gate bytes
and observations are unchanged. NativeK remains an immutable V7 continuation;
no old production snapshot is retargeted. Its original partner route, r200's
door-loading uploads, and the rest of chapter3-1 remain separate open work.
