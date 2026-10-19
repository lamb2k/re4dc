# Original inventory message field audit, 2026-10-19

The far-Ashley rejection reaches its authored completion through normal A, but PieceCommand remains in mode3 with an empty frame. The independently read frozen e86 ELF c9f614 and original saved-state chain locate main RAM with three unique256-byte executable anchors. MessageControl.mes starts at8, Message is236bytes, and its fields start after the virtual pointer: slot1.flags2 is cMes+104hex. The source alias CMES_FLAGS usesFChex, which is the actual be_flag. Before A both values are1. After A, original code01 marks flags2=2 and clears be_flag to0; m_pMes advances from8C8EE374 to8C8EE376, r_no_0=1, and Loop remains1. No guest writes or extra test capture were used for this audit.

Source references: include/mes.h already documents the platform layout and supplies typed getMes; src/game/mes.cpp code01 marks completion; src/Sscrn/ss_pzzl.cpp201/1870/2825 use the legacy alias to await completion. Its second alias CMES_RESULT1D1hex should access signed slot1.m_sel, actually1D9hex. The latter is read only by PieceSelect's original yes/no transition at2057. That is a source/layout risk, not a claimed guest yes/no failure.

## Proposed bounded change (not yet implemented)

Only src/Sscrn/ss_pzzl.cpp and port/dreamcast/game/subscreen.mk, plus owned tests/docs. New SS_MSG_FIELDS defaults0, accepts only0/1 and requires SUBSCREEN1. Only the actual Sscrn ss_pzzl object receives the enabled definition. On the enabled non-PPC path the two aliases use cMes.getMes(1)->flags2 and ->m_sel. Default/PPC aliases and every original transition, message script, key input, close/delete, item consequence and Stop restoration remain exact. No mes.cpp, message lifetime, actor backing/reset, model, renderer or shared recipe change is proposed.

Required verification: extracted original completion and signed-selection decisions with inactive/active/first-frame/finished/keep-displayed cases and decoy neighbouring fields; default/explicit0 preprocessing; fresh current083 literal-T15 and chapter disabled program/overlay/allocated-section identity; actual compile-definition coverage; then fresh original far-refusal completion, ordinary yes/no choices/cancel, health/item consistency and exact close/hash. Current actor-healing acceptance and its missing injured-Ashley target remain separate. Central ownership and reviewed diff are required before edits/builds.

Private audit: healing/message-field-layout-saved-state-audit.json, SHA2564f47bd53e2a3e291f6048a24b6749378c3fcf132aabf169fb17b2caddda9beb2. Detailed run/state/file hashes are in ss-actor-lifetime-later-menu-gates-20261019.json.

## Typed answer semantics

The existing public Message member is signed s8 m_sel (include/mes.h); original Message::init clears it to0 at mes.cpp713/726. Message::code08 writes m_cur+1 on ordinary A at1439; source B may select the last choice or write-1 according to original attributes at1458/1461. PieceSelect::move at2057 waits on0, closes the original window for nonzero, then preserves its existing1=yes and2=no consequences. The proposed alias retains signed promotion and does not reinterpret-1, manufacture an answer, or change these decisions. The only callsite changes are the aliases themselves; checkMsgWindow and both original menu consumers remain textually unchanged.

## Implemented behind a disabled switch

The approved two-file change is now implemented as proposed. Original-source sanitizer tests pass 260 flag cases, 24 signed-answer cases and five original input cases. Tests run the actual Message classes/getMes, code01/code08 and original menu consumers with external rendering/board effects stubbed. A separate SH-4 compile of the real header proves the 236-byte slot stride, 4-byte virtual pointer, control mes offset 8, flags2 offset 16 and signed answer offset 229. Neither replaces guest acceptance.

Both actual current compiler inputs produce byte-identical preprocessed output with the switch omitted or explicitly zero; the PPC aliases remain exact. Eight knob cases verify the single target definition and reject invalid/missing dependencies. Initial host extraction/compatibility failures are preserved, then corrected without changing game code.

Fresh isolated controls are complete: exact upstream 083c09d17 literal T15 reference c32msrrP has ELF 4e2683e9 and end 8c40a618; the clean current Castle 9b53329f5 chapter arm c32msbmW has ELF 9ea2e107 and end 8c473778. Both preserve 45 generated headers, actual commands and all program payloads. SG_SELECT_LEAN and SCENERY_CHUNK are inherited at 1. Chapter actor-lifetime/Goto switches remain 0. Candidate disabled identity and a same-current-source SS1/MSG0 versus SS1/MSG1 refusal pair remain pending. No recipe is enabled.

## Fresh current compiled identity

All four serial candidate builds are complete. With SS_MSG_FIELDS off, the 11 Disc1 payloads match the exact upstream 083 reference and all 23 chapter payloads match the clean current Castle baseline. Scrambled boot, raw bytes, allocated ELF sections and all 45 generated headers are exact. Whole ELF files retain only nonallocated/debug differences; added zero-valued knob declarations and the identical linker/KOS input paths are recorded explicitly.

The isolated current healing-on message pair is c32mshmW (ELF 61afeac7, MSG0) versus c32msnmW (ELF 5ecf33fb, MSG1). Both resolve four actual actor-lifetime definitions; only the candidate adds the message definition to the real Sscrn object. All headers and resident program bytes remain identical, with the same end 8c473bb8. Only sscrn.ovl differs among the 23 game payloads. Fresh refusal/answer/cancel runtime gates are pending; no recipe is enabled. Full commands and hashes are retained in ss-message-fields-build-identity-20261019.json.
