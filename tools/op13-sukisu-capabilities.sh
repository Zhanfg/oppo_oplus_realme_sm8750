#!/system/bin/sh
# OnePlus 13 / SukiSU Ultra runtime capability probe.
# Read-only: no feature toggles, remounts or persistent edits.
# Run as root from Android's built-in shell: sh op13-sukisu-capabilities.sh

echo "===== OnePlus 13 / SukiSU feature runtime probe ====="
printf 'Kernel: '
uname -r 2>/dev/null || echo unknown

KSUD=/data/adb/ksud
if [ ! -x "$KSUD" ]; then
    KSUD="$(command -v ksud 2>/dev/null || true)"
fi
if [ -z "$KSUD" ] || [ ! -x "$KSUD" ]; then
    echo "ERROR: compatible ksud executable not found; no kernel feature status can be inferred."
    exit 1
fi
echo "ksud: $KSUD"
echo

for name in su_compat kernel_umount selinux_hide avc_spoof mount_hide sulog adb_root shell_su_adb_only; do
    echo "--- feature: $name ---"
    "$KSUD" feature check "$name" 2>&1 || echo "Probe failed: feature ABI or permission mismatch"
    "$KSUD" feature get "$name" 2>&1 || true
done

for name in kpm cpu_spoof umount_paths dynamic_manager susfs version_spoof; do
    echo "--- extension: $name ---"
    "$KSUD" extension check "$name" 2>&1 || echo "Probe failed: extension ABI or permission mismatch"
done

echo "--- AVC spoof diagnostic (read-only) ---"
echo "Kernel/ksud feature ID must match SukiSU AVC_SPOOF=10003."
echo "Device kernel: $(uname -r 2>/dev/null)"
echo "Root uid: $(id -u 2>/dev/null)"
"$KSUD" feature check avc_spoof 2>&1
echo "feature check exit code: $?"
"$KSUD" feature get avc_spoof 2>&1
echo "feature get exit code: $?"
"$KSUD" feature get avc_spoof --config 2>&1 || true
echo "Kernel feature and AVC hook messages (filtered, latest 20 lines):"
if command -v dmesg >/dev/null 2>&1; then
    dmesg 2>/dev/null |
      grep -E 'avc_spoof:|feature: feature 10003|feature: set_handler for 10003|set_feature: failed for feature 10003|register_slow_avc_audit' |
      tail -n 20 || true
fi
echo "Interpretation: 'supported' means registered. It does not establish that"
echo "an AVC audit hook was successfully installed or that Manager's JNI can set it."
echo

echo "--- NoMount built-in driver / userspace protocol (read-only) ---"
NM=""
if command -v nm >/dev/null 2>&1; then
    NM="$(command -v nm)"
elif [ -x /data/adb/ksu/bin/nm ]; then
    NM=/data/adb/ksu/bin/nm
elif [ -x /data/adb/modules/nomount/bin/nm ]; then
    NM=/data/adb/modules/nomount/bin/nm
fi
if [ -n "$NM" ]; then
    echo "NoMount CLI: $NM"
    "$NM" version 2>&1 || echo "NoMount v22 driver/CLI handshake failed"
    if [ -r /proc/modules ] && grep -q '^nomount ' /proc/modules; then
        echo "NoMount driver mode: LKM"
    else
        echo "NoMount driver mode: not listed as LKM (built-in candidate)"
    fi
else
    echo "NoMount CLI is not installed; built-in support cannot be probed from userspace yet."
    echo "Install the matching NoMount v2.2.0 Metamodule after flashing."
fi
echo

echo "--- SUSFS kernel interface ---"
"$KSUD" susfs status 2>&1 || echo "SUSFS probe unavailable; check compatibility of ksud, kernel and SUSFS variant"

echo
echo "--- mount_hide hook initialization (read-only filtered kernel log) ---"
if command -v dmesg >/dev/null 2>&1; then
    dmesg 2>/dev/null |
        grep 'mount_hide:' |
        grep -E 'enabled \(3/3 files hooked\)|symbol lookup failed|show fns unresolved|ops unresolved|patch_text.*err' |
        tail -n 12 || true
else
    echo "dmesg not available; check the device's kernel log manually."
fi

echo "NOTE: feature status 'enabled' is a flag, not proof that"
echo "mount_hide hooks resolved and were installed successfully."
echo "Soft reboot is a ksud/Manager operation; default module umount is an app"
echo "profile setting, so neither is an independent kernel feature ID."
