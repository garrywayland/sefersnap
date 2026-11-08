#!/usr/bin/env python3
"""Mine citation formulas and abbreviations from a hand-picked sample of seforim.

Reads tools/sample_units.json, fetches each page and its Sefaria links, finds where
each *earlier* linked text is quoted, records the words before the quote, and counts
every abbreviation (tokens with " or '). Writes data/formulas-sample.json and
docs/citation-formulas.md.

    python3 tools/mine_sample.py --cache /tmp/sefaria-cache
"""
import argparse, collections, concurrent.futures as cf, json, os, re, sys, urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mine_formulas import BASE, fetch_json, text_url, links_url, tokens, key, find_quote  # noqa: E402

SKIP_TYPES = {'commentary', 'mishnah in talmud', 'targum', 'translation'}
SKIP_CATS = {'Reference', 'Modern Commentary'}
# Sources whose words get quoted; later authors are cited by name, which the abbreviation lists capture.
QUOTE_CATS = {'Tanakh', 'Mishnah', 'Tosefta', 'Talmud', 'Midrash'}

# ------------------------------------------------------------ helpers
def first_year(cd):
    if isinstance(cd, list) and cd:
        cd = cd[0]
    if isinstance(cd, (int, float)):
        return cd
    m = re.search(r'-?\d+', str(cd or ''))
    return int(m.group()) if m else None

_index_cache = {}
def index_info(title, cache):
    if title not in _index_cache:
        d = fetch_json(f'{BASE}/api/v2/index/{urllib.parse.quote(title)}', cache) or {}
        _index_cache[title] = {'year': first_year(d.get('compDate')), 'he': d.get('heTitle', title)}
    return _index_cache[title]

def resolve_he(he, cache):
    d = fetch_json(f'{BASE}/api/name/{urllib.parse.quote(he)}?limit=10', cache) or {}
    if d.get('index'):
        return d['index']
    for c in d.get('completion_objects', []):
        if c.get('type') == 'ref' and c.get('title') == he:
            return c.get('key')
    return None

def bump(ref, k):
    """Advance the last section number of a ref by k (amudim for a/b dapim)."""
    m = re.match(r'^(.*?)(\d+)([ab]?)$', ref)
    if not m:
        return None
    head, n, ab = m.group(1), int(m.group(2)), m.group(3)
    if ab:
        i = (n - 2) * 2 + (ab == 'b') + k
        return f'{head}{i // 2 + 2}{"ab"[i % 2]}'
    return f'{head}{n + k}'

def has_text(t):
    def nonempty(x):
        return any(nonempty(y) for y in x) if isinstance(x, list) else bool(str(x or '').strip())
    return bool(t) and 'error' not in t and nonempty(t.get('he'))

def expand_group(g, cache, log):
    refs = [(r, g.get('version')) for r in g.get('refs', [])]
    for w in g.get('walk', []):
        title = w.get('title') or resolve_he(w['he'], cache)
        if not title:
            log.append(f"could not resolve {w.get('he')}"); continue
        secs = available_sections(title, cache)
        if not secs:
            log.append(f'no sections found for {title}'); continue
        n = min(w['count'], len(secs))
        picks = [secs[int((j + 0.5) * len(secs) / n)] for j in range(n)]   # spread evenly
        refs += [(r, None) for r in picks]
        if n < w['count']:
            log.append(f"{title}: only {n} sections available")
    return refs

def available_sections(title, cache):
    """Section refs that have text, from /api/shape (handles complex books with parts)."""
    shape = fetch_json(f'{BASE}/api/shape/{urllib.parse.quote(title)}', cache)
    if not shape or (isinstance(shape, dict) and 'error' in shape):
        return []
    top = shape[0] if isinstance(shape, list) else shape
    idx = fetch_json(f'{BASE}/api/v2/index/{urllib.parse.quote(title)}', cache) or {}
    talmud_top = (idx.get('schema') or {}).get('addressTypes', [''])[0] == 'Talmud'

    def nonzero(c):
        return any(nonzero(x) for x in c) if isinstance(c, list) else bool(c)

    out = []
    def walk(node, name, talmud):
        ch = node.get('chapters') or []
        if not isinstance(ch, list):
            ch = [ch]
        if ch and isinstance(ch[0], dict):
            for sub in ch:
                if not re.search(r'Introduction|Preface|Subject|Index', sub.get('title', '')):
                    walk(sub, sub['title'], False)
            return
        if not isinstance(ch, list):
            ch = [ch]
        for i, c in enumerate(ch):
            if nonzero(c):
                out.append(f'{name} {i // 2 + 1}{"ab"[i % 2]}' if talmud else f'{name} {i + 1}')
    walk(top, top.get('title') or title, talmud_top)
    return out

