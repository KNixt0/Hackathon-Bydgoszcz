"""Thresholds used by the rule checks (one place, no per-sample values)."""

RISK_PROXIMITY_CHARS = 500  # rule 3: a warning further than this from every claim is not "direct"
FONT_RATIO_MIN = 0.85  # rule 4: risk font / dominant font
CONTRAST_MIN = 4.5  # rule 5: WCAG AA for body text
OPACITY_MIN = 0.6  # rule 5
MOBILE_MIN_FONT_PX = 9.0  # rule 8: below this the text is unreadable on a phone
PROMINENT_FONT_RATIO = 1.2  # rule 13: historical result this much bigger than body text
FOG_MAX = 22.0  # rule 9: Polish FOG index of the risk warning
SENTENCE_WORDS_MAX = 40  # rule 9

# Rendered visual audit (document.visual, contract v3). A rule decides from these measurements
# (method "rendered") whenever the scraper measured the page in a real browser.
RENDERED_FONT_RATIO_MIN = 0.8  # rule 4: warning font / dominant body font
RENDERED_FONT_MIN_PX = 12.0  # rule 4: absolute floor for the warning font
RENDERED_CONTRAST_MIN = 4.5  # rule 5: WCAG 2.x AA for normal text
RENDERED_OPACITY_MIN = 0.6  # rule 5: effective opacity (element x ancestors)
CONCEALING_CONTRAST_MAX = 3.0  # rule 6: below WCAG's large-text minimum the warning is obscured, not just faint
RESPONSIVE_FONT_MIN_PX = 12.0  # rule 8: rendered size (CSS px x device zoom) on any viewport
HISTORY_FONT_RATIO = 1.2  # rule 13: past performance this much bigger than body text ...
HISTORY_LARGEST_TOLERANCE_PX = 0.5  # ... and (within this tolerance) the largest text on the page
HISTORY_AREA_SHARE_MAX = 0.25  # rule 13: share of the first viewport taken by a past-performance block
