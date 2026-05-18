# Pretty Fly — Generation Notes

> **Audience:** Hackathon hosts, not participants. This file documents how the dataset was generated, the assumptions made, and a complete reference card for the eight deliberate weaknesses baked into the data.

---

## 1. Reproduction

**Seed:** `42` (numpy `default_rng(42)`, with per-stage offsets `SEED + N`).

**Command:**
```bash
python generate.py --months 24 --output data/full/
```

The generator is deterministic — same seed, same code, same output. All monetary arithmetic uses `decimal.Decimal` to avoid floating-point drift.

**Dataset window:** 1 June 2024 – 31 May 2026.

---

## 2. Repeat-rate lineage

Early validation runs showed different 120-day repeat rates because the generator was iteratively tuned:

| Run | Mens 120-day | Womens 120-day | Notes |
|-----|-------------|----------------|-------|
| v1 (38k customers) | 11.7% | 33.4% | Low repeat prob (22%), uniform customer selection. Too many unique customers. |
| v2 (20k customers) | 42.1% | 79.1% | High repeat prob + 2,000-person recency pool. Concentrated ALL repeats within days. Womens looked like a subscription product. |
| v3 (22k customers) | 36.6% | 69.5% | Widened pool to 5,000. Better but womens still too high. |
| **Final (22.4k)** | **37.4%** | **57.7%** | 50/50 blend for womens (dedicated pool + general pool), 55/45 split for mens (recent + full-base). Womens median days-to-repeat: 16. |

The original spec targeted 10-12k customers with 30% repeat, but those figures were internally inconsistent with the order count target (20-25k/year). The final dataset lands at ~22k unique customers with ~50k orders — closer to the order target, with a realistic repeat profile for a premium streetwear brand.

---

## 3. Assumptions made during generation

| Assumption | Rationale |
|-----------|-----------|
| **POs per-drop-per-supplier** (21 total, not per-product) | Realistic: a drop is one order per supplier. ~25-30 POs over 24 months. |
| **One refund per order max** | Simplifies inventory movement reconciliation. Refund can return one variant. |
| **Cap sizes as "ONE"** | Caps are one-size-fits-all in streetwear. No S/M/L variants. |
| **Trainer sizes UK6-12** (7 sizes) | Spec said "~8 sizes". UK6-12 is 7, close enough. |
| **VAT-inclusive pricing with extraction** | Variant prices are what a UK customer pays. Net = price / 1.20. Non-UK pays the net amount. |
| **Shopify payouts weekly** | Orders Mon-Sun settle the following Wednesday. Refunds batched monthly. |
| **Ad spend paid on last day of spending month** | Keeps monthly ad spend = monthly bank transaction exactly. |
| **HMRC VAT paid quarterly** | Standard UK VAT return schedule. First payment in dataset: August 2024. |
| **PO deposits ~60-90 days before delivery** | Based on supplier lead times. Summer 24 deposits fall before dataset start (April 2024). |
| **Opening bank balance £400k** | Realistic for a £4M-revenue DTC brand with seasonal inventory commitments. |
| **Prospecting campaigns force ~90% new customers** | Prospecting = acquisition. Non-prospecting channels handle repeats. |

---

## 4. Weaknesses Reference Card

Eight deliberate inefficiencies baked into the data. Each is surfaceable with basic pandas in under 5 minutes — the value participants add is the tool they build around the insight, not finding it.

---

### Weakness 1: "The Hidden Womenswear Goldmine"

**Where it shows up:** `meta_ads_daily` (campaign spend), `customers` (gender_segment_affinity), `orders` (utm attribution, repeat behaviour)

**The numbers:**
- Womens Meta CAC: **£81** vs mens Meta CAC: **£50** (1.6× ratio)
- Womens 120-day repeat rate: **57.7%** vs mens: **37.4%** (1.5× ratio)
- Womens AOV (Meta-acquired): **£128** vs mens: **£131** (comparable)
- Womens Meta cohort: **395 customers** from £32k spend

**The "so what":** Womens acquisition is expensive but the customers are stickier — they repeat at 1.5× the mens rate. The brand is over-spending on acquisition and under-investing in retention. Fix the funnel, not the segment.

