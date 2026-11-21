/* nl_glue.c (lane eng-e1g): what newlib's float wrappers need when linked into re4ref (nlnative build, svc.mk): their
 * errno through newlib's __errno(). With _IEEE_LIBM the wrappers return the core's result directly; errno is never read. */
static int nl_errno;
int* __errno(void) { return &nl_errno; }
