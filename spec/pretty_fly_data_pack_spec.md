# Pretty Fly — Hackathon Data Pack Specification

> **Purpose:** This document specifies the complete dummy dataset to be provided to participants in the "Build the Future of E-commerce" hackathon, co-hosted by Wayflyer and Fin AI. It is intended as a brief for the dummy data provider. Every dataset described below must reconcile to the cent with every other dataset where indicated.

---

## 1. The Fictional Business

**Pretty Fly** is a London-based premium streetwear brand selling t-shirts, hoodies, sweatpants, caps, and trainers to fashion-conscious consumers. Reference points: Cole Buxton, Stüssy. The brand started in menswear and launched a small womenswear line approximately 6 months before the end of the dataset window.

| Attribute | Value |
|---|---|
| Headquarters | London, UK |
| Currency | GBP (£) — all reporting in GBP; some supplier invoices in EUR/USD |
| Sales channels | Shopify DTC (primary), some wholesale ignored for this exercise |
| Markets | UK primary (~75% of revenue), EU (~15%), US (~10%) |
| Dataset timeframe | **24 months**, ending at a clean month-end |
| Annual revenue | £3-5M (target: ~£4M in year 2) |
| Annual orders | 20-25k |
| Unique customers | 10-12k |
| Average order value | £120-160 |
| Gross margin | High-50s to low-60s % |
| Business health | Moderately healthy with discoverable opportunities for improvement |

---

## 2. Product Catalogue & Pricing

The catalogue should feel like a real premium streetwear brand. Suggested product type distribution:

| Category | SKU count (variants) | Price range (£) |
|---|---|---|
| T-shirts | ~25 products × 4 sizes × 3 colours | £45-60 |
| Hoodies | ~15 products × 4 sizes × 3 colours | £140-175 |
| Sweatpants | ~10 products × 4 sizes × 2 colours | £125-160 |
| Caps | ~12 products × 1 size × 3 colours | £40-55 |
| Trainers | ~6 products × 8 sizes × 2 colours | £175-225 |
| Outerwear / heavier knitwear | ~5 products (premium tier) | £200-350 |

**Sizes:** XS, S, M, L, XL for apparel; UK 6-12 for trainers.

**Colourways:** Use realistic premium streetwear palettes — washed black, vintage cream, faded olive, charcoal, off-white, deep navy, burgundy, sage.

**Drops:** ~6-8 drops per year. Drops cause clear sales spikes. Some pieces are "core" (always-on), most are seasonal/limited.

**Womenswear:** Launched 6 months before dataset end. ~8 products initially (tees, hoodies, sweatpants, one cap), priced 5-10% lower on average. Sizes XS-L.

---

## 3. Datasets to Generate

### 3.1 Shopify Storefront Data

#### `products`
| Field | Type | Notes |
|---|---|---|
| product_id | string | e.g. `prod_00001` |
| title | string | e.g. "Heritage Hoodie", "Court Tee" |
| handle | string | URL-safe slug |
| description | text | Brand-voiced product copy |
| product_type | string | Tee / Hoodie / Sweatpants / Cap / Trainer / Outerwear |
| vendor | string | "Pretty Fly" |
| collection | string | "Core", "SS24 Drop", "AW24 Drop", "Womens", etc. |
| gender_segment | enum | `mens` / `womens` / `unisex` |
| tags | array | e.g. `["drop:ss24", "category:hoodie", "fit:relaxed"]` |
| status | enum | `active` / `archived` |
| created_at | timestamp | Drop launch date |

#### `variants`
| Field | Type | Notes |
|---|---|---|
| variant_id | string | e.g. `var_00001` |
| product_id | FK | → products |
| sku | string | e.g. `PF-HOOD-HER-BLK-M` |
| option1_name / option1_value | string | "Size" / "M" |
| option2_name / option2_value | string | "Colour" / "Washed Black" |
| price | decimal | Retail price in GBP |
| compare_at_price | decimal | Original price if discounted, else null |
| barcode | string | 12-digit EAN-like |
| weight_grams | int | |
| inventory_quantity | int | Current stock (snapshot at dataset end) |

#### `collections`
Simple lookup: `collection_id`, `title`, `created_at`. Products may belong to multiple collections.

