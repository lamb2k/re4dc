// Include inside uv32 after BlobHeader/MeshletInfo/LevelInfo and counters.
// A tag supplies a proposed bound, never authority over the current UV input.
// No retained pointer proof, allocation, source write or changed geometry.
#if defined(RE4DC_ACTOR_SPAN_MEMO31) && RE4DC_ACTOR_SPAN_MEMO31
unsigned scan_certificate(const Re4dcModelPart& p, const BlobHeader& b) {
    using namespace re4dc::format32;
#else
unsigned checked_certificate(const Re4dcModelPart& p, const BlobHeader& b) {
    using namespace re4dc::format32;
#if RE4DC_ACTOR_SOURCE_SPAN
    if(p.source_span.owner_serial) {
        unsigned certificate=kUvSourceDeclined;
        return prepare_owned(p,&certificate)?certificate:kUvSourceDeclined;
    }
#endif
#endif
    const unsigned code = uv_excess_bits(b), exponent = uv_certificate_exponent(code);
    if (!exponent) return code; // Legacy/preconverted data declines without a scan.
    if (!p.uv || p.stream != reinterpret_cast<const u8*>(&b) || p.stream_bytes < sizeof(BlobHeader))
        return kUvSourceDeclined;
    if ((reinterpret_cast<std::uintptr_t>(p.uv) & 1U) || !ram(p.uv, 4U)) return kUvSourceDeclined;
    unsigned readable_bytes = ~0U;
#if defined(__sh__)
    // RAM containment prevents a new read outside the existing source address
    // space. It does not establish an allocation extent or immutable ownership.
    readable_bytes = 0x8d000000U - unsigned(reinterpret_cast<std::uintptr_t>(p.uv));
#endif
    const unsigned rec_at = unsigned(b.rec4) * 4U, idx_at = unsigned(b.idx4) * 4U;
    if (!b.meshlets || b.levels > kMaxLevels || rec_at < sizeof(BlobHeader) ||
        b.meshlets > (rec_at - sizeof(BlobHeader)) / sizeof(MeshletInfo) ||
        idx_at < rec_at || idx_at > p.stream_bytes) return kUvSourceDeclined;
    const unsigned stride = 3U + ((b.flags & kHasCi) ? 1U : 0U) + ((b.flags & kHasBake) ? 1U : 0U);
    const unsigned records = (idx_at - rec_at) / (stride * 2U);
    const auto* table = reinterpret_cast<const MeshletInfo*>(p.stream + sizeof(BlobHeader));
    const LevelInfo* levels = nullptr;
    if (b.levels) {
        const unsigned at = unsigned(b.lod4) * 4U;
        if (at < idx_at || at > p.stream_bytes || b.levels > (p.stream_bytes - at) / sizeof(LevelInfo))
            return kUvSourceDeclined;
        levels = reinterpret_cast<const LevelInfo*>(p.stream + at);
        for (unsigned l = 0; l < b.levels; ++l) {
            const unsigned table_at = unsigned(levels[l].table4) * 4U;
            if (table_at < idx_at || table_at > p.stream_bytes ||
                b.meshlets > (p.stream_bytes - table_at) / sizeof(MeshletLevel)) return kUvSourceDeclined;
        }
    }
    const auto* data = reinterpret_cast<const std::uint16_t*>(p.stream + rec_at);
    for (unsigned m = 0; m < b.meshlets; ++m) {
        const unsigned count = table[m].n.vertices(), first = table[m].first;
        if (!count || count > kMaxVertices || first > records || count > records - first)
            return kUvSourceDeclined;
        // The format promises prefix-only LODs; reject a malformed extension
        // that would transform UV records outside the certified level-zero set.
        for (unsigned l = 0; l < b.levels; ++l) {
            const auto* lod = reinterpret_cast<const MeshletLevel*>(p.stream + unsigned(levels[l].table4) * 4U);
            if (lod[m].n.vertices() > count) return kUvSourceDeclined;
        }
        if (!uv_record_range(exponent, data + first * stride, stride, count, p.uv,
                             (p.flags & 0x80000000U) != 0, counters.scanned_records, readable_bytes)) return kUvSourceDeclined;
    }
    return code;
}
#if defined(RE4DC_ACTOR_SPAN_MEMO31) && RE4DC_ACTOR_SPAN_MEMO31
unsigned checked_certificate(const Re4dcModelPart& p, const BlobHeader& b) {
    using namespace re4dc::format32;
#if RE4DC_ACTOR_SOURCE_SPAN
    if(p.source_span.owner_serial) {
        unsigned certificate=kUvSourceDeclined;
        return prepare_owned(p,&certificate)?certificate:kUvSourceDeclined;
    }
#endif
    // ACTOR_SPAN_MEMO31: parts without an owner scanned every UV record on every draw (r100 MODELLED 1.25 ms per
    // drawn tick). The scan reads the blob and the UV array only, so its answer is kept per content in the same
    // entries (marked unowned in flags); dropped on a stream rewrite and with the lifetime epoch.
    if (p.stream == reinterpret_cast<const u8*>(&b) && p.stream_bytes >= 16U) {
        ContentKey ck;
        ck.info=p.info;ck.uv=p.uv;ck.stream=p.stream;ck.stream_bytes=p.stream_bytes;
        ck.positions=p.position_count;ck.normals=p.normal_count;
        ck.flags=(p.flags&0x80000000U)|0x40000000U;ck.epoch=re4dc_actor_span_epoch;
        std::memcpy(ck.head,p.stream,sizeof ck.head);
        ContentEntry& ce=content_entries[content_slot(p.stream)];
        if(same_content(ce.key,ck)){++content_hits;return ce.certificate;}
        const unsigned certificate=scan_certificate(p,b);
        ce={ck,certificate};
        return certificate;
    }
    return scan_certificate(p,b);
}
#endif
