"""Post the next queued reel to Instagram. Runs once a day in GitHub Actions.

Safety rules (to look like a normal creator, never like a bot):
  * at most ONE post per run, and never two within 20 hours
  * never re-post something whose caption is already on the account
  * caption must have <= 5 hashtags and <= 2200 chars
  * reels unticked in the "Upcoming posts" issue are skipped

Env: IG_USER_ID, IG_ACCESS_TOKEN, MEDIA_BASE_URL, GITHUB_TOKEN, GITHUB_REPOSITORY, DRY_RUN
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUEUE = os.path.join(ROOT, "queue.json")
IG = "https://graph.instagram.com/v25.0"
DRY = os.environ.get("DRY_RUN", "") in ("1", "true")
MIN_GAP = timedelta(hours=20)


def http(method, url, params=None, headers=None):
    data = None
    if params and method == "GET":
        url += "?" + urllib.parse.urlencode(params)
    elif params:
        data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        raise SystemExit(f"{method} {url.split('?')[0]} -> {e.code}: {e.read().decode()[:500]}")


def ig(method, path, **params):
    params["access_token"] = os.environ["IG_ACCESS_TOKEN"]
    return http(method, f"{IG}/{path}", params)


def check_caption(text):
    tags = re.findall(r"#\w+", text)
    if len(tags) > 5:
        raise SystemExit(f"caption has {len(tags)} hashtags (max 5)")
    if len(text) > 2200:
        raise SystemExit(f"caption is {len(text)} chars (max 2200)")


# ---- GitHub control issue: tick boxes = allowed to post -------------------
ISSUE_TITLE = "📅 Upcoming posts"


def gh(method, path, body=None):
    url = f"https://api.github.com/repos/{os.environ['GITHUB_REPOSITORY']}/{path}"
    req = urllib.request.Request(url, method=method, data=json.dumps(body).encode() if body else None,
                                 headers={"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
                                          "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read() or b"{}")


def control_issue():
    for it in gh("GET", "issues?state=open&per_page=50"):
        if it["title"] == ISSUE_TITLE:
            return it
    return None


def unticked(issue):
    """ids whose box the user unticked: '- [ ] `id`'"""
    return set(re.findall(r"- \[ \] `([\w-]+)`", (issue or {}).get("body") or ""))


def render_issue(queue):
    lines = ["Untick a box to **skip** that reel. One reel posts per day, top to bottom.",
             "Edit this issue from the GitHub app on your phone.", ""]
    for q in queue:
        if q["status"] == "queued":
            lines.append(f"- [x] `{q['id']}` {q['title']}")
        elif q["status"] == "skipped":
            lines.append(f"- [ ] `{q['id']}` {q['title']}")
    done = [q for q in queue if q["status"] == "posted"][-5:]
    if done:
        lines += ["", "**Recently posted**"] + [f"- {q['posted_at'][:10]} {q['title']}" for q in done]
    return "\n".join(lines)


def sync_issue(queue, issue):
    body = render_issue(queue)
    if issue:
        gh("PATCH", f"issues/{issue['number']}", {"body": body})
    else:
        gh("POST", "issues", {"title": ISSUE_TITLE, "body": body})


# ---- main -----------------------------------------------------------------
def main():
    queue = json.load(open(QUEUE))
    issue = control_issue() if os.environ.get("GITHUB_TOKEN") else None
    off = unticked(issue)
    for q in queue:   # the issue is the source of truth for skip / unskip
        if q["status"] == "queued" and q["id"] in off:
            q["status"] = "skipped"
        elif q["status"] == "skipped" and issue and q["id"] not in off:
            q["status"] = "queued"

    posted = [q for q in queue if q["status"] == "posted"]
    last = max((datetime.fromisoformat(q["posted_at"]) for q in posted), default=None)
    nxt = next((q for q in queue if q["status"] == "queued"), None)

    if nxt is None:
        print("queue empty, nothing to post")
    elif last and datetime.now(timezone.utc) - last < MIN_GAP:
        print(f"last post was {last}, under 20 h ago: waiting")
    else:
        caption = open(os.path.join(ROOT, "captions", f"{nxt['id']}.txt")).read().strip()
        check_caption(caption)
        url = f"{os.environ['MEDIA_BASE_URL'].rstrip('/')}/{nxt['video']}"
        print(f"posting {nxt['id']}  ({url})")
        if DRY:
            print("DRY_RUN: would post now. Caption:\n" + caption)
        else:
            uid = os.environ["IG_USER_ID"]
            recent = ig("GET", f"{uid}/media", fields="caption,timestamp", limit=25).get("data", [])
            if any((m.get("caption") or "")[:80] == caption[:80] for m in recent):
                print("already on the account: marking posted, not re-posting")
                nxt.update(status="posted", posted_at=datetime.now(timezone.utc).isoformat())
            else:
                c = ig("POST", f"{uid}/media", media_type="REELS", video_url=url,
                       caption=caption, share_to_feed="true")["id"]
                for _ in range(30):   # Instagram downloads + transcodes the video
                    time.sleep(20)
                    st = ig("GET", c, fields="status_code,status")
                    print("  container:", st.get("status_code"))
                    if st.get("status_code") == "FINISHED":
                        break
                    if st.get("status_code") in ("ERROR", "EXPIRED"):
                        nxt["status"] = "failed"
                        nxt["error"] = st.get("status", "")
                        break
                else:
                    raise SystemExit("container never finished")
                if nxt["status"] != "failed":
                    mid = ig("POST", f"{uid}/media_publish", creation_id=c)["id"]
                    nxt.update(status="posted", media_id=mid,
                               posted_at=datetime.now(timezone.utc).isoformat())
                    print("  published media", mid)

    json.dump(queue, open(QUEUE, "w"), indent=2, ensure_ascii=False)
    open(QUEUE, "a").write("\n")
    if os.environ.get("GITHUB_TOKEN") and not DRY:
        sync_issue(queue, issue)
    if nxt and nxt["status"] == "failed":
        sys.exit(f"Instagram rejected {nxt['id']}: {nxt.get('error')}")


if __name__ == "__main__":
    main()
