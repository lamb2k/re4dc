#define RE4DC_WORLD_PREPARED09 1
#include "world_portal29.hpp"
#include <cassert>
#include <cstdio>
#include <vector>
int main(){
    using namespace re4dc::portal29;unsigned checks=0,worst=0;
    for(unsigned n=0;n<=kMaxWitnesses;++n){
        std::vector<Witness> rows;for(unsigned i=0;i<n;++i)rows.push_back({i/4U,2U*(i%4U)+1U});
        for(unsigned pl=0;pl<=n/4U+1U;++pl)for(unsigned part=0;part<10U;++part){
            unsigned expected=kMaxWitnesses;
            for(unsigned q=0;q<n;++q)if(rows[q].placement==pl && rows[q].part==part){expected=q;break;}
            unsigned comparisons=0;assert(witness_index(rows.data(),n,pl,part,&comparisons)==expected);++checks;
            if(comparisons>worst)worst=comparisons;
            assert(comparisons<=10U);
        }
    }
    assert(witness_index(nullptr,256,0,0)==kMaxWitnesses);
    Witness row{};assert(witness_index(&row,257,0,0)==kMaxWitnesses);
    assert(worst==10U);std::printf("world prepared09 witness index: %u checks PASS; worst=%u tuple comparisons\n",checks,worst);
}