# ------------------------------------------------------------ per page
def mine_page(ref, version, cache):
    t = fetch_json(text_url(ref, version), cache)
    if not has_text(t):
        return {'ref': ref, 'missing': True}
    links = fetch_json(links_url(ref), cache) or []
    book = t.get('indexTitle') or t.get('book') or ''
    year = index_info(book, cache)['year'] if book else None
    toks = tokens(t.get('he'))
    keys = [key(x) for x in toks]
    hits, seen = [], set()
    for l in links if isinstance(links, list) else []:
        if l.get('type') in SKIP_TYPES or l.get('category') in SKIP_CATS:
            continue
        src = l.get('sourceRef') or l.get('ref') or ''
        other = l.get('index_title') or ''
        if src in seen or other == book:
            continue
        seen.add(src)
        cat = l.get('category') or '?'
        if cat not in QUOTE_CATS:
            continue
        oy = first_year(l.get('compDate'))
        if cat != 'Tanakh' and (oy is None or year is None or oy >= year):
            continue  # undated, or a later work quoting this page: not a citation by it
        q = find_quote(keys, [key(x) for x in tokens(l.get('he') or '')],
                       min_letters=8 if cat == 'Tanakh' else 12)
        if not q or (cat != 'Tanakh' and q[1] < 3):
            continue
        s, n = q
        hits.append({'cat': cat, 'src': src, 'start': s, 'prev': toks[max(0, s - 3):s],
                     'quote': ' '.join(toks[s:s + min(n, 6)])})
    return {'ref': ref, 'book': book, 'tokens': toks, 'hits': hits}

# ------------------------------------------------------------ analysis
ABBR = re.compile(r'["\']')

def analyse(pages):
    pages = [p for p in pages if not p.get('missing')]
    f_count, f_cat, f_ex = collections.Counter(), collections.defaultdict(collections.Counter), {}
    occ = collections.Counter()
    ab_count, ab_ex = collections.Counter(), {}
    for p in pages:
        toks = p['tokens']
        for i, tk in enumerate(toks):
            occ[tk] += 1
            if i:
                occ[toks[i - 1] + ' ' + tk] += 1
            if ABBR.search(tk) and len(re.sub(r'[^א-ת]', '', tk)) >= 1:
                ab_count[tk] += 1
                ab_ex.setdefault(tk, f"{' '.join(toks[max(0, i - 3):i + 4])} ({p['ref']})")
        starts = set()
        for h in p['hits']:
            if h['start'] in starts or not h['prev']:
                continue
            starts.add(h['start'])
            pv = h['prev']
            for f in [pv[-1]] + ([pv[-2] + ' ' + pv[-1]] if len(pv) > 1 else []):
                f_count[f] += 1
                f_cat[f][h['cat']] += 1
                f_ex.setdefault(f, f"{' '.join(pv)} ⟨{h['quote']}⟩ = {h['src']} ({p['ref']})")
    formulas = [{'formula': f, 'quotes': n, 'occurrences': max(occ[f], n),
                 'precision': round(n / max(occ[f], n), 2), 'by_target': dict(f_cat[f]), 'example': f_ex[f]}
                for f, n in f_count.most_common() if n >= 2]
    abbrevs = [{'abbr': a, 'count': n, 'example': ab_ex[a]} for a, n in ab_count.most_common(60) if n >= 2]
    terms = {t: n for t, n in occ.items() if n >= 2}   # word and two-word counts, for the vocabulary
    return {'pages': len(pages), 'quotes': sum(len(p['hits']) for p in pages),
            'formulas': formulas, 'abbreviations': abbrevs, 'term_counts': terms}

