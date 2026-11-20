"""Put a rendered story into the posting feed that autopost (on the user's PC) reads.

usage: python3 publish.py 01-onoda [--at 2026-11-21T20:37]

Copies out/<name>.mp4 to ready/<date>-<name>.mp4, gives it the next free posting slot
(Baghdad time) unless --at is given, and adds it to ready/index.json with the story's
title, caption and hashtags. Commit and push the branch afterwards; autopost checks
the feed every 10 minutes and schedules it.
"""
import json, os, shutil, sys
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.abspath(__file__))
BAGHDAD = timezone(timedelta(hours=3))           # Iraq has no daylight saving
SLOTS = [(14, 37), (20, 37)]                     # afternoon + evening peak in Iraq
PLATFORMS = ["youtube", "tiktok"]
INDEX = os.path.join(ROOT, "ready", "index.json")


def load_index():
    try:
        return json.load(open(INDEX, encoding="utf-8"))
    except (OSError, ValueError):
        return []


def next_slot(items):
    taken = {datetime.fromisoformat(i["at"]).astimezone(BAGHDAD).replace(second=0, microsecond=0)
             for i in items}
    now = datetime.now(BAGHDAD) + timedelta(minutes=45)  # time for autopost to pick it up
    day = now.date()
    for _ in range(400):
        for h, m in SLOTS:
            t = datetime(day.year, day.month, day.day, h, m, tzinfo=BAGHDAD)
            if t > now and t not in taken:
                return t
        day += timedelta(days=1)
    raise RuntimeError("no free slot")


def main():
    name = sys.argv[1]
    story = json.load(open(os.path.join(ROOT, "stories", f"{name}.json"), encoding="utf-8"))
    src = os.path.join(ROOT, "out", f"{name}.mp4")
    if not os.path.exists(src):
        sys.exit(f"render it first: node render.js stories/{name}.json")
    items = load_index()
    if any(i.get("story") == name for i in items):
        sys.exit(f"{name} is already in the feed")
    if "--at" in sys.argv:
        at = datetime.fromisoformat(sys.argv[sys.argv.index("--at") + 1]).replace(tzinfo=BAGHDAD)
    else:
        at = next_slot(items)
    iid = f"{at:%Y-%m-%d-%H%M}-{name}"
    os.makedirs(os.path.dirname(INDEX), exist_ok=True)
    shutil.copy(src, os.path.join(ROOT, "ready", f"{iid}.mp4"))
    items.append({"id": iid, "story": name, "video": f"ready/{iid}.mp4", "at": at.isoformat(),
                  "title": story.get("title", name), "caption": story.get("caption", ""),
                  "platforms": story.get("platforms", PLATFORMS)})
    items.sort(key=lambda i: i["at"])
    json.dump(items, open(INDEX, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{name} -> {at:%A %Y-%m-%d %H:%M} Baghdad  ({iid})")


if __name__ == "__main__":
    main()
