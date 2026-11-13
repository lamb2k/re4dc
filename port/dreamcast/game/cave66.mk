# STREAM_PEAK_LOG=<KiB> (lane cave66, GitHub #66 bug 4; diagnostic, log only, test builds; default 0 = no code): one
#   "SPK: frame=<native frame> bytes=<model stream bytes>" line for every presented frame whose model stream reaches
#   <KiB> KiB (at most one line per 4 frames), and every 30 frames "SPK win: frame= max=" with the window's largest
#   frame. The TA parameter buffer is 2,000,896 B per bank (1,770,496 B with FSAA); lines between the warp's plpos
#   rows place a heavy view in the room.
STREAM_PEAK_LOG ?= 0
ifneq ($(STREAM_PEAK_LOG),0)
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_STREAM_PEAK_LOG=$(STREAM_PEAK_LOG)
endif
