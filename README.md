# SeferSnap

A small installable web app (PWA): photograph a page of a sefer and get tappable Sefaria links for every citation on it.

Plain HTML/CSS/JS with no build step. Files: `index.html` (everything), `manifest.json`, `sw.js`, `icon.svg` and the PNG icons.

## How it works

1. Take a photo or choose one from the gallery. You can rotate it, and crop to one column for better accuracy.
2. **Read text** sends the image to Gemini for OCR. The image is scaled to 2400px on its longest side by default, as JPEG at 0.85.
3. Fix any OCR mistakes in the text box.
4. **Find citations** sends the text to Sefaria's Linker (`/api/find-refs`). The app polls `/api/async/{task_id}` for up to 30 seconds and shows each citation as a card with a preview and an "Open in Sefaria" link.
5. Anything Sefaria couldn't resolve is listed under "Not recognised" and added to the **Failure log**. You can copy the log to look for patterns.

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