#### `customers`
| Field | Type | Notes |
|---|---|---|
| customer_id | string | |
| email | string | Realistic but fake (`name@example-domain.com`) |
| first_name / last_name | string | |
| created_at | timestamp | First account creation |
| accepts_marketing | bool | ~70% true |
| total_spent | decimal | Sum of orders.total_price (must reconcile) |
| orders_count | int | Must reconcile |
| acquisition_source | string | First-touch UTM (e.g. `google/cpc/brand`, `meta/paid_social/ss24_launch`, `klaviyo/email/welcome`, `direct`) |
| acquisition_date | timestamp | Date of first order |
| default_country | string | UK / FR / DE / NL / US / IE etc. |
| gender_segment_affinity | enum | Derived from purchase history: `mens` / `womens` / `mixed` |

#### `addresses`
Standard shipping/billing fields linked to customer_id. UK-heavy distribution.

#### `orders`
| Field | Type | Notes |
|---|---|---|
| order_id | string | |
| order_number | int | Sequential, e.g. 1001-26000 |
| customer_id | FK | |
| created_at | timestamp | |
| currency | string | Always GBP |
| subtotal | decimal | Sum of line items before discount |
| total_discounts | decimal | |
| total_shipping | decimal | |
| total_tax | decimal | VAT @ 20% for UK, 0% for non-UK (export) |
| total_price | decimal | Final amount paid |
| financial_status | enum | `paid` / `partially_refunded` / `refunded` |
| fulfillment_status | enum | `fulfilled` / `partial` / `unfulfilled` |
| utm_source | string | `google` / `facebook` / `instagram` / `klaviyo` / `direct` / `organic` |
| utm_medium | string | `cpc` / `paid_social` / `email` / `organic` |
| utm_campaign | string | Must match a campaign name in ads or email tables |
| landing_site | string | |
| referring_site | string | |
| tags | array | |

#### `line_items`
| Field | Type | Notes |
|---|---|---|
| line_item_id | string | |
| order_id | FK | |
| variant_id | FK | |
| product_id | FK | |
| title | string | Product + variant title snapshot |
| quantity | int | |
| price | decimal | Unit price at time of order |
| total_discount | decimal | Discount applied to this line |

#### `discount_codes`
| Field | Type | Notes |
|---|---|---|
| code | string | e.g. `WELCOME10`, `SS24LAUNCH`, `RESTOCK15` |
| type | enum | `percentage` / `fixed_amount` / `free_shipping` |
| value | decimal | |
| usage_count | int | Must match count of orders applying this code |
| starts_at / ends_at | timestamp | |

#### `refunds`
| Field | Type | Notes |
|---|---|---|
| refund_id | string | |
| order_id | FK | |
| created_at | timestamp | Typically 7-30 days after order |
| amount | decimal | |
| reason | enum | `size_too_small` / `size_too_large` / `not_as_described` / `quality_issue` / `changed_mind` / `damaged_in_transit` |
| refund_line_items | array | variant_ids returned |

**Reconciliation rules — Shopify:**
- `orders.subtotal` = sum of (`line_items.price` × `line_items.quantity`) for that order
- `orders.total_price` = subtotal − discounts + shipping + tax
- `customers.total_spent` = sum of `orders.total_price` for that customer
- `customers.orders_count` = count of orders for that customer
- `discount_codes.usage_count` = count of orders using that code

---

### 3.2 Suppliers, Purchase Orders & Inventory

#### `suppliers`
| Field | Type | Notes |
|---|---|---|
| supplier_id | string | |
| name | string | e.g. "Porto Knit Co.", "Milano Trims SRL", "Lisbon Garment Works" |
| country | string | Portugal (most), Italy (premium), Turkey (basics) |
| payment_terms | string | e.g. "50% deposit / 50% on shipment", "Net 60" |
| lead_time_days | int | 45-90 typical |
| currency | string | EUR primarily, some GBP |

#### `purchase_orders`
| Field | Type | Notes |
|---|---|---|
| po_id | string | e.g. `PO-2023-0042` |
| supplier_id | FK | |
| created_at | timestamp | |
| expected_delivery | date | |
| actual_delivery | date | **Equal to expected_delivery** — simplified, no lead-time variance |
| status | enum | `received` (for past POs) / `in_production` / `placed` (for future) |
| total_cost_supplier_ccy | decimal | In supplier's currency |
| total_cost_gbp | decimal | Converted at order date FX |
| deposit_paid_at | date | |
| balance_paid_at | date | |