# ------------------------------------------------------------ report
def md_report(groups):
    out = ['# Citation formulas and abbreviations: sample across genres', '',
           'Generated by `tools/mine_sample.py` from the pages in `tools/sample_units.json` (Sefaria texts and links).', '',
           '**How to read this.**', '',
           '- *Formulas* are the one or two words just before a passage the author quotes. A quote only counts when Sefaria',
           '  links the page to an earlier text and that text\'s words are found on the page. Sefaria does not link every',
           '  quote, so counts are low and *precision* (share of the formula\'s appearances on these pages that introduce a',
           '  linked quote) is a lower bound.',
           '- *Abbreviations* are every token with " or \' on the sample pages, most frequent first. Sefaria\'s editions differ',
           '  in how much they abbreviate (e.g. the Vilna-style Wikisource Bavli abbreviates, the vocalized edition does not).',
           '- Samples are small (2-21 pages per row): read these as tendencies, not statistics.', '']
    toc = []
    body = []
    for g in groups:
        a = g['analysis']
        anchor = re.sub(r'[^a-z0-9]+', '-', (g['genre'] + ' ' + g['group']).lower()).strip('-')
        toc.append(f"- [{g['genre']}: {g['group']}](#{anchor}) — {a['pages']} pages, {a['quotes']} linked quotes")
        body += [f"## {g['genre']}: {g['group']}", '',
                 f"{a['pages']} pages, {a['quotes']} linked quotes located. Pages: " +
                 ', '.join(p for p in g['pages_used']) + '.', '']
        if g.get('missing'):
            body += ['Not found on Sefaria: ' + ', '.join(g['missing']) + '.', '']
        if a['formulas']:
            body += ['**Formulas before quotes**', '', '| Formula | Quotes | Precision | Cites | Example |', '|---|---:|---:|---|---|']
            for f in a['formulas'][:25]:
                cites = ', '.join(f'{k} {v}' for k, v in sorted(f['by_target'].items(), key=lambda x: -x[1]))
                body.append(f"| {f['formula']} | {f['quotes']} | {f['precision']:.0%} | {cites} | {f['example']} |")
            body.append('')
        else:
            body += ['*No formula appeared before two or more linked quotes in this sample.*', '']
        if a['abbreviations']:
            body += ['**Most frequent abbreviations**', '', '| Abbreviation | Count | Example |', '|---|---:|---|']
            body += [f"| {x['abbr']} | {x['count']} | {x['example']} |" for x in a['abbreviations'][:30]]
            body.append('')
    return '\n'.join(out + ['## Contents', ''] + toc + [''] + body)

# ------------------------------------------------------------ main
def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser()
    ap.add_argument('--cache', required=True)
    ap.add_argument('--units', default=os.path.join(here, 'sample_units.json'))
    ap.add_argument('--json', default=os.path.join(here, '..', 'data', 'formulas-sample.json'))
    ap.add_argument('--doc', default=os.path.join(here, '..', 'docs', 'citation-formulas.md'))
    ap.add_argument('--workers', type=int, default=4)
    a = ap.parse_args()
    os.makedirs(a.cache, exist_ok=True)
    spec = json.load(open(a.units, encoding='utf-8'))
    log, out = [], []
    for g in spec['groups']:
        refs = expand_group(g, a.cache, log)
        with cf.ThreadPoolExecutor(a.workers) as ex:
            pages = list(ex.map(lambda rv: mine_page(rv[0], rv[1], a.cache), refs))
        missing = [p['ref'] for p in pages if p.get('missing')]
        used = [p['ref'] for p in pages if not p.get('missing')]
        an = analyse(pages)
        print(f"{g['genre']} / {g['group']}: {an['pages']} pages, {an['quotes']} quotes, missing {len(missing)}", flush=True)
        out.append({'genre': g['genre'], 'group': g['group'], 'pages_used': used, 'missing': missing, 'analysis': an})
    for m in log:
        print('  note:', m)
    os.makedirs(os.path.dirname(a.json), exist_ok=True); os.makedirs(os.path.dirname(a.doc), exist_ok=True)
    json.dump({'groups': out, 'notes': log}, open(a.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    open(a.doc, 'w', encoding='utf-8').write(md_report(out))
    print('wrote', a.json, a.doc)

if __name__ == '__main__':
    main()
