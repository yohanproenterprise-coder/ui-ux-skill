---
description: 7-step pipeline that builds a complete animated single-page website from a text brief. Fully free — uses UI UX Pro Max, Nano Banana 2 (infsh), WebFetch, and hand-crafted code. Optional paid enhancements: Stitch, Firecrawl, Magic.
argument-hint: [optional brief]
---

# Animated Website Builder Pipeline

You are orchestrating a 7-step pipeline that turns a short brief into a complete, production-quality animated single-page website.

**This pipeline is designed to be 100% free.** The core path uses only built-in tools, Nano Banana 2 (free via `infsh`), and open CDNs. Paid MCPs (Stitch, Firecrawl, Magic) are optional enhancements — the pipeline produces excellent output without them.

If the user invoked this command with no arguments, your very first message must be exactly:

> Animated website builder pipeline is ready. What would you like to build?

Then wait for the brief. If arguments were passed, treat them as the brief and skip the greeting.

After receiving the brief, execute the pipeline below, narrating each step briefly (one sentence per step) before running its tool calls. For every optional tool, if it is unavailable or fails, apply the fallback and keep moving — never halt the pipeline on an optional failure.

---

## Step 1 — Intake & Plan

Extract from the brief: product/topic, audience, tone, primary CTA, any reference URLs, any brand colors/fonts the user named, and preferred style keywords. If critical info is missing, ask one consolidated question; otherwise proceed with reasonable defaults.

Produce a short plan (sections, palette direction, typography direction, motion language). Show the plan to the user and ask for confirmation before continuing. If the user says "go" or similar, continue without re-confirming later steps.

---

## Step 2 — Design System (UI UX Pro Max — REQUIRED, FREE)

Invoke the `ui-ux-pro-max` skill to lock in:
- a design style (from the 50+ styles)
- a color palette (from the 161 palettes)
- a font pairing (from the 57 pairings)
- motion language (easing curves, duration scale)

Record the chosen tokens (hex values, font family names, radii, spacing scale, motion timings). These tokens are the single source of truth for all later steps.

> **Cost:** Free. This is a local skill with no API calls.

---

## Step 3 — Reference Scrape (WebFetch PRIMARY — FREE; Firecrawl ENHANCEMENT — OPTIONAL)

Only if the brief included a reference URL:

**Primary (free):** Use the `WebFetch` tool to fetch the URL and extract structure, copy tone, and hero layout from the returned HTML/text.

**Enhancement (optional):** If the `firecrawl_scrape` MCP is available and the user wants deeper JS-rendered scraping, use it instead.

Summarize what to borrow (layout rhythm, headline voice) vs. what to avoid.

Fallback: skip silently if no URL was given or fetch fails.

> **Cost:** WebFetch is free and built-in. Firecrawl has a limited free tier (500 scrapes/month) — only use it if the user explicitly has it configured.

---

## Step 4 — Section Layouts (Hand-Authored PRIMARY — FREE; Stitch ENHANCEMENT — OPTIONAL)

**Primary (free):** Hand-author high-quality semantic HTML sections for: hero, features, social proof, pricing/CTA, and footer. Use the locked design tokens from Step 2 as CSS custom properties. Write clean, well-structured markup — this is the default excellent output.

**Enhancement (optional):** If the `stitch` MCP is available and the user wants AI-generated screen mockups, use:
- `create_project` → `generate_screen_from_text` for each section using Step 2 tokens.
- `fetch_screen_code` to retrieve generated React/HTML per screen.
- Merge the Stitch output into the hand-authored structure.

> **Cost:** Hand-authored HTML is free. Stitch requires a Google account and may have usage limits — use only if explicitly configured.

---

## Step 5 — Hero & Feature Imagery (Nano Banana 2 via infsh — PRIMARY, FREE)

**Primary (free):** Generate the hero image and feature illustrations using Nano Banana 2:

```bash
infsh app run google/gemini-3-1-flash-image-preview --input '{"prompt": "...", "aspect_ratio": "16:9"}'
```

Run image generations in parallel for hero + feature sections. Save the returned paths and embed them in the HTML.