#### `po_line_items`
| Field | Type | Notes |
|---|---|---|
| po_line_id | string | |
| po_id | FK | |
| variant_id | FK | |
| quantity_ordered | int | |
| quantity_received | int | Equal to quantity_ordered |
| unit_cost_supplier_ccy | decimal | |
| landed_cost_per_unit_gbp | decimal | Includes freight + duties (typical: unit cost × 1.15-1.25) |

#### `inventory_movements`
| Field | Type | Notes |
|---|---|---|
| movement_id | string | |
| variant_id | FK | |
| date | timestamp | |
| type | enum | `po_receipt` / `sale` / `return` |
| quantity_delta | int | Positive for receipts/returns, negative for sales |
| running_balance | int | Stock level after this movement |
| reference_id | string | order_id or po_id |

**Reconciliation rules — Inventory:**
- For each variant, `inventory_movements` quantities must sum to the current `variants.inventory_quantity`
- Every `line_items` row must produce a matching `inventory_movements` row of type `sale`
- Every received PO line must produce a matching `inventory_movements` row of type `po_receipt`
- Every refund must produce a matching `inventory_movements` row of type `return`

---

### 3.3 Advertising Data

#### `google_ads_daily`
| Field | Type | Notes |
|---|---|---|
| date | date | |
| campaign_name | string | e.g. `Brand_Search_UK`, `Shopping_Hoodies_UK`, `PMax_Womens_Launch` |
| campaign_type | enum | `search` / `shopping` / `pmax` |
| ad_group | string | |
| impressions | int | |
| clicks | int | |
| spend_gbp | decimal | |
| conversions | int | Platform-reported (will slightly overclaim vs Shopify reality) |
| conversion_value_gbp | decimal | |

#### `meta_ads_daily`
| Field | Type | Notes |
|---|---|---|
| date | date | |
| campaign_name | string | e.g. `Prospecting_Mens_UK_SS24`, `Retargeting_AllUsers`, `Womens_Launch_Prospecting` |
| campaign_objective | enum | `conversions` / `traffic` / `awareness` |
| ad_set | string | |
| ad_name | string | |
| placement | enum | `instagram_feed` / `instagram_stories` / `facebook_feed` / `reels` |
| impressions | int | |
| clicks | int | |
| spend_gbp | decimal | |
| conversions | int | |
| conversion_value_gbp | decimal | |

**Reconciliation rules — Ads:**
- Monthly sum of `google_ads_daily.spend_gbp` must equal Google's monthly bank transaction(s) for that period
- Monthly sum of `meta_ads_daily.spend_gbp` must equal Meta's monthly bank transaction(s) for that period
- For every `campaign_name` referenced in `orders.utm_campaign`, there must be a matching campaign in the ads tables
- Ads platforms should overclaim conversions by ~10-20% vs. true Shopify-attributed orders (realistic platform behaviour)

**The "discoverable opportunity" baked in here:**
- The **Womens_Launch_Prospecting** Meta campaign has high spend, decent clicks, but poor conversion vs. menswear campaigns. CAC roughly 2× menswear.
- However, customers acquired via this campaign have **above-average AOV and repeat rate** when they do convert. This is the easter egg: the segment has product-market fit, but the acquisition strategy needs work.

---

### 3.4 Email Marketing (Klaviyo-style)

#### `email_campaigns`
| Field | Type | Notes |
|---|---|---|
| campaign_id | string | |
| name | string | e.g. "SS24 Drop Announcement", "Welcome Flow Email 1", "Abandoned Cart" |
| type | enum | `campaign` (one-off) / `flow` (automated) |
| sent_at | timestamp | For campaigns; null for flows (use first_sent) |
| recipients | int | |
| opens | int | |
| clicks | int | |
| unsubscribes | int | |
| attributed_orders | int | Must equal count of orders with utm_source=klaviyo and matching utm_campaign |
| attributed_revenue_gbp | decimal | Must equal sum of those orders' total_price |

#### `email_events`
| Field | Type | Notes |
|---|---|---|
| event_id | string | |
| campaign_id | FK | |
| customer_id | FK | |
| event_type | enum | `sent` / `opened` / `clicked` / `unsubscribed` / `converted` |
| timestamp | timestamp | |

**Reconciliation rules — Email:**
- `email_campaigns.attributed_orders` and `attributed_revenue_gbp` must reconcile exactly with `orders` filtered by `utm_source='klaviyo'` and matching `utm_campaign`
- Klaviyo monthly subscription fee appears as a recurring bank transaction (~£150-400/month depending on list size growth)

