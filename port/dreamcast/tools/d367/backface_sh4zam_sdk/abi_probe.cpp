// The SH4 single-precision ABI allocates scalar float args to FR5,FR4,
// FR7,FR6,FR9,FR8; bind that explicitly in the generator via these probes.
#define ARG(N) extern "C" __attribute__((noinline)) float sdk_arg_##N(float a, float b, float c, float d, float e, float f) { return N; }
ARG(a)
ARG(b)
ARG(c)
ARG(d)
ARG(e)
ARG(f)
