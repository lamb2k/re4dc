// A C ABI around the actual production certificate; no decision logic is copied.
#include "backface_certificate.hpp"

namespace cert = re4dc::bf::certificate;

extern "C" {
unsigned cone_probe(const float matrix[16], float near_distance,
                    const cert::Cone* cone, unsigned cull,
                    const void* cache, unsigned vertices,
                    const cert::RawPositions* raw, cert::Proof* proof) {
    cert::Context context;
    *proof = {};
    if (!cert::prepare(context, matrix, near_distance)) return 0;
    const cert::Outcome outcome = cert::classify(context, *cone, cull, *proof);
    unsigned result = 1U | (unsigned(outcome) << 1);
    if (cert::positive_depth(context, *cone)) result |= 8;
    if (outcome == cert::FrontCandidate && cert::projected_front(context, *proof, cache, vertices, *raw)) result |= 16;
    return result;
}

unsigned cone_strict(const void* cache, const std::uint8_t* index,
                     unsigned count, unsigned cull, unsigned actor_eol) {
    return cert::strict_front(cache, index, count, 127, cull, actor_eol != 0);
}

unsigned cone_projected(const float matrix[16], float near_distance,
                        const cert::Proof* proof, const void* cache,
                        unsigned vertices, const cert::RawPositions* raw,
                        unsigned stride) {
    cert::Context context;
    return cert::prepare(context, matrix, near_distance) &&
           cert::projected_front(context, *proof, cache, vertices, *raw, stride);
}

unsigned cone_strict_layout(const void* cache, const std::uint8_t* index,
                            unsigned count, unsigned stride) {
    return cert::strict_front(cache, index, count, 127, 1, true, stride);
}

float cone_normal(const float axis[3], float cosine, const std::int64_t normal[3]) {
    return cert::normal_lower_bound(axis, cosine, normal);
}

float cone_sine(float cosine) { return cert::sine_upper(cosine); }

unsigned cone_worth(unsigned vertices, unsigned indices, unsigned strips) {
    return cert::worth_front(vertices, indices, strips);
}

unsigned cone_worth_world(unsigned vertices, unsigned indices, unsigned strips) {
    return cert::worth_front_world(vertices, indices, strips);
}

unsigned cone_sizes(unsigned which) {
    return which == 0 ? sizeof(cert::Context) : which == 1 ? sizeof(cert::Cone) :
           which == 2 ? sizeof(cert::Proof) : sizeof(cert::RawPositions);
}
}
