// Run: node tests/cite.test.js
const assert = require('assert');
const C = require('../cite.js');
let n = 0;
const t = (name, fn) => { fn(); n++; console.log('ok', name); };

t('prepareForLinker keeps length and blanks ד"ה', () => {
  const s = 'עיין תוס׳ ב״מ נט ע״ב ד״ה תנור וכו׳ ושם.';
  const p = C.prepareForLinker(s);
  assert.strictEqual(p.linkText.length, s.length);
  assert.ok(!p.linkText.includes('ד"ה'));
  assert.ok(p.linkText.includes('תוס\' ב"מ נט ע"ב'));
  assert.deepStrictEqual(p.dhs[0].words, ['תנור']);
});

t('ד"ה words stop at punctuation and at 7 words', () => {
  assert.deepStrictEqual(C.findDH('רש"י ד"ה פתילה ושמנים. ועוד')[0].words, ['פתילה', 'ושמנים']);
  assert.strictEqual(C.findDH('ד"ה א ב ג ד ה ו ז ח ט')[0].words.length, 7);
  assert.deepStrictEqual(C.findDH('תוס\' ד"ה תנור, ובתוס\' ד"ה נצחוני בני')[0].words, ['תנור']);
});

t('ה prefix blanked on מג"א / ט"ז / ש"ך only', () => {
  const s = 'והמג"א סי\' א והט"ז שם והרמב"ם';
  const p = C.prepareForLinker(s).linkText;
  assert.strictEqual(p.length, s.length);
  assert.ok(p.startsWith('  מג"א'));
  assert.ok(p.includes('  ט"ז'));
  assert.ok(p.includes('והרמב"ם'));
});

t('sectionForDH: citation right before', () => {
  const s = 'תוס\' ב"מ נט ע"ב ד"ה תנור';
  const dh = C.findDH(s)[0];
  const items = [{ start: 0, end: 15, refs: ['Tosafot on Bava Metzia 59b'] }];
  assert.strictEqual(C.sectionForDH(s, dh, items).section, 'Tosafot on Bava Metzia 59b');
});

t('sectionForDH: implied daf from an earlier citation', () => {
  const s = 'בב"מ נט ע"ב. ובתוס\' ד"ה תנור';
  const dh = C.findDH(s)[0];
  const items = [{ start: 0, end: 11, refs: ['Bava Metzia 59b'] }];
  assert.strictEqual(C.sectionForDH(s, dh, items).section, 'Tosafot on Bava Metzia 59b');
});

t('sectionForDH: uses the nearest citation even if items are unsorted', () => {
  const s = 'תוס\' ב"מ נט ע"ב ד"ה תנור. וברש"י שבת כא ע"ב ד"ה גירסא';
  const dh = C.findDH(s)[1];
  const items = [{ start: 30, end: 47, refs: ['Rashi on Shabbat 21b'] }, { start: 0, end: 25, refs: ['Tosafot on Bava Metzia 59b:1:1'] }];
  items[0].end = dh.start - 1;
  assert.strictEqual(C.sectionForDH(s, dh, items).section, 'Rashi on Shabbat 21b');
});

t('matchDH finds the comment by its dibbur hamaschil', () => {
  const he = [['זה תנור של עכנאי - יש דגרס'], [], [], [], ['לא בשמים היא - והא דאמר', 'קחייך ואמר נצחוני בני - והא']];
  const m = C.matchDH(he, ['נצחוני', 'בני']);
  assert.deepStrictEqual([m.seg, m.idx], [5, 2]);
  assert.strictEqual(C.matchDH(he, ['תנור']).seg, 1);
  assert.strictEqual(C.matchDH(he, ['שמש', 'ירח']), null);
});

t('pointers resolve to the previous citation, or the named author', () => {
  const s = 'הרשב"א ב"מ נט ע"ב, ורש"י שבת כא ע"ב. ועיין שם. והרשב"א הנ"ל';
  const items = [{ start: 0, end: 17, refs: ['Rashba on Bava Metzia 59b'] }, { start: 19, end: 35, refs: ['Rashi on Shabbat 21b'] }];
  const ps = C.findPointers(s, items);
  assert.strictEqual(ps.length, 2);
  assert.strictEqual(ps[0].target.refs[0], 'Rashi on Shabbat 21b');
  assert.strictEqual(ps[1].target.refs[0], 'Rashba on Bava Metzia 59b');
});

t('pointer ignored with no citation before it', () => {
  assert.strictEqual(C.findPointers('ע"ש בדבריו', []).length, 0);
});

t('preferContext puts the same-book candidate first', () => {
  assert.deepStrictEqual(C.preferContext(['Bava Kamma 72', 'Berakhot 3b'], 'Berakhot 2a'), ['Berakhot 3b', 'Bava Kamma 72']);
});

t('quote candidates after formulas, stopping at וגו\'', () => {
  const s = 'תנא אקרא קאי דכתיב בשכבך ובקומך וגו\'. ותנן מאימתי קורין את שמע בערבית.';
  const q = C.findQuoteCandidates(s, []);
  assert.strictEqual(q.length, 2);
  assert.deepStrictEqual([q[0].cat, q[0].query], ['tanakh', 'בשכבך ובקומך']);
  assert.strictEqual(q[1].cat, 'mishnah');
  assert.strictEqual(q[1].query, 'מאימתי קורין את שמע בערבית');
});

t('quote candidate skipped inside an existing citation', () => {
  const s = 'שנאמר בשכבך ובקומך';
  assert.strictEqual(C.findQuoteCandidates(s, [{ start: 6, end: 19 }]).length, 0);
});

t('pickSearchHits dedupes and flags ambiguity', () => {
  const h = (ref, sc) => ({ _source: { ref }, _score: sc });
  assert.deepStrictEqual(C.pickSearchHits([h('A', 10), h('A', 10), h('B', 9.5), h('C', 2)]).refs.map((x) => x.ref), ['A', 'B']);
  assert.ok(C.pickSearchHits([h('A', 10), h('B', 10), h('C', 10), h('D', 10)]).ambiguous);
});

t('dafOf / bookOf', () => {
  assert.strictEqual(C.dafOf('Rashi on Shabbat 21b:3:1'), 'Shabbat 21b');
  assert.strictEqual(C.dafOf('Mishneh Torah, Sabbath 2:1'), null);
  assert.strictEqual(C.bookOf('Shulchan Arukh, Orach Chayim 695:2'), 'Shulchan Arukh, Orach Chayim');
});
console.log(`\n${n} tests passed`);
