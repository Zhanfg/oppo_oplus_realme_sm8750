#!/usr/bin/env python3
"""Fail-closed audit of the SUSFS priority-UID RCU lifetime hardening.

This checks the actual source fetched for the current Android15/6.6
build. SUSFS version labels alone cannot establish this fix.
"""
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("Usage: op13-audit-susfs-rcu.py <susfs.c>")
src = Path(sys.argv[1]).read_text()

a = src.find("/* priority uid filter */")
b = src.find("/* susfs avc log spoofing */", a)
if a == -1 or b <= a:
    raise SystemExit("SUSFS priority UID filter source not found")
section = src[a:b]
if "struct rcu_head" not in section or    "priority_uid_filter_bitmap __rcu *" not in section or    "rcu_dereference(priority_uid_filter_bitmap)" not in section:
    raise SystemExit("RCU data representation or lockless reader missing")

split1 = section.find("void susfs_set_priority_uid_filter(")
split2 = section.find("static int susfs_priority_app_strings_worker(", split1)
split3 = section.find("bool susfs_is_priority_uid_filtered(", split2)
if not (0 <= split1 < split2 < split3):
    raise SystemExit("Unrecognized filter update/worker/reader layout")

for label, block in [
    ("priority UID filter setter", section[split1:split2]),
    ("priority UID filter worker", section[split2:split3]),
]:
    operations = [
        "rcu_dereference_protected(priority_uid_filter_bitmap",
        "rcu_assign_pointer(priority_uid_filter_bitmap, new_bitmap)",
        "mutex_unlock(&susfs_mutex_lock_priority_uid_filter)",
        "synchronize_rcu();",
        "kfree_rcu(old_bitmap, rcu);",
    ]
    positions = [block.find(op) for op in operations]
    if any(i < 0 for i in positions) or positions != sorted(positions):
        raise SystemExit(label + ": missing or misordered RCU lifetime barrier")
print("SUSFS priority UID filter: both updater paths publish, unlock, synchronize RCU and defer freeing safely")