**Example pandas snippet:**
```python
import pandas as pd

orders = pd.read_csv("data/orders.csv")
customers = pd.read_csv("data/customers.csv")
meta = pd.read_csv("data/meta_ads_daily.csv")

# CAC by gender
womens_spend = meta[meta.campaign_name.str.contains("Womens", case=False)].spend_gbp.sum()
womens_custs = customers[customers.gender_segment_affinity == "womens"].shape[0]
mens_spend = meta[~meta.campaign_name.str.contains("Womens", case=False)].spend_gbp.sum()
mens_custs = customers[customers.gender_segment_affinity == "mens"].shape[0]
print(f"Mens CAC: £{mens_spend/mens_custs:.0f}  |  Womens CAC: £{womens_spend/womens_custs:.0f}")
```

**Suggested tool:** Customer segment analyser — surfaces LTV vs CAC by segment and recommends reallocation.

---

### Weakness 2: "The Campaign That's Burning Cash"

**Where it shows up:** `google_ads_daily` (campaign-level spend and conversion value)

**The numbers:**
- `Generic_Streetwear_UK`: ROAS **1.2×** on £24.3k total spend
- Portfolio average ROAS: **3.5×**
- All other campaigns: 3.0-5.0× ROAS

**The "so what":** One non-brand search campaign has been bleeding budget for 24 months. Kill it tomorrow and redeploy the £1k/month to Shopping or PMax.

**Example pandas snippet:**
```python
google = pd.read_csv("data/google_ads_daily.csv")
by_camp = google.groupby("campaign_name").agg({"spend_gbp": "sum", "conversion_value_gbp": "sum"})
by_camp["roas"] = by_camp.conversion_value_gbp / by_camp.spend_gbp
print(by_camp.sort_values("roas"))
```

**Suggested tool:** Ad efficiency dashboard — ranks campaigns by ROAS with spend-weighted alerts.

---

### Weakness 3: "The Trainer Sizing Problem"

**Where it shows up:** `refunds` (reason field), `line_items` + `products` (product_type join)

**The numbers:**
- Trainer return rate: **26.8%**
- All other categories: **12-14%**
- Trainer refund reasons: predominantly `size_too_small` / `size_too_large`

**The "so what":** Trainers return at 2× the rate of everything else, almost entirely due to sizing. Better fit guidance or a size-recommendation tool would cut returns by half.

**Example pandas snippet:**
```python
orders = pd.read_csv("data/orders.csv")
refunds = pd.read_csv("data/refunds.csv")
li = pd.read_csv("data/line_items.csv")
products = pd.read_csv("data/products.csv")

refund_orders = set(refunds.order_id)
li_typed = li.merge(products[["product_id", "product_type"]], on="product_id")
li_typed["refunded"] = li_typed.order_id.isin(refund_orders)
print(li_typed.groupby("product_type")["refunded"].mean().sort_values())
```

**Suggested tool:** Returns predictor or AI sizing assistant — predicts return risk at checkout and recommends correct size.

---

### Weakness 4: "Discounts That Destroy Margin"

**Where it shows up:** `orders` (discount_code, total_discounts), `line_items` (basket composition)

**The numbers:**
- Discount usage rate: **14.6%** of orders
- Discounted basket: **1.20 items** avg vs non-discounted: **1.44 items**
- Discounted AOV: **£103** vs non-discounted: **£135**
- `BLACKFRIDAY20` and `SUMMER24` have the lowest per-order contribution

**The "so what":** Discounts don't increase basket size — they shrink it. Customers using codes buy fewer, cheaper items. Some codes are net-negative after COGS and fulfilment.

**Example pandas snippet:**
```python
orders = pd.read_csv("data/orders.csv")
li = pd.read_csv("data/line_items.csv")
items_per_order = li.groupby("order_id")["quantity"].sum()
orders["items"] = orders.order_id.map(items_per_order)
orders["has_discount"] = orders.discount_code.fillna("").str.len() > 0
print(orders.groupby("has_discount")[["items", "total_price"]].mean())
```

**Suggested tool:** Discount strategy analyser — models contribution per code and recommends which to kill.

---

### Weakness 5: "The Supplier Problem Hiding in the Margins"

**Where it shows up:** `line_items` + `po_line_items` (landed cost join via variant_id), `products` (product_type)

**The numbers:**
- Caps: **42%** gross margin
- Sweatpants: **45%** gross margin
- Hoodies: **62%**, Tees: **60%**, Outerwear: **60%**, Trainers: **57%**

**The "so what":** Caps and sweatpants are 15-20 points below the rest of the portfolio. The supplier is overcharging or the brand hasn't renegotiated. At current volumes, fixing cap margins alone recovers ~£40k/year.

