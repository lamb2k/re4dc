// Existing native carrier refusal policy is an explicit boundary here; actual
// EvtFree and cDataUnit::setClear refusal propagation execute unchanged.
static bool cabin_clear_refuse;
static unsigned clear_refusals;
static unsigned re4dc_cabin_carrier_reserved(const void*){return cabin_clear_refuse;}
static int re4dc_cabin_carrier_clear(const void*){if(cabin_clear_refuse){++clear_refusals;return 0;}return 1;}
static int re4dc_cabin_carrier_before_free(const void*){return 1;}
static unsigned re4dc_cabin_carrier_reverse_token(const void*,const void*,const void*,unsigned,int*){std::abort();}
static int re4dc_cabin_carrier_reverse_complete(const void*,const void*,const void*,unsigned,int,unsigned){std::abort();}
static int re4dc_cabin_carrier_event(const void*,const void*,const char*){return 1;}
static void re4dc_cabin_carrier_event_deleted(const void*){}
static void re4dc_cabin_event_bound(const void*,const char*){}
static void re4dc_cabin_event_deleted(const void*){}
static void re4dc_missing(const char*){std::abort();}
