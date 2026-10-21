// Tests the owned journal component; this is not loader/movie integration.
#include "../../../game/platform/motion_resume_journal.hpp"
#include <cassert>
#include <cstdint>
#include <iostream>
using namespace re4dc::motion;
int main() {
    ResumeJournal j;j.binding_changed(0);j.binding_changed(1);
    j.acquired(0,1,10);j.acquired(0,2,11);j.acquired(1,254,11);
    assert(j.begin_movie(11));assert(!j.begin_movie(11));
    for(unsigned i:{1u,2u,3u})j.movie_evicted(0,i);j.movie_evicted(1,254);
    auto first=j.finish_movie();assert(first.contains(0,1)&&first.contains(0,2)&&!first.contains(0,3)&&first.contains(1,254));
    assert(j.current(first,0)&&j.current(first,1)); // no preload/unrelated key ticket
    assert(!j.finish_movie().contains(0,1)); // idempotent finish
    j.binding_changed(0);assert(!j.current(first,0)); // same binding/address reused
    j.acquired(0,7,12);assert(j.begin_movie(12));j.movie_evicted(0,7);
    j.binding_changed(0);j.acquired(0,7,12);j.movie_evicted(0,7);
    assert(!j.finish_movie().contains(0,7)); // no old-generation or movie-internal demand
    j.acquired(0,8,20);assert(j.begin_movie(22));j.movie_evicted(0,8);
    assert(!j.finish_movie().contains(0,8)); // stale footprint is not a required set
    j.acquired(0,9,30);assert(j.begin_movie(31));j.movie_evicted(0,9);
    assert(j.finish_movie().contains(0,9)); // immediately preceding source tick
    j.acquired(0,10,40);j.movie_evicted(0,10);assert(!j.finish_movie().contains(0,10)); // no movie owner
    assert(j.begin_movie(40));j.movie_evicted(0,10);j.cancel_movie();assert(!j.finish_movie().contains(0,10));
    j.acquired(0,11,UINT32_MAX);j.acquired(0,12,0);assert(j.begin_movie(0));j.movie_evicted(0,11);j.movie_evicted(0,12);
    auto wrap=j.finish_movie();assert(wrap.contains(0,11)&&wrap.contains(0,12)); // source frame wrap
    j.acquired(0,13,50);assert(j.begin_movie(50));j.movie_evicted(0,13);
    auto forgotten=j.finish_movie();j.key_forgotten(0,13);
    assert(j.restrict_recent(forgotten,50)&&!forgotten.contains(0,13));
    j.acquired(0,14,60);assert(j.begin_movie(60));j.movie_evicted(0,14);
    auto stale=j.finish_movie();assert(j.restrict_recent(stale,62)&&!stale.contains(0,14));
    j.acquired(0,15,70);assert(j.begin_movie(70));j.movie_evicted(0,15);
    auto valid=j.finish_movie();assert(j.restrict_recent(valid,71)&&valid.contains(0,15));
    assert(j.begin_movie(71));assert(!j.restrict_recent(valid,71)&&!valid.contains(0,15));j.cancel_movie();
    j.acquired(4,0,1);j.acquired(0,255,1);j.binding_changed(4);j.movie_evicted(4,0);
    assert(!wrap.contains(4,0)&&!wrap.contains(0,255));
    std::cout<<"motion resume journal PASS metadata="<<sizeof j<<" tickets="<<sizeof wrap<<"\n";
}
