// Additional cold semantic and warm owner lifecycle gates over retained arrays.
// The included fixture identifies foreign roles as host sentinels, not live proof.
#define main retained_binding_probe_main
#include "bind_probe.cpp"
#undef main
#include <set>
#include <utility>

static unsigned cold_refusals=0,uv_components=0,record_fields=0,ordering=0,lifecycle=0;
static void write16(std::vector<unsigned char>& b,unsigned at,unsigned value) {
    b[at]=static_cast<unsigned char>(value);b[at+1]=static_cast<unsigned char>(value>>8);
}
static void cold_reject(const Bundle& invalid,bool run_still_valid,unsigned changed_run) {
    if(run_still_valid) {
        auto c=invalid.source;const auto& r=invalid.runs[changed_run];
        c.uv=r.uv;c.stream=r.stream;c.triangles=r.triangles;
        re4dc_source::ChunkProof proof{};
        assert(re4dc_source::preflight_chunk(c,proof)==re4dc_source::BlobError::None);
    }
    Qualified rejected{};assert(!qualify(invalid,rejected));++cold_refusals;
}
static void semantic_campaign(const Bundle& b) {
    using re4dc_source::pre_u16;using re4dc_source::pre_u32;
    for(unsigned run=0;run<b.run_count;++run) {
        const auto& r=b.runs[run];std::set<unsigned> referenced_uv;
        detail::Triangles triangles(r.stream);const unsigned char* corners[3];
        const unsigned char* first_record=nullptr;
        while(triangles.next(corners))for(const auto* corner:corners) {
            referenced_uv.insert(pre_u16(corner+4));if(!first_record)first_record=corner;
        }
        assert(first_record && !referenced_uv.empty());
        // Mutate every UV component actually referenced by the emitted stream.
        // Untouched padding/unused UV entries do not claim a semantic refusal.
        for(unsigned uv:referenced_uv)for(unsigned component=0;component<2;++component) {
            std::vector<unsigned char> changed(r.uv.data,r.uv.data+r.uv.size);
            changed[uv*4+component*2]^=1;auto invalid=b;
            invalid.runs[run].uv={changed.data(),changed.size()};cold_reject(invalid,true,run);++uv_components;
        }
        // Source position/normal indices are bounded but semantically exact.
        for(unsigned field=0;field<2;++field) {
            std::vector<unsigned char> changed(r.stream.data,r.stream.data+r.stream.size);
            const unsigned at=unsigned(first_record-r.stream.data)+field*2;
            const unsigned count=field?b.source.normal_count:b.source.position_count;assert(count>1);
            write16(changed,at,(pre_u16(changed.data()+at)+1)%count);
            auto invalid=b;invalid.runs[run].stream={changed.data(),changed.size()};cold_reject(invalid,true,run);++record_fields;
        }
        // Generated FE strips contain one ordered triangle per terminated list.
        const unsigned index_at=pre_u16(r.stream.data+10)*4u;
        bool swapped=false;
        for(unsigned meshlet=0;meshlet<pre_u16(r.stream.data+4)&&!swapped;++meshlet) {
            const auto* t=r.stream.data+32+meshlet*8;
            const unsigned ni=(pre_u32(t)>>8)&4095,base=index_at+pre_u16(t+6);
            for(unsigned j=0;j+5<ni;j+=3) {
                if(!(r.stream.data[base+j+2]&128u)||!(r.stream.data[base+j+5]&128u))continue;
                if(!std::memcmp(r.stream.data+base+j,r.stream.data+base+j+3,3))continue;
                std::vector<unsigned char> changed(r.stream.data,r.stream.data+r.stream.size);
                for(unsigned k=0;k<3;++k)std::swap(changed[base+j+k],changed[base+j+3+k]);
                auto invalid=b;invalid.runs[run].stream={changed.data(),changed.size()};cold_reject(invalid,true,run);++ordering;swapped=true;break;
            }
        }
        // A triangle can retain its count/range while reversing its winding.
        bool reversed=false;
        for(unsigned meshlet=0;meshlet<pre_u16(r.stream.data+4)&&!reversed;++meshlet) {
            const auto* t=r.stream.data+32+meshlet*8;
            const unsigned ni=(pre_u32(t)>>8)&4095,base=index_at+pre_u16(t+6);
            for(unsigned j=0;j+2<ni;j+=3) {
                if(!(r.stream.data[base+j+2]&128u)||r.stream.data[base+j]==r.stream.data[base+j+1])continue;
                std::vector<unsigned char> changed(r.stream.data,r.stream.data+r.stream.size);
                std::swap(changed[base+j],changed[base+j+1]);auto invalid=b;
                invalid.runs[run].stream={changed.data(),changed.size()};cold_reject(invalid,true,run);++ordering;reversed=true;break;
            }
        }
        assert(reversed); // Tiny runs need not contain two different triangles.
        // Source render colour and conservative bounds are part of the proof.
        for(unsigned field: {6u,16u}) {
            std::vector<unsigned char> changed(r.stream.data,r.stream.data+r.stream.size);
            if(field==6)changed[6]^=1;
            else {const float value=re4dc_source::pre_float(changed.data()+16)+1.f;std::memcpy(changed.data()+16,&value,4);}
            auto invalid=b;invalid.runs[run].stream={changed.data(),changed.size()};cold_reject(invalid,true,run);
        }
    }
    // Unsupported authored LOD/colour/bake variants decline before admission.
    for(unsigned flag: {1u,2u,128u}) {
        std::vector<unsigned char> changed(b.source.stream.data,b.source.stream.data+b.source.stream.size);
        changed[2]|=static_cast<unsigned char>(flag);auto invalid=b;invalid.source.stream={changed.data(),changed.size()};cold_reject(invalid,false,0);
    }
    for(unsigned at: {3u,12u,14u}) {
        std::vector<unsigned char> changed(b.source.stream.data,b.source.stream.data+b.source.stream.size);
        changed[at]=1;auto invalid=b;invalid.source.stream={changed.data(),changed.size()};cold_reject(invalid,false,0);
    }
}
static void warm_lifecycle(const Bundle& b) {
#if RE4DC_ATLAS_RUNTIME_PROBE
    pl08_pack.published=true;pl08_pack.generation=10;re4dc_atlas_retire_pl08();
    auto ordinary=source_plan(b),split=ordinary;assert(re4dc_atlas_apply(&split));++lifecycle;
    const auto split_before=bytes(split);assert(!re4dc_atlas_apply(&split));unchanged(split,split_before);++lifecycle;
    auto projected=ordinary;assert(re4dc_atlas_project(&split,&projected));++lifecycle;
    // Warm hand changes use all17 retained source blobs, without altering body proof.
    for(unsigned h=0;h<case_data::hand_count;++h) {
        auto current=ordinary;const unsigned source_role=case_data::hand_role(h);
        const unsigned role=b.appearance==0x109?source_role-1:source_role;
        current.input[role]=case_data::hand_input(h);current.immutable_asset_id[role]=300+h;
        for(unsigned i=0;i<current.run_count;++i)if(current.runs[i].role==role) {
            auto& r=current.runs[i];r.immutable_asset_id=current.immutable_asset_id[role];r.uv=current.input[role].uv;
            r.stream=current.input[role].stream;r.triangles=current.input[role].triangles;
        }
        auto transformed=current;assert(re4dc_atlas_apply(&transformed));auto recovered=current;
        assert(re4dc_atlas_project(&transformed,&recovered));
        assert(same(recovered.input[role],current.input[role])&&recovered.immutable_asset_id[role]==current.immutable_asset_id[role]&&recovered.info[role]==current.info[role]);
        if(b.appearance==0x109)assert(recovered.input[3].triangles==37&&same(recovered.input[3],ordinary.input[3]));
        ++lifecycle;
    }
    // A cold unsupported replacement leaves the ordinary plan byte-for-byte.
    std::vector<unsigned char> lod(b.source.stream.data,b.source.stream.data+b.source.stream.size);lod[3]=1;
    auto unsupported=ordinary;unsupported.input[b.role].stream={lod.data(),lod.size()};
    for(unsigned i=0;i<unsupported.run_count;++i)if(unsupported.runs[i].role==b.role)unsupported.runs[i].stream=unsupported.input[b.role].stream;
    const auto unsupported_before=bytes(unsupported);assert(!re4dc_atlas_apply(&unsupported));unchanged(unsupported,unsupported_before);++lifecycle;
    auto restored=ordinary;assert(re4dc_atlas_apply(&restored));assert(re4dc_atlas_project(&restored,&projected));++lifecycle;
    if(b.appearance==0x100) {
        re4dc_atlas_retire_pl08();assert(re4dc_atlas_project(&restored,&projected));++lifecycle;
    } else {
        ++pl08_pack.generation;const auto before=bytes(projected);
        assert(!re4dc_atlas_project(&restored,&projected));unchanged(projected,before);++lifecycle;
        auto fresh=ordinary;assert(re4dc_atlas_apply(&fresh));++lifecycle;
        re4dc_atlas_retire_pl08();assert(!re4dc_atlas_project(&fresh,&projected));unchanged(projected,before);++lifecycle;
        pl08_pack.published=false;auto absent=ordinary;const auto absent_before=bytes(absent);
        assert(!re4dc_atlas_apply(&absent));unchanged(absent,absent_before);++lifecycle;
        pl08_pack.published=true;pl08_pack.generation=0;
        assert(!re4dc_atlas_apply(&absent));unchanged(absent,absent_before);++lifecycle;
        pl08_pack.generation=11;auto republished=ordinary;assert(re4dc_atlas_apply(&republished));assert(re4dc_atlas_project(&republished,&projected));++lifecycle;
    }
#endif
}
int main() {
    assert(retained_binding_probe_main()==0);auto b=case_data::bundle();
    semantic_campaign(b);warm_lifecycle(b);
    std::printf("{\"source_only_cold_campaign\":true,\"appearance\":%u,\"cold_refusals\":%u,\"referenced_uv_components\":%u,\"record_fields\":%u,\"order_winding_refusals\":%u,\"runtime_wrapper_lifecycle_cases\":%u,\"default_off_unmodified\":true,\"target_admission\":false}\n",b.appearance,cold_refusals,uv_components,record_fields,ordering,lifecycle);
}