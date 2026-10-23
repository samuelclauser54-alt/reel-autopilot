"""Print per-reel retention / share / save rates from the Instagram API.
   python3 scripts/stats.py        (uses ~/.config/reel-autopilot/token)
Breakouts on this account held >=45% average watch; flops sat at 25-30%."""
import json
import os
import subprocess
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = open(os.path.expanduser("~/.config/reel-autopilot/token")).read().strip()
IG = "https://graph.instagram.com/v25.0"


def get(path, **kw):
    q = "&".join(f"{k}={v}" for k, v in kw.items())
    return json.load(urllib.request.urlopen(f"{IG}/{path}?{q}&access_token={T}"))


def duration(f):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", f], capture_output=True, text=True).stdout
    return float(out) if out.strip() else None


queue = {q.get("media_id"): q for q in json.load(open(os.path.join(ROOT, "queue.json")))}
media = get("me/media", fields="id,timestamp,like_count", limit=25)["data"]
print(f"{'reel':12} {'posted (UTC)':16} {'views':>6} {'watch%':>6} {'share%':>6} {'save%':>6}")
for m in reversed(media):
    ins = {x["name"]: x["values"][0]["value"] for x in get(
        f"{m['id']}/insights", metric="views,reach,saved,shares,ig_reels_avg_watch_time")["data"]}
    q = queue.get(m["id"], {})
    d = duration(os.path.join(ROOT, "videos", q["video"])) if q else None
    watch = f"{ins['ig_reels_avg_watch_time'] / 10 / d:5.0f}%" if d else "     ?"
    r = max(ins["reach"], 1)
    print(f"{q.get('id', '-'):12} {m['timestamp'][:16]} {ins['views']:6} {watch} "
          f"{ins['shares'] / r * 100:5.2f}% {ins['saved'] / r * 100:5.2f}%")
