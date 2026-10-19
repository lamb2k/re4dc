# Lane chardraw19 (character-draw-path, P2; CHARDRAW19-STATUS.md). Default 0: no code, image unchanged.
# CHAR_CHUNK=1 (exact, render only; needs COARSE_ONE_SUBMIT=1): skinned characters drawn through the chunk front end
# (platform/native_actor_chunk.inc): each repeated skinned point of a chunk is skinned and projected once, then the
# chunk is sent through the chunk-sink adapter (today's store-queue window until chunk_submit.h v1 lands).
CHAR_CHUNK ?= 0
ifneq ($(CHAR_CHUNK),0)
ifeq ($(filter 1,$(CHAR_CHUNK)),)
$(error CHAR_CHUNK must be 0 or 1)
endif
ifneq ($(COARSE_ONE_SUBMIT),1)
$(error CHAR_CHUNK needs COARSE_ONE_SUBMIT=1)
endif
$(OBJDIR)/platform/native_actor_fast.o: PLATFORM_CPPFLAGS += -DRE4DC_CHAR_CHUNK=$(CHAR_CHUNK)
endif
