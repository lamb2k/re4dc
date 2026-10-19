// native_ui.cpp, after load() and its existing private namespace.
extern "C" const Re4dcManualPageContext* re4dc_ui_manual_page(unsigned row){
    return row<RE4DC_MANUAL_PAGE_COUNT ? &manual_pages[row].context : nullptr;
}
#if defined(RE4DC_MANUAL_PACK_PROBE) && RE4DC_MANUAL_PACK_PROBE && RE4DC_TEX_PACK
// MANUAL_PACK_PROBE: a packed disc has no loose dc/tex/<n>/ files; the package is in dc/tex.pak (load() reads it there).
static int manual_pack_size(const Key& key){
    unsigned offset=0,size=0;
    return texpack::find(key,offset,size,frame)==texpack::kFound ? int(size) : -1;
}
#define RE4DC_MANUAL_PACK_SIZE(key) manual_pack_size(key)
#else
#define RE4DC_MANUAL_PACK_SIZE(key) (-1)
#endif
extern "C" int re4dc_ui_manual_page_available(unsigned row){
    if(row>=RE4DC_MANUAL_PAGE_COUNT || !manual_pages[row].context.companion_path)return 0;
    const int packed=RE4DC_MANUAL_PACK_SIZE(manual_pages[row].keys[1]);
    if(packed>=0)return packed==RE4DC_MANUAL_PACKAGE_BYTES || packed==RE4DC_MANUAL_VQ_PACKAGE_BYTES;
    // One authority for resident/sharded versus flat package paths.
    char path[96];RE4DC_TEX_PATH(path,manual_pages[row].keys[1]);
    const file_t f=fs_open(path,O_RDONLY);if(f==FILEHND_INVALID)return 0;
    const size_t bytes=fs_total(f);fs_close(f);
    return bytes==RE4DC_MANUAL_PACKAGE_BYTES || bytes==RE4DC_MANUAL_VQ_PACKAGE_BYTES;
}
extern "C" unsigned re4dc_ui_manual_page_identify(unsigned row,const Re4dcUiImage* image){
    if(row>=RE4DC_MANUAL_PAGE_COUNT || !image || !image->pixels ||
       image->width!=640 || image->height!=360 || image->format!=14 ||
       image->palette || image->palette_bytes || image->palette_format!=0xffffffffU)return 0;
    // Only once after a fresh bounded read, before source relocation. A reused
    // pointer is never sufficient and no source pixel hash runs on the draw path.
    const unsigned metadata[]={640,360,14,0xffffffffU,0};
    Key key{0xffffffffU,2166136261U};hash_bytes(key,metadata,sizeof(metadata));
    hash_bytes(key,image->pixels,115200U);key.crc=~key.crc;
    for(unsigned variant=0;variant<(manual_pages[row].context.companion_path ? 2U : 1U);++variant)
        if(key==manual_pages[row].keys[variant])return variant+1;
    return 0;
}
// Generic UI_FRAG_LATCH remembers one key. A failing original/companion pair
// must not alternate around it and reattempt two 1MiB uploads every frame.
// Fifteen identities in sixteen slots: 64B timestamps plus a 4B validity bitmask.
static_assert(RE4DC_MANUAL_PAGE_COUNT*2<=32,"manual failure mask capacity");
static unsigned manual_failed_frame[RE4DC_MANUAL_PAGE_COUNT*2],manual_failed_mask;
static bool manual_page_load(unsigned row,unsigned variant,Re4dcUiImage& image){
    const unsigned index=row*2+variant,bit=1U<<index;
    image=manual_page_image(row,variant);
    if((manual_failed_mask&bit) && unsigned(frame-manual_failed_frame[index])<120U){
        // An independently populated entry may be used and pinned immediately.
        // A miss during the cooldown never reaches file I/O/eviction/upload.
        bool resident=false;
        for(const auto& entry:entries)
            if(entry.valid && entry.key==manual_pages[row].keys[variant]){resident=true;break;}
        if(!resident)return false;
    }
    if(load(image,true)){manual_failed_mask&=~bit;return true;}
    manual_failed_frame[index]=frame;manual_failed_mask|=bit;return false;
}
static unsigned manual_generic_failed_frame;
static bool manual_generic_failed;
extern "C" int re4dc_ui_manual_generic_identify(const Re4dcUiImage* image){
    if(!image || !image->pixels || image->width!=640 || image->height!=360 || image->format!=14 ||
       image->palette || image->palette_bytes || image->palette_format!=0xffffffffU)return 0;
    // Once per fresh bounded read (as re4dc_ui_manual_page_identify), never on the draw path.
    const unsigned metadata[]={640,360,14,0xffffffffU,0};
    Key key{0xffffffffU,2166136261U};hash_bytes(key,metadata,sizeof(metadata));
    hash_bytes(key,image->pixels,115200U);key.crc=~key.crc;
    if(RE4DC_MANUAL_PACK_SIZE(key)<0){
    char path[96];RE4DC_TEX_PATH(path,key);
    const file_t f=fs_open(path,O_RDONLY);if(f==FILEHND_INVALID)return 0;
    fs_close(f);
    }
    if(!(key==manual_generic_key))manual_generic_failed=false;
    manual_generic_key=key;return 1;
}
extern "C" int re4dc_ui_manual_generic_image(Re4dcUiImage* out){
    if(!frame_ready || !out)return 0;
    const Re4dcUiImage image={&manual_generic_key,nullptr,640,360,14,0xffffffffU,0};
    if(manual_generic_failed && unsigned(frame-manual_generic_failed_frame)<120U){
        bool resident=false;
        for(const auto& entry:entries)if(entry.valid && entry.key==manual_generic_key){resident=true;break;}
        if(!resident)return 0;
    }
    Re4dcUiImage loaded=image;
    if(!load(loaded,true)){manual_generic_failed=true;manual_generic_failed_frame=frame;return 0;}
    manual_generic_failed=false;*out=loaded;return 1;
}
extern "C" int re4dc_ui_manual_page_image(unsigned row,unsigned kind,int companion,Re4dcUiImage* out){
    if(!frame_ready || !out || row>=RE4DC_MANUAL_PAGE_COUNT || kind<1 || kind>2)return 0;
    unsigned variant=manual_pages[row].context.companion_path &&
        (row==RE4DC_MANUAL_CAMERA ? companion : kind==2 && companion) ? 1 : 0;
    Re4dcUiImage image;
    // Normal cache validation/upload/pinning remains authoritative. Failed
    // companion CRC or upload can use ONLY this row's exact original package.
    if(!manual_page_load(row,variant,image)){
        if(!variant || row==RE4DC_MANUAL_CAMERA)return 0; // never C-stick art beside D-pad text
        if(!manual_page_load(row,0,image))return 0;
    }
    *out=image;return 1;
}
