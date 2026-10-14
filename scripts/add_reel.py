"""Add a finished reel to the end of the posting queue.

usage: python3 scripts/add_reel.py <id> <video.mp4> <caption.txt> "<short title>"
"""
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rid, video, caption, title = sys.argv[1:5]
assert re.fullmatch(r"[\w-]+", rid), "id: letters, digits, - and _ only"

queue = json.load(open(f"{ROOT}/queue.json")) if os.path.exists(f"{ROOT}/queue.json") else []
assert rid not in {q["id"] for q in queue}, f"{rid} is already in the queue"

text = open(caption).read().strip()
tags = re.findall(r"#\w+", text)
assert len(tags) <= 5, f"{len(tags)} hashtags; Instagram allows 5"

# stream-copy into place with the index at the front so Instagram can start fetching immediately
out = f"{ROOT}/videos/{rid}.mp4"
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-c", "copy", "-movflags", "+faststart", out], check=True)
open(f"{ROOT}/captions/{rid}.txt", "w").write(text + "\n")
queue.append({"id": rid, "title": title, "video": f"{rid}.mp4", "status": "queued"})
json.dump(queue, open(f"{ROOT}/queue.json", "w"), indent=2, ensure_ascii=False)
open(f"{ROOT}/queue.json", "a").write("\n")
print(f"queued {rid} (position {sum(q['status'] == 'queued' for q in queue)})")
