// Bounded, tick-local sharing of pure local channels. Included only by the
// default-off Dreamcast experiment in motion.cpp; no actor clocks or events.
#ifndef RE4DC_LOCOMOTION_POSE_CACHE_H
#define RE4DC_LOCOMOTION_POSE_CACHE_H

struct LocomotionPoseCache {
    enum { POSES = 4, CHANNELS = 128 };
    struct Channel {
        Vec value;
        u16 before[3], after[3];
        const void* key;
        u32 stamp;
        u16 type, flags;
    };
    struct Pose {
        const void* clip;
        const void* keys;
        u32 frame, maximum, flags, count, epoch, stamp;
        Channel channels[CHANNELS];
    };
    Pose poses[POSES];
    const void* roomOwner;
    u32 tick, room, epoch, serial, replacement;
    u32 hits, misses, bypasses, mismatches;

    static u32 bits(f32 value) {
        u32 result;
        __builtin_memcpy(&result, &value, 4);
        return result;
    }

    // The legacy search carries interpolation temporaries between axes if it
    // exhausts a malformed/uncovered stream. Such calls are not pure samples.
    static bool covered(const HermitePrm& prm) {
        const int stride = prm.type == 0 ? 12 : prm.type == 5 ? 6 : 4;
        const u8* p = prm.key;
        for (int axis = 0; axis < 3; ++axis) {
            u16 count, first, last;
            __builtin_memcpy(&count, p, 2);
            if (!count) return false;
            __builtin_memcpy(&first, p + 2, 2);
            __builtin_memcpy(&last, p + 2 * count, 2);
            if (!(prm.frame >= first && prm.frame <= last)) return false;
            p += 2 + count * (2 + stride);
        }
        return true;
    }

    // Cache lifetime is one source Frame_cnt in one loaded room. Clip identity
    // is the immutable motion/proxy, NOT just a reusable streamed key address.
    // The caller holds the existing Re4dcMotionLease across begin and sample.
    Pose* begin(u32 now, u32 roomId, const void* owner, const void* clip,
                const void* keys, const HermitePrm& prm, int count) {
        if (count <= 0 || count > CHANNELS || !clip || !keys ||
            !(prm.frame >= 0.0f && prm.frame < prm.maxFrame && prm.maxFrame <= 65535.0f))
            return 0;
        if (!epoch || now != tick || roomId != room || owner != roomOwner) {
            tick = now; room = roomId; roomOwner = owner;
            if (++epoch == 0) {
                for (int i = 0; i < POSES; ++i) poses[i].epoch = 0;
                epoch = 1;
            }
            replacement = 0;
        }
        const u32 frame = bits(prm.frame), maximum = bits(prm.maxFrame);
        for (int i = 0; i < POSES; ++i) {
            Pose& p = poses[i];
            if (p.epoch == epoch && p.clip == clip && p.keys == keys &&
                p.frame == frame && p.maximum == maximum &&
                p.flags == prm.flags && p.count == (u32)count)
                return &p;
        }
        Pose& p = poses[replacement++ & (POSES - 1)];
        if (++serial == 0) {
            for (int i = 0; i < POSES; ++i)
                for (int j = 0; j < CHANNELS; ++j) poses[i].channels[j].stamp = 0;
            serial = 1;
        }
        p.clip = clip; p.keys = keys; p.frame = frame; p.maximum = maximum;
        p.flags = prm.flags; p.count = count; p.epoch = epoch; p.stamp = serial;
        return &p;
    }

    // Matching the input histories preserves the evaluator's full contract,
    // including unusual search histories. Failed evaluations are never cached.
    // Check mode recomputes each hit on the target and serves the reference.
    template <bool Check, typename Evaluate>
    int sample(Pose* pose, int channel, HermitePrm* prm, Vec* out, u16* hist, Evaluate evaluate) {
        if (!pose || channel < 0 || (u32)channel >= pose->count ||
            (prm->type != 0 && prm->type != 5 && prm->type != 6)) {
            ++bypasses;
            return evaluate(prm, out, hist);
        }
        Channel& c = pose->channels[channel];
        if (c.stamp == pose->stamp && c.key == prm->key && c.type == prm->type &&
            c.flags == prm->flags && c.before[0] == hist[0] &&
            c.before[1] == hist[1] && c.before[2] == hist[2]) {
            ++hits;
            if (Check) {
                const int result = evaluate(prm, out, hist);
                if (result || bits(out->x) != bits(c.value.x) || bits(out->y) != bits(c.value.y) ||
                    bits(out->z) != bits(c.value.z) || hist[0] != c.after[0] ||
                    hist[1] != c.after[1] || hist[2] != c.after[2]) {
                    ++mismatches;
                    c.stamp = 0;
                }
                return result;
            }
            *out = c.value;
            hist[0] = c.after[0]; hist[1] = c.after[1]; hist[2] = c.after[2];
            return 0;
        }
        ++misses;
        c.stamp = 0;
        c.before[0] = hist[0]; c.before[1] = hist[1]; c.before[2] = hist[2];
        const int result = evaluate(prm, out, hist);
        if (!result && covered(*prm)) {
            c.value = *out;
            c.after[0] = hist[0]; c.after[1] = hist[1]; c.after[2] = hist[2];
            c.key = prm->key; c.type = prm->type; c.flags = prm->flags;
            c.stamp = pose->stamp;
        }
        return result;
    }
};

#endif