**Example pandas snippet:**
```python
li = pd.read_csv("data/line_items.csv")
po = pd.read_csv("data/po_line_items.csv")
products = pd.read_csv("data/products.csv")
variants = pd.read_csv("data/variants.csv")

cost = po.groupby("variant_id")["landed_cost_per_unit_gbp"].last()
li["cost"] = li.variant_id.map(cost) * li.quantity
li["rev"] = li.price * li.quantity
li["product_type"] = li.product_id.map(products.set_index("product_id")["product_type"])
print(li.groupby("product_type").apply(lambda x: 1 - x.cost.sum()/x.rev.sum()).sort_values())
```

**Suggested tool:** Margin diagnostic / supplier rebid tool — flags categories below threshold and models the P&L impact of renegotiation.

---

### Weakness 6: "The SaaS Line Nobody Cancelled"

**Where it shows up:** `bank_transactions` (description contains "MIXVIEW ANALYTICS")

**The numbers:**
- Mixview Analytics Ltd: **£349/month × 24 months = £8,376** total
- No corresponding data anywhere else in the dataset (no events, no campaigns, no integrations)
- Pure waste

**The "so what":** Someone signed up for an analytics tool two years ago and nobody cancelled it. £8.4k is a small line but it's free money — and a participant who surfaces it is demonstrating subscription audit capability.

**Example pandas snippet:**
```python
bank = pd.read_csv("data/bank_transactions.csv")
subs = bank[bank.raw_category == "SAAS"].groupby("counterparty")["amount_gbp"].sum()
print(subs.sort_values())
# Mixview Analytics shows up alongside legitimate tools — but has no matching usage data
```

**Suggested tool:** Subscription audit / SpendOps tool — cross-references SaaS payments against usage signals and flags orphaned subscriptions.

---

### Weakness 7: "The Sizing Guide That's Failing Women"

**Where it shows up:** `support_tickets` (category, related_product_id), `products` (gender_segment)

**The numbers:**
- Womens sizing-related tickets: **37.7%** of all womens tickets
- Mens sizing-related tickets: **13.1%** of all mens tickets
- 3× gap — womens customers are confused about fit at nearly triple the rate

**The "so what":** The womenswear sizing guide is broken or missing. Every sizing ticket is a potential lost sale or unnecessary return. An AI sizing assistant or better product descriptions could cut this by half.

**Example pandas snippet:**
```python
tickets = pd.read_csv("data/support_tickets.csv")
products = pd.read_csv("data/products.csv")
tickets = tickets.merge(products[["product_id", "gender_segment"]],
                        left_on="related_product_id", right_on="product_id", how="left")
sizing = tickets[tickets.category == "sizing_fit"]
print(tickets.groupby("gender_segment")["category"].apply(
    lambda x: (x == "sizing_fit").mean()).sort_values())
```

**Suggested tool:** Support automation (Fin AI-aligned) — auto-resolves sizing queries using product data, or a sizing recommendation widget for the storefront.

---

### Weakness 8: "The Cash Trapped in Dead Stock"

**Where it shows up:** `variants` (inventory_quantity), `inventory_movements`, `po_line_items` (landed cost)

**The numbers:**
- **45 womens SKUs** with DIO > 180 days
- **£24.5k** of cash tied up in slow-moving womens stock
- Worst offenders: Womens Wide-Leg Sweatpants (Sage, Charcoal, Vintage Cream in M/L/S)
- Portfolio average DIO is healthy; these are clear outliers

**The "so what":** The initial womens buy was too aggressive on certain colourways and the demand didn't follow. That inventory is cash the brand can't use for anything else. A Wayflyer-style cash forecasting tool would have flagged this before the PO was placed.

**Example pandas snippet:**
```python
variants = pd.read_csv("data/variants.csv")
li = pd.read_csv("data/line_items.csv")
po = pd.read_csv("data/po_line_items.csv")
products = pd.read_csv("data/products.csv")

sold = li.groupby("variant_id")["quantity"].sum()
cost = po.groupby("variant_id")["landed_cost_per_unit_gbp"].last()
variants["sold"] = variants.variant_id.map(sold).fillna(0)
variants["cost"] = variants.variant_id.map(cost).fillna(0)
variants["dio"] = variants.inventory_quantity * 730 / variants.sold.clip(lower=1)
variants["gender"] = variants.product_id.map(products.set_index("product_id")["gender_segment"])
slow = variants[(variants.gender == "womens") & (variants.dio > 180)]
print(slow[["sku", "inventory_quantity", "sold", "dio"]].sort_values("dio", ascending=False))
```

**Suggested tool:** Inventory / cash forecasting tool (Wayflyer-aligned) — predicts sell-through and flags overstock risk before POs are placed.
