#pragma once
#include <cstdint>
#include <cstring>

// A private capture image uses one producer on the render thread. The host
// takes a copy between matching even sequence reads. Odd means in progress.
namespace m1capture {
struct Buffer {
    volatile unsigned sequence;
    unsigned magic, room, picture, game_frame, bytes, overflow;
    unsigned char payload[65536];
};
extern "C" Buffer m1_capture;
inline bool active, camera_written;
struct Prior { unsigned offset, bytes; };
inline Prior prior[2][64];
inline unsigned prior_count[2];

inline unsigned room_seen, warmup, completed;

enum Kind : unsigned { Camera=1, World, Actor, Palette, Light, Sprite, Hud };
inline void append(Kind kind, const void* data, unsigned bytes) {
    if (!active || m1_capture.overflow) return;
    const unsigned used = m1_capture.bytes;
    if (bytes > sizeof(m1_capture.payload) - used ||
        sizeof(m1_capture.payload) - used - bytes < 8) {
        m1_capture.overflow = 1;
        return;
    }
    const unsigned header[] = {kind, bytes};
    std::memcpy(m1_capture.payload + used, header, sizeof(header));
    std::memcpy(m1_capture.payload + used + 8, data, bytes);
    m1_capture.bytes = used + 8 + bytes;
}
// A back-reference identifies a complete earlier payload in this picture.
inline void intern(Kind kind, const void* data, unsigned bytes) {
    if (!active) return;
    const unsigned table = kind == Palette ? 0 : 1;
    for (unsigned i = 0; i < prior_count[table]; ++i) {
        const auto& entry = prior[table][i];
        if (entry.bytes == bytes && !std::memcmp(m1_capture.payload + entry.offset, data, bytes)) {
            append(static_cast<Kind>(unsigned(kind) + 8), &entry.offset, 4);
            return;
        }
    }
    unsigned offset = m1_capture.bytes + 8;
    append(kind, data, bytes);
    if (!m1_capture.overflow && prior_count[table] < 64)
        prior[table][prior_count[table]++] = {offset, bytes};
}
inline void begin(unsigned room, unsigned frame) {
    active = false;
    if (room != room_seen) { warmup = completed = 0; room_seen = room; }
    if ((room != 0x101 && room != 0x103) || completed == 300 || warmup < 300) return;
    if (!(m1_capture.sequence & 1)) m1_capture.sequence = m1_capture.sequence + 1;
    asm volatile("" ::: "memory");
    m1_capture.magic = 0x31434d46;
    m1_capture.room = room;
    m1_capture.game_frame = frame;
    m1_capture.picture = completed + 1;
    m1_capture.bytes = m1_capture.overflow = 0;
    camera_written = false;
    prior_count[0] = prior_count[1] = 0;
    active = true;
}
inline void end(bool shown) {
    if (shown && warmup < 300) ++warmup;
    if (active && shown) {
        ++completed;
        asm volatile("" ::: "memory");
        m1_capture.sequence = m1_capture.sequence + 1;
    }
    active = false;
}
}
