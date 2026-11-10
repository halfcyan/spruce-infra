#!/bin/sh
# check that every Quadlet unit in the repo generates a valid systemd service
set -eu

cd "$(dirname "$0")"

quadlet=/usr/libexec/podman/quadlet
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

for unit in */*.container */*.network */*.volume */*.build; do
    [ -e "$unit" ] || continue
    name=$(basename "$unit")
    if [ -e "$tmp/$name" ]; then
        echo "duplicate unit name: $name" >&2
        exit 1
    fi
    cp "$unit" "$tmp/$name"
done

echo "Validating Quadlet units"
if ! out=$(QUADLET_UNIT_DIRS="$tmp" "$quadlet" -dryrun -user 2>&1 >/dev/null); then
    echo "$out" >&2
    exit 1
fi
