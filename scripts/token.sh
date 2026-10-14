#!/bin/bash
# Instagram login tokens last 60 days. This keeps ours alive.
#   scripts/token.sh save      paste a new token (hidden), store it locally + in GitHub
#   scripts/token.sh refresh   swap for a fresh 60-day token (run at least once a month)
set -euo pipefail
DIR="$HOME/.config/reel-autopilot"; FILE="$DIR/token"
REPO="$(cd "$(dirname "$0")/.." && gh repo view --json nameWithOwner -q .nameWithOwner)"
mkdir -p "$DIR"; chmod 700 "$DIR"

store() {
  umask 077; printf '%s' "$1" > "$FILE"
  printf '%s' "$1" | gh secret set IG_ACCESS_TOKEN -R "$REPO"
}

case "${1:-}" in
  save)
    read -rsp "Paste the Instagram access token (it won't show): " T; echo
    ID=$(curl -fsS "https://graph.instagram.com/v25.0/me?fields=user_id,username&access_token=$T")
    echo "Token works for: @$(echo "$ID" | python3 -c 'import json,sys;print(json.load(sys.stdin)["username"])')"
    store "$T"
    echo "$ID" | python3 -c 'import json,sys;print(json.load(sys.stdin)["user_id"],end="")' | gh secret set IG_USER_ID -R "$REPO"
    echo "Saved IG_ACCESS_TOKEN and IG_USER_ID to GitHub."
    ;;
  refresh)
    NEW=$(curl -fsS "https://graph.instagram.com/refresh_access_token?grant_type=ig_refresh_token&access_token=$(cat "$FILE")" |
          python3 -c 'import json,sys;print(json.load(sys.stdin)["access_token"],end="")')
    store "$NEW"; echo "$(date): token refreshed (good for 60 more days)"
    ;;
  *) echo "usage: $0 save|refresh"; exit 1 ;;
esac
