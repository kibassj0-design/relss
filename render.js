// usage: node render.js stories/01-onoda.json [--preview]
// Renders a story JSON into a 1080x1920 MP4 (30fps) with an ambient sound bed.
const { chromium } = require('playwright');
const { spawn, execFileSync } = require('child_process');
const fs = require('fs'), path = require('path');

const FPS = 30;
const file = process.argv[2];
const preview = process.argv.includes('--preview');
const story = JSON.parse(fs.readFileSync(file, 'utf8'));
const name = path.basename(file, '.json');
for (const sc of story.scenes) if (sc.img && !fs.existsSync(path.join(__dirname, sc.img))) { console.log('missing image, motion only:', sc.img); delete sc.img; }
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

  if (preview) {
    for (const [i, c] of cuts.entries()) {
      await page.evaluate(t => window.seek(t), c + 2.2);
      await page.screenshot({ path: path.join(outDir, `${name}-p${i}.jpg`), type: 'jpeg', quality: 80 });
    }
    await browser.close();
    console.log('preview frames written; total', total.toFixed(1), 's');
    return;
  }

  const silent = path.join(outDir, `${name}.silent.mp4`);
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-',
    '-c:v', 'libx264', '-preset', 'medium', '-crf', '22', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', silent],
    { stdio: ['pipe', 'inherit', 'inherit'] });
  const frames = Math.ceil(total * FPS);
  for (let f = 0; f < frames; f++) {
    await page.evaluate(t => window.seek(t), f / FPS);
    const buf = await page.screenshot({ type: 'jpeg', quality: 92 });
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if (f % 150 === 0) process.stdout.write(`\r${name}: ${f}/${frames}`);
  }
  ff.stdin.end();
  await new Promise(r => ff.on('close', r));
  await browser.close();

  // ---- ambient bed: low drone + soft noise + a hit on every scene change ----
  const T = total.toFixed(2);
  const inputs = ['-f', 'lavfi', '-i', `sine=f=55:d=${T}`, '-f', 'lavfi', '-i', `sine=f=82.4:d=${T}`,
    '-f', 'lavfi', '-i', `anoisesrc=c=pink:d=${T}:a=0.25`];
  let filt = '[1]volume=0.35,tremolo=f=0.15:d=0.6[a0];[2]volume=0.18,tremolo=f=0.11:d=0.7[a1];[3]lowpass=f=500,volume=0.25[a2];';
  const hits = [];
  cuts.forEach((c, i) => {
    inputs.push('-f', 'lavfi', '-i', `aevalsrc='0.9*sin(2*PI*(45+60*exp(-8*t))*t)*exp(-3.5*t)':d=1.6`);
    const ms = Math.round(c * 1000);
    filt += `[${4 + i}]adelay=${ms}|${ms},volume=0.55[h${i}];`;
    hits.push(`[h${i}]`);
  });
  filt += `[a0][a1][a2]${hits.join('')}amix=inputs=${3 + hits.length}:normalize=0,lowpass=f=4000,` +
    `afade=t=in:d=1,afade=t=out:st=${(total - 1.5).toFixed(2)}:d=1.5,alimiter=limit=0.8,aformat=channel_layouts=stereo[aout]`;
  const out = path.join(outDir, `${name}.mp4`);
  execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-i', silent, ...inputs, '-filter_complex', filt,
    '-map', '0:v', '-map', '[aout]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k', '-ar', '44100', '-shortest', out]);
  fs.unlinkSync(silent);
  console.log(`\r${name}: done ${total.toFixed(1)}s -> ${out}`);
})();
