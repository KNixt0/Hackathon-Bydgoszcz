# DESIGN.md: InvestWatch "Miękki nadzór"

Source: proposal 4 in `docs/design/proposals.html` (CSS scoped to `.p4`, shared `.spec` rules), plus (a) from proposal 2 "Teczka": the verdict is one sentence in words before any number, (b) from proposal 1 "Urzędowy": register checks as a ruled table with source and "stan na" date. Product context: `PRODUCT.md`. Values below are copied from the page CSS. Items marked **[ext]** are not on the page: they are extensions I propose and should be confirmed.

Principle: softness comes from three rules only: radii by role, 1 px borders instead of shadows, pills only in the navigation and the level filter. New information is a row, list or column in an existing panel, never a new panel or tile.

## 1. Colour tokens

Contrast is computed from the WCAG 2.x formula (checked by hand against the page's own table). "Existing" = name in `services/frontend/src/styles/tokens.css`.

| Role | New property | Hex | Contrast | Existing token |
|---|---|---|---|---|
| Canvas (page background) | `--canvas` | `#E8ECF1` | n/a | `--bg` |
| Surface (panels, fields) | `--surface` | `#FFFFFF` | n/a | `--surface` |
| Soft surface (filter track, row hover, sunken) | `--soft` | `#F3F5F8` | n/a | `--surface-sunken`, `--surface-hover`, `--neutral-soft` |
| Tint (recommendation panel) | `--tint` | `#E0E7F1` | ink 13.2:1 | `--accent-soft` (partly) |
| Selection | `--sel` | `#D5E0F0` | ink 12.3:1 | `::selection` literal `#cfdcff` |
| Ink | `--ink` | `#18202B` | 16.4 on surface, 13.8 on canvas | `--ink` |
| Ink 2 | `--ink-2` | `#364150` | 10.4 / 8.7 | `--ink-2` |
| Muted | `--muted` | `#505B6A` | 6.9 / 5.8 / 5.5 on tint | `--muted` |
| Panel border | `--line` | `#D3DAE3` | decorative (1.4 on surface) | `--line` |
| Inner rule (rows, blocks) | `--line-in` | `#E3E8EE` | decorative | none (new) |
| Control edge | `--line-ctl` | `#858F9E` | 3.3 on surface (2.8 on canvas: use only on white fields) | `--line-strong` |
| Accent (links, focus) | `--accent` | `#2F5089` | 8.0 on surface, 6.7 on canvas | `--accent` (see note) |
| Nav / primary button / slider thumb | `--nav` | `#22324A` | white on it 12.9:1 | `--accent` (buttons, brand), `--accent-hover` |
| Focus ring | `--focus` | `#2F5089` | 8.0 on surface, 6.7 on canvas | `--focus` |
| Critical, text | `--c-red` | `#A3262A` | 7.3 on surface, 6.2 canvas, 5.9 tint | `--red-ink` |
| To verify, text | `--c-amb` | `#7A4D00` | 7.3 / 6.1 / 5.8 | `--orange-ink` |
| Compliant, text | `--c-grn` | `#22694A` | 6.6 / 5.6 / 5.3 | `--green-ink` |
| Critical, marker | `--m-red` | `#C53A3E` | 5.2 on surface | `--red` |
| To verify, marker | `--m-amb` | `#B87A0A` | 3.6 on surface (3.0 on canvas) | `--orange` |
| Compliant, marker | `--m-grn` | `#3C8C66` | 4.1 on surface | `--green` |
| Unflagged unit (calibration) | `--u-off` | `#C3CCD8` | decorative | none (new) |
| Flagged unit, threshold | `--u-on` | `#22324A` (= `--nav`) | 12.9 | none (new) |

Notes
- The page has **no fill variants** ("brak wypełnień"): levels are an icon, a word in the text colour and, in graphics, the marker colour. Tokens `--red-soft`, `--red-line`, `--orange-soft`, `--orange-line`, `--green-soft`, `--green-line` have no counterpart and are deleted. Do not tint rows, panels or badges by level.
- `--accent` splits in two: today it is both the primary-button navy and the link colour. In the new system buttons and nav use `--nav`; links and focus use `--accent`.
- Markers (`--m-*`) are for graphics only (mini-scale, scale zones, chart series). Text and icons next to a level use `--c-*`. Marker amber and green are below 4.5:1, so a marker is always paired with an icon, a word or a number.
- **No counterpart, drop:** `--faint` (use `--muted`; placeholder text still needs 4.5:1), `--accent-soft`/`--accent-ink` (use `--tint`, `--accent`), `--red/orange/green-*` soft and line, `--surface-hover` (use `--soft`), `--shadow-pop`, `--shadow-drawer`, `--sidebar-w` (if top nav is chosen).
- **New:** `--canvas` (rename of `--bg`, keep `--bg` as alias for a smaller diff), `--soft`, `--tint`, `--sel`, `--line-in`, `--line-ctl`, `--nav`, `--c-red/amb/grn`, `--m-red/amb/grn`, `--u-off`, `--u-on`, radii `--r-panel/--r-block/--r-ctl/--r-tag/--r-bar`, `--scale-*` (see 3).
- `--accent-hover` has no value on the page. **[ext]** Derive: `--nav` hover `#1A2638`, secondary button hover background `--soft`.
- Dark theme: not designed (see section 12). `tokens.css` is light only today, so nothing regresses.

## 2. Typography

| Item | Value |
|---|---|
| Family | Figtree (SIL OFL). Stack: `"Figtree", system-ui, "Segoe UI", sans-serif` |
| Self-hosting | `@fontsource/figtree`, replacing `@fontsource/ibm-plex-sans`. Imports in `main.tsx`: `latin-400`, `latin-ext-400`, `latin-500`, `latin-ext-500`, `latin-600`, `latin-ext-600` (`latin-ext` carries ą ć ę ł ń ó ś ź ż). Pin an exact version like the current `5.3.0`. Add the licence to `THIRD_PARTY_LICENSES.md` (OFL; the repo allows MIT/Apache/BSD/ISC, so confirm OFL fonts are accepted, as IBM Plex already is). No `<link>` to Google Fonts. |
| Weights | 400 body, 500 labels/links/buttons, 600 headings, level words, numerals. No 700. |
| Base | 16 px / 1.5, `font-variant-numeric: tabular-nums` on the whole app (page: `.spec`) |
| Smoothing | `-webkit-font-smoothing: antialiased` |

Scale (px): 12 / 14 / 16 / 18 / 20 / 24 / 32 / 40.

| Token | Size / line | Use |
|---|---|---|
| `--fs-12` | 12 / 1.4 | scale labels, matrix sub-labels, chart ticks |
| `--fs-14` | 14 / 1.5 | table headers, sub-lines, captions, hints, form hints, register table |
| `--fs-16` | 16 / 1.5 | body, table cells, nav, buttons, field values |
| `--fs-18` | 18 / 1.3 | panel titles (h5), brand, matrix cells, recommendation title |
| `--fs-20` | 20 / 1.45 (sentence), 1.2 (count) | verdict sentence (500); level counts in the filter (600) |
| `--fs-24` | 24 / 1.25 | page and case titles (h4, 600) |
| `--fs-32` | 32 / 1.15, -0.01em | calibration metric values only |
| `--fs-40` | 40 / 1, -0.02em | Compliance Score and threshold value only |

Large numerals: 40 px only for the Compliance Score and the calibration threshold; 32 px only for the three calibration metrics; 20 px for filter counts. Nowhere else (no KPI tiles, no big numbers in the queue). Numbers are always tabular. Existing `--fs-xs/sm/base/md/lg/xl/2xl` (11.5 to 34 px) are replaced; base grows from 13.5 to 16 px, see section 12.

## 3. Spacing, radii, borders, focus

- Unit 8 px. Scale: 4, 8, 12, 16, 20, 24, 32 (keep `--sp-1..8` names; values unchanged).
- Panel padding 24 (16 on narrow). Gap between panels 16. Page body padding `0 24 24` (16 on narrow). Header padding `16 24`.
- Radii by role:

| Role | Token | Value |
|---|---|---|
| Panel, recommendation panel | `--r-panel` | 16 |
| Block inside a panel (scale block, matrix wrapper) | `--r-block` | 12 |
| Controls (buttons, selects, inputs) | `--r-ctl` | 10 |
| Tags, small chips | `--r-tag` | 4 (see ambiguity in section 12) |
| Mini-scale bar / unit | `--r-bar` / `--r-unit` | 3 / 1 |
| Nav container, nav pill, level filter | 999 / 24 on the filter track | pill, only these |
| Slider thumb | 50% | circle (the one other round element) |

- **Borders, not shadows.** Panel: 1 px `--line` on white over `--canvas`. Rows: 1 px `--line-in`. Table header underline: 1 px `--line`. Scale axes and matrix head/foot: 1 px `--ink`. No `box-shadow` for depth, no gradients, no `backdrop-filter`. The only box-shadow allowed is `inset 0 0 0 1px var(--line-ctl)` as a border on the pressed filter segment.
- Overlays (dialog, menu, popover, drawer, toast) **[ext]**: no shadow; white surface, 1 px `--line`, `--r-block`, scrim `rgba(24,32,43,.40)` behind dialog and drawer. Delete `--shadow-pop` and `--shadow-drawer`.
- Focus: `outline: 3px solid var(--focus); outline-offset: 2px` on every `:focus-visible`. The ring sits outside the element, so it is measured against the surrounding canvas or panel (6.7:1 / 8.0:1). On the slider thumb use `outline-offset: 4px`.
- Motion: only colour/background transitions, `--dur` 140 ms; honour `prefers-reduced-motion` (already in `base.css`).

## 4. Components

### 4.1 Header and navigation
Header, one row, padding `16 24`, gap `12 24`, wraps: brand (18/600, text "InvestWatch") then the nav then user area on the right (`margin-left: auto`, 14 px `--ink-2`, gap 16: user name, help, sign out).
- Nav container: white, 1 px `--line`, radius 999, padding 4, gap 4. Items: padding `8 16`, radius 999, 16/500, `--ink-2`, no underline. Current (`aria-current="page"`): background `--nav`, text white. Items: Kolejka, Kalibracja, Skanowania (page); product also has Dziennik audytu (supervisor only).
- Hover **[ext]**: background `--soft`. No counts or badges on nav items.

**Sidebar vs top nav.**

| Option | For | Against |
|---|---|---|
| A. Top pills (page design) | Matches the page and reference 7; frees the 220 px column, which the 7-column queue needs (table `min-width` 1040 px plus 48 px panel padding does not fit a 1280 px screen with a 220 px sidebar); one header instead of sidebar plus topbar | Cost "Średni" per the page: `Sidebar.tsx`, `TopBar.tsx`, `layout.css`, `AppShell.tsx`. Search, "Skanuj URL", jobs, demo menu, connection and the threshold card need a new home |
| B. Keep sidebar, pill-shaped active item | "Mały" cost per the page | Contradicts the chosen proposal and its fragments; table scrolls horizontally below about 1330 px; two stacked chrome areas remain |

**Recommendation: A.** The width argument decides it, and the threshold card becomes redundant because the queue and calibration panels already state "oznaczenie od 20, krytyczne od 70". Placement: row 1 = brand, pills, then right-aligned: search button (opens command palette), primary "Skanuj URL", jobs, demo menu (as today), user. Connection state becomes a text-and-icon item in the header's right group ("Połączono" / "Brak połączenia", icon plus word, not a haloed dot). The version line "Prototyp · dane przetwarzane lokalnie" moves to a page footer line. The nav count of flagged cases is dropped (the filter shows counts). Below 960 px the pills scroll horizontally or wrap; the page does not define a phone layout.

### 4.2 Level filter (replaces the three risk tiles)
- Track: `--soft`, 1 px `--line-in`, radius 24, padding 4, gap 4, `width: fit-content`, `margin-top: 20`. A `role="group"` with `aria-label="Poziom ryzyka"`.
- Segment: pill (999), padding `8 16`, transparent, `--ink-2` 16, inner gap 8, baseline aligned. Content: level icon (centred, in `--c-*`), word, then count (20/600 `--ink`, line 1.2). Segments: Wszystkie (no icon), Krytyczne, Do weryfikacji, Zgodne.
- Pressed (`aria-pressed="true"`): white background, text `--ink`, `inset 0 0 0 1px var(--line-ctl)`.
- Behaviour: sets the same level filter as today's "Poziom ryzyka" select, which is removed. Clicking the pressed level returns to Wszystkie **[ext]** (today's tiles toggle).
- Counts are the live counts at current thresholds (existing `LevelCounts`).

