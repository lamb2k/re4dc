OBJDIR := obj
TA_HASH := 0
include /root/probe/codex-backface-walk23/port/dreamcast/game/backface.mk
.PHONY: all
all: obj/platform/native_static.o obj/platform/native_actor_fast.o
obj/platform/native_static.o obj/platform/native_actor_fast.o:
	@echo $@ $(PLATFORM_CPPFLAGS)
