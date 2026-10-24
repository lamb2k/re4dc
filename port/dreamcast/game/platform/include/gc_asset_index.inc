// Included inside gc_asset_gate.cpp's private namespace. No allocation or
// whole-catalog resident table. APIs remain owner-only; epoch checks reject
// retirement/replacement during a callback, not arbitrary concurrent mutation.
unsigned index_word(const unsigned char* p){unsigned value;std::memcpy(&value,p,4);return value;}
bool new_catalog_epoch(){
    catalog_ok=false;catalog=nullptr;catalog_read=nullptr;catalog_context=nullptr;
    catalog_rows=catalog_bytes=unknown_count=0;
    if(catalog_epoch>=(1U<<18)-2){catalog_epoch=(1U<<18)-1;return false;}
    ++catalog_epoch;return true;
}
bool index_generation(unsigned epoch){return epoch && epoch<(1U<<18)-1 && epoch==catalog_epoch;}
unsigned index_read_at(CatalogReadAt read,void* context,unsigned epoch,unsigned offset,void* target,unsigned bytes){
    if(!read || !index_generation(epoch))return 0;
    const unsigned count=read(context,offset,target,bytes);
    return index_generation(epoch)?count:0;
}
struct IndexStream{CatalogReadAt read;void* context;unsigned offset,epoch;};
unsigned index_stream_read(void* opaque,void* target,unsigned bytes){
    auto& stream=*static_cast<IndexStream*>(opaque);
    const unsigned count=index_read_at(stream.read,stream.context,stream.epoch,stream.offset,target,bytes);
    stream.offset+=count;return count;
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
bool index_read_row(CatalogReadAt read,void* context,unsigned epoch,unsigned rows,unsigned total,unsigned index,AssetDescription& out){
    if(index>=rows)return false;
    unsigned char bytes[112];const unsigned offset=128+index*112;
    if(offset>total || sizeof bytes>total-offset ||
       index_read_at(read,context,epoch,offset,bytes,sizeof bytes)!=sizeof bytes)return false;
    AssetDescription row{};
    if(!index_string(bytes,16,row.kind) || !index_string(bytes+16,48,row.id) || bytes[96]>Authored)return false;
    for(unsigned i=97;i<112;++i)if(bytes[i])return false;
    std::memcpy(row.digest.bytes,bytes+64,32);row.provenance=Provenance(bytes[96]);
    if(!index_generation(epoch))return false;
    out=row;return true;
}
bool index_row(unsigned index,AssetDescription& out){
    const unsigned epoch=catalog_epoch,rows=catalog_rows;
    if(!catalog_ok || !index_generation(epoch) || index>=rows)return false;
    if(!catalog_read){
        const auto& row=catalog[index];out={};
        std::strcpy(out.kind,row.kind);std::strcpy(out.id,row.id);out.digest=row.digest;out.provenance=row.provenance;return true;
    }
    return index_read_row(catalog_read,catalog_context,epoch,rows,catalog_bytes,index,out) &&
        catalog_ok && index_generation(epoch);
}
