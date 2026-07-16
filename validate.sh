#!/bin/sh
set -eu

for compose in nginx-proxy-manager/compose.yml willowidk.dev/compose.yml; do
    dir=$(dirname "$compose")
    echo "Validating $compose"
    (cd "$dir" && podman-compose config >/dev/null)
done
