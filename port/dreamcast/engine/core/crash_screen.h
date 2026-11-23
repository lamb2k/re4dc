// The engine's crash screen (lane eng-crash1, core/crash_screen.cpp) and its control boot file CRASHCTL.
#ifndef E1_CRASH_SCREEN_H
#define E1_CRASH_SCREEN_H
#ifdef __cplusplus
extern "C" {
#endif
// Once at boot, before play (core/main.cpp, after the lab's boot files): the BIOS glyphs copied to RAM, the log ring
// put in front of the serial line, the fault handlers installed (chained to the console loop's when it is running),
// and the boot file CRASHCTL read. Nothing of it runs again unless the program faults.
void e1_crash_boot(void);
#ifdef __cplusplus
}
#endif
#endif
