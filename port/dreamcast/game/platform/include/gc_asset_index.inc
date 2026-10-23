// Included inside gc_asset_gate.cpp's private namespace. No allocation or
// whole-catalog resident table; caller owns one immutable read-only CD handle.
unsigned index_word(const unsigned char* p){unsigned value;std::memcpy(&value,p,4);return value;}
bool new_catalog_epoch(){
    catalog_ok=false;catalog=nullptr;catalog_read=nullptr;catalog_rows=catalog_bytes=unknown_count=0;
    if(catalog_epoch>=(1U<<18)-2)return false;
    ++catalog_epoch;return true;
}
struct IndexStream{CatalogReadAt read;void* context;unsigned offset;};
unsigned index_stream_read(void* opaque,void* target,unsigned bytes){
    auto& stream=*static_cast<IndexStream*>(opaque);
    const unsigned count=stream.read(stream.context,stream.offset,target,bytes);stream.offset+=count;return count;
}
int index_compare(const AssetDescription& row,const char* kind,const char* id,const Digest& digest){
    int order=std::strcmp(row.kind,kind);if(order)return order;
    order=std::strcmp(row.id,id);return order?order:std::memcmp(row.digest.bytes,digest.bytes,32);
}
bool index_string(const unsigned char* bytes,unsigned count,char* out){
    unsigned n=0;for(;n<count && bytes[n];++n)out[n]=char(bytes[n]);
    if(n==count)return false;
    out[n]=0;
    for(unsigned i=n;i<count;++i)if(bytes[i])return false;
    return token(out,count);
}
bool index_row(unsigned index,AssetDescription& out){
    if(index>=catalog_rows)return false;
    if(!catalog_read){
        const auto& row=catalog[index];out={};
        std::strcpy(out.kind,row.kind);std::strcpy(out.id,row.id);out.digest=row.digest;out.provenance=row.provenance;return true;
    }
    unsigned char bytes[112];const unsigned offset=128+index*112;
    if(offset>catalog_bytes || sizeof bytes>catalog_bytes-offset || catalog_read(catalog_context,offset,bytes,sizeof bytes)!=sizeof bytes)return false;
    out={};
    if(!index_string(bytes,16,out.kind) || !index_string(bytes+16,48,out.id) || bytes[96]>Authored)return false;
    for(unsigned i=97;i<112;++i)if(bytes[i])return false;
    std::memcpy(out.digest.bytes,bytes+64,32);out.provenance=Provenance(bytes[96]);return true;
}
