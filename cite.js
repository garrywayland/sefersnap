/* SeferSnap citation helpers: pure text functions, no network.
 * Loaded by index.html as window.Cite; also require()-able in Node for tests.
 *
 * Every transform of the text sent to Sefaria's Linker keeps its length (characters are
 * replaced by spaces, never removed), so the Linker's offsets map straight back onto the
 * original text.
 */
(function (root) {
  'use strict';

  const NIKUD = /[֑-ֽֿ-ׇ]/g;
  const FINALS = { 'ך': 'כ', 'ם': 'מ', 'ן': 'נ', 'ף': 'פ', 'ץ': 'צ' };
  const BOUND_BEFORE = '(^|[\\s(\\[,.:;])';
  const BOUND_AFTER = '(?=[\\s,.:;)\\]]|$)';

  /** Same-length normalisation: Hebrew gershayim/geresh to ASCII quote marks. */
  function normMarks(s) {
    return s.replace(/״/g, '"').replace(/׳/g, "'");
  }

  /** Hebrew word tokens with their offsets in the text. */
  function tokenize(text) {
    const out = [];
    const re = /[א-ת][א-ת֑-ׇ"'׳״]*/g;
    let m;
    while ((m = re.exec(text))) {
      let t = m[0];
      // a closing quotation mark glued to a word, e.g. בשכבך״ (but keep ת"ר)
      if (/["״]$/.test(t) && (t.match(/["״]/g) || []).length === 1 && t.length > 2) t = t.slice(0, -1);
      out.push({ t, s: m.index, e: m.index + t.length });
    }
    return out;
  }

  /** Plain form of a token: no nikud, ASCII quote marks. */
  function plain(t) {
    return normMarks(String(t).replace(NIKUD, ''));
  }

  /** Spelling-insensitive key: letters only, final forms, internal ו/י dropped, divine names unified. */
  function key(t) {
    const p = plain(t);
    if (/^(ה'|יהוה|יקוק|ד'|יי|ה'')$/.test(p)) return '@@@';
    const letters = p.replace(/[^א-ת]/g, '').replace(/[ךםןףץ]/g, (c) => FINALS[c]);
    return letters ? letters[0] + letters.slice(1).replace(/[וי]/g, '') : '';
  }

  // ------------------------------------------------------------------ ד"ה
  const DH_RE = new RegExp(BOUND_BEFORE + '([ובל]?ד"ה|דיבור המתחיל)(?=\\s)', 'g');
  const DH_STOP = new Set(["וכו'", "כו'", "וגו'", 'וכו', 'כו']);

  /** Find each ד"ה and the words of its dibbur hamaschil. */
  function findDH(text) {
    const t = normMarks(text);
    const toks = tokenize(t);
    const out = [];
    let m;
    DH_RE.lastIndex = 0;
    while ((m = DH_RE.exec(t))) {
      const start = m.index + m[1].length;
      const markEnd = start + m[2].length;
      const words = [];
      let end = markEnd;
      for (const tk of toks) {
        if (tk.s < markEnd) continue;
        if (/^[ובל]?ד"ה$/.test(plain(tk.t))) break;
        end = tk.e;
        if (DH_STOP.has(plain(tk.t))) break;
        words.push(tk.t);
        const after = t[tk.e] || '';
        if (/[.,:;)\]]/.test(after) || words.length >= 7) break;   // a comma ends a ד"ה too
      }
      if (words.length) out.push({ start, end, words });
    }
    return out;
  }

  // ------------------------------------------------------------------ Linker preparation
  // The Linker fails on "המג"א" etc. but resolves "מג"א": blank the leading (ו)ה.
  const H_PREFIXED = ['מג"א', 'ט"ז', 'ש"ך', 'ב"ח', 'ב"י', 'ד"מ', 'פמ"ג', 'מ"ב', 'פר"ח', 'ח"מ'];
  const H_PREFIX_RE = new RegExp(BOUND_BEFORE + '(ו?ה)(?=(?:' + H_PREFIXED.join('|') + ')' + BOUND_AFTER + ')', 'g');

  /**
   * Text to send to the Linker, same length as the original:
   *  - gershayim/geresh as ASCII marks,
   *  - every ד"ה and its dibbur hamaschil blanked (the Linker rejects the whole citation otherwise),
   *  - the ה prefix blanked on abbreviations the Linker only knows without it.
   */
  function prepareForLinker(text) {
    const chars = normMarks(text).split('');
    const dhs = findDH(text);
    for (const d of dhs) for (let i = d.start; i < d.end; i++) chars[i] = ' ';
    const t = chars.join('');
    let out = t.replace(H_PREFIX_RE, (all, before, pre) => before + ' '.repeat(pre.length));
    return { linkText: out, dhs };
  }

  // ------------------------------------------------------------------ refs
  const COMMENTARY_RE = /^(.+?) on (.+)$/;
  /** "Tosafot on Bava Metzia 59b:3:1" -> {commentator:'Tosafot', base:'Bava Metzia 59b'} */
  function splitCommentary(ref) {
    const m = COMMENTARY_RE.exec(ref || '');
    if (!m) return null;
    const base = m[2].replace(/:.*$/, '');
    return { commentator: m[1], base, section: `${m[1]} on ${base}` };
  }
  /** Talmud daf in a ref, e.g. "Bava Metzia 59b" from "Bava Metzia 59b:4" or "Rashi on Bava Metzia 59b". */
  function dafOf(ref) {
    const c = splitCommentary(ref);
    const r = c ? c.base : String(ref || '').replace(/:.*$/, '');
    return /^[A-Z][A-Za-z' ]+ \d+[ab]$/.test(r) ? r : null;
  }
  /** Book part of a ref: everything before the trailing section numbers. */
  function bookOf(ref) {
    return String(ref || '').replace(/\s[\d:ab\-–.]+$/, '');
  }

  // Commentators on the daf that are cited as "<name> ד"ה ..." with the daf implied.
  const DAF_COMMENTATORS = { 'רש"י': 'Rashi', 'רשי': 'Rashi', "תוס'": 'Tosafot', 'תוספות': 'Tosafot', 'תוס': 'Tosafot', 'רשב"ם': 'Rashbam' };
  function commentatorOf(tok) {
    const p = plain(tok);
    for (const pre of ['', 'ו', 'ב', 'וב', 'ה', 'וה', 'ל']) {
      if (p.startsWith(pre) && DAF_COMMENTATORS[p.slice(pre.length)]) return DAF_COMMENTATORS[p.slice(pre.length)];
    }
    return null;
  }

  /**
   * Work out which commentary section a ד"ה belongs to.
   * items: resolved citations so far, sorted, each {start,end,refs}.
   * Returns {item?, section} where item is the citation the ד"ה extends, if any.
   */
  function sectionForDH(text, dh, items) {
    const before = items.filter((x) => x.refs && x.refs.length && x.end <= dh.start).sort((a, b) => a.end - b.end);
    const last = before[before.length - 1];
    // 1. A citation ending right before the ד"ה, e.g. "תוס' ב"מ נט ע"ב ד"ה ..."
    if (last && /^[\s,.:;]*$/.test(normMarks(text.slice(last.end, dh.start)))) {
      const c = splitCommentary(last.refs[0]);
      if (c) return { item: last, section: c.section };
    }
    // 2. A commentator name just before, with the daf implied: "ובתוס' ד"ה ...", "ורש"י שם ד"ה ..."
    const toks = tokenize(text.slice(Math.max(0, dh.start - 40), dh.start)).slice(-3);
    for (let i = toks.length - 1; i >= 0; i--) {
      const comm = commentatorOf(toks[i].t);
      if (!comm) continue;
      for (let k = before.length - 1; k >= 0; k--) {
        const daf = dafOf(before[k].refs[0]);
        if (daf) return { item: null, section: `${comm} on ${daf}`, nameStart: dh.start - 40 + toks[i].s };
      }
    }
    return null;
  }

  /**
   * Match dibbur hamaschil words against a commentary section's text (Sefaria "he": nested list).
   * Returns {seg, idx, score, head, body} or null.
   */
  function matchDH(he, words) {
    const want = words.map(key).filter(Boolean);
    if (!want.length) return null;
    let best = null;
    const segs = Array.isArray(he) ? he : [he];
    segs.forEach((seg, i) => {
      const comments = Array.isArray(seg) ? seg : [seg];
      comments.forEach((c, j) => {
        if (!c || typeof c !== 'string') return;
        const body = c.replace(/<[^>]*>/g, '').replace(/\s+/g, ' ').trim();
        const dash = body.search(/\s[-–—]\s/);
        const head = dash > 0 && dash < 250 ? body.slice(0, dash) : body.slice(0, 120);
        const hk = tokenize(head).map((x) => key(x.t));
        let k = 0;
        for (const h of hk) if (k < want.length && h === want[k]) k++;
        const score = k / want.length;
        if (!best || score > best.score) best = { seg: i + 1, idx: Array.isArray(seg) ? j + 1 : null, score, head, body };
      });
    });
    const need = want.length === 1 ? 1 : 0.6;
    return best && best.score >= need ? best : null;
  }

  // ------------------------------------------------------------------ pointers
  const POINTERS = ['עיי"ש', 'ע"ש', "עי' שם", 'עיין שם', 'ועיין שם', 'הנ"ל', "הנז'", 'כנ"ל', 'וכנ"ל', 'הנזכר'];
  const POINTER_RE = new RegExp(BOUND_BEFORE + '(ו?(?:' + POINTERS.map((p) => p.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|') + '))' + BOUND_AFTER, 'g');
  const AUTHOR_PREFIX = {
    'רש"י': 'Rashi', "תוס'": 'Tosafot', 'תוספות': 'Tosafot', 'הרמב"ם': 'Mishneh Torah', 'רמב"ם': 'Mishneh Torah',
    'הרמב"ן': 'Ramban', 'הרא"ש': 'Rosh', 'הרשב"א': 'Rashba', 'הר"ן': 'Ran', 'הריטב"א': 'Ritva', 'הטור': 'Tur',
    'הב"י': 'Beit Yosef', 'המג"א': 'Magen Avraham', 'מג"א': 'Magen Avraham', 'הט"ז': 'Turei Zahav', 'הש"ך': 'Siftei Kohen',
  };
  const MAX_POINTER_DISTANCE = 300; // characters back to the citation a pointer can refer to

  /**
   * Pointers (ע"ש, הנ"ל, …) outside existing citations, resolved to the citation they refer to.
   * Returns [{start,end,text,target}] where target is an item from `items`.
   */
  function findPointers(text, items) {
    const t = normMarks(text);
    const out = [];
    const resolved = items.filter((x) => x.refs && x.refs.length && !x.failed);
    let m;
    POINTER_RE.lastIndex = 0;
    while ((m = POINTER_RE.exec(t))) {
      const start = m.index + m[1].length, end = start + m[2].length;
      if (items.some((x) => start < x.end && end > x.start)) continue;
      const prev = resolved.filter((x) => x.end <= start);
      if (!prev.length) continue;
      let target = null;
      // "הרשב"א הנ"ל": the last citation of that author
      const tokBefore = tokenize(t.slice(Math.max(0, start - 20), start)).pop();
      const author = tokBefore && (AUTHOR_PREFIX[plain(tokBefore.t)] || AUTHOR_PREFIX[plain(tokBefore.t).replace(/^ו/, '')]);
      if (author) target = [...prev].reverse().find((x) => x.refs[0].startsWith(author)) || null;
      if (!target) {
        const last = prev[prev.length - 1];
        if (start - last.end <= MAX_POINTER_DISTANCE) target = last;
      }
      if (target) out.push({ start, end, text: text.slice(start, end), target });
    }
    return out;
  }

  /** For an ibid-style Linker result with several candidates, prefer one in the same book as the previous citation. */
  function preferContext(refs, prevRef) {
    if (!refs || refs.length < 2 || !prevRef) return refs;
    const pb = bookOf(splitCommentary(prevRef) ? splitCommentary(prevRef).base : prevRef);
    const i = refs.findIndex((r) => bookOf(splitCommentary(r) ? splitCommentary(r).base : r) === pb);
    return i > 0 ? [refs[i], ...refs.filter((_, k) => k !== i)] : refs;
  }

  // ------------------------------------------------------------------ quotations
  const QUOTE_FORMULAS = {
    tanakh: ['שנאמר', "שנא'", "שנ'", 'דכתיב', "דכתי'", "דכת'", 'כדכתיב', "כדכתי'", 'וכתיב', "וכתי'", 'והכתיב', 'כתיב',
             'ונאמר', 'ואומר', 'שכתוב', 'ככתוב', 'כאמרו', 'ת"ל', 'קרא', 'הכתוב'],
    mishnah: ['תנן', 'דתנן', 'כדתנן', 'ותנן', 'והתנן', 'שנינו', 'תנינא'],
    baraita: ['תניא', 'דתניא', 'כדתניא', 'ותניא', 'והתניא', 'ת"ר', 'תנו רבנן', 'תני', 'ותני'],
  };
  const TWO_WORD = { 'תלמוד לומר': 'tanakh', 'תנו רבנן': 'baraita', 'אמר קרא': 'tanakh' };
  const QUOTE_FILTERS = { tanakh: ['Tanakh'], mishnah: ['Mishnah'], baraita: ['Tosefta', 'Midrash'] };
  const QUOTE_END = new Set(["וגו'", "וכו'", "כו'", 'וגו', 'וכו']);
  const FORMULA_CAT = {};
  for (const [cat, list] of Object.entries(QUOTE_FORMULAS)) for (const f of list) FORMULA_CAT[f] = cat;

  /**
   * Places where a formula introduces a quotation outside existing citations.
   * Returns [{start, end, formula, cat, words, query}] (start..end covers formula + quoted words).
   */
  function findQuoteCandidates(text, items, maxWords = 6) {
    const toks = tokenize(text);
    const out = [];
    for (let i = 0; i < toks.length; i++) {
      const p = plain(toks[i].t);
      let cat = FORMULA_CAT[p], skip = 1;
      if (i + 1 < toks.length && TWO_WORD[p + ' ' + plain(toks[i + 1].t)]) { cat = TWO_WORD[p + ' ' + plain(toks[i + 1].t)]; skip = 2; }
      if (!cat) continue;
      const words = [];
      let end = toks[i + skip - 1].e;
      for (let k = i + skip; k < toks.length && words.length < maxWords; k++) {
        const w = plain(toks[k].t);
        if (QUOTE_END.has(w)) break;
        if (FORMULA_CAT[w]) break;           // the next formula starts
        words.push(w.replace(/["']/g, ''));
        end = toks[k].e;
        if (/[.:;)\]׃]/.test(text[toks[k].e] || '')) break;
      }
      const letters = words.join('').length;
      if (words.length < 2 || letters < 6) continue;
      const qStart = toks[i + skip] ? toks[i + skip].s : end;
      if (items.some((x) => qStart < x.end && end > x.start)) continue;
      out.push({ start: toks[i].s, end, formula: text.slice(toks[i].s, toks[i + skip - 1].e), cat, words, query: words.join(' ') });
      i += skip - 1;
    }
    return out;
  }

  /** Pick the refs worth showing from search hits: near-best scores, at most `max` distinct refs. */
  function pickSearchHits(hits, max = 3) {
    const best = new Map();
    for (const h of hits || []) {
      const src = h._source || {};
      if (!src.ref) continue;
      const cur = best.get(src.ref);
      if (!cur || h._score > cur.score) {
        const hl = h.highlight && Object.values(h.highlight)[0];
        best.set(src.ref, { ref: src.ref, heRef: src.heRef || '', score: h._score || 0, snippet: hl ? String(hl[0]).replace(/<[^>]*>/g, '') : '' });
      }
    }
    const list = [...best.values()].sort((a, b) => b.score - a.score);
    if (!list.length) return { refs: [], ambiguous: false };
    const near = list.filter((x) => x.score >= list[0].score * 0.9);
    return near.length > max ? { refs: [], ambiguous: true, count: near.length } : { refs: near, ambiguous: false };
  }

  const Cite = {
    normMarks, tokenize, plain, key, findDH, prepareForLinker, splitCommentary, dafOf, bookOf,
    sectionForDH, matchDH, findPointers, preferContext, findQuoteCandidates, pickSearchHits, QUOTE_FILTERS,
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = Cite;
  else root.Cite = Cite;
})(typeof window !== 'undefined' ? window : globalThis);
