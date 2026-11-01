#!/usr/bin/env python3
"""Fail-closed SukiSU builtin Preinit source-layout audit (pinned SHA).

The 2026-11-01 SukiSU builtin commit rewrote preinit as a standalone C
translation unit using an embedded nolibc runner. Do not rewrite it into a
unity build or disable Preinit to work around incompatible older commits.
"""
from pathlib import Path

root = Path("kernel_workspace/KernelSU/kernel")
checks = {
    "Makefile": [
        "ksu-y += preinit/preinit.o preinit/blob.o",
        "$(obj)/preinit/runner.elf:",
    ],
    "ksu_main.c": [
        '#include "preinit/preinit.h"',
        "ksu_preinit_init();",
    ],
    "preinit/preinit.c": [
        "#include <linux/err.h>",
        "void __init ksu_preinit_init(void)",
        "int ksu_setup_preinit_file(",
        "ksu_preinit_handle_post_execveat(",
        "ksu_preinit_runner_start",
        "ksu_preinit_runner_end",
    ],
    "preinit/blob.S": [".incbin KSU_PREINIT_RUNNER_BIN"],
    "preinit/runner/runner.c": [
        '#include "nolibc.h"',
        "ksu_preinit:",
    ],
}
for rel, terms in checks.items():
    path = root / rel
    if not path.is_file():
        raise SystemExit(f"Missing pinned SukiSU preinit file: {rel}")
    data = path.read_text()
    for term in terms:
        if term not in data:
            raise SystemExit(f"Unexpected builtin Preinit ABI in {rel}: {term}")

if "constexpr" in (root / "preinit/preinit.c").read_text():
    raise SystemExit("C++ expressions found in pinned standalone Preinit source")

print("Pinned SukiSU builtin Preinit: standalone C unit + embedded nolibc runner; no source edits needed.")
