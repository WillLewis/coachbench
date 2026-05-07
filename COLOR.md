# CoachBench — Color Design Plan

**Direction: Broadcast Vault** *(Amber + Cool Slate)*

NFL Films heritage meets a modern analytics product. Amber sits on football's actual visual heritage (leather, end-zone pylons, broadcast lower-thirds), is rare in dev-tool space, and reads as **strategic** rather than "success." Pairs with a violet **insight** color so adaptation moments — the product's headline narrative beat — finally have their own visual signature.

---

## 1. What the palette has to do

CoachBench is a strategy benchmark with adversarial sides. The system has to serve four jobs at once:

1. **Two equal sides.** Offense vs Defense need symmetrical color weight. Not good/bad.
2. **Broadcast intelligence.** Should feel like NFL Films meets Bloomberg Terminal, not Spotify.
3. **Honest semantics.** TD / turnover / validation / adaptation are distinct events; each needs a separate signal that doesn't collide with brand.
4. **Data density that breathes.** The canvas is dark, dense, and read for minutes. Color must be earned per pixel.

## 2. Diagnosis of the current system

The token set in `ui/styles.css` has one accent (`--accent: #00d28e`) doing **at least 14 jobs**: brand wordmark, active nav, primary CTA, validation-OK, inspector-tab-active, chips, `code`, hover borders, meter fills, adaptation feed cards, sparkline strokes, positive deltas, slate-seed numbers, film-room "next" callout. The `--warn` red is used for genuine failure *and* the end-zone marker — semantically wrong, since the end zone is the goal, not a hazard.

This produces:

- **No hierarchy** between primary action and ambient state.
- **Brand reads as generic dev-tool green**, indistinguishable from Vercel / Linear / Replit / Stripe.
- **Adaptation events** look identical to a "valid" badge.
- **Offense/Defense are color-undifferentiated** — the central dramatic axis of the product is invisible.

## 3. Design principles

| Principle | Implication |
|---|---|
| **One brand color, used scarce** | Wordmark, single primary CTA per screen, one "now" indicator. ≤5% of pixels. |
| **Two team colors, equal weight** | Offense and Defense are *peers*, not winner/loser. |
| **Three semantic signals** | Positive (success / TD), Negative (turnover / warn), Insight (adaptation / belief shift). Each visually distinct from brand. |
| **Numerals get tabular neutrals, not brand** | Score, points, deltas, yardage — all neutral by default; color only when state is non-default. |
| **Warm + cool tension** | Football leather warm + analyst-grade cool. Avoids the "everything is teal" trap. |
| **The field is furniture** | Field surface is the dimmest area, not the brightest. Color goes on action, not on the stadium. |

## 4. The palette

### Surfaces (cool slate)

| Token | Hex | Role |
|---|---|---|
| `--bg` | `#0B0D12` | Page surface, slightly cool |
| `--bg-elev-1` | `#14171F` | Panels |
| `--bg-elev-2` | `#1C2030` | Inputs, raised cards |
| `--border` | `#252A38` | Hairline |
| `--border-strong` | `#3A4154` | Emphasis hairline |

### Type

| Token | Hex | Role |
|---|---|---|
| `--text` | `#F2F4F8` | Primary |
| `--text-muted` | `#9099AB` | Labels, eyebrows |
| `--text-faint` | `#5C6577` | Tertiary |

### Brand (scarce)

| Token | Hex | Role |
|---|---|---|
| `--brand` | `#F2B85C` | Amber. Wordmark, hero number, single primary CTA |
| `--brand-soft` | `rgba(242,184,92,0.10)` | Brand background tint |

### Team axis (equal weight)

| Token | Hex | Role |
|---|---|---|
| `--offense` | `#FF7A59` | Coral. Offense call cards, offense belief bar |
| `--offense-soft` | `rgba(255,122,89,0.10)` | Offense tint |
| `--defense` | `#4FB3FF` | Sky. Defense call cards, defense belief bar |
| `--defense-soft` | `rgba(79,179,255,0.10)` | Defense tint |

### Semantic (state only)

| Token | Hex | Role |
|---|---|---|
| `--positive` | `#6EE7B7` | TD, validation-OK, delta-pos |
| `--positive-soft` | `rgba(110,231,183,0.10)` | Positive tint |
| `--negative` | `#FB7185` | Turnover, validation-fail, delta-neg |
| `--negative-soft` | `rgba(251,113,133,0.10)` | Negative tint |
| `--insight` | `#C4B5FD` | Adaptation / belief-shift moments — the third semantic |
| `--insight-soft` | `rgba(196,181,253,0.10)` | Insight tint |

### Field & ball

| Token | Hex | Role |
|---|---|---|
| `--field` | `#13201E` | Muted dark teal — broadcast-board feel |
| `--ball` | `#FBBF24` | Keep |

