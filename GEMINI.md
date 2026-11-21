# Gemini (the owner's Pro subscription) — images, video clips, music

Runs on the owner's PC (Claude desktop app + Claude in Chrome), the same way as FLOW.md.
Use it when a story needs something Commons/Openverse can't give: atmosphere shots, b-roll,
a scene that has no real photo, a music bed. Flow (FLOW.md) stays the first choice for video;
Gemini video is the fallback when Flow is out of credits.

## How
1. In Chrome open https://gemini.google.com/app (the owner is signed in, plan "Pro").
2. Click **+** ("التحميل والأدوات") next to the prompt box and pick the tool:
   - **إنشاء صورة** — image. Set "نسبة العرض إلى الارتفاع" to 9:16 (or write "Vertical 9:16" in the
     prompt). Result is about 1536x2752.
   - **إنشاء فيديو** — Veo video, portrait 9:16, 8 s. Same prompt rules as `flow/<story>.json`.
   - **إنشاء موسيقى** — short music track (instrumental, mood of the story, no vocals).
3. Write the prompt in English, end with "no text, no subtitles, no logos". Send, wait, then
   click the download icon on the result (top corner of the image/video, "full size").
4. The file lands in `~/Downloads` (`Gemini_Generated_Image_*.jfif|png`, videos `*.mp4`).
   Move it, never leave copies in Downloads:
   - image  -> `images/<story>/gem-<scene>.jpg` (convert jfif/png with ffmpeg), then set the
     scene's `img` (or add it to `imgs`) in `stories/<story>.json`
   - video  -> `clips/<story>/s<scene>.mp4`, then set the scene's `"clip"` (render.js plays it
     under the whole scene)
   - music  -> `sfx/music_<mood>/gem-<story>.mp3` and set the story's `"music": "music_<mood>"`
5. Commit with the story and `git push origin qisas`.

Voice is not made in the browser: `narrate.py` already uses Gemini TTS through the API
(`GEMINI_API_KEY` on the PC).

## Rules
- Never make fake "real photos" of real people or real events (no AI Onoda, no AI wreck
  photo). AI images/clips are for atmosphere and re-enactment-style shots only; real people
  stay Commons photos.
- Never type the owner's passwords; never change Gemini settings or the subscription.
- If Gemini asks to pay, to upgrade, or says the daily limit is reached: stop and tell the
  owner (in Iraqi), don't try another account.
