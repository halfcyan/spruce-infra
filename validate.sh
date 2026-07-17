#!/bin/sh
set -eu

cleanup_envs=""

prepare_env() {
    dir="$1"
    if [ ! -f "$dir/.env" ] && [ -f "$dir/.env.example" ]; then
        cp "$dir/.env.example" "$dir/.env"
        cleanup_envs="$cleanup_envs $dir/.env"
    fi
}

prepare_env "voidauth"
prepare_env "willowidk.dev"
prepare_env "portainer"

if [ -f "portainer/.env" ]; then
    uid=$(id -u)
    sed -i "s|<uid>|$uid|" portainer/.env
fi

trap 'for env in $cleanup_envs; do rm -f "$env"; done' EXIT

for compose in nginx-proxy-manager/compose.yml voidauth/compose.yml willowidk.dev/compose.yml portainer/compose.yml; do
    dir=$(dirname "$compose")
    echo "Validating $compose"
    (cd "$dir" && podman-compose config >/dev/null)
done
