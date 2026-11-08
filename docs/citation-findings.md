# How seforim cite: findings from a 160-page sample

Sample: 160 pages from Sefaria across six genres (Gemara with Rashi, Tosafot and Acharonim; Rishonim on Shas; codes
from the Rambam to the Mishnah Berurah; responsa of Rishonim and Acharonim; commentaries on Chumash; Midrash, lomdus,
mussar). Page list: `tools/sample_units.json`. Full tables: [citation-formulas.md](citation-formulas.md). The vocabulary
the app will use: `data/citation-vocabulary.json`.

## 1. Only Tanakh is regularly quoted with an introducing formula

Where an author quotes earlier words and Sefaria links the source, the source is overwhelmingly a verse. The words
before it are a small, stable set:

| Formula | Seen in the sample | Where |
|---|---:|---|
| שנאמר / שנא' | 298 | everywhere; the Rambam uses almost nothing else (39 of his 189 linked quotes) |
| דכתיב / דכתי' / כדכתיב | 182 + 39 | Aramaic contexts: Gemara, Rishonim, Tur |
| שכתוב, כתוב, ככתוב | 89, 81 | Chumash commentaries, codes |
| כאמרו | 37 | Ibn Ezra only |
| ת"ל, שאמר הכתוב, הוא אומר, ואומר | 31, 29, 30, 67 | Chumash commentaries, Midrash |
| מאי דכתיב, מאי קרא, הוא דכתיב, מהכא | small | Gemara and Midrash; 67-88% of their appearances introduce a linked verse |

Two-word forms (מאי דכתיב, כענין שנאמר, שאמר הכתוב) almost always introduce a verse. Single words like כתיב, קרא
or כתוב often don't. So when a quote-introducer is found, **search the next few words in Tanakh**.

## 2. Mishnah and baraita formulas show up mainly in the Rishonim

| Introduces | Formulas (sample count) |
|---|---|
| Mishnah | מתני' 48, דתנן 36, תנן 32, במשנה 29, דמתני' 24, כדתנן 10, שנינו 8 |
| Baraita | תני 38, ת"ר 28, תניא 25, דתניא 19, ותניא 11, והתניא 6 |
| Gemara (by later authors) | גבי 190, התם 154, אמרינן 141, דאמרינן 83, בגמרא 76, בירושלמי 64, בגמ' 60, כדאיתא 60 |

Sefaria links few of these quotes, so they rarely appear in the formula tables. The word counts show they're common.

## 3. After the Gemara, citation is by name and location, not by quote

From the Rishonim on, most citations name an author or book and give a location; the words are seldom quoted.
The vocabulary:

- **Author/book:** רש"י 184, הרמב"ם 173, הרשב"א 110, ר"ת 63, התוס' 61, הטור 58, הרא"ש 55, הר"ן 54, הרמ"א 48 …
- **Location:** סי'/סימן 280, פרק/פ'/בפ' 448, דף 89, ס"ס 53, סעיף 40, ע"א/ע"ב, ד"ה, בפ"ק 37, ה"א …
- **Quote brackets:** וז"ל … עכ"ל marks an exact quote (וז"ל 89, עכ"ל 153). ז"ל on its own (469) is usually the
  honorific after a name.
- **Reported opinion:** כתב 422, וכתב 117, וכ"כ 89, כמ"ש / וכמ"ש / מ"ש / ומ"ש 349 together. These are concentrated in the
  codes and their commentaries (Beit Yosef, Magen Avraham, Mishnah Berurah).

**For the app:** the Linker resolves this kind of citation well when the reference is complete, e.g.
`שו"ע או"ח סי' תרצ"ה ס"ב`. Where it fails is when the author is abbreviated or the location is a ד"ה or ס"ק, which is
what the earlier live test showed: תוס' … ד"ה, מג"א … סק"ז. The `author_or_book` list in the vocabulary maps
those abbreviations to Sefaria titles.

## 4. Pointers (שם, ע"ש, הנ"ל) are frequent, mostly in the codes and responsa

שם 920 (but also "name"/"there"), עיין 156 + ועיין 111, ע"ש 141, לעיל 112, לקמן 98, הנ"ל 36, כנ"ל 28, הנז' 23.
Resolving these needs the previous citation on the page. Over 60% of them are in the codes and their commentaries.

## 5. Abbreviation density varies a lot by genre

The Rambam and Shulchan Arukh hardly abbreviate. Nosei kelim and responsa are dense with abbreviations: כו' 229,
וכמ"ש 103, ע"ש 94, סי' 95 in just 12 pages of Magen Avraham, Taz, Shach and Ketzot. The edition matters too. The Vilna-style
Wikisource Bavli abbreviates (א"ר, ת"ר, שנא'), while Sefaria's vocalized Bavli spells everything out. A photo of a
printed page will look like the abbreviated kind.

## 6. Ambiguous tokens: never a citation on their own

| Token | Meanings seen |
|---|---|
| ה' (674) | divine name, the number 5, הלכה ה |
| ע"ש (141) | עיין שם, ערב שבת, על שם |
| פ' (171) | פרק, פרשת, פירוש |
| כ', ס' | כתב/כתיב/20; סימן/ספר/60 |
| ר"י, ר"א, ב"ה | different people; בית הלל or ברוך הוא |
| שם, כלל | very common ordinary words |

## Limits of this sample

- Formulas were only counted before quotes Sefaria links, and Sefaria links few quotes outside Tanakh. Counts are
  therefore lower bounds, and Rishonim citing the Gemara are under-represented in the formula tables. The word counts
  make up for some of this.
- 2 to 21 pages per group. Not found on Sefaria: Kesef Mishneh on the three Rambam chapters chosen, Ritva on Pesachim
  116a and Yoma 85b, one Meiri section, one Rashba responsum. Sefaria doesn't have Igrot Moshe.
- Sefaria's texts aren't printed pages: no marginal sources (תורה אור, עין משפט), different punctuation, and some
  editions spell out abbreviations.

## Suggested next steps for SeferSnap

1. **Quote search:** when a `quote_tanakh` / `quote_mishnah` / `quote_baraita` formula appears, take the next 3-8
   words and search Sefaria within that category. Show a result only for a close match.
2. **Abbreviation expansion before the Linker:** expand common author abbreviations (תוס' → תוספות, מג"א → מגן אברהם)
   in a copy of the text sent to the Linker, keeping the original offsets for display.
3. **ד"ה resolution:** for `X on <daf> ד"ה <words>`, fetch that commentary on the daf and match the dibbur hamaschil.
4. **Pointer tracking:** resolve שם / ע"ש / הנ"ל to the previous resolved citation on the page.
5. **Prompt Gemini with this vocabulary** in the experimental AI-suggestion mode.
