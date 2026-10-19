// LEON_HEADLESS (lane garr18, 2026-10-19): appearance 0x109 = the pl08 player after setHead(0) (pl_leon.cpp: the head
// shape, hair and eye infos deleted, the neck, player arc 0xB / TPL 7, appended). Seven roles, compact: 0..2 and 6 are
// pl08's roles 0..2 and 8, 3 the neck (actor_material_records_leon_neck.inc), 4 / 5 the right / left hand rows of 0x108.
{265u,0u,4u,5u,&m_pl08_4,t_pl08_5,9u},  // pl08/4
{265u,1u,10u,5u,&m_pl08_10,t_pl08_5,9u},  // pl08/10
{265u,2u,13u,5u,&m_pl08_13,t_pl08_5,9u},  // pl08/13
{265u,3u,11u,7u,&m_pl00_11,t_pl00_7,5u},  // pl00/11 (the neck; pl08's arc 0xB is byte-identical)
{265u,4u,10u,17u,&m_wep02_10,t_pl00_17,2u},  // wep02/10
{265u,5u,24u,17u,&m_pl00_24,t_pl00_17,2u},  // pl08/24
{265u,6u,16u,5u,&m_pl08_16,t_pl08_5,9u},  // pl08/16
