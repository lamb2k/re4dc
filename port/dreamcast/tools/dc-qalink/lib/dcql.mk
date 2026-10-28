# dcql.mk: include from a KOS Makefile.
#   DCQL_DIR := path/to/dc-qalink/lib
#   include $(DCQL_DIR)/dcql.mk
#   OBJS += $(DCQL_OBJS); compile your files with $(DCQL_CFLAGS) -I$(DCQL_DIR); link with $(DCQL_LDFLAGS).
#   Do NOT also link -lppp.
# DCQL_ENABLE=1 builds the link (QA / test builds). Default 0: DCQL_OBJS is empty and the header's calls are no-ops,
# so a retail build carries nothing.
# libppp is compiled from $(KOS_BASE)/addons/libppp with four functions renamed to dcql.c's hardened versions.
DCQL_ENABLE ?= 0
DCQL_DIR ?= $(dir $(lastword $(MAKEFILE_LIST)))
DCQL_OBJDIR ?= dcql-obj
ifeq ($(DCQL_ENABLE),1)
DCQL_CFLAGS := -DDCQL_ENABLE=1
DCQL_PPP_DIR := $(KOS_BASE)/addons/libppp
DCQL_PPP_OBJS := $(addprefix $(DCQL_OBJDIR)/,ppp.o lcp.o pap.o ipcp.o ppp_modem.o)
DCQL_OBJS := $(DCQL_OBJDIR)/dcql.o $(DCQL_PPP_OBJS)
DCQL_LDFLAGS := -Wl,--wrap=createChainBuffer -Wl,--wrap=destroyChainBuffer -Wl,--wrap=thd_worker_create_ex
DCQL_PPP_DEFS := -Dthd_create=dcql_ppp_thd_create -Dthd_pass=dcql_ppp_thd_pass \
                 -Dmodem_write_data=dcql_ppp_modem_write -Dmodem_read_data=dcql_ppp_modem_read

$(DCQL_OBJDIR)/dcql.o: $(DCQL_DIR)/dcql.c $(DCQL_DIR)/dcql.h
	@mkdir -p $(DCQL_OBJDIR)
	kos-cc $(KOS_CFLAGS) -Os $(DCQL_CFLAGS) -I$(DCQL_DIR) -c $< -o $@
$(DCQL_OBJDIR)/%.o: $(DCQL_PPP_DIR)/%.c
	@mkdir -p $(DCQL_OBJDIR)
	kos-cc $(KOS_CFLAGS) -Os -I$(DCQL_PPP_DIR) -I$(KOS_BASE)/kernel/net $(DCQL_PPP_DEFS) -c $< -o $@
else
DCQL_CFLAGS :=
DCQL_OBJS :=
DCQL_LDFLAGS :=
endif
