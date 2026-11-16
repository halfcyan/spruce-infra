#!/bin/sh
# check that every Quadlet unit in the repo generates a valid systemd service
set -eu

cd "$(dirname "$0")"

quadlet=/usr/libexec/podman/quadlet
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

for host in hosts/*/; do
    host=$(basename "$host")
    mkdir "$tmp/$host"
    # unit names only have to be unique within a host
    for unit in hosts/"$host"/*/*.container hosts/"$host"/*/*.network \
        hosts/"$host"/*/*.volume hosts/"$host"/*/*.build; do
        [ -e "$unit" ] || continue
        name=$(basename "$unit")
        if [ -e "$tmp/$host/$name" ]; then
            echo "duplicate unit name on $host: $name" >&2
            exit 1
        fi
        cp "$unit" "$tmp/$host/$name"
    done

    echo "Validating Quadlet units for $host"
    if ! out=$(QUADLET_UNIT_DIRS="$tmp/$host" "$quadlet" -dryrun -user 2>&1 >/dev/null); then
        echo "$out" >&2
        exit 1
    fi
done
