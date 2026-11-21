"""Real photos for every scene, found with Brave image search.

usage: python3 find_images.py stories/01-onoda.json [--scene N] [--n 3] [--force]

Each scene needs "find": an English search for exactly what the narrator says there
(e.g. "Hiroo Onoda surrender 1974 Marcos"). Up to --n candidates are saved as
images/<story>/s<scene>-<k>.jpg and listed in the scene's "cands"; look at them, then put
the good ones (in order) in the scene's "imgs" - only photos that show what is said.

Stock sites with watermarks are skipped; Wikimedia / archives / government sites come first.
The Brave key is added by the network proxy; nothing is read from disk.
"""
import io, json, os, sys, time, urllib.parse, urllib.request
from PIL import Image, ImageOps

ROOT = os.path.dirname(os.path.abspath(__file__))
BAD = ("gettyimages", "shutterstock", "alamy", "istockphoto", "dreamstime", "depositphotos", "123rf",
       "stock.adobe", "bigstock", "agefotostock", "pond5", "vectorstock", "freepik", "pinimg", "pinterest")
GOOD = ("wikimedia", "wikipedia", "archives.gov", "loc.gov", ".gov", "nara", "archive.org", "britannica",
        "smithsonian", "museum", "iwm.org.uk")
UA = {"User-Agent": "qisas-story-video-bot/1.0 (personal, non-commercial)", "Accept": "application/json"}


def get(url, raw=False, headers=UA):
    for i in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=40) as r:
                data = r.read()
                return data if raw else json.loads(data)
        except urllib.error.HTTPError as e:
            if e.code == 429 and i < 3:
                time.sleep(2 + 3 * i); continue
            raise


def search(q, count=20):
    d = get("https://api.search.brave.com/res/v1/images/search?" +
            urllib.parse.urlencode({"q": q, "count": count, "safesearch": "strict"}))
    out = []
    for r in d.get("results", []):
        src = (r.get("source") or "") + " " + (r.get("url") or "")
        orig = (r.get("properties") or {}).get("url", "")
        if any(b in (src + orig).lower() for b in BAD):
            continue
        score = 1 if any(g in (src + orig).lower() for g in GOOD) else 0
        out.append((score, r.get("title", ""), orig, (r.get("thumbnail") or {}).get("src", ""), r.get("url", "")))
    out.sort(key=lambda x: -x[0])          # stable: keeps Brave's relevance order inside each group
    return out


def save(data, path):
    im = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB")
    if min(im.size) < 220:
        raise ValueError("too small")
    im.thumbnail((1600, 1600))
    im.save(path, "JPEG", quality=90)
    return im.size


def main():
    path = sys.argv[1]
    n = int(sys.argv[sys.argv.index("--n") + 1]) if "--n" in sys.argv else 3
    only = int(sys.argv[sys.argv.index("--scene") + 1]) if "--scene" in sys.argv else None
    force = "--force" in sys.argv
    story = json.load(open(path, encoding="utf-8"))
    name = os.path.basename(path)[:-5]
    folder = os.path.join(ROOT, "images", name)
    os.makedirs(folder, exist_ok=True)
    credits = []
    for i, sc in enumerate(story["scenes"]):
        if not sc.get("find") or (only is not None and i != only) or (sc.get("cands") and not force):
            continue
        cands = []
        for score, title, orig, thumb, page in search(sc["find"]):
            if len(cands) >= n:
                break
            dest = os.path.join(folder, f"s{i}-{len(cands) + 1}.jpg")
            # full size when it is on Wikimedia (reachable), else Brave's 500px copy
            for url in ([orig] if "upload.wikimedia.org" in orig else []) + [thumb]:
                try:
                    size = save(get(url, raw=True, headers={"User-Agent": UA["User-Agent"]}), dest)
                    break
                except Exception:
                    size = None
            if not size:
                continue
            rel = os.path.relpath(dest, ROOT)
            cands.append(rel)
            credits.append(f"{os.path.basename(dest)}: {title} — {page}")
            print(f"  scene {i}: {rel} {size} {title[:60]} [{page[:50]}]")
        sc["cands"] = cands
        if not cands:
            print(f"  scene {i}: nothing found for {sc['find']!r}")
    if credits:
        with open(os.path.join(folder, "CREDITS.txt"), "a", encoding="utf-8") as f:
            f.write("\n".join(credits) + "\n")
    json.dump(story, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
