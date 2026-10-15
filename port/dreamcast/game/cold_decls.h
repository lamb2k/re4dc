#pragma once
// HOT_COLD_SPLIT=1 (lane t2exact B5, t2exact.mk; exact: code placement only): the diagnostic report functions are
// declared cold before any other declaration in each object (-include), so GCC predicts the paths that call them as
// never taken and places those blocks after the function's hot code. A hot function's cache lines then hold more of
// the code it runs every frame.
#ifdef __cplusplus
extern "C" {
#endif
void re4dc_log(const char* fmt, ...) __attribute__((cold));
void re4dc_missing(const char* name) __attribute__((cold));
#ifdef __cplusplus
}
#endif
