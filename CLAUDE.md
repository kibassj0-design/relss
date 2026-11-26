# قصص بالعراقي — مصنع الفيديوهات اليومي

This branch (`qisas` of kibassj0-design/relss) is a content factory for a faceless
TikTok + YouTube Shorts channel: **true strange stories / mysteries told in Iraqi
dialect**, as 45–60 s vertical motion videos with real photos. The owner does not want
to do any work: Claude proposes, the owner approves, Claude makes and schedules
everything. Talk to the owner in **Iraqi Arabic**, short and friendly.

## Files
- `stories/<NN>-<slug>.json` — one story: scenes, captions, hashtags, image queries.
- `template.html` — the motion design (driven by `window.seek(t)`); `render.js` renders it.
- `fetch_images.py` — downloads a photo for every scene that has `img` + `q`
  (Wikimedia Commons first, Openverse fallback; credits go to `images/<story>/CREDITS.txt`).
- `publish.py` — puts a rendered video in `ready/` + `ready/index.json` with the next free
  slot (Baghdad 14:37 and 20:37). The owner's PC runs **autopost**, which polls
  `ready/index.json` on this branch every 10 min and posts at that time with that caption.
- `ideas/used.txt` — every story already made (never repeat one).
- `FLOW.md` / `GEMINI.md` — on the owner's PC (Claude in Chrome) make AI video clips with Flow and
  images / clips / music with Gemini, using the owner's subscriptions. A scene with
  `"clip": "clips/<story>/<file>.mp4"` plays that clip under the whole scene.

## Daily run (a scheduled task starts a fresh session every day)
1. **Propose one idea** — read `ideas/used.txt`, pick a NEW story. Mostly real, well-documented
   events (mysteries, survivals, crazy history, Iraqi/Arab history every ~3rd day). Fiction or
   urban legends are allowed only when told as legends. Write to the owner, in Iraqi:
   the title, the hook (first line), 6–10 scene bullet points, the photos you plan to use,
   and "تريدني أسويها؟". Then **stop and wait** for the reply. Do not render before approval.
   If the owner wants changes, adjust and ask again.
2. **After "موافق"/approval**:
   - Write `stories/<next NN>-<slug>.json` (copy the shape of an existing one). Scene types:
     `hook`, `text`, `big` (year/number; `count` animates 0→N), `emoji`, `cta`.
     `*word*` highlights a word. Photo scenes: `img` + `q` (English Commons search) and
     optionally `file` (exact `File:...` on Commons), `imgStyle: "card"` for a framed photo.
     Use 3–5 photos per video, alternating with pure-motion scenes.
   - Facts must be correct. Hedge anything uncertain ("يكولون", "حسب الروايات").
   - `python3 fetch_images.py stories/<name>.json` (Wikimedia rate-limits: it waits; be patient).
     **Look at every downloaded image** (Read the jpg). Delete wrong/ugly ones, change `q`
     or set `file`, re-run. A slot with no file renders as motion only.
   - Narration: every scene has `say` = what the narrator speaks (clear Arabic, fuller than the
     on-screen `lines`). `python3 narrate.py stories/<name>.json` makes the voice (Gemini TTS,
     key injected by the proxy) and sets each scene's `dur`/`wordGap` to follow the voice.
     Listen to one scene first (`--scene 0`, then `node render.js ... --first 1`).
   - `node render.js stories/<name>.json --preview` → look at `out/<name>-p*.jpg`, fix
     overlaps or long lines, then `node render.js stories/<name>.json` (~5 min).
   - Title + caption: `title` = short hook; `caption` = 2 lines in Iraqi + a question for
     comments, blank line, then hashtags:
     `#قصص #قصص_حقيقية #معلومات #حقائق #غموض #العراق #عراقي #explore #fyp #shorts`
     plus 2–3 topic tags.
   - `python3 publish.py <name>`, append the story to `ideas/used.txt`, commit
     (`out/` is ignored), `git push origin qisas`.
   - Tell the owner in one or two lines: the posting day/time and that autopost will post it.
3. If nothing is approved that day, do nothing else.

## Rules
- **Sound: never use whoosh / swish / impact / boom / riser transition effects** in any video
  (stories, promos, edits): the owner finds them very annoying. Use music + voice + only quiet,
  on-topic ambience (sfx/<topic>). Do not re-edit a delivered video because of a note like this
  unless the owner asks; apply it to the next videos.
- Never post or copy other creators' videos. Photos: Commons / CC licences, or our own AI shots
  from Flow/Gemini for atmosphere only (never fake photos of real people or events).
- Keep `ready/` small: delete videos whose time passed more than 7 days ago (keep their index entries).
- Requirements in a fresh container: Chromium + Playwright are preinstalled; ffmpeg present;
  Python Pillow present. Network: upload.wikimedia.org, commons.wikimedia.org, api.openverse.org.
