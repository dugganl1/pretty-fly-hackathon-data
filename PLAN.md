# Pretty Fly Data Generation — Plan

## 1. Dataset Window

**1 June 2024 – 31 May 2026** (24 months). All timestamps capped at `2026-05-31 23:59:59`.

- Year 1: Jun 2024 – May 2025 (revenue target ~£3M)
- Year 2: Jun 2025 – May 2026 (revenue target ~£4M, ~30% YoY growth)
- Womenswear launches **December 2025** (6 months of mixed-segment data through dataset end)
- `--months 1` generates June 2024 only

---

## 2. Python Module Structure

```
generators/
  __init__.py
  config.py              # Shared constants, seed, date range, Decimal helpers, FX rates
  stage1_products.py     # Products, variants, collections, product_collections, suppliers
  stage2_purchase_orders.py  # POs, PO line items (paced to drops + restock)
  stage3_ads.py          # Google Ads daily, Meta Ads daily
  stage4_orders.py       # Customers, addresses, orders, line items, refunds, discount codes
  stage5_inventory.py    # Inventory movements (reconciling POs, sales, returns)
  stage6_email.py        # Email campaigns, email events
  stage7_support.py      # Support tickets (CSV), support messages (JSON)
  stage8_bank.py         # Bank transactions (reconciling everything)

generate.py              # CLI entrypoint: python generate.py --months 24 --output data/full/
validate.py              # 20 reconciliation rules
sanity_report.py         # Headline metrics + weakness visibility
```

Each `stageN_*.py` module exposes a `generate(config, prior_data) -> dict[str, DataFrame]` function. The main `generate.py` runs them in sequence, piping each stage's output forward. All money handled with `decimal.Decimal`. Random state controlled via a single `numpy.random.Generator` seeded from `config.SEED`.

---

## 3. Drop Timing & Seasonality

### 3.1 Drops calendar

**Year 1 (Jun 2024 – May 2025):**

| Drop | Launch date | Products | Notes |
|------|------------|----------|-------|
| Summer 24 | Jun 2024 | ~12 products | Launch collection — tees, caps, light hoodies |
| Autumn 24 | Sep 2024 | ~12 products | Heavier hoodies, sweatpants, outerwear |
| Winter 24 | Nov 2024 | ~8 products | Pre-Black Friday drop, premium outerwear |
| Spring 25 | Feb/Mar 2025 | ~10 products | Transitional pieces, new colourways |

**Year 2 (Jun 2025 – May 2026):**

| Drop | Launch date | Products | Notes |
|------|------------|----------|-------|
| Summer 25 | Jun 2025 | ~10 products | Summer refresh, new trainer colourways |
| Autumn 25 | Sep 2025 | ~10 products | AW collection, heavier weights |
| **Womens Launch / Winter 25** | **Dec 2025** | **~8 womens + ~4 mens** | **Womenswear debut folded into winter drop** |
| Spring 26 | Feb/Mar 2026 | ~8 products (incl. 2-3 womens) | Spring refresh, womens range expansion |

Plus a **Core** collection (~15-20 products) that exists from day one and stays always-on.

Womens product `created_at` dates are set a few weeks before Dec 2025 launch (pre-launch inventory build). The `Womens_Launch_Prospecting` Meta campaign and womens email flows begin December 2025.

### 3.2 Seasonality curve

Daily order volume = base trend × seasonal multiplier × drop spike × day-of-week effect.

- **Base trend**: gentle upward slope (~30% YoY compounding monthly)
- **Seasonal multiplier** (monthly):
  - Jun 0.90, Jul 0.80, Aug 0.85, Sep 1.05, Oct 1.00
  - Nov 1.30 (Black Friday spike in final week), Dec 1.10 (pre-Christmas, drop-off after 20th)
  - Jan 1.05 (January sale spike in first two weeks, then trough), Feb 0.85, Mar 1.00
  - Apr 1.00, May 0.95
