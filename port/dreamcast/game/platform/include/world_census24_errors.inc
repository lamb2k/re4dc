// Included only inside wc24's private namespace with ERRORS=1. The live
// collection is tentative until finish_tick commits its original aggregate.
// Every abandoned tick also discards the original active window, so direct
// window accumulation needs no per-tick bin clearing, copying or merging.
struct ErrorCounts {
    uint32_t used,spill,wrapped;
    ErrorBin bins[ErrorBinCapacity];
};
ErrorCounts errors_live;
ErrorSnapshot errors_sealed;

void errors_clear(bool clear_snapshot) {
    errors_live.used=errors_live.spill=errors_live.wrapped=0;
    if(clear_snapshot)errors_sealed=ErrorSnapshot{};
}
void errors_record(ErrorReason reason,ErrorSite site,uint32_t a,uint32_t b,uint32_t context=UINT32_MAX) {
    if(unsigned(reason)>=ErrorReasonCount)reason=ErrorUnspecified;
    if(unsigned(site)>=ErrorSiteCount)site=ErrorSiteUnspecified;
    if(context==UINT32_MAX)context=state;
    const uint32_t key=unsigned(reason)|(unsigned(site)<<8)|((context&255u)<<16);
    for(unsigned i=0;i<errors_live.used;++i){
        auto& bin=errors_live.bins[i];
        if(bin.key!=key)continue;
        if(bin.count==UINT32_MAX)errors_live.wrapped=1;
        ++bin.count;return;
    }
    if(errors_live.used==ErrorBinCapacity){
        if(errors_live.spill==UINT32_MAX)errors_live.wrapped=1;
        ++errors_live.spill;return;
    }
    errors_live.bins[errors_live.used++]={key,1,current.tick,a,b};
}
void errors_current(ErrorReason reason,ErrorSite site,uint32_t a=0,uint32_t b=0) {
    ++current.errors;
    errors_record(reason,site,a,b);
}
uint32_t errors_total(const ErrorSnapshot& s) {
    uint32_t sum=s.spill;
    for(unsigned i=0;i<s.used;++i)sum+=s.bins[i].count;
    return sum;
}
void errors_seal() {
    errors_sealed=ErrorSnapshot{};
    auto& s=errors_sealed;
    s.sequence=sealed.sequence;s.room=sealed.identity[0];
    s.first_tick=sealed.first_tick;s.last_tick=sealed.last_tick;s.total=sealed.errors;
    s.used=errors_live.used;s.spill=errors_live.spill;s.wrapped=errors_live.wrapped;
    uint32_t sum=s.spill;
    for(unsigned i=0;i<s.used;++i){
        s.bins[i]=errors_live.bins[i];
        if(s.bins[i].count>UINT32_MAX-sum)s.wrapped=1;
        sum+=s.bins[i].count;
    }
    errors_clear(false);
}
const char* errors_reason(uint32_t key) {
    static const char* const names[ErrorReasonCount]={
        "unspecified","pass-incomplete","pass-abort","binding-lost",
        "movie-suppressed","camera-missing","projection","depth",
        "package-missing","invalid-pass","owner-rejected","entry-rejected",
        "far-invalid","deferred-stale","receipt-incomplete","shell-missing",
        "shell-bind","clock-reversed","scope-unclosed","tick-reversed",
        "phase-overrun","scope-depth","scope-order","counter-saturated","shell-scratch"};
    return names[key&255u];
}
const char* errors_site(uint32_t key) {
    static const char* const names[ErrorSiteCount]={
        "unspecified","ps2-pass","mesh-draw","mesh-camera","mesh-source",
        "source-draw","r11f-draw","world-draw","world-source","world-flush",
        "far-shell","core-charge","core-finish","core-scope","core-count"};
    return names[(key>>8)&255u];
}
const char* errors_path(uint32_t key) {
    static const char* const names[PathCount+1]={"OUT","N-OP","N-PT","N-TR","F-OP","F-PT","F-TR"};
    const unsigned path=(key>>16)&7u;
    return path<=PathCount?names[path]:"INVALID";
}
const char* errors_phase(uint32_t key) {
    static const char* const names[PhaseCount]={"SEL","XFORM","CLIP","HEADER","SUBMIT","OTHER"};
    if(!((key>>16)&7u))return "OUT";
    const unsigned phase=(key>>19)&7u;
    return phase<PhaseCount?names[phase]:"INVALID";
}
__attribute__((noinline)) void errors_log() {
    const auto& s=errors_sealed;char line[240];
    int n=snprintf(line,sizeof(line),"WC24E q=%u room=%03x total=%u bins=%u spill=%u wrap=%u match=%u",
        s.sequence,s.room,s.total,s.used,s.spill,s.wrapped,unsigned(errors_total(s)==s.total));
    if(n<0 || unsigned(n)>=sizeof(line))snprintf(line,sizeof(line),"WC24E q=%u format_overflow=1 full=QA",s.sequence);
    print_line(line);
    for(unsigned i=0;i<s.used;++i){
        const auto& b=s.bins[i];
        n=snprintf(line,sizeof(line),"WC24E q=%u key=%08x r=%s at=%s p=%s ph=%s wait=%u n=%u tick=%u a=%08x b=%08x",
            s.sequence,b.key,errors_reason(b.key),errors_site(b.key),errors_path(b.key),errors_phase(b.key),
            (b.key>>22)&3u,b.count,b.first_tick,b.detail0,b.detail1);
        if(n<0 || unsigned(n)>=sizeof(line))snprintf(line,sizeof(line),"WC24E q=%u bin=%u format_overflow=1 full=QA",s.sequence,i);
        print_line(line);
    }
}
