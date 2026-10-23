#include "../../../room/backface_sh4zam.hpp"
extern "C" __attribute__((noinline)) float sdk_area_probe(float ax, float ay,
    float bx, float by, float cx, float cy) {
    return re4dc::bf::sdk::area(shz_vec2_init(ax, ay), shz_vec2_init(bx, by),
                               shz_vec2_init(cx, cy));
}
