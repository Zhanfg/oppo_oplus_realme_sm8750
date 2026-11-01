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
