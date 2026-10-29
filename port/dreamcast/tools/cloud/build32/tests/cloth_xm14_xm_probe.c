/* Actual pinned SH4ZAM API, independent of the production wrapper under test.
 * Only rejection tests call these: a rejected wrapper must leave XMTRX intact.
 */
#include <sh4zam/shz_xmtrx.h>
#include <sh4zam/shz_vector.h>

void fixture_seed_xm(void)
{
    shz_vec4_t a = shz_vec4_init(2.0f, 0.0f, 0.0f, 7.0f);
    shz_vec4_t b = shz_vec4_init(0.0f, 3.0f, 0.0f, 11.0f);
    shz_vec4_t c = shz_vec4_init(0.0f, 0.0f, 5.0f, 13.0f);
    shz_xmtrx_load_rows_3x4(&a, &b, &c);
}

void fixture_probe_xm(float out[3])
{
    shz_vec3_t v = shz_xmtrx_transform_point3(shz_vec3_init(1.0f, 2.0f, 3.0f));
    out[0] = v.x;
    out[1] = v.y;
    out[2] = v.z;
}
