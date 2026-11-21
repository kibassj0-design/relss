# Flow clips (run on the owner's PC, Claude desktop app + Claude in Chrome)

For every file `flow/<story>.json` that has clips missing from `clips/<story>/`:
1. In Chrome open https://labs.google/fx/tools/flow (the owner is already signed in with Google).
2. Make a new project (or reuse "5ssj5"). For each clip: text-to-video, portrait 9:16, the
   prompt exactly as written + the "settings" line. Generate, wait, pick the best of the results.
3. Download it (720p is fine) and save it as `clips/<story>/<file>` in this repo.
4. When all clips of the story are saved: `git add clips && git commit -m "Flow clips <story>" && git push origin qisas`.
Rules: never type the owner's passwords anywhere; if Flow asks to pay or for more credits, stop and tell the owner.
