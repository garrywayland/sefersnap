// Live check of page identification against Sefaria (needs network).
// Builds a "scrambled" page by interleaving lines of a text and its commentaries,
// as OCR reading straight across the columns would, then identifies it.
// Run: node tests/live-identify.js   (behind a proxy: NODE_USE_ENV_PROXY=1)
const C = require('../cite.js');
const B = 'https://www.sefaria.org';
const plainText = (he) => (Array.isArray(he) ? he.flat(Infinity).join(' ') : String(he || ''))
  .replace(/<[^>]+>/g, ' ').replace(/[֑-ׇ]/g, '').replace(/\s+/g, ' ').trim();
async function text(ref, v) {
  const q = new URLSearchParams({ commentary: 0, context: 0, pad: 0 }); if (v) q.set('vhe', v);
  const r = await fetch(`${B}/api/texts/${encodeURIComponent(ref)}?${q}`); return plainText((await r.json()).he);
}
const lines = (t, w) => { const ws = t.split(' '); const o = []; for (let i = 0; i < ws.length; i += w) o.push(ws.slice(i, i + w).join(' ')); return o; };
async function search(q) {
  const filters = ['Talmud', 'Talmud Commentary', 'Halakhah', 'Mishnah', 'Mishnah Commentary'];
  const r = await fetch(`${B}/api/search-wrapper`, { method: 'POST', headers: { 'Content-Type': 'text/plain' },
    body: JSON.stringify({ query: q, type: 'text', field: 'naive_lemmatizer', slop: 1, size: 10, filters,
      filter_fields: filters.map(() => 'path'), source_proj: ['ref'] }) });
  return ((await r.json()).hits || {}).hits || [];
}
const CASES = [
  ['Shabbat 21b', [['Shabbat 21b', 'Wikisource Talmud Bavli', 9], ['Rashi on Shabbat 21b', null, 5], ['Tosafot on Shabbat 21b', null, 5]]],
  ['Bava Metzia 59b', [['Bava Metzia 59b', 'Wikisource Talmud Bavli', 9], ['Rashi on Bava Metzia 59b', null, 5], ['Tosafot on Bava Metzia 59b', null, 5]]],
  ['Shulchan Arukh, Orach Chayim 695', [['Shulchan Arukh, Orach Chayim 695', null, 9], ['Magen Avraham 695', null, 4], ['Turei Zahav on Shulchan Arukh, Orach Chayim 695', null, 4]]],
  ['Shulchan Arukh, Orach Chayim 695 (Mishnah Berurah page)', [['Shulchan Arukh, Orach Chayim 695', null, 9], ['Mishnah Berurah 695', null, 9], ['Biur Halacha 695', null, 5]]],
  ['Mishneh Torah, Sabbath 2', [['Mishneh Torah, Sabbath 2', null, 9], ['Maggid Mishneh on Mishneh Torah, Sabbath 2', null, 5]]],
  ['Mishnah Berakhot 1', [['Mishnah Berakhot 1', null, 9], ['Bartenura on Mishnah Berakhot 1', null, 5]]],
];
(async () => {
  let pass = 0;
  for (const [want, parts] of CASES) {
    const cols = await Promise.all(parts.map(async ([ref, v, w]) => lines(await text(ref, v), w).slice(0, 25)));
    const rows = []; for (let i = 0; i < 25; i++) rows.push(cols.map((c) => c[i] || '').join(' '));
    const probes = C.probeWindows(rows.join(' '), 20);
    const picks = [];
    for (let i = 0; i < probes.length; i += 4) picks.push(...await Promise.all(probes.slice(i, i + 4).map(async (q) => C.pickPageHit(await search(q)))));
    const v = C.votePage(picks);
    const ok = v.page && want.startsWith(v.page.key) && v.status !== 'unclear';
    pass += ok ? 1 : 0;
    console.log(`${ok ? 'PASS' : 'FAIL'} ${want}\n     -> ${v.status} ${v.page ? v.page.key : '-'} (${v.votes || 0} votes of ${v.hits} hits / ${v.probes} probes)` +
      `${v.runnerUp ? `, runner-up ${v.runnerUp.page.key} ${v.runnerUp.votes}` : ''}; texts: ${v.texts ? Object.entries(v.texts).map(([k, x]) => k + ' ' + x.refs.length).join(', ') : ''}`);
  }
  console.log(`${pass}/${CASES.length} identified`);
})();
