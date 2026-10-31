# Design QA — Sift launch site

**Source visual truth (style references):**
- `.playwright-cli/page-2026-10-31T12-30-38-175Z.png` — vercel.com hero, 1280×720
- `.playwright-cli/page-2026-10-31T12-30-54-984Z.png` — grok.com hero, 1280×720

**Implementation:** http://127.0.0.1:5173/ (Vite dev server)

**Implementation screenshots:**
- Fold: `.playwright-cli/page-2026-10-31T12-38-06-462Z.png` (1280×720, default state)
- Demo after K keypress: `.playwright-cli/page-2026-10-31T12-38-07-505Z.png` (1280×720)
- Sections: `page-2026-10-31T12-39-24-575Z.png`, `page-2026-10-31T12-39-25-609Z.png`, `page-2026-10-31T12-39-26-651Z.png`, `page-2026-10-31T12-39-56-023Z.png`, `page-2026-10-31T12-39-57-056Z.png` (1280×720, scrolled)
- Mobile: `page-2026-10-31T12-40-50-034Z.png`, `page-2026-10-31T12-40-51-052Z.png` (390×844)

**Viewport:** 1280×720 desktop (matches source captures), 390×844 mobile
**State:** default hero; review demo after one `K` press; scrolled sections; mobile stacked

**Comparison approach:** brief is style-matching ("like Grok and Vercel"), not a 1:1 clone — source screenshots judged as the design language (light monochrome, tight display type, pill CTAs, hairline grids, rounded cards). Full-view comparison at matched 1280×720 viewport; focused regions compared on the hero/nav (type, buttons, spacing) and demo card (radii, borders, chips).

## Findings

### Iteration 1 (initial capture `page-2026-10-31T12-36-15-943Z.png`)

- **[P1] Hero overflowed the 720px fold.** Location: `.hero-inner` / `.demo-stage`. Evidence: source (Vercel) fits nav + full hero + start of logo strip within 720; implementation clipped the demo filmstrip and note below the fold, headline pushed to mid-screen. Fix: hero padding 96/72 → 64/48, gap 64 → 52, stage aspect 4/3 → 16/9.
- **[P2] Favicon 404 in console.** Evidence: `Failed to load resource: .../favicon.ico 404`. Fix: added `public/favicon.svg` (brand funnel mark) + `<link rel="icon">`.
- **[P2] Placeholder gradients too saturated vs the monochrome source language.** Evidence: purple mesh dominated the fold; Vercel centerpiece is neutral black. Fix: HSL saturation 42/38/30 → 26/24/18; hero glow alpha 0.16 → 0.10.

### Iteration 2 (post-fix `page-2026-10-31T12-38-06-462Z.png` + section/mobile captures)

- No new P0/P1/P2 findings. Fold now fits: nav + full hero + demo note visible; trust strip begins at the fold edge (Vercel's logo strip is likewise partially below it — classified intentional).
- Console: 0 errors, 0 warnings (only React DevTools info).
- Interaction tested: `K` press → Keep chip 1, advanced to photo 2/8, strip dot + active ring update, filename updates, screenshot placeholder renders.
- Mobile 390×844: nav collapses to brand + CTAs, sections stack single-column, cards full-width, trust strip wraps — no overflow.

### Iteration 3 (copy correctness)

- **[P1] Wrong GitHub org in every link.** Evidence: implementation linked `github.com/latent-spaces/sift`; actual remote is `github.com/alokkr016/sift` (`git remote -v`). Fix: all 8 URLs replaced (nav, hero, install snippet ×2, README, footer ×3). Post-fix evidence: grep confirms 8/8 links use `alokkr016/sift`. Not a visual-layout issue, but app-specific copy — fails the copy fidelity surface until fixed, so it was fixed before handoff.

## Fidelity surfaces

- **Fonts/typography:** Inter (fallback system-ui) vs source Geist — closest free substitute; weights/sizes/tracking match (display 500, -0.04em, ~76px; body 15–17px; mono JetBrains Mono for commands). Checked hierarchy, wrapping, no truncation.
- **Spacing/layout rhythm:** 1280 grid two-column hero ~1.05/0.95, 64px nav, pill buttons, 24px card radii, hairline section dividers — consistent with source rhythm.
- **Colors/tokens:** `#fafafa` bg, `#0a0a0a` ink, `rgba(0,0,0,0.09)` lines, black solid + white outlined pills — matches sampled source palette; one blue accent (Grok's button blue) kept whisper-level in the glow.
- **Image quality/assets:** **Deviation (accepted):** photo placeholders are CSS gradients and the logo is inline SVG per the user's explicit "placeholder visuals" choice; real screenshots/logotype can be swapped in later. Icons are inline SVG (no emoji).
- **Copy/content:** all commands, paths, limits, and stats taken from the repo README; GitHub URLs verified against `git remote`.

## Open Questions

- Placeholders are deliberate (user-selected); switch to real app screenshots when available.
- No mobile hamburger menu — section links are reachable via footer at <980px (P3 follow-up).

## Implementation Checklist

1. ~~Compact hero so the fold fits~~ (done, iteration 2)
2. ~~Add favicon~~ (done, iteration 2)
3. ~~Desaturate placeholder gradients + neutralize glow~~ (done, iteration 2)
4. ~~Fix GitHub URLs to alokkr016/sift~~ (done, iteration 3)

## Follow-up Polish (P3)

- Add a mobile nav menu for the hidden section links.
- Swap CSS-gradient placeholders for real Sift screenshots.
- Hover states on feature cells (border tint) to match Vercel's cell interactivity.

**final result: passed**