### 4.3 Queue table
- Lives inside the queue panel; the table wrapper is `margin: 16px -24px 0` so rules run edge to edge; first cell `padding-left 24`, last `padding-right 24`. Wrapper is a focusable scroll region (`tabindex="0"`, `role="region"`, label "Tabela spraw"). `table { width: 100%; min-width: 1040px; font-size: 16px }`.
- Header cells: padding `10 12`, 14/500 `--muted`, 1 px `--line` underline, `nowrap`. Sentence case. A visually hidden `<caption>`.
- Body cells: padding 12, bottom rule 1 px `--line-in`. Row hover: cell background `--soft`. No coloured left bar, no row tinting, no zebra.
- **Row height:** about 72 px with a one-line title, about 96 px when the title wraps to two lines (the page quotes about 96; compact variant with one-line title about 64 px). Case column `min-width: 300`.
- Columns, in order (7):

| # | Column | Content |
|---|---|---|
| 1 | Poziom i ryzyko | level indicator (4.4) over risk number plus mini-scale |
| 2 | Sprawa | title as link (16/500) over sub-line `IW/2026/0412, entity` (14 muted, 2 px above) |
| 3 | Źródło | plain text (Instagram, YouTube, WWW) |
| 4 | Moduł | module numbers as plain text, "1, 2" (full names in the Moduł column title or a legend, see section 12) |
| 5 | Naruszone kryteria | plain text "kryt. 3, 7, 12, 14", or "brak" in `--muted` |
| 6 | Status | select, 216 px wide |
| 7 | Wykryto | relative time ("2 godz.", `nowrap`) in a `<time>` with the absolute date in `title` |