## 5. Where color goes (and where it doesn't)

This matters more than the hex codes.

### Brand (`--brand`) — ≤5% of pixels

- Wordmark only (`index.html:11`)
- **One** primary CTA per route, not every `.btn`
- `.scorecard strong` numeric — kept; the score is the literal headline
- `.mode-banner.static-proof` dot
- **Remove from**: `.chip`, `code`, active nav (use neutral underline instead), inspector-tab active (border + neutral fill), film-notes summary, slate-seed, sparkline strokes, gallery hover border, resume-chip background

### Team axis (`--offense` / `--defense`) — the new dramatic axis

- Offense call card: 3px left stripe + eyebrow in `--offense`
- Defense call card: same in `--defense`
- Belief-state bars: split — offense conviction in `--offense`, defense conviction in `--defense`
- Sparklines: when comparing two series, offense vs defense. Single series stays neutral white.
- Roster grid: each side wears its team color in the eyebrow only; bars stay neutral
- Resource matrix deltas: decoupled from brand — `--positive` / `--negative`

### Semantic — used only for state, never for decoration

- `--positive`: validation-OK badge, TD outcome flash, success deltas
- `--negative`: validation-fail, turnover flash, negative deltas. **Stop using it for the end zone** — color the end zone with `--brand-soft` or `--positive-soft`; the end zone is the goal, not a hazard.
- `--insight`: reserved for adaptation events (`.feed-card.is-adaptation`), belief-state pulses (`@keyframes barGlow`), and the Film Room "next adjustment" callout (`.film-next`). This single change makes the headline product moment — *the agent learned* — visually identifiable in a half-second glance.

### Neutrals — the canvas, 85%+ of pixels

- Field surface dark muted; yard rules at 6–8% white
- All `.chip` borders/backgrounds neutral by default. A chip turns colored only when it *carries state* (e.g., an offense-tagged chip wears `--offense`)
- `.btn` hover: neutral `--border-strong`. The `.btn` only turns brand on the **primary** action of the screen.
- `code` literal: neutral mono treatment, not green

## 6. Quick-win sequence

If only one day were available:

1. **Split brand from semantic.** Add `--positive`, `--negative`, `--insight` tokens; move all `is-ok` / `delta-pos` / adaptation usage off `--accent`.
2. **Introduce `--offense` and `--defense`.** Apply to the call-card eyebrow + 3px left stripe, and to belief bars.
3. **De-color the chips and `code`.** Single biggest perceptual cleanup — the screen will instantly feel calmer.
4. **Move brand to amber `#F2B85C`.** Wordmark, one CTA, score number — that's it.
5. **Re-color the end zone.** It's the goal, not a danger zone.
6. **Field tone darker, more muted.** The play card and feed should pop *off* the field, not compete with it.

## 7. Component-level application map

| Current (`styles.css`) | Today | New |
|---|---|---|
| `.wordmark` | `--accent` | `--brand` |
| `.nav-links a.active` | `--accent` bg + border | neutral text + 1px `--brand` underline |
| `.scorecard strong` | `--accent` | `--brand` (kept) |
| `.mode-banner.static-proof` | `--accent` | `--brand` |
| `.btn` hover | `--accent` border | `--border-strong` border (only primary CTA gets `--brand`) |
| `.icon-btn` | `--accent` | `--text-muted`, hover `--text` |
| `.chip` | `--accent` background | neutral chip; colored variants `chip--offense` / `chip--defense` / `chip--insight` |
| `code` | `--accent` | `--text` with `--bg-elev-2` background |
| `.fill` (meter) | `--accent` | `--text-muted` default; `--offense` / `--defense` for belief bars |
| `.validation-badge.is-ok` | `--accent` | `--positive` |
| `.validation-badge.is-warn` | `--warn` | `--negative` |
| `.feed-card.is-adaptation` | `--accent` | `--insight` |
| `.film-next` | `--accent-soft` bg | `--insight-soft` bg, `--insight` left rule |
| `.delta-pos` / `.delta-neg` | `--accent` / `--warn` | `--positive` / `--negative` |
| `.endzone` | `--warn` tint | `--brand-soft` tint, `--brand` left border |
| `.field` background | `#101114` | `--field` `#13201E` |
| `.ball` | `--ball` | `--ball` (unchanged) |
| `.slate-seed` | `--accent` | `--text-muted` (numerals stay neutral) |
| Inspector tab active | `--accent` bg | `--bg-elev-2` bg + `--brand` 2px bottom border |
| Sparkline stroke | `--accent` | `--text-muted` single-series; `--offense` / `--defense` two-series |

## 8. Final composition rule

A viewer should be able to **count brand-color occurrences on one hand** per screen. If the count goes higher, something has been miscategorized as brand when it should be neutral, semantic, or team-axis.
