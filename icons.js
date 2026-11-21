// "gi:helmet" -> gold line drawing (game-icons.net, CC BY 3.0), "flag:japan" -> flag (Twemoji, CC BY 4.0)
const sets = { gi: require('@iconify-json/game-icons/icons.json'), tw: require('@iconify-json/twemoji/icons.json') };
function svg(name) {
  let set, key;
  if (name.startsWith('gi:')) { set = sets.gi; key = name.slice(3); }
  else if (name.startsWith('flag:')) { set = sets.tw; key = 'flag-' + name.slice(5); }
  else return null;
  const ic = set.icons[key]; if (!ic) return null;
  const w = ic.width || set.width || 512, h = ic.height || set.height || 512;
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${w} ${h}" fill="currentColor">${ic.body}</svg>`;
}
function resolve(story) {
  for (const sc of story.scenes) if (sc.icons) sc.icons = sc.icons.map(ic => {
    const [g, cap] = Array.isArray(ic) ? ic : [ic, ''];
    const s = svg(g); if (g.includes(':') && !s) console.log('unknown icon', g);
    return [s || g, cap];
  });
  return story;
}
module.exports = { svg, resolve };
