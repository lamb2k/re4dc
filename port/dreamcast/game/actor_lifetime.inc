// Included once after material row definitions and bounded texture comparator.
// Full BIN identity is computed at archive adoption, before relocation/FE.
// Metadata borrows real source allocations; it never owns or duplicates them.
#include "actor_transaction_diag.h"
#if RE4DC_LEON_HAND_POSES
#include "pl_body.h"
// LEON_HAND_POSES: 5 when info is the player's current right hand info, 6 the left hand, else 0 (m must be the player).
static unsigned re4dc_leon_hand_role(const cModel* m,const cModelInfo* info) {
    if(!pPL || m!=(const cModel*)pPL || !pPL->Body || !info)return 0;
#if RE4DC_NMR_ASHLEY >= 2 && defined(RE4DC_NMR_PL_ASHLEY) && RE4DC_NMR_PL_ASHLEY
    // The Leon pose shortcut must not bypass playable Ashley's hand proof.
    // Her 141-joint owner binds its open/closed variant through exact records.
    if(m->id!=0u || m->nParts!=119u)return 0;
#endif
    if(info==pPL->Body->pRight)return 5;
    if(info==pPL->Body->pLeft)return 6;
    return 0;
}
#endif
#if RE4DC_CROWD_CENSUS
unsigned crowd_adopt_calls,crowd_adopt_ok,crowd_adopt_fail[4],crowd_archive_full,crowd_archive_unsupported,crowd_revokes,crowd_revoked_infos,crowd_readopt_ok,crowd_readopt_fail;
#define CROWD_LIFE(stmt) stmt
#else
#define CROWD_LIFE(stmt)
#endif
namespace re4dc_material { namespace life {
// ACTOR_GANADO_PS2_STUMP (lane stump17): each Ganado archive also admits up to 8 stump / hand-pose assets (em12 / em13 /
// em15: 8). r100 after the ambush uses 26 of 48 without the knob; 16 more covers two Ganado archives' variants beside
// that (24 would cross the 16 KiB character data block step on the warp image, char_data_block.ld).
#if RE4DC_ACTOR_GANADO_PS2_STUMP
#define RE4DC_LIFE_VARIANT_ASSETS 16
#else
#define RE4DC_LIFE_VARIANT_ASSETS 0
#endif
#if RE4DC_NATIVE_MODEL_REGISTRY
// Registry descriptors adopt their source infos too: room for them beside a full Ganado crowd.
constexpr unsigned kArchives=8,kAssets=48+RE4DC_LIFE_VARIANT_ASSETS,kInfos=192,kModels=40;
#else
constexpr unsigned kArchives=8,kAssets=40+RE4DC_LIFE_VARIANT_ASSETS,kInfos=160,kModels=40;
#endif
struct Archive { const void* key;const unsigned char* base;unsigned bytes,revision,family; };
struct Asset {
    const ModelData* data;const unsigned char* base;unsigned bytes;
    unsigned archive,owner_revision,serial;BlobMask templates;unsigned pending;
    const void* section[7]; // head,colour,UV,weights,parts,positions,normals
};
struct Info { cModelInfo* info;unsigned asset,asset_serial,roles[kRoleMaskWords],tpl_owner,tpl_revision;const void* tpl;unsigned tpl_bytes; };
struct Binding { cModel* model;const void* parts;unsigned serial,revision,epoch; };
static_assert(sizeof(source_blobs)/sizeof(source_blobs[0])<=kBlobMaskBits,"asset template mask capacity");
static_assert(sizeof(roles)/sizeof(roles[0])<=kRoleMaskBits,"info role mask capacity");
static_assert(sizeof(void*)!=4 || (sizeof(Archive)==20 && sizeof(Asset)==60u+sizeof(BlobMask)-sizeof(unsigned) && sizeof(Info)==28u+kRoleMaskWords*4u && sizeof(Binding)==20),"reviewed 32-bit metadata size");
Archive archives[kArchives]{};Asset assets[kAssets]{};Info infos_live[kInfos]{};Binding bindings[kModels]{};
unsigned serial=1,epoch=1;bool exhausted=false;
unsigned next() {if(exhausted || serial==~0u){exhausted=true;return 0;}return ++serial;}
bool span(const void* begin,unsigned size,const void* p,unsigned n) {
    const auto a=reinterpret_cast<std::uintptr_t>(begin),b=reinterpret_cast<std::uintptr_t>(p);
    return begin && p && b>=a && b-a<=size && n<=size-(b-a);
}
bool overlap(const void* a,unsigned an,const void* b,unsigned bn) {
    const auto x=reinterpret_cast<std::uintptr_t>(a),y=reinterpret_cast<std::uintptr_t>(b);
    return an && bn && (x<=y ? y-x<an : x-y<bn);
}
void changed() {epoch=next();}
void revoke(unsigned owner) {
#if RE4DC_CROWD_CENSUS
    ++crowd_revokes;
    for(auto& i:infos_live)if(i.info && (i.tpl_owner==owner || assets[i.asset].archive==owner))++crowd_revoked_infos;
#endif
    for(auto& i:infos_live)if(i.info && (i.tpl_owner==owner || assets[i.asset].archive==owner))i={};
    for(auto& a:assets)if(a.data && a.archive==owner)a={};
    archives[owner]={};changed();
}
bool entry(const Archive& o,unsigned no,const char* tag,const unsigned char*& begin,unsigned& size) {
    if(!o.key || no<4 || !span(o.base,o.bytes,o.base,16))return false;
    const unsigned count=u32at(o.base,0);if(count>4096 || no-4>=count || 16u+count*8u>o.bytes)return false;
    const unsigned idx=no-4,at=u32at(o.base,16+idx*4),table=16+count*4;
    if(std::memcmp(o.base+table+idx*4,tag,3) || at<16+count*8 || at>=o.bytes)return false;
    unsigned end=o.bytes;
    // Empty DRS slots have a zero four-byte tag and zero length: their
    // immediate next offset equals their own. Only the contiguous empty run
    // directly before this tagged entry may alias it. Tagged, later and
    // noncontiguous aliases remain ambiguous and are rejected.
    unsigned empty_first=idx;
    while(empty_first && u32at(o.base,16+(empty_first-1)*4)==at &&
          u32at(o.base,table+(empty_first-1)*4)==0) --empty_first;
    // REL begins at header+4. Use the nearest later entry/REL as the span.
    unsigned rel=u32at(o.base,4);if(rel>at && rel<end)end=rel;
    for(unsigned k=0;k<count;++k)if(k!=idx) {
        const unsigned off=u32at(o.base,16+k*4);
        if(off==at && (k<empty_first || k>=idx))return false;
        if(off>at && off<end)end=off;
    }
    begin=o.base+at;size=end-at;return true;
}
bool current(const Asset& a) {
    if(!a.data || a.archive>=kArchives || a.pending)return false;
    const auto& o=archives[a.archive];
    if(!o.key || o.revision!=a.owner_revision || !span(o.base,o.bytes,a.base,a.bytes))return false;
    const auto* d=a.data;
    return d->pHead==a.section[0] && d->pClr==a.section[1] && d->pTex==a.section[2] &&
      d->pWeight==a.section[3] && d->pParts==a.section[4] && d->vtxOrig==a.section[5] && d->nrmOrig==a.section[6];
}
bool tpl_owned(const Archive& o,const void* p,unsigned bytes,const Role& r) {
    if(!span(o.base,o.bytes,p,bytes) || !span(p,bytes,p,12) || u32at(p,4)!=r.texture_count)return false;
    const void* td=ptrat(p,8);
    if(!span(p,bytes,td,r.texture_count*8))return false;
    for(unsigned k=0;k<r.texture_count;++k) {
        const auto* t=static_cast<const unsigned char*>(td)+k*8;const void* h=ptrat(t,0),*c=ptrat(t,4);
        if(!span(p,bytes,h,36))return false;
        const unsigned n=r.textures[k].palette.bytes?64u:32u;
        if(!span(p,bytes,ptrat(h,8),n))return false;
        if(c && (!span(p,bytes,c,12) || !span(p,bytes,ptrat(c,8),r.textures[k].palette.bytes)))return false;
        if(texture(t,r.textures[k])!=Error::None)return false;
    }
    return true;
}
// The row's admitted source family, not its appearance number, identifies
// playable Ashley's TPL owner. Static Leon/head/weapon semantics stay intact.
unsigned tpl_family(const Role& row) {
    if(RE4DC_LEON_LIKE(row.appearance) || RE4DC_HEAD_APP(row.appearance))return 1u;
#if RE4DC_NMR_ASHLEY >= 2 && defined(RE4DC_NMR_PL_ASHLEY) && RE4DC_NMR_PL_ASHLEY
    // The package validator permits family1 only when every referencing role
    // belongs to the complete model0/141-joint/seven-role player descriptor.
    for(unsigned t=0;t<RE4DC_BLOB_COUNT;++t)
        if(RE4DC_BLOB(t).model==row.model && RE4DC_BLOB(t).family==1u)return 1u;
#endif
    return 2u;
}
Info* find_info(const void* p) {for(auto& i:infos_live)if(i.info==p)return &i;return nullptr;}
bool info_current(const Info& i,unsigned role) {
    if(!i.info || i.asset>=kAssets || i.tpl_owner>=kArchives || role>=kRoleMaskBits || !(i.roles[role/32]&(1u<<(role%32))))return false;
    const auto& a=assets[i.asset];const auto& t=archives[i.tpl_owner];
    return current(a) && a.serial==i.asset_serial && t.key && t.revision==i.tpl_revision &&
      span(t.base,t.bytes,i.tpl,i.tpl_bytes) && i.info->pData==a.data && i.info->tpl_addr==i.tpl;
}
} }
#if RE4DC_SS_CERT
#include "actor_swap_park.inc"
#define SS_PARK(stmt) re4dc_material::life::stmt
#else
#define SS_PARK(stmt) ((void)0)
#endif
extern "C" void re4dc_actor_archive_retire(const void* key) {
    RE4DC_SPAN_EPOCH_BUMP(); // ACTOR_SPAN_MEMO31: model data retired / moved / forgotten
    using namespace re4dc_material::life;
    SS_PARK(park_drop_key(key));
    if(!key)return;for(unsigned k=0;k<kArchives;++k)if(archives[k].key==key)revoke(k);
}
extern "C" void re4dc_actor_archive_adopt(const void* key,void* base,unsigned bytes,unsigned family) {
    using namespace re4dc_material;using namespace life;
    // This owner revision was issued by the same successful load boundary and
    // has NOT passed its mandatory unbind-before-overwrite boundary. Duplicate
    // UI adoption preserves that revision after relocation/native conversion.
    // A retired owner cannot enter this branch even at the same address.
    for(const auto& o:archives)if(o.key==key && o.base==base && o.bytes==bytes && o.family==family)return;
    re4dc_actor_archive_retire(key);
    SS_PARK(park_drop_overlap(base,bytes));
    // Overlapping adoption revokes the old owner before any positive proof.
    for(unsigned k=0;k<kArchives;++k)if(archives[k].key && overlap(base,bytes,archives[k].base,archives[k].bytes))revoke(k);
    if(exhausted || !key || !readable(base,bytes) || bytes<16 || family<1 || family>3)return;
    unsigned oi=0;while(oi<kArchives && archives[oi].key)++oi;if(oi==kArchives){CROWD_LIFE(++crowd_archive_full);return;}
    auto& owner=archives[oi];owner={key,static_cast<const unsigned char*>(base),bytes,next(),family};
    for(unsigned t=0;t<RE4DC_BLOB_COUNT;++t) {
        const auto& s=RE4DC_BLOB(t);if(s.family!=family)continue;
        const unsigned char* b=nullptr;unsigned n=0;
        if(!entry(owner,s.bin,"BIN",b,n) || s.normalized.bytes>n || !digest(b,s.normalized))continue;
        Asset* a=nullptr;
        for(auto& x:assets)if(x.data==reinterpret_cast<const ModelData*>(b)){a=&x;break;}
        if(a){a->templates|=BlobMask(1u)<<t;continue;}
        for(auto& x:assets)if(!x.data){a=&x;break;}if(!a)continue;
        *a={};a->data=reinterpret_cast<const ModelData*>(b);a->base=b;a->bytes=s.normalized.bytes;
        a->archive=oi;a->owner_revision=owner.revision;a->serial=next();a->templates=BlobMask(1u)<<t;
        const unsigned fields[7]={0,12,16,20,28,48,52};bool okay=true;
        for(unsigned j=0;j<7;++j) {
            const unsigned off=u32at(b,fields[j]);
            if(off>=a->bytes){okay=false;break;}a->section[j]=b+off;
        }
        if(!okay)*a={};
    }
    // Unrelated animals/actors must not consume all eight reviewed owner slots.
    // They retain their source preparation/rendering and acquire no proof.
    bool supported=false;for(const auto& a:assets)if(a.data && a.archive==oi)supported=true;
    if(!supported){owner={};CROWD_LIFE(++crowd_archive_unsupported);}
    changed();
}
extern "C" void re4dc_actor_archive_retire_transient() {
    RE4DC_SPAN_EPOCH_BUMP(); // ACTOR_SPAN_MEMO31: model data retired / moved / forgotten
    using namespace re4dc_material::life;
    SS_PARK(park_drop_family(2));
    for(unsigned k=0;k<kArchives;++k)if(archives[k].key && archives[k].family==2)revoke(k);
}
#if RE4DC_ACTOR_TRANSACTION_DIAG
void atd_drop(const char*,const re4dc_material::life::Info&,const void*,unsigned,const void*);
#endif
extern "C" void re4dc_actor_info_retire(const void* p) {
    RE4DC_SPAN_EPOCH_BUMP(); // ACTOR_SPAN_MEMO31: model data retired / moved / forgotten
    using namespace re4dc_material::life;
    SS_PARK(park_info_retire(p));
    if(auto* i=find_info(p)){
#if RE4DC_ACTOR_TRANSACTION_DIAG
        atd_drop("info_retire",*i,static_cast<const cModelInfo*>(p)->pData,0,__builtin_return_address(0));
#endif
        *i={};changed();
    }
}
#if RE4DC_CROWD_CENSUS
// Lane crowd census (diagnostic): why infos stay unadopted (every owner-path plan of their actor then fails at
// find_info and the actor draws through the source path). adopt_fail: [0] no asset, [1] asset not current, [2] no
// role / TPL row, [3] no free info slot; revokes: archives revoked (their infos dropped until setTplAddr runs again).
extern "C" void re4dc_crowd_life_report(unsigned frame) {
    using namespace re4dc_material::life;
    unsigned ar=0,as=0,in=0;
    for(const auto& a:archives)ar+=a.key!=nullptr;
    for(const auto& a:assets)as+=a.data!=nullptr;
    for(const auto& i:infos_live)in+=i.info!=nullptr;
    re4dc_log("CROWDLIFE f=%u archives=%u/%u assets=%u/%u infos=%u/%u exhausted=%u adopt=%u ok=%u fail=%u/%u/%u/%u archive_full=%u unsupported=%u revokes=%u revoked_infos=%u readopt=%u/%u\n",
        frame,ar,kArchives,as,kAssets,in,kInfos,unsigned(exhausted),crowd_adopt_calls,crowd_adopt_ok,crowd_adopt_fail[0],crowd_adopt_fail[1],
        crowd_adopt_fail[2],crowd_adopt_fail[3],crowd_archive_full,crowd_archive_unsupported,crowd_revokes,crowd_revoked_infos,crowd_readopt_ok,crowd_readopt_fail);
}
#endif
#if defined(RE4DC_NMR_BIN_DIAG) && RE4DC_NMR_BIN_DIAG
extern "C" unsigned re4dc_ui_frame();
extern "C" void re4dc_log(const char*,...);
// NATIVE_MODEL_REGISTRY_BIN_DIAG (lane cast16 2026-10-16; diagnostic): an info that gets no live record names its source
// BIN / TPL as archive entry numbers (the ARC numbers of <em>_set.cpp), so a pool's missing sections can be read off a
// run (NMRBIN f model info bin tpl archive; 96 lines). Called when a registry actor fails on its role rows.
static void bin_diag(const cModelInfo* info,unsigned why) {
    using namespace re4dc_material;using namespace life;
    static unsigned logged;if(logged>=96 || !info)return;++logged;
    unsigned bin=~0u,tpl=~0u,arc=~0u;const auto* d=reinterpret_cast<const unsigned char*>(info->pData);
    for(unsigned k=0;k<kArchives;++k) {
        const auto& o=archives[k];if(!o.key)continue;
        for(unsigned no=4;no<0x400 && (bin==~0u || tpl==~0u);++no) {
            const unsigned char* p=nullptr;unsigned n=0;
            if(bin==~0u && entry(o,no,"BIN",p,n) && d>=p && d<p+n){bin=no;arc=k;}
            if(tpl==~0u && entry(o,no,"TPL",p,n) && p==info->tpl_addr)tpl=no;
        }
    }
    re4dc_log("NMRBIN f=%u model=%02x info=%p bin=%x tpl=%x archive=%u\n",re4dc_ui_frame(),why,info,bin,tpl,arc);
}
// Called by the registry census when a registry actor fails on its role rows: every source info of that model.
extern "C" void re4dc_nmr_bin_name(const cModelInfo* info,unsigned model) {bin_diag(info,model);}
#endif
extern "C" void re4dc_actor_info_adopt(cModelInfo* info) {
    using namespace re4dc_material;using namespace life;
    re4dc_actor_info_retire(info);if(exhausted || !info)return;
    CROWD_LIFE(++crowd_adopt_calls);
    unsigned ai=0;while(ai<kAssets && assets[ai].data!=info->pData)++ai;
    if(ai==kAssets || !current(assets[ai])){CROWD_LIFE(++crowd_adopt_fail[ai==kAssets?0:1]);return;}
    const auto& a=assets[ai];Info found{};
    for(unsigned r=0;r<RE4DC_ROLE_COUNT;++r) {
        const auto& row=RE4DC_ROLE(r);bool match=false;
        for(unsigned t=0;t<RE4DC_BLOB_COUNT;++t)
            if((a.templates&(BlobMask(1u)<<t)) && RE4DC_BLOB(t).model==row.model)match=true;
        if(!match)continue;
        for(unsigned k=0;k<kArchives;++k) {
            // LEON_HEADLESS v2: the flying head's rows (0x10A) name the player archive (family 1) like Leon's.
            const auto& o=archives[k];if(o.family!=tpl_family(row))continue;
            const unsigned char* p=nullptr;unsigned n=0;
            if(!entry(o,row.source_tpl,"TPL",p,n) || p!=info->tpl_addr || !tpl_owned(o,p,n,row))continue;
            // Multiple rows may intentionally share default hand geometry.
            if(found.info && (found.tpl_owner!=k || found.tpl!=p))return;
            found.roles[r/32]|=1u<<(r%32);
#if RE4DC_ACTOR_WIDE_IDENTITY && RE4DC_NMR_POOL && RE4DC_NMR_ROLES5 && RE4DC_ACTOR_GANADO_PS2_STUMP
            found={info,ai,a.serial,{found.roles[0],found.roles[1],found.roles[2],found.roles[3],found.roles[4],found.roles[5]},k,o.revision,
                p,n};
#elif RE4DC_ACTOR_WIDE_IDENTITY && RE4DC_ACTOR_WIDE_BLOBS
            found={info,ai,a.serial,{found.roles[0],found.roles[1],found.roles[2],found.roles[3],found.roles[4]},k,o.revision,p,n};
#elif RE4DC_ACTOR_WIDE_IDENTITY && RE4DC_NMR_POOL
            found={info,ai,a.serial,{found.roles[0],found.roles[1],found.roles[2],found.roles[3]},k,o.revision,p,n};
#elif RE4DC_ACTOR_WIDE_IDENTITY || RE4DC_ACTOR_GANADO_PS2_STUMP
            found={info,ai,a.serial,{found.roles[0],found.roles[1],found.roles[2]},k,o.revision,p,n};
#else
            found={info,ai,a.serial,{found.roles[0],found.roles[1]},k,o.revision,p,n};
#endif
        }
    }
    if(!found.info){CROWD_LIFE(++crowd_adopt_fail[2]);return;}
    for(auto& slot:infos_live)if(!slot.info){slot=found;changed();CROWD_LIFE(++crowd_adopt_ok);return;}
    CROWD_LIFE(++crowd_adopt_fail[3]);
}
#if RE4DC_ACTOR_TRANSACTION_DIAG
extern "C" unsigned re4dc_ui_frame();
extern "C" void re4dc_log(const char*,...);
// WP2 census (diagnostic): why an info has no live record, as the first re4dc_actor_info_adopt clause that fails
// now (1 exhausted, 2 no recorded asset for pData, 3 asset not current, 4 no row for the asset's templates,
// 5 no archive TPL entry equal to tpl_addr, 6 TPL entry not owned, 7 ambiguous owner, 0 would adopt now).
// One line per info / pData / tpl / reason.
extern "C" void re4dc_actor_txdiag_info(const cModel* m,const cModelInfo* info,unsigned index) {
    using namespace re4dc_material;using namespace life;
    unsigned code=0,detail=0;
    unsigned ai=0;while(ai<kAssets && assets[ai].data!=info->pData)++ai;
    if(exhausted)code=1;
    else if(ai==kAssets) {
        // detail = family<<12 | BIN entry number of pData in a live archive (0 = not in one)
        code=2;
        for(unsigned k=0;k<kArchives && !detail;++k) {
            const auto& o=archives[k];if(!o.key || !span(o.base,o.bytes,info->pData,1))continue;
            for(unsigned no=4;no<4+4096 && no-4<u32at(o.base,0);++no) {
                const unsigned char* p=nullptr;unsigned n=0;
                if(entry(o,no,"BIN",p,n) && p==reinterpret_cast<const unsigned char*>(info->pData)){detail=o.family<<12|no;break;}
            }
        }
    }
    else if(!current(assets[ai])){code=3;detail=ai;}
    else {
        const auto& a=assets[ai];bool row=false,tpl=false,owned=false;const unsigned char* first=nullptr;unsigned owner=kArchives;
        detail=unsigned(a.templates); // diagnostic detail retains the low word; proof uses the whole mask
        for(unsigned r=0;r<RE4DC_ROLE_COUNT && !code;++r) {
            bool match=false;
            for(unsigned t=0;t<RE4DC_BLOB_COUNT;++t)
                if((a.templates&(BlobMask(1u)<<t)) && RE4DC_BLOB(t).model==RE4DC_ROLE(r).model)match=true;
            if(!match)continue;row=true;
            for(unsigned k=0;k<kArchives;++k) {
                const auto& o=archives[k];if(o.family!=tpl_family(RE4DC_ROLE(r)))continue;
                const unsigned char* p=nullptr;unsigned n=0;
                if(!entry(o,RE4DC_ROLE(r).source_tpl,"TPL",p,n) || p!=info->tpl_addr)continue;tpl=true;
                if(!tpl_owned(o,p,n,RE4DC_ROLE(r)))continue;
                if(first && (owner!=k || first!=p)){code=7;break;}
                owned=true;first=p;owner=k;
            }
        }
        if(!code)code=!row?4u:!tpl?5u:!owned?6u:0u;
    }
    static struct { const void* info; const void* data; const void* tpl; unsigned code; } seen[32];
    static unsigned nseen;
    for(unsigned k=0;k<nseen;++k)if(seen[k].info==info && seen[k].data==info->pData && seen[k].tpl==info->tpl_addr && seen[k].code==code)return;
    if(nseen<32)seen[nseen++]={info,info->pData,info->tpl_addr,code};
    re4dc_log("ATX_INFO f=%u m=%p id=%02x idx=%u info=%p data=%p tpl=%p why=%u detail=%x\n",re4dc_ui_frame(),m,
              m?unsigned(m->id):0u,index,info,info->pData,info->tpl_addr,code,detail);
}
// Who dropped a live Leon record (appearance 256 rows; bounded): info_retire's caller or a forget_range span.
unsigned atd_drops;
void atd_drop(const char* how,const re4dc_material::life::Info& rec,const void* a,unsigned b,const void* ra) {
    using namespace re4dc_material;
    unsigned leon=0;
    for(unsigned r=0;r<RE4DC_ROLE_COUNT;++r)if(RE4DC_ROLE(r).appearance==256 && (rec.roles[r/32]&(1u<<(r%32))))leon|=1u<<RE4DC_ROLE(r).role;
    if(leon && atd_drops++<48)re4dc_log("ATX_DROP f=%u %s info=%p roles=%02x a=%p b=%u ra=%p\n",re4dc_ui_frame(),how,rec.info,leon,a,b,ra);
}
#define ATD_DROP(how,rec,a,b) atd_drop(how,rec,a,b,__builtin_return_address(0))
#else
#define ATD_DROP(how,info,a,b) ((void)0)
#endif
extern "C" void re4dc_actor_forget_range(const void* p,unsigned bytes) {
    RE4DC_SPAN_EPOCH_BUMP(); // ACTOR_SPAN_MEMO31: model data retired / moved / forgotten
    using namespace re4dc_material::life;if(!p || !bytes)return;
    SS_PARK(park_forget(p,bytes));
    for(unsigned k=0;k<kArchives;++k)if(archives[k].key && overlap(p,bytes,archives[k].base,archives[k].bytes))revoke(k);
    bool hit=false;for(auto& i:infos_live)if(i.info && overlap(p,bytes,i.info,sizeof(cModelInfo))){ATD_DROP("forget_range",i,p,bytes);i={};hit=true;}
    for(auto& b:bindings)if(b.model && (overlap(p,bytes,b.model,sizeof(cModel)) || span(p,bytes,b.parts,1))){b={};hit=true;}
    if(hit)changed();
}
extern "C" void re4dc_actor_forget_all() {
    RE4DC_SPAN_EPOCH_BUMP(); // ACTOR_SPAN_MEMO31: model data retired / moved / forgotten
    using namespace re4dc_material::life;
    SS_PARK(park_drop_all());
    for(unsigned k=0;k<kArchives;++k)if(archives[k].key)revoke(k);
    for(auto& i:infos_live)i={};for(auto& b:bindings)b={};changed();
}
#if RE4DC_NATIVE_MODEL_REGISTRY_PACK
// NATIVE_MODEL_REGISTRY_PACK (coarse_actor_registry_pack.inc): one room generation's identity rows. Publishing changes
// what an adoption can prove, so the epoch moves (every binding revision is derived again). Retiring removes the
// room rows' bits from every live record (a record left with none is dropped, as a revoked owner's records are) and
// moves the epoch; afterwards no live record names a room row. The counts of dropped records are returned.
namespace re4dc_material { namespace life {
void room_rows_publish(const Role* r,unsigned nr,const SourceBlob* b,unsigned nb,unsigned generation) {
    room_rows={r,b,nr,nb,generation};changed();
}
void room_rows_retire(unsigned& infos,unsigned& assets_dropped) {
    infos=assets_dropped=0;
    if(!room_rows.role_count && !room_rows.blob_count){room_rows={};return;}
    unsigned rmask[kRoleMaskWords]={};BlobMask tmask=0;
    for(unsigned r=kBaseRoles;r<kBaseRoles+room_rows.role_count;++r)rmask[r/32]|=1u<<(r%32);
    for(unsigned t=kBaseBlobs;t<kBaseBlobs+room_rows.blob_count;++t)tmask|=BlobMask(1u)<<t;
#if RE4DC_ACTOR_WIDE_IDENTITY
    for(auto& i:infos_live)if(i.info) {
        unsigned hit=0,live=0;
        for(unsigned w=0;w<kRoleMaskWords;++w){hit|=i.roles[w]&rmask[w];i.roles[w]&=~rmask[w];live|=i.roles[w];}
        if(hit && !live){i={};++infos;}
    }
#else
    for(auto& i:infos_live)if(i.info && ((i.roles[0]&rmask[0]) || (i.roles[1]&rmask[1]))) {
        i.roles[0]&=~rmask[0];i.roles[1]&=~rmask[1];
        if(!i.roles[0] && !i.roles[1]){i={};++infos;}
    }
#endif
    for(auto& a:assets)if(a.data && (a.templates&tmask)){a.templates&=~tmask;if(!a.templates){a={};++assets_dropped;}}
    room_rows={};changed();
}
// Live records naming a room row (0 after a retire).
unsigned room_rows_users() {
    unsigned n=0;
    for(const auto& i:infos_live)if(i.info)for(unsigned r=kBaseRoles;r<kRoleMaskBits;++r)if(i.roles[r/32]&(1u<<(r%32))){++n;break;}
    for(const auto& a:assets)if(a.data && (a.templates>>kBaseBlobs))++n;
    return n;
}
unsigned live_family(unsigned family) {
    unsigned n=0;for(const auto& o:archives)n+=o.key && o.family==family;return n;
}
} }
#endif
extern "C" void re4dc_actor_data_move(const void* p) {
    RE4DC_SPAN_EPOCH_BUMP(); // ACTOR_SPAN_MEMO31: model data retired / moved / forgotten
    using namespace re4dc_material::life;
    SS_PARK(park_forget(p,1));
    for(unsigned k=0;k<kArchives;++k)if(archives[k].key && span(archives[k].base,archives[k].bytes,p,1))revoke(k);
}
extern "C" void re4dc_actor_model_retire(cModel* m) {
    // No span epoch here: this releases one instance's binding slot (also every model_changed, ~2 a frame), not model
    // data; the memos key on the info, stream and arrays, and the owner check stays per draw.
    using namespace re4dc_material::life;
#if RE4DC_NATIVE_MODEL_REGISTRY_CENSUS
    registry_note_retire(m,"retire");
#endif
    // Also called on destruction: release the slot rather than accumulating
    // dead model addresses. A later binding receives a fresh monotonic token.
    for(auto& b:bindings)if(b.model==m){b={};return;}
}
extern "C" void re4dc_actor_model_changed(cModel* m) { re4dc_actor_model_retire(m); }
extern "C" unsigned re4dc_actor_binding_revision(cModel* m) {
    using namespace re4dc_material::life;
    if(!m || exhausted)return 0;
    Binding* free=nullptr;
    for(auto& b:bindings) {
        if(!b.model && !free)free=&b;
        if(b.model!=m)continue;
        if(b.serial!=m->serial || b.parts!=m->pParts || b.epoch!=epoch){b={m,m->pParts,m->serial,next(),epoch};}
        return b.revision;
    }
    if(!free)return 0;*free={m,m->pParts,m->serial,next(),epoch};return free->revision;
}
#if RE4DC_ACTOR_BIND_REUSE
// ACTOR_BIND_REUSE (crowd.mk): re4dc_actor_binding_revision without its refresh: the model's live binding revision
// when that binding is current (the value the full call would return without calling next()), else 0. A binding
// cleared by re4dc_actor_model_retire (no epoch move) reads 0.
extern "C" unsigned re4dc_actor_binding_peek(cModel* m) {
    using namespace re4dc_material::life;
    if(!m || exhausted)return 0;
    for(const auto& b:bindings)if(b.model==m)return b.serial==m->serial && b.parts==m->pParts && b.epoch==epoch?b.revision:0u;
    return 0;
}
#endif
#if RE4DC_NATIVE_MODEL_REGISTRY_TX
// NATIVE_MODEL_REGISTRY_TX: row r can match an info only when info_current(i,r), whose first clause is the info's role
// bit r; so a registry appearance's role scans visit just the info's set bits below the row count, in ascending order
// as the full scans do. Leon and the Ganado cast keep the full scans. =2 runs both and counts different results.
static unsigned registry_role_next(const re4dc_material::life::Info& i,unsigned r) {
    const unsigned n=RE4DC_ROLE_COUNT;
    for(;r<n && r<re4dc_material::kRoleMaskBits;r=(r|31u)+1u) {
        const unsigned bits=i.roles[r>>5]>>(r&31u);
        if(bits){r+=__builtin_ctz(bits);return r<n?r:n;}
    }
    return n;
}
#endif
#if RE4DC_ACTOR_PLAN
#include "actor_plan.h"
// ACTOR_PLAN (actorplan.mk): actor_current_role's answer for (model, info, appearance, role) is kept while the lifetime
// serial stands. Every write to the lifetime tables (archives, assets, infos_live, bindings, room rows, the swap park)
// takes next() (adopt / retire / revoke / forget / room rows / park: changed(); stream pending: a.pending=next(); a
// pending clear only follows a set), so with the serial unchanged find_info returns the same record and only the live
// clauses can differ: the info's membership in m's list (game state) and info_current's per-info clauses (the asset's
// section pointers, info->pData, info->tpl_addr). Those are read again on every reuse; info_current(record, the found
// row) true means every per-info clause holds, so each row's info_current is what it was and the unique-row scan
// returns the same row. Only found rows are kept (a miss runs the scan).
namespace re4dc_material { namespace life {
struct RowMemo { cModel* m;cModelInfo* info;unsigned app,role,serial;unsigned short slot,row; };
constexpr unsigned kRowMemos=24;
RE4DC_PLAN_ARRAY(RowMemo,row_memo,kRowMemos,kRe4dcPlanRowOff);unsigned row_memo_next;
} }
static const re4dc_material::Role* actor_current_role_full(cModel*,cModelInfo*,unsigned,unsigned);
static const re4dc_material::Role* actor_current_role(cModel* m,cModelInfo* info,unsigned app,unsigned role) {
    using namespace re4dc_material;using namespace life;
    if(RE4DC_PLAN_ON && m && !exhausted) {
        for(const auto& e:row_memo) {
            if(e.info!=info || e.m!=m || e.app!=app || e.role!=role || e.serial!=serial)continue;
            unsigned n=0;bool member=false;
            for(auto* p=m->pModelInfo;p && n<kRe4dcActorRoles+1;p=p->pList,++n)if(p==info)member=true;
            const bool hit=member && n<=kRe4dcActorRoles && infos_live[e.slot].info==info && info_current(infos_live[e.slot],e.row);
#if RE4DC_ACTOR_PLAN == 2
            const Role* full=actor_current_role_full(m,info,app,role);
            re4dc_actor_plan_note(APLAN_ROW,hit,hit && full!=&RE4DC_ROLE(e.row));
            return full;
#else
            re4dc_actor_plan_note(APLAN_ROW,hit,0);
            if(hit)return &RE4DC_ROLE(e.row);
            break;
#endif
        }
    }
    const Role* found=actor_current_role_full(m,info,app,role);
    if(found && RE4DC_PLAN_ON && m && !exhausted) {
        const Info* i=find_info(info);unsigned r=0;
        while(r<RE4DC_ROLE_COUNT && &RE4DC_ROLE(r)!=found)++r;
        if(i && r<RE4DC_ROLE_COUNT && r<=0xffffu)
            row_memo[row_memo_next++%kRowMemos]={m,info,app,role,serial,(unsigned short)(i-infos_live),(unsigned short)r};
    }
    return found;
}
#define actor_current_role actor_current_role_full
#endif
// Returns the unique currently-owned material row, never a pointer-only match.
// Multiple rows can share geometry but must resolve one exact TPL owner.
static const re4dc_material::Role* actor_current_role(cModel* m,cModelInfo* info,unsigned app,unsigned role) {
    using namespace re4dc_material;using namespace life;
    if(!m || exhausted)return nullptr;
    unsigned n=0;bool member=false;
    for(auto* p=m->pModelInfo;p && n<kRe4dcActorRoles+1;p=p->pList,++n)if(p==info)member=true;
    if(!member || n>kRe4dcActorRoles)return nullptr;
    auto* i=find_info(info);if(!i)return nullptr;
    const Role* found=nullptr;
#if RE4DC_NATIVE_MODEL_REGISTRY_TX
    if(app>=nmr::appearance_first) {
        bool ambiguous=false;
        for(unsigned r=registry_role_next(*i,0);r<RE4DC_ROLE_COUNT;r=registry_role_next(*i,r+1))
            if(RE4DC_ROLE(r).appearance==app && RE4DC_ROLE(r).role==role && info_current(*i,r)) {
                if(found){ambiguous=true;break;}found=&RE4DC_ROLE(r);
            }
        if(ambiguous)found=nullptr;
#if RE4DC_NATIVE_MODEL_REGISTRY_TX == 2
        const Role* full=nullptr;
        for(unsigned r=0;r<RE4DC_ROLE_COUNT;++r)
            if(RE4DC_ROLE(r).appearance==app && RE4DC_ROLE(r).role==role && info_current(*i,r)) {
                if(full){full=nullptr;break;}full=&RE4DC_ROLE(r);
            }
        ++registry_txc.roles;if(full!=found)++registry_txc.roles_bad;
        found=full;
#endif
        return found;
    }
#endif
    for(unsigned r=0;r<RE4DC_ROLE_COUNT;++r)
        if(RE4DC_ROLE(r).appearance==app && RE4DC_ROLE(r).role==role && info_current(*i,r)) {
            if(found)return nullptr;found=&RE4DC_ROLE(r);
        }
    return found;
}
#if RE4DC_ACTOR_PLAN
#undef actor_current_role
#endif
extern "C" unsigned re4dc_actor_role_source_bin(cModel* m,cModelInfo* info,unsigned app,unsigned role) {
    const auto* r=actor_current_role(m,info,app,role);return r?r->source_bin:0;
}
extern "C" int re4dc_actor_material_owner_proof(cModel* m,cModelInfo* info,unsigned appearance,unsigned role,unsigned revision) {
    using namespace re4dc_material;using namespace life;
    if(!m || exhausted || revision!=RE4DC_ACTOR_MATERIAL_RECORD_REVISION)return 0;
    unsigned n=0;bool member=false;
    for(auto* p=m->pModelInfo;p && n<kRe4dcActorRoles+1;p=p->pList,++n)if(p==info)member=true;
    if(!member || n>kRe4dcActorRoles)return 0;
    auto* i=find_info(info);if(!i)return 0;
#if RE4DC_NATIVE_MODEL_REGISTRY_TX
    if(appearance>=nmr::appearance_first) {
        int found=0;
        for(unsigned r=registry_role_next(*i,0);r<RE4DC_ROLE_COUNT && !found;r=registry_role_next(*i,r+1))
            found=RE4DC_ROLE(r).appearance==appearance && RE4DC_ROLE(r).role==role && info_current(*i,r);
#if RE4DC_NATIVE_MODEL_REGISTRY_TX == 2
        int full=0;
        for(unsigned r=0;r<RE4DC_ROLE_COUNT && !full;++r)
            full=RE4DC_ROLE(r).appearance==appearance && RE4DC_ROLE(r).role==role && info_current(*i,r);
        ++registry_txc.roles;if(full!=found)++registry_txc.roles_bad;
        found=full;
#endif
        return found;
    }
#endif
    for(unsigned r=0;r<RE4DC_ROLE_COUNT;++r)
        if(RE4DC_ROLE(r).appearance==appearance && RE4DC_ROLE(r).role==role && info_current(*i,r))return 1;
    return 0;
}
#if RE4DC_CROWD_READOPT && RE4DC_CROWD_READOPT_MEMO
// CROWD_READOPT_MEMO (crowd.mk; render only, exact): a CROWD_READOPT proof that failed with its asset current (so at
// the row / TPL owner stage, or with no free info slot) is remembered and not run again while nothing it read can
// have changed. Every table it reads (archives, assets and their templates, live infos and free slots, the identity
// rows) moves the epoch when it changes. What no epoch move covers is part of the memory and checked each time: the
// info, its pData and tpl_addr, the TPL's descriptor word (calcTplAddr relocates in place without a notification) and
// the asset's current() (pending conversions, section pointers relocated by calcModelAddr). The sub screen park keeps
// the full proof (its info retire drops parked records). A failed proof has no side effect outside the park, so a
// remembered failure is the same outcome as the proof (the r100 s03 corpse re-proved it every drawn tick: ~0.76 ms).
namespace re4dc_material { namespace life {
struct AdoptMiss { const void* info;const void* data;const void* tpl;unsigned tpl_word,epoch; };
AdoptMiss adopt_miss[4]{};unsigned adopt_miss_next;
// note=false: 1 when p's proof is remembered as failed under the current key; note=true: remember it (returns 0).
bool adopt_memo(const cModelInfo* p,bool note) {
#if RE4DC_SS_CERT
    if(park.open)return false;
#endif
    unsigned ai=0;while(ai<kAssets && assets[ai].data!=p->pData)++ai;   // re4dc_actor_info_adopt's asset lookup
    if(exhausted || ai==kAssets || !current(assets[ai]))return false;
    unsigned word=0;
    for(const auto& o:archives)if(o.key && span(o.base,o.bytes,p->tpl_addr,12)){word=u32at(p->tpl_addr,8);break;}
    const AdoptMiss key{p,p->pData,p->tpl_addr,word,epoch};
    if(note){adopt_miss[adopt_miss_next++&3]=key;return false;}
    for(const auto& k:adopt_miss)
        if(k.info==key.info && k.data==key.data && k.tpl==key.tpl && k.tpl_word==key.tpl_word && k.epoch==key.epoch)return true;
    return false;
}
} }
#endif
#if RE4DC_ACTOR_PLAN
// ACTOR_PLAN: a successful re4dc_actor_role_bindings result for (model, appearance, count) is kept while the lifetime
// serial stands (see RowMemo: the tables are unchanged). A reuse walks the model's info list again (the same infos in
// the same order), and per info checks what the scan read live: the player's hand role (LEON_HAND_POSES: pPL's
// pRight / pLeft) and, for every other info, its record still names it with info_current(record, a row it matched)
// true, so every row's info_current is unchanged and the role scan gives the same unique role. Hand infos never needed
// a record. Failures are not kept; nothing else is skipped.
namespace re4dc_material { namespace life {
constexpr unsigned kRoleMemoInfos=kRe4dcActorRoles,kRoleMemos=12;
struct RoleMemo {
    cModel* m;unsigned appearance,count,serial;
    cModelInfo* chain[kRoleMemoInfos];cModelInfo* out[kRoleMemoInfos];
    unsigned short slot[kRoleMemoInfos],row[kRoleMemoInfos];unsigned char hand[kRoleMemoInfos];
};
RE4DC_PLAN_ARRAY(RoleMemo,role_memo,kRoleMemos,kRe4dcPlanRoleOff);unsigned role_memo_next;
} }
static int role_bindings_full(cModel* m,unsigned appearance,cModelInfo** out,unsigned count);
extern "C" int re4dc_actor_role_bindings(cModel* m,unsigned appearance,cModelInfo** out,unsigned count) {
    using namespace re4dc_material;using namespace life;
    if(RE4DC_PLAN_ON && m && out && !exhausted && count<=kRoleMemoInfos) {
        for(const auto& e:role_memo) {
            if(e.m!=m || e.appearance!=appearance || e.count!=count || e.serial!=serial)continue;
            unsigned n=0;bool hit=true;
            for(auto* p=m->pModelInfo;p && hit;p=p->pList,++n) {
                if(n==count || p!=e.chain[n]){hit=false;break;}
#if RE4DC_LEON_HAND_POSES
                const unsigned hand=re4dc_leon_hand_role(m,p);
                if(hand!=e.hand[n]){hit=false;break;}
                if(hand)continue;
#endif
                hit=infos_live[e.slot[n]].info==p && info_current(infos_live[e.slot[n]],e.row[n]);
            }
            hit=hit && n==count;
#if RE4DC_ACTOR_PLAN == 2
            cModelInfo* full_out[kRoleMemoInfos]{};
            const int full=role_bindings_full(m,appearance,full_out,count);
            bool same=full!=0;for(unsigned k=0;k<count && same;++k)same=full_out[k]==e.out[k];
            re4dc_actor_plan_note(APLAN_ROLES,hit,hit && !same);
            for(unsigned k=0;k<count;++k)out[k]=full_out[k];
            return full;
#else
            re4dc_actor_plan_note(APLAN_ROLES,hit,0);
            if(hit){for(unsigned k=0;k<count;++k)out[k]=e.out[k];return 1;}
            break;
#endif
        }
    }
    const int ok=role_bindings_full(m,appearance,out,count);
    if(ok && RE4DC_PLAN_ON && !exhausted && count<=kRoleMemoInfos) {
        RoleMemo e{};e.m=m;e.appearance=appearance;e.count=count;e.serial=serial;
        unsigned n=0;bool keep=true;
        for(auto* p=m->pModelInfo;p && keep;p=p->pList,++n) {
            if(n==count){keep=false;break;}
            e.chain[n]=p;
#if RE4DC_CROWD_READOPT
            // An info the full proof would try to adopt again (no record, readopt applies) is never replayed: the
            // adoption could succeed later without a serial change having been seen here.
            if(!find_info(p) && (RE4DC_CROWD_READOPT==2 || appearance!=256)){keep=false;break;}
#endif
#if RE4DC_LEON_HAND_POSES
            e.hand[n]=(unsigned char)re4dc_leon_hand_role(m,p);
            if(e.hand[n])continue;
#endif
            const Info* i=find_info(p);
            unsigned r=0;
            if(i)while(r<RE4DC_ROLE_COUNT && !(RE4DC_ROLE(r).appearance==appearance && info_current(*i,r)))++r;
            if(!i || r>=RE4DC_ROLE_COUNT || r>0xffffu){keep=false;break;}
            e.slot[n]=(unsigned short)(i-infos_live);e.row[n]=(unsigned short)r;
        }
        if(keep && n==count) {
            for(unsigned k=0;k<count;++k)e.out[k]=out[k];
            role_memo[role_memo_next++%kRoleMemos]=e;
        }
    }
    return ok;
}
static int role_bindings_full(cModel* m,unsigned appearance,cModelInfo** out,unsigned count) {
#else
extern "C" int re4dc_actor_role_bindings(cModel* m,unsigned appearance,cModelInfo** out,unsigned count) {
#endif
    using namespace re4dc_material;using namespace life;
#if RE4DC_NATIVE_MODEL_REGISTRY
    // A registry appearance has exactly its descriptor's sections, in source info order.
    const unsigned registry_sections=re4dc_registry_sections(appearance);
    if(!m || !out || (registry_sections?count!=registry_sections:
       (appearance==256?count!=8u:(RE4DC_ACTOR_PL08 && appearance==264)?count!=9u:(RE4DC_LEON_HEADLESS && appearance==265)?count!=7u:(RE4DC_LEON_HEADLESS && appearance==266)?count!=1u:(count<4u || count>5u || (appearance==0 && count!=4u)))) || exhausted){ATD(m,30,appearance,exhausted);return 0;}
#else
    if(!m || !out || (appearance==256?count!=8u:(RE4DC_ACTOR_PL08 && appearance==264)?count!=9u:(RE4DC_LEON_HEADLESS && appearance==265)?count!=7u:(RE4DC_LEON_HEADLESS && appearance==266)?count!=1u:(count<4u || count>5u || (appearance==0 && count!=4u))) || exhausted){ATD(m,30,appearance,exhausted);return 0;}
#endif
    unsigned seen=0,n=0;for(unsigned k=0;k<count;++k)out[k]=nullptr;
#if RE4DC_ACTOR_PL08
    static const unsigned char pl08_order[9]={0,1,2,3,4,7,8,5,6};
#endif
    static const unsigned char leon_order[8]={0,1,2,3,4,7,5,6};
    for(auto* p=m->pModelInfo;p;p=p->pList) {
        if(n++==count){ATD(m,21,appearance,n);return 0;}auto* i=find_info(p);
#if RE4DC_CROWD_READOPT
        // Lane crowd (CROWD_READOPT=1): an info with no live record (dropped by a heap free / forget_range, or
        // set up before its archive was adopted) is proved again here with the load-time proof
        // (re4dc_actor_info_adopt: current asset sections, the reviewed TPL owner and row). Nothing is assumed:
        // an info that fails the proof stays unadopted and its actor keeps the source path.
        // =1: Ganados only (Leon keeps whichever path he has today); =2: Ganados and Leon (appearance 256).
#if RE4DC_CROWD_READOPT_MEMO
        if(!i && (RE4DC_CROWD_READOPT==2 || appearance!=256)) {
            if(!adopt_memo(p,false)){re4dc_actor_info_adopt(p);i=find_info(p);if(!i)adopt_memo(p,true);}
            CROWD_LIFE(++(i?crowd_readopt_ok:crowd_readopt_fail));
        }
#else
        if(!i && (RE4DC_CROWD_READOPT==2 || appearance!=256)){re4dc_actor_info_adopt(p);i=find_info(p);CROWD_LIFE(++(i?crowd_readopt_ok:crowd_readopt_fail));}
#endif
#endif
#if RE4DC_LEON_HAND_POSES
        // LEON_HAND_POSES (crowd.mk): the player's current right / left hand infos (cPlBody pRight / pLeft) are roles
        // 5 / 6 whatever pose data they show (weapon grips, the empty hand, the boat hand); the plan draws the PS2
        // hand for that pose (re4dc_leon_hand_chunk). Every other info still needs its exact record.
        if(unsigned hand=re4dc_leon_hand_role(m,p)) {
#if RE4DC_LEON_HEADLESS
            if(appearance==265)--hand;  // LEON_HEADLESS: 0x109's compact roles 4 / 5 are the right / left hands
#endif
            if(hand>=count || (seen&(1u<<hand))){ATD(m,23,appearance,(n-1)*256+hand);return 0;}
            out[hand]=p;seen|=1u<<hand;continue;
        }
#endif
#if RE4DC_ACTOR_TRANSACTION_DIAG
        if(!i)re4dc_actor_txdiag_info(m,p,n-1);
#endif
        if(!i){ATD(m,22,appearance,n-1);return 0;}
        unsigned role=count;
#if RE4DC_NATIVE_MODEL_REGISTRY_TX
        if(appearance>=nmr::appearance_first) {
            bool conflict=false;
            for(unsigned r=registry_role_next(*i,0);r<RE4DC_ROLE_COUNT;r=registry_role_next(*i,r+1))
                if(RE4DC_ROLE(r).appearance==appearance && info_current(*i,r)) {
                    if(role!=count && role!=RE4DC_ROLE(r).role){conflict=true;break;}role=RE4DC_ROLE(r).role;
                }
#if RE4DC_NATIVE_MODEL_REGISTRY_TX == 2
            unsigned full=count;bool full_conflict=false;
            for(unsigned r=0;r<RE4DC_ROLE_COUNT;++r)
                if(RE4DC_ROLE(r).appearance==appearance && info_current(*i,r)) {
                    if(full!=count && full!=RE4DC_ROLE(r).role){full_conflict=true;break;}full=RE4DC_ROLE(r).role;
                }
            ++registry_txc.roles;if(full!=role || full_conflict!=conflict)++registry_txc.roles_bad;
            role=full;conflict=full_conflict;
#endif
            if(conflict){ATD(m,24,appearance,n-1);return 0;}
        } else
#endif
        for(unsigned r=0;r<RE4DC_ROLE_COUNT;++r)
            if(RE4DC_ROLE(r).appearance==appearance && info_current(*i,r)) {if(role!=count && role!=RE4DC_ROLE(r).role){ATD(m,24,appearance,n-1);return 0;}role=RE4DC_ROLE(r).role;}
#if RE4DC_ACTOR_PL08
        const unsigned expected=appearance==256?leon_order[n-1]:appearance==264?pl08_order[n-1]:n-1;
#else
        const unsigned expected=appearance==256?leon_order[n-1]:n-1;
#endif
#if RE4DC_LEON_HAND_POSES
        // LEON_HAND_POSES: Leon's roles may appear in any source order (a hand swap re-appends its info at the end).
        const bool order_ok=(appearance==256 || appearance==264 || (RE4DC_LEON_HEADLESS && appearance==265)) || role==expected;
#else
        const bool order_ok=role==expected;
#endif
        if(role>=count || !order_ok || (seen&(1u<<role))){
#if RE4DC_ACTOR_TRANSACTION_DIAG
            static unsigned i26_logs;
            if(appearance==264 && i26_logs++<12){
                re4dc_log("I26 bind23 f=%u pos=%u role=%u expected=%u seen=%x info=%p data=%p\n",re4dc_ui_frame(),n-1,role,expected,seen,p,p->pData);
                unsigned k=0;for(auto* q=m->pModelInfo;q;q=q->pList,++k){auto* qi=find_info(q);unsigned rr=99;
                    if(qi)for(unsigned r=0;r<RE4DC_ROLE_COUNT;++r)if(RE4DC_ROLE(r).appearance==appearance && info_current(*qi,r)){rr=RE4DC_ROLE(r).role;break;}
                    re4dc_log("I26  list %u info=%p data=%p rec=%u role=%u\n",k,q,q->pData,unsigned(qi!=nullptr),rr);}
            }
#endif
            ATD(m,23,appearance,(n-1)*256+role);return 0;}
        out[role]=p;seen|=1u<<role;
    }
    if(n!=count || seen!=((1u<<count)-1)){ATD(m,25,n,seen);return 0;}return 1;
}
#if RE4DC_NMR_POOL
// NATIVE_MODEL_REGISTRY_POOL (native_model_registry.mk): a pool descriptor's sections are a pool of source BIN + TPL
// identities (one role row each: the body, heads, every hand pose, every accessory the source can attach). An actor
// binds it when each of its source infos proves exactly one current pool row of the appearance (the same per-info
// proof as re4dc_actor_role_bindings: find_info, the readopt rule, one unique current row), no two infos prove the
// same row, and the first info, and only it, is the body (section 0). out[k] / sec[k] keep source info order.
extern "C" int re4dc_actor_pool_bindings(cModel* m,unsigned appearance,unsigned sections,cModelInfo** out,unsigned char* sec,unsigned count) {
    using namespace re4dc_material;using namespace life;
    if(!m || !out || !sec || !count || count>8u || !sections || sections>64u || exhausted){ATD(m,30,appearance,exhausted);return 0;}
    unsigned seen[2]={0,0},n=0;
    for(unsigned k=0;k<count;++k){out[k]=nullptr;sec[k]=0;}
    for(auto* p=m->pModelInfo;p;p=p->pList) {
        if(n==count){ATD(m,21,appearance,n+1);return 0;}
        auto* i=find_info(p);
#if RE4DC_CROWD_READOPT
#if RE4DC_CROWD_READOPT_MEMO
        if(!i) {
            if(!adopt_memo(p,false)){re4dc_actor_info_adopt(p);i=find_info(p);if(!i)adopt_memo(p,true);}
            CROWD_LIFE(++(i?crowd_readopt_ok:crowd_readopt_fail));
        }
#else
        if(!i){re4dc_actor_info_adopt(p);i=find_info(p);CROWD_LIFE(++(i?crowd_readopt_ok:crowd_readopt_fail));}
#endif
#endif
#if RE4DC_ACTOR_TRANSACTION_DIAG
        if(!i)re4dc_actor_txdiag_info(m,p,n);
#endif
        if(!i){ATD(m,22,appearance,n);return 0;}
        unsigned role=sections;
#if RE4DC_NATIVE_MODEL_REGISTRY_TX
        for(unsigned r=registry_role_next(*i,0);r<RE4DC_ROLE_COUNT;r=registry_role_next(*i,r+1))
#else
        for(unsigned r=0;r<RE4DC_ROLE_COUNT;++r)
#endif
            if(RE4DC_ROLE(r).appearance==appearance && info_current(*i,r)) {
                if(role!=sections && role!=RE4DC_ROLE(r).role){ATD(m,24,appearance,n);return 0;}
                role=RE4DC_ROLE(r).role;
            }
        if(role>=sections || (n==0)!=(role==0) || (seen[role/32]&(1u<<(role%32)))){ATD(m,23,appearance,n*256+role);return 0;}
        seen[role/32]|=1u<<(role%32);out[n]=p;sec[n]=(unsigned char)role;++n;
    }
    if(n!=count){ATD(m,25,n,count);return 0;}
    return 1;
}
#endif
extern "C" unsigned re4dc_actor_stream_begin(const void* p,unsigned bytes) {
    using namespace re4dc_material::life;
    if(!p || !bytes || exhausted)return 0;
    for(unsigned k=0;k<kAssets;++k) {auto& a=assets[k];
        if(!a.data || !overlap(a.base,a.bytes,p,bytes))continue;
        if(!span(a.base,a.bytes,p,bytes) || !current(a)){revoke(a.archive);return 0;}
        // Only a recorded source ModelPart stream may transition to native.
        const auto* part=static_cast<const unsigned char*>(a.section[4]);
        const unsigned count=a.data->displist_num;
        for(unsigned n=0;n<count;++n) {
            if(!span(a.base,a.bytes,part,32))break;unsigned length=re4dc_material::u32at(part,24);
            if(!span(a.base,a.bytes,part+32,length))break;
            if(part+32==p && length==bytes) {
                if(a.pending){revoke(a.archive);return 0;}
                a.pending=next();return a.pending;
            }
            part+=32+length;
        }
        // A mutation in any other certified section invalidates its owner.
        revoke(a.archive);return 0;
    }
    return 0;
}
extern "C" void re4dc_actor_stream_end(unsigned ticket,const void* p,unsigned bytes) {
    using namespace re4dc_material::life;
    if(!ticket)return;
    for(auto& a:assets)if(a.data && a.pending==ticket) {
        if(!span(a.base,a.bytes,p,bytes)){revoke(a.archive);return;}
        a.pending=0;return;
    }
    // Retired during conversion: never resurrect a proof into a newer owner.
}
