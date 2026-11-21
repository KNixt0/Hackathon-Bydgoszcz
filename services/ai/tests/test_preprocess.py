from __future__ import annotations

import hashlib

from app.preprocess import HashEmbedder, contrast_ratio, detect_language, fold, preprocess, split_sentences

HTML = """<html><head><title>Tytuł</title><meta name="viewport" content="width=device-width">
<style>.r{font-size:9px;color:#999} @media (max-width:600px){.gone{display:none}}</style></head>
<body><h1>Nagłówek</h1><p>Pierwszy <b>ważny</b> akapit.</p><p class="r">Drobny druk.</p>
<p class="gone">Znika na telefonie.</p><p style="display:none">Ukryty tekst.</p>
<details><summary>Rozwiń</summary><p>Treść po kliknięciu.</p></details>
<footer><small>Stopka prawna.</small></footer><script>var x = "nie tekst";</script></body></html>"""


def seg(page, text):
    return next(s for s in page.segments if text in s.text)


def test_html_is_stripped_and_normalised():
    page = preprocess(HTML, "", "")
    assert "var x" not in page.text and "<" not in page.text
    assert "Pierwszy ważny akapit." in page.text
    assert page.text.startswith("Tytuł\nNagłówek")


def test_segments_index_into_the_text():
    page = preprocess(HTML, "", "")
    assert all(page.text[s.start : s.end] == s.text for s in page.segments)


def test_visual_signals():
    page = preprocess(HTML, "", "")
    assert seg(page, "Drobny").style.font_px == 9 and seg(page, "Drobny").style.color == (153, 153, 153)
    assert seg(page, "Ukryty").style.hidden
    assert seg(page, "Treść po kliknięciu").style.collapsed and not seg(page, "Rozwiń").style.collapsed
    assert seg(page, "Stopka").style.low_visibility
    assert seg(page, "Znika").style.media_hidden
    assert seg(page, "Nagłówek").style.heading == 1
    assert page.signals.has_viewport_meta and page.signals.media_queries == 1
    assert page.signals.dominant_font_px == 16
    assert [s.text for s in page.signals.expand_links] == ["Rozwiń"]


def test_legal_heading_marks_section_low_visibility():
    page = preprocess("<div><h3>Nota prawna</h3><p>Ryzyko utraty kapitału.</p></div><p>Dalej.</p>", "", "")
    assert seg(page, "Ryzyko").style.low_visibility and not seg(page, "Dalej").style.low_visibility


def test_text_only_document_has_no_visual_signals():
    page = preprocess("", "  Linia  pierwsza \n\n druga linia ", "")
    assert page.text == "Linia pierwsza\ndruga linia" and not page.signals.has_html


def test_script_shell_html_falls_back_to_visible_text():
    page = preprocess("<html><body><div id='app'></div></body></html>", "Długi widoczny tekst strony " * 5, "")
    assert not page.signals.has_html and "widoczny" in page.text


def test_content_hash_is_sha256_of_normalised_text():
    page = preprocess("", "Ala  ma kota", "")
    assert page.content_hash == hashlib.sha256(b"Ala ma kota").hexdigest()
    assert preprocess("", "Ala ma   kota\n", "").content_hash == page.content_hash


def test_fold_keeps_length():
    text = "Zażółć GĘŚLĄ jaźń – „cudzysłów”"
    assert len(fold(text)) == len(text) and fold(text).startswith("zazolc gesla jazn")


def test_sentences_respect_abbreviations():
    sents = [s.text for s in split_sentences("Np. w 2024 r. zysk wyniósł 30%. Drugie zdanie.")]
    assert sents == ["Np. w 2024 r. zysk wyniósł 30%.", "Drugie zdanie."]


def test_language_detection():
    assert detect_language("Inwestowanie wiąże się z ryzykiem utraty środków i nie jest dla każdego.")[0] == "pl"
    assert detect_language("CFDs are complex instruments and you can lose your money.")[0] == "en"


def test_embedder_similarity_orders_paraphrases():
    e = HashEmbedder()
    a = "Polecam, zarobiłem w tydzień!"
    assert e.similarity(a, "Polecam, zarobilem w tydzien!!") > e.duplicate_threshold
    assert e.similarity(a, "Opłaty mogłyby być niższe.") < 0.3
    assert abs(e.similarity(a, a) - 1.0) < 1e-9


def test_contrast_ratio():
    assert round(contrast_ratio((0, 0, 0), (255, 255, 255))) == 21
    assert contrast_ratio((204, 204, 204), (255, 255, 255)) < 2
