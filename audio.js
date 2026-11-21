// usage: node audio.js stories/01-onoda.json [video.mp4]
// Builds the sound bed (dark pad + clock ticks + boom/whoosh on every scene cut) and puts it
// on the video (video stream is copied, nothing is re-rendered). Mixed for phone speakers:
// most energy is between 200 Hz and 4 kHz, loudness normalised to -14 LUFS.
const { chromium } = require('playwright');
const { execFileSync } = require('child_process');
const fs = require('fs'), path = require('path');

async function timing(story) {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
  await page.addInitScript(s => { window.STORY = s; }, story);
  await page.goto('file://' + path.join(__dirname, 'template.html'));
  await page.evaluate(() => window.READY);
  const r = await page.evaluate(() => ({ total: window.TOTAL, cuts: window.CUTS }));
  await browser.close();
  return r;
}

function addAudio(video, total, cuts, out) {
  const T = total.toFixed(2);
  // A-minor pad with harmonics (audible on phones), slowly breathing
  const pad = `aevalsrc='(0.5+0.5*sin(2*PI*0.08*t))*(` +
    `0.20*sin(2*PI*220*t)+0.16*sin(2*PI*261.6*t)+0.16*sin(2*PI*329.6*t)+0.10*sin(2*PI*440*t)` +
    `+0.06*sin(2*PI*659.3*t+sin(2*PI*0.3*t))+0.08*sin(2*PI*110*t))':s=44100:d=${T}`;
  // clock tick every second (suspense)
  const tick = `aevalsrc='0.5*sin(2*PI*2200*t)*exp(-90*mod(t,1))+0.3*sin(2*PI*1400*t)*exp(-120*mod(t+0.5,1))*0.6':s=44100:d=${T}`;
  const inputs = ['-f', 'lavfi', '-i', pad, '-f', 'lavfi', '-i', tick];
  let filt = '[1]lowpass=f=2500,volume=0.55[pad];[2]highpass=f=900,volume=0.18[tick];';
  const hits = [];
  cuts.forEach((c, i) => {
    // boom with a punchy mid harmonic + short noise whoosh
    inputs.push('-f', 'lavfi', '-i',
      `aevalsrc='0.9*sin(2*PI*(70+300*exp(-12*t))*t)*exp(-4*t)+0.35*sin(2*PI*(180+500*exp(-15*t))*t)*exp(-6*t)+0.5*(random(0)*2-1)*exp(-9*t)':s=44100:d=1.4`);
    const ms = Math.max(0, Math.round(c * 1000 - 60));
    filt += `[${3 + i}]highpass=f=60,adelay=${ms}|${ms},volume=0.7[h${i}];`;
    hits.push(`[h${i}]`);
  });
  filt += `[pad][tick]${hits.join('')}amix=inputs=${2 + hits.length}:normalize=0,` +
    `afade=t=in:d=0.6,afade=t=out:st=${(total - 1.5).toFixed(2)}:d=1.5,` +
    `loudnorm=I=-14:TP=-1.5:LRA=11,aformat=channel_layouts=stereo[aout]`;
  const tmp = out + '.tmp.mp4';
  execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-i', video, ...inputs, '-filter_complex', filt,
    '-map', '0:v', '-map', '[aout]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k', '-ar', '44100',
    '-shortest', '-movflags', '+faststart', tmp]);
  fs.renameSync(tmp, out);
}

module.exports = { timing, addAudio };

if (require.main === module) {
  (async () => {
    const file = process.argv[2];
    const name = path.basename(file, '.json');
    const story = JSON.parse(fs.readFileSync(file, 'utf8'));
    const video = process.argv[3] || path.join(__dirname, 'out', `${name}.mp4`);
    const { total, cuts } = await timing(story);
    addAudio(video, total, cuts, video);
    console.log(`${name}: sound done -> ${video}`);
  })();
}