- Tags and criteria references are plain text. Remove `.rule-pill`, `.module-tag` number squares, `.queue__rules` chips and the badge for status.
- Toolbar under the panel title: "Eksportuj CSV" secondary button on the right of the title row. Footer row: "Pokazano 6 ze 148" (14 `--muted`) left, "Następna strona" secondary button right, margin-top 16.
- Search and the other filters (module, source, status, date): not on the page, see section 12. Proposal **[ext]**: keep one compact row of 40 px fields between the filter track and the table, without the risk-level select.

### 4.4 Level indicator
- Icon (own shape per level) plus word, 16/600, colour `--c-*`. Gap 6. Never a dot, never a pill or fill.
- Icons (24 px viewBox, stroke 2, round caps and joins, `fill: none`, size `1.125em`), lucide equivalents in the product:

| Level | Word | Shape | Lucide |
|---|---|---|---|
| Critical, risk from 70 | Krytyczne | octagon with "!" | `OctagonAlert` |
| To verify, from 20 | Do weryfikacji | magnifier | `Search` |
| Compliant, below 20 | Zgodne | circle with tick | `CircleCheck` |

- Register-result icons: warn (triangle `TriangleAlert`), ok (`CircleCheck`), no (circle with dash `CircleMinus`).
- **Ruled mini-scale** under the word in the queue: `.ms` 56 x 12 px. Baseline 1 px `--ink-2` at `bottom: 2px`; fill bar 5 px high at `bottom: 3px`, width = risk %, colour `--m-*` of the level, radius `--r-bar` (3); two 1 px x 12 px ticks in `--ink` at 20% and 70%. Next to it the risk number: 16/600, `min-width: 2ch`, right-aligned, gap 8; screen readers get "na 100". Level cell is a grid, gap 4, left aligned. The mini-scale is `aria-hidden`.

