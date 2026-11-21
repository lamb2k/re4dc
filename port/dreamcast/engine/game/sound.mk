# Sound (lane eng-snd1, integrator ruling H-025.1): included once by game/Makefile, in every image.
#
# Two layers:
#   - the engine's sound service (services/sound/): the AICA layer lifted from the old port's Dreamcast backend and
#     adapted (aica.cpp: no old-port globals or hooks), what the driver needs below it (snd_host.cpp: interrupt guards,
#     ARAM addresses, the stream player's I/O without the disc, logged stubs), and the service (snd_svc.cpp: the
#     driver's boot and the room's sound banks loaded with the room, the tick's SndWatcher, the 5 ms audio frame on its
#     own thread, the request log, the cost per picture, the output probe, the report line);
#   - the original game's sound driver (src/game/snd*.cpp: SE resolution, the ISS voice manager, the stream player and
#     the MIDI sequencer, on the GameCube AX / MIX / SYN interfaces), hosted UNCHANGED under the recorded waiver
#     H-025.1 of "no original service code": the link check lists its 22 units in their own group of
#     allowed_original.txt ("sound-driver-waived-H-025.1"); the waiver holds while sound costs under 1.0 ms a picture
#     mean and 2.0 ms worst on the calibrated tier (the selector fails a timing scene over it: loader/selector.c).
SND_DIR := $(ENG)/services/sound
SND_DRIVER := game/snd game/snd_efx game/snd_iss0 game/snd_iss1 game/snd_iss2 game/snd_iss3 game/snd_iss4 \
	game/snd_main game/snd_ram game/snd_seq0 game/snd_seq1 game/snd_seq2 game/snd_seq3 game/snd_str0 game/snd_str1 \
	game/snd_str2 game/snd_str3 game/snd_str4 game/snd_sub0 game/snd_sub1 game/snd_sub2 game/snd_sub3
SND_HOSTED_OBJS := $(addprefix $(OUT)/h/,$(addsuffix .o,$(SND_DRIVER)))
HOSTED_OBJS += $(SND_HOSTED_OBJS)
# The driver units include "re4dc_platform.h" (the sound region, the boot log): the service's stand-in, theirs only.
$(SND_HOSTED_OBJS): ORIG_FLAGS += -I$(SND_DIR)/host
# The random SE variant (snd.cpp seRandomCheck, the unit's only Rnd call) is presentation (owner 2026-11-19, "Split
# it"), and the driver keeps its own generator (H-025.1): snd.o's Rnd is bound to the sound service's own generator
# (services/sound/snd_host.cpp snd_rnd), so a sound moves neither the behaviour generator nor the engine's shared
# presentation generator (the effects', cloth's and voices' draws stay as on the PC reference, which plays no sound).
# snd.o is built by this rule (the hosted pattern rule's flags, then the symbol bound; the fight and boss images'
# weakened symbols, below, in the same step).
$(OUT)/h/game/snd.o: $(ROOT)/src/game/snd.cpp $(ENG)/host/e1_prelude.h $(SND_DIR)/host/re4dc_platform.h
	@mkdir -p $(dir $@)
	kos-c++ $(ORIG_FLAGS) $(ORIG_INC) -c $< -o $@.tmp.o
	sh-elf-objcopy --redefine-sym _Rnd=_snd_rnd $(foreach f,$(SND_WEAK_FIGHT),--weaken-symbol=$(f)) $@.tmp.o $@
	rm -f $@.tmp.o

# The service (compiled by game/Makefile's engine rule).
SND_OBJS := $(OUT)/e/services/sound/aica.o $(OUT)/e/services/sound/snd_host.o $(OUT)/e/services/sound/snd_svc.o
ENG_OBJS += $(SND_OBJS)
ENG_HDRS += $(wildcard $(SND_DIR)/*.h)

# Hooks: the room's sound loaded with the room (after e1_load_room), the tick's SndWatcher after drawing and before
# the pacer's wait (before e1_fields_late, where the original main loop calls it after Trans), the report's E1 SOUND
# lines (before e1_report); the behaviour's requests counted, timed and traced (SndCall, SndStop). Wraps keep this
# lane out of the core files; the hand-back asks for three direct calls instead.
WRAPS += -Wl,--wrap=_Z12e1_load_roomj -Wl,--wrap=_Z14e1_fields_latej -Wl,--wrap=_Z9e1_reportv \
	-Wl,--wrap=_Z7SndCallttP3VeciiP5cUnit -Wl,--wrap=_Z7SndStopmi

# The fight and boss images keep generated stubs for some driver entry points (fight/fight_gen_stubs.cpp,
# fight/fight_stubs.cpp, boss/boss_stubs.cpp: other lanes' files). Until those are removed (hand-back request), the
# driver's own definitions of them are made weak so the images link with the stubs in place.
ifneq ($(BOSS)$(FIGHT),)
SND_WEAK_FIGHT := __Z10SndBlkStopi __Z13SndAllFadeOutv __Z13SndBgmTblInitv __Z15SndRoomStrStartiii __Z9SndStrReqiiiiif \
	__Z14SndRoomStrStopi
endif