**Easter egg in email data:** Women's-targeted email flows show notably higher open and click rates than men's equivalents. The audience is engaged once acquired.

---

### 3.5 Support Tickets (Fin AI-ready)

This dataset deserves particular care given Fin AI's involvement. Target: **800-1,200 tickets** over the 24-month window.

#### `support_tickets`
| Field | Type | Notes |
|---|---|---|
| ticket_id | string | |
| customer_id | FK (nullable) | Some tickets pre-account |
| created_at | timestamp | |
| channel | enum | `email` / `chat` / `instagram_dm` |
| status | enum | `open` / `pending` / `resolved` / `closed` |
| priority | enum | `low` / `normal` / `high` |
| category | enum | See distribution below |
| subject | string | |
| related_order_id | FK (nullable) | |
| related_product_id | FK (nullable) | For pre-purchase queries |
| first_response_at | timestamp | |
| resolved_at | timestamp (nullable) | |
| resolution_time_minutes | int (nullable) | |
| satisfaction_rating | int 1-5 (nullable) | ~30% of resolved tickets |
| resolved_by | enum | `bot` / `human` / `unresolved` |

**Category distribution:**
| Category | Share | Notes |
|---|---|---|
| Order status / shipping | 30% | Where is my order, tracking issues |
| Sizing & fit | 20% | Pre-purchase and returns-related — **skewed to womenswear in last 6 months** |
| Returns & exchanges | 15% | |
| Discount code issues | 10% | |
| Drop / restock questions | 10% | |
| Product quality | 10% | |
| Other / general | 5% | |

#### `support_messages`
| Field | Type | Notes |
|---|---|---|
| message_id | string | |
| ticket_id | FK | |
| sender | enum | `customer` / `agent` / `bot` |
| sender_name | string (nullable) | Agent name if applicable |
| timestamp | timestamp | |
| body | text | Realistic conversational text |

**Conversation realism:**
- Average 3-6 messages per ticket
- Realistic flow: customer message → bot triage attempt → either bot resolution or handoff to human → resolution
- Bot resolution rate ~40% currently (leaves room for Fin AI to demonstrate improvement)
- Average first-response time ~2-4 hours, resolution time 4-24 hours
- Messages should reference real `order_id`, `product_id`, and tracking numbers where relevant

**Reconciliation rules — Support:**
- Every `related_order_id` must exist in `orders`
- Every `related_product_id` must exist in `products`
- Every `customer_id` (when present) must exist in `customers`

**Easter egg in support:** Womenswear sizing tickets disproportionately high — clear "fit guidance is broken for this segment" signal.

---

### 3.6 Bank Transactions

A single flat table of all business banking activity over 24 months.

#### `bank_transactions`
| Field | Type | Notes |
|---|---|---|
| transaction_id | string | |
| date | date | |
| description | string | "Strange but identifiable" — see below |
| amount_gbp | decimal | Signed: positive for inflow, negative for outflow |
| balance_gbp | decimal | Running balance |
| counterparty | string | Cleaner name (left blank or messy — this is what taggers fix) |
| category | string | **Left blank** — this is what the tagger build would fill in |

**"Strange but identifiable" description style:**

| Type | Example description |
|---|---|
| Shopify payout | `SHOPIFY* 8829 PAYOUT REF#82910` |
| Stripe (if used) | `STRIPE PAYOUT GBP 4421` |
| Google Ads | `GOOGLE*ADS8821 CC@GOOGLE.COM` |
| Meta Ads | `FB*ADS9921XK MENLO PARK` |
| Klaviyo | `SQ *KLAVIYO INC 8889999 DUB` |
| Shopify subscription | `SHOPIFY* SUB 029184` |
| Fin / Intercom | `INTERCOM INC SF CA 7721` |
| 3PL | `HUB3PL LONDON N1 INVC2284` |
| Shipping carriers | `DHL EXPRESS IRL`, `ROYAL MAIL BUSINESS` |
| Supplier payment (PT) | `SWIFT XFER PORTO KNIT CO EUR` |
| Supplier payment (IT) | `SWIFT XFER MILANO TRIMS SRL EUR` |
| Payroll | `BACS PAYROLL 21JAN STAFF` |
| Rent | `STANDING ORDER STUDIO N1 LDN` |
| Software | `XERO LTD`, `NOTION LABS INC`, `FIGMA INC` |
| Refunds processed | `SHOPIFY REFUND BATCH 882` |
| Founder coffee, misc | `PRET A MANGER`, `WORKSHOP COFFEE` (small, infrequent) |

