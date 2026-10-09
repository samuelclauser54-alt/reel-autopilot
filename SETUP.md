# Reel Autopilot: one-time setup

## How it works
- `queue.json` is the posting order. Each day at about 6:17 pm Chicago time, a GitHub Action posts the next reel through Instagram's official API.
- The videos are hosted on GitHub Pages (`media` branch), because Instagram downloads each video from a public link.
- To skip a reel, untick it in the **📅 Upcoming posts** issue in the GitHub phone app.
- Safety rules: at most 1 post per 20 hours, never a repeat caption, no more than 5 hashtags.

## Your steps (about 20 min)

1. **Instagram → Creator account.** In the app go to Settings → *Account type and tools* → *Switch to professional account* → **Creator**. It's free and doesn't hurt reach.
2. **Create a Meta developer app.**
   - Go to https://developers.facebook.com and log in. This needs a Facebook account.
   - Click **My Apps → Create App**, name it `reel-autopilot`, and pick the use case **"Manage messaging & content on Instagram"**.
   - In the app, open **Instagram → API setup with Instagram login**.
   - Under *Generate access tokens*, click **Add account**, log in to your Instagram, and allow the permissions. Make sure *content publish* is included.
   - Click **Generate token** and copy the token.
   - If it says the account isn't a tester, go to **App roles → Roles → Add Instagram tester** and add your username. Then in Instagram, accept the invite under Settings → *Website permissions → Apps and websites → Tester invites*. Then generate the token again.
   - The app stays in development mode. That's fine, because it only posts to your own account.
3. **Save the token.** Don't paste it in chat. Run this in the terminal:
   ```
   ~/reel-autopilot/scripts/token.sh save
   ```
4. **Test.** Run *Actions → post-reel → Run workflow* with "dry run" ticked. Then run it once more with it unticked to post the first reel.

## Upkeep
- Tokens expire after 60 days. To get a fresh one, run `~/reel-autopilot/scripts/token.sh refresh` at least once a month. You can also have a weekly launchd job do this.
- To add a reel: `python3 scripts/add_reel.py <id> <video.mp4> <caption.txt> "<title>"`, then `git push`, then `scripts/sync_media.sh`.
