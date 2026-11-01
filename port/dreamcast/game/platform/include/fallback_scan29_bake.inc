// Own block after the existing bake implementation. Do not rebake a tagged
// offline palette when live-state admission declines: the original fast/exact
// evaluator can draw that state while the next admitted draw keeps the bake.
BakeUse scan29_bake_prepare(Part& e, const Lights& L, const BlobHeader& b, unsigned rs, unsigned scale[3]) {
    const auto* tagged = re4dc::fallback29::tagged(reinterpret_cast<const u8*>(&b), e.p.stream_bytes);
    if (tagged) {
        if (L.scan29_bake != tagged) return kBakeNone;
        bool same = true;
        for (unsigned c = 0; c < 3; ++c) { scale[c] = L.scan29_gain[c]; same &= scale[c] == 256U; }
        return same ? kBakeCopy : kBakeScaled;
    }
    return bake_prepare(e, L, b, rs, scale);
}
#define bake_prepare scan29_bake_prepare
