"""Download a CC0 sound library from Freesound into sfx/<category>/ (run once; needs an API key).

usage: FS_KEY_FILE=/path/to/key python3 sfx_library.py
The videos only use the downloaded files, so daily runs need no key. Credits: sfx/CREDITS.txt
"""
import json, os, sys, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
KEY = open(os.environ["FS_KEY_FILE"]).read().strip()
# category: (query, how many, min seconds, max seconds)
LIB = {
 "whoosh": ("whoosh", 10, 0.3, 2.5), "swish": ("swish fast transition", 6, 0.2, 1.5),
 "impact": ("cinematic impact boom", 8, 0.5, 5), "riser": ("riser tension cinematic", 5, 1.5, 6),
 "glitch": ("glitch transition", 4, 0.2, 2), "shutter": ("camera shutter click", 4, 0.1, 1.5),
 "pop": ("pop ui", 5, 0.05, 0.8), "typewriter": ("typewriter keys", 3, 0.5, 4),
 "paper": ("paper rustle", 3, 0.5, 4), "heartbeat": ("heartbeat", 3, 2, 15), "clock": ("clock ticking", 3, 2, 15),
 "plane": ("airplane flyby", 4, 2, 15), "propeller": ("propeller plane", 3, 3, 20),
 "gunshot": ("gunshot distant", 4, 0.3, 4), "explosion": ("explosion distant", 4, 1, 8), "battle": ("war battle ambience", 3, 10, 60),
 "ocean": ("ocean waves", 3, 8, 60), "ship": ("ship creaking wood", 3, 4, 40), "storm": ("storm wind howling", 3, 8, 60),
 "rain": ("rain thunder", 3, 8, 60), "jungle": ("jungle ambience", 3, 10, 60), "forest": ("forest birds", 2, 10, 60),
 "night": ("night crickets", 2, 10, 60), "crowd": ("crowd murmur", 3, 5, 40), "cheer": ("crowd cheering", 2, 2, 15),
 "gasp": ("crowd gasp", 2, 0.5, 4), "footsteps": ("footsteps", 3, 2, 15), "snow": ("footsteps snow", 2, 2, 15),
 "city": ("city traffic ambience", 2, 10, 60), "radio": ("radio static", 3, 2, 15), "morse": ("morse code", 2, 2, 15),
 "radar": ("radar beep", 3, 1, 15), "fire": ("fire crackling", 2, 5, 40), "wind": ("wind desert", 2, 8, 60),
 "metal": ("metal hit", 3, 0.3, 3), "bell": ("church bell", 2, 2, 15), "money": ("coins cash", 3, 0.5, 5),
 "music_dark": ("dark ambient music", 4, 40, 240), "music_mystery": ("mystery suspense music", 4, 40, 240),
 "music_drone": ("suspense drone", 3, 30, 240), "music_epic": ("epic cinematic music", 3, 40, 240),
}
API = "https://www.freesound.org/apiv2/search/text/?"


def get(url, raw=False):
    for i in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "qisas-sfx/1.0"}), timeout=60) as r:
                d = r.read()
                return d if raw else json.loads(d)
        except urllib.error.HTTPError as e:
            if e.code in (403, 429) and i < 3: time.sleep(15 * (i + 1)); continue
            raise


credits = []
for cat, (q, n, lo, hi) in LIB.items():
    folder = os.path.join(ROOT, "sfx", cat); os.makedirs(folder, exist_ok=True)
    if len([f for f in os.listdir(folder) if f.endswith(".mp3")]) >= n:
        continue
    p = {"query": q, "filter": f'license:"Creative Commons 0" duration:[{lo} TO {hi}]', "sort": "rating_desc",
         "fields": "id,name,username,duration,previews", "page_size": n * 2, "token": KEY}
    try:
        res = get(API + urllib.parse.urlencode(p)).get("results", [])
    except Exception as e:
        print(f"{cat}: search failed {e}"); continue
    got = 0
    for r in res:
        if got >= n: break
        dest = os.path.join(folder, f"{r['id']}.mp3")
        if not os.path.exists(dest):
            try:
                data = get(r["previews"]["preview-hq-mp3"], raw=True)
            except Exception as e:
                print(f"  skip {r['id']}: {e}"); continue
            open(dest, "wb").write(data)
        credits.append(f"{cat}/{r['id']}.mp3: \"{r['name']}\" by {r['username']} (CC0) https://freesound.org/s/{r['id']}/")
        got += 1
    print(f"{cat}: {got}")
    time.sleep(3)
with open(os.path.join(ROOT, "sfx", "CREDITS.txt"), "a", encoding="utf-8") as f:
    f.write("\n".join(credits) + "\n")
