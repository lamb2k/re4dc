# Lane chardraw19 (character-draw-path, P2; CHARDRAW19-STATUS.md). Default 0: no code, image unchanged.
# CHAR_CHUNK=1 (exact, render only; needs COARSE_ONE_SUBMIT=1): every native actor draw goes through the chunk front
# end (platform/native_actor_chunk.inc): each repeated skinned point of a chunk is skinned and projected once, each
# distinct normal lit once, then the chunk is sent through the shared chunk-submit back end (chunk_submit.h v1,
# CHUNK_SUBMIT=1). CHAR_CHUNK_BACKEND=0 keeps the stage-1 adapter over today's store-queue window instead.
# CHAR_CHUNK=2: check build (each pass compared word for word with today's; prints CCHK / LCHK lines).
CHAR_CHUNK ?= 0
CHAR_CHUNK_BACKEND ?= 1
ifneq ($(CHAR_CHUNK),0)
ifeq ($(filter 1 2,$(CHAR_CHUNK)),)
$(error CHAR_CHUNK must be 0, 1 or 2 (2 = check build))
endif
ifneq ($(COARSE_ONE_SUBMIT),1)
$(error CHAR_CHUNK needs COARSE_ONE_SUBMIT=1)
endif
ifeq ($(filter 0 1,$(CHAR_CHUNK_BACKEND)),)
$(error CHAR_CHUNK_BACKEND must be 0 or 1)
endif
ifeq ($(CHAR_CHUNK_BACKEND),1)
ifneq ($(CHUNK_SUBMIT),1)
$(error CHAR_CHUNK_BACKEND=1 needs CHUNK_SUBMIT=1 (the shared back end, scenery19.mk))
endif
endif
$(OBJDIR)/platform/native_actor_fast.o: PLATFORM_CPPFLAGS += -DRE4DC_CHAR_CHUNK=$(CHAR_CHUNK) -DRE4DC_CHAR_CHUNK_BACKEND=$(CHAR_CHUNK_BACKEND)
endif
