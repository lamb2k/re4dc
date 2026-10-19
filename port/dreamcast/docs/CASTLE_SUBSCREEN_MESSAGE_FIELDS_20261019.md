# Original inventory message field audit, 2026-10-19

The far-Ashley rejection reaches its authored completion through normal A, but PieceCommand remains in mode3 with an empty frame. The independently read frozen e86 ELF c9f614 and original saved-state chain locate main RAM with three unique256-byte executable anchors. MessageControl.mes starts at8, Message is236bytes, and its fields start after the virtual pointer: slot1.flags2 is cMes+104hex. The source alias CMES_FLAGS usesFChex, which is the actual be_flag. Before A both values are1. After A, original code01 marks flags2=2 and clears be_flag to0; m_pMes advances from8C8EE374 to8C8EE376, r_no_0=1, and Loop remains1. No guest writes or extra test capture were used for this audit.

Source references: include/mes.h already documents the platform layout and supplies typed getMes; src/game/mes.cpp code01 marks completion; src/Sscrn/ss_pzzl.cpp201/1870/2825 use the legacy alias to await completion. Its second alias CMES_RESULT1D1hex should access signed slot1.m_sel, actually1D9hex. The latter is read only by PieceSelect's original yes/no transition at2057. That is a source/layout risk, not a claimed guest yes/no failure.

## Proposed bounded change (not yet implemented)

Only src/Sscrn/ss_pzzl.cpp and port/dreamcast/game/subscreen.mk, plus owned tests/docs. New SS_MSG_FIELDS defaults0, accepts only0/1 and requires SUBSCREEN1. Only the actual Sscrn ss_pzzl object receives the enabled definition. On the enabled non-PPC path the two aliases use cMes.getMes(1)->flags2 and ->m_sel. Default/PPC aliases and every original transition, message script, key input, close/delete, item consequence and Stop restoration remain exact. No mes.cpp, message lifetime, actor backing/reset, model, renderer or shared recipe change is proposed.

Required verification: extracted original completion and signed-selection decisions with inactive/active/first-frame/finished/keep-displayed cases and decoy neighbouring fields; default/explicit0 preprocessing; fresh current083 literal-T15 and chapter disabled program/overlay/allocated-section identity; actual compile-definition coverage; then fresh original far-refusal completion, ordinary yes/no choices/cancel, health/item consistency and exact close/hash. Current actor-healing acceptance and its missing injured-Ashley target remain separate. Central ownership and reviewed diff are required before edits/builds.

Private audit: healing/message-field-layout-saved-state-audit.json, SHA2564f47bd53e2a3e291f6048a24b6749378c3fcf132aabf169fb17b2caddda9beb2. Detailed run/state/file hashes are in ss-actor-lifetime-later-menu-gates-20261019.json.

## Typed answer semantics

The existing public Message member is signed s8 m_sel (include/mes.h); original Message::init clears it to0 at mes.cpp713/726. Message::code08 writes m_cur+1 on ordinary A at1439; source B may select the last choice or write-1 according to original attributes at1458/1461. PieceSelect::move at2057 waits on0, closes the original window for nonzero, then preserves its existing1=yes and2=no consequences. The proposed alias retains signed promotion and does not reinterpret-1, manufacture an answer, or change these decisions. The only callsite changes are the aliases themselves; checkMsgWindow and both original menu consumers remain textually unchanged.
