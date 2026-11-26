// usage: node audio.js stories/01-onoda.json [video.mp4]
// Sound design for a story video (the video stream is copied, nothing is re-rendered):
//   narration (each scene's voice at its cut)  +  a real music bed from sfx/music_*  +
//   NO whoosh/swish/impact/riser (the owner finds them annoying); a camera click on framed photos,
//   on hooks and big numbers, and each scene's own effects ("sfx": ["plane", "crowd", ...]).
// Every sound is a CC0 file from sfx/<category>/ (see sfx/CREDITS.txt). Loudness -14 LUFS.
const { chromium } = require('playwright');
const { execFileSync } = require('child_process');
const fs = require('fs'), path = require('path');

async function timing(story) {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
  await page.addInitScript(s => { window.STORY = s; }, story);
  await page.goto('file://' + path.join(__dirname, 'template.html'));
  await page.evaluate(() => window.READY);
  const r = await page.evaluate(() => ({ total: window.TOTAL, cuts: window.CUTS, beats: window.BEATS || [] }));
  await browser.close();
  return r;
}

// deterministic pick so the same story always sounds the same, but stories differ
function picker(seed) {
  let x = seed | 0;
  const rnd = () => { x = (x * 1103515245 + 12345) & 0x7fffffff; return x / 0x7fffffff; };
  const lists = {};
  const files = cat => {
    if (!lists[cat]) {
      const dir = path.join(__dirname, 'sfx', cat);
      lists[cat] = fs.existsSync(dir) ? fs.readdirSync(dir).filter(f => f.endsWith('.mp3')).map(f => path.join(dir, f)) : [];
    }
    return lists[cat];
  };
  let last = '';
  return cat => {             // never the same file twice in a row
    const l = files(cat); if (!l.length) return null;
    let f = l[Math.floor(rnd() * l.length)];
    if (f === last && l.length > 1) f = l[(l.indexOf(f) + 1) % l.length];
    return (last = f);
  };
}

function addAudio(video, total, cuts, out, scenes = [], beats = [], story = {}) {
  const pick = picker((story.seed || 7) * 7919);
  const inputs = [], parts = [];
  let k = 1;                                   // input 0 is the video
  const add = (file, opts = []) => { inputs.push(...opts, '-i', file); return k++; };
  const at = s => Math.max(0, Math.round(s * 1000));
  const place = (idx, start, vol, extra = '') => {
    const lab = `a${parts.length}`;
    parts.push({ f: `[${idx}]aresample=44100,aformat=channel_layouts=stereo${extra},volume=${vol},adelay=${at(start)}|${at(start)}[${lab}]`, lab });
  };
  const voiced = scenes.some(sc => sc.voice && fs.existsSync(path.join(__dirname, sc.voice)));

  // music bed (looped, faded, under the voice)
  const music = pick(story.music || 'music_mystery') || pick('music_dark') || pick('music_drone');
  if (music) {
    const i = add(music, ['-stream_loop', '-1']);
    place(i, 0, voiced ? 0.16 : 0.45, `,atrim=0:${total.toFixed(2)},afade=t=in:d=1.5,afade=t=out:st=${(total - 2.5).toFixed(2)}:d=2.5`);
  }
  // narration
  scenes.forEach((sc, s) => {
    if (sc.voice && fs.existsSync(path.join(__dirname, sc.voice)))
      place(add(path.join(__dirname, sc.voice)), cuts[s] + (sc.voiceLead || 0), 1.9);
  });
  // framed photos: a soft camera click
  beats.forEach((b, j) => {
    if (b.t < 0.05) return;
    if (b.kind === 'card') { const c = pick('shutter'); if (c) place(add(c), b.t + 0.05, 0.45, ',atrim=0:1'); }
  });
  // per scene: the scene's own effects
  scenes.forEach((sc, s) => {
    const st = cuts[s], dur = sc.dur || 3;
    for (const cat of sc.sfx || []) {
      const f = pick(cat); if (!f) continue;
      const len = Math.min(dur + 0.6, 12).toFixed(2);
      place(add(f), st, voiced ? 0.33 : 0.55, `,atrim=0:${len},afade=t=in:d=0.25,afade=t=out:st=${Math.max(0, len - 0.8).toFixed(2)}:d=0.8`);
    }
  });
  let filt = parts.map(p => p.f).join(';') + ';' + parts.map(p => `[${p.lab}]`).join('') +
    `amix=inputs=${parts.length}:normalize=0,atrim=0:${total.toFixed(2)},afade=t=out:st=${(total - 1.2).toFixed(2)}:d=1.2,` +
    `loudnorm=I=-14:TP=-1.5:LRA=11,aformat=channel_layouts=stereo[aout]`;
  const tmp = out + '.tmp.mp4';
  execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-i', video, ...inputs, '-filter_complex', filt,
    '-map', '0:v', '-map', '[aout]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-ar', '44100',
    '-t', total.toFixed(2), '-movflags', '+faststart', tmp], { maxBuffer: 1 << 26 });
  fs.renameSync(tmp, out);
}

module.exports = { timing, addAudio };

if (require.main === module) {
  (async () => {
    const file = process.argv[2];
    const name = path.basename(file, '.json');
    const story = JSON.parse(fs.readFileSync(file, 'utf8'));
    const video = process.argv[3] || path.join(__dirname, 'out', `${name}.mp4`);
    const { total, cuts, beats } = await timing(story);
    addAudio(video, total, cuts, video, story.scenes, beats, story);
    console.log(`${name}: sound done -> ${video}`);
  })();
}
