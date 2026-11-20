# Effect equivalence check (lane eng-e2): the original effect code against the native effect service (services/effects),
# per tick, on a PC (i386, the hostref build's flags and objects: SDK matrix library, the game's libm, math_sub).
#
#   make -C port/dreamcast/engine/services/effects/check HOSTREF=<re4ref build dir>   -> $(BUILD)/fxcheck
#   $(BUILD)/fxcheck <data tree> <engine serial with FX source / FXCALL lines> [--control drop=k|gravity=x]
ROOT   := $(abspath ../../../../../..)
GAME   := $(ROOT)/port/dreamcast/game
BUILD  ?= $(ROOT)/build/fxcheck
HOSTREF ?= $(ROOT)/build/hostref
ARCH   := -m32 -msse2 -mfpmath=sse -malign-double -fno-pie -fno-stack-protector
GAMEINC := -include $(GAME)/platform/include/re4dc_prelude.h -I$(ROOT)/include -I$(ROOT)/src -I$(ROOT)/src/game \
           -I$(GAME)/platform/include -DRE4DC_GAME
CXXF := $(ARCH) -isystem /usr/include/x86_64-linux-gnu/c++/13 -O1 -g -fno-strict-aliasing -ffunction-sections -fdata-sections -ffp-contract=off -std=gnu++20 \
        -fpermissive -w -fno-exceptions -fno-rtti -fno-threadsafe-statics $(GAMEINC) -I.. -I.
# The native service under test: its entry points renamed so the original side keeps the original names.
RENAME := -DEstSet=native_EstSet -DEspDataLoad=native_EspDataLoad -DEspDataRelease=native_EspDataRelease \
          -DEspGetEstAddr=native_EspGetEstAddr -DEspEstSetSelect=native_EspEstSetSelect -DEffectEspDelete=native_EffectEspDelete \
          -DEffectEspgenDelete=native_EffectEspgenDelete -DEffectEfmDelete=native_EffectEfmDelete \
          -DEffectDeleteAll=native_EffectDeleteAll -DEspSetEatEffect=native_EspSetEatEffect \
          -DEspSetWaterHitmark=native_EspSetWaterHitmark -DEstSetEm10WaterFall=native_EstSetEm10WaterFall \
          -DEspPullCoreKind=native_EspPullCoreKind
ORIG_SPECS := $(ROOT)/src/game/esp_sub.cpp:EspSeqSet,cEsp::CommonMove,cEsp::ColorUpdate,cEsp::AnmMove,cEsp::ApplyMatrix,cEsp::SetFreeWork,cEsp::Destruct,cEsp::cEsp,cEsp::~cEsp,cEsp::move \
              $(ROOT)/src/game/esp.cpp:PullEsp,PushEsp,cEsp::operator+new \
              $(ROOT)/src/game/espgen10.cpp:espgen10_Update,EspgenDataSet \
              $(ROOT)/src/game/rnd.cpp:fRandSeed1_1
HR := $(HOSTREF)/plain
HR_OBJS := $(HR)/sdk/sdk_mtx.o $(HR)/sdk/sdk_mtxvec.o $(HR)/sdk/sdk_vec.o $(HR)/sdk/pmtx.o $(HR)/game/math_sub.o \
           $(wildcard $(HR)/libm/*.o)

all: $(BUILD)/fxcheck
$(BUILD)/orig_fx.cpp: orig_extract.py Makefile
	@mkdir -p $(BUILD)
	echo '#include "global.h"' > $@.head; echo '#include "model.h"' >> $@.head; echo '#include "esp.h"' >> $@.head
	echo '#include "espgen.h"' >> $@.head; echo '#include "math_sub.h"' >> $@.head; echo '#include "rnd.h"' >> $@.head
	echo '#include "db_log.h"' >> $@.head; echo '#include "native_effect_source.h"' >> $@.head; echo '#include "obj.h"' >> $@.head
	echo 'struct EspPtr { cEsp* p; };   /* esp_sub.cpp file scope */' >> $@.head
	echo 'int EspChkTexId(int no); cObj* SmdGetObjPtr(u32);' >> $@.head
	echo 'int EspgenSeqSet(EspSeqData*, int, EspInfo*, cModel*, u16, Mtx*, Vec*, Vec*, EspSeqOpt*, int); void PushEspgen(EspgenWork*);' >> $@.head
	echo 'extern EspCreateFunc EspCreateTbl[0xFF]; extern cEspSystem* g_pEspSys; extern "C" void espgen10_Update(EspgenWork* w);' >> $@.head
	python3 orig_extract.py $@.body $(CXXF) $(ORIG_SPECS)
	cat $@.head $@.body > $@
$(BUILD)/orig_fx.o: $(BUILD)/orig_fx.cpp
	g++ $(CXXF) -c $< -o $@
$(BUILD)/esp00.o: $(ROOT)/src/game/esp00.cpp
	g++ $(CXXF) -c $< -o $@
$(BUILD)/check_orig.o: check_orig.cpp check.h
	@mkdir -p $(BUILD)
	g++ $(CXXF) -c $< -o $@
$(BUILD)/check_main.o: check_main.cpp check.h ../fx.h
	@mkdir -p $(BUILD)
	g++ $(CXXF) -c $< -o $@
$(BUILD)/fx_native.o: ../fx.cpp ../fx.h
	@mkdir -p $(BUILD)
	g++ $(CXXF) -DFX_HOST_CHECK $(RENAME) -c $< -o $@
$(BUILD)/fxcheck: $(BUILD)/orig_fx.o $(BUILD)/esp00.o $(BUILD)/check_orig.o $(BUILD)/check_main.o $(BUILD)/fx_native.o
	gcc -m32 -no-pie -Wl,--gc-sections -o $@ $^ $(HR_OBJS) $(HR)/host/host_rt.o -lm 2> $(BUILD)/link.log || { grep -o "undefined reference to \`[^']*'" $(BUILD)/link.log | sort | uniq -c | sort -rn | head -40; exit 1; }
.PHONY: all