### 4.5 Buttons and links
| Kind | Spec |
|---|---|
| Primary | `min-height: 44`, padding `8 20`, no border, radius 10, bg `--nav`, white 16/500, icon gap 8 |
| Secondary | `min-height: 44`, padding `8 18`, 1 px `--line-ctl`, bg white, `--ink` 16/500, radius 10; used for exports, pagination, cancel |
| Link | `--accent`, underline 1 px, `text-underline-offset: 3px`, hover underline 2 px |
| Compact **[ext]** | 40 px high (matches selects) for in-row and toolbar use; the page defines none. Do not go below 32 px |
| Disabled **[ext]** | opacity .55, `cursor: not-allowed` (as today) |

One primary button per panel. Labels verb-first. "Ghost" buttons (`.btn--ghost`) are removed; use link or secondary. Round icon buttons are not used.

### 4.6 Form fields and selects
- Label above the field, always visible, 16/500; hint under it 14 `--muted`.
- Select: height 40, 1 px `--line-ctl`, radius 10, bg white, padding `0 32 0 10`, text 14 `--ink` (never white text), `appearance: none`, 14 px chevron at right 10, `min-width: 172`, `max-width: 220`; in the table 216 px.
- Input **[ext]**: same 40 px, border, radius and text as the select; placeholder only as a format hint. Checkbox: 16 px native with `accent-color: var(--nav)`.
- Error text: icon plus words in `--c-red`, under the field.

### 4.7 Panels
- White, 1 px `--line`, radius 16, padding 24. Title h4 24/1.25/600 (page level) or h5 18/1.3/600 (section level); subtitle 16 `--muted`, `max-width: 60ch`, 4 px under the title. Title row is flex, space-between, wraps (`16 24` gap); the action button sits right and aligns to the bottom.
- Blocks inside a panel (scale, matrix): 1 px `--line-in`, radius 12, padding 16.
- No panel header bar with its own background or border (current `.panel__head`). Panels are never nested more than one level deep.

### 4.8 Recommendation callout
`--tint` background, no border, radius 16, padding 24 (16 narrow), gap 10. h5 "Zalecenie: eskalować" (18/600), one sentence of text including the next step, then an action row (gap `12 16`, margin-top 6): primary "Przekaż do postępowania" and link "Zmień zalecenie". Same tint for every recommendation: the level is not repeated in its colour. Remove `.reco--escalate/explain/none`.

