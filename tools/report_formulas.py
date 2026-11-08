#!/usr/bin/env python3
"""Turn mine_formulas.py output into docs/citation-formulas.md and data/citation-formulas.json.

    python3 tools/report_formulas.py --in data --doc docs/citation-formulas.md
"""
import argparse, json, os, re

TARGET_HE = {'Tanakh': 'Tanakh', 'Mishnah': 'Mishnah', 'Tosefta': 'Tosefta / Baraita'}
# Formulas need this many quotes behind them to make the report.
MIN_QUOTES = {'single_words': int(__import__('os').environ.get('MINQ', 15)), 'two_words': int(__import__('os').environ.get('MINQ', 10))}

def letters(s):
    return re.sub(r'[^א-ת ]', '', s)

def is_abbrev(f):
    return "'" in f or '"' in f

def group_variants(rows):
    """Attach abbreviated forms to the full form they abbreviate.

    שנא' -> שנאמר (prefix), ת"ר -> תנו רבנן (initials). Returns {full: [abbrevs]}.
    """
    fulls = [r['formula'] for r in rows if not is_abbrev(r['formula'])]
    groups = {}
    for r in rows:
        f = r['formula']
        if not is_abbrev(f):
            continue
        core = letters(f).replace(' ', '')
        best = None
        for full in fulls:
            words = full.split()
            initials = ''.join(w[0] for w in words)
            joined = ''.join(words)
            if ('"' in f and len(words) > 1 and core == initials) or \
               ("'" in f and len(words) == 1 and len(core) >= 2 and joined.startswith(core) and joined != core):
                best = full
                break
        if best:
            groups.setdefault(best, []).append(f)
    return groups

def table(rows, n):
    out = ['| Formula | Quotes introduced | Precision (lower bound) | Cites | Example |',
           '|---|---:|---:|---|---|']
    for r in rows[:n]:
        tgt = ', '.join(f'{TARGET_HE.get(k, k)} {v}' for k, v in sorted(r['by_target'].items(), key=lambda x: -x[1]))
        ex = r['examples'][0] if r['examples'] else None
        exs = f"{ex['context']} ({ex['source']}, cited at {ex['ref']})" if ex else ''
        out.append(f"| {r['formula']} | {r['quotes']} | {r['precision']:.0%} | {tgt} | {exs} |")
    return '\n'.join(out)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--in', dest='inp', default='data')
    ap.add_argument('--doc', default='docs/citation-formulas.md')
    ap.add_argument('--json', default='data/citation-formulas.json')
    a = ap.parse_args()

    corpora, summary = [], {}
    for name in ('bavli', 'mishnah'):
        p = os.path.join(a.inp, f'formulas-{name}.json')
        if os.path.exists(p):
            with open(p, encoding='utf-8') as f:
                corpora.append((name, json.load(f)))

    md = ['# Citation formulas in Gemara and Mishnah', '',
          'Mined from Sefaria by `tools/mine_formulas.py`. For every daf (Bavli) and chapter (Mishnah), each passage',
          "Sefaria links to (Tanakh, Mishnah, Tosefta) is located in the text, and the words just before the quote are",
          'counted. "Precision" is how often the formula, wherever it appears, is followed by a quote Sefaria has a',
          'link for. Sefaria does not link every quotation, so treat it as a lower bound.', '']

    for name, d in corpora:
        md += [f"## {d['corpus']}", '',
               f"{d['units']} units scanned, {d['quotes_found']} linked quotations located.", '']
        entry = {'corpus': d['corpus'], 'formulas': []}
        for kind, title in (('two_words', 'Two-word formulas'), ('single_words', 'Single words')):
            rows = [r for r in d[kind] if r['quotes'] >= MIN_QUOTES[kind]]
            md += [f'### {title}', '', table(rows, 40), '']
            for r in rows:
                entry['formulas'].append({
                    'formula': r['formula'], 'words': len(r['formula'].split()),
                    'quotes': r['quotes'], 'precision': r['precision'],
                    'cites': r['target'], 'by_target': r['by_target'],
                })
        groups = group_variants(d['single_words'] + d['two_words'])
        if groups:
            md += ['### Abbreviated spellings found', '', '| Full form | Abbreviations in the text |', '|---|---|']
            md += [f"| {full} | {', '.join(sorted(set(v)))} |" for full, v in sorted(groups.items())]
            md += ['']
        entry['abbreviations'] = groups
        summary[name] = entry

    os.makedirs(os.path.dirname(a.doc), exist_ok=True)
    os.makedirs(os.path.dirname(a.json), exist_ok=True)
    with open(a.doc, 'w', encoding='utf-8') as f:
        f.write('\n'.join(md))
    with open(a.json, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=1)
    print('wrote', a.doc, a.json)

if __name__ == '__main__':
    main()
