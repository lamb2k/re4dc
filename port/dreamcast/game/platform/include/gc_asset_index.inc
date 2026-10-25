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
// the first row of each block, built in the install pass. A bind binary-searches
// the candidate block(s) with single 112-byte row reads (~6). BSS: 4096 + 3584 B.
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
// Resident texture table (gc-catalog24b option A, gate-ON diagnostics only):
// every texture row as {first 4 digest bytes, row index}, sorted by prefix then
// row; 6 B per row (7350 rows: ~44 KB), one KOS allocation per install. A texture
// bind confirms each prefix match with one row read: same verdict as sparse_find.
struct TexEntry{unsigned char prefix[4];unsigned short row;};
static_assert(sizeof(TexEntry)==6,"packed texture entry");
TexEntry* tex_table;unsigned tex_count;
void tex_table_free(){std::free(tex_table);tex_table=nullptr;tex_count=0;}
bool tex_less(const TexEntry& a,const TexEntry& b){const int o=std::memcmp(a.prefix,b.prefix,4);return o?o<0:a.row<b.row;}
// Description ring (gate-ON only, 32 x 104 B = 3.3 KB): the row a
// texture bind just confirmed, so that texture's first room use (describe) reads
// no record again. Token-tagged; a miss reads the row as before.
struct DescEntry{unsigned value;AssetDescription row;};
constexpr unsigned DescRing=16;   // gc-catalog24b: 128 -> 32 -> 16 (KOS: gate-ON r101 room load OOM; r8 Motion)
DescEntry* desc_ring;unsigned desc_next;
bool desc_find(unsigned value,AssetDescription& out){
    if(desc_ring)for(unsigned i=0;i<DescRing;++i)if(desc_ring[i].value==value){out=desc_ring[i].row;return true;}
    return false;
}
void desc_store(unsigned value,const AssetDescription& row){
    if(!desc_ring)return;
    auto& d=desc_ring[desc_next++%DescRing];d.value=value;d.row=row;
}
SparseResult tex_find(const char* id,const Digest& digest,unsigned epoch,unsigned& index,AssetDescription& found){
    unsigned l=0,u=tex_count;
    while(l<u){const unsigned m=(l+u)/2;if(std::memcmp(tex_table[m].prefix,digest.bytes,4)<0)l=m+1;else u=m;}
    for(;l<tex_count && !std::memcmp(tex_table[l].prefix,digest.bytes,4);++l){
        AssetDescription row;
        if(!index_read_row(catalog_read,catalog_context,epoch,catalog_rows,catalog_bytes,tex_table[l].row,row))return SparseFault;
        if(!index_compare(row,"texture",id,digest)){index=tex_table[l].row;found=row;return SparseFound;}
    }
    return SparseAbsent;
}
// Exact lookup: returns the row index of kind/id/digest, or SparseAbsent.
SparseResult sparse_find(const char* kind,const char* id,const Digest& digest,unsigned epoch,unsigned& index){
    const unsigned rows=catalog_rows;
    unsigned char q[SparseKeyBytes];sparse_prefix(kind,id,digest,q);
    unsigned lower=0,upper=sparse_blocks;   // first block whose key > q
    while(lower<upper){const unsigned m=(lower+upper)/2;if(std::memcmp(sparse_key[m],q,SparseKeyBytes)<=0)lower=m+1;else upper=m;}
    if(!lower)return SparseAbsent;          // q sorts before row 0
    const unsigned hi=lower-1;unsigned lo=hi;
    while(lo && !std::memcmp(sparse_key[lo],q,SparseKeyBytes))--lo; // equal prefixes may start in the previous block
    // Binary search over the candidate rows with single-row reads (~5 x 112 B):
    // small reads cost far less disc time than a whole 3.5 KiB block.
    const unsigned first=lo*sparse_block_rows,last=(hi+1)*sparse_block_rows<rows?(hi+1)*sparse_block_rows:rows;
    unsigned l=first,u=last;AssetDescription row;
    while(l<u){
        const unsigned m=(l+u)/2;
        if(!index_read_row(catalog_read,catalog_context,epoch,rows,catalog_bytes,m,row))return SparseFault;
        if(index_compare(row,kind,id,digest)<0)l=m+1;else u=m;
    }
    if(l==last)return SparseAbsent;
    if(!index_read_row(catalog_read,catalog_context,epoch,rows,catalog_bytes,l,row))return SparseFault;
    if(index_compare(row,kind,id,digest))return SparseAbsent;
    index=l;return SparseFound;
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
