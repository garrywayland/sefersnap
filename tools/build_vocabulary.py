#!/usr/bin/env python3
"""Build data/citation-vocabulary.json: the curated citation vocabulary the app will use.

The lists are curated by hand from the mined sample (data/formulas-sample.json) plus
standard usage; each entry is annotated with how often it appeared in the sample, overall
and per genre, so we can see which ones are evidenced and where.

    python3 tools/build_vocabulary.py
"""
import collections, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
SAMPLE = os.path.join(HERE, '..', 'data', 'formulas-sample.json')
OUT = os.path.join(HERE, '..', 'data', 'citation-vocabulary.json')

VOCAB = {
    'quote_tanakh': {
        'doc': 'Introduce a quoted verse. Search the following words in Tanakh.',
        'items': ['שנאמר', "שנא'", "שנ'", 'דכתיב', "דכתי'", "דכת'", 'כדכתיב', "כדכתי'", 'וכתיב', "וכתי'", 'כתיב', 'והכתיב',
                  'הוא דכתיב', 'מאי דכתיב', 'מאי קרא', 'אמר קרא', 'ת"ל', 'תלמוד לומר', 'ונאמר', 'ואומר', 'הוא אומר',
                  'כענין שנאמר', 'כמו שנאמר', 'שאמר הכתוב', 'שכתוב', 'ככתוב', 'כאמרו', 'מהכא', 'מנין', 'ועליהם נאמר', 'קרא', 'כתוב'],
    },
    'quote_mishnah': {
        'doc': 'Introduce a quoted Mishnah. Search the following words in Mishnah.',
        'items': ['תנן', 'דתנן', 'כדתנן', 'ותנן', 'והתנן', 'תנן התם', 'תנינא', "מתני'", "במתני'", "דמתני'", 'במשנה', 'שנינו'],
    },
    'quote_baraita': {
        'doc': 'Introduce a baraita. Search Tosefta, Sifra, Sifrei, Mekhilta, and the Bavli itself.',
        'items': ['תניא', 'דתניא', 'כדתניא', 'ותניא', 'והתניא', 'ת"ר', 'תנו רבנן', 'תני', 'ותני', 'ת"ש', 'תא שמע', 'במתניתא'],
    },
    'quote_gemara': {
        'doc': 'Later authors pointing to the Gemara, often with a quote or a location.',
        'items': ['כדאמרינן', 'דאמרינן', "כדאמרי'", "דאמרי'", 'אמרינן', "בגמ'", 'בגמרא', 'איתא', 'כדאיתא', 'דאיתא', 'התם', 'גבי',
                  'איתמר', 'אמר מר', 'ירושלמי', 'בירושלמי'],
    },
    'quote_named_author': {
        'doc': 'Verbatim or paraphrased citation of a named author. וז"ל ... עכ"ל brackets an exact quote.',
        'items': ['וז"ל', 'ז"ל', 'עכ"ל', 'ע"כ', 'כתב', 'וכתב', 'וכ"כ', 'כמ"ש', 'וכמ"ש', 'ומ"ש', 'מ"ש', 'כמו שכתב', 'פירש"י', "פי'", 'כתבו', 'וכתבו'],
    },
    'pointer': {
        'doc': 'See / ibid / above / below. Resolve against the previous citation on the page.',
        'items': ['ע"ש', 'עיי"ש', 'שם', 'הנ"ל', "הנז'", 'כנ"ל', 'וכנ"ל', "עי'", "ועי'", "וע'", 'עיין', 'ועיין', 'לקמן', 'לעיל', 'בסמוך', 'כדלקמן', 'כדלעיל'],
    },
    'location': {
        'doc': 'Location markers that follow a book or author name.',
        'items': ["סי'", 'סימן', "בסי'", 'ס"ק', 'סק"א', 'סק"ב', 'סק"ז', 'ס"ס', "סעי'", 'סעיף', 'ס"א', "ס'", 'ד"ה', 'בד"ה', 'דף', 'ע"א', 'ע"ב',
                  "פ'", 'פרק', 'פ"ק', 'בפ"ק', "בפ'", "הל'", "מהל'", 'ה"א', 'ה"ב', 'ה"ג', 'כלל', 'אות', 'עמוד', "בתשו'", 'תשובה'],
    },
    'author_or_book': {
        'doc': 'Common author and book abbreviations (Hebrew name, Sefaria title).',
        'items': {
            'רש"י': 'Rashi', 'פירש"י': 'Rashi', 'ר"ת': 'Rabbeinu Tam (Tosafot)', 'ר"י': 'Ri (Tosafot)', "תוס'": 'Tosafot', 'התוס\'': 'Tosafot',
            'הרמב"ם': 'Mishneh Torah', 'הרמב"ן': 'Ramban', 'הרא"ש': 'Rosh', 'הרשב"א': 'Rashba', 'הר"ן': 'Ran', 'הריטב"א': 'Ritva',
            'הרי"ף': 'Rif', 'הטור': 'Tur', 'ב"י': 'Beit Yosef', 'ד"מ': 'Darkhei Moshe', 'הרמ"א': 'Rema', 'המ"א': 'Magen Avraham',
            'מג"א': 'Magen Avraham', 'הט"ז': 'Turei Zahav', 'ט"ז': 'Turei Zahav', 'הש"ך': 'Siftei Kohen', 'ש"ך': 'Siftei Kohen',
            'מ"ב': 'Mishnah Berurah', 'שו"ע': 'Shulchan Arukh', 'או"ח': 'Orach Chayim', 'יו"ד': "Yoreh De'ah", 'אה"ע': 'Even HaEzer',
            'אבהע"ז': 'Even HaEzer', 'חו"מ': 'Choshen Mishpat', 'רשב"ם': 'Rashbam', 'נ"י': 'Nimukei Yosef', 'מהרש"א': 'Maharsha',
            'פנ"י': 'Penei Yehoshua', 'נוב"י': 'Noda BiYehudah', 'חת"ס': 'Chatam Sofer', 'הש"ס': 'Talmud', 'ש"ס': 'Talmud',
            'ב"ר': 'Bereshit Rabbah', 'מד"ר': 'Midrash Rabbah', 'רז"ל': '(the Sages)', 'חז"ל': '(the Sages)', 'האר"י': 'Arizal',
        },
    },
    'ambiguous': {
        'doc': 'Seen in the sample with more than one meaning; never treat as a citation on their own.',
        'items': {
            'ע"ש': 'עיין שם / ערב שבת / על שם', "ה'": 'divine name / 5 / הלכה ה', "כ'": 'כתב / כתיב / 20',
            "פ'": 'פרק / פרשת / פירוש', "ס'": 'סימן / ספר / 60', 'ב"ה': 'בית הלל / ברוך הוא / בעזרת השם',
            'ר"י': 'Ri (Tosafot) / Rabbi Yehuda / Rabbi Yochanan', 'ר"א': 'Rabbi Eliezer / Rabbi Akiva (rare)', 'ש"ש': 'unclear in this sample (Nosei kelim)',
        },
    },
}

