# SeferSnap

A small installable web app (PWA): photograph a page of a sefer and get tappable Sefaria links for every citation on it.

Plain HTML/CSS/JS with no build step. Files: `index.html` (everything), `manifest.json`, `sw.js`, `icon.svg` and the PNG icons.

## How it works

1. Take a photo or choose one from the gallery. You can rotate it, and crop to one column for better accuracy.
2. **Read text** sends the image to Gemini for OCR. The image is scaled to 2400px on its longest side by default, as JPEG at 0.85.
3. Fix any OCR mistakes in the text box.
4. **Find citations** sends the text to Sefaria's Linker (`/api/find-refs`). The app polls `/api/async/{task_id}` for up to 30 seconds and shows each citation as a card with a preview and an "Open in Sefaria" link.
   SeferSnap then fills gaps the Linker leaves, using only Sefaria's public API (no key):
   - **Abbreviations:** blanks the ה in המג"א, הט"ז, הש"ך and so on, because the Linker only recognises them without it.
   - **ד"ה:** links `תוס' ב"מ נט ע"ב ד"ה תנור`, or `ובתוס' ד"ה …` with the daf implied, to the exact comment. It does this by matching the dibbur hamaschil on that daf.
   - **Pointers:** links ע"ש, עיין שם, הנ"ל and `הרשב"א הנ"ל` back to the citation they refer to.
   - **Quotations:** after a formula such as דכתיב, שנאמר, תנן or תניא, searches Sefaria for the quoted words in Tanakh, Mishnah, or Tosefta and Midrash.

   Each card says how it was found. The logic is in `cite.js`; run its tests with `node tests/cite.test.js`.
5. Anything Sefaria couldn't resolve is listed under "Not recognised" and added to the **Failure log**. You can copy the log to look for patterns.

## Standard pages: identify, don't transcribe

On a Vilna daf, or a Shulchan Aruch, Mishnah Berurah, Tur, Rambam or Mishnah page, OCR reads straight across the columns and mixes them up. SeferSnap therefore doesn't need a clean transcription for these. It searches Sefaria for about 20 short phrases from the text and votes on which page they come from. Then it shows that page: the texts recognised on it (Gemara, Rashi, Tosafot; Shulchan Aruch, Mishnah Berurah, Biur Halacha; …) and the sources Sefaria links from it (verses, Mishnah, Tosefta, Talmud, Ein Mishpat). Text is the only input, so a Google Lens copy works, however jumbled. A phrase found on two pages (a Mishnah quoted in the Bavli) splits its vote, and a close vote is shown as "Probably …" with the alternative. `node tests/live-identify.js` checks this against live Sefaria (behind a proxy, set `NODE_USE_ENV_PROXY=1`).

## Getting text in without an API key

- **Paste & find:** in Google Lens, select the text and tap Copy, then tap Paste & find in SeferSnap.
- **Share:** SeferSnap is a share target, so text shared to it from another app opens in it and is processed straight away. Whether Lens offers Share for text depends on the phone.

Gemini (with your key) remains available for reading a photo inside the app.

## Settings (stored on the device only)

- **Gemini API key:** get one at aistudio.google.com/apikey.
- **Model:** defaults to `gemini-2.5-flash`. "List models available to my key" shows what your key can use.
- **Image size:** longest side sent to Gemini.
- **AI-suggested citations (experimental):** Gemini also proposes refs, including "שם" and "הנ״ל". Each is checked with Sefaria's `/api/name` before it is shown, and labelled "AI suggestion".
- **Advanced:** the Sefaria base URL (for a proxy if CORS is ever blocked), and whether find-refs is sent as `text/plain` (the default, which avoids a CORS preflight). If one content type fails the app tries the other and remembers which worked.

## Hosting on GitHub Pages

Everything uses relative paths, so it works from a subpath. Serve these files over HTTPS, open the page in Chrome on Android, and choose "Add to Home screen" / "Install app".

To check installability on a Chromebook, use DevTools → Application → Manifest. Lighthouse no longer has a PWA audit.

## Not yet verified against the live services

These were tested in a browser with mocked responses only. The first real run will show:

- whether Sefaria allows browser calls from a GitHub Pages origin (CORS);
- the exact shape of the `/api/async` response (the parser accepts several shapes and logs anything unexpected);
- the real Gemini free-tier behaviour.

Errors and unexpected responses go to the Failure log.

## Citation research (`tools/`, `data/`, `docs/`)

Groundwork for recognising citations that Sefaria's Linker misses. These Python scripts are for development only; the app itself still has no build step.

- `docs/citation-findings.md`: what a 160-page sample across genres shows about how seforim cite, and next steps for the app.
- `docs/citation-formulas.md`: the full tables for each genre (formulas before quotes, and the most frequent abbreviations).
- `data/citation-vocabulary.json`: the curated vocabulary (quote introducers, pointers, location markers, author abbreviations and ambiguous tokens), with sample counts.
- `tools/mine_sample.py` regenerates the tables from the pages in `tools/sample_units.json`, and `tools/build_vocabulary.py` rebuilds the vocabulary. `tools/mine_formulas.py` does the same for a whole corpus (all of Bavli or Mishnah).

Run them with Python 3 (standard library only) and a cache folder, e.g. `python3 tools/mine_sample.py --cache /tmp/sefaria-cache`.
