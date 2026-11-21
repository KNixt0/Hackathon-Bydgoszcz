# DESIGN.md: InvestWatch "Urzędowy"

Source: proposal 1 "Urzędowy" in `docs/design/proposals.html` (CSS scoped to `.p1`, shared `.spec`, `.ds`, `.cal`, `.cm`, `.lvl`, `.ms` rules and the fragments `p1A` queue, `p1B` case, `p1C` calibration). It replaces the earlier choice of proposal 4. Product context: `PRODUCT.md`. Values below are copied from the page CSS. Items marked **[ext]** are not on the page: they are extensions proposed here and need confirming. Sections 4.12 to 4.17 and section 5 (calibration) are new design work, not extracted.

Principle: the product looks like a register, not an app. Square, ruled, table-first. Hierarchy comes from 1 px rules, a 2 px rule under table headers, weight 700 and one accent colour. No radii except the top of fields and the 4 px badge, no shadows, no fills by level. New information is a row, a table column or a key–value pair, never a new card.

## 1. Colour tokens

Contrast computed with the WCAG 2.x formula. "Existing" = name in `services/frontend/src/styles/tokens.css`.

| Role | New property | Hex | Contrast | Existing token |
|---|---|---|---|---|
| Page and panel background | `--bg` | `#FFFFFF` | n/a | `--bg`, `--surface` (both white now) |
| Field background (inputs, selects) | `--field` | `#EEEEEE` | ink 15.2:1 (derived), muted 5.6:1 | `--surface-sunken` (alias) |
| Row hover | `--hover` | `#F6F6F6` | ink 16.7:1, accent 10.6:1 | `--surface-hover` |
| Tint (recommendation callout, inactive tab) | `--tint` | `#EDEFF8` | ink on it 15.5:1 (derived), accent 10.0:1, muted 5.7:1 | `--accent-soft` |
| Selection | `--sel` | `#D9DFF6` | ink 13.6:1 | `::selection` literal |
| Ink | `--ink` | `#161616` | 18.1 on white | `--ink` |
| Ink 2 | `--ink-2` | `#3A3A3A` | 11.4 on white, 9.8 on field | `--ink-2` |
| Muted | `--muted` | `#5E5E5E` | 6.5 on white, 5.6 on field, 5.7 on tint | `--muted` (drop `--faint`) |
| Rule (panel, rows) | `--line` | `#DDDDDD` | decorative | `--line` |
| Strong rule, scrollbar | `--line-strong` | `#929292` | 3.1 on white | `--line-strong` (`--line2` on the page) |
| Accent: links, primary button, active tab, slider thumb | `--accent` | `#1A2F8C` | 11.5 on white, white on it 11.5, 9.9 on field | `--accent` |
| Accent hover | `--accent-hover` | `#121F66` | white on it 15.7 (derived) | `--accent-hover` |
| Focus ring | `--focus` | `#0A6CD6` | 5.1 on white | `--focus` |
| Critical, text | `--c-red` | `#B0121A` | 7.1 on white, 6.2 on tint, 6.0 on badge fill | `--red-ink` |
| To verify, text | `--c-amb` | `#8F3F00` | 7.3 | `--orange-ink` |
| Compliant, text | `--c-grn` | `#1C6B3B` | 6.5 | `--green-ink` |
| Critical, marker | `--m-red` | `#C8141E` | 5.9 | `--red` |
| To verify, marker | `--m-amb` | `#C25200` | 4.7 | `--orange` |
| Compliant, marker | `--m-grn` | `#2E8A53` | 4.3 | `--green` |
| Unflagged unit (details histogram) | `--u-off` | `#C9C9C9` | 1.7, decorative | none (new) |
| Flagged unit | `--u-on` | `#1A2F8C` (= accent) | 11.5 | none (new) |
| "Critical" badge fill | `--red-soft` | `#FCE7E7` | `--c-red` on it 6.0:1 | `--red-soft` (kept for this one badge) |
| "New" badge fill | `--accent-soft` | `#E6EAF8` | accent on it 9.5 (derived) | `--accent-soft` (value changes; `--tint` is the callout) |

Notes
- Level colour appears in three places only: the word and icon (`--c-*`), the mini-scale and axis zones (`--m-*`), and the single "Krytyczne" badge in the case header (`--red-soft`). Do not tint rows, panels, tabs or alerts by level. Tokens `--red-line`, `--orange-soft`, `--orange-line`, `--green-soft`, `--green-line`, `--neutral-soft`, `--shadow-pop`, `--shadow-drawer`, `--sidebar-w`, `--faint`, `--accent-ink` are deleted.
- One accent for link and button (the page has no second colour): `--accent` `#1A2F8C` replaces `#1b2a5c`. `--focus` stays a different blue (`#0A6CD6`) so the ring is visible on accent-coloured controls.
- Markers `--m-amb` and `--m-grn` are 4.7 and 4.3 on white (above the 3:1 needed for graphics) but never carry meaning alone: they sit next to a word or an icon.
- `--line-strong` `#929292` (3.1 on white) is the control edge for checkboxes, radios and secondary-button text-less borders; fields use the 2 px bottom edge in `--ink-2` instead.
- The page background is white, not grey: panels are separated by 1 px `--line`, not by a canvas colour.
- Dark theme: not designed (section 9). `tokens.css` is light only today, so nothing regresses.

## 2. Typography

| Item | Value |
|---|---|
| Family | Public Sans (SIL OFL 1.1). Stack: `"Public Sans", system-ui, "Segoe UI", sans-serif` |
| Self-hosting | `@fontsource/public-sans`, replacing `@fontsource/ibm-plex-sans` (current `5.3.0` pinned). Imports in `main.tsx`: `latin-400`, `latin-ext-400`, `latin-500`, `latin-ext-500`, `latin-700`, `latin-ext-700` (`latin-ext` carries ą ć ę ł ń ó ś ź ż). Pin an exact version. `THIRD_PARTY_LICENSES.md` needs the entry in both tables the file keeps for fonts (runtime list and the per-service list): `@fontsource/public-sans | <version> | OFL-1.1 | Frontend | self-hosted UI typeface, bundled into the build`; remove the IBM Plex rows. OFL is already accepted for IBM Plex. No `<link>` to a font CDN. |
| Weights | 400 body, 500 links, tabs, buttons, labels, 700 headings, level words, numerals, table headers. No 600. |
| Base | 16 px / 1.5, `font-variant-numeric: tabular-nums` on the whole app (page: `.spec`) |
| Smoothing | `-webkit-font-smoothing: antialiased` |

Scale (px): 12 / 14 / 16 / 18 / 20 / 28.

| Token | Size / line | Use |
|---|---|---|
| `--fs-12` | 12 / 1.4 | legend, breadcrumb, file size, scale labels and ticks, chart ticks |
| `--fs-14` | 14 / 1.5 | table cells and headers, tabs, nav, key–value pairs, hints, captions, register table, secondary text |
| `--fs-16` | 16 / 1.5 | body, field values, buttons, labels |
| `--fs-18` | 18 / 1.45 | verdict sentence, matrix cell counts, calibration secondary values |
| `--fs-20` | 20 / 1.25 | section titles (h5), service name in the header, calibration live sentence (1.45) |
| `--fs-28` | 28 / 1.2 (1 for numerals) | page titles (h4), threshold and calibration core counts |

Compliance Score and risk values in the case verdict use 28/700; there is no 40 px numeral. Numbers are always tabular. Existing `--fs-xs/sm/base/md/lg/xl/2xl` (11.5 to 34 px) are replaced; base grows from 13.5 to 16 px for body, while tables and most chrome are 14 px (section 9).

## 3. Spacing, radii, borders, focus

- Unit 8 px, micro 4. Scale: 4, 8, 12, 16, 24, 32 (keep `--sp-1..8` names; `--sp-5` 20 only for legacy use).
- Page body padding 24 (16 below 640 px). Gap between blocks 16 (grid). Gap inside a case column 24. Header top row padding `16 24` (12 16 narrow). Tab panel padding 16 (12 narrow). Callout padding 24 (16 narrow).
- Radii: **0 everywhere** (containers, tables, buttons, tabs, panels). Exceptions: fields and selects 4 px on the top corners only (`4px 4px 0 0`; a search field joined to its button `4px 0 0 0`), badges 4 px on all corners. Mini-scale bar 0. Slider thumb 0 (square). Delete `--r-md`, `--r-lg`; keep `--r-sm: 4px` for the exceptions.
- **Rules, not shadows.** Panel and tab-panel: 1 px `--line`. Row separator: 1 px `--line`. Table header underline: 2 px `--ink`. Key–value rows: 1 px `--line`, first row also on top. Field: no border, 2 px bottom edge `--ink-2` as `inset 0 -2px 0`. Secondary button: `inset 0 0 0 1px var(--accent)`. Recommendation callout: 4 px `--accent` left border. No `box-shadow` for depth, no gradients, no `backdrop-filter`.
- Overlays (dialog, menu, palette, toast) **[ext]**: no shadow; white background, 1 px `--ink-2` border (2 px on the dialog top in `--accent`), radius 0, scrim `rgba(22,22,22,.50)` behind dialogs. Delete `--shadow-pop` and `--shadow-drawer`.
- Focus: `outline: 3px solid var(--focus); outline-offset: 2px` on every `:focus-visible`. On the slider thumb `outline-offset: 4px`.
- Motion: only colour and background transitions, `--dur` 140 ms; honour `prefers-reduced-motion` (already in `base.css`).
- Layout width **[ext]**: content is fluid up to `1440px`, centred; the case grid and calibration column cap their own width (4.9, 5.2).

