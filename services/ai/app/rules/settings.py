"""Thresholds used by the rule checks (one place, no per-sample values)."""

RISK_PROXIMITY_CHARS = 500  # rule 3: a warning further than this from every claim is not "direct"
FONT_RATIO_MIN = 0.85  # rule 4: risk font / dominant font
CONTRAST_MIN = 4.5  # rule 5: WCAG AA for body text
OPACITY_MIN = 0.6  # rule 5
MOBILE_MIN_FONT_PX = 9.0  # rule 8: below this the text is unreadable on a phone
PROMINENT_FONT_RATIO = 1.2  # rule 13: historical result this much bigger than body text
FOG_MAX = 22.0  # rule 9: Polish FOG index of the risk warning
SENTENCE_WORDS_MAX = 40  # rule 9
