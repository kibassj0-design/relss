"""Fetch a picture for every scene that has an "img" + "q" (search query) in a story JSON.

usage: python3 fetch_images.py stories/01-onoda.json [--force]

Sources (both free, both reachable from the cloud environment):
  1. Wikimedia Commons  - real historical photos, original file from upload.wikimedia.org
  2. Openverse          - Creative-Commons photos for anything else (500px proxy thumbs)
A scene may set "src": "openverse" to skip Commons, or "file": "File:Exact name.jpg"
to pin an exact Commons file. Credits are written to images/<story>/CREDITS.txt.
"""
import io, json, os, sys, time, urllib.error, urllib.parse, urllib.request
from PIL import Image, ImageOps

UA = {"User-Agent": "qisas-story-video-bot/1.0 (personal, non-commercial)"}
ROOT = os.path.dirname(os.path.abspath(__file__))


def get(url, raw=False, tries=4):
    time.sleep(1.5)  # be gentle: Wikimedia answers 429 to fast clients
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                data = r.read()
                return data if raw else json.loads(data)
        except urllib.error.HTTPError as e:
            if e.code != 429 or i == tries - 1:
                raise
            wait = int(e.headers.get("Retry-After") or 0) or 15 * (i + 1)
            print(f"    rate limited, waiting {wait}s")
            time.sleep(min(wait, 90))
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(3 + 3 * i)


def commons(query, exact=None, limit=12):
    p = {"action": "query", "format": "json", "prop": "imageinfo", "iiprop": "url|size|mime|extmetadata"}
    if exact:
        p["titles"] = exact
    else:
        p.update(generator="search", gsrnamespace=6, gsrsearch=query, gsrlimit=limit)
    d = get("https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(p))
    pages = sorted(d.get("query", {}).get("pages", {}).values(), key=lambda x: x.get("index", 0))
    out = []
    for pg in pages:
        ii = (pg.get("imageinfo") or [{}])[0]
        if ii.get("mime") not in ("image/jpeg", "image/png"):
            continue
        if ii.get("width", 0) < 450 or ii.get("size", 0) > 25_000_000:
            continue
        meta = ii.get("extmetadata", {})
        who = meta.get("Artist", {}).get("value", "")
        lic = meta.get("LicenseShortName", {}).get("value", "")
        out.append((ii["url"], f"{pg['title']} — {lic} — {strip(who)} — {ii.get('descriptionurl','')}"))
    return out


def openverse(query, limit=10):
    q = urllib.parse.urlencode({"q": query, "page_size": limit, "mature": "false",
                                "license": "by,by-sa,cc0,pdm"})  # commercial use allowed
    d = get("https://api.openverse.org/v1/images/?" + q)
    return [(f"https://api.openverse.org/v1/images/{r['id']}/thumb/?full_size=true",
             f"{r.get('title','')} — {r.get('license','')} {r.get('license_version','')} — {r.get('creator','')} — {r.get('foreign_landing_url','')}")
            for r in d.get("results", [])]


def strip(html):
    import re
    return re.sub(r"<[^>]+>", "", html or "").strip()[:80]


def save(data, path, max_side=1600):
    im = Image.open(io.BytesIO(data))
    im = ImageOps.exif_transpose(im).convert("RGB")
    im.thumbnail((max_side, max_side))
    im.save(path, "JPEG", quality=88)
    return im.size


def main():
    story_path = sys.argv[1]
    force = "--force" in sys.argv
    story = json.load(open(story_path, encoding="utf-8"))
    credits, used = [], set()
    for sc in story["scenes"]:
        if not sc.get("img"):
            continue
        dest = os.path.join(ROOT, sc["img"])
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        if os.path.exists(dest) and not force:
            continue
        q = sc.get("q") or " ".join(sc.get("lines", []))
        cands = []
        print(f'  searching: {q}')
        if sc.get("src") != "openverse":
            try:
                cands += commons(q, sc.get("file"))
            except Exception as e:
                print("  commons failed:", e)
        try:
            cands += openverse(sc.get("q_en") or q)
        except Exception as e:
            print("  openverse failed:", e)
        ok = False
        for url, credit in cands:
            if url in used:
                continue
            try:
                size = save(get(url, raw=True), dest)
            except Exception as e:
                print("  skip", url[:80], e)
                continue
            used.add(url)
            credits.append(f"{os.path.basename(dest)}: {credit}")
            print(f"  {sc['img']}  <- {credit[:90]}  {size}")
            ok = True
            break
        if not ok:
            print(f"  NO IMAGE for {sc['img']} ({q}) -> scene renders as motion only")
    if credits:
        folder = os.path.dirname(os.path.join(ROOT, next(s["img"] for s in story["scenes"] if s.get("img"))))
        with open(os.path.join(folder, "CREDITS.txt"), "a", encoding="utf-8") as f:
            f.write("\n".join(credits) + "\n")
    json.dump(story, open(story_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