**Reconciliation rules — Bank (CRITICAL):**

This is where the dataset earns its keep. Every line below must reconcile to the cent:

1. **Shopify payouts:** Sum of payouts per month = (orders.total_price − refunds − Shopify fees) for orders settled that month, accounting for the realistic 2-3 day payout delay.
2. **Ad spend:** Monthly Google bank txn(s) = monthly Google spend. Same for Meta.
3. **Klaviyo:** Monthly Klaviyo bank txn = Klaviyo subscription cost.
4. **PO payments:** Every PO has a deposit transaction (typically 50%) on `deposit_paid_at` and a balance transaction on `balance_paid_at`. Sum reconciles to `purchase_orders.total_cost_gbp`.
5. **Payroll:** Monthly payroll = fixed staff base with realistic small variations.
6. **Rent, software subscriptions:** Recurring at fixed intervals.
7. **Closing cash balance** in bank = opening balance + sum of all transactions. Must equal the Cash figure on the balance sheet.

---

### 3.7 Minimum Viable Balance Sheet

Derived rather than stored, but the data must support clean derivation at any month-end:

| Item | Source |
|---|---|
| **Cash** | Running balance from `bank_transactions` |
| **Inventory** | Sum across variants of (current `inventory_quantity` × landed cost per unit) |
| **Accounts Payable** | Outstanding PO balances: POs placed where balance has not yet been paid |

Excluded: Accounts Receivable, Debt, Fixed Assets, D&A.

---

## 4. The Profit & Loss Statement

The dataset must support generation of a P&L matching this structure for any period (month / quarter / year). All lines below are derivable from the datasets specified above:

| Line Item | Source |
|---|---|
| **Gross Sales** | Sum of `orders.subtotal` (pre-discount, pre-VAT) |
| – Discounts & Returns | Sum of `orders.total_discounts` + sum of `refunds.amount` |
| **Net Sales** | Calculated |
| – Product Purchases (Landed) | COGS: for each unit sold, the landed cost per unit from associated PO. Recognised when sold, not when paid. |
| **Product Margin** | Calculated |
| – Shipping & Fulfilment | Sum of bank txns categorised as 3PL / carriers |
| – Merchant & Payment Fees | Shopify Payments fees (~1.5-2.5% of GMV) |
| – Other Cost of Sales | Packaging, returns processing |
| **Gross Profit** | Calculated |
| – Total Marketing | Google + Meta ad spend + Klaviyo subscription + any influencer line |
| **Contribution Profit** | Calculated |
| **Operating Costs** | Sum of below |
| – Salaries & Wages | Payroll bank txns |
| – Rent & Facilities | Rent bank txns |
| – Software & Subscriptions | Software bank txns (Shopify, Fin/Intercom, Xero, Figma, Notion, etc.) |
| – Other Operating Costs | Misc tagged bank txns |
| **Operating Profit** | Calculated |
| – Other Income / Expenses | FX gains/losses on EUR/USD supplier payments |
| **EBITDA** | Calculated (no D&A; no Interest/Tax for this exercise) |
|  |  |
| *Memo: Inventory Turnover (annual)* | COGS ÷ avg inventory value |
| *Memo: Days Inventory Outstanding* | 365 ÷ inventory turnover |

---

## 5. Headline Metrics — All Calculable

Participants must be able to derive each of the following from the data:

| Metric | Formula | Source |
|---|---|---|
| Revenue Growth (YoY) | Year 2 net sales / Year 1 net sales − 1 | orders |
| Gross Margin | Gross Profit / Net Sales | P&L |
| AOV | Net sales / order count | orders |
| CAC | Marketing spend / new customers acquired | ads + customers |
| LTV | Avg revenue per customer over their lifetime (or annualised) | customers + orders |
| Payback Period | CAC / (AOV × Gross Margin × Purchase Frequency) | Derived |
| Marketing Spend (% Revenue) | Total marketing / net sales | P&L |
| Purchase Frequency | Orders per customer per year | orders + customers |
| New vs Returning (% Revenue) | Compare customer first-order date vs each order date | orders + customers |
| Return Rate | Refund count / order count (or value-based) | refunds + orders |
| Cash Runway (months) | Closing cash / avg monthly net burn | bank_transactions |

