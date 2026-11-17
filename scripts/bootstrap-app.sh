#!/usr/bin/env bash
# One-time: exchange the GitHub App manifest code for the App credentials and
# store them on catholicit/governance. The private key never touches disk.
# Usage: scripts/bootstrap-app.sh <code from ?code=... in the redirect URL>
set -euo pipefail
code="${1:?usage: $0 <code>}"
repo="catholicit/governance"

json=$(gh api -X POST "/app-manifests/$code/conversions")
id=$(jq -r .id <<<"$json")
slug=$(jq -r .slug <<<"$json")
jq -r .pem <<<"$json" | gh secret set GOVERNANCE_APP_PRIVATE_KEY --repo "$repo"
gh variable set GOVERNANCE_APP_ID --repo "$repo" --body "$id"
unset json

echo "App id: $id, slug: $slug"
echo "Install it on the org (All repositories): https://github.com/apps/$slug/installations/new"