## 4. Components

### 4.1 Header and navigation (replaces the sidebar)
Two stacked rows, full width, white, no shadow.

**Row 1** (`.top`): flex, space-between, centre-aligned, gap `8 24`, padding `16 24`, wraps. Left: service block, name "InvestWatch" 20/700 `line-height 1.2`, under it "Nadzór nad reklamą finansową" 14 `--muted` (no logo mark; the existing `.brand__mark` goes). Right: quick actions, 14 px, gap `4 24`.

**Row 2** (`.p1-nav`): tab links, flex, `overflow-x: auto`, padding `0 24`, `border-top` and `border-bottom` 1 px `--line`. Item: block, padding `12 16`, 14/500 `--ink`, no underline, `nowrap`, `border-bottom: 2px solid transparent; margin-bottom: -1px`. Current (`aria-current="page"`): `--accent`, 700, bottom border 2 px `--accent`. Hover **[ext]**: `--hover` background. Items: Kolejka spraw, Kalibracja, Skanowania, and **Dziennik audytu** only for the supervisor (`/audyt`). No counts in the nav.

The page's row 1 only has "Pomoc", the user name and "Wyloguj". The product needs more, and the lead's decision is to put all of it in the header **[ext]**:

| Control | Where | Spec |
|---|---|---|
| Search (opens command palette, `Ctrl+K`) | row 1, right group, first | secondary button 40 px with the search icon and the label "Szukaj" (a 40 px square icon button needs a visible tooltip and `aria-keyshortcuts`); the field-and-button pair of the queue toolbar stays for queue search |
| "Skanuj URL" | row 1, right group | primary button 40 px |
| Jobs menu ("Skanowania w toku") | row 1, right group | link-style menu trigger with a count in brackets only when jobs run: "Zadania (2)" |
| Demo menu | row 1, right group | link-style menu trigger "Dane demo", present only when demo mode is on |
| Connection state | row 1, right group | icon plus word: "Połączono" or "Brak połączenia" in 14 px (icons `Wifi` / `WifiOff`; colour `--c-grn` / `--c-red`; the word carries meaning); polite live region |
| User name and role | row 1, rightmost group | "A. Kowalczyk, analityk" 14 px (role in `--muted`) |
| Wyloguj | after the user | link, 14 px |
| Pomoc | before the user | link |

At 1280 px row 1 holds about 9 items: if they do not fit they wrap (the row wraps by design); below 960 px put search, jobs, demo and Pomoc into one "Menu" disclosure. Version line "Prototyp · dane przetwarzane lokalnie" moves to a page footer, 12 px `--muted`.

**Breadcrumb** (on the case, evidence and audit screens): 12 px `--muted`, links `--ink-2`, separator "›", gap `4 8`, directly above the page title: "Kolejka spraw › IW/2026/0412". The current item has `aria-current="page"`.

### 4.2 Level tabs with counts (replaces the three risk tiles and the level select)
- Tab list: `role="tablist"`, `aria-label="Poziom ryzyka"`, flex, gap 4, `overflow-x: auto`, `margin-bottom: -1px`, `z-index: 1` so the selected tab merges into the panel below.
- Tab: inline-flex, centre, gap 8, height 44, padding `0 16`, border 1 px transparent, top border 2 px transparent, no bottom border, radius 0, background `--tint`, 14/500 `--ink`. Content: level icon (not on "Wszystkie"), word, count in `<b>` 700.
- Selected (`aria-selected="true"`): white background, border 1 px `--line`, **top border 2 px `--accent`**, text `--accent`. Level icons keep their `--c-*` colour.
- Tabs: Wszystkie, Krytyczne, Do weryfikacji, Zgodne. Counts are live at the current thresholds (existing `LevelCounts`; keep `data-testid` `count-*`). Clicking sets the same `filters.level`. The tab panel is the box below it (4.3).
- Keyboard: roving tabindex, arrows move and select, Home/End; Radix Tabs is already a dependency.

### 4.3 Queue page
Order from top: breadcrumb-free title block, summary line, alert banner (4.17) if any, **trend strip (section 6)**, tab list, tab panel, legend.

- Title block: h4 28/700, summary under it (`.p1-sum`, 16 `--ink-2`, `max-width: 75ch`): "148 spraw z ostatnich 30 dni. Na decyzję czeka 7 krytycznych. Dziś wpłynęło 29 nowych spraw, średnio wpływa 23 dziennie."
- Tab panel (`.p1-panel`): 1 px `--line`, padding 16, grid gap 16.
- Toolbar (`.p1-tool`): flex, wrap, gap `16 24`, align end, space-between. Left: search field group, label "Szukaj w kolejce" (14, 4 px above), input 40 px high, width `min(300px, 60vw)`, placeholder only as a format hint ("np. Nordhaven"), joined to a primary button "Szukaj" (40 px). Right: sort select "Sortowanie" (label 14 above, 40 px), a download link "Eksportuj CSV" (14, icon `Download` 1.125em, gap 6). **[ext]** further filters (moduł, źródło, status, data) as 40 px selects in the same right group, each with a visible label; "Wyczyść filtry" link when any is active.
- Table: wrapper `overflow-x: auto`, focusable (`tabindex="0"`, `role="region"`, `aria-label="Tabela spraw"`), `min-width: 1060px`, 14 px text, a visually hidden `<caption>`.
  - Header cells: padding `8 12`, 14/700, bottom border 2 px `--ink`, `nowrap`, bottom aligned.
  - Body cells: padding `8 12`, bottom border 1 px `--line`. Hover: cell background `--hover`. No zebra, no coloured bars, no row tint.
  - **Row height: about 40 px** (14 px text, line 1.5 = 21, plus 8 + 8 padding = 37, 40 with the 1 px rule and 36 px select). The page's own rows are about 80 px because the title wraps and has a second line `IW/2026/0412, entity`. To get 40 px rows **[ext]** the case cell keeps the title on one line (`white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 420px`, full title in `title` and in the accessible name) and the signature and entity move to their own columns. The two-line variant (title over `sub`) stays as a "Gęsty / Przestronny" density option **[ext]** only if the owner wants it.
  - Columns (7 on the page, 8 here): 1 Poziom i ryzyko (level word with icon, risk number, mini-scale on one line in dense mode), 2 Sprawa (title link 14/500), 3 Sygnatura **[ext]** (plain text, `IW/2026/0412`), 4 Źródło, 5 Moduł (numbers "1, 2" plus the legend below), 6 Naruszone kryteria ("kryt. 3, 7, 12, 14" `nowrap`, or "brak" `--muted`), 7 Status (select, 36 px high inside the table, 216 px wide), 8 Wykryto (relative time, absolute in `title`). Entity name is dropped from the row or goes into the case title tooltip; this is a choice for the owner (section 9).
- Footer (`.p1-ft`): flex, space-between, 14 `--muted`: "Pokazano 1–6 ze 148" left, pagination nav right (`aria-label="Strony kolejki"`): links and the current page as 32 x 32 min cells, padding `0 8`, link `--ink`, no underline until hover, current = `--accent` background, white text; "Następna" link. Replaces the "Następna strona" button.
- Legend (`.p1-leg`): 12 `--muted`, line 1.4, `max-width: 90ch`: "Moduły: 1 Finfluencerzy i podmioty trzecie, 2 Zgodność i informacja o ryzyku, 3 Shadow advisory. Kryteria według załącznika UKNF." (count of criteria: section 9). It makes the module numbers readable without a mouse.
- Row "fresh" highlight and "Nowe" tag: tag becomes the `bdg-new` badge (4.17) in the status cell next to the select **[ext]**; the yellow fade is deleted.

### 4.4 Level indicator and mini-scale
- Icon (own shape) plus word, inline-flex, gap 6, 700, colour `--c-*`, `nowrap`. Icon size `1.125em`, stroke 2, round caps, no fill. Never a dot, never a pill, never a fill.

| Level | Word | Shape (page symbol) | Lucide |
|---|---|---|---|
| Critical, risk from the critical threshold | Krytyczne | octagon with "!" (`i-crit`) | `OctagonAlert` |
| To verify, from the flag threshold | Do weryfikacji | magnifier (`i-rev`) | `Search` |
| Compliant, below the flag threshold | Zgodne | circle with tick (`i-ok`) | `CircleCheck` |

