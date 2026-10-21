// Transport completion is a boundary. Actual EvtReadSub, command dispatch and
// wait/usable/load checks execute; no Event start or release result is mocked.
static unsigned transport_calls;
static bool transport_refuse;
static bool transport_other_flags;
cDataUnit* Controller::setData(char*){return &loaded;}
void cDataUnit::setLoadToMram(){
    ++transport_calls;
    if(transport_other_flags){global.Status_flg[2]|=0x20;global.System_flg|=0x4000000;}
    if(transport_refuse){m_err=1;return;}
    assert(m_condition==0||m_condition==2||m_condition==4);
    m_addr=m_malloc_addr=arena;m_malloc_heap=4;m_be_flag|=3;
    m_condition=2;m_command=0;m_err=0;
}
