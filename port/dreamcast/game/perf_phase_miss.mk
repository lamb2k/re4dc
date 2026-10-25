# Build 14: diagnostic, fixed PRFC1 event. Absent/0 adds no flags or objects.
PERF_PHASE_MISS ?= 0
PERF_PHASE_MISS_EVENT ?= 15
ifneq ($(words $(PERF_PHASE_MISS)),1)
$(error PERF_PHASE_MISS must be one value, 0 or 1)
endif
ifneq ($(filter-out 0 1,$(PERF_PHASE_MISS)),)
$(error PERF_PHASE_MISS must be 0 or 1)
endif
ifeq ($(PERF_PHASE_MISS),1)
ifneq ($(WORLD_CENSUS24),1)
$(error PERF_PHASE_MISS=1 needs WORLD_CENSUS24=1)
endif
ifneq ($(PMC_ROW),0)
$(error PERF_PHASE_MISS and PMC_ROW both own PRFC1; PMC_ROW must be 0)
endif
ifneq ($(words $(PERF_PHASE_MISS_EVENT)),1)
$(error PERF_PHASE_MISS_EVENT must be one fixed event, 15 or 37)
endif
ifeq ($(filter $(PERF_PHASE_MISS_EVENT),15 37),)
$(error PERF_PHASE_MISS_EVENT must be 15 (OC misses) or 37 (D-miss freeze cycles))
endif
$(OBJDIR)/world_census24.o $(OBJDIR)/qa_menu.o: PLATFORM_CPPFLAGS += -DRE4DC_PERF_PHASE_MISS=1
PLATFORM_OBJS += $(OBJDIR)/perf_phase_miss.o
$(TARGET): $(OBJDIR)/perf_phase_miss.o
$(OBJDIR)/perf_phase_miss.o: perf_phase_miss.cpp platform/include/perf_phase_miss.h platform/include/perf_phase_accounting.hpp
	@mkdir -p $(dir $@)
	kos-c++ $(KOS_CFLAGS) $(PLATFORM_CPPFLAGS) -DRE4DC_WORLD_CENSUS24=1 -DRE4DC_PERF_PHASE_MISS=1 -DRE4DC_PERF_PHASE_MISS_EVENT=$(PERF_PHASE_MISS_EVENT) -MMD -MP -c $< -o $@
-include $(OBJDIR)/perf_phase_miss.d
endif
