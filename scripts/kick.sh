#!/bin/bash
# Backup trigger (launchd): GitHub drops most cron runs, so the Mac also starts a run at each slot.
# slot_check=true -> publish.py still decides whether a slot is due, so this can never double-post.
/opt/homebrew/bin/gh workflow run post-reel -R samuelclauser54-alt/repository-1 -f dry_run=false -f slot_check=true \
  && echo "$(date): kicked" >> "$HOME/.config/reel-autopilot/kick.log"
