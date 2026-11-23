#!/usr/bin/env bash
# Run explicitly after preparation. This is the only repository entry point that builds an ISO.
set -Eeuo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
if (( EUID != 0 )); then
    echo 'Run: sudo bash scripts/build.sh' >&2
    exit 1
fi
python3 "$root/scripts/validate.py" --prepared
work="$root/.local/prepared"
[[ -d "$work/config" && ! -L "$work" ]] || exit 1
exec 9>"$root/.local/build.lock"
flock -n 9 || { echo 'Another build is running.' >&2; exit 1; }
cd "$work"
lb build 2>&1 | tee "$root/.local/build.log"
image="$work/live-image-amd64.hybrid.iso"
[[ -s "$image" ]] || { echo 'Expected hybrid ISO was not produced.' >&2; exit 1; }
xorriso -abort_on FAILURE -indev "$image" -ls /live/filesystem.squashfs
mkdir -p "$root/build"
output="$root/build/portable-live-os-$(date -u +%Y%m%d-%H%M%S).iso"
[[ ! -e "$output" ]] || exit 1
cp -- "$image" "$output"
(cd "$root/build" && sha256sum "$(basename "$output")" > "$(basename "$output").sha256")
printf 'ISO: %s\n' "$output"
