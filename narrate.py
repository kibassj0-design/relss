"""Voice-over for a story: every scene's "say" is spoken by Gemini TTS (one request per
scene; if the free daily quota runs out it stops - run it again later, finished scenes are kept).

usage: python3 narrate.py stories/01-onoda.json [--voice Charon] [--force]

1. All scenes' "say" texts, one per line, are sent together -> out/voice/<story>/full.wav
2. Scene borders: each scene's expected start (by its share of the text) is snapped to the
   nearest pause in the voice.
3. Each scene clip has long pauses shortened (max ~0.35 s) -> out/voice/<story>/<i>.wav
4. Each scene gets dur / wordGap / voice so the picture follows the voice.
The API key is added by the network proxy (header x-goog-api-key); nothing is read from disk.
"""
import base64, json, os, re, subprocess, sys, time, urllib.error, urllib.request, wave

ROOT = os.path.dirname(os.path.abspath(__file__))
MODELS = ["gemini-3.8-flash-tts", "gemini-2.5-flash-preview-tts", "gemini-3.1-flash-tts-preview",
          "gemini-2.5-pro-preview-tts"]
STYLE = ""  # 3.8 TTS reads any instruction aloud: send the bare text
RATE = 24000
LEAD, TAIL = 0.15, 0.35   # silence before the voice starts / after it ends, per scene


def tts(text, voice):
    body = {"contents": [{"parts": [{"text": STYLE + text}]}],
            "generationConfig": {"responseModalities": ["AUDIO"],
                                 "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}}}}
    last = None
    for model in MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        for attempt in range(3):
            req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=300) as r:
                    d = json.load(r)
                part = d["candidates"][0]["content"]["parts"][0]["inlineData"]
                return base64.b64decode(part["data"]), model
            except urllib.error.HTTPError as e:
                msg = e.read()[:300]
                last = f"{model}: HTTP {e.code} {msg!r}"
                if e.code == 429 and b"per day" not in msg and b"PerDay" not in msg:
                    time.sleep(30 * (attempt + 1)); continue
                break  # daily quota / auth / not found: next model
            except (KeyError, IndexError):
                last = f"{model}: no audio in answer"; break
    raise RuntimeError(last)


def write_wav(path, pcm):
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(RATE); w.writeframes(pcm)


def read_pcm(path):
    with wave.open(path) as w:
        return w.readframes(w.getnframes())


def pauses(path, db=-35, dur=0.18):
    out = subprocess.run(["ffmpeg", "-hide_banner", "-i", path, "-af", f"silencedetect=n={db}dB:d={dur}",
                          "-f", "null", "-"], capture_output=True, text=True).stderr
    s = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", out)]
    e = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", out)]
    return list(zip(s, e))


def tighten(src, dst):
    """Shorten every pause to ~0.35 s and trim the ends."""
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-af",
                    "silenceremove=start_periods=1:start_threshold=-40dB:start_silence=0.05,"
                    "silenceremove=stop_periods=-1:stop_duration=0.35:stop_threshold=-40dB:stop_silence=0.3,"
                    "areverse,silenceremove=start_periods=1:start_threshold=-40dB:start_silence=0.05,areverse",
                    "-ar", str(RATE), "-ac", "1", dst], check=True)
    with wave.open(dst) as w:
        return w.getnframes() / w.getframerate()


def borders(texts, total, gaps):
    """Start time of every scene: proportional guess snapped to the nearest unused pause."""
    sizes = [len(t) for t in texts]
    acc, guess = 0, []
    for n in sizes[:-1]:
        acc += n
        guess.append(total * acc / sum(sizes))
    mids = [(a + b) / 2 for a, b in gaps]
    out, lo = [], 0
    for g in guess:
        cand = [(abs(m - g), j) for j, m in enumerate(mids) if j >= lo]
        if not cand:
            out.append(g); continue
        _, j = min(cand)
        out.append(mids[j]); lo = j + 1
    return [0.0] + out + [total]


ALIGN_MODELS = ["gemini-3.5-flash", "gemini-flash-latest", "gemini-3.8-flash", "gemini-3-flash-preview"]


