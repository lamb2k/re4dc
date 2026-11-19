/* link.h: the loader's modem link (link.c; a copy of the QA link's console transport). */
#ifndef LOADER_LINK_H
#define LOADER_LINK_H
enum { LINK_OFF, LINK_DIAL, LINK_PPP, LINK_UP, LINK_FAILED, LINK_DROPPED, LINK_STOPPING };
void link_config(const char *number, const char *host, unsigned port, unsigned lport);
int link_start(void);          /* dial (3 tries) on a thread; returns at once */
void link_stop(void);          /* hang up on a thread; returns at once */
int link_state(void);
int link_busy(void);           /* a dial / hang-up / PPP thread still runs */
int link_send(const void *p, unsigned n);   /* queue one datagram (<= 1200 bytes); 0 = not queued */
int link_recv(void *p, unsigned max);       /* one received datagram, -1 none */
unsigned link_tx_queued(void);
unsigned link_console_ip(void), link_host(void), link_port(void), link_lport(void);
const char *link_number(void);
void link_text(char *out, unsigned n);
void link_counters(unsigned *tx, unsigned *rx, unsigned *tx_drops, unsigned *rx_drops);
#endif
