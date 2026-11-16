#!/bin/sh
set -eu

: "${GITHUB_TOKEN:?set GITHUB_TOKEN in .env}"
: "${DISPATCH_REPOSITORY:?}" "${DISPATCH_REF:?}" "${DISPATCH_WORKFLOWS:?}"

echo "dispatching $DISPATCH_WORKFLOWS on $DISPATCH_REPOSITORY@$DISPATCH_REF hourly"
while :; do
    # wake at the top of the next hour
    sleep $((3600 - $(date +%s) % 3600))
    for wf in $DISPATCH_WORKFLOWS; do
        if curl -fsS -o /dev/null -X POST \
            -H "Accept: application/vnd.github+json" \
            -H "Authorization: Bearer $GITHUB_TOKEN" \
            -H "X-GitHub-Api-Version: 2022-11-28" \
            -d "{\"ref\":\"$DISPATCH_REF\"}" \
            "https://api.github.com/repos/$DISPATCH_REPOSITORY/actions/workflows/$wf/dispatches"; then
            echo "$(date -u +%FT%TZ) dispatched $wf"
        else
            echo "$(date -u +%FT%TZ) failed to dispatch $wf" >&2
        fi
    done
done
