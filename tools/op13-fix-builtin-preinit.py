#!/usr/bin/env python3
"""Build-only SukiSU builtin preinit compilation unit compatibility probe.

Do not use for a release without a full binary/boot audit.
Checks exact upstream structure, then compiles preinit into KernelSU's
ksu_main unity translation unit so all kernel compat types are available.
"""
from pathlib import Path

root = Path("kernel_workspace/KernelSU/kernel")
mk = root / "Makefile"
main = root / "ksu_main.c"
pre = root / "preinit/preinit.c"
header = root / "preinit/preinit.h"
blob = root / "preinit/blob.S"
for p in (mk, main, pre, header, blob):
    if not p.is_file():
        raise SystemExit(f"Missing SukiSU builtin path: {p}")

m = mk.read_text()
if m.count("ksu-y += preinit/preinit.o preinit/blob.o") != 1:
    raise SystemExit("Unexpected upstream KSU preinit Makefile")
m = m.replace("ksu-y += preinit/preinit.o preinit/blob.o",
              "ksu-y += preinit/blob.o", 1)
mk.write_text(m)

c = pre.read_text()
if c.count("constexpr char expected[]") != 2:
    raise SystemExit("Unknown C++ constexpr uses in builtin preinit")
c = c.replace("constexpr char expected[]", "static const char expected[]")
if c.count("nullptr") != 2:
    raise SystemExit("Unexpected nullptr uses in two kthread_run calls")
c = c.replace("nullptr", "NULL")
c = '''/* Link runner blob from preinit/blob.S without file-scope integer init. */
extern const unsigned char ksu_preinit_runner_start[];
extern const unsigned char ksu_preinit_runner_end[];
#define runner_binary ksu_preinit_runner_start
#define runner_binary_len ((size_t)(ksu_preinit_runner_end - ksu_preinit_runner_start))
''' + c
pre.write_text(c)

s = main.read_text()
anchor = '''#ifdef CONFIG_KSU_SUSFS
#include "preinit/preinit.h"
#else
#include "preinit/common/preinit.h"
#endif'''
if s.count(anchor) != 1:
    raise SystemExit("Unexpected SukiSU builtin preinit integration layout")
new = '''#ifdef CONFIG_KSU_SUSFS
#include "preinit/preinit.h"
#ifndef KSU_NO_PREINIT
/* Build as part of the existing KernelSU unity translation unit. */
#include "preinit/preinit.c"
#endif
#else
#include "preinit/common/preinit.h"
#endif'''
main.write_text(s.replace(anchor, new, 1))
print("SukiSU builtin preinit integrated with parent kernel compile context")
