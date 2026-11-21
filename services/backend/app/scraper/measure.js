({riskSrc, perfSrc, maxItems, budgetMs, collectLinks}) => {
  const t0 = performance.now();
  const fold = (s) => s.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/ł/g, 'l');
  const norm = (s) => s.replace(/\s+/g, ' ').trim();
  const RISK = new RegExp(riskSrc);
  const PERF = new RegExp(perfSrc);
  const PCT = /[+-]?\d+(?:[.,]\d+)?\s?%/;
  const SKIP = new Set(['SCRIPT', 'STYLE', 'NOSCRIPT', 'TEMPLATE', 'SVG', 'IFRAME', 'OBJECT', 'SELECT', 'OPTION', 'HEAD', 'TITLE']);
  const de = document.documentElement;
  const vv = window.visualViewport;
  const scale = vv && vv.scale ? vv.scale : 1;
  const W = window.innerWidth, H = window.innerHeight;
  window.scrollTo(0, 0);
  const all = Array.from(document.getElementsByTagName('*'));
  const indexOf = new Map(all.map((el, i) => [el, i]));
  const csCache = new Map();
  const cs = (el) => { let s = csCache.get(el); if (!s) { s = getComputedStyle(el); csCache.set(el, s); } return s; };
  const blockish = (el) => { const d = cs(el).display; return d !== 'inline' && d !== 'contents'; };
  const blockOf = (el) => { while (el && el !== document.body && !blockish(el)) el = el.parentElement; return el || document.body; };
  const isVisible = (el) => {
    if (!el.isConnected) return false;
    if (el.checkVisibility && !el.checkVisibility({opacityProperty: true, visibilityProperty: true, contentVisibilityAuto: true})) return false;
    const r = el.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) return false;
    if (r.right + window.scrollX <= 0 || r.bottom + window.scrollY <= 0) return false;
    return true;
  };
  const parseRgba = (v) => {
    const m = v && v.match(/rgba?\(\s*([\d.]+)[\s,]+([\d.]+)[\s,]+([\d.]+)(?:[\s,/]+([\d.]+%?))?\s*\)/);
    if (!m) return null;
    let a = m[4] === undefined ? 1 : (m[4].endsWith('%') ? parseFloat(m[4]) / 100 : parseFloat(m[4]));
    return [parseFloat(m[1]), parseFloat(m[2]), parseFloat(m[3]), a];
  };
  const over = (top, bottom) => {  // alpha-composite `top` (rgba) over an opaque `bottom` (rgb)
    const a = top[3];
    return [0, 1, 2].map((i) => top[i] * a + bottom[i] * (1 - a));
  };
  const effectiveBackground = (el) => {
    const layers = [];
    let image = false;
    for (let e = el; e; e = e.parentElement) {
      const s = cs(e);
      const c = parseRgba(s.backgroundColor);
      if (s.backgroundImage && s.backgroundImage !== 'none') image = true;
      if (c && c[3] > 0) { layers.push(c); if (c[3] >= 0.999) break; }
    }
    let bg = [255, 255, 255];
    for (let i = layers.length - 1; i >= 0; i--) bg = over(layers[i], bg);
    return {bg, image};
  };
  const opacityOf = (el) => { let o = 1; for (let e = el; e; e = e.parentElement) o *= parseFloat(cs(e).opacity || '1'); return o; };
  const lum = (c) => { const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }; return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2]); };
  const contrast = (a, b) => { const la = lum(a), lb = lum(b); return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05); };
  const rgb = (c) => `rgb(${Math.round(c[0])}, ${Math.round(c[1])}, ${Math.round(c[2])})`;
  const box = (el) => {
    let r = el.getBoundingClientRect();
    try {  // tight box around the rendered text when there is any
      const range = document.createRange(); range.selectNodeContents(el);
      const t = range.getBoundingClientRect();
      if (t.width >= 1 && t.height >= 1) r = t;
    } catch (e) { /* keep the element box */ }
    if (r.width < 1 || r.height < 1) return null;
    return {x: Math.round(r.left + window.scrollX), y: Math.round(r.top + window.scrollY), w: Math.round(r.width), h: Math.round(r.height)};
  };
  const clipped = (el) => {
    const s = cs(el);
    if (s.textOverflow === 'ellipsis' && el.scrollWidth > el.clientWidth + 1) return true;
    if (s.webkitLineClamp && s.webkitLineClamp !== 'none' && el.scrollHeight > el.clientHeight + 1) return true;
    const r = el.getBoundingClientRect();
    let depth = 0;
    for (let a = el; a && a !== de && depth < 12; a = a.parentElement, depth++) {
      const as = cs(a);
      const hx = as.overflowX !== 'visible', hy = as.overflowY !== 'visible';
      if (!hx && !hy) continue;
      if (a === el) {
        if ((hx && el.scrollWidth > el.clientWidth + 1 && as.overflowX !== 'auto' && as.overflowX !== 'scroll') ||
            (hy && el.scrollHeight > el.clientHeight + 1 && as.overflowY !== 'auto' && as.overflowY !== 'scroll')) return true;
        continue;
      }
      if (as.overflowX === 'auto' || as.overflowX === 'scroll' || as.overflowY === 'auto' || as.overflowY === 'scroll') continue;
      const ar = a.getBoundingClientRect();
      if ((hx && (r.right > ar.right + 1 || r.left < ar.left - 1)) || (hy && (r.bottom > ar.bottom + 1 || r.top < ar.top - 1))) return true;
    }
    return false;
  };
  const chainText = (el) => {  // class + id of the element and its ancestors, folded
    const out = [];
    for (let e = el; e && e !== de; e = e.parentElement) out.push(((e.getAttribute('class') || '') + ' ' + (e.id || '')).toLowerCase());
    return out.join(' ');
  };
  const LEGAL_WORDS = /\b(?:nota prawna|informacje prawne|zastrzezenia? prawne|zastrzezenie|disclaimer|legal|przypisy|regulamin|warunki)\b/;
  const legalHeadingBefore = (el) => {
    for (let e = el; e && e !== document.body; e = e.parentElement) {
      for (let p = e.previousElementSibling, n = 0; p && n < 4; p = p.previousElementSibling, n++) {
        const t = fold(norm(p.textContent || ''));
        if (t.length && t.length < 60 && (/^H[1-6]$/.test(p.tagName) || p.tagName === 'SUMMARY' || p.tagName === 'STRONG' || p.tagName === 'B' || t.length < 30) && LEGAL_WORDS.test(t)) return true;
      }
    }
    return false;
  };
  const placementOf = (el, text) => {
    const chain = chainText(el);
    if (/^(?:\*+|\(\d+\)|\[\d+\]|[¹²³⁴⁵⁶⁷⁸⁹])/.test(text) || el.closest('sup') || /foot-?note|przypis|fine-?print|small-?print/.test(chain)) return 'footnote';
    const det = el.closest('details');
    const summary = det && det.querySelector('summary');
    if (/legal|disclaimer|nota-?prawna|zastrzez|regulamin|terms/.test(chain) || (summary && LEGAL_WORDS.test(fold(summary.textContent || ''))) || legalHeadingBefore(el)) return 'legal_section';
    if (el.closest('footer, [role=contentinfo]') || /\b(?:footer|stopka|site-footer|page-footer)\b/.test(chain)) return 'footer';
    return 'body';
  };
  const controlFor = (el) => {  // the element a reader must click to reveal `el`
    for (let e = el; e && e !== document.body; e = e.parentElement) {
      if (!e.id) continue;
      const sel = `[aria-controls~="${CSS.escape(e.id)}"], [data-target="#${CSS.escape(e.id)}"], [data-bs-target="#${CSS.escape(e.id)}"], a[href="#${CSS.escape(e.id)}"]`;
      const c = document.querySelector(sel);
      if (c) return c;
    }
    return null;
  };
  const interactionOf = (el, visible, text) => {
    const det = el.closest('details');
    if (det && !det.open) {
      const summary = det.querySelector(':scope > summary');
      if (!(summary && summary.contains(el))) return {kind: 'details', control: summary};
    }
    if (visible) {
      const a = el.closest('a[href]');
      if (a && text.length < 140) {
        const href = a.getAttribute('href') || '';
        if (href && !href.startsWith('#') && !href.toLowerCase().startsWith('javascript:')) return {kind: 'link', control: a};
      }
      return {kind: null, control: null};
    }
    const chain = chainText(el);
    const dialog = el.closest('dialog, [role=dialog], [aria-modal=true]');
    if (dialog || /\bmodal\b|lightbox|popup/.test(chain)) return {kind: 'modal', control: controlFor(dialog || el)};
    if (el.closest('[role=tooltip]') || /tooltip|popover|tippy/.test(chain)) return {kind: 'tooltip', control: controlFor(el)};
    const control = controlFor(el);
    if (control || /collaps|accordion|spoiler|read-?more|expand|toggle|tab-pane|rozwin/.test(chain)) return {kind: 'accordion', control};
    return {kind: null, control: null};
  };
  const occludedAt = (el, textNode) => {
    let rects = [];
    try { const range = document.createRange(); range.selectNodeContents(textNode); rects = Array.from(range.getClientRects()).filter((r) => r.width > 2 && r.height > 2).slice(0, 3); } catch (e) { rects = []; }
    if (!rects.length) { const r = el.getBoundingClientRect(); if (r.width > 2 && r.height > 2) rects = [r]; }
    if (!rects.length) return false;
    let covered = 0, checked = 0;
    for (const r0 of rects) {
      const docY = r0.top + window.scrollY + r0.height / 2;
      if (docY < window.scrollY + 4 || docY > window.scrollY + H - 4) window.scrollTo(0, Math.max(0, docY - H / 2));
      const range = document.createRange();
      let r = r0;
      try { range.selectNodeContents(textNode); const rr = Array.from(range.getClientRects()).filter((x) => x.width > 2 && x.height > 2); r = rr[checked] || rr[0] || el.getBoundingClientRect(); } catch (e) { r = el.getBoundingClientRect(); }
      const x = Math.min(Math.max(r.left + Math.min(r.width / 2, 40), 1), W - 2);
      const y = Math.min(Math.max(r.top + r.height / 2, 1), H - 2);
      const hit = document.elementFromPoint(x, y);
      checked++;
      if (hit && !(el.contains(hit) || hit.contains(el))) covered++;
    }
    window.scrollTo(0, 0);
    return covered * 2 >= checked && covered > 0;
  };

  // -- walk all text: dominant font (visible text, by length) + blocks with their own text
  const fontLen = new Map();
  let maxFont = 0;
  const blocks = new Map();  // block -> {parts, fonts: Map, longest: {node, len}, maxFont}
  const walker = document.createTreeWalker(document.body || de, NodeFilter.SHOW_TEXT);
  let visCache = new Map();
  const visibleCached = (el) => { let v = visCache.get(el); if (v === undefined) { v = isVisible(el); visCache.set(el, v); } return v; };
  for (let node = walker.nextNode(); node; node = walker.nextNode()) {
    const t = norm(node.data);
    if (!t) continue;
    const parent = node.parentElement;
    if (!parent) continue;
    let skip = false;
    for (let e = parent; e; e = e.parentElement) if (SKIP.has(e.tagName.toUpperCase())) { skip = true; break; }
    if (skip) continue;
    const fs = parseFloat(cs(parent).fontSize) || 0;
    const vis = visibleCached(parent);
    if (vis) { fontLen.set(fs, (fontLen.get(fs) || 0) + t.length); if (fs > maxFont) maxFont = fs; }
    const block = blockOf(parent);
    let b = blocks.get(block);
    if (!b) { b = {parts: [], fonts: new Map(), visFonts: new Map(), longest: null, maxFont: 0, visibleChars: 0}; blocks.set(block, b); }
    b.parts.push(t);
    b.fonts.set(fs, (b.fonts.get(fs) || 0) + t.length);
    if (fs > b.maxFont && vis) b.maxFont = fs;
    if (vis) { b.visibleChars += t.length; b.visFonts.set(fs, (b.visFonts.get(fs) || 0) + t.length); }
    if (!b.longest || t.length > b.longest.len) b.longest = {node, len: t.length, el: parent};
  }
  // dominant body font: visible text by length, the risk warnings themselves excluded
  const bodyLen = new Map(fontLen);
  for (const [, b] of blocks) {
    if (!RISK.test(fold(b.parts.join(' ')))) continue;
    for (const [fs, n] of b.visFonts) bodyLen.set(fs, (bodyLen.get(fs) || 0) - n);
  }
  const pick = (m) => { let f = null, n0 = 0; for (const [fs, n] of m) if (n > n0 || (n === n0 && n > 0 && fs > f)) { n0 = n; f = fs; } return f; };
  const dominant = pick(bodyLen) || pick(fontLen);
  const topFont = (fonts) => { let f = 0, n = -1; for (const [fs, c] of fonts) if (c > n) { n = c; f = fs; } return f; };

  const risk = [], perf = [], clippedTexts = [];
  for (const [block, b] of blocks) {
    if (performance.now() - t0 > budgetMs) break;
    const text = norm(b.parts.join(' '));
    if (!text) continue;
    const folded = fold(text);
    const styleEl = b.longest.el;
    const visible = visibleCached(styleEl) && b.visibleChars > 0;
    const isClipped = visible && clipped(styleEl);
    if (isClipped && clippedTexts.length < 12) clippedTexts.push(text.slice(0, 160));
    if (RISK.test(folded) && text.length <= 2500 && risk.length < maxItems) {
      const s = cs(styleEl);
      const fg = parseRgba(s.color) || [0, 0, 0, 1];
      const {bg, image} = effectiveBackground(styleEl);
      const opacity = opacityOf(styleEl);
      const fgEff = over([fg[0], fg[1], fg[2], fg[3] * opacity], bg);
      const inter = interactionOf(block, visible, text);
      const elBox = visible ? box(block) : null;
      const ctlBox = inter.control && isVisible(inter.control) ? box(inter.control) : null;
      risk.push({
        key: 'el:' + indexOf.get(block),
        order: indexOf.get(block),
        text: text.slice(0, 600),
        chars: text.length,
        font_px: topFont(b.fonts),
        color: rgb(fgEff),
        background: rgb(bg),
        background_image: image,
        contrast: Math.round(contrast(fgEff, bg) * 100) / 100,
        opacity: Math.round(opacity * 1000) / 1000,
        visible: visible && fg[3] * opacity > 0.05,
        occluded: visible ? occludedAt(styleEl, b.longest.node) : false,
        placement: placementOf(block, text),
        requires_interaction: inter.kind,
        control_text: inter.control ? norm(inter.control.textContent || '').slice(0, 120) : null,
        bbox: elBox || ctlBox,
        bbox_of: elBox ? 'element' : (ctlBox ? 'control' : null),
        clipped: isClipped,
      });
    }
    if (visible && PCT.test(text) && PERF.test(folded) && text.length <= 400 && perf.length < maxItems) {
      const bb = box(block);
      let share = 0;
      if (bb) {
        const ix = Math.max(0, Math.min(bb.x + bb.w, W) - Math.max(bb.x, 0));
        const iy = Math.max(0, Math.min(bb.y + bb.h, H) - Math.max(bb.y, 0));
        share = (ix * iy) / (W * H);
      }
      perf.push({key: 'el:' + indexOf.get(block), order: indexOf.get(block), text: text.slice(0, 400), font_px: b.maxFont || topFont(b.fonts), bbox: bb, area_share: Math.round(share * 1000) / 1000});
    }
  }
  // risk text that exists only in attributes shown on hover / focus (tooltips)
  for (const el of document.querySelectorAll('[title], [data-tooltip], [data-tippy-content], [data-bs-content], [data-content], [data-original-title]')) {
    if (risk.length >= maxItems) break;
    const value = ['title', 'data-tooltip', 'data-tippy-content', 'data-bs-content', 'data-content', 'data-original-title'].map((a) => el.getAttribute(a) || '').join(' ');
    const text = norm(value);
    if (!text || !RISK.test(fold(text)) || text.length > 2500) continue;
    const s = cs(el);
    const fg = parseRgba(s.color) || [0, 0, 0, 1];
    const {bg} = effectiveBackground(el);
    const fgEff = over(fg, bg);
    const ctlBox = isVisible(el) ? box(el) : null;
    risk.push({
      key: 'attr:' + indexOf.get(el), order: indexOf.get(el), text: text.slice(0, 600), chars: text.length,
      font_px: parseFloat(s.fontSize) || 0, color: rgb(fgEff), background: rgb(bg), background_image: false,
      contrast: Math.round(contrast(fgEff, bg) * 100) / 100, opacity: 1, visible: false, occluded: false,
      placement: placementOf(el, text), requires_interaction: 'tooltip',
      control_text: norm(el.textContent || '').slice(0, 120) || null,
      bbox: ctlBox, bbox_of: ctlBox ? 'control' : null, clipped: false,
    });
  }
  window.scrollTo(0, 0);
  const links = [];
  if (collectLinks) {
    for (const a of document.querySelectorAll('a[href]')) {
      if (links.length >= 200) break;
      const href = a.href;
      if (/^https?:/i.test(href)) links.push(href);
    }
  }
  return {
    scale, inner_width: W, inner_height: H,
    client_width: de.clientWidth, scroll_width: Math.max(de.scrollWidth, document.body ? document.body.scrollWidth : 0),
    page_height: Math.max(de.scrollHeight, document.body ? document.body.scrollHeight : 0),
    dominant_font_px: dominant, max_font_px: maxFont,
    risk, perf, clipped_texts: clippedTexts, links,
    has_viewport_meta: !!document.querySelector('meta[name=viewport]'),
    elapsed_ms: Math.round(performance.now() - t0),
  };
}
