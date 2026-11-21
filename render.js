// usage: node render.js stories/01-onoda.json [--preview] [--first N]
// Renders a story JSON into a 1080x1920 MP4 (30fps) with an ambient sound bed.
const { chromium } = require('playwright');
const { spawn, execFileSync } = require('child_process');
const fs = require('fs'), path = require('path');

const FPS = 30;
const file = process.argv[2];
const preview = process.argv.includes('--preview');
const story = JSON.parse(fs.readFileSync(file, 'utf8'));
const only = process.argv.includes('--first') ? +process.argv[process.argv.indexOf('--first') + 1] : 0;
if (only) story.scenes = story.scenes.slice(0, only);   // quick sample: only the first N scenes
const name = path.basename(file, '.json') + (only ? `-first${only}` : '');
for (const sc of story.scenes) {
  if (sc.img && !fs.existsSync(path.join(__dirname, sc.img))) { console.log('missing image, motion only:', sc.img); delete sc.img; }
  if (sc.imgs) sc.imgs = sc.imgs.filter(f => fs.existsSync(path.join(__dirname, f)));
}
const outDir = path.join(__dirname, 'out');
fs.mkdirSync(outDir, { recursive: true });

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  await page.addInitScript(s => { window.STORY = s; }, story);
  await page.goto('file://' + path.join(__dirname, 'template.html'));
  await page.evaluate(() => window.READY);
  const total = await page.evaluate(() => window.TOTAL);
  const cuts = await page.evaluate(() => window.CUTS);
  const beats = await page.evaluate(() => window.BEATS || []);

  if (preview) {
    for (const [i, c] of cuts.entries()) {
      await page.evaluate(t => window.seek(t), c + 2.2);
      await page.screenshot({ path: path.join(outDir, `${name}-p${i}.jpg`), type: 'jpeg', quality: 80 });
    }
    await browser.close();
    console.log('preview frames written; total', total.toFixed(1), 's');
    return;
  }

  // parallel: split the frames over several browser pages, encode each part, then join
  const silent = path.join(outDir, `${name}.silent.mp4`);
  const frames = Math.ceil(total * FPS);
  const W = Math.max(1, +(process.argv.includes('--workers') ? process.argv[process.argv.indexOf('--workers') + 1] : 4));
  const per = Math.ceil(frames / W);
  let done = 0;
  const part = async (k) => {
    const a = k * per, b = Math.min(frames, a + per);
    const pg = k === 0 ? page : await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
    if (k) { await pg.addInitScript(s => { window.STORY = s; }, story);
      await pg.goto('file://' + path.join(__dirname, 'template.html')); await pg.evaluate(() => window.READY); }
    const seg = path.join(outDir, `${name}.part${k}.mp4`);
    const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-',
      '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '21', '-pix_fmt', 'yuv420p', seg], { stdio: ['pipe', 'inherit', 'inherit'] });
    for (let f = a; f < b; f++) {
      await pg.evaluate(t => window.seek(t), f / FPS);
      const buf = await pg.screenshot({ type: 'jpeg', quality: 90 });
      if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
      if (++done % 150 === 0) process.stdout.write(`\r${name}: ${done}/${frames}`);
    }
    ff.stdin.end();
    await new Promise(r => ff.on('close', r));
    return seg;
  };
  const segs = await Promise.all([...Array(W).keys()].map(part));
  await browser.close();
  const list = path.join(outDir, `${name}.parts.txt`);
  fs.writeFileSync(list, segs.map(f => `file '${f}'`).join('\n'));
  execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', list, '-c', 'copy', '-movflags', '+faststart', silent]);
  for (const f of segs) fs.unlinkSync(f); fs.unlinkSync(list);

  const out = path.join(outDir, `${name}.mp4`);
  require('./audio').addAudio(silent, total, cuts, out, story.scenes, beats, story);
  fs.unlinkSync(silent);
  console.log(`\r${name}: done ${total.toFixed(1)}s -> ${out}`);
})();
