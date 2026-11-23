! lane eng-draw5 (item 2): pos.tpl of tools/game30/avk (origin/t15/int, the released kernel re4dc_avk_pos_skin_u16)
! without the texture coordinates: no uv record words read, no u, v computed or stored (the engine takes u, v from
! the strip corners). Entries keep x, y, 1/w at +4, +8, +12; r7 = entry + 16 on entry, +44 a vertex.
! Generated input of render/gen/mkavk_xy.py; the uv lines removed are listed in that script.
! Position kernel half-body: vertex k in fvV, vertex k+1 prepared into fvN; record k+2's position / uv lines
! and the record line 64 bytes past it prefetched.
! Entry state: fvV = (x, y, z, 1) of k; r9/r10 = tu/tv(k); r5 = record k+1; r6 = n - k;
! r7 = entry k + 24; r8 = oc[k-1] (tail stores it); r4 = code of k-1 (tail).
! @p8 / @p6: position index x 8 (stride 8) or x 6 (rigid stride 6: r14, the skin palette register, is the
! scratch; p6 is never skinned).
@tail mov.b r4,@r8
@tail add #1,r8
ftrv xmtrx,fvV
fldi0 N3
mov.w @r5,r1
add r11,r5
@p8 shll2 r1
@p8 add r1,r1
@p6 add r1,r1
@p6 mov r1,r14
@p6 add r1,r1
@p6 add r14,r1
add r12,r1
@skin mov.w @(6,r1),r0
mov.w @r1+,r2
mov.w @r1+,r3
mov.w @r1,r1
fcmp/gt V2,fr10
movt r4
fcmp/gt fr11,V2
rotcl r4
dt r6
bt @end
@skin cmp/eq r14,r0
@skin bf @switch
@pf mov.w @r5,r0
@pf @p8 shll2 r0
@pf @p8 add r0,r0
@pf @p6 add r0,r0
@pf @p6 mov r0,r14
@pf @p6 add r0,r0
@pf @p6 add r14,r0
@pf add r12,r0
@pf pref @r0
@pf mov #64,r0
@pf add r5,r0
@pf pref @r0
fmul V3,V3
fsrra V3
fmul V3,V0
fmul V3,V1
fmov.s V3,@-r7
fcmp/gt V0,N3
rotcl r4
fcmp/gt fr8,V0
rotcl r4
fmov.s V1,@-r7
fcmp/gt V1,N3
fldi1 N3
rotcl r4
fcmp/gt fr9,V1
rotcl r4
fmov.s V0,@-r7
add #44,r7
lds r2,fpul
float fpul,N0
lds r3,fpul
float fpul,N1
lds r1,fpul
float fpul,N2
