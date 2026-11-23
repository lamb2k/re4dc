// The engine's sampling profiler (lane eng-crash1, core/pc_sampler.cpp) and its lab arm PCSAMPLE.
#ifndef E1_PC_SAMPLER_H
#define E1_PC_SAMPLER_H
#ifdef __cplusplus
extern "C" {
#endif
// Once at boot, before play (core/main.cpp). Without the boot file PCSAMPLE it does nothing else: no timer, no ring,
// no thread. With it: the ring is allocated (loading work), a helper thread starts the sampler when play starts,
// stops it when play ends and prints the table (E1 PCS lines; tools/engine/pcs_table.py resolves them on the map).
void e1_pcs_boot(void);
#ifdef __cplusplus
}
#endif
#endif
