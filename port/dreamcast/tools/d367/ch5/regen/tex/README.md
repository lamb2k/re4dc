# ch5 island tex.pak regeneration (lane ch5tex, 2026-10-18)

Rebuilds tex-ch5e.pak (sha d5986c3e, 159,711,232 B, 7,088 keys), the dc/tex.pak of the recorded ch5found16 runs
(h-cx76mW..cx80mW). Byte-exact. Outputs: /root/probe/lanes-20261018/ch5tex (private); verified copy in
re4-assets-private\ch5regen-20261018\paks\tex-ch5e-d5986c3e.pak + SHA256SUMS.

Chain (checkpoint shas from the recorded transcripts / targets, all matched):
1. st3 vqroom.py pass 1 on Test 10 tex.pak 7137e9e5 (tex-gcatlas), loose sources from the st3d12/st3d13 run
   stage.json + payload-manifest (c5t_fixmat.py resolves each loose file by sha) plus the r331/r332 PS2-world keys
   of the later j1 fixtures, logs st3d12+st3d13 -> tex-st3vq e3c55502 (c5t-vq1b.sh).
2. addss.py chap05..07 (ch5regen sschap/tex5), pairs-e1, pairs-e2 (c5t-vq23.sh).
3. vqroom pass 2 (st3e2 fixtures, logs *-11 only: the -12 runs came later) -> st3vq2 ba6379dc; pass 3 (all st3e2
   logs) -> st3vq3 0e0015de (c5t-vq23b.sh).
4. fx_ps2_pack common,r101 then fx_ps2_pack_st3 lib+pack over a fresh fxcache that includes r332/r333 (r333 PS2 world
   via run_rooms_st3 in this lane's copy, c5t-ps2w.sh): 156 rows / 262 packages -> st3vq4 1c55bd53 (c5t-fx5.sh).
5. ch5found16: pakunion(st3vq4, Test 15 pak 15611245) = tex-ch5 5b04d865; pakadd pairs-c5 = ch5b a973583f; pakadd
   prepem tex-em* = ch5c eb6bffde; pakbase(51f1f7a4 = test 17 vram101 pak, ch5c, evt5 x3 + pairs-c5b x2) = ch5d
   f79fcddf; pakbase + 196d7189 / 5430b7b8 = ch5d1; vq_pak.py with vq16-c5.txt (17 keys, 3f757369) = tex-ch5e d5986c3e
   (c5t-pairs.sh, c5t-ch5.sh, c5t-ch5e.sh; pak tools from C:\tmp\ch5).

Gates (c5t-prepfix.sh, c5t-gates.sh: ch5regen gate fixtures with dc/tex.pak = the rebuilt pak, 60 s, discs deleted):
r307, r310, r31b, r31c all texfail 0, CAST-GC PASS, no HALT/FAULT/MISSING. The r31c "open failed" lines were the 19
em39 textures (prepem tex-em39) that only tex-ch5c+ carried; the 51f1f7a4 fallback had neither the pak entry nor a
loose file.
