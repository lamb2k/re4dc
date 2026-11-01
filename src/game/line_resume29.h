#ifndef RE4DC_LINE_RESUME29_H
#define RE4DC_LINE_RESUME29_H

// The line walk's source-order continuation. A step is a leaf (1), an untouched
// child chain at the stack limit (2), or the end (0). The caller runs a child
// chain with the existing recursive polygon walk before asking for another step;
// the continuation already points at the block after that child chain.
struct LineResume29 {
    cSatBlock* cur;
    cSatBlock* after[16];
    int depth;
    Vec mid;
    Vec dir;
    Vec adir;
};

static inline void lineResume29BeginBounds(LineResume29* q, cSatBlock* root, const Vec* mid,
                                            const Vec* dir, const Vec* adir)
{
    q->cur = root;
    q->depth = 0;
    q->mid = *mid;
    q->dir = *dir;
    q->adir = *adir;
}

static inline void lineResume29Begin(LineResume29* q, cSatBlock* root, Vec* a, Vec* b)
{
    q->cur = root;
    q->depth = 0;
    PSVECAdd(a, b, &q->mid);
    PSVECScale(&q->mid, &q->mid, 0.5f);
    PSVECSubtract(a, &q->mid, &q->dir);
    q->adir.x = fabsf(q->dir.x);
    q->adir.y = 0.0f;
    q->adir.z = fabsf(q->dir.z);
    q->dir.y = 0.0f;
    q->mid.y = 0.0f;
}

static inline int lineResume29Next(LineResume29* q, cSatBlock** out)
{
    for (;;) {
        cSatBlock* blk = q->cur;
        if (!blk) {
            if (q->depth == 0) {
                return 0;
            }
            q->cur = q->after[--q->depth];
            continue;
        }
        q->cur = blk->next;
        COL_PREFETCH(q->cur);
        if (!blk->lineOverlap(&q->mid, &q->dir, &q->adir)) {
            continue;
        }
        if (blk->m_Flag & 1) {
            if (q->depth == 16) {
                *out = blk;
                return 2;
            }
            q->after[q->depth++] = q->cur;
            q->cur = (cSatBlock*) blk->idx;
            continue;
        }
        *out = blk;
        return 1;
    }
}

// GAME_LINE_PIECE's x/z rows with the same contract-off operation order and
// operand roles as re4dc_line_piece and PSMTXMultVec. A miss needs no y row.
static inline void lineResume29XZ(f32 (*m)[4], const Vec* p, f32* x, f32* z)
{
    *x = ((p->x * m[0][0] + p->y * m[0][1]) + p->z * m[0][2]) + m[0][3];
    *z = ((m[2][0] * p->x + m[2][1] * p->y) + m[2][2] * p->z) + m[2][3];
}

#endif
