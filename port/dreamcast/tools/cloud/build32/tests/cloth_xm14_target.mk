# Public EF14 target executable. The Python driver pins and materializes both
# production source excerpts before Make reads this file. No game assets.
.DEFAULT_GOAL := all
TARGET := $(OUT)/cloth_xm14.elf
OBJECTS := $(OUT)/production_batch.o $(OUT)/production_scalar.o \
           $(OUT)/production_geometry.o $(OUT)/cloth_xm14_xm_probe.o $(OUT)/cloth_xm14_main.o

KOS_CFLAGS += -m4-single -ml -O2 -ffp-contract=off \
              -ffunction-sections -fdata-sections -fstack-usage \
              -DRE4DC_CLOTH_XM_BATCH14=1 \
              -DRE4DC_FX_STRIP21=1 \
              -I$(SH4ZAM_DIR)/include -I$(OUT) \
              -I$(SOURCE_ROOT)/port/dreamcast/game/platform/include
include $(KOS_BASE)/Makefile.rules

.PHONY: all production_objects inspect_inputs run
all: $(TARGET)
production_objects: $(OUT)/production_batch.o $(OUT)/production_scalar.o \
                    $(OUT)/production_geometry.o $(OUT)/cloth_xm14_xm_probe.o

# The same wrappers and flags used by the real compile produce this evidence.
inspect_inputs:
	$(XM14_CC) $(KOS_CFLAGS) -std=gnu11 -dM -E -x c /dev/null > $(OUT)/effective-c-defines.txt
	$(XM14_CXX) $(KOS_CFLAGS) -std=c++20 -dM -E -x c++ /dev/null > $(OUT)/effective-cxx-defines.txt
	$(XM14_CXX) $(KOS_CFLAGS) -std=c++20 -M $(OUT)/sdk_probe.cpp -MF $(OUT)/sdk_probe.o.d

run: $(TARGET)
	@test -n "$(KOS_LOADER)" || { echo 'KOS_LOADER is required'; exit 2; }
	$(KOS_LOADER) $(TARGET)

$(OUT)/production_batch.o: $(OUT)/production_batch.c
	$(XM14_CC) $(KOS_CFLAGS) -std=gnu11 -MD -MF $@.d -c $< -o $@

# The public build-r21 recipe selects GAME_FP_CONTRACT=off and
# GAME_MULTVEC_SCHED=1. Select that exact production assembly branch.
$(OUT)/production_scalar.o: $(OUT)/production_scalar.S
	$(XM14_CC) $(KOS_CFLAGS) -ffp-contract=off -MD -MF $@.d \
	  -DRE4DC_FP_CONTRACT_OFF=1 -DRE4DC_MULTVEC_SCHED=1 -c $< -o $@

$(OUT)/cloth_xm14_xm_probe.o: $(TEST_DIR)/cloth_xm14_xm_probe.c
	$(XM14_CC) $(KOS_CFLAGS) -std=gnu11 -MD -MF $@.d -c $< -o $@

$(OUT)/production_geometry.o: $(SOURCE_ROOT)/port/dreamcast/room/pvr_geometry.cpp
	$(XM14_CXX) $(KOS_CFLAGS) -std=c++20 -MD -MF $@.d -c $< -o $@

$(OUT)/cloth_xm14_main.o: $(TEST_DIR)/cloth_xm14_main.cpp $(OUT)/cloth_xm14_offsets.h
	$(XM14_CXX) $(KOS_CFLAGS) -std=c++20 -MD -MF $@.d -c $< -o $@

$(TARGET): $(OBJECTS)
	$(XM14_CXX) -m4-single -ml -Wl,--gc-sections -Wl,-Map,$(OUT)/cloth_xm14.map \
	  -Wl,--defsym,_PSMTXMultVec=_re4dc_sh4_MTXMultVec \
	  -o $@ $(OBJECTS)