*Debt / Sales dropped from original list (no debt modelled).*

---

## 6. The "Discoverable Opportunities" — Easter Eggs

These are intentional patterns layered into the data. A sophisticated participant build should be able to surface them. None should be screaming red flags; all should reward analysis.

| # | Signal | Where it shows up |
|---|---|---|
| 1 | **Womens Meta campaign has poor CAC** | High spend, decent clicks, low conversion rate on `Womens_Launch_Prospecting` in `meta_ads_daily` |
| 2 | **Womens customers have strong LTV when acquired** | Above-average AOV and repeat rate for `gender_segment_affinity = womens` in `customers` |
| 3 | **Womens sizing drives support tickets** | Disproportionate `sizing & fit` tickets linked to women's products in `support_tickets` |
| 4 | **Strong email engagement for womens flows** | Above-average open/click rates on women's-tagged email campaigns |
| 5 | **One women's product is quietly a hit** | One specific SKU outperforms wildly on sell-through rate — buried in the data |
| 6 | **Slow-moving inventory on certain women's SKUs** | DIO worse for some women's variants — Wayflyer angle: cash tied up |
| 7 | **An underperforming Google campaign** | One generic non-brand search campaign with poor ROAS |
| 8 | **A redundant SaaS subscription** | One software bank txn that's clearly waste (e.g. a duplicate analytics tool) |

The cumulative narrative: *Pretty Fly's womenswear isn't failing — it has hidden product-market fit. They're spending wrong on acquisition, struggling with fit guidance, but the segment is engaged and high-value once acquired.* A participant who surfaces this story has built something genuinely valuable.

---

## 7. Build Order & Delivery Format

### Suggested generation order
The data provider should generate datasets in this order to maintain consistency:

1. **Products + variants + suppliers**
2. **Purchase orders + PO line items** (24 months of buying, paced to drops)
3. **Ads campaigns** (Google + Meta, daily granularity)
4. **Customers + orders + line items + refunds + discount codes** (UTM-threaded, seasonally paced, drops drive spikes)
5. **Inventory movements** (reconciling PO receipts and order sales)
6. **Email campaigns + events** (Klaviyo-style, drop-timed, attribution working)
7. **Support tickets + messages** (referencing real orders/products/customers)
8. **Bank transactions** (reconciling to P&L lines)
9. **Validation pass** — every reconciliation rule above checked

### Suggested delivery format
- **CSV** for tabular data (one file per table)
- **JSON** for the support_messages table (conversational structure suits JSON better) — alternatively CSV with escaped text
- **A single ZIP** containing all files, plus a top-level `README.md` describing the schema for participants
- **A validation script** (Python or similar) that participants can run to confirm the data they receive reconciles — useful for trust

---

## 8. Open Items / Stretch

- **Shopify development store seeding (stretch).** Once flat datasets are validated, spinning up a real Shopify dev store and importing this data via the Admin API would let participants building Shopify apps/storefronts connect to a real backend. Estimated effort: 1-2 days for someone with prior Shopify API experience. Not required for hackathon to run.

---

## 9. Summary of Reconciliation Rules

For the data provider's reference, all reconciliation requirements in one place:

1. Order subtotals = sum of line items
2. Customer total_spent and orders_count = aggregations of their orders
3. Discount code usage_count = orders referencing that code
4. Every line item produces an inventory movement (`sale`)
5. Every PO receipt produces inventory movements (`po_receipt`)
6. Every refund produces inventory movement (`return`) and a refund bank txn
7. Sum of inventory movements per variant = current `variants.inventory_quantity`
8. Monthly Google ad spend = monthly Google bank transactions
9. Monthly Meta ad spend = monthly Meta bank transactions
10. UTM campaign names on orders must exist in ads or email campaign tables
11. Email campaign attributed_orders/revenue = orders with matching utm
12. Klaviyo subscription appears monthly in bank
13. PO deposits + balances in bank = `purchase_orders.total_cost_gbp`
14. Closing cash = opening cash + sum of all bank transactions
15. P&L Net Sales = sum of orders.subtotal − discounts − refunds (for period)
16. P&L COGS = sum of (units sold × landed cost) (for period)
17. Inventory on balance sheet = current inventory_quantity × landed cost
18. Accounts Payable = outstanding PO balances at month-end
19. Support ticket related_order_id / related_product_id / customer_id all exist
20. Every UTM campaign name is consistent across orders, ads, and email

---

*End of specification.*