- Register icons: `i-warn` (`TriangleAlert`), `i-ok` (`CircleCheck`), `i-no` circle with dash (`CircleMinus`).
- **Risk number plus ruled mini-scale** (`.rk`): inline-flex, centre, gap 8. Number 700, `min-width: 2ch`, right-aligned; scale `.ms` 56 x 12: baseline 1 px `--ink-2` at `bottom: 2px`, fill bar 5 px high at `bottom: 3px`, width = risk %, colour `--m-*` of the level, radius 0; two ticks 1 x 12 px `--ink` at the flag and critical thresholds (read from settings, 20% and 70% by default). The scale is `aria-hidden`; screen readers hear "86 na 100". In the case list the cell `.lr` is a grid, gap 4, left aligned; in the dense queue level word, number and scale sit in one row **[ext]**.

### 4.5 Buttons and links
| Kind | Spec |
|---|---|
| Primary | height 40, padding `0 16`, no border, radius 0, bg `--accent`, white 16/500, icon gap 8, hover `--accent-hover` |
| Secondary | height 40, padding `0 16`, no border, radius 0, bg transparent, text `--accent`, `inset 0 0 0 1px var(--accent)`, 16/500 |
| Link | `--accent`, underline 1 px, `text-underline-offset: 3px`, hover underline 2 px; "download" links carry the 1.125em icon and the type and size ("PDF, 1,2 MB") on a second 12 px `--muted` line |
| Square step button (slider − / +) **[ext]** | 44 x 44, secondary style, icon `Minus` / `Plus` |
| Disabled | opacity .55, `cursor: not-allowed`; the reason is in text next to the control, never only a tooltip |

Rules: one primary button per panel or callout; labels verb-first; no ghost buttons (use link or secondary); no round buttons; 24 px is the AA floor, product floor 40 (44 for slider controls). The page's buttons are 40 px high, below the 44 px that `PRODUCT.md` asks for primary controls: accepted for density, see section 9.

### 4.6 Form fields and selects
- Label above the field, always visible, 14 px, margin-bottom 4. Hint under the field or label 14 `--muted`, `max-width: 64ch`.
- Input: height 40, width `min(300px, 60vw)` (100% below 640), padding `0 12`, no border, radius `4px 4px 0 0`, bg `--field`, `inset 0 -2px 0 var(--ink-2)`, 16 px `--ink`.
- Select: height 40 (36 inside the table), radius `4px 4px 0 0`, same bg and bottom edge, 14 px `--ink` (never white text), `appearance: none`, 14 px chevron (stroke `#161616`) at right 10, padding `0 32 0 10`, `min-width: 172`, `max-width: 220`; in the table 216 px.
- Number field **[ext]**: input as above, width 72, `text-align: right`, `inputmode="numeric"`.
- Checkbox/radio **[ext]**: 20 px native, `accent-color: var(--accent)`, label to the right 16 px.
- Textarea **[ext]**: input style, min-height 96, radius `4px 4px 0 0`.
- Error: icon `CircleAlert` plus words in `--c-red` 14 px under the field; field gets `inset 0 -2px 0 var(--c-red)`; `aria-invalid` and `aria-describedby`.

### 4.7 Panels and tab panels
- Panel: 1 px `--line`, no radius, padding 16 (12 narrow), grid gap 16, white. Title h5 20/700; subtitle 16 `--ink-2` `max-width: 75ch`. A panel title row with an action is flex, space-between, wraps.
- No panel header bar with its own background, no nested panels. Inside a panel use h5 plus tables, key–value lists and rules.

### 4.8 Recommendation callout (`mise en avant`)
`--tint` background, `border-left: 4px solid var(--accent)`, no other border, radius 0, padding 24 (16 narrow), grid gap 12. h5 "Rekomendacja: eskalować" (20/700, `--ink`), one paragraph `max-width: 62ch` that includes the next step, then an actions row (flex, gap `12 16`, margin-top 4, 14 px): primary "Przekaż do postępowania" and a muted note ("Decyzję zatwierdza analityk prowadzący.") or the link "Zmień zalecenie". The same tint for every recommendation; the level is not repeated in the callout. Remove `.reco--escalate/explain/none`.
The same left-rule callout is the **only** pattern for "important note" on any page (preview-not-saved note, section 5; demo-data note; read-only note). Variant **[ext]** for an error: same shape with the left rule in `--c-red`, background white, icon plus bold lead word.

### 4.9 Case page
Order: breadcrumb, badges, title (h4 28/700, 24 narrow), two columns.
- Badges (`.p1-bdg`): flex, gap 8. `bdg`: inline-flex, gap 4, padding `2 8`, radius 4, 14/700. "Krytyczne": icon plus word, `--c-red` on `--red-soft`. "Nowe": `--accent` on `--accent-soft`. These are the only badges with a fill; "Zgodne"/"Do weryfikacji" in the header appear as the plain level word (4.4), not as a badge.
- Grid `.p1-case`: `minmax(0, 1.55fr) minmax(0, 1fr)`, gap 32, align start; one column below 900 px of container width. Left column (gap 24): case data, assessment, recommendation, workflow (4.12). Right column (gap 24): registers (4.11), evidence (4.13), downloads, decision history (4.12).
- **Key–value case data** (`.p1-meta`, `dl`): grid `11em minmax(0, 1fr)`, top border 1 px `--line`, 14 px; `dt` 500 `--ink-2` padding `8 16 8 0`, `dd` padding `8 0`; both with 1 px `--line` bottom. Rows: Sygnatura, Wykryto ("21.11.2026, 09:14"), Podmiot ("name, KRS ..."), Źródło, Moduły ("1 Finfluencerzy i podmioty trzecie; 2 ..."), Podstawa prawna. Single column on phone (`dt` loses its rule).
- Parties card, relationships, financials, forensics, debate, 18-rule matrix: tables in the 14 px register style (4.11), no fills; graphs keep their own rules (section 6). Not on the page, see section 9.
- Downloads (`.p1-files`): `ul`, each item padding `8 0`, 1 px `--line` bottom (and top on the first); link 500 with download icon, under it 12 `--muted` "PDF, 1,2 MB".

### 4.10 Assessment (verdict) block
1. h5 "Ocena" (20/700).
2. Verdict sentence (`.p1-verd`): 18/1.45, `max-width: 60ch`. It starts with the finding word in 700 and `--c-red` for a violation ("Naruszenie."), `--c-amb` ("Wymaga weryfikacji."), `--c-grn` ("Brak naruszeń."), then one sentence of reason and the violated criteria: "Naruszone kryteria: 3, 7, 12 i 14." Words, not numbers, carry the verdict.
3. Level and Compliance Score row **[ext]** under the sentence: level indicator (4.4), "Compliance Score" 14 `--muted`, value 28/700, "z 100" 14 `--muted`.
4. Dual ruled scale (4.10.1).
5. Numbered findings **[ext]**: `ol`, counter "1." in `--muted`, columns `1.75em / 1fr`, 8 px gap, criterion as `<small>` "Kryt. 3" (14 `--muted`).

**4.10.1 Dual ruled scale** (`figure.ds`): grid `9.5em minmax(0, 1fr)`, column gap 16.
- Row 1 (22 px): threshold names "oznaczenie" at the flag threshold and "krytyczne" at the critical one; 12/700 `--ink`, `border-left: 2px solid --ink`, `padding-left: 8`, sit on the baseline.
- Row 2 (18 px): risk labels every 10, 12 `--muted`, the two threshold values 700 `--ink`; first label starts at the left edge, last ends at the right edge. Row label "Ryzyko" (14 `--ink-2`).
- Row 3 (24 px): axis. Three 4 px bars at `top: 10`: 0 to flag `--m-grn`, flag to critical `--m-amb`, critical to 100 `--m-red`; 1 px ticks `--ink-2` every 5 (14 px high at tens, 8 px between); threshold lines 2 x 24 px `--ink`.
- Row 4 (18 px): Compliance Score labels (100 minus risk) every 10; row label "Compliance Score".
- Row 5: caption 14 `--ink-2`, values in 700 `--ink`: "Odczyt: ryzyko 86 z 100, Compliance Score 14. Progi na skali ryzyka: oznaczenie od 20, krytyczne od 70."
- Needle spanning rows 2 to 4: 2 px `--ink` line at the risk value, 6 px triangle pointing down at `top: 21`. Everything but the caption is `aria-hidden`. Thresholds are read from settings. Below 640 px the label column and every other label are dropped and the caption gains "Górna skala to ryzyko, dolna to Compliance Score (100 minus ryzyko)."