def align(path, texts):
    """Ask Gemini (listening to the voice) when each line starts. None if it fails."""
    mp3 = path[:-4] + ".mp3"   # small upload
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", path, "-ac", "1", "-b:a", "48k", mp3], check=True)
    audio = base64.b64encode(open(mp3, "rb").read()).decode()
    lines = "\n".join(f"{i}: {t}" for i, t in enumerate(texts))
    prompt = ("This audio is an Arabic narration of the numbered lines below, read in order. "
              "For every line give the time in seconds when its first word starts. "
              'Answer only JSON: {"starts": [s0, s1, ...]} with exactly %d numbers.\n\n%s' % (len(texts), lines))
    body = {"contents": [{"parts": [{"inlineData": {"mimeType": "audio/mp3", "data": audio}}, {"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json", "temperature": 0}}
    for model in ALIGN_MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        try:
            req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=180) as r:
                d = json.load(r)
            st = json.loads(d["candidates"][0]["content"]["parts"][0]["text"])["starts"]
            st = [float(x) for x in st]
            if len(st) == len(texts) and all(a < b for a, b in zip(st, st[1:])):
                print(f"  aligned by {model}")
                return st
        except Exception as e:
            print(f"  align {model} failed: {str(e)[:80]}")
    return None


def snap(starts, total, gaps):
    """Move every scene start (except the first) to the middle of the nearest pause before it."""
    out = [0.0]
    for g in starts[1:]:
        before = [b for a, b in gaps if b <= g + 0.4 and b > out[-1] + 0.5]
        out.append(max(before, key=lambda b: -abs(b - g)) - 0.12 if before else g)
    return out + [total]


def word_times(wav, text, secs):
    """Time of every word inside a scene clip: the speech (between pauses) is shared out by
    word length, so pauses fall between words and every word lights up when it is spoken."""
    words = text.split()
    gaps = [(a, b) for a, b in pauses(wav, -38, 0.12) if b - a > 0.1 and a > 0.05 and b < secs - 0.05]
    segs, t = [], 0.0
    for a, b in gaps:
        segs.append((t, a)); t = b
    segs.append((t, secs))
    speech = sum(b - a for a, b in segs) or secs
    wts = [len(w.strip(".،,؟?!…:")) + 1.5 for w in words]
    total = sum(wts)

    def at(x):                      # speech-time -> clip time
        for a, b in segs:
            if x <= b - a + 1e-9:
                return a + x
            x -= b - a
        return secs
    out, x = [], 0.0
    for w in wts:
        d = speech * w / total
        out.append([round(at(x + 0.001), 3), round(at(x + d), 3)])
        x += d
    return out


def main():
    path = sys.argv[1]
    voice = sys.argv[sys.argv.index("--voice") + 1] if "--voice" in sys.argv else "Charon"
    force = "--force" in sys.argv
    story = json.load(open(path, encoding="utf-8"))
    name = os.path.basename(path)[:-5]
    folder = os.path.join(ROOT, "out", "voice", name)
    os.makedirs(folder, exist_ok=True)
    texts = [sc.get("say") or " ".join(sc.get("lines", [])).replace("*", "") for sc in story["scenes"]]
    for i, sc in enumerate(story["scenes"]):
        raw = os.path.join(folder, f"{i}.raw.wav")
        wav = os.path.join(folder, f"{i}.wav")
        if force or not os.path.exists(raw):
            try:
                pcm, model = tts(texts[i], voice)
            except RuntimeError as e:
                json.dump(story, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
                sys.exit(f"  stopped at scene {i} (quota?): {e}\n  run again later; done scenes are kept")
            write_wav(raw, pcm)
            print(f"  scene {i}: voiced by {model}")
        secs = tighten(raw, wav)
        words = len(" ".join(sc.get("lines", [])).split())
        sc["voice"] = os.path.relpath(wav, ROOT)
        sc["voiceLead"] = LEAD
        sc["dur"] = round(max(2.0, LEAD + secs + TAIL), 2)
        sc["wordStart"] = LEAD
        sc["wordGap"] = round(max(0.12, min(0.45, secs * 0.8 / max(words, 1))), 3)
        sc["wt"] = word_times(wav, texts[i], secs)
        print(f"  scene {i}: {secs:4.1f}s  {texts[i][:40]}")
    json.dump(story, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
