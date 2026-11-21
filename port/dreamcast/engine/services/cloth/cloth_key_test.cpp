// cloth_key_test.cpp (lane eng-cloth1): the cloth service's chain table is keyed by (PenCloth, model).
//
// El Gigante's chained form sets one PenCloth up on two chain objects (em2bChainSet, rope[1]). The test runs the
// service's set-up lookup (cloth.cpp build(): find, and when there is no chain for the key, forget and a new entry) for
// the same PenCloth on two models, then the step lookup (PenClothMove: find) for each: each model must find its own
// chain. Built twice by cloth_key_test.sh: as the service is (must PASS) and with CLOTH_KEY_CONTROL_OLD, the old key
// (the PenCloth alone; must FAIL: the second set-up takes the first chain over and the first model's steps find none).
//   g++ -I<include dirs> cloth_key_test.cpp && ./a.out   (exit 0 PASS, 1 FAIL)
#include "cloth.h"
#include <stdio.h>

static ClothChain blk[4];
static ClothChain* tab[4];
static u32 n;

// cloth.cpp build()'s lookup on the table: the key's chain, or a new entry after forgetting the key
static ClothChain* setup(const PenCloth* c, cModel* m, ClothChain* fresh)
{
    const int i = cloth_key_find(tab, n, c, m);
    ClothChain* ch = i < 0 ? 0 : tab[i];
    if (ch && ch->m != m) ch = 0;   // as cloth.cpp before the fix: a chain of another model is not this one
    if (!ch) {
        cloth_key_forget(tab, n, c, m);
        ch = fresh;
        tab[n++] = ch;
    }
    ch->c = (PenCloth*) c;
    ch->m = m;
    return ch;
}
// PenClothMove's lookup: the chain, or none (the fallback)
static ClothChain* step(const PenCloth* c, cModel* m)
{
    const int i = cloth_key_find(tab, n, c, m);
    return i >= 0 && tab[i]->m == m ? tab[i] : 0;
}

int main()
{
    static char modelA, modelB, cloth0, cloth1;
    cModel* A = (cModel*) &modelA;
    cModel* B = (cModel*) &modelB;
    const PenCloth* rope = (const PenCloth*) &cloth0;
    const PenCloth* other = (const PenCloth*) &cloth1;
    int bad = 0;
    ClothChain* a = setup(rope, A, &blk[0]);
    ClothChain* b = setup(rope, B, &blk[1]);
    ClothChain* o = setup(other, A, &blk[2]);
    ClothChain* a2 = setup(rope, A, &blk[3]);   // set up again: the same chain
    if (step(rope, A) != a) { printf("FAIL: model A's chain on the shared PenCloth not found (taken over)\n"); bad = 1; }
    if (step(rope, B) != b) { printf("FAIL: model B's chain on the shared PenCloth not found\n"); bad = 1; }
    if (step(other, A) != o) { printf("FAIL: model A's other chain not found\n"); bad = 1; }
    if (a2 != a) { printf("FAIL: a second set-up of (PenCloth, model) made a new chain\n"); bad = 1; }
    if (n != 3) { printf("FAIL: %u chains in the table, 3 expected\n", (unsigned) n); bad = 1; }
    // the eviction order: the chain stepped least recently
    blk[0].stamp = 5; blk[1].stamp = 3; blk[2].stamp = 9;
    if (tab[cloth_key_oldest(tab, n)] != &blk[1]) { printf("FAIL: eviction order\n"); bad = 1; }
    blk[0].stamp = 0xFFFFFFF0u; blk[1].stamp = 2; blk[2].stamp = 0xFFFFFFF8u;   // across the counter's wrap
    if (tab[cloth_key_oldest(tab, n)] != &blk[0]) { printf("FAIL: eviction order across the wrap\n"); bad = 1; }
#ifdef CLOTH_KEY_CONTROL_OLD
    printf("control build (the old key, the PenCloth alone): ");
#endif
    printf("%s\n", bad ? "FAIL" : "PASS");
    return bad;
}
