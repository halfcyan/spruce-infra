#!/bin/sh
# install one host's Quadlet units for the current user and (re)start services.
# Run on the host from the checkout at ~/spruce-infra.
#
#   --host NAME     deploy hosts/NAME (default: short hostname)
#   --since REV     restart services whose directory changed between REV and HEAD
#   --env-dir DIR   install rendered .env files from DIR/<service>/.env, then delete DIR
set -eu

repo=$(dirname "$(readlink -f "$0")")

host=$(hostname -s)
since=""
env_dir=""
while [ $# -gt 0 ]; do
    case "$1" in
        --host) host="$2"; shift 2 ;;
        --since) since="$2"; shift 2 ;;
        --env-dir) env_dir="$2"; shift 2 ;;
        *) echo "usage: $0 [--host NAME] [--since REV] [--env-dir DIR]" >&2; exit 2 ;;
    esac
done

if [ ! -d "$repo/hosts/$host" ]; then
    echo "no such host: $repo/hosts/$host" >&2
    exit 2
fi
cd "$repo/hosts/$host"

# one-time migration from the flat layout. git pull moves tracked files into
# hosts/<host>/, but ignored runtime state (.env, data/, db/...) stays behind in
# the old top-level directory. Renames keep running containers' bind mounts
# intact, and podman unshare lets us move files owned by container subuids.
for dir in */; do
    dir=${dir%/}
    old="$repo/$dir"
    [ -d "$old" ] || continue
    for entry in "$old"/* "$old"/.[!.]* "$old"/..?*; do
        [ -e "$entry" ] || continue
        name=$(basename "$entry")
        if [ -e "$dir/$name" ]; then
            echo "not migrating $entry: $dir/$name already exists" >&2
            continue
        fi
        echo "migrating $entry -> hosts/$host/$dir/$name"
        podman unshare mv "$entry" "$dir/$name"
    done
    podman unshare rmdir "$old" 2>/dev/null || echo "left $old behind, check it by hand" >&2
done

units_dir="${XDG_CONFIG_HOME:-$HOME/.config}/containers/systemd/spruce-infra"
unit_globs='*.container *.network *.volume *.build'

changed=""
mark() {
    case " $changed " in
        *" $1 "*) ;;
        *) changed="$changed $1" ;;
    esac
}

# map a Quadlet file name to the systemd service it generates
service_for() {
    name=$(basename "$1")
    case "$name" in
        *.container) echo "${name%.container}.service" ;;
        *.network) echo "${name%.network}-network.service" ;;
        *.volume) echo "${name%.volume}-volume.service" ;;
        *.build) echo "${name%.build}-build.service" ;;
    esac
}

services=$(for g in $unit_globs; do
    for f in */$g; do
        [ -e "$f" ] && dirname "$f"
    done
done | sort -u)

# anything but docs changing in a service directory gets it restarted
if [ -n "$since" ]; then
    for dir in $(git diff --relative --name-only "$since" HEAD -- . ':!*.md' | cut -s -d/ -f1 | sort -u); do
        [ -d "$dir" ] && mark "$dir"
    done
fi

if [ -n "$env_dir" ]; then
    for env in "$env_dir"/*/.env; do
        [ -e "$env" ] || continue
        dir=$(basename "$(dirname "$env")")
        [ -d "$dir" ] || continue
        if ! cmp -s "$env" "$dir/.env"; then
            install -m 600 "$env" "$dir/.env"
            mark "$dir"
        fi
    done
    rm -rf "$env_dir"
fi

# stop and remove units that are no longer in the repo
if [ -d "$units_dir" ]; then
    for unit in "$units_dir"/*/*; do
        [ -e "$unit" ] || continue
        rel=${unit#"$units_dir"/}
        [ -e "$rel" ] && continue
        echo "removing $rel"
        systemctl --user stop "$(service_for "$unit")" || true
        rm -f "$unit"
    done
    find "$units_dir" -mindepth 1 -type d -empty -delete
fi

for dir in $services; do
    mkdir -p "$units_dir/$dir"
    for g in $unit_globs; do
        for unit in "$dir"/$g; do
            [ -e "$unit" ] || continue
            if ! cmp -s "$unit" "$units_dir/$unit"; then
                cp "$unit" "$units_dir/$unit"
                mark "$dir"
            fi
        done
    done
done

systemctl --user daemon-reload

failed=""
for dir in $services; do
    case " $changed " in
        *" $dir "*) action=restart ;;
        # start is a no-op for services that are already running
        *) action=start ;;
    esac
    # rebuild local images before restarting the containers that use them
    for unit in "$dir"/*.build "$dir"/*.container; do
        [ -e "$unit" ] || continue
        svc=$(service_for "$unit")
        echo "$action $svc"
        systemctl --user "$action" "$svc" || failed="$failed $svc"
    done
done

if [ -n "$failed" ]; then
    echo "failed:$failed" >&2
    echo "check with: journalctl --user -u <service>" >&2
    exit 1
fi
