# PRD: Wayflyer's Operator Assessment — Pretty Fly

**Internal build by Wayflyer × Fin AI team, ahead of hackathon on 3-5 June 2026.**
**Target build date: today. Executed by AI agent (Claude Code) against the existing data repo.**

---

## What this is

A web-based **operator assessment of Pretty Fly** in Wayflyer's voice. Not a dashboard tool, not a P&L app — a **prepared analytical narrative**, rendered as an interactive product, that says: *here is what the data tells us about this business, and here is what we'd tell their CEO.*

This is the artefact we open the hackathon with, the thing we walk through on stage, and the answer sheet we lean on when discussing builds with participants. *"Here's what we found in the data — now let's see what you found."*

## Why we're building it

1. **It's our answer sheet.** As hosts, we need a confident point of view on the dataset. When a participant pitches "we noticed Pretty Fly is overspending on womens prospecting," we need to be able to say "yes, here's exactly that signal, and here's what we'd add" — not "interesting, tell us more."

2. **It's signature Wayflyer.** "We turn complex data into a comprehensive financial assessment of your business" — this dashboard *is* that value prop, demonstrated in public. It's an asset that holds value beyond the hackathon.

3. **It stress-tests the dataset.** Every chart computed and every total rendered is a real test of whether the data reconciles in practice — not just in `validate.py`. Anything that doesn't hold up gets fixed before participants see the pack.

4. **It sets the bar.** Day 1 opener: participants see *this*, then build their own thing. That's a much higher quality bar than "here's a CSV, build something."

## Audience

**On stage:** the hosting team (you), presenting to ~100 hackathon participants on Day 1 and again at the closing on Day 3.

**One-on-one:** judges, sponsors, future Wayflyer prospects who see this asset after the event.

**Never participants directly during the build.** Deploy URL stays internal until Day 1 reveal.

## Tone — this matters

The dashboard speaks **in Wayflyer's voice**. Confident, opinionated, specific. Numbers backed by interpretation. Each observation is a sentence a Wayflyer analyst would write to a merchant.

Examples of the right voice:

> "Womenswear is acquiring customers at 1.6× the cost of menswear, but those customers are repeating at 1.5× the rate. Pretty Fly is overspending on acquisition for a segment that has real product-market fit — the problem isn't the product, it's the funnel."

> "Caps and sweatpants are running at 42% and 45% gross margin against a portfolio average of 56%. There's £180k of annual margin available to recover by renegotiating supplier terms on these two categories alone."

> "The Generic_Streetwear_UK Google campaign has run for 24 months at a 1.2× ROAS. Pretty Fly has paid £19,000 to Google to generate £23,000 of revenue — a marginal contribution well below the threshold where the marketing pays for itself after fulfilment costs."

Not generic analytics-tool voice. Not vague. Always specific with a number and a recommendation.

## Structure — five tabs

### Tab 1 — Assessment *(the headline)*

The opening view. This is what we screen-share on stage. Eight observations about Pretty Fly's business — one per easter egg — each presented as:

- **A single chart** that makes the observation visible
- **The number** stated plainly: *"£8,400 over 24 months"*
- **Wayflyer's commentary**: 2-4 sentences in the voice above
- **The "what would we do"**: one sentence of recommendation

This is the spine of the closing-ceremony presentation. We walk through the eight observations top to bottom, and each one is a chart + voice + recommendation we can read off the screen.

Ordering matters. Lead with the strongest narratives:

1. **The hidden womenswear story** (easter egg #1 — segment analysis is the showcase Wayflyer build)
2. **Where cash is tied up** (easter egg #8 — direct Wayflyer relevance)
3. **The bleeding Google campaign** (easter egg #2)
4. **Discounting that destroys margin** (easter egg #4)
5. **The dead-weight SaaS subscription** (easter egg #6)
6. **Margin compression on caps and sweatpants** (easter egg #5)
7. **Trainer return rate** (easter egg #3)
8. **Womenswear support volume** (easter egg #7 — natural handoff to Fin AI)

The last observation handing off to Fin AI is deliberate — it sets up their portion of the opening.

### Tab 2 — P&L

The full monthly P&L per the spec format. Two parts:

- **The statement itself** — Gross Sales → Net Sales → Product Margin → Gross Profit → Contribution Profit → Operating Profit → EBITDA. Selectable month, with prior-period and YoY comparison columns where available.

- **Annotated lines** — each P&L line has a small Wayflyer annotation next to it that interprets the number. *"Total Marketing at 21% of revenue — within the healthy band for a growth-stage DTC brand, but the composition is uneven (see Tab 3)."* The annotations are the bridge between "here's a number" and "here's what it means."

Trailing 12-month view available. Memo lines for inventory turnover and DIO at the bottom. Minimum balance sheet items (Cash, Inventory, AP) at the side.

### Tab 3 — Revenue & Marketing

Where revenue comes from and where ad spend goes.

- Daily revenue chart with seasonal/drop annotations
- Channel mix over time (stacked area)
- Mens vs Womens split since Dec 2025 launch
- ROAS by campaign, table with platform-reported vs Shopify-attributed
- CAC trend, split by acquisition channel and by segment

Less editorial than Tab 1 — this is the supporting evidence. But every chart has a one-line caption that interprets it.

### Tab 4 — Operations

Inventory, cash conversion, suppliers. The Wayflyer-native view.

- Inventory health table with DIO flagging
- Cash position over 24 months with PO-deposit moments annotated — *the cash conversion cycle made visible*
- Upcoming supplier payments (next 90 days)
- PO lifecycle view: deposit → balance → delivery → revenue earned (rolling)

Same approach — supporting evidence with light editorial captioning.

### Tab 5 — Customers & Support

How customers behave, what they complain about.

- Cohort retention grid
- LTV by acquisition source — *reinforces the Tab 1 womenswear story*
- Support volume and category breakdown
- Bot resolution rate trend — *the Fin AI invitation*

## Why this surfaces the easter eggs in the strongest possible way

The original PRD framed surfacing as "naturally, as a side effect of good operator views." This version makes it explicit and editorial: each easter egg gets a curated Tab 1 entry with Wayflyer's read on it.

This is better because:
- **You can present it.** Each observation is something to say, not just something to find.
- **It models what a great hackathon build looks like.** Participants who see the Assessment tab understand the bar: insight + chart + recommendation, not just a chart.
- **It's a defensible artefact.** Wayflyer can re-use it post-event as a sample analysis to show prospects. *"This is the kind of read we'd give your business if you shared your data with us."*

## Technical approach

### Stack

- **Frontend:** React + Recharts + Tailwind
- **Backend:** none — static, client-side data loading
- **Data:** the 21 CSV/JSON files from the locked dataset, copied into `/public/data/`
- **Data loading:** PapaParse for CSVs, JSON natively. Loaded once at app startup, held in React context.
- **Hosting:** Vercel deploy, internal URL until Day 1

### Layout & aesthetic

Premium streetwear feel, not corporate analytics. Black/off-white/single accent (e.g. a confident magenta or deep green). Inter or similar — large numbers, generous whitespace, no chartjunk. The dashboard should look like the brand it's reporting on.

Header has a small Wayflyer × Fin AI lockup; tab navigation underneath. Each tab is a single scrollable page. No modals, no sidebar, no clutter.

### Reconciliation route

A `/reconcile` route (linked from footer, not main nav) runs the equivalent of `validate.py` in the browser against the data the dashboard is using. Shows 20/20 pass when working correctly. Our smoke test — if any chart's totals diverge from the validator, we've got a bug.

## Build plan for today

Agent-executed, single day. Phases are sequential but each builds something demoable.

### Phase 0 — Scaffold (early morning)

- Vite + React + TypeScript + Tailwind + Recharts
- Copy locked dataset into `/public/data/`
- Build the CSV/JSON loader and data context
- Wire up basic five-tab navigation with placeholder pages
- Add the `/reconcile` route and implement at least 5 of the 20 rules to prove the pattern works (rest follow in Phase 4)

**Demoable:** the app loads, the data loads, the reconcile route shows ✓ on the rules implemented so far.

### Phase 1 — Assessment tab (mid-morning to early afternoon)

The headline tab. Eight observations, one per easter egg, in the order above.

For each observation:
- Compute the relevant numbers from the data
- Build the chart (one chart per observation, kept simple — line, bar, or table)
- Render the commentary block with placeholder copy
- Render the recommendation

Commentary goes in as my voice from this PRD; you'll review and edit before the event. Don't write it from scratch in the agent — pull from this document and the Weaknesses Reference Card in `GENERATION_NOTES.md`.

**Demoable:** click through eight observations end-to-end. The "what's the dataset about" story is fully tellable from Tab 1 alone.

### Phase 2 — P&L tab (early-to-mid afternoon)

Full P&L renderer with annotated lines. Month selector. YoY comparison column.

Computing the P&L is the biggest reconciliation test in the build — every line has to derive cleanly from the source tables. Spec Section 4 of `pretty_fly_data_pack_spec.md` is the mapping.

**Demoable:** select any month, see the full P&L with Wayflyer's annotations alongside.

### Phase 3 — Supporting tabs (mid-to-late afternoon)

Revenue & Marketing, Operations, Customers & Support — all three. Lighter editorial than Tab 1, but every chart needs a one-line caption.

This is the longest chunk of work but the lowest-judgement — most of it is rendering aggregations with reasonable defaults. Agent should be able to power through.

**Demoable:** every tab populated. Whole dashboard usable end-to-end.

### Phase 4 — Polish + reconciliation (late afternoon)

- Complete the remaining `/reconcile` rules (all 20)
- Visual polish — typography, spacing, accent colour, hover states, empty states
- Run through every tab with one eye on "would I show this on stage"
- Deploy to Vercel
- One full dry-run by us

**Demoable:** stage-ready dashboard at a deploy URL.

### Reserved buffer

A real day rarely goes to plan. Phases above should leave time at the end for unexpected fixes — either in the dashboard or, more usefully, in the data if the build surfaces issues.

## What we'll learn (and fix before the pack ships)

The reason we're doing this *before* the participant pack goes out: every annoyance we hit, every total that doesn't tie, every chart that looks weird — we fix in the data before anyone else sees it.

Expected findings (rough prediction, worth comparing against reality):
- One or two date-parsing inconsistencies between tables
- A join where nulls appear where we didn't expect
- A metric where the headline number is technically right but visually misleading
- One easter egg that's less obvious in chart form than it was in the spec
- At least one place where the README should explain something it currently doesn't

Each finding either: gets fixed in the data, gets documented in the participant README, or gets noted as known limitation.

## Definition of done (end of today)

- [ ] Five tabs implemented, all charts rendering real data
- [ ] All 8 easter eggs surface in the Assessment tab with chart + commentary + recommendation
- [ ] `/reconcile` shows 20/20 pass
- [ ] Headline numbers across all tabs match `sanity_report.py` to the penny
- [ ] Deployed to a Vercel URL (internal access only)
- [ ] One stage-style dry-run completed
- [ ] List of dataset issues surfaced during the build, with fix/document/accept decision noted for each

## What's deliberately out of scope

Even with an agent doing the work, scope discipline matters. We're not building:

- **AI features in the dashboard.** Wayflyer's voice is *us*, written into the commentary. Adding an LLM Q&A interface would dilute the curated narrative and step on participants' build territory.
- **Editing or interactivity beyond filtering.** Read-only, with sensible defaults.
- **Mobile responsiveness.** Desktop only — we're demoing on a laptop.
- **Authentication or multi-user.** Static URL.
- **Anomaly auto-detection.** The Assessment tab is the *curated* version of this — automatic detection would either spoil the easter eggs prematurely or surface things that aren't on the easter egg list.
- **Comparison to other businesses / benchmarks.** No "industry average" rows. The story is Pretty Fly's, not Pretty Fly-vs-the-world.

## Open decisions

1. **Public deploy or internal-only?** Strong preference for internal-only until Day 1 reveal. Avoids any chance of participants seeing the easter-egg spoilers before the event.

2. **Accent colour?** A confident magenta (Wayflyer-ish?) or a deep green (more streetwear-ish?). Either works; small detail but worth picking before the build starts so it threads through.

3. **Voice approval before commit?** Worth one quick review of the Tab 1 commentary copy before the agent ships polish — that's the highest-value editorial decision in the build and it's worth me seeing it before deploy. ~30 minutes of review during Phase 1.

4. **Post-hackathon: re-use as a Wayflyer asset?** Worth deciding now so we build with the right level of polish from the start. If yes, the dashboard wants to be a presentable artefact — favour the deeper editorial in Tab 1, give it a small "About this analysis" footer, design it to be screenshotted.

5. **Where does this repo live?** Same repo as the data, or separate? Separate is cleaner (the data repo is a participant deliverable; this is internal-only). New repo recommended.

---

## Notes for the agent executing this

- The Weaknesses Reference Card in `GENERATION_NOTES.md` is your source of truth for what each Assessment-tab observation should say. Pull commentary from there as a starting point; the human reviewer will edit voice.
- Every number rendered must match what `sanity_report.py` outputs. If you compute something and it doesn't match, debug before moving on — that's the bug we're trying to catch.
- The `/reconcile` route is non-negotiable. It's the smoke test that makes this build worth doing.
- When in doubt on visual design: less is more. Big numbers, clean charts, lots of whitespace. Don't add elements that aren't earning their place.
- Don't add features not in this PRD without flagging. Especially: no AI features, no auto-anomaly detection, no chat interface.

*Next step after PRD approval: start Phase 0.*