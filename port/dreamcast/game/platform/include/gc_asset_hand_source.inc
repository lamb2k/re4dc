// Included inside leon_hand_pack after its fixed storage and read_at definition.
#if RE4DC_GC_ASSET_GATE
#define RE4DC_GC_ASSET_HAND_SOURCE 1
re4dc_gcasset::PayloadProof gcasset_hand_source,gcasset_hand_slot[2];
re4dc_gcasset::Digest gcasset_hand_directory_sha;
unsigned gcasset_hand_header[8],gcasset_hand_prefix_bytes;
bool gcasset_hand_started,gcasset_hand_candidate,gcasset_hand_checked,gcasset_hand_ready;
struct GcassetHandFile {
    file_t file;const unsigned* header=nullptr;unsigned at=0;
    static unsigned read(void* context,void* to,unsigned bytes){
        auto& self=*static_cast<GcassetHandFile*>(context);ssize_t got;
        {Re4dcIoScope io;got=fs_read(self.file,to,bytes);}
        if(got!=ssize_t(bytes))return 0;
        if(self.header && self.at<32){const unsigned n=bytes<32-self.at?bytes:32-self.at;
            if(std::memcmp(to,reinterpret_cast<const unsigned char*>(self.header)+self.at,n))return 0;}
        self.at+=bytes;return bytes;
    }
};
// Named startup only. This extra complete read grants no origin by pathname.
// The immutable mounted-CD source epoch must also cover later runtime handles;
// catalog retirement invalidates every inherited token without rehashing slots.
void gcasset_hand_startup(){
    using namespace re4dc_gcasset;
    if(gcasset_hand_started)return;
    gcasset_hand_started=true;
    for(unsigned side=0;side<2;++side)
        (void)payload_copy_register(gcasset_hand_slot[side],&gcasset_hand_slot[side],slot[side],kSlotBytes[side]);
#if RE4DC_LEON_HAND_RETAIN
    unresolved(SourceGeometry,"hand-retain-unqualified");return;
#else
    file_t file;{Re4dcIoScope io;file=fs_open(package(),O_RDONLY);}
    if(file==FILEHND_INVALID){unresolved(SourceGeometry,"hand-source-open");return;}
    GcassetHandFile reader{file};Digest full{},directory_sha{};bool ok=false;off_t total;
    {Re4dcIoScope io;total=fs_total(file);}
    auto& h=gcasset_hand_header;
    if(total>=32 && total<=40*1024*1024 && GcassetHandFile::read(&reader,h,32)==32 &&
       h[0]==kMagic && (h[1]&0xffffU)==kVersion && h[3]==kSlotBytes[0] && h[4]==kSlotBytes[1] && h[6]==unsigned(total)){
        const unsigned nr=h[1]>>16,nb=h[2]&0xffffU,ns=h[2]>>16,prefix=32+nr*12+nb*24+ns*4;
        if(nr<=kRows && nb>=2 && nb<=kBlobs && ns<=kSources && h[5]>=prefix && h[5]<=0x10000 && h[5]<=unsigned(total)){
            bool seek;{Re4dcIoScope io;seek=fs_seek(file,0,SEEK_SET)==0;}
            reader.header=h;reader.at=0;
            if(seek && fingerprint_read_prefix(full,directory_sha,GcassetHandFile::read,&reader,unsigned(total),prefix)){
                Re4dcIoScope io;ok=fs_total(file)==total;
            }
            if(ok)gcasset_hand_prefix_bytes=prefix;
        }
    }
    {Re4dcIoScope io;fs_close(file);}
    if(!ok){unresolved(SourceGeometry,"hand-source-read");return;}
    gcasset_hand_directory_sha=directory_sha;
    if(ensure_disc_catalog())(void)payload_capture_digest(gcasset_hand_source,&gcasset_hand_source,full);
#endif
}
// The real loader calls this only after its validation succeeds. Fixed memory
// comparison is permitted under LH; full hashing waits until its safe return.
void gcasset_hand_directory_candidate(const unsigned* header){
    gcasset_hand_candidate=gcasset_hand_source.serial && header &&
        !std::memcmp(header,gcasset_hand_header,sizeof gcasset_hand_header) &&
        nrows==(header[1]>>16) && nblobs==(header[2]&0xffffU) && nsrcs==(header[2]>>16) && file_bytes==header[6];
}
void gcasset_hand_directory_pump(){
    using namespace re4dc_gcasset;
    if(gcasset_hand_checked || !gcasset_hand_candidate)return;
    gcasset_hand_checked=true;
    if(nrows!=(gcasset_hand_header[1]>>16) || nblobs!=(gcasset_hand_header[2]&0xffffU) ||
       nsrcs!=(gcasset_hand_header[2]>>16) || file_bytes!=gcasset_hand_header[6]){
        unresolved(SourceGeometry,"hand-directory-counts");return;
    }
    struct Reader {
        PayloadSpan spans[4];unsigned index=0,at=0;
        static unsigned read(void* context,void* target,unsigned requested){
            auto& self=*static_cast<Reader*>(context);auto* out=static_cast<unsigned char*>(target);unsigned written=0;
            while(written<requested && self.index<4){const auto& span=self.spans[self.index];
                const unsigned left=span.bytes-self.at,take=left<requested-written?left:requested-written;
                std::memcpy(out+written,static_cast<const unsigned char*>(span.data)+self.at,take);
                self.at+=take;written+=take;if(self.at==span.bytes){++self.index;self.at=0;}
            }return written;
        }
    } reader{{{gcasset_hand_header,sizeof gcasset_hand_header},{rows,nrows*12},{blobs,nblobs*24},{srcs,nsrcs*4}}};
    Digest actual{};
    gcasset_hand_ready=gcasset_hand_source.serial && checked_current(gcasset_hand_source.asset) &&
        fingerprint_read(actual,Reader::read,&reader,gcasset_hand_prefix_bytes) &&
        !std::memcmp(actual.bytes,gcasset_hand_directory_sha.bytes,32);
    if(!gcasset_hand_ready)unresolved(SourceGeometry,"hand-directory-source");
}
#endif