### 4.9 Case header block
One panel at the top: case reference "Sprawa IW/2026/0412" (14 `--muted`), title as h4 (24/600, the ad's headline), then a `dl` of four columns (2 below 900 px, 1 on phone), gap `12 24`, margin-top 16, padding-top 16, top rule 1 px `--line-in`: Podmiot, Źródło ("Instagram, post z 20.11.2026"), Wykryto ("21.11.2026, 09:14"), Podstawa prawna. `dt` 14 `--muted`, `dd` 16. Breadcrumb, status stepper and the case sub-navigation are not on the page (section 12).

### 4.10 Verdict block
Panel in a two-column case grid (`1.4fr / 1fr`, gap 16, one column below 900 px); the left is the verdict, the right column holds the recommendation callout, the register table and the export buttons.
1. h5 "Werdykt" (18/600).
2. **Verdict sentence first**: 20/500, line 1.45, `max-width: 52ch`, margin-top 12. Starts with the finding word ("Naruszenie.", "Wymaga weryfikacji.", "Brak naruszeń.") and one sentence of reason. No number inside it except what the ad itself claims.
3. Level and Compliance Score row: flex, baseline, `column-gap 24`, `row-gap 8`, margin `20 0 12`. Level indicator (4.4), then label "Compliance Score" (14 `--muted`), the value (40/600, -0.02em, `nowrap`), "z 100" (14 `--muted`).
4. **Dual scale** in a block (4.10.1).
5. Numbered findings: `ol` with counter "1." in `--muted`, 8 px gap, margin-top 20, columns `1.75em / 1fr`; each item a plain sentence with the criterion as `<small>` "Kryt. 3" (14 `--muted`). This replaces the 18-criteria chip clusters in the summary.

**4.10.1 Dual ruled scale** (`figure.ds`): two scales, one above the other, same 0 to 100 axis. Grid: label column `9.5em` plus `1fr`, `column-gap: 16`. Rows:
1. Threshold names (22 px): "oznaczenie" at 20%, "krytyczne" at 70%; 12/600 `--ink`, `border-left: 2px solid --ink`, `padding-left: 8`, text sits on the baseline.
2. Risk labels (18 px, 12 `--muted`) every 10 (0 to 100); 20 and 70 in `--ink` 600. Row label "Ryzyko" (14 `--ink-2`).
3. Axis (24 px): three 4 px bars at `top: 10`: 0 to 20 `--m-grn`, 20 to 70 `--m-amb`, 70 to 100 `--m-red`; 1 px ticks every 5 (14 px high at multiples of 10, 8 px between); threshold lines 2 px x 24 px `--ink` at 20% and 70%.
4. Compliance Score labels (18 px, 12 `--muted`) = 100 minus risk, every 10. Row label "Compliance Score".
5. Caption (14 `--ink-2`): "Odczyt: ryzyko 86 z 100, Compliance Score 14. Progi na skali ryzyka: oznaczenie od 20, krytyczne od 70." The values in `--ink` 600.
The reading needle spans rows 2 to 4: 2 px `--ink` line at the risk value, with a 6 px downward triangle at `top: 21`. Everything but the caption is `aria-hidden`; the caption carries the information. Thresholds come from `thresholds` (configurable), not constants. Below 640 px: drop the row-label column and the odd labels, show a sentence version of the labels.

### 4.11 Register checks (borrowed element b)
Heading h5 "Rejestry"; a ruled table (14 px, no panel inside the panel). Columns: **Rejestr** (register label; the register name is the source, with the existing "open register" link beside it, new tab, "(otwiera się w nowej karcie)" for screen readers), **Wynik** (icon plus words, e.g. "wpis aktywny", "na liście od 14.10.2026", "brak wpisu", coloured `--c-*` per status, weight 500), **Stan na** (`snapshot_date` as `21.11.2026`, `nowrap`; when null: "brak migawki"). Header cells: `padding 8 12 8 0`, 2 px `--ink` bottom border, 14/600. Body: `padding 8 12 8 0`, 1 px `--line` bottom border, `vertical-align: top`. Optional second line with `subject` and `detail` in 14 `--muted` inside the first and second cells. Status mapping: `listed` ok / `--c-grn`, `warning_listed` warn / `--c-red`, `inactive` warn / `--c-amb`, `not_listed` no / `--c-amb`, `not_checked` no / `--muted`.
Note: the page puts "brak wpisu" in the firm-register row in amber. Whether "not listed" is good or bad depends on the register; the mapping above follows the page and must be reviewed with the domain owners.

### 4.12 Calibration instrument
Panel title h4 "Kalibracja progu", subtitle "Zestaw testowy: 204 materiały, w tym 50 naruszeń." (counts from data). Two columns: `1.35fr / 1fr`, gap 32, one column below 900 px.
Left, the instrument:
- Control row (flex, space-between, align end): label "Próg oznaczenia sprawy" (16/500), hint "Sprawa trafia do kolejki od tej wartości ryzyka." (14 `--muted`), and `<output>` with the value (40/600).
- One 0 to 100 axis. Above it a stack of 5 px unit marks, one per violation in the test set; below it the compliant items. Each bin = 5 risk points (5% width), units 5 px high, gap 1 px, padding `0 1`, `--r-unit` 1; above-axis bins grow up (area 30 px high), below-axis bins grow down (76 px high, 62 narrow). Bins over 10 items are cut to 9 units and end in a count label (12 px, `--ink`, top border 1 px dashed `--ink-2`, padding-top 4) so that heights stay bounded.
- Unit colours: below threshold `--u-off`, at or above threshold `--u-on` (`--nav`). The threshold marker is a 2 px `--u-on` bar from the axis, so the state is also encoded by position. Critical threshold: 1 px dashed `--ink-2` vertical line at 70% with label "krytyczne od 70" (12 `--ink-2`, `padding-left: 5`).
- Axis: 2 px `--ink` line, ticks 1 px (10 px, minor 6 px) every 5, labels 12 `--muted` every 10 (odd ones hidden narrow).
- Slider: native `input[type=range]` over the axis, transparent track, thumb 28 px circle `--nav` with 4 px white border; arrow keys change by 1; `aria-describedby` the hint; same value shown in `<output>`.
- Key (14 `--muted`, `max-width: 72ch`): what one mark means (one case of the test set), which are above and below, and that tall bins are cut with the count at the end.
Right:
- Metrics `dl` in 3 columns, gap 16, `padding-bottom 20`, `margin-bottom 20`, 1 px `--line-in` below. Each: `dt` 14 `--muted` (Precyzja, Czułość, F1), value 32/600 (e.g. 91%), then the fraction line 14 `--ink-2` ("42 z 46 oznaczonych to naruszenia", "wykryto 42 z 50 naruszeń"). F1: "średnia harmoniczna obu miar".
- Matrix in a block (`--r-block`, 1 px `--line-in`, padding 16): 14 px table, caption "Macierz pomyłek przy progu 20" (16/600, left, 8 below). Columns: row label, Oznaczone, Nieoznaczone, Razem; rows: Naruszenie, Zgodne, Razem. Cells: padding `10 12`, right-aligned (first column left), rule 1 px `--line`; header bottom 1 px `--ink`; footer top 1 px `--ink` in `--ink-2`. Cell content: count 18/600 (block) over 12 `--muted` meaning ("trafne alarmy", "pominięte", "fałszywe alarmy", "trafnie pominięte"). No green/red cell fills. Narrow: hide the Razem column.
- The existing misclassified lists stay below as plain tables inside a panel.

### 4.13 Alerts and toasts
- Alert banner (new critical case): not a red-filled bar. White panel, 1 px `--line`, radius 12, padding `12 16`, a 24 px level icon in `--c-red` and the words "Nowa sprawa krytyczna", title as link, primary or secondary button on the right. The 4 px left coloured border and `--red-soft` fill are removed. Live region `role="status"`.
- Toast **[ext]**: bottom right, width up to 380, white surface, 1 px `--line`, radius 12, padding 12; icon plus text, close button 40 px; error variant has the icon and a bold lead word, no fill. Replace today's dark `--ink` toast and red toast.
- Inline form error: icon plus words in `--c-red`, 14 px.
- Copy: what happened and what to do next, never "Podałeś błędne...".

### 4.14 Empty and loading states
- Empty: inside the panel, left-aligned or centred text only: one title (18/600), one sentence (`--muted`, `max-width: 52ch`) and one action (secondary button or link). No illustrations, no icon discs. Filtered-to-zero: say which filter caused it and give "Wyczyść filtry".
- Loading: under 100 ms nothing; to about 1 s an inline text ("Wczytywanie...") next to the control; longer, skeleton rows: `--soft` blocks (flat, no shimmer gradient), radius 4, with the table header already rendered. `prefers-reduced-motion`: no pulse.
- Error state: title "Nie udało się wczytać kolejki", sentence with cause if known, button "Spróbuj ponownie". Icon `--c-red` optional, never a red fill.

## 5. Charts (Recharts)
- Chrome: no chart background; grid lines `--line-in`, 1 px, horizontal only; axis line `--ink-2`; tick text 12 px `--muted` Figtree (`.recharts-text`); no legend inside the chart: use a text legend (14 `--ink-2`) with a 2 px line or 10 px square swatch.
- Series colour: sequential use of `--nav` (primary series), `--accent` family or `--muted` for the second; do not use level colours for non-level series. Distinguish series also by line style (solid, dashed `4 3`) and direct labels. The teal `#0e8f8f` in `PrCurve.tsx` is off-palette: replace with `--accent`/`--nav` plus dash.
- Level series, where unavoidable, use `--m-red/--m-amb/--m-grn` and are labelled by word (swatch alone is not enough).
- Threshold reference lines: `--ink`, 2 px solid for the flag threshold, 1 px dashed for the critical one, label "20" / "70" in `--ink` 12/600. Not orange/red lines.
- Histogram on calibration: if kept, use unit marks (4.12) rather than bars; otherwise bars `--u-off` (compliant) and `--nav` (violation) with `--r-unit` radius.
- Tooltip (`ChartTip`): white, 1 px `--line`, radius 12 (`--r-block`), padding `8 12`, 14 px, no shadow.
- No animation (`isAnimationActive={false}` stays).
- **Trend chart is demoted**: it leaves the queue. If the supervisor still needs inflow, put it behind a closed `<details>` titled "Napływ spraw" at the foot of the queue page **[ext]**, single series (all cases per day, `--nav` bars, `--r-unit`), text summary above it ("29 nowych spraw wczoraj"). Not in the calibration page (different task). The page itself only says the chart is removed from the queue and that proposal 3 shows inflow if needed.

## 6. Do / don't
1. Do write the verdict as one sentence before any number; don't open a verdict with a gauge or score.
2. Do show level as icon plus word; don't use colour, dots, halos or pills alone.
3. Do separate with 1 px borders and rules; don't add shadows, gradients or blur.
4. Do give new information a row, list item or column in an existing panel; don't add new panels, tiles or a trio of KPI numbers.
5. Do use large numerals only for the score (40), threshold (40) and metrics (32); don't make counts or deltas into hero numbers.
6. Do read scales as rulers (axis, ticks, thresholds, both Risk and Compliance Score); don't draw semicircle gauges or progress rings.
7. Do keep pills for the navigation and the level filter; don't pill-ify tags, statuses or counts.
8. Do use `--c-*` for text and `--m-*` for graphics; don't fill rows, cards or alerts with pastel level colours.
9. Do write verb-first, sentence-case Polish and errors that say what to do next; don't blame the user or use "OK", "Submit", exclamation marks.
10. Do keep every control keyboard-reachable with the 3 px focus ring; don't hide focus, shrink primary targets below 44 px or use icon-only buttons without a text label or tooltip.

## 7. Implementation checklist (`services/frontend/src`)
Effort per the page's cost table, adjusted after reading the tree. Do not change logic, props or `data-testid`s.

| File | Change | Effort |
|---|---|---|
| `styles/tokens.css` | New palette and names (section 1); keep legacy names as aliases during the swap (`--bg`, `--ink`, `--line`, `--accent`, `--focus`), then remove the `-soft`/`-line` level tokens; radii `--r-panel/block/ctl/tag/bar`; type scale 12 to 40 and `--font`; delete `--shadow-*`, `--sidebar-w`; add `--dur` unchanged | S |
| `main.tsx`, `package.json`, `THIRD_PARTY_LICENSES.md` | `@fontsource/figtree` imports (400/500/600, latin and latin-ext); remove `@fontsource/ibm-plex-sans`; record OFL | S |
| `styles/base.css` | body 16/1.5; focus ring 3 px, offset 2; `::selection` `--sel`; recharts text 12 px, grid `--line-in`; remove outline radius hack | S |
| `styles/layout.css`, `components/layout/Sidebar.tsx`, `TopBar.tsx`, `AppShell.tsx`, `UserChip.tsx`, `ConnectionIndicator.tsx`, `DemoMenu.tsx`, `JobsMenu.tsx` | Single header with brand, pill nav, search, scan, jobs, demo, connection, user (4.1); delete the sidebar, threshold card, `.brand__mark`, `.nav__count`; single-column shell; page max width and paddings; keep skip link | M |
| `styles/ui.css`, `components/ui/Button.tsx`, `Badge.tsx`, `LevelBadge.tsx`, `ScoreRail.tsx`, `ModuleTag.tsx`, `Panel.tsx`, `States.tsx`, `Notices.tsx` | Buttons 44 px and variants; `Badge` loses level fills (keep a neutral outline tag only); `LevelBadge` = icon + word (4.4); `ScoreRail` becomes the 56 x 12 ruled mini-scale (and a wide variant inside `ScoreScale`); `ModuleTag`/`.chip`/`.rule-pill` become plain text; panels per 4.7; skeleton flat; toasts per 4.13; fields 40 px; dialog/menu/palette: border, no shadow, scrim | M |
| `styles/queue.css`, `components/queue/LevelSummary.tsx`, `QueueFilters.tsx`, `QueueTable.tsx`, `StatusSelect.tsx`, `AlertBanner.tsx`, `pages/QueuePage.tsx` | `LevelSummary` becomes the pill filter with counts and writes the same `filters.level`; drop the `Poziom ryzyka` select from `QueueFilters`; table per 4.3 (7 columns, remove inset coloured bars, rule pills, module tags); "fresh" row highlight needs a decision (section 12); `AlertBanner` restyled; remove `TrendChart` from `QueuePage` (optional `<details>` at the foot) | M |
| `components/queue/TrendChart.tsx` | Demote (5); `ChartTip` is imported by `ScoreHistogram`, `PrCurve`, `ForensicsPanel`: move it to `components/ui/ChartTip.tsx` before removing the chart | S |
| `styles/case.css`, `components/case/VerdictBlock.tsx`, `RecommendationCard.tsx`, `RegistryChecks.tsx`, `StatusStepper.tsx`, `pages/CasePage.tsx` | Case header block (4.9); verdict sentence first, level + Compliance Score, new `ScoreScale` component (HTML and CSS, no dependency; props: risk, thresholds) (4.10.1); findings list; single-tint recommendation; `RegistryChecks` becomes the ruled table (4.11) with `snapshot_date` and link; remove `.reco--*` fills, `.score` 52 px numeral, three-column `.verdict` | M |
| `components/case/PartiesCard.tsx`, `ComplianceMatrix.tsx`, `EvidenceChips.tsx`, `SourcesBlock.tsx`, `DebateBlock.tsx`, `ForensicsPanel.tsx`, `FinancialsPanel.tsx`, `RelationshipGraph.tsx`, `EvidenceDrawer.tsx`, `VisualsBlock.tsx` | Not on the page. Token swap only: new colours, radii, rule-based tables, evidence chips become plain links, avatars lose fills. Review visually after the swap | M (unspecified) |
| `styles/calibration.css`, `components/calibration/ThresholdControl.tsx`, `ScoreHistogram.tsx`, `ConfusionMatrix.tsx`, `MetricsRow.tsx`, `PrCurve.tsx`, `MisclassifiedList.tsx`, `pages/CalibrationPage.tsx` | One instrument: axis with unit marks under the slider on the same 0 to 100 axis (reuse `ScoreHistogram` data, render as HTML marks); native range with 28 px thumb; confusion matrix with row/column totals and no cell fills; metrics 32 px with fractions (counts from `domain/calibration.ts`); decide the fate of the secondary slider and the PR curve (section 12) | M |
| `styles/auth.css`, `pages/LoginPage.tsx`, `NotFoundPage.tsx` | Token swap, panel, 44 px buttons | S |
| Tests / e2e | Selectors that depend on class names (`.level-tile`, `.queue__row--*`, `.reg`) need updating; keep `data-testid` values (`count-red`, `nav-flagged`, `registry-check`...). `nav-flagged` disappears with the nav count: remove or retarget the test | S |

Order: tokens and font, base, ui primitives, header, queue, case, calibration, remaining case blocks, charts.

## 8. Open questions / not verified
Copied from the page ("Czego nie sprawdzono") and from what this spec found:
- Not checked on the page: behaviour on real data, dark theme of the product, print of the evidence package, screen readers, touch on a real tablet. The page was viewed at 1360 px and 390 px in a light and a dark page frame; the samples are always light.
- Dark theme: the page forces `color-scheme: light` for the proposals. The product has no dark theme today. Not designed.
- Phone layout: only a 390 px preview of the fragments, with container queries at 900 and 640 px. App-wide behaviour below 960 px (nav, table as list, filters) is not specified.
- Content not covered by the three fragments: login, command palette, scan dialog, jobs menu, demo menu, evidence drawer, compliance matrix of 18 rules, parties card, relationship graph, forensics, debate, financials, audit log page, status stepper, breadcrumbs, case sub-navigation. They need the token swap and review.
- Queue search, module, source, status and date filters: absent in fragment A.
- Secondary (critical) threshold slider and PR curve in today's calibration page: absent in fragment C, which has a single threshold with 70 as a fixed dashed line. Today's product has two editable thresholds (`flag` and `critical`).
- The "fresh" case highlight (yellow fade) and "new" tag in the queue: absent.
- Font density: base text grows from 13.5 to 16 px and controls from 32 to 40 to 44 px. Fewer rows fit on screen; the page accepts this (row about 72 to 96 px). Dense tables inside a case (18-rule matrix, forensics, financials) should use 14 px as the register table does **[ext]**.
- Contrast: markers `--m-amb` (3.6 on white, 3.0 on canvas) and `--m-grn` (4.1 on white) are above 3:1 only on white or just on canvas; always pair them with text or an icon. `--line-ctl` is 3.3:1 on white but 2.8:1 on canvas, so it is for fields on white only. Unflagged unit colour `--u-off` is decorative.

### Ambiguities and inconsistencies found in the proposal
1. **Tag radius**: the rules text says tags 3 px; the page's cost table says `--r-tag: 4px`; the p4 CSS has no tag rule (3 px is the scale bar `--r-bar`). This spec uses 4 for tags and 3 for scale bars.
2. **Row height**: "about 96 px" appears in the comparison and the fragment, but the markup gives about 72 px with a one-line title; 96 only when the title wraps at the 300 px minimum.
3. **"Large numerals only for score and threshold"** versus the page: 20 px counts in the filter and 32 px metrics also exist. Kept as listed in 2.
4. **Level fills**: the cost table says "trzy trójki poziomów: tekst, znacznik, brak wypełnień", so there are no fill variants, even though the existing product has soft fills. Level colour appears as text and markers only.
5. **Threshold meaning**: the page uses 20 (oznaczenie) and 70 (krytyczne), the README `ALERT_THRESHOLD` default is 70 and the product has two thresholds. 20 and 70 should be read from settings, not hard-coded. The calibration fragment only moves the flag threshold.
6. **Compliance Score 14 with risk 86**: the verdict fragment shows both, consistent with 100 minus risk, but the first draft of the page had markers at 30 and 80 on the Compliance Score scale. The dual scale resolves this; keep both scales together.
7. **Focus ring** is the same colour as the accent and the link; the ring never sits on `--nav` (outline is outside the element), so it is fine, but the thumb needs offset 4.
8. **Module column** shows bare numbers with a `title` tooltip only: not keyboard or touch accessible. Needs a visible legend or abbreviations.
9. **Tablet touch targets**: the page spec states 44 px for buttons and 40 px for selects; the select is below 44 px.
10. **Sidebar**: the page's header has no search, scan, jobs, connection or version item; where they go is this spec's proposal (4.1).
11. **User name** "A. Kowalczyk" and all sample cases are invented page content, not product data.