- **Drop spikes**: +200-400% on launch day, exponential decay over ~10 days back to baseline
- **Black Friday**: additional +500% spike on the Friday itself, +300% Sat-Mon, tapering over the week
- **January sale**: +150% spike for the first 10 days of January
- **Day-of-week effect**: weekday orders ~20% higher than weekend

### 3.3 Customer cohorting

- ~60% of customers make exactly 1 purchase
- ~25% make 2 purchases
- ~10% make 3 purchases
- ~5% make 4+ purchases
- Repeat purchases cluster 2-6 months after first order, biased toward drop weeks
- Acquisition channels weighted: Meta paid social ~30%, Google paid search ~25%, Klaviyo email ~15%, organic/direct ~20%, organic social ~10%
- Each customer gets a cohort month (month of first order) and an `acquisition_source`
- Womens repeat rate measured as **repeat purchase within 120 days** of first order (fully observable for Dec 2025 – Jan 2026 cohort within dataset window): ~38% for womens vs ~22% for mens over the same window (weakness #1)
- The womens prospecting cohort (Dec 2025 – Feb 2026) should contain ~400-500 customers — large enough for the signal to be statistically visible

---

## 4. Resolved Design Decisions

All seven open questions from v1 are now settled:

### 4.1 VAT & pricing — VAT-inclusive with extraction
- **Variant prices are VAT-inclusive** (what the UK customer sees). A £50 tee includes £8.33 VAT.
- Price ranges in Section 2 of the spec (£45-60 for tees, etc.) are the VAT-inclusive retail prices.
- UK orders (~75%): `total_tax` = extracted VAT = `(subtotal - total_discounts) × 20/120`. Shipping VAT handled the same way.
- Non-UK orders (~25%): customer pays the VAT-exclusive price. Line item prices are reduced by the VAT component. `total_tax = 0`.
- The reconciliation formula `total_price = subtotal - total_discounts + total_shipping + total_tax` holds for all orders:
  - **UK**: subtotal is VAT-inclusive, total_tax is the extracted VAT (already inside subtotal), so effectively `total_price = subtotal - discounts + shipping`. The `total_tax` field is informational — it's the VAT portion of what was already in subtotal. To make the formula work: for UK orders, subtotal is recorded **net of VAT**, tax is added separately. Wait — this gets circular.
  - **Cleaner model**: Store line item prices as **net** internally. For UK customers, the net price = listed price / 1.20. For non-UK customers, the net price = listed price / 1.20 (same — they pay the ex-VAT amount). UK orders then add `total_tax = 20% × (subtotal_net - discounts + shipping)`. Non-UK add `total_tax = 0`.
  - **Result**: `orders.subtotal` = sum of net line prices × qty. UK `total_price` = subtotal - discounts + shipping + 20% tax. Non-UK `total_price` = subtotal - discounts + shipping. A UK customer buying a "£50" tee pays £50 total (£41.67 subtotal + £8.33 tax). A non-UK customer pays £41.67.
- This matches real Shopify UK behaviour where displayed prices are inclusive but the Shopify data model stores net amounts and adds tax.

### 4.2 Shopify payouts — weekly, 2-business-day settlement
- Orders placed Monday–Sunday settle the following Wednesday (2 business days after the week closes on Sunday).
- Payout = settled orders' `total_price` − refunds processed that week − Shopify Payments fees (2% of settled GMV).
- ~104 payout transactions over 24 months.
- Bank description: `SHOPIFY* XXXX PAYOUT REF#XXXXX`

### 4.3 Order numbers — 1001 to ~26000
Confirmed. Sequential, starting at 1001.

### 4.4 Support messages — JSON; tickets — CSV
`support_tickets.csv` + `support_messages.json` (array of ticket objects, each with a `messages` array).

### 4.5 --months behaviour
`--months 1` generates June 2024 only. Products, suppliers, and POs for the full window are still generated (they're structural), but orders, inventory movements, support tickets, email events, ads, and bank transactions are filtered to the month window. Validators skip metrics requiring more data (e.g. YoY growth) with `N/A — insufficient data` rather than failing.

### 4.6 Collections — many-to-many via join table
- `collections.csv`: collection_id, title, created_at
- `product_collections.csv`: product_id, collection_id
- The `collection` field on `products` is retained as the primary/launch collection for convenience.

### 4.7 Addresses — one per customer
One default address per customer. No separate billing/shipping distinction.

---

## 5. Additional Assumptions

### 5.1 Shipping
- Free shipping on orders with subtotal (net) >= £75
- £4.95 flat rate for UK orders under £75
- £9.95 for EU, £12.95 for US (under threshold)
- ~85% of orders qualify for free shipping
- Shipping amounts are also subject to VAT for UK orders (included in total_tax)

### 5.2 Shopify fees & subscriptions
- Shopify Payments fee: 2.0% of total_price (card processing), deducted from payouts
- Shopify subscription: £79/month (separate bank transaction)

### 5.3 Refunds
- Blended refund rate: ~12% of orders (inflated by trainers at ~22%; apparel alone ~8%)
- Womenswear refund rate: slightly elevated due to sizing (contributes to blended rate)
- Refund amount = full price of returned items (net) + proportional tax for UK orders
- Refunds occur 7-30 days after order, median ~14 days
- Each refund generates: a `refunds` row, inventory `return` movements, and is netted in Shopify payouts

### 5.4 Discounts
- ~15% of orders use a discount code (deliberately moderate — weakness #4)
- Codes: `WELCOME10` (10%, first order), `SUMMER24` (15%, drop promo), `AUTUMN24` (15%, drop promo), `BLACKFRIDAY20` (20%, Nov only), `PRETTYNEW` (£10 off, referral), `NEWYEAR15` (15%, January sale), `WOMENSLAUNCH` (10%, Dec 2025), `SPRING26` (10%, drop promo)
- Discount applied to subtotal before tax calculation
- Key insight for weakness #4: discounted orders have *smaller* basket sizes and negative net contribution for some codes

### 5.5 Fixed operating costs (monthly)
| Cost | Amount | Notes |
|------|--------|-------|
| Payroll | ~£18,000/month | Small team of 6-7; slight raise Jun 2025 |
| Rent | £3,200/month | Studio in N1, London |
| Shopify subscription | £79/month | |
| Klaviyo | £150→£350/month | Grows with list size |
| Fin/Intercom | £199/month | |
| Xero | £42/month | |
| Figma | £33/month | |
| Notion | £24/month | |
| **Mixview Analytics Ltd** | **£349/month** | **Dead-weight SaaS — weakness #6** |
| 3PL | ~£3.50/order | Variable |
| Shipping carriers | ~£6 avg/order | Weighted UK/EU/US mix |

### 5.6 FX rates
- EUR/GBP: 0.86 base, small monthly noise (±2%)
- USD/GBP: 0.79 base, small monthly noise (±2%)
- FX rate locked at PO creation date

### 5.7 Opening bank balance
£180,000 at 1 June 2024.

### 5.8 Items per order
- Average ~1.4 items per order
- Distribution: ~70% single item, ~20% two items, ~8% three items, ~2% four+

---

## 6. Baseline Business Benchmarks

Everything *not* deliberately weakened should hit these healthy targets:

| Metric | Target |
|--------|--------|
| Gross margin (blended) | ~58% |
| EBITDA margin | ~6-9% |
| Blended repeat rate (12-month) | ~30% |
| Blended return rate | ~12% (inflated by trainers; apparel alone ~8%) |
| CAC payback | ~6-9 months |
| Marketing % of revenue | ~22% |
| LTV:CAC (blended) | ~3.0 |
| Cash runway from current burn | ~9-12 months |

---

## 7. Eight Deliberate Weaknesses

These are intentional features baked into the data. Each is surfaceable with straightforward analysis — a group-by, a filter, a chart. A competent analyst with pandas should find each in under 5 minutes.

### 7.1 Summary Table

| # | Weakness | Target metric | Invites build category |
|---|----------|--------------|----------------------|
| 1 | Womens Meta acquisition inefficient, but hidden LTV | Mens Meta CAC ~£28, Womens Meta CAC ~£58. Womens 120-day repeat rate ~38% vs Mens ~22%. Womens AOV slightly higher. Cohort size: ~400-500 womens customers (Dec 2025 – Feb 2026). | Segment analyser |
| 2 | One Google non-brand search campaign bleeds budget | One campaign at ~1.2× ROAS, portfolio average ~3.5× ROAS | Ad efficiency tool |
| 3 | Elevated return rate on trainers (sizing) | Trainers ~22% return rate, apparel ~8% | Returns / fit predictor |
| 4 | Discounting destroys margin without driving volume | ~15% of orders use discount codes; discounted baskets smaller than non-discounted; net contribution after COGS + fulfilment negative for `BLACKFRIDAY20`, `NEWYEAR15`, and `PRETTYNEW` (£10-off referral) codes | Discount strategy tool |
| 5 | Margin compression on caps and sweatpants from supplier overcosting | Caps ~42% gross margin, Sweatpants ~45%, Hoodies ~62%, Tees ~60% | Margin / supplier rebid tool |
| 6 | One dead-weight SaaS subscription | Recurring ~£349/month to "Mixview Analytics Ltd" with no corresponding usage signals | Subscription audit / SpendOps tool |
| 7 | Sizing-driven support volume on womenswear | 31% of womens support tickets are sizing-related vs ~12% for mens | Support automation (Fin AI-aligned) |
| 8 | Slow-moving womens inventory ties up cash | 4 specific womens SKUs at >180 DIO vs portfolio average ~75 DIO: Womens Relaxed Hoodie (Burgundy, M+L), Womens Wide-Leg Sweatpant (Sage, M+L) | Inventory / cash forecasting (Wayflyer-aligned) |

### 7.2 Generator Tuning — How Each Weakness Is Produced

Each weakness is created by adjusting specific parameters from baseline. This section documents exactly which levers are pulled so it's clear these are deliberate features, not random noise.

**Weakness 1 — Womens Meta CAC + hidden LTV:**
- In `stage3_ads.py`: `Womens_Launch_Prospecting` campaign (Dec 2025 – May 2026) gets high daily spend (~£150-200/day) but its conversion rate is set to ~40% of the equivalent mens prospecting campaign. This produces ~£58 CAC vs ~£28 for mens.
- In `stage4_orders.py`: customers acquired via this campaign (utm_campaign matches) are tagged `gender_segment_affinity=womens`. Their order generation uses higher AOV weights (+10-15% vs mens baseline) and a 120-day repeat probability of 0.38 vs 0.22 for mens over the equivalent window.
- **Cohort sizing**: ~400-500 womens customers are acquired via Meta prospecting Dec 2025 – Feb 2026. This is large enough for the repeat-rate signal to be unambiguous in any group-by analysis.
- **Time window**: the 120-day repeat metric is fully observable within the dataset for anyone acquired before ~Feb 2026. The generator schedules repeat purchases for this cohort within the remaining dataset window.
- The contrast between poor acquisition efficiency and strong downstream metrics is the core signal.

**Weakness 2 — Bleeding Google campaign:**
- In `stage3_ads.py`: `Generic_Streetwear_UK` search campaign runs all 24 months at ~£700-900/month. Its conversion_value_gbp is set to ~1.2× its spend (ROAS 1.2). All other Google campaigns target ROAS 3.0-5.0.
- In `stage4_orders.py`: a small number of orders are attributed to this campaign via utm_campaign, keeping real Shopify-attributed ROAS even worse than the platform-reported 1.2× (since platforms overclaim ~15%).

**Weakness 3 — Trainer return rate:**
- In `stage4_orders.py`: when generating refunds, the probability of refund for trainer line items is set to 0.22 vs 0.08 for apparel. Refund reasons for trainers skew to `size_too_small` and `size_too_large`.
- This is independent of gender — trainers have sizing issues for everyone.

**Weakness 4 — Discounting destroys margin:**
- In `stage4_orders.py`: ~15% of orders use a discount code. When a discount code is applied, the item count distribution shifts downward (average ~1.15 items vs ~1.5 for non-discounted). The generator also biases discounted orders toward lower-price items (tees, caps).
- **Negative-contribution codes** (net contribution after COGS + fulfilment is negative):
  - `BLACKFRIDAY20` (20% off): deep discount attracts bargain hunters buying single low-margin items (caps, sweatpants). A single cap at £45 with 20% off: revenue £30.00 net, COGS £17.40 (42% margin), fulfilment ~£9.50 → contribution −£3.10.
  - `NEWYEAR15` (15% off, January sale): same small-basket pattern during a low-intent period. Negative on caps, near-zero on sweatpants.
  - `PRETTYNEW` (£10 fixed off): negative on any order under ~£55 (i.e. single-item cap or tee orders). The fixed-amount discount disproportionately hurts small baskets.
- The signal: these three codes collectively account for ~40% of all discounted orders but generate negative contribution. A participant's tool can flag them by name.

**Weakness 5 — Margin compression on caps and sweatpants:**
- In `stage2_purchase_orders.py`: landed cost per unit for caps is set to ~58% of retail (→ 42% gross margin), and sweatpants to ~55% of retail (→ 45% gross margin). This is achieved by using a more expensive supplier or higher per-unit costs in PO line items.
- Hoodies and tees use the standard cost structure (~38% of retail → 62% margin for hoodies, ~40% → 60% for tees).
- **Blended margin check** — the revenue mix must roll up to ~58%:

| Category | Revenue share | Gross margin | Contribution to blend |
|----------|-------------|-------------|----------------------|
| Tees | 28% | 60% | 16.8% |
| Hoodies | 32% | 62% | 19.8% |
| Sweatpants | 13% | 45% | 5.9% |
| Caps | 4% | 42% | 1.7% |
| Trainers | 13% | 57% | 7.4% |
| Outerwear | 10% | 60% | 6.0% |
| **Blended** | **100%** | | **57.6%** |

- The revenue share weights above are target parameters in `stage4_orders.py` (product selection probabilities). Tees and hoodies dominate revenue because of volume and price respectively. The low-margin categories (caps, sweatpants) are kept to a combined ~17% of revenue so they drag the blend down visibly but not catastrophically.

**Weakness 6 — Dead-weight SaaS:**
- In `stage8_bank.py`: a monthly transaction of ~£349 to `MIXVIEW ANALYTICS LTD` appears every month for all 24 months. There is no corresponding data anywhere else in the dataset — no email events, no ad campaigns, no support integration. Pure waste.
- The name is deliberately distinct from any real tool to avoid confusion.

**Weakness 7 — Womenswear sizing support tickets:**
- In `stage7_support.py`: when generating tickets for orders containing womens products, 31% are assigned `category=sizing_fit`. For mens products, only 12% get this category.
- These tickets reference real womens `product_id` values and include realistic conversation threads about fit uncertainty.

**Weakness 8 — Slow-moving womens inventory:**
- In `stage1_products.py` + `stage2_purchase_orders.py`: 4 specific womens variants receive large initial PO quantities relative to demand:

| SKU | Variant | Units ordered | Target sold | Target remaining | Target DIO |
|-----|---------|--------------|-------------|-----------------|-----------|
| `PF-W-HOOD-REL-BUR-M` | Womens Relaxed Hoodie — Burgundy — M | 120 | ~15 | ~105 | ~240 |
| `PF-W-HOOD-REL-BUR-L` | Womens Relaxed Hoodie — Burgundy — L | 80 | ~8 | ~72 | ~270 |
| `PF-W-SWEAT-WL-SAG-M` | Womens Wide-Leg Sweatpant — Sage — M | 100 | ~12 | ~88 | ~225 |
| `PF-W-SWEAT-WL-SAG-L` | Womens Wide-Leg Sweatpant — Sage — L | 60 | ~5 | ~55 | ~300 |

- In `stage4_orders.py`: these variants are given low purchase probability weights (0.1× baseline), resulting in high remaining inventory.
- Result: these 4 SKUs all exceed 180 DIO vs the portfolio average of ~75 DIO. At landed costs of ~£82 (hoodie) and ~£70 (sweatpant), that's ~£20k of cash tied up in dead stock — visible on the balance sheet and in `inventory_movements` (large po_receipt, few sales).

---

## 8. Seasonality & Event Spikes (Detailed)

| Event | Timing | Effect on daily orders |
|-------|--------|----------------------|
| Summer 24 drop | 1st week Jun 2024 | +300% day 1, decay over 10 days |
| Autumn 24 drop | 1st week Sep 2024 | +350% day 1, decay over 10 days |
| Black Friday 2024 | 29 Nov 2024 | +500% Fri, +300% Sat-Mon, taper over week |
| Winter 24 drop | Mid-Nov 2024 | +250% day 1 (stacks with BF buildup) |
| January sale 2025 | 1-10 Jan 2025 | +150% for 10 days |
| Spring 25 drop | Late Feb 2025 | +300% day 1, decay over 10 days |
| Summer 25 drop | 1st week Jun 2025 | +300% day 1 |
| Autumn 25 drop | 1st week Sep 2025 | +350% day 1 |
| Womens Launch / Winter 25 | 1st week Dec 2025 | +300% day 1, amplified by pre-Christmas |
| Black Friday 2025 | 28 Nov 2025 | +500% Fri, +300% Sat-Mon |
| January sale 2026 | 1-10 Jan 2026 | +150% for 10 days |
| Spring 26 drop | Late Feb 2026 | +300% day 1 |

---

## 9. Verification Approach

### validate.py (20 rules)
Each of the 20 reconciliation rules from Section 9 of the spec becomes an independent function. Every function:
- Loads only the CSVs/JSON it needs
- Uses `decimal.Decimal` for all monetary comparisons
- Allows 1-penny tolerance (£0.01) per row
- Returns `(passed: bool, message: str)`
- On failure, prints 2-3 example rows showing the mismatch
- When `--months 1` produces insufficient data for a rule, returns `(True, "N/A — insufficient data")`

Exit code 0 if all pass, 1 if any fail.

### sanity_report.py (metrics + weakness visibility)
Prints a structured report:
- **Top-line**: gross sales, net sales, AOV, order count, unique customers, gross margin (with explicit check: blended gross margin must land in 55-60% range)
- **Growth**: Y1 vs Y2 revenue, YoY growth %
- **Channel mix**: revenue by UTM source, ad spend by channel, blended CAC
- **Product mix**: top 10 products by units, menswear vs womenswear breakdown
- **Category margins**: gross margin by product_type (surfaces weakness #5)
- **Returns**: overall return rate, return rate by product_type (surfaces weakness #3), by gender segment
- **Discounting**: discount usage rate, AOV discounted vs non-discounted, contribution analysis (surfaces weakness #4)
- **Support**: total tickets, bot resolution rate, sizing % by gender (surfaces weakness #7)
- **Cash**: opening balance, closing balance, runway estimate
- **Inventory health**: DIO by product/variant, flagging >180 DIO items (surfaces weakness #8)
- **Weakness dashboard**: dedicated section with one block per weakness, showing the exact metric and whether it hits the target magnitude

Both scripts accept: `python scriptname.py data/sample/` or `python scriptname.py data/full/`

---

## 10. GENERATION_NOTES.md

A `GENERATION_NOTES.md` file will be produced alongside the data. It will include:

- Schema reference for each table (field names, types, relationships)
- Data generation methodology overview
- **Weaknesses Reference Card** — for each of the 8 weaknesses:
  - **Title** (short, presentation-ready, e.g. "The Hidden Womenswear Goldmine")
  - **Where it shows up** (which tables, which fields, which filters)
  - **The numbers** (exact target metrics observable in the data)
  - **The "so what"** (one-sentence framing of why this matters)
  - **Example pandas snippet** (3-5 lines that surfaces the weakness)
  - **Suggested tool** a participant might build to address it

This is formatted as a clean reference card the hackathon hosts can read from on stage.
