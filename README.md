# Pretty Fly Hackathon Data

Dummy e-commerce dataset for the "Build the Future of E-commerce" hackathon,
co-hosted by Wayflyer and Fin AI.

See `spec/pretty_fly_data_pack_spec.md` for the full data specification.

## Structure
- `generate.py` — generates the dataset
- `validate.py` — verifies 20 reconciliation rules
- `sanity_report.py` — prints headline metrics for eyeball checks
- `data/sample/` — one-month sample (for verification)
- `data/full/` — full 24-month dataset

## A note on building P&Ls from this data

**COGS** is recognised when goods are sold, not when suppliers are paid. To calculate product-level COGS, join `line_items` → `po_line_items` (via `variant_id`) and multiply `quantity × landed_cost_per_unit_gbp`. Supplier payment timing in `bank_transactions` reflects cash flow, not cost recognition.

**Shopify payment processing fees** (~2% of GMV) are embedded inside payout amounts — they are not broken out as separate bank transactions. To derive them: `fees = sum(orders.total_price for batch) - payout_amount + refunds_in_batch`.

**Returns** affect both the `refunds` table (granular, per-return) and `bank_transactions` (batched as `SHOPIFY REFUND BATCH` lines). Use `refunds` for product-level return analysis; use bank for cash-flow timing.

**Quick-start P&L**: group `bank_transactions` by `raw_category` and sum `amount_gbp` for a first-pass P&L. The `raw_category` column classifies every transaction into one of: `PAYOUT`, `REFUND`, `SUPPLIER`, `MARKETING`, `SAAS`, `PAYROLL`, `RENT`, `FULFILMENT`, `SHIPPING`, `OTHER`.

**Precise P&L**: join through `orders` → `line_items` → `po_line_items` for accurate gross margin, and use `refunds` + `orders.total_discounts` for net sales. The bank-based quick P&L and the order-based precise P&L should reconcile at the total level.