**Fallback (if infsh is not authenticated or unavailable):** Generate high-quality inline SVG illustrations that match the Step 2 palette — gradient blobs, abstract geometric shapes, animated CSS backgrounds. Make these visually polished, not placeholder-quality.

> **Cost:** Free. Nano Banana 2 via `infsh` (inference.sh by Flow) is free to use.

---

## Step 6 — Polished Components (Hand-Coded PRIMARY — FREE; Magic/21st.dev ENHANCEMENT — OPTIONAL)

**Primary (free):** Hand-code all UI components (navbar, pricing table, testimonial grid, bento cards, CTA buttons, footer) using Tailwind CSS and the Step 2 tokens. Apply micro-interactions via CSS transitions and JS event listeners. Quality bar: indistinguishable from a premium template.

**Enhancement (optional):** If the user's brief specifically asked for a 21st.dev component AND the `magic` MCP is available:
- Call `21st_magic_component_builder` with the component request plus Step 2 tokens.
- Splice the returned component into the relevant section.

> **Cost:** Hand-coded Tailwind is free. Magic/21st.dev has usage limits on its free tier — use only if configured.

---

## Step 7 — Assemble & Animate (REQUIRED, FREE)

Produce a single `index.html` at the project root. This step is entirely free — no API calls, only CDN links and code generation.

The file must:
- Load Tailwind via CDN (`<script src="https://cdn.tailwindcss.com"></script>`).
- Load the chosen Google Fonts via `<link>` (free).
- Apply Step 2 tokens as CSS custom properties on `:root`.
- Load GSAP via CDN for animations (free CDN: `https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js` + ScrollTrigger).
- Compose all sections top-to-bottom (Step 4 layouts + Step 5 images + Step 6 components).
- Add GSAP animations: hero entrance (fade + rise with stagger), ScrollTrigger scroll-reveal on each section, hover micro-interactions on CTAs and cards.
- Respect `prefers-reduced-motion` by wrapping all GSAP calls in a motion check.
- Be fully responsive (mobile-first, breakpoints at 640 / 1024 / 1280).
- Include `<title>`, meta description, OG tags, and viewport meta derived from the brief.
- Use semantic HTML5 elements (`<header>`, `<main>`, `<section>`, `<footer>`).

**Animation quality bar:**
- Hero: text splits in with stagger, background gradient shifts slowly.
- Features: cards cascade in on scroll.
- Testimonials / social proof: fade-slide from alternating sides.
- CTA: pulse ring on primary button, lift on hover.
- Navbar: transparent → frosted glass on scroll.

After writing the file, print a short summary:
- What was built and which sections are included.
- Which optional tools fired (Nano Banana 2, Stitch, Firecrawl, Magic) vs. fell back to free alternatives.
- How to preview: `python3 -m http.server 8000` then open `http://localhost:8000`.

Do NOT open a browser or start a server unless the user asks.

---

## Pipeline Rules

- **Free path is primary.** Never treat hand-coded or built-in fallbacks as inferior — produce premium quality regardless.
- Never stop the pipeline for an optional-tool failure — log it and continue with the free path.
- Never invent design tokens outside Step 2's output.
- Run Nano Banana 2 image generations in parallel when multiple images are needed.
- The final deliverable is one `index.html` unless the user asks for a multi-file build.
- If the user has no paid MCPs configured, the pipeline still delivers a complete, high-quality animated website at zero cost.

## Free Tool Summary

| Tool | Free? | Purpose |
|------|-------|---------|
| UI UX Pro Max | ✅ Always free | Design system |
| WebFetch | ✅ Always free | Reference URL scraping |
| Nano Banana 2 (infsh) | ✅ Free via Flow/inference.sh | AI image generation |
| Tailwind CDN | ✅ Always free | Styling |
| Google Fonts | ✅ Always free | Typography |
| GSAP CDN | ✅ Free for non-commercial, CDN always free | Animations |
| Hand-coded HTML/CSS/JS | ✅ Always free | Layouts & components |
| Firecrawl | ⚡ Optional (limited free tier) | Enhanced scraping |
| Stitch | ⚡ Optional (account required) | AI screen layouts |
| Magic / 21st.dev | ⚡ Optional (limited free tier) | Pre-built components |

$ARGUMENTS
