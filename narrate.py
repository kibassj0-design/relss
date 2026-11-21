"""Voice-over for a story: every scene's "say" text is spoken by Gemini TTS.

usage: python3 narrate.py stories/01-onoda.json [--scene N] [--voice Charon] [--force]

Writes out/voice/<story>/<i>.wav per scene (24 kHz mono), then sets on each scene
  dur       = voice length + a short breath  (so the picture follows the voice)
  wordGap   = seconds between on-screen word reveals, spread over the voice
  voice     = the wav path (audio.js mixes it in at the scene start)
and saves the story JSON. The API key is added by the network proxy (header
x-goog-api-key on generativelanguage.googleapis.com) - nothing is read from disk.
"""
import base64, json, os, sys, time, urllib.error, urllib.request, wave

ROOT = os.path.dirname(os.path.abspath(__file__))
MODELS = ["gemini-2.5-flash-preview-tts", "gemini-3.8-flash-tts", "gemini-3.1-flash-tts-preview"]
STYLE = ("اقرأ النص التالي بالعربية بصوت راوي قصص غامضة، هادئ وعميق، "
         "بإيقاع مشوّق ووقفات قصيرة عند النقاط: ")
LEAD, TAIL = 0.25, 0.55   # silence before the voice starts / after it ends, per scene


def tts(text, voice):
    body = {"contents": [{"parts": [{"text": STYLE + text}]}],
            "generationConfig": {"responseModalities": ["AUDIO"],
                                 "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}}}}
    last = None
    for model in MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        for attempt in range(4):
            req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=120) as r:
                    d = json.load(r)
                part = d["candidates"][0]["content"]["parts"][0]["inlineData"]
                return base64.b64decode(part["data"]), model
            except urllib.error.HTTPError as e:
                last = f"{model}: HTTP {e.code} {e.read()[:200]!r}"
                if e.code == 429:
                    time.sleep(20 * (attempt + 1)); continue
                break  # 401/403/404: try the next model
            except (KeyError, IndexError) as e:
                last = f"{model}: no audio in answer"; break
    raise RuntimeError(last)


def save_wav(pcm, path, rate=24000):
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate); w.writeframes(pcm)
    return len(pcm) / 2 / rate


def main():
    path = sys.argv[1]
    voice = sys.argv[sys.argv.index("--voice") + 1] if "--voice" in sys.argv else "Charon"
    only = int(sys.argv[sys.argv.index("--scene") + 1]) if "--scene" in sys.argv else None
    force = "--force" in sys.argv
    story = json.load(open(path, encoding="utf-8"))
    name = os.path.basename(path)[:-5]
    folder = os.path.join(ROOT, "out", "voice", name)
    os.makedirs(folder, exist_ok=True)
    for i, sc in enumerate(story["scenes"]):
        if only is not None and i != only:
            continue
        text = sc.get("say") or " ".join(sc.get("lines", [])).replace("*", "")
        wav = os.path.join(folder, f"{i}.wav")
        if force or not os.path.exists(wav):
            pcm, model = tts(text, voice)
            secs = save_wav(pcm, wav)
            print(f"  scene {i}: {secs:.1f}s ({model})")
        with wave.open(wav) as w:
            secs = w.getnframes() / w.getframerate()
        words = len(" ".join(sc.get("lines", [])).split())
        sc["voice"] = os.path.relpath(wav, ROOT)
        sc["voiceLead"] = LEAD
        sc["dur"] = round(LEAD + secs + TAIL, 2)
        sc["wordStart"] = LEAD
        sc["wordGap"] = round(max(0.12, min(0.45, secs * 0.8 / max(words, 1))), 3)
    json.dump(story, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
