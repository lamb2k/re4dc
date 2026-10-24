// Fixed metadata observers inside leon_hand_pack. No hash/IO/log/allocation.
#if RE4DC_GC_ASSET_GATE
using re4dc_gcasset::HandCopyProof;
HandCopyProof gcasset_hand_copy[2],gcasset_hand_cell[4],gcasset_hand_scratch;
re4dc_gcasset::HandDerivationState gcasset_hand_deriving[2];
unsigned gcasset_hand_clock,gcasset_hand_aica;
struct GcassetHandJob {
    void* allocation=nullptr;void* data=nullptr;void* thread=nullptr;
    unsigned offset=0,bytes=0;int blob=-1;HandCopyProof proof{};bool complete=false;
} gcasset_hand_job;
unsigned gcasset_hand_parent(){
    return gcasset_hand_candidate && gcasset_hand_source.serial &&
        re4dc_gcasset::checked_current(gcasset_hand_source.asset)?gcasset_hand_source.serial:0;
}
bool gcasset_hand_blob(int b){
    if(b<0 || unsigned(b)>=nblobs || nblobs!=(gcasset_hand_header[2]&0xffffU) || !gcasset_hand_parent())return false;
    const auto& x=blobs[b];const unsigned n=blob_bytes(x),off=unsigned(x.offset32)*32U;
    return (x.role-5U)<2 && n && n<=kSlotBytes[x.role-5] && off>=gcasset_hand_header[5] &&
        off<=file_bytes && n<=file_bytes-off && x.pc && x.nc && x.pal && x.pal<=256 &&
        x.pc<=x.size[0]/8 && x.nc<=x.size[1]/8 && x.pal<=x.size[4]/16 &&
        x.size[2] && x.stream && x.stream<=x.size[3];
}
HandCopyProof gcasset_hand_read_begin(int b){
    if(!gcasset_hand_blob(b))return {};
    const auto& x=blobs[b];return re4dc_gcasset::hand_read_begin(gcasset_hand_clock,gcasset_hand_parent(),unsigned(b),
        unsigned(x.offset32)*32U,blob_bytes(x),file_bytes);
}
HandCopyProof gcasset_hand_read_end(HandCopyProof ticket,int b,bool ok){
    return re4dc_gcasset::hand_read_complete(ticket,gcasset_hand_parent(),unsigned(b),ok && gcasset_hand_blob(b));
}
void gcasset_hand_slot_revoke(unsigned side){
    re4dc_gcasset::payload_copy_invalidate(gcasset_hand_slot[side],&gcasset_hand_slot[side]);
    gcasset_hand_copy[side]={};gcasset_hand_deriving[side]={};
}
HandCopyProof gcasset_hand_origin(const void* from,int b){
    const unsigned source=gcasset_hand_parent();
    for(unsigned side=0;side<2;++side)if(from==slot[side] && re4dc_gcasset::hand_copy_valid(gcasset_hand_copy[side],source,unsigned(b)))return gcasset_hand_copy[side];
    if(from==re4dc_dvd_buff+0x10000 && re4dc_gcasset::hand_copy_valid(gcasset_hand_scratch,source,unsigned(b)))return gcasset_hand_scratch;
    if(gcasset_hand_job.complete && from==gcasset_hand_job.data && gcasset_hand_job.blob==b &&
       re4dc_gcasset::hand_copy_valid(gcasset_hand_job.proof,source,unsigned(b)))return gcasset_hand_job.proof;
    return {};
}
HandCopyProof gcasset_hand_slot_begin(unsigned side,int b,HandCopyProof origin){
    gcasset_hand_slot_revoke(side);
    return re4dc_gcasset::hand_copy_begin(gcasset_hand_copy[side],origin,gcasset_hand_clock,gcasset_hand_parent(),unsigned(b));
}
void gcasset_hand_slot_end(unsigned side,int b,HandCopyProof ticket){
    (void)re4dc_gcasset::hand_copy_complete(gcasset_hand_copy[side],ticket,gcasset_hand_parent(),unsigned(b),gcasset_hand_blob(b));
}
HandCopyProof gcasset_hand_cell_begin(unsigned c,int b,const void* from){
    if(gcasset_hand_aica!=aica){for(auto& cell:gcasset_hand_cell)cell={};gcasset_hand_aica=aica;}
    return re4dc_gcasset::hand_copy_begin(gcasset_hand_cell[c],gcasset_hand_origin(from,b),gcasset_hand_clock,gcasset_hand_parent(),unsigned(b));
}
void gcasset_hand_cell_end(unsigned c,int b,HandCopyProof ticket){
    // Issued ordered stores. A later spu_memread performs its FIFO wait and
    // complete CPU readback; this is not an ARM/DMA completion acknowledgement.
    (void)re4dc_gcasset::hand_copy_complete(gcasset_hand_cell[c],ticket,gcasset_hand_parent(),unsigned(b),aica && gcasset_hand_aica==aica && gcasset_hand_blob(b));
}
HandCopyProof gcasset_hand_cell_origin(unsigned c,int b){
    return aica && gcasset_hand_aica==aica && cell_blob[c]==b &&
        re4dc_gcasset::hand_copy_valid(gcasset_hand_cell[c],gcasset_hand_parent(),unsigned(b))?gcasset_hand_cell[c]:HandCopyProof{};
}
void gcasset_hand_job_begin(int b,void* allocation,void* data){
    gcasset_hand_job={};if(!gcasset_hand_blob(b) || !allocation || !data)return;
    gcasset_hand_job.allocation=allocation;gcasset_hand_job.data=data;gcasset_hand_job.blob=b;
    gcasset_hand_job.offset=unsigned(blobs[b].offset32)*32U;gcasset_hand_job.bytes=blob_bytes(blobs[b]);
    gcasset_hand_job.proof=gcasset_hand_read_begin(b);
}
void gcasset_hand_job_end(void* thread,void* allocation,void* data,int b,bool ok){
    const bool match=thread && gcasset_hand_job.thread==thread && gcasset_hand_job.allocation==allocation &&
        gcasset_hand_job.data==data && gcasset_hand_job.blob==b && gcasset_hand_blob(b) &&
        gcasset_hand_job.offset==unsigned(blobs[b].offset32)*32U && gcasset_hand_job.bytes==blob_bytes(blobs[b]);
    gcasset_hand_job.proof=gcasset_hand_read_end(gcasset_hand_job.proof,b,ok && match);
    gcasset_hand_job.complete=bool(gcasset_hand_job.proof.source);
}
void gcasset_hand_slot_publish(unsigned side,int b){
    if(gcasset_hand_blob(b) && blobs[b].role==5+side &&
       re4dc_gcasset::hand_copy_valid(gcasset_hand_copy[side],gcasset_hand_parent(),unsigned(b)))
        (void)re4dc_gcasset::payload_copy_publish(gcasset_hand_slot[side],&gcasset_hand_slot[side],gcasset_hand_source,gcasset_hand_parent());
}
bool gcasset_hand_chunk_current(unsigned side){
    const int b=slot_blob[side];if(!gcasset_hand_ready || !gcasset_hand_blob(b) || blobs[b].role!=5+side ||
        !re4dc_gcasset::hand_copy_valid(gcasset_hand_copy[side],gcasset_hand_parent(),unsigned(b)) ||
        !re4dc_gcasset::payload_copy_current(gcasset_hand_slot[side]))return false;
    const auto& c=leon4k::chunks[5+side];const auto& x=blobs[b];const unsigned char* arrays[5];auto* p=slot[side];
    for(unsigned i=0;i<5;++i){arrays[i]=p;p+=r32(x.size[i]);}
    return c.source_info==5+side && c.positions==arrays[0] && c.normals==arrays[1] && c.uv==arrays[2] &&
        c.stream==arrays[3] && reinterpret_cast<const unsigned char*>(c.weights)==arrays[4] &&
        c.position_count==x.pc && c.normal_count==x.nc && c.palette_count==x.pal && c.triangles==x.tri && c.stream_bytes==x.stream;
}
unsigned gcasset_hand_derive_begin(const void* target,unsigned bytes){
    const auto at=reinterpret_cast<std::uintptr_t>(target);
    for(unsigned side=0;side<2;++side){const auto base=reinterpret_cast<std::uintptr_t>(slot[side]);
        if(!target || !bytes || (at<=base?base-at>=bytes:at-base>=kSlotBytes[side]))continue;
        if(!gcasset_hand_chunk_current(side)){gcasset_hand_slot_revoke(side);return 0;}
        const auto& c=leon4k::chunks[5+side];const auto& x=blobs[slot_blob[side]];
        return re4dc_gcasset::hand_derive_begin(gcasset_hand_deriving[side],gcasset_hand_slot[side],gcasset_hand_copy[side],
            gcasset_hand_parent(),unsigned(slot_blob[side]),c.stream,x.size[3],target,bytes);
    }return 0;
}
void gcasset_hand_derive_end(unsigned ticket,bool complete){
    for(unsigned side=0;side<2;++side)if(ticket && gcasset_hand_deriving[side].serial==ticket){
        (void)re4dc_gcasset::hand_derive_end(gcasset_hand_deriving[side],gcasset_hand_slot[side],gcasset_hand_copy[side],
            gcasset_hand_parent(),unsigned(slot_blob[side]),ticket,complete);return;
    }
}
#endif
