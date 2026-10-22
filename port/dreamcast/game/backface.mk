# Lane backface22 (2026-10-22; BASEBALL-RENDERER-ASSESSMENT-20261022.md item 1). Default 0: no code, image unchanged.
# BACKFACE_CENSUS=1 (test builds only, needs TA_HASH=1): platform/backface_census.cpp watches every TA burst (the TA_HASH
#   hooks) and logs "bfc:" lines per draw class every 60 presented scenes: strip vertices, vertices of culling strips,
#   triangles, back triangles, vertices in back runs of >= 3 triangles and vertices a strip split would save, under both
#   PVR sign conventions (h0/h1). Classes (platform/include/bfc_class.h): 1 PS2 world, 2 static parts, 3 Leon,
#   4 Ganados, 5 other actors (bosses, animals, Ashley; id = largest model id), 0 everything else.
BACKFACE_CENSUS ?= 0
ifneq ($(filter $(BACKFACE_CENSUS),0 1),$(BACKFACE_CENSUS))
$(error BACKFACE_CENSUS must be 0 or 1)
endif
ifeq ($(BACKFACE_CENSUS),1)
ifneq ($(TA_HASH),1)
$(error BACKFACE_CENSUS=1 needs TA_HASH=1)
endif
$(OBJDIR)/platform/native_ui.o $(OBJDIR)/platform/native_static.o $(OBJDIR)/platform/backface_census.o: PLATFORM_CPPFLAGS += -DRE4DC_BACKFACE_CENSUS=1
$(OBJDIR)/coarse.o: GAME_CPPFLAGS += -DRE4DC_BACKFACE_CENSUS=1
endif
