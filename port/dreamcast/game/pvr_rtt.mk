# PVR_RTT=1 (lane castlerender19 2026-10-19; user decision 10-19 "Verdugo ice option (a), exact"; render only,
#   default 0): render-to-texture on the PVR for the source's TexRenderMng targets (game/TexRender.cpp; GXCopyTex is a
#   stub). A target's effects (esp Tool_flg 0x10000 in the target's OT slot) are captured as sprites and rendered by a
#   KOS render-to-texture scene into the target's own VRAM texture (w x h x 2 bytes, ARGB4444) before the next frame's
#   scene, only while a model uses the target (platform/include/pvr_rtt.inc). The first user: the frozen Verdugo's ice
#   (em2c, 64 x 64, TextureBlend3 blend type 2) as a second pass on its registry draw (coarse_actor_transaction.inc).
#   Knob off: unchanged.
PVR_RTT ?= 0
ifeq ($(PVR_RTT),1)
ifneq ($(EFFECT_SPRITES)$(D349_RENDERER_STACK),11)
$(error PVR_RTT needs EFFECT_SPRITES=1 and D349_RENDERER_STACK=1)
endif
$(OBJDIR)/src/game/TexRender.o $(OBJDIR)/src/game/esp_sub.o $(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -DRE4DC_PVR_RTT=1
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_PVR_RTT=1
endif
# PVR_RTT_STATS=1 (test builds only; render only): every rendered target is read back (texel coverage and mean
#   colour in the log; Flycast keeps render-to-texture on the host GPU, so its readback is 0) and shown as a 128 x 128
#   sprite at the top left of the screen.
ifneq ($(PVR_RTT_STATS),)
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_PVR_RTT_STATS=1
endif