### 4.11 Register checks
h5 "Rejestry", a ruled table (`.rt`, 14 px), no panel. Columns: **Rejestr** (name; link "otwórz rejestr" in a new tab, with "(otwiera się w nowej karcie)" for screen readers; optional 12 `--muted` second line with subject or detail), **Wynik** (icon plus words, `--c-*`, weight 500: "wpis aktywny", "na liście od 14.10.2026", "brak wpisu", "nie sprawdzono"), **Stan na** (`snapshot_date`, `21.11.2026`, `nowrap`; "brak migawki" if null). Header `padding 8 12 8 0`, bottom 2 px `--ink`, 700; body the same padding, bottom 1 px `--line`, `vertical-align: top`.

| Status | Icon | Colour |
|---|---|---|
| `listed` | ok | `--c-grn` |
| `warning_listed` | warn | `--c-red` |
| `inactive` | warn | `--c-amb` |
| `not_listed` | no | `--c-amb` |
| `not_checked` | no | `--muted` |

The page puts "brak wpisu" in the firm-register row in amber; whether it is good or bad depends on the register: review with the domain owners (section 9).

### 4.12 Case workflow actions and decision history **[ext]**
Not on the page; built from the existing `WorkflowPanel`, `TransitionDialog`, `DecisionHistory`, `StatusStepper`.
- **Workflow** (left column, after the recommendation callout): h5 "Postępowanie". A key–value row "Status" with the current status as plain text 700, and the status select (40 px) with the primary button "Zmień status" only if the change needs a note; otherwise the select commits on change like in the queue. Next-step actions as a row: primary (the recommended step, e.g. "Przekaż do postępowania"), secondary others ("Zamknij: bez naruszeń", "Zamknij: naruszenie"). Supervisor-only actions (approve escalation) are visible to analysts as disabled with the text next to them "Zatwierdza kierownik." Not hidden.
- **Transition dialog**: modal (4.17 overlay rules), title h5 "Zmiana statusu: {from} na {to}", a required note textarea with visible label "Uzasadnienie decyzji" (hint "Wpis trafia do historii decyzji i do dziennika audytu."), buttons: primary "Zapisz decyzję", secondary "Anuluj". A confirmation naming what happens for destructive or final steps: "Zamknięcie sprawy jako naruszenie jest ostateczne bez zgody kierownika." Errors inline under the field.
- **Status stepper**: replaced by a text line "Status: W analizie" plus the history; no graphical stepper (the page has none).
- **Decision history** (right column): h5 "Historia decyzji", a ruled table: **Data** (`nowrap`, `21.11.2026, 09:14`), **Kto** (name, role in `--muted`), **Decyzja** (e.g. "Nowe → W analizie", 500), **Uzasadnienie** (text, wraps). 14 px, `rt` style, newest first, "Pokaż starsze" link after 10 rows. Empty: "Brak decyzji. Pierwszy wpis powstanie po zmianie statusu."

### 4.13 Evidence viewer **[ext]**
Built from the existing `EvidenceDrawer`, `ScreenshotEvidence`, `VisualsBlock`, `EvidenceChips`, `SourceText`.
- Opens as a page-level panel in the right column, not a drawer with a shadow; on narrow screens a full-width panel. Evidence references in text are plain links (`kryt. 3`, `zrzut 2`), never chips with fills.
- **Screenshot**: image in a 1 px `--line` frame (no radius, no shadow), `max-width: 100%`, caption 12 `--muted` ("Zrzut ekranu, post z 20.11.2026, zarchiwizowano 21.11.2026 09:14, SHA-256 skrócone do 12 znaków"). Zoom control: secondary button "Powiększ" opens the image in an overlay; keyboard: Esc closes.
- **Violation boxes** on the screenshot: 2 px `--c-red` outline (offset −0), no fill, with a 20 x 20 square numeral label in the top-left corner (white 14/700 on `--c-red`, number = finding number). Three or more boxes alternate nothing: all boxes use the same colour and are identified by number, never by colour. Box and numeral have `forced-colors` fallback `CanvasText`.
- **Legend below the image**: ordered list "1. Stopa zwrotu podana jako pewna. Kryt. 3", each linking to the box (focus moves to it, `aria-current`). Screen readers get the list as the alternative; the image has `alt` summarising the content.
- **Source text**: block with 1 px `--line` left rule 4 px `--line-strong`, the quoted phrase wrapped in `<mark>` styled `--sel` background, `--ink` text (no yellow).
- Toolbar above the image (14 px): "Pobierz zrzut" link, "Otwórz źródło" link (new tab), "Pokaż pola naruszeń" checkbox (default on).

### 4.14 Login page **[ext]**
Page shell without the header nav: only row 1 of the header (service name, tagline). Centred single column `max-width: 440`, padding `48 24 24`. h4 "Logowanie"; summary "Zaloguj się, aby pracować w kolejce spraw." Panel (4.7) with two fields (labels "Adres e-mail" and "Hasło", input style), primary button "Zaloguj się" (full width of the panel on phone, otherwise auto), error as the red-rule callout (4.8): "Nie udało się zalogować. Sprawdź adres i hasło, potem spróbuj ponownie." Under the panel a 14 `--muted` line "Narzędzie analityczne UKNF, dane przetwarzane lokalnie." No illustration, no remembered-password tricks. Autofill and password managers allowed (`autocomplete="username"`/`"current-password"`).

### 4.15 Audit log page (`/audyt`, supervisor) **[ext]**
Breadcrumb, h4 "Dziennik audytu", summary "Kto, kiedy i co zmienił w sprawach i progach. Wpisów nie można edytować." Same tab-panel frame as the queue but without level tabs. Toolbar: search "Szukaj we wpisach", selects "Użytkownik", "Zdarzenie" (status, próg, eksport, logowanie), date range as two fields "Od" and "Do" (`dd.mm.rrrr` hint), link "Eksportuj CSV". Table (14 px, dense, 40 px rows): **Data i godzina** (`nowrap`), **Użytkownik**, **Zdarzenie**, **Sprawa** (link to case or "—"), **Szczegóły** (`old → new` in plain text; long text truncated with "Pokaż" link). Footer and pagination as in 4.3. An analyst who types the URL sees the page with a red-rule callout "Dziennik audytu jest dostępny dla kierownika." and a link back to the queue (not a bare 404).

### 4.16 Public report form **[ext]**
Page for members of the public (no session, no nav; row 1 of the header only). `max-width: 640`, h4 "Zgłoś podejrzaną reklamę", summary "Zgłoszenie trafi do kolejki analityków UKNF. Nie musisz podawać danych osobowych." Fields, labels always visible: "Adres strony lub konta" (input, required), "Co jest nie tak?" (textarea), "Zrzut ekranu (opcjonalnie)" (file input, hint "PNG lub JPG, do 5 MB"), "Twój adres e-mail (opcjonalnie)" (hint "Podaj go tylko, jeśli chcesz dostać odpowiedź."). Required marked in the label as "(wymagane)", never only with an asterisk. Blur-first validation; the error summary is a red-rule callout at the top listing the fields as links. Primary button "Wyślij zgłoszenie". Success state replaces the form: h5 "Zgłoszenie przyjęte", "Numer zgłoszenia: ZG/2026/0183. Zapisz go, jeśli chcesz zapytać o sprawę." and a secondary "Wyślij kolejne". No CAPTCHA illustrations; rate limiting is server-side.

### 4.17 Alerts, toasts, overlays, empty and loading states
- **Alert banner** (new critical case): white block, 1 px `--line`, `border-left: 4px solid var(--c-red)`, padding `12 16`, icon `OctagonAlert` 24 px `--c-red`, "Nowa sprawa krytyczna" 700, title as link, secondary button on the right, `role="status"`. No red fill.
- **Toast** **[ext]**: bottom right, width up to 380, white, 1 px `--ink-2` border, left rule 4 px (`--accent` info, `--c-grn` success, `--c-red` error), padding 12, icon plus text, close button 40 px, no shadow.
- **Dialog, menu, command palette** **[ext]**: white, 1 px `--ink-2`, radius 0, no shadow; dialog top border 2 px `--accent`; menu items 40 px high, hover `--hover`, selected has a 4 px left `--accent` rule.
- **Empty**: inside the panel, left-aligned: one title (18/700), one sentence (`--muted`, `max-width: 52ch`), one action (secondary button or link). No illustration, no icon disc. Filtered to zero: name the filter and offer "Wyczyść filtry".
- **Loading**: under 100 ms nothing; to about 1 s inline "Wczytywanie…" next to the control; longer, skeleton rows in `--field` (flat, no shimmer) under the real table header; no pulse under `prefers-reduced-motion`.
- **Error state**: title "Nie udało się wczytać kolejki", one sentence with the cause if known, button "Spróbuj ponownie". Icon `--c-red` optional, never a red fill.
- Copy: what happened and what to do next; never blame the user.

## 5. Calibration screen (new design)

Goal: a first-time official understands in ten seconds what the threshold does, from one slider and one sentence, and sees the false-positive/false-negative trade-off (the challenge requirement) without knowing what precision or recall mean. Everything for analysts who do know is behind one closed disclosure.

### 5.1 Wireframe (container 960 px; real widths in 5.2)

