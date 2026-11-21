version: 1

# Contract: demo portfolio site

Every task builds against this file. Changing it needs `status: needs-decision` and KNixt0's approval.

## Files (`demo/portfolio/`)

```
index.html                  # task 1: page shell, loads tokens + all components
styles/tokens.css           # task 1: design tokens (below)
styles/base.css             # task 1: reset, body, layout helpers
components/site-nav.js      # task 2  → <site-nav>
components/site-footer.js   # task 2  → <site-footer>
components/site-hero.js     # task 3  → <site-hero>
components/site-about.js    # task 4  → <site-about>
data/projects.json          # task 5
components/project-grid.js  # task 6  → <project-grid>
components/contact-form.js  # task 7  → <contact-form>
README.md                   # task 1: how to run
QA.md                       # task 8: QA report
```

## index.html (exact order of elements in `<body>`)

```html
<site-nav></site-nav>
<main id="main">
  <site-hero id="top"></site-hero>
  <site-about id="about"></site-about>
  <project-grid id="projects" src="data/projects.json"></project-grid>
  <contact-form id="contact"></contact-form>
</main>
<site-footer></site-footer>
```

Every component is loaded with `<script type="module" src="components/<name>.js"></script>`. A missing component must not break the page: unknown elements stay empty.

## Component rules

- **Vanilla Web Components:** `class X extends HTMLElement` and `customElements.define('<tag>', X)`. Use **light DOM** (no shadow DOM), so global tokens apply.
- Each component styles itself with a class prefix equal to its tag (e.g. `.site-hero__title`). Inject one `<style>` per component, guarded with an id so it's added only once.
- Use only tokens for colors, fonts and spacing. No hardcoded hex values inside components.
- Nav links: `#about`, `#projects`, `#contact` (section ids above).
- Content language: **Polish**.

## Tokens (`styles/tokens.css`)

```css
:root {
  --bg: #f7f7f4; --surface: #ffffff; --text: #17181c; --muted: #5a5f6b;
  --accent: #2f5bea; --accent-contrast: #ffffff; --line: #e3e4e8;
  --radius: 10px; --space-1: 4px; --space-2: 8px; --space-3: 16px; --space-4: 24px; --space-5: 40px; --space-6: 64px;
  --font-body: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  --font-display: ui-serif, Georgia, serif;
  --maxw: 1080px;
}
@media (prefers-color-scheme: dark) {
  :root { --bg: #111317; --surface: #191c22; --text: #eceef2; --muted: #a2a8b5; --accent: #7d9bff; --accent-contrast: #0b0d12; --line: #2a2e37; }
}
```

## `data/projects.json`

An array of 4–6 objects:

```json
[{
  "id": "kebab-case-id",
  "title": "string",
  "year": 2025,
  "summary": "one sentence, max 140 chars",
  "tags": ["react", "a11y"],
  "url": "https://example.com/...",
  "image": null
}]
```

`project-grid` fetches the URL in its `src` attribute, shows the cards and a tag filter (buttons built from all tags, plus "Wszystkie"), and shows a short message if the fetch fails.

## Contact form

Fields: name, email, message. Every field has a visible `<label>`. Validation runs on blur and on submit, with errors shown under each field (`aria-describedby`). On a valid submit it calls `preventDefault()`, shows "Dziękujemy! Odezwiemy się wkrótce." and resets. No network request.

## Quality bar (task 8 checks this; everyone aims for it)

- Works at 375 px and 1280 px wide, with no horizontal scroll.
- WCAG AA contrast, visible keyboard focus, a skip link to `#main` (task 1).
- **Clean console:** no errors and no `console.log`.
- No external requests (no CDNs, fonts or analytics).
