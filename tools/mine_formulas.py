#!/usr/bin/env python3
"""Mine citation-introducing formulas (דכתיב, תנן, ת"ר ...) from Sefaria.

For every daf of the Bavli (and every chapter of the Mishnah) this fetches the
text and Sefaria's links to Tanakh / Mishnah / Tosefta, finds where each linked
passage is quoted in the text, and records the words just before the quote.
Then it measures, for each candidate formula, how often it is actually followed
by a quotation, so we know how reliable it is as a detector.

Standard library only. Responses are cached so reruns are cheap:
    python3 tools/mine_formulas.py --cache /path/to/cache --out data
Options: --tractates Berakhot,Shabbat  --max-amudim 40  --workers 4
"""
import argparse, collections, concurrent.futures as cf, json, os, re, sys, time, urllib.parse, urllib.request

BASE = 'https://www.sefaria.org'
BAVLI_VERSION = 'Wikisource Talmud Bavli'   # keeps printed abbreviations: ת"ר, א"ר, שנא'
TARGET_CATS = {'Tanakh', 'Mishnah', 'Tosefta'}

# ---------------------------------------------------------------- fetching
def fetch_json(url, cache_dir, retries=4):
    key = re.sub(r'[^A-Za-z0-9._-]+', '_', url[len(BASE):])[:180]
    path = os.path.join(cache_dir, key + '.json')
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    delay = 2
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'sefersnap-formula-miner/1.0'})
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.load(r)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)
            return data
        except Exception as e:  # noqa: BLE001
            if attempt == retries - 1:
                print(f'  ! {url}: {e}', file=sys.stderr)
                return None
            time.sleep(delay); delay *= 2

def text_url(ref, version=None):
    q = {'commentary': 0, 'context': 0, 'pad': 0}
    if version:
        q['vhe'] = version
    return f'{BASE}/api/texts/{urllib.parse.quote(ref)}?{urllib.parse.urlencode(q)}'

def links_url(ref):
    return f'{BASE}/api/links/{urllib.parse.quote(ref)}?with_text=1'

# ---------------------------------------------------------------- text handling
NIKUD = re.compile(r'[֑-ֽֿ-ׇ]')
TAGS = re.compile(r'<[^>]+>')
FINALS = str.maketrans('ךםןףץ', 'כמנפצ')
TOKEN = re.compile(r'[א-ת][א-ת"\'׳״]*')

def clean(s):
    if isinstance(s, list):
        s = ' '.join(clean(x) for x in s)
    s = TAGS.sub(' ', s or '')
    s = re.sub(r'\([^()]*\)|\[[^\[\]]*\]', ' ', s)  # inline source refs, e.g. (תהלים קיט א)
    s = s.replace('־', ' ')               # maqaf
    s = NIKUD.sub('', s)
    s = s.replace('״', '"').replace('׳', "'").replace('״', '"').replace('׳', "'")
    return s

def tokens(s):
    """Raw tokens (abbreviation marks kept) from cleaned text."""
    return [t.rstrip('"') if t.endswith('"') and t.count('"') == 1 and len(t) > 2 and t[-2] != '"' else t
            for t in TOKEN.findall(clean(s))]

DIVINE = {"ה'", 'יהוה', 'יקוק', "ד'", 'יי', "ה''", 'ה"'}

def key(tok):
    """Spelling-insensitive key: letters only, finals normalised, internal ו/י dropped."""
    if tok in DIVINE:
        return '@@@'   # all spellings of the divine name match each other
    t = re.sub(r'[^א-ת]', '', tok).translate(FINALS)
    return t[:1] + re.sub('[וי]', '', t[1:]) if t else ''

def find_quote(text_keys, quote_keys, min_letters=8):
    """Longest run of consecutive matching tokens; returns (start, length) or None."""
    if not quote_keys:
        return None
    pos = collections.defaultdict(list)
    for j, k in enumerate(quote_keys):
        if k:
            pos[k].append(j)
    best = None
    for i, k in enumerate(text_keys):
        for j in pos.get(k, ()):
            n = 0
            while i + n < len(text_keys) and j + n < len(quote_keys) and text_keys[i + n] and text_keys[i + n] == quote_keys[j + n]:
                n += 1
            if n >= 2 and sum(len(x) for x in text_keys[i:i + n]) >= min_letters:
                if best is None or n > best[1]:
                    best = (i, n)
        if best and best[1] >= 6:
            break
    return best

# ---------------------------------------------------------------- per-unit mining
TARGET_PREFIX = {'Mishnah': 'Mishnah ', 'Tosefta': 'Tosefta '}

def mine_unit(ref, text_version, cache_dir, cats=TARGET_CATS, skip_types=('mishnah in talmud',)):
    t = fetch_json(text_url(ref, text_version), cache_dir)
    l = fetch_json(links_url(ref), cache_dir)
    if not t or not l or not isinstance(l, list):
        return None
    toks = tokens(t.get('he') or [])
    keys = [key(x) for x in toks]
    hits, seen = [], set()
    for link in l:
        cat = link.get('category')
        if cat not in cats or link.get('type') in skip_types:
            continue
        src = link.get('sourceRef') or link.get('ref')
        if cat in TARGET_PREFIX and not src.startswith(TARGET_PREFIX[cat]):
            continue  # e.g. modern works filed under Mishnah
        if src in seen:
            continue
        seen.add(src)
        q = find_quote(keys, [key(x) for x in tokens(link.get('he') or '')])
        if not q:
            continue
        start, n = q
        hits.append({
            'cat': cat, 'src': src, 'start': start, 'len': n,
            'prev': toks[max(0, start - 3):start],
            'quote': ' '.join(toks[start:start + min(n, 6)]),
        })
    return {'ref': ref, 'tokens': toks, 'hits': hits}

