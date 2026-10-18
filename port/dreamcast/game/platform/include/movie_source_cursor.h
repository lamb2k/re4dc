#pragma once
#include <stdint.h>
// NTSC movie clock: picture zero starts at v0 and each picture lasts two
// retraces. Source Run() precedes cancel even before the first picture shows.
// Signed subtraction handles the retrace counter wrapping during a short movie.
static inline unsigned re4dc_movie_source_picture(unsigned now, unsigned v0, unsigned count)
{
    const int32_t elapsed = (int32_t) (now - v0);
    const unsigned picture = elapsed > 0 ? (unsigned) elapsed / 2 : 0;
    return !count ? 0 : picture >= count ? count - 1 : picture;
}