def main():
    sample = json.load(open(SAMPLE, encoding='utf-8'))
    total = collections.Counter()
    by_genre = collections.defaultdict(collections.Counter)
    for g in sample['groups']:
        a = g['analysis']
        for t, n in a.get('term_counts', {}).items():
            total[t] += n; by_genre[t][g['genre']] += n

    out = {'_doc': 'Curated citation vocabulary. "sample" = times the term appears on the sample pages '
                   '(see docs/citation-formulas.md); 0 means not seen in this small sample but standard usage.',
           'groups': {}}
    for name, spec in VOCAB.items():
        items = spec['items']
        pairs = items.items() if isinstance(items, dict) else ((i, None) for i in items)
        rows = []
        for term, meaning in pairs:
            row = {'term': term, 'sample': total.get(term, 0)}
            if meaning:
                row['meaning'] = meaning
            if by_genre.get(term):
                row['genres'] = dict(by_genre[term].most_common())
            rows.append(row)
        out['groups'][name] = {'doc': spec['doc'], 'items': rows}
    json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('wrote', OUT)
    for name, g in out['groups'].items():
        ev = sum(1 for r in g['items'] if r['sample'])
        print(f"  {name}: {len(g['items'])} terms, {ev} seen in sample")

if __name__ == '__main__':
    main()
