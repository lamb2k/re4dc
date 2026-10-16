# RE4 Dreamcast port toolchain image.
#
#   docker build -t re4dc-toolchain -f port/dreamcast/docker/Dockerfile .      (from the repository root)
#   docker run --rm -it -v "$PWD":/src -w /src re4dc-toolchain bash port/dreamcast/build-public.sh
#
# It runs port/dreamcast/tools/setup-toolchain.sh, so the image holds exactly what the script builds:
# KallistiOS 804b3195 with the three port patches and the kos-chain "stable" SH4 compiler
# (GCC 15.2.0, binutils 2.45.1, newlib 4.6.0.20260123), under /opt/re4dc. SH4ZAM comes with the mounted repository (the git
# submodule port/dreamcast/game/third_party/sh4zam: clone with --recurse-submodules); cmake is only for `make sh4zam-lib`.
FROM ubuntu:24.04

ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential bison flex texinfo libgmp-dev libmpfr-dev libmpc-dev libelf-dev \
        libjpeg-dev libpng-dev cmake git curl wget ca-certificates xz-utils bzip2 patch \
        python3 python3-pip genisoimage \
    && rm -rf /var/lib/apt/lists/*

# Only the files the toolchain build reads, so editing the game does not invalidate this layer.
COPY port/dreamcast/toolchain.lock port/dreamcast/kos-env.sh port/dreamcast/requirements.txt /tmp/re4dc/port/dreamcast/
COPY port/dreamcast/patches /tmp/re4dc/port/dreamcast/patches
COPY port/dreamcast/tools/setup-toolchain.sh /tmp/re4dc/port/dreamcast/tools/
RUN JOBS="$(nproc)" bash /tmp/re4dc/port/dreamcast/tools/setup-toolchain.sh /opt/re4dc \
    && rm -rf /tmp/re4dc /root/.cache

ENV RE4DC_KOS_BASE=/opt/re4dc/kos \
    RE4DC_KOS_CC_BASE=/opt/re4dc/sh-elf \
    RE4DC_KOS_PORTS=/opt/re4dc/kos-ports \
    KOS_TOOLS_BASE=/opt/re4dc/kos \
    PATH=/opt/re4dc/sh-elf/bin:$PATH
# The repository is mounted from the host and owned by another uid.
RUN git config --global --add safe.directory '*'
WORKDIR /src
