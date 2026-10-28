# dc-qalink example for a stock KallistiOS toolchain (source environ.sh first).
TARGET = dcql-example.elf

all: rm-elf $(TARGET)

DCQL_ENABLE ?= 1
DCQL_DIR := ../lib
include $(DCQL_DIR)/dcql.mk
OBJS = main.o $(DCQL_OBJS)

include $(KOS_BASE)/Makefile.rules

main.o: main.c $(DCQL_DIR)/dcql.h
	kos-cc $(KOS_CFLAGS) $(CFLAGS_EXTRA) $(DCQL_CFLAGS) -I$(DCQL_DIR) -c $< -o $@

clean: rm-elf
	-rm -f main.o
	-rm -rf $(DCQL_OBJDIR)

rm-elf:
	-rm -f $(TARGET)

$(TARGET): $(OBJS)
	kos-cc -o $(TARGET) $(OBJS) $(DCQL_LDFLAGS)

run: $(TARGET)
	$(KOS_LOADER) $(TARGET)
