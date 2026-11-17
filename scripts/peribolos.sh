#!/usr/bin/env bash
# Run Peribolos against a rendered config. Dry run unless --confirm is passed.
#
# Auth, one of:
#   PERIBOLOS_APP_ID + PERIBOLOS_APP_KEY_FILE   (the governance GitHub App, in CI)
#   PERIBOLOS_TOKEN_FILE                        (a personal token, for local tests)
#
# Usage: scripts/peribolos.sh <rendered-config.yaml> [--confirm]
set -euo pipefail
here=$(cd "$(dirname "$0")/.." && pwd)
config=$(cd "$(dirname "$1")" && pwd)/$(basename "$1"); shift

# Pinned image; bump through a governance PR.
image="us-docker.pkg.dev/k8s-infra-prow/images/peribolos:v20261028-c06373a3e"

min_admins=$(python3 -c "import yaml;print((yaml.safe_load(open('$here/governance.yml')).get('peribolos') or {}).get('min_admins',2))")
delta=$(python3 -c "import yaml;print((yaml.safe_load(open('$here/governance.yml')).get('peribolos') or {}).get('maximum_removal_delta',0.25))")

mounts=(-v "$config:/config/org.yaml:ro")
if [ -n "${PERIBOLOS_APP_ID:-}" ]; then
  mounts+=(-v "$PERIBOLOS_APP_KEY_FILE:/secret/app.pem:ro")
  auth=(--github-app-id="$PERIBOLOS_APP_ID" --github-app-private-key-path=/secret/app.pem)
else
  mounts+=(-v "$PERIBOLOS_TOKEN_FILE:/secret/token:ro")
  auth=(--github-token-path=/secret/token)
fi

docker run --rm "${mounts[@]}" "$image" \
  --config-path=/config/org.yaml \
  "${auth[@]}" \
  --require-self=false \
  --min-admins="$min_admins" \
  --maximum-removal-delta="$delta" \
  --fix-org --fix-org-members \
  --fix-teams --fix-team-members --fix-team-repos \
  "$@"
