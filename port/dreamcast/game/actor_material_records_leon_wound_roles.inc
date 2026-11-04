// LEON_WOUND (lane bosscast-wound, 2026-11-03): appearance 0x10B = the pl08 player after cPlLeon::setWound() (r317
// after the Krauser knife fight; every later chapter 5 room via setModel while Scenario_flg[0] & 0x20). Roles 0..8 are
// 0x108's rows unchanged; role 9 is the wound overlay, player arc 0xE / TPL 0xF (actor_material_records_leon_wound.inc,
// gen_wound_records.py from the original pl08.drs).
{267u,0u,4u,5u,&m_pl08_4,t_pl08_5,9u},  // pl08/4
{267u,1u,10u,5u,&m_pl08_10,t_pl08_5,9u},  // pl08/10
{267u,2u,13u,5u,&m_pl08_13,t_pl08_5,9u},  // pl08/13
{267u,3u,8u,7u,&m_pl00_8,t_pl00_7,5u},  // pl08/8
{267u,4u,6u,7u,&m_pl00_6,t_pl00_7,5u},  // pl08/6
{267u,5u,10u,17u,&m_wep02_10,t_pl00_17,2u},  // wep02/10
{267u,6u,24u,17u,&m_pl00_24,t_pl00_17,2u},  // pl08/24
{267u,7u,9u,7u,&m_pl00_9,t_pl00_7,5u},  // pl08/9
{267u,8u,16u,5u,&m_pl08_16,t_pl08_5,9u},  // pl08/16
{267u,9u,14u,15u,&m_pl08_14,t_pl08_15,2u},  // pl08/14 (the wound; pl00 arc 0xE is byte-identical)