```
Kolejka spraw | [Kalibracja] | Skanowania | Dziennik audytu          <- header row 2 (4.1)

Kalibracja progów                                                    <- h4 28/700
Wybierz, od jakiego wyniku ryzyka system oznacza sprawę do kolejki.
Sprawdzamy to na 45 sprawach, które analitycy już ocenili.            <- 16 ink-2

Obowiązują progi globalne: oznaczenie od 20, krytyczne od 70.         <- status line, 14 ink-2; when the preview
Ustawił J. Nowak, 14.11.2026.                                            differs it becomes this callout (same slot):
 ##############################################################
 # Podgląd, niezapisane. Progi globalne to 20 i 70, tu 35 i 70. #   <- tint, 4px accent left rule
 # [Zapisz jako progi globalne]  [Przywróć globalne]            #   <- analyst: only "Przywróć globalne" and
 ##############################################################        "Progi globalne zapisuje kierownik."

+------------------------------------------------------------------+ <- panel 1px line, pad 16
| Próg oznaczenia sprawy (0–100)                                     | <- label 16/700
| Od tego wyniku ryzyka sprawa trafia do kolejki.                    | <- hint 14 muted
|                                                                    |
| [ - ]  |------------------[#]=====================|  [ + ]  [ 35 ]| <- 44px buttons, slider, number field
|        0    10   20   30   40   50   60   70   80   90   100       | <- ruled axis, labels 12
|                          ¦ oznaczane od 35      ¦ krytyczne od 70  |
|                                                                    |
| Przy progu 35 system oznacza 21 z 45 sprawdzonych spraw. W tym     | <- live sentence 20/1.45
| 19 rzeczywistych naruszeń i 2 fałszywe alarmy. 4 naruszenia        |    role="status"
| zostają przeoczone.                                                |
|                                                                    |
| Fałszywe alarmy                    Przeoczone naruszenia           | <- two columns, h5 18/700
| zgodne sprawy oznaczone przez      naruszenia, których system      |    gloss 14 muted
| pomyłkę                            nie oznaczył                    |
| 2  z 22 zgodnych spraw             4  z 23 naruszeń                | <- count 28/700 + 14 muted
| [###-------------------------]     [#####----------------------]   | <- ruled bar 16px
| Niższy próg: mniej przeoczonych naruszeń, więcej fałszywych        |
| alarmów. Wyższy próg: odwrotnie.                                   | <- 14 muted, full width
|--------------------------------------------------------------------|
| Trafność alertów  90%              Wykrywalność naruszeń  83%      | <- 18/700 + 14 label
| 19 z 21 alertów to rzeczywiste     wykryto 19 z 23 naruszeń        |
| naruszenia                                                         |
|--------------------------------------------------------------------|
| [Ustaw zalecany próg: 30]  Próg 30 najlepiej godzi oba cele:       |
|                            wykrywa 87% naruszeń przy 87% trafnych |
|                            alertów.                                |
|--------------------------------------------------------------------|
| Próg krytyczny                                                     |
| [ 70 ]  Od tego wyniku sprawa jest krytyczna i wywołuje alert.     |
| W kolejce przy tych progach: Krytyczne 7 · Do weryfikacji 24 ·     |
| Zgodne 117                                                         |
|--------------------------------------------------------------------|
| Progi globalne ustawił J. Nowak, 14.11.2026.   (analyst note)      |
+------------------------------------------------------------------+

> Szczegóły dla analityka   macierz pomyłek, rozkład wyników, ...    <- <details>, closed
  (open: confusion matrix + measures table, score histogram,
   precision/recall curve, lists of false positives and negatives,
   cases rated by analysts)
```

### 5.2 Measurements and structure
- Page: breadcrumb-free; h4 28/700 "Kalibracja progów"; summary 16 `--ink-2`, `max-width: 64ch`. The old long paragraph is cut; the sentence about the critical threshold's non-effect on the matrix moves into the hint (below).
- Panel: 1 px `--line`, padding 16, content `max-width: 960`, left aligned; sections inside separated by 1 px `--line` rules with padding `24 0` (first section padding-top 0). Panel is one block, not several cards.
- **Status and preview note** (a block directly under the page summary, above the panel, with a reserved `min-height: 72px` so nothing below it moves when it changes). Default content: the global line, 14 `--ink-2`: "Obowiązują progi globalne: oznaczenie od 20, krytyczne od 70. Ustawił J. Nowak, 14.11.2026." When the preview differs from the global values the line is replaced in place by a left-rule callout (4.8, padding 16, grid gap 8): bold lead "Podgląd, niezapisane." then "Progi globalne to 20 i 70, a w tym podglądzie 35 i 70. Zmiana działa tylko w tej przeglądarce, dopóki jej nie zapiszesz." Actions row (14 px, gap 12): supervisor: primary "Zapisz jako progi globalne" and secondary "Przywróć globalne"; analyst: secondary "Przywróć globalne" and the muted text "Progi globalne zapisuje kierownik."
- **Control block**: label "Próg oznaczenia sprawy" (16/700) `for` the number field; hint 14 `--muted`: "Od tego wyniku ryzyka (0–100) sprawa trafia do kolejki. Strzałki na klawiaturze zmieniają próg o 1." Row (flex, centre, gap 12): `−` button 44 x 44, slider flex 1, `+` button 44 x 44, number field 72 x 40 (right aligned, `min 0 max 100`, own label "Wartość" visible 12 px above is not needed: the field has `aria-labelledby` the main label and is placed right of the buttons). `−`/`+` step 1; hold repeats after 400 ms (every 80 ms).
- **Slider** (Radix Slider kept, restyled): hit area 44 px high; on the 0 to 100 ruled axis taken from the page (`.cal-ax`): 2 px `--ink` line, ticks 1 px every 5 (10 px at tens, 6 between), labels 12 `--muted` every 10 (odd tens hidden below 640 px); thumb **28 x 28 square, `--accent` with a 3 px white border (visible 22 px)**, `outline-offset: 4px` on focus. From the thumb to 100 a 4 px `--accent` bar sits on the axis (what is flagged); label above the bar start "oznaczane od 35" (12/700 `--ink`, left rule 2 px). Critical threshold: 1 px dashed `--ink-2` vertical line on the axis with label "krytyczne od 70" (12 `--ink-2`, `padding-left: 5`). The slider changes only the flag threshold. Value shown in the number field only (no second large output).
- **Live sentence** (`role="status"`, `aria-live="polite"`, `aria-atomic="true"`): 20/1.45, `max-width: 60ch`, numbers in 700. Visual update on every change; the live region content is updated after 400 ms without change (debounce) so screen readers do not read every step while dragging.
- **Two opposing quantities** (the core visual): grid two equal columns, gap 32 (stack below 640). Each: h5 18/700 name, 14 `--muted` gloss, then the count in 28/700 (line 1) and, on the same baseline, " z 22 zgodnych spraw" 14 `--ink-2`; then a bar. Left "Fałszywe alarmy", gloss "zgodne sprawy oznaczone przez pomyłkę". Right "Przeoczone naruszenia", gloss "naruszenia, których system nie oznaczył". Bar: height 16, track 1 px `--ink-2` outline on white, fill `--accent` from the left, width = count / its own population (22 zgodnych, 23 naruszeń), minimum visible width 2 px when count > 0, radius 0, `aria-hidden` (the count and the fraction are the accessible value; also give each bar a `role="img"` with `aria-label="2 z 22"`). No red or green: this is not a level. Bars are decorative twins of the numbers; their widths animate nothing. Under both a caption 14 `--muted` spanning the grid: "Niższy próg: mniej przeoczonych naruszeń, ale więcej fałszywych alarmów. Wyższy próg: odwrotnie."
- **Secondary figures**: `dl` with two columns, gap 32, top rule 1 px `--line`, padding-top 16. `dt` 14 `--ink-2` 500: "Trafność alertów" and "Wykrywalność naruszeń", each wrapped in `<abbr title="po angielsku: precision">` (resp. `recall`) for pointer users; the English terms also appear in plain text in the details (5.4), so a tooltip is never the only place. `dd` value 18/700 "91%", `dd` fraction 14 `--ink-2`: "19 z 21 alertów to rzeczywiste naruszenia" and "wykryto 19 z 23 naruszeń". If a value is undefined: "brak danych" and the reason in the fraction line ("żadna sprawa nie jest oznaczona").
- **Zalecany próg**: row (flex, wrap, gap 16, top rule). Secondary button "Ustaw zalecany próg: 30" (label includes the value). Text 14 `--ink-2`: "Próg 30 najlepiej godzi oba cele: wykrywa 87% naruszeń przy 87% trafnych alertów." (the F1 criterion is explained only in the details). When already at the suggestion: the button is disabled and the text reads "To jest zalecany próg: najlepiej godzi wykrywanie naruszeń z liczbą fałszywych alarmów." Value comes from `bestF1Threshold` (ties go to the lower threshold, as today). Clicking sets only the preview.
- **Próg krytyczny** (secondary): label "Próg krytyczny" (16/500), number field 72 x 40, text beside it 14 `--ink-2`: "Od tego wyniku sprawa jest krytyczna i wywołuje alert. Nie wpływa na fałszywe alarmy ani przeoczone naruszenia." When the flag threshold would exceed it, existing normalisation holds (flag never above critical): show hint under the field "Próg krytyczny nie może być niższy niż próg oznaczenia ({flag})." under `role="status"`. Below it one line 14: "W kolejce przy tych progach:" then level words with counts, each as level icon + word + count (keeps `data-testid` `queue-flagged`, `queue-red`, `queue-orange`, `queue-green`; "Oznaczone: 31, w tym Krytyczne 7").
- **Global state line** (panel foot, 14 `--muted`): supervisor sees nothing extra when saved (the primary button lives in the preview callout, disabled and absent when nothing differs); analyst sees always "Progi globalne ustawił {updated_by}, {date}. Zmienia je kierownik." Keep `data-testid="global-thresholds"` on the status line above the panel.

