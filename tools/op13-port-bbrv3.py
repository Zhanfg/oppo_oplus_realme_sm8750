#!/usr/bin/env python3
"""Strict OPlus 6.6.118 compatibility port for the pinned Android 15 BBRv3 patch.

This script only rewrites patch hunks already checked against the known OPlus
source and applies three equivalent adaptations after GNU patch completes.
Usage: op13-port-bbrv3.py prepare <patch> <kernel-tree>
       op13-port-bbrv3.py finish  <patch> <kernel-tree>
No patching error is ignored.
"""
from pathlib import Path
import sys

_, mode, patch_name, kernel_name = sys.argv
patch_path = Path(patch_name)
kernel = Path(kernel_name)

if mode == "prepare":
    patch = patch_path.read_text()
    marker = "diff --git a/"
    chunks = patch.split(marker)
    if len(chunks) < 12:
        raise RuntimeError("Expected 13-file BBRv3 upstream patch")
    prefix, sections = chunks[0], chunks[1:]
    omitted = {"net/ipv4/Kconfig", "net/ipv4/Makefile"}
    kept = []
    for raw in sections:
        filename = raw.split(" b/", 1)[0]
        if filename in omitted:
            continue
        if filename == "net/ipv4/tcp_input.c":
            start = "@@ -3987,7 +4017,7 @@ static int tcp_ack"
            end = "@@ -4011,6 +4041,7 @@ static int tcp_ack"
            a, b = raw.find(start), raw.find(end)
            if a < 0 or b <= a or raw.count(start) != 1 or raw.count(end) != 1:
                raise RuntimeError("Unexpected BBRv3 ACK hunk; do not drop protection")
            raw = raw[:a] + raw[b:]
        kept.append(marker + raw)
    if len(kept) != len(sections) - 2:
        raise RuntimeError("BBRv3 source patch layout mismatch")
    kconfig = (kernel / "net/ipv4/Kconfig").read_text()
    makefile = (kernel / "net/ipv4/Makefile").read_text()
    tcp = (kernel / "net/ipv4/tcp_input.c").read_text()
    for desc, condition in [
        ("vendor Kconfig", "config TCP_CONG_BBR\n" in kconfig and "config TCP_CONG_BBR3" not in kconfig),
        ("vendor Makefile", "obj-$(CONFIG_TCP_CONG_BBR) += tcp_bbr.o" in makefile),
        ("vendor ACK path", "tcp_in_ack_event(sk, flag);" in tcp and
         tcp.count("tcp_process_tlp_ack(sk, ack, flag);") == 2)
    ]:
        if not condition:
            raise RuntimeError("BBRv3 unsupported " + desc)
    patch_path.write_text(prefix + "".join(kept))
    print("Prepared BBRv3 patch: retained all vendor-compatible TCP hunks")

elif mode == "finish":
    kconfig_path = kernel / "net/ipv4/Kconfig"
    makefile_path = kernel / "net/ipv4/Makefile"
    tcp_path = kernel / "net/ipv4/tcp_input.c"
    kconfig = kconfig_path.read_text()
    mk = makefile_path.read_text()
    tcp = tcp_path.read_text()
    if "config TCP_CONG_BBR3" in kconfig or "tcp_bbr3.o" in mk:
        raise RuntimeError("BBRv3 already registered")
    anchor = 'choice\n\tprompt "Default TCP congestion control"'
    if kconfig.count(anchor) != 1:
        raise RuntimeError("Unrecognized OPlus congestion Kconfig layout")
    added = ('config TCP_CONG_BBR3\n'
             '\ttristate "BBRv3 TCP"\n'
             '\tdefault n\n'
             '\thelp\n'
             '\t  Google BBRv3 congestion control, alongside BBRv1.\n\n')
    kconfig_path.write_text(kconfig.replace(anchor, added + anchor, 1))
    old = "obj-$(CONFIG_TCP_CONG_BBR) += tcp_bbr.o"
    if mk.count(old) != 1:
        raise RuntimeError("Unrecognized OPlus Makefile BBR layout")
    makefile_path.write_text(mk.replace(old, old + "\nobj-$(CONFIG_TCP_CONG_BBR3) += tcp_bbr3.o", 1))
    old_call = "tcp_process_tlp_ack(sk, ack, flag);"
    if tcp.count(old_call) != 1 or tcp.count("tcp_process_tlp_ack(sk, ack, flag, &rs);") != 1:
        raise RuntimeError("ACK call graph does not match expected port")
    tcp_path.write_text(tcp.replace(old_call, "tcp_process_tlp_ack(sk, ack, flag, &rs);", 1))
    if not (kernel / "net/ipv4/tcp_bbr3.c").is_file():
        raise RuntimeError("BBRv3 implementation was not created by patch")
    print("BBRv3 port complete: Kconfig/Makefile/ACK adapted; original BBRv1 retained")
else:
    raise SystemExit("Usage: op13-port-bbrv3.py prepare|finish <patch> <kernel>")
