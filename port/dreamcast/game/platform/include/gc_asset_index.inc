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
bool index_decode_row(const unsigned char* bytes,AssetDescription& out){
    AssetDescription row{};
    if(!index_string(bytes,16,row.kind) || !index_string(bytes+16,48,row.id) || bytes[96]>Authored)return false;
    for(unsigned i=97;i<112;++i)if(bytes[i])return false;
    std::memcpy(row.digest.bytes,bytes+64,32);row.provenance=Provenance(bytes[96]);
    out=row;return true;
}
bool index_read_row(CatalogReadAt read,void* context,unsigned epoch,unsigned rows,unsigned total,unsigned index,AssetDescription& out){
    if(index>=rows)return false;
    unsigned char bytes[112];const unsigned offset=128+index*112;
    if(offset>total || sizeof bytes>total-offset ||
       index_read_at(read,context,epoch,offset,bytes,sizeof bytes)!=sizeof bytes)return false;
    AssetDescription row{};
    if(!index_decode_row(bytes,row))return false;
    if(!index_generation(epoch))return false;
    out=row;return true;
}
// Sparse resident index (gc-catalog24b): the 16-byte order-preserving prefix of
// the first row of each block, built in the install pass. A bind reads one block
// (32 rows, 3584 B) instead of ~13 uncached row reads. BSS: 4096 + 3584 B.
constexpr unsigned SparseKeys=256,SparseKeyBytes=16,BufferRows=32;
unsigned char sparse_key[SparseKeys][SparseKeyBytes];
unsigned sparse_blocks,sparse_block_rows;
unsigned char block_buffer[BufferRows*112];
// kind NUL id NUL digest, first 16 bytes: memcmp order of prefixes is a monotone
// (non-strict) image of index_compare order (strcmp compares unsigned bytes).
void sparse_prefix(const char* kind,const char* id,const Digest& digest,unsigned char* out){
    unsigned n=0;
    for(const char* p=kind;*p && n<SparseKeyBytes;++p)out[n++]=static_cast<unsigned char>(*p);
    if(n<SparseKeyBytes)out[n++]=0;
    for(const char* p=id;*p && n<SparseKeyBytes;++p)out[n++]=static_cast<unsigned char>(*p);
    if(n<SparseKeyBytes)out[n++]=0;
    for(unsigned i=0;i<32 && n<SparseKeyBytes;++i)out[n++]=digest.bytes[i];
}
enum SparseResult{SparseFound,SparseAbsent,SparseFault};
// Exact lookup: returns the row index of kind/id/digest, or SparseAbsent.
SparseResult sparse_find(const char* kind,const char* id,const Digest& digest,unsigned epoch,unsigned& index){
    const unsigned rows=catalog_rows;
    unsigned char q[SparseKeyBytes];sparse_prefix(kind,id,digest,q);
    unsigned lower=0,upper=sparse_blocks;   // first block whose key > q
    while(lower<upper){const unsigned m=(lower+upper)/2;if(std::memcmp(sparse_key[m],q,SparseKeyBytes)<=0)lower=m+1;else upper=m;}
    if(!lower)return SparseAbsent;          // q sorts before row 0
    const unsigned hi=lower-1;unsigned lo=hi;
    while(lo && !std::memcmp(sparse_key[lo],q,SparseKeyBytes))--lo; // equal prefixes may start in the previous block
    for(unsigned b=lo;b<=hi;++b){
        const unsigned start=b*sparse_block_rows,end=start+sparse_block_rows<rows?start+sparse_block_rows:rows;
        for(unsigned h=start;h<end;h+=BufferRows){
            const unsigned n=end-h<BufferRows?end-h:BufferRows;
            if(index_read_at(catalog_read,catalog_context,epoch,128+h*112,block_buffer,n*112)!=n*112)return SparseFault;
            AssetDescription row;
            if(!index_decode_row(block_buffer+(n-1)*112,row))return SparseFault;
            if(index_compare(row,kind,id,digest)<0)continue;   // beyond this part of the block
            unsigned l=0,u=n;
            while(l<u){
                const unsigned m=(l+u)/2;
                if(!index_decode_row(block_buffer+m*112,row))return SparseFault;
                if(index_compare(row,kind,id,digest)<0)l=m+1;else u=m;
            }
            if(!index_decode_row(block_buffer+l*112,row))return SparseFault;
            if(index_compare(row,kind,id,digest))return SparseAbsent;
            index=h+l;return SparseFound;
        }
    }
    return SparseAbsent;
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