### 5.3 Copy (all strings, Polish)
Plural helper `pl(n, one, few, many)`: 1 `one`; n mod 10 in 2–4 and n mod 100 not in 12–14 `few`; else `many`. (Note: the page's helper tests `n % 100 < 10 || n % 100 >= 20`, which is equivalent.)

| Where | String |
|---|---|
| Title | Kalibracja progów |
| Summary | Wybierz, od jakiego wyniku ryzyka system oznacza sprawę do kolejki. Sprawdzamy to na {N} {pl(N,"sprawie","sprawach","sprawach")}, które analitycy już ocenili. |
| Global line, default | Obowiązują progi globalne: oznaczenie od {o}, krytyczne od {r}. Wartości domyślne, jeszcze nie zmieniane. |
| Global line, set | Obowiązują progi globalne: oznaczenie od {o}, krytyczne od {r}. Ustawił {kto}, {dd.mm.rrrr}. |
| Preview callout | **Podgląd, niezapisane.** Progi globalne to {o} i {r}, a w tym podglądzie {o'} i {r'}. Zmiana działa tylko w tej przeglądarce, dopóki jej nie zapiszesz. |
| Buttons | Zapisz jako progi globalne · Zapisywanie… · Przywróć globalne ({o} / {r}) |
| Analyst note | Progi globalne zapisuje kierownik. |
| Save success toast | Zapisano progi globalne: oznaczenie od {o}, krytyczne od {r}. Obowiązują wszystkich analityków i alert na żywo. |
| Save error | Nie zapisano progów. {powód}. Spróbuj ponownie. |
| Control label | Próg oznaczenia sprawy |
| Control hint | Od tego wyniku ryzyka (0–100) sprawa trafia do kolejki. Strzałki na klawiaturze zmieniają próg o 1. |
| Step buttons (accessible names) | Zmniejsz próg o 1 · Zwiększ próg o 1 |
| Axis labels | oznaczane od {o} · krytyczne od {r} |
| Live sentence | Przy progu {t} system oznacza {a} z {n} sprawdzonych spraw. W tym {tp} {rzeczywiste naruszenia} i {fp} {fałszywe alarmy}. {fn} {naruszenia} {zostają przeoczone}. |
| Live sentence, zero flagged | Przy progu {t} system nie oznacza żadnej z {n} sprawdzonych spraw. {fn} {naruszeń zostaje przeoczonych}. |
| Live sentence, all caught | …W tym {tp} … i {fp} …. Żadne naruszenie nie zostaje przeoczone. |
| Quantity titles | Fałszywe alarmy · Przeoczone naruszenia |
| Quantity gloss | zgodne sprawy oznaczone przez pomyłkę · naruszenia, których system nie oznaczył |
| Quantity fractions | z {zg} zgodnych spraw · z {nar} naruszeń |
| Trade-off caption | Niższy próg: mniej przeoczonych naruszeń, ale więcej fałszywych alarmów. Wyższy próg: odwrotnie. |
| Secondary | Trafność alertów · {tp} z {a} alertów to rzeczywiste naruszenia · Wykrywalność naruszeń · wykryto {tp} z {nar} naruszeń |
| Tooltips (`abbr`) | po angielsku: precision · po angielsku: recall |
| Recommend button | Ustaw zalecany próg: {s} |
| Recommend text | Próg {s} najlepiej godzi oba cele: wykrywa {recall}% naruszeń przy {precision}% trafnych alertów. |
| Recommend, already | To jest zalecany próg: najlepiej godzi wykrywanie naruszeń z liczbą fałszywych alarmów. |
| Critical | Próg krytyczny · Od tego wyniku sprawa jest krytyczna i wywołuje alert. Nie wpływa na fałszywe alarmy ani przeoczone naruszenia. |
| Critical clamp | Próg krytyczny nie może być niższy niż próg oznaczenia ({o}). |
| Queue effect | W kolejce przy tych progach: oznaczone {x}, w tym krytyczne {y}. |
| Details summary | Szczegóły dla analityka (right, `--muted`: macierz pomyłek, rozkład wyników, krzywa, lista spraw) |

Forms for the sentence ({n} = the count):

| Noun | 1 | 2–4 | 0, 5+ |
|---|---|---|---|
| rzeczywiste naruszenie | rzeczywiste naruszenie | rzeczywiste naruszenia | rzeczywistych naruszeń |
| fałszywy alarm | fałszywy alarm | fałszywe alarmy | fałszywych alarmów |
| naruszenie (last sentence) | 1 naruszenie zostaje przeoczone | {n} naruszenia zostają przeoczone | {n} naruszeń zostaje przeoczonych |
| sprawa in "z N spraw" | z 1 sprawdzonej sprawy | z {n} sprawdzonych spraw | z {n} sprawdzonych spraw |

Worked example: threshold 20, 45 cases, 21 flagged: "Przy progu 20 system oznacza 21 z 45 sprawdzonych spraw. W tym 19 rzeczywistych naruszeń i 2 fałszywe alarmy. 4 naruszenia zostają przeoczone." (If the owner prefers the wording "19 to rzeczywiste naruszenia, 2 to fałszywe alarmy", the plural table above still applies; "19 to rzeczywiste" is non-standard for numerals from 5 up.)

### 5.4 Disclosure "Szczegóły dla analityka"
- Native `<details>` (not open by default, no stored state). Summary: full-width row, height 44, border-top and border-bottom 1 px `--line`, 16/700 `--accent`, chevron icon rotating 90 degrees (no animation under reduced motion), right side 14 `--muted` hint text. Focus ring as everywhere.
- Content padding `16 0`, grid gap 24. **Render the Recharts charts only after the first open** (a chart inside a closed `<details>` measures 0 width); keep results in state so reopening is instant. Tests and e2e that read `cm-*`, `metric-*`, `false-positives` must open the disclosure first.
- Inside, in this order, with h5 titles 20/700:
  1. **Macierz pomyłek** (table in the page's `.cm` style: caption "Macierz pomyłek przy progu {t}", columns Oznaczone / Nieoznaczone / Razem, rows Naruszenie / Zgodne / Razem; cell: count 18/700 over 12 `--muted` meaning "trafne alarmy (TP)", "przeoczone (FN)", "fałszywe alarmy (FP)", "trafnie pominięte (TN)"; header bottom 1 px `--ink`, footer top 1 px `--ink`, no cell fills). This is the English-term home.
  2. **Miary** (`.mtab`: Miara | Wartość | Z czego wynika): "Trafność alertów (precyzja, precision)", "Wykrywalność naruszeń (czułość, recall)", "F1" with "średnia harmoniczna obu miar; według niej wyznaczamy zalecany próg". Values 18/700 right aligned.
  3. **Rozkład wyników ryzyka**: `ScoreHistogram`, bars `--u-off` (zgodne) and `--accent` (naruszenia) with labelled legend, threshold lines per 6. 
  4. **Precyzja i czułość a próg**: `PrCurve`, two series (solid `--accent` for precyzja, dashed `4 3` `--ink` for czułość), direct labels, vertical line at the threshold.
  5. **Sprawy błędnie sklasyfikowane przy tym progu**: `MisclassifiedList` as two plain tables side by side ("Fałszywe alarmy ({n})", "Przeoczone naruszenia ({n})"): score (700, right), title link, source, module numbers, "analityk" badge-less note. Rows 40 px.
  6. **Oznaczone przez analityków** (if any): same table style.
- Not in the page, so **[ext]**: all of 5.4's inner styles follow the register style (14 px, 2 px header rule, 1 px row rules).

### 5.5 States
| State | What changes |
|---|---|
| Loading | Panel with skeleton (title line, 44 px control row, three text lines); details hidden |
| Error | `ErrorState` "Nie udało się wczytać zbioru oznaczonego" + "Spróbuj ponownie". Threshold control and queue effect stay usable (they need no labelled set) |
| No labelled cases | Control, axis, critical field and queue effect stay. Live sentence becomes "Przy progu {t} system oznacza {a} z {m} spraw w kolejce. Nie wiemy, ile z nich to pomyłki, bo brak ocenionych spraw." The quantity block, secondary figures, recommend row and details are replaced by an empty state (4.17): title "Brak ocenionych spraw", text "Żeby pokazać, ile fałszywych alarmów i przeoczonych naruszeń daje próg, system potrzebuje spraw ocenionych jako „naruszenie” lub „zgodne”. Oceń trafność alarmów w sprawach albo zaimportuj próbki z etykietami.", action link "Przejdź do kolejki" |
| Only one class labelled | The missing quantity shows "—" with "brak spraw zgodnych w zbiorze" (or "naruszeń"); undefined measures read "brak danych"; recommend row hidden |
| Small set (fewer than 30 labelled, **[ext]** threshold) | Muted line under the summary: "Zbiór jest mały ({N} spraw). Wyniki mogą się zmienić po ocenie kolejnych spraw." |
| Preview equals global | Status line only; no callout; save button absent (analyst) or absent (supervisor) |
| Preview differs, supervisor | Callout with both buttons; "Zapisz jako progi globalne" primary |
| Preview differs, analyst | Callout with "Przywróć globalne" and "Progi globalne zapisuje kierownik." |
| Saving | Primary button label "Zapisywanie…", disabled; controls stay live |
| Save error | Red-rule callout under the preview callout, `role="alert"` |
| Flag at critical ceiling | Hint line under the critical field |
| Reduced motion | Bars and thumb jump, no transitions |

### 5.6 Component map (files under `services/frontend/src`)
| Existing | Fate |
|---|---|
| `pages/CalibrationPage.tsx` | Simplified. Keeps hooks and logic; drops the stacked panels and the `calib-grid`. Renders: title, global/preview status, one panel (`ThresholdControl`, `LiveSentence`, `TradeOff`, `SecondaryMeasures`, `RecommendedThreshold`, `CriticalThreshold`, queue effect), then `<details>`. Adds the plural helper (`domain/format.ts` or `domain/plural.ts`) |
| `components/calibration/ThresholdControl.tsx` | Simplified. Only the flag slider (Radix), `−`/`+`, number field, "oznaczane od" bar; the secondary slider is removed. The critical field, the recommend button and the restore button move out into their own small components or into the page. Props lose `suggested` and `onReset`/`isGlobal`/`globalThresholds` |
| `components/calibration/MetricsRow.tsx` | Simplified, becomes the secondary figures (two items, drops F1, 18 px values, new names). `data-testid` `metric-precision`, `metric-recall` kept; `metric-f1` moves into the details table |
| `components/calibration/ConfusionMatrix.tsx` | Moved into the disclosure. Becomes the ruled table with totals, no cell fills (`cm__cell--good/bad/warn` classes deleted), keeps `cm-tp/fn/fp/tn` test ids |
| `components/calibration/ScoreHistogram.tsx` | Moved into the disclosure, restyled (4.17 chart rules), lazily mounted |
| `components/calibration/PrCurve.tsx` | Moved into the disclosure, off-palette teal replaced (section 6), lazily mounted |
| `components/calibration/MisclassifiedList.tsx` | Moved into the disclosure, two tables instead of badge lists; keeps `false-positives`, `false-negatives` test ids |
| New (small) | `TradeOff.tsx` (two quantities and bars), `LiveSentence.tsx` (sentence, plural forms, live region), `RecommendedThreshold.tsx`, `CriticalThreshold.tsx`, `PreviewNote.tsx` (callout plus save/restore), `Details.tsx` (disclosure wrapper that mounts charts after the first open) |
| `hooks/useThresholds.tsx`, `domain/calibration.ts`, `domain/levels.ts` | No change in logic |
| `styles/calibration.css` | Rewritten: removes `.thr__track` pill, `.thr__secondary`, `.cm__cell--*`, `.metrics` 3-column grid |

## 6. Charts (Recharts) and the trend strip
- Chrome: no background; grid lines `--line`, 1 px, horizontal only; axis line `--ink-2`; tick text 12 px `--muted` Public Sans (`.recharts-text`); no legend inside the chart: text legend 14 `--ink-2` with a 2 px line or 10 px square swatch.
- Series colour: `--accent` (first), `--ink` dashed `4 3` (second), `--muted` (third). The teal `#0e8f8f` in `PrCurve.tsx` goes. Series are also distinguished by line style and direct labels. Level colours only for level series, labelled by word.
- Threshold reference lines: flag 2 px solid `--ink`, critical 1 px dashed `--ink-2`, labels "20" and "70" in 12/700 `--ink`.
- Bars radius 0. Tooltip (`ChartTip`): white, 1 px `--ink-2` border, radius 0, padding `8 12`, 14 px, no shadow. No animation (`isAnimationActive={false}` stays).
- **Trend strip (kept on the queue page; the challenge requires trend charts)**. Placed between the summary line and the tab list as a bordered section, 1 px `--line`, padding 16, grid gap 8, **[ext]**: h5 "Napływ spraw" 18/700 with a 14 `--ink-2` sentence right of it ("29 nowych spraw dziś, średnio 23 dziennie; 10 ostatnich dni"). Under it a chart **120 px high** (full width): one series "Nowe sprawy dziennie" as `--accent` bars (radius 0, gap 2 px); a second dashed `--ink` line "Oznaczone" only if the data exist. X axis dates `dd.mm`, 12 px, every second label hidden on narrow; Y axis 3 ticks, left, 12 px. The last day bar has a direct value label. A visually hidden data table (`<table class="sr-only">`) mirrors the values and a link "Pokaż dane jako tabelę" toggles it visible (14 px, ruled). Under 640 px the strip collapses to the sentence and the link to the table. A toggle "Pokaż co 30 dni / 10 dni" **[ext]** is a segmented pair of secondary buttons only if the owner wants longer ranges.
- Compliance and risk scales in the case view are HTML and CSS rulers (4.10.1), not Recharts.

## 7. Do / don't
1. Do lead with words (verdict sentence, calibration sentence) and put numbers after; don't open a block with a gauge or a score.
2. Do show level and status as an icon of its own shape plus a word; don't use colour, dots or fills alone.
3. Do separate with 1 px rules and a 2 px rule under table headers; don't add shadows, gradients, blur or radii.
4. Do give new information a column, a key–value row or a table row; don't add panels, tiles or KPI trios.
5. Do keep tables dense: 14 px text, 8 px cell padding, about 40 px rows; don't put the entity and the signature on a second line unless the owner picks the roomy density.
6. Do read scales as rulers (axis, ticks, thresholds); don't draw semicircle gauges or progress rings.
7. Do use `--c-*` for text and `--m-*` for graphics; don't fill rows, tabs, alerts or bars with level colours. The single filled badge is "Krytyczne" in the case header.
8. Do use the left-rule callout for the one important block on a screen; don't stack callouts.
9. Do write verb-first sentence-case Polish and errors that say what to do next; don't use "OK", "Submit", exclamation marks, or English terms without a Polish gloss in the calibration screen.
10. Do keep every control keyboard-reachable with the 3 px focus ring; don't hide focus, don't rely on a tooltip for meaning, don't use icon-only buttons without a text label or tooltip and accessible name.

## 8. Implementation checklist (`services/frontend/src`)
Effort estimates are rough. Do not change logic, props of hooks or `data-testid`s (calibration test ids move into the disclosure, see 5.4).

| File | Change | Effort |
|---|---|---|
| `styles/tokens.css` | New palette (section 1), aliases kept during the swap (`--bg`, `--ink`, `--line`, `--accent`, `--focus`), radii (`--r-sm: 4px`, others 0), type scale 12 to 28, `--font`; delete `--shadow-*`, `--sidebar-w`, soft and line level tokens except `--red-soft` | S |
| `main.tsx`, `package.json`, `THIRD_PARTY_LICENSES.md` | `@fontsource/public-sans` imports (400, 500, 700; latin and latin-ext); remove `@fontsource/ibm-plex-sans`; record OFL-1.1 in both font tables | S |
| `styles/base.css` | body 16/1.5; focus 3 px, offset 2; `::selection` `--sel`; table base (`border-collapse`, 14 px); recharts text 12 px, grid `--line`; sr-only | S |
| `styles/layout.css`, `components/layout/AppShell.tsx`, `Sidebar.tsx` (delete), `TopBar.tsx` (becomes `Header`), `UserChip.tsx`, `ConnectionIndicator.tsx`, `DemoMenu.tsx`, `JobsMenu.tsx`, `CommandPalette.tsx`, `ScanDialog.tsx` | Two-row header (4.1), nav tabs, quick actions, breadcrumb component, footer line; remove sidebar, threshold card, brand mark, nav counts; keep skip link; palette and dialog restyled | M |
| `styles/ui.css`, `components/ui/Button.tsx`, `Badge.tsx`, `LevelBadge.tsx`, `ScoreRail.tsx`, `ModuleTag.tsx`, `Panel.tsx`, `States.tsx`, `Notices.tsx` | Buttons 40 px primary and secondary; `Badge` only for Krytyczne/Nowe; `LevelBadge` = icon + word; `ScoreRail` = 56 x 12 mini-scale; `ModuleTag` plain text; `Panel` 1 px rule, no radius, no head bar; fields with the bottom edge; skeleton flat; toast per 4.17 | M |
| `styles/queue.css`, `components/queue/LevelSummary.tsx` (becomes the tab list), `QueueFilters.tsx`, `QueueTable.tsx`, `StatusSelect.tsx`, `AlertBanner.tsx`, `pages/QueuePage.tsx` | Tabs with counts writing `filters.level`; toolbar (search group, sort, export, other filters); dense table (8 columns, ~40 px rows, 2 px header rule, plain-text tags); footer pagination; legend; new `TrendStrip` in place of `TrendChart` placement (4.3, section 6); alert banner left rule | M |
| `components/queue/TrendChart.tsx` | Restyle to the strip (120 px, one series, table toggle); move `ChartTip` to `components/ui/ChartTip.tsx` first (imported by `ScoreHistogram`, `PrCurve`, `ForensicsPanel`) | S |
| `styles/case.css`, `components/case/VerdictBlock.tsx`, `RecommendationCard.tsx`, `RegistryChecks.tsx`, `StatusStepper` (if present, replace by text), `pages/CasePage.tsx` | Breadcrumb, badges, key–value data, assessment with sentence first, new `ScoreScale` (HTML/CSS ruler, props risk and thresholds), left-rule callout, ruled register table with `snapshot_date` | M |
| `components/case/WorkflowPanel.tsx`, `TransitionDialog.tsx`, `DecisionHistory.tsx` | Workflow row and dialog per 4.12; history as a ruled table | M |
| `components/case/EvidenceDrawer.tsx`, `EvidenceChips.tsx`, `EvidenceContext.tsx`, `SourceText.tsx`, `VisualsBlock.tsx`, `components/evidence/ScreenshotEvidence.tsx`, `evidence.css` | Evidence panel per 4.13: framed screenshot, numbered violation boxes, legend list, `<mark>` source text, plain-link chips | M |
| `components/case/PartiesCard.tsx`, `ComplianceMatrix.tsx`, `SourcesBlock.tsx`, `DebateBlock.tsx`, `ForensicsPanel.tsx`, `FinancialsPanel.tsx`, `RelationshipGraph.tsx` | Token swap and register-table style; review visually (not on the page) | M |
| `styles/calibration.css`, `pages/CalibrationPage.tsx`, `components/calibration/*` | Per section 5.6; new small components; disclosure with lazy chart mount; plural helper with a unit test | M to L |
| `styles/auth.css`, `pages/LoginPage.tsx`, `NotFoundPage.tsx` | Login per 4.14; 404 as a plain empty state with a link to the queue | S |
| `pages/AuditPage.tsx` | Per 4.15 | S to M |
| Public report form (new page, route outside `RequireSession`) | Per 4.16 | M (needs backend endpoint) |
| Tests / e2e | Class-based selectors change (`.level-tile`, `.queue__row--*`, `.reg`); open the details before asserting `cm-*`, `metric-f1`, `false-*`; `nav-flagged` disappears with nav counts: remove or retarget | S |

Order: tokens and font, base, ui primitives, header, queue (tabs, table, trend strip), case (verdict, registers, workflow, evidence), calibration, audit, login, report form, remaining case blocks.

## 9. Open questions and issues in proposal 1

Not checked on the page (its own "Czego nie sprawdzono"): behaviour on real data, product dark theme, print of the evidence package, screen readers, touch on a real tablet. The page was viewed at 1360 px and 390 px.

### Ambiguities, inconsistencies and gaps in proposal 1
1. **Criteria count**: the queue legend says "załącznik UKNF (19 kryteriów)"; `PRODUCT.md` and the plan say 18. Page content error or product error: confirm with the domain owners before copying the legend.
2. **Row height**: the page quotes about 80 px (two-line case cell, 36 px select inside 8 px padding). The lead wants about 40 px; that needs the one-line title and extra columns (4.3) and drops the entity name from the row. Confirm the trade, or offer a density switch.
3. **Critical threshold**: fragment C says "Próg krytyczny (70) zmienia się osobno" but offers no control, and fixes it as a dashed line. The product has two thresholds, so the control is designed in 5.2.
4. **Slider thumb 22 px square**: below the 24 px AA target size and below the 44 px the product asks for; this spec uses 28 px (22 visible) and 44 px hit area **[ext]**.
5. **Buttons 40 px, tabs 44 px, fields 40 px**: `PRODUCT.md` says 44 px for primary controls. Accepted at 40 for density; `PRODUCT.md` needs the exception or the buttons go to 44.
6. **Field edge contrast**: fields are `#EEEEEE` on white (1.2:1) with only a 2 px bottom edge (9.8:1). DSFR does this; WCAG 1.4.11 is met by the edge, but users who miss it need the full-border variant if reported.
7. **Badge fills**: the only fills are `#FCE7E7` (Krytyczne) and `#E6EAF8` (Nowe). Accent-on-`#E6EAF8` contrast is not stated on the page (computed 9.5).
8. **Module column** shows bare numbers with a `title` tooltip: not keyboard or touch accessible. This spec adds the legend line; confirm it.
9. **Header**: the page header has no search, scan, jobs, demo, connection or role; their layout in 4.1 is this spec's proposal. At 1280 px row 1 is crowded; priorities and the "Menu" collapse need a visual check.
10. **Sample content** ("A. Kowalczyk", invented cases, 148, 204 test cases) is page content, not product data. The page's calibration test set (204 items, 50 violations) is far from the real set (45 in the example): copy shows counts from data only.
11. **Compliance Score** appears on the page only in the dual scale (risk 86, Score 14); the case header has no separate big number. 4.10 step 3 adds one **[ext]** at 28 px.
12. **Page width**: not defined (fragments are fluid). 1440 px max is an extension.
13. **Tab semantics**: the level tabs are a filter, not navigation between views; the panel stays the same table. The page marks them as `role="tab"`; if usability tests show confusion with the header nav, move to a segmented filter (not a pill).
14. **Phone layout**: only a 390 px preview of fragments, container queries at 900 and 640. App-wide behaviour below 960 px (table as list, header Menu) is not specified.
15. **Dark theme**: the page forces `color-scheme: light`; not designed.
16. **Trend strip**: the page has no trend chart; its range, series and placement are proposed here.
17. **Calibration sentence**: the exact owner-provided wording ("19 to rzeczywiste naruszenia") needs a grammar decision (5.3); the "unlabelled counts" threshold for the small-set warning (30) is a guess.
18. **Screens not on the page**: login, audit log, public report form, workflow actions and decision history, evidence viewer, command palette, scan dialog, jobs and demo menus, 18-rule matrix, parties, relationships, forensics, debate, financials. Specified or swapped by rule (4.12 to 4.17), not designed in the proposal.
19. **Register status colouring**: "brak wpisu" in amber (the page) versus a warning in red for the warning list: confirm per register.
20. **Public form and abuse**: the form is anonymous. Spam control and personal-data handling (the e-mail field) are product/legal decisions, not design.
21. **Branding**: the header uses a plain service name, no emblem; keep it that way so the tool is not mistaken for a state service. The page's tagline "Nadzór nad reklamą finansową" is an assumption.

## Lead decisions on the open questions (2026-11-21)

1. **18 criteria, 19 rows.** The UKNF attachment has 18 criteria; criterion 12 is split into 12a and 12b, so the matrix has 19 rows. UI copy says "18 kryteriów"; the matrix may say "19 pozycji".
2. **Queue rows keep two lines**: title link on the first, case reference + entity on the second (about 52 px). The entity name is what an analyst scans for; do not drop it.
3. **Controls are 40 px** (tabs and slider controls 44 px).
4. **Live sentence wording** as specified ("W tym 19 rzeczywistych naruszeń i 2 fałszywe alarmy").
5. **Small-set warning** under 30 labelled cases stays.
6. **"Brak wpisu" in a register is amber with icon + words**, never red on its own: absence from a list is a reason to verify, not a verdict.
7. **No dark theme.** Below 960 px the header's second row scrolls horizontally and the queue table becomes a list; phone layout is best effort, not a demo target.
8. **Trend strip:** last 30 days, stacked by level at the current thresholds, 120 px tall, on the queue page.
9. Charts inside "Szczegóły dla analityka" mount on first open; tests open the disclosure first.
10. **Calibration slider is plain (owner, 2026-11-21, overrides section 5):** one native range slider 0–100 with its value next to the label and "0" / "100" end labels. No − / + buttons, no separate number field, no ruled tick axis, no distribution marks around it. The sentence, the two opposing counts, the recommended-threshold action and the details disclosure stay.