# ---------------------------------------------------------------- units
def bavli_units(cache_dir, only=None, max_amudim=None):
    shape = fetch_json(f'{BASE}/api/shape/Bavli', cache_dir) or []
    units = []
    for book in shape:
        title = book['title']
        if only and title not in only:
            continue
        n = book.get('length') or 0
        for i in range(n if not max_amudim else min(n, max_amudim)):
            daf = i // 2 + 2
            units.append((title, f'{title} {daf}{"ab"[i % 2]}'))
    return units

def mishnah_units(cache_dir, only=None):
    shape = fetch_json(f'{BASE}/api/shape/Mishnah', cache_dir) or []
    units = []
    for book in shape:
        title = book['title']
        if only and title.replace('Mishnah ', '') not in only:
            continue
        for ch in range(1, (book.get('length') or 0) + 1):
            units.append((title, f'{title} {ch}'))
    return units

# ---------------------------------------------------------------- analysis
def analyse(results, label):
    """Formula candidates with support (quotes introduced) and precision."""
    by_cat = collections.defaultdict(collections.Counter)
    examples = collections.defaultdict(list)
    uni_total, bi_total = collections.Counter(), collections.Counter()
    uni_hits, bi_hits = collections.Counter(), collections.Counter()

    for r in results:
        toks = r['tokens']
        for i, tok in enumerate(toks):
            uni_total[tok] += 1
            if i:
                bi_total[toks[i - 1] + ' ' + tok] += 1
        hit_starts = set()
        for h in r['hits']:
            if h['start'] in hit_starts:
                continue
            hit_starts.add(h['start'])
            prev = h['prev']
            if not prev:
                continue
            w1 = prev[-1]
            uni_hits[w1] += 1
            by_cat[w1][h['cat']] += 1
            if len(prev) >= 2:
                bg = prev[-2] + ' ' + w1
                bi_hits[bg] += 1
                by_cat[bg][h['cat']] += 1
            for f in ([w1] + ([prev[-2] + ' ' + w1] if len(prev) >= 2 else [])):
                if len(examples[f]) < 3:
                    examples[f].append({'ref': r['ref'], 'context': ' '.join(prev + [h['quote']]), 'source': h['src']})

    def rows(hits, totals, min_support):
        out = []
        for f, n in hits.most_common():
            if n < min_support:
                break
            tot = max(totals[f], n)
            cats = by_cat[f]
            out.append({
                'formula': f, 'quotes': n, 'occurrences': tot,
                'precision': round(n / tot, 3),
                'target': cats.most_common(1)[0][0],
                'by_target': dict(cats),
                'examples': examples[f],
            })
        return out

    n_hits = sum(len(r['hits']) for r in results)
    return {
        'corpus': label, 'units': len(results), 'quotes_found': n_hits,
        'single_words': rows(uni_hits, uni_total, 5),
        'two_words': rows(bi_hits, bi_total, 5),
    }

# ---------------------------------------------------------------- main
def run(units, version, cache_dir, workers, label, cats=TARGET_CATS):
    results, done = [], 0
    with cf.ThreadPoolExecutor(workers) as ex:
        futs = {ex.submit(mine_unit, ref, version, cache_dir, cats): ref for _, ref in units}
        for f in cf.as_completed(futs):
            r = f.result()
            if r:
                results.append(r)
            done += 1
            if done % 100 == 0 or done == len(units):
                print(f'  {label}: {done}/{len(units)}', flush=True)
    return results

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cache', required=True)
    ap.add_argument('--out', default='data')
    ap.add_argument('--tractates', default='')
    ap.add_argument('--max-amudim', type=int, default=0)
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--skip-mishnah', action='store_true')
    ap.add_argument('--skip-bavli', action='store_true')
    a = ap.parse_args()
    os.makedirs(a.cache, exist_ok=True); os.makedirs(a.out, exist_ok=True)
    only = set(x.strip() for x in a.tractates.split(',') if x.strip()) or None

    if not a.skip_bavli:
        units = bavli_units(a.cache, only, a.max_amudim or None)
        print(f'Bavli: {len(units)} amudim')
        res = run(units, BAVLI_VERSION, a.cache, a.workers, 'Bavli')
        with open(os.path.join(a.out, 'formulas-bavli.json'), 'w', encoding='utf-8') as f:
            json.dump(analyse(res, f'Bavli ({BAVLI_VERSION})'), f, ensure_ascii=False, indent=1)

    if not a.skip_mishnah:
        units = mishnah_units(a.cache, only)
        print(f'Mishnah: {len(units)} chapters')
        # Tosefta/Mishnah matches inside the Mishnah are mostly parallels, not citations.
        res = run(units, None, a.cache, a.workers, 'Mishnah', cats={'Tanakh'})
        with open(os.path.join(a.out, 'formulas-mishnah.json'), 'w', encoding='utf-8') as f:
            json.dump(analyse(res, 'Mishnah'), f, ensure_ascii=False, indent=1)

if __name__ == '__main__':
    main()
