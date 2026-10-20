# Lane cache20 (cache-stalls, 2026-10-20; CACHE20-STATUS.md). All default 0: nothing is compiled or linked and the image
# is unchanged. Memory-traffic levers only (the bytes written never change): exact, logic STRICT. The hw model cannot
# price them (store miss term 0 since the 10-15 refit), so each is judged by a console A/B (the cache20 bench disc).
#   GAME_SHZ_MEMSET=1  memset >= 64 bytes through SH4ZAM's shz_memset8 (8-byte stores; rebuilt from lane sh4zam-adopt
#                      0efa5516; MODELLED 10-15 -0.64 cross / -0.77 house, refit -0.60 / -1.05, console unconfirmed).
#   SQ_OUT=1           memset / memcpy >= SQ_OUT_MIN bytes (default 512) into cached main RAM through the SH-4 store
#                      queues: whole 32-byte lines, ocbi first, QACR saved / restored, interrupts off per SQ_OUT_CHUNK.
#                      (World and actor vertex output already stream to the TA through the store queues: MESH_DIRECT,
#                      NATIVE_ACTOR_DIRECT; the OT clear is ClearOTagR, a small list, not a memset.)
#   PREF_WALK=1        pref of the next unit: scenery chunk walk (next pick's corners + strips, next meshlet header) and
#                      the Trans object / enemy loops (next model's first two lines). platform/include/cache20.h.
#   CACHE20_BOOT=<mask> the run-time mask at boot (bit 0 SHZ, 1 SQ, 2 PREF; default every built lever). The benchmark
#                      disc's start screen overrides it (arm A = 0, arm B = every built lever).
# All three wrap memset (and SQ_OUT memcpy) at link time: not with MEMPROF or MEM_MOVCA (the same wraps).
GAME_SHZ_MEMSET ?= 0
SQ_OUT ?= 0
SQ_OUT_MIN ?= 512
SQ_OUT_CHUNK ?= 4096
PREF_WALK ?= 0
CACHE20_BUILT := $(shell echo $$(( ($(if $(filter-out 0,$(GAME_SHZ_MEMSET)),1,0)) | ($(if $(filter-out 0,$(SQ_OUT)),2,0)) | ($(if $(filter-out 0,$(PREF_WALK)),4,0)) )))
CACHE20_BOOT ?= $(CACHE20_BUILT)
ifneq ($(CACHE20_BUILT),0)
ifneq ($(filter-out 0 1,$(GAME_SHZ_MEMSET) $(SQ_OUT) $(PREF_WALK)),)
$(error GAME_SHZ_MEMSET, SQ_OUT and PREF_WALK are 0 or 1)
endif
ifneq ($(filter-out 0,$(MEMPROF) $(MEM_MOVCA)),)
$(error cache20 (GAME_SHZ_MEMSET / SQ_OUT) and MEMPROF / MEM_MOVCA both wrap memset / memcpy)
endif
CACHE20_DEFS := -DRE4DC_CACHE20_BOOT=$(CACHE20_BOOT)u -DRE4DC_CACHE20_BUILT=$(CACHE20_BUILT)u -DRE4DC_SHZ_MEMSET=$(GAME_SHZ_MEMSET) -DRE4DC_SQ_OUT=$(SQ_OUT) \
	-DRE4DC_SQ_OUT_MIN=$(SQ_OUT_MIN)u -DRE4DC_SQ_OUT_CHUNK=$(SQ_OUT_CHUNK)u -DRE4DC_PREF_WALK=$(PREF_WALK)
# platform/cache20.cpp is compiled like every platform/*.cpp (PLATFORM_SRCS); without RE4DC_CACHE20 it is empty.
$(OBJDIR)/platform/cache20.o: PLATFORM_CPPFLAGS += -DRE4DC_CACHE20=1 $(CACHE20_DEFS) -fno-tree-loop-distribute-patterns -Ithird_party/sh4zam/include
ifneq ($(filter-out 0,$(GAME_SHZ_MEMSET) $(SQ_OUT)),)
GAME_LDFLAGS += -Wl,--wrap=memset
endif
ifneq ($(SQ_OUT),0)
GAME_LDFLAGS += -Wl,--wrap=memcpy
endif
ifneq ($(GAME_SHZ_MEMSET),0)
PLATFORM_OBJS += $(OBJDIR)/platform/shz_mem_sh4.o
$(TARGET): $(OBJDIR)/platform/shz_mem_sh4.o
$(OBJDIR)/platform/shz_mem_sh4.o: third_party/sh4zam/source/sh4/shz_mem_sh4.s
	@mkdir -p $(dir $@)
	kos-cc $(KOS_CFLAGS) -c $< -o $@
endif
ifneq ($(PREF_WALK),0)
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_PREF_WALK=1
$(OBJDIR)/src/game/trans.o: GAME_CPPFLAGS += -DRE4DC_PREF_WALK=1
endif
endif
# BENCH_CENSUS=1 (cache20 bench disc only; needs BENCHMARK=1, RIGID_CENSUS=2, MIST_CUT=239 and BENCH_SCENES=<rows>;
#   default 0 = nothing): render-census rows (bench.cpp): a fixture file holds several `bench` rows run back to back in
#   one room, with the timed warp lines rigid / fx / crowd / tank / autofire between them (dbgwarp_bridge.cpp), the arm
#   picked on the start screen (D-pad LEFT A, RIGHT B: re4dc_cache20_arm), and a results page of every row (fps, CPU,
#   GPU, frame-tail buckets, logic phases, alive, live effects, tank hits, rigid parts). BENCH_FILES=<files>.
#   MIST_CUT's build mask is reset to 0 (every effect drawn) at each fixture load; `fx <frame> off` sets 239.
BENCH_CENSUS ?= 0
BENCH_FILES ?=
ifneq ($(BENCH_CENSUS),0)
ifneq ($(BENCHMARK)$(RIGID_CENSUS),12)
$(error BENCH_CENSUS=1 needs BENCHMARK=1 and RIGID_CENSUS=2)
endif
ifeq ($(MIST_CUT),)
$(error BENCH_CENSUS=1 needs MIST_CUT=239 (the fx off rows))
endif
$(OBJDIR)/bench.o: PLATFORM_CPPFLAGS += -DRE4DC_BENCH_CENSUS=1 $(if $(BENCH_FILES),-DRE4DC_BENCH_FILES=$(BENCH_FILES)) '-DRE4DC_BENCH_NAME="CACHE + CENSUS BENCH"'
$(OBJDIR)/dbgwarp_bridge.o: GAME_CPPFLAGS += -DRE4DC_BENCH_CENSUS=1 -DRE4DC_BENCH_MISTCUT=1
$(OBJDIR)/src/game/esp.o: GAME_CPPFLAGS += -DRE4DC_BENCH_CENSUS=1
endif
