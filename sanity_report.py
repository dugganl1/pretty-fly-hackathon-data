#!/usr/bin/env python3
"""
sanity_report.py — Headline metrics and weakness visibility for Pretty Fly dataset.

Not pass/fail. Prints metrics so a human can confirm the data looks right and all
eight deliberate weaknesses are baked in at the correct magnitudes.

Usage:
    python sanity_report.py data/sample/
    python sanity_report.py data/full/
"""

import sys
import csv
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from collections import defaultdict
from datetime import datetime, date

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def D(value):
    if value is None or str(value).strip() in ("", "null", "None", "NaN"):
        return Decimal("0")
    try:
        return Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _ym(date_str):
    if not date_str:
        return None
    return str(date_str)[:7]


def _load_csv(path):
    if not path.exists():
        return None
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _load_json(path):
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _pct(num, denom):
    """Safe percentage."""
    if denom == 0:
        return Decimal("0")
    return (Decimal(str(num)) / Decimal(str(denom))) * 100


def _ratio(num, denom):
    """Safe ratio."""
    if denom == 0:
        return Decimal("0")
    return Decimal(str(num)) / Decimal(str(denom))


def _fmt_gbp(val):
    """Format as GBP with commas."""
    d = D(val)
    if d >= 0:
        return f"£{d:,.2f}"
    return f"-£{abs(d):,.2f}"


def _fmt_pct(val):
    return f"{D(val):.1f}%"


def _section(title):
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print(f"{'─'*60}")


def _line(label, value, indent=4):
    pad = " " * indent
    print(f"{pad}{label:<45} {value}")


def _na():
    return "N/A — insufficient data"


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

class Data:
    """Container for all loaded data files."""
    def __init__(self, data_dir):
        d = Path(data_dir)
        self.orders = _load_csv(d / "orders.csv") or []
        self.line_items = _load_csv(d / "line_items.csv") or []
        self.customers = _load_csv(d / "customers.csv") or []
        self.refunds = _load_csv(d / "refunds.csv") or []
        self.products = _load_csv(d / "products.csv") or []
        self.variants = _load_csv(d / "variants.csv") or []
        self.po_line_items = _load_csv(d / "po_line_items.csv") or []
        self.purchase_orders = _load_csv(d / "purchase_orders.csv") or []
        self.google_ads = _load_csv(d / "google_ads_daily.csv") or []
        self.meta_ads = _load_csv(d / "meta_ads_daily.csv") or []
        self.email_campaigns = _load_csv(d / "email_campaigns.csv") or []
        self.bank_txns = _load_csv(d / "bank_transactions.csv") or []
        self.support_tickets = _load_csv(d / "support_tickets.csv") or []
        self.discount_codes = _load_csv(d / "discount_codes.csv") or []

        # Derived lookups
        self._build_lookups()

    def _build_lookups(self):
        # Product gender segment
        self.product_gender = {}
        for p in self.products:
            self.product_gender[p["product_id"]] = p.get("gender_segment", "mens")

        # Product type
        self.product_type = {}
        for p in self.products:
            self.product_type[p["product_id"]] = p.get("product_type", "unknown")

        # Variant -> product
        self.variant_product = {}
        for v in self.variants:
            self.variant_product[v["variant_id"]] = v["product_id"]

        # Landed cost per variant (latest PO)
        self.landed_cost = {}
        for pli in self.po_line_items:
            self.landed_cost[pli["variant_id"]] = D(pli["landed_cost_per_unit_gbp"])

        # Order months
        self.order_months = sorted({_ym(o["created_at"]) for o in self.orders
                                     if _ym(o["created_at"])})

        # Year boundaries (for YoY)
        if self.order_months:
            first = self.order_months[0]
            # Y1 = first 12 months, Y2 = next 12 months
            all_yms = sorted(self.order_months)
            mid_idx = min(12, len(all_yms))
            self.y1_months = set(all_yms[:mid_idx])
            self.y2_months = set(all_yms[mid_idx:])
        else:
            self.y1_months = set()
            self.y2_months = set()

    def order_gender(self, order):
        """Determine gender segment of an order from its line items."""
        genders = set()
        for li in self.line_items:
            if li["order_id"] == order["order_id"]:
                pid = self.variant_product.get(li["variant_id"], "")
                genders.add(self.product_gender.get(pid, "mens"))
        if "womens" in genders and "mens" not in genders:
            return "womens"
        if "mens" in genders and "womens" not in genders:
            return "mens"
        if genders:
            return "mixed"
        return "unknown"


# ---------------------------------------------------------------------------
# Report sections
# ---------------------------------------------------------------------------

def report_topline(data):
    _section("TOP-LINE METRICS")

    gross_sales = sum(D(o["subtotal"]) for o in data.orders)
    total_discounts = sum(D(o["total_discounts"]) for o in data.orders)
    total_refunds = sum(D(r["amount"]) for r in data.refunds)
    net_sales = gross_sales - total_discounts - total_refunds
    order_count = len(data.orders)
    unique_customers = len({o["customer_id"] for o in data.orders})
    aov = _ratio(net_sales, order_count) if order_count else Decimal("0")

    # COGS
    cogs = Decimal("0")
    for li in data.line_items:
        vid = li["variant_id"]
        cost = data.landed_cost.get(vid, Decimal("0"))
        cogs += D(li["quantity"]) * cost

    gross_profit = net_sales - cogs
    gross_margin = _pct(gross_profit, net_sales) if net_sales else Decimal("0")

    _line("Gross Sales", _fmt_gbp(gross_sales))
    _line("Discounts", _fmt_gbp(total_discounts))
    _line("Refunds", _fmt_gbp(total_refunds))
    _line("Net Sales", _fmt_gbp(net_sales))
    _line("COGS (landed)", _fmt_gbp(cogs))
    _line("Gross Profit", _fmt_gbp(gross_profit))
    _line("Gross Margin", _fmt_pct(gross_margin))
    _line("Order Count", f"{order_count:,}")
    _line("Unique Customers", f"{unique_customers:,}")
    _line("AOV (net sales / orders)", _fmt_gbp(aov))

    # GROSS MARGIN RANGE CHECK
    gm = float(gross_margin)
    if 55 <= gm <= 60:
        _line("** Gross margin range check **", f"OK ({gm:.1f}% is in 55-60%)")
    else:
        _line("** Gross margin range check **",
              f"WARNING: {gm:.1f}% outside 55-60% target")


def report_growth(data):
    _section("YEAR-OVER-YEAR GROWTH")

    if not data.y2_months:
        _line("YoY Growth", _na())
        return

    y1_rev = sum(D(o["subtotal"]) - D(o["total_discounts"])
                 for o in data.orders if _ym(o["created_at"]) in data.y1_months)
    y2_rev = sum(D(o["subtotal"]) - D(o["total_discounts"])
                 for o in data.orders if _ym(o["created_at"]) in data.y2_months)
    y1_refunds = sum(D(r["amount"]) for r in data.refunds
                     if _ym(r["created_at"]) in data.y1_months)
    y2_refunds = sum(D(r["amount"]) for r in data.refunds
                     if _ym(r["created_at"]) in data.y2_months)

    y1_net = y1_rev - y1_refunds
    y2_net = y2_rev - y2_refunds
    growth = _pct(y2_net - y1_net, y1_net) if y1_net else Decimal("0")

    _line("Y1 Net Sales", _fmt_gbp(y1_net))
    _line("Y2 Net Sales", _fmt_gbp(y2_net))
    _line("YoY Growth", _fmt_pct(growth))


def report_channel_mix(data):
    _section("CHANNEL MIX")

    # Revenue by UTM source
    rev_by_source = defaultdict(lambda: Decimal("0"))
    for o in data.orders:
        src = (o.get("utm_source") or "direct").strip() or "direct"
        rev_by_source[src] += D(o["total_price"])

    total_rev = sum(rev_by_source.values())
    print("    Revenue by UTM source:")
    for src in sorted(rev_by_source, key=lambda s: rev_by_source[s], reverse=True):
        share = _pct(rev_by_source[src], total_rev)
        _line(f"  {src}", f"{_fmt_gbp(rev_by_source[src])} ({_fmt_pct(share)})",
              indent=4)

    # Ad spend by channel
    google_spend = sum(D(r["spend_gbp"]) for r in data.google_ads)
    meta_spend = sum(D(r["spend_gbp"]) for r in data.meta_ads)
    total_ad_spend = google_spend + meta_spend

    # Klaviyo cost (from bank)
    klaviyo_spend = Decimal("0")
    for bt in data.bank_txns:
        if "KLAVIYO" in bt.get("description", "").upper():
            klaviyo_spend += abs(D(bt["amount_gbp"]))

    total_marketing = total_ad_spend + klaviyo_spend

    print("\n    Ad spend by channel:")
    _line("  Google Ads", _fmt_gbp(google_spend))
    _line("  Meta Ads", _fmt_gbp(meta_spend))
    _line("  Klaviyo (from bank)", _fmt_gbp(klaviyo_spend))
    _line("  Total Marketing", _fmt_gbp(total_marketing))

    net_sales = sum(D(o["subtotal"]) - D(o["total_discounts"]) for o in data.orders)
    net_sales -= sum(D(r["amount"]) for r in data.refunds)
    if net_sales > 0:
        mkt_pct = _pct(total_marketing, net_sales)
        _line("  Marketing % of Net Sales", _fmt_pct(mkt_pct))

    # Blended CAC
    new_customers = len({o["customer_id"] for o in data.orders})  # approximation
    if new_customers > 0:
        cac = _ratio(total_marketing, new_customers)
        _line("  Blended CAC (approx)", _fmt_gbp(cac))


def report_product_mix(data):
    _section("PRODUCT MIX")

    # Units by product
    units_by_product = defaultdict(int)
    rev_by_product = defaultdict(lambda: Decimal("0"))
    for li in data.line_items:
        pid = data.variant_product.get(li["variant_id"], li.get("product_id", "?"))
        qty = int(D(li["quantity"]))
        units_by_product[pid] += qty
        rev_by_product[pid] += D(li["price"]) * D(li["quantity"])

    # Product title lookup
    titles = {p["product_id"]: p.get("title", p["product_id"]) for p in data.products}

    print("    Top 10 products by units:")
    sorted_prods = sorted(units_by_product.items(), key=lambda x: x[1], reverse=True)
    for pid, units in sorted_prods[:10]:
        title = titles.get(pid, pid)
        rev = rev_by_product[pid]
        _line(f"  {title[:35]}", f"{units:>5} units, {_fmt_gbp(rev)}")

    # Menswear vs Womenswear
    rev_by_gender = defaultdict(lambda: Decimal("0"))
    units_by_gender = defaultdict(int)
    for li in data.line_items:
        pid = data.variant_product.get(li["variant_id"], li.get("product_id", ""))
        gender = data.product_gender.get(pid, "mens")
        rev_by_gender[gender] += D(li["price"]) * D(li["quantity"])
        units_by_gender[gender] += int(D(li["quantity"]))

    print("\n    Revenue by gender segment:")
    total_rev = sum(rev_by_gender.values())
    for g in sorted(rev_by_gender):
        share = _pct(rev_by_gender[g], total_rev)
        _line(f"  {g}", f"{_fmt_gbp(rev_by_gender[g])} ({_fmt_pct(share)}), "
              f"{units_by_gender[g]:,} units")


def report_category_margins(data):
    _section("CATEGORY MARGINS (Weakness #5: caps & sweatpants)")

    # Revenue and COGS by product_type
    rev_by_type = defaultdict(lambda: Decimal("0"))
    cogs_by_type = defaultdict(lambda: Decimal("0"))
    for li in data.line_items:
        vid = li["variant_id"]
        pid = data.variant_product.get(vid, li.get("product_id", ""))
        ptype = data.product_type.get(pid, "unknown")
        rev = D(li["price"]) * D(li["quantity"])
        cost = data.landed_cost.get(vid, Decimal("0")) * D(li["quantity"])
        rev_by_type[ptype] += rev
        cogs_by_type[ptype] += cost

    print(f"    {'Category':<20} {'Revenue':>12} {'COGS':>12} {'Margin':>8}")
    print(f"    {'─'*52}")
    for ptype in sorted(rev_by_type):
        rev = rev_by_type[ptype]
        cogs = cogs_by_type[ptype]
        margin = _pct(rev - cogs, rev) if rev > 0 else Decimal("0")
        flag = " ◄" if ptype.lower() in ("cap", "caps", "sweatpants") else ""
        _line(f"{ptype:<20}", f"{_fmt_gbp(rev):>12} {_fmt_gbp(cogs):>12} "
              f"{_fmt_pct(margin):>7}{flag}")


def report_returns(data):
    _section("RETURNS (Weakness #3: trainers)")

    if not data.orders:
        _line("Return rate", _na())
        return

    total_orders = len(data.orders)
    total_refunds = len(data.refunds)
    overall_rate = _pct(total_refunds, total_orders)

    _line("Total orders", f"{total_orders:,}")
    _line("Total refunds", f"{total_refunds:,}")
    _line("Overall return rate", _fmt_pct(overall_rate))

    # Return rate by product type
    # Build order -> product types mapping via line items
    order_types = defaultdict(set)
    for li in data.line_items:
        pid = data.variant_product.get(li["variant_id"], li.get("product_id", ""))
        ptype = data.product_type.get(pid, "unknown")
        order_types[li["order_id"]].add(ptype)

    orders_by_type = defaultdict(int)
    for oid, types in order_types.items():
        for t in types:
            orders_by_type[t] += 1

    refund_by_type = defaultdict(int)
    for r in data.refunds:
        oid = r["order_id"]
        for t in order_types.get(oid, {"unknown"}):
            refund_by_type[t] += 1

    print("\n    Return rate by product type:")
    for ptype in sorted(orders_by_type):
        rate = _pct(refund_by_type.get(ptype, 0), orders_by_type[ptype])
        flag = " ◄" if "trainer" in ptype.lower() else ""
        _line(f"  {ptype}",
              f"{refund_by_type.get(ptype, 0)}/{orders_by_type[ptype]} "
              f"({_fmt_pct(rate)}){flag}")

    # By gender segment
    orders_by_gender = defaultdict(int)
    refunds_by_gender = defaultdict(int)
    order_gender_cache = {}
    for o in data.orders:
        # Determine gender from line items
        genders = set()
        for li in data.line_items:
            if li["order_id"] == o["order_id"]:
                pid = data.variant_product.get(li["variant_id"], "")
                genders.add(data.product_gender.get(pid, "mens"))
        g = "womens" if "womens" in genders else "mens"
        orders_by_gender[g] += 1
        order_gender_cache[o["order_id"]] = g

    for r in data.refunds:
        g = order_gender_cache.get(r["order_id"], "mens")
        refunds_by_gender[g] += 1

    print("\n    Return rate by gender:")
    for g in sorted(orders_by_gender):
        rate = _pct(refunds_by_gender.get(g, 0), orders_by_gender[g])
        _line(f"  {g}",
              f"{refunds_by_gender.get(g, 0)}/{orders_by_gender[g]} "
              f"({_fmt_pct(rate)})")


def report_discounting(data):
    _section("DISCOUNTING (Weakness #4: margin destruction)")

    if not data.orders:
        _line("Discount usage", _na())
        return

    discounted = [o for o in data.orders
                  if (o.get("discount_code") or "").strip()]
    non_discounted = [o for o in data.orders
                      if not (o.get("discount_code") or "").strip()]

    disc_rate = _pct(len(discounted), len(data.orders))
    _line("Discount usage rate", f"{len(discounted)}/{len(data.orders)} "
          f"({_fmt_pct(disc_rate)})")

    if discounted:
        disc_aov = _ratio(sum(D(o["total_price"]) for o in discounted),
                          len(discounted))
        _line("AOV (discounted orders)", _fmt_gbp(disc_aov))
    if non_discounted:
        non_disc_aov = _ratio(sum(D(o["total_price"]) for o in non_discounted),
                              len(non_discounted))
        _line("AOV (non-discounted orders)", _fmt_gbp(non_disc_aov))

    # Contribution per discount code
    # Build order -> line items for COGS
    order_li = defaultdict(list)
    for li in data.line_items:
        order_li[li["order_id"]].append(li)

    FULFILMENT_COST = Decimal("9.50")  # 3PL + shipping estimate

    print("\n    Per-code contribution analysis:")
    print(f"    {'Code':<20} {'Orders':>7} {'Avg Revenue':>12} "
          f"{'Avg COGS':>10} {'Avg Contrib':>12}")
    print(f"    {'─'*65}")

    code_stats = defaultdict(lambda: {"count": 0, "rev": Decimal("0"),
                                       "cogs": Decimal("0")})
    for o in discounted:
        code = (o.get("discount_code") or "").strip()
        if not code:
            continue
        rev = D(o["total_price"])
        cogs = Decimal("0")
        for li in order_li.get(o["order_id"], []):
            vid = li["variant_id"]
            cogs += data.landed_cost.get(vid, Decimal("0")) * D(li["quantity"])
        code_stats[code]["count"] += 1
        code_stats[code]["rev"] += rev
        code_stats[code]["cogs"] += cogs

    for code in sorted(code_stats):
        s = code_stats[code]
        n = s["count"]
        avg_rev = _ratio(s["rev"], n)
        avg_cogs = _ratio(s["cogs"], n)
        avg_contrib = avg_rev - avg_cogs - FULFILMENT_COST
        flag = " ◄ NEGATIVE" if avg_contrib < 0 else ""
        _line(f"{code:<20}",
              f"{n:>7} {_fmt_gbp(avg_rev):>12} {_fmt_gbp(avg_cogs):>10} "
              f"{_fmt_gbp(avg_contrib):>12}{flag}")


def report_support(data):
    _section("SUPPORT (Weakness #7: womens sizing)")

    if not data.support_tickets:
        _line("Support stats", _na())
        return

    total = len(data.support_tickets)
    bot_resolved = sum(1 for t in data.support_tickets
                       if t.get("resolved_by") == "bot")
    human_resolved = sum(1 for t in data.support_tickets
                         if t.get("resolved_by") == "human")

    _line("Total tickets", f"{total:,}")
    _line("Bot-resolved", f"{bot_resolved:,} ({_fmt_pct(_pct(bot_resolved, total))})")
    _line("Human-resolved",
          f"{human_resolved:,} ({_fmt_pct(_pct(human_resolved, total))})")

    # Category breakdown
    by_cat = defaultdict(int)
    for t in data.support_tickets:
        by_cat[t.get("category", "unknown")] += 1

    print("\n    Category breakdown:")
    for cat in sorted(by_cat, key=lambda c: by_cat[c], reverse=True):
        share = _pct(by_cat[cat], total)
        _line(f"  {cat}", f"{by_cat[cat]:,} ({_fmt_pct(share)})")

    # Sizing tickets by gender (via related_product_id)
    mens_tickets = 0
    mens_sizing = 0
    womens_tickets = 0
    womens_sizing = 0
    for t in data.support_tickets:
        rpid = (t.get("related_product_id") or "").strip()
        gender = data.product_gender.get(rpid, None)
        if gender is None:
            # Try to infer from related_order_id
            roid = (t.get("related_order_id") or "").strip()
            if roid:
                for li in data.line_items:
                    if li["order_id"] == roid:
                        pid = data.variant_product.get(li["variant_id"], "")
                        gender = data.product_gender.get(pid, "mens")
                        break
        if gender == "womens":
            womens_tickets += 1
            if t.get("category", "").lower() in ("sizing_fit", "sizing & fit",
                                                   "sizing_and_fit"):
                womens_sizing += 1
        elif gender == "mens":
            mens_tickets += 1
            if t.get("category", "").lower() in ("sizing_fit", "sizing & fit",
                                                   "sizing_and_fit"):
                mens_sizing += 1

    print("\n    Sizing tickets by gender:")
    if mens_tickets:
        _line("  Mens sizing %",
              f"{mens_sizing}/{mens_tickets} "
              f"({_fmt_pct(_pct(mens_sizing, mens_tickets))})")
    if womens_tickets:
        _line("  Womens sizing %",
              f"{womens_sizing}/{womens_tickets} "
              f"({_fmt_pct(_pct(womens_sizing, womens_tickets))}) ◄")


def report_cash(data):
    _section("CASH POSITION")

    if not data.bank_txns:
        _line("Cash", _na())
        return

    opening = D(data.bank_txns[0]["balance_gbp"]) - D(data.bank_txns[0]["amount_gbp"])
    closing = D(data.bank_txns[-1]["balance_gbp"])

    _line("Opening balance", _fmt_gbp(opening))
    _line("Closing balance", _fmt_gbp(closing))

    # Monthly net burn (last 6 months if available)
    monthly_flows = defaultdict(lambda: Decimal("0"))
    for bt in data.bank_txns:
        monthly_flows[_ym(bt["date"])] += D(bt["amount_gbp"])

    months = sorted(monthly_flows.keys())
    if len(months) >= 3:
        recent = months[-min(6, len(months)):]
        avg_flow = sum(monthly_flows[m] for m in recent) / len(recent)
        _line("Avg monthly net flow (recent)", _fmt_gbp(avg_flow))
        if avg_flow < 0:
            runway = closing / abs(avg_flow)
            _line("Estimated runway (months)", f"{runway:.1f}")
        else:
            _line("Estimated runway", "N/A — net positive cash flow")


def report_inventory_health(data):
    _section("INVENTORY HEALTH (Weakness #8: slow-moving womens SKUs)")

    if not data.variants or not data.line_items:
        _line("Inventory", _na())
        return

    # Compute date range from orders
    order_dates = [o["created_at"][:10] for o in data.orders if o.get("created_at")]
    if not order_dates:
        _line("Inventory", _na())
        return
    first_date = min(order_dates)
    last_date = max(order_dates)
    try:
        d0 = datetime.strptime(first_date, "%Y-%m-%d").date()
        d1 = datetime.strptime(last_date, "%Y-%m-%d").date()
        total_days = max((d1 - d0).days, 1)
    except ValueError:
        total_days = 730  # fallback

    # Units sold per variant
    sold = defaultdict(int)
    for li in data.line_items:
        sold[li["variant_id"]] += int(D(li["quantity"]))

    # Variant title lookup
    var_titles = {}
    for v in data.variants:
        parts = [v.get("option1_value", ""), v.get("option2_value", "")]
        title = v.get("sku", v["variant_id"])
        var_titles[v["variant_id"]] = title

    # Product title lookup
    prod_titles = {p["product_id"]: p.get("title", "") for p in data.products}

    # Compute DIO per variant (only for those with stock)
    portfolio_cogs = Decimal("0")
    portfolio_inv = Decimal("0")
    high_dio = []  # variants with DIO > 180

    for v in data.variants:
        vid = v["variant_id"]
        qty = int(D(v["inventory_quantity"]))
        cost = data.landed_cost.get(vid, Decimal("0"))
        pid = data.variant_product.get(vid, "")
        units_sold = sold.get(vid, 0)

        inv_value = Decimal(str(qty)) * cost
        portfolio_inv += inv_value
        portfolio_cogs += Decimal(str(units_sold)) * cost

        if qty > 0 and units_sold > 0:
            dio = qty * total_days / units_sold
        elif qty > 0:
            dio = float("inf")
        else:
            continue

        if dio > 180:
            ptitle = prod_titles.get(pid, "")
            sku = v.get("sku", vid)
            high_dio.append((dio, sku, ptitle, qty, units_sold, inv_value))

    # Portfolio average DIO
    if portfolio_cogs > 0:
        daily_cogs = portfolio_cogs / total_days
        portfolio_dio = float(portfolio_inv / daily_cogs)
    else:
        portfolio_dio = 0

    _line("Total inventory value", _fmt_gbp(portfolio_inv))
    _line("Portfolio average DIO", f"{portfolio_dio:.0f} days")

    if high_dio:
        high_dio.sort(key=lambda x: -x[0])
        print(f"\n    Variants with DIO > 180 days ({len(high_dio)} found):")
        for dio, sku, ptitle, qty, sold_qty, inv_val in high_dio[:10]:
            dio_str = f"{dio:.0f}" if dio != float("inf") else "INF"
            _line(f"  {sku[:30]}",
                  f"DIO={dio_str}, stock={qty}, sold={sold_qty}, "
                  f"value={_fmt_gbp(inv_val)} ◄")
    else:
        _line("Variants with DIO > 180", "None found")


# ---------------------------------------------------------------------------
# Weakness dashboard
# ---------------------------------------------------------------------------

def report_weakness_dashboard(data):
    _section("WEAKNESS DASHBOARD — 8 Deliberate Signals")

    _weakness_1(data)
    _weakness_2(data)
    _weakness_3(data)
    _weakness_4(data)
    _weakness_5(data)
    _weakness_6(data)
    _weakness_7(data)
    _weakness_8(data)


def _weakness_1(data):
    print("\n  #1: Womens Meta CAC + hidden LTV")
    print("  " + "─" * 40)

    # Meta spend by campaign type
    mens_meta_spend = Decimal("0")
    womens_meta_spend = Decimal("0")
    for r in data.meta_ads:
        name = r["campaign_name"].lower()
        spend = D(r["spend_gbp"])
        if "womens" in name or "women" in name:
            womens_meta_spend += spend
        else:
            mens_meta_spend += spend

    # Customers acquired via Meta, split by gender
    meta_orders = [o for o in data.orders
                   if (o.get("utm_source") or "").lower() in ("facebook", "instagram",
                                                                "meta")]
    # First orders only (new customers)
    first_order_dates = {}
    for o in data.orders:
        cid = o["customer_id"]
        odate = o["created_at"]
        if cid not in first_order_dates or odate < first_order_dates[cid]:
            first_order_dates[cid] = odate

    # Build order -> gender cache
    order_genders = {}
    li_by_order = defaultdict(list)
    for li in data.line_items:
        li_by_order[li["order_id"]].append(li)

    for o in data.orders:
        genders = set()
        for li in li_by_order.get(o["order_id"], []):
            pid = data.variant_product.get(li["variant_id"], "")
            genders.add(data.product_gender.get(pid, "mens"))
        if "womens" in genders and "mens" not in genders:
            order_genders[o["order_id"]] = "womens"
        else:
            order_genders[o["order_id"]] = "mens"

    # New customers via Meta by gender
    new_meta_mens = set()
    new_meta_womens = set()
    for o in meta_orders:
        cid = o["customer_id"]
        if o["created_at"] == first_order_dates.get(cid):
            g = order_genders.get(o["order_id"], "mens")
            if g == "womens":
                new_meta_womens.add(cid)
            else:
                new_meta_mens.add(cid)

    mens_cac = (_ratio(mens_meta_spend, len(new_meta_mens))
                if new_meta_mens else Decimal("0"))
    womens_cac = (_ratio(womens_meta_spend, len(new_meta_womens))
                  if new_meta_womens else Decimal("0"))

    _line("  Mens Meta spend", _fmt_gbp(mens_meta_spend), indent=2)
    _line("  Mens new customers via Meta", f"{len(new_meta_mens):,}", indent=2)
    _line("  Mens Meta CAC", _fmt_gbp(mens_cac), indent=2)
    _line("  Womens Meta spend", _fmt_gbp(womens_meta_spend), indent=2)
    _line("  Womens new customers via Meta", f"{len(new_meta_womens):,}", indent=2)
    _line("  Womens Meta CAC", _fmt_gbp(womens_cac), indent=2)

    # 120-day repeat rate by gender for Meta-acquired customers
    # Count customers who made a 2nd purchase within 120 days
    customer_orders = defaultdict(list)
    for o in data.orders:
        customer_orders[o["customer_id"]].append(o["created_at"])

    def _repeat_120(customer_set):
        repeaters = 0
        for cid in customer_set:
            dates = sorted(customer_orders.get(cid, []))
            if len(dates) >= 2:
                try:
                    d0 = datetime.strptime(dates[0][:10], "%Y-%m-%d")
                    d1 = datetime.strptime(dates[1][:10], "%Y-%m-%d")
                    if (d1 - d0).days <= 120:
                        repeaters += 1
                except ValueError:
                    pass
        return repeaters

    mens_repeat = _repeat_120(new_meta_mens)
    womens_repeat = _repeat_120(new_meta_womens)
    mens_rr = _pct(mens_repeat, len(new_meta_mens)) if new_meta_mens else Decimal("0")
    womens_rr = (_pct(womens_repeat, len(new_meta_womens))
                 if new_meta_womens else Decimal("0"))

    _line("  Mens 120-day repeat rate", _fmt_pct(mens_rr), indent=2)
    _line("  Womens 120-day repeat rate", f"{_fmt_pct(womens_rr)} ◄", indent=2)
    _line("  Womens cohort size", f"{len(new_meta_womens):,}", indent=2)

    # AOV comparison
    mens_cust_orders = [o for o in data.orders
                        if o["customer_id"] in new_meta_mens]
    womens_cust_orders = [o for o in data.orders
                          if o["customer_id"] in new_meta_womens]
    mens_aov = (_ratio(sum(D(o["total_price"]) for o in mens_cust_orders),
                       len(mens_cust_orders)) if mens_cust_orders else Decimal("0"))
    womens_aov = (_ratio(sum(D(o["total_price"]) for o in womens_cust_orders),
                         len(womens_cust_orders))
                  if womens_cust_orders else Decimal("0"))

    _line("  Mens AOV (Meta-acquired)", _fmt_gbp(mens_aov), indent=2)
    _line("  Womens AOV (Meta-acquired)", _fmt_gbp(womens_aov), indent=2)


def _weakness_2(data):
    print("\n  #2: Bleeding Google non-brand campaign")
    print("  " + "─" * 40)

    # ROAS by Google campaign
    camp_spend = defaultdict(lambda: Decimal("0"))
    camp_conv_val = defaultdict(lambda: Decimal("0"))
    for r in data.google_ads:
        name = r["campaign_name"]
        camp_spend[name] += D(r["spend_gbp"])
        camp_conv_val[name] += D(r["conversion_value_gbp"])

    print(f"    {'Campaign':<35} {'Spend':>10} {'Conv Val':>10} {'ROAS':>6}")
    print(f"    {'─'*65}")
    for name in sorted(camp_spend, key=lambda n: camp_spend[n], reverse=True):
        spend = camp_spend[name]
        conv = camp_conv_val[name]
        roas = float(_ratio(conv, spend)) if spend else 0
        flag = " ◄" if roas < 1.5 and spend > Decimal("1000") else ""
        _line(f"{name[:35]}", f"{_fmt_gbp(spend):>10} {_fmt_gbp(conv):>10} "
              f"{roas:>5.1f}×{flag}")


def _weakness_3(data):
    print("\n  #3: Trainer return rate")
    print("  " + "─" * 40)
    # Already covered in report_returns, just show the summary
    order_types = defaultdict(set)
    for li in data.line_items:
        pid = data.variant_product.get(li["variant_id"], li.get("product_id", ""))
        ptype = data.product_type.get(pid, "unknown")
        order_types[li["order_id"]].add(ptype)

    refund_orders = {r["order_id"] for r in data.refunds}
    for ptype in sorted({t for types in order_types.values() for t in types}):
        type_orders = {oid for oid, types in order_types.items() if ptype in types}
        type_refunds = type_orders & refund_orders
        rate = _pct(len(type_refunds), len(type_orders)) if type_orders else Decimal("0")
        flag = " ◄" if "trainer" in ptype.lower() else ""
        _line(f"  {ptype}", f"{_fmt_pct(rate)} return rate{flag}", indent=2)


def _weakness_4(data):
    print("\n  #4: Discounting destroys margin")
    print("  " + "─" * 40)
    # Summary: already covered in report_discounting
    discounted = [o for o in data.orders
                  if (o.get("discount_code") or "").strip()]
    non_discounted = [o for o in data.orders
                      if not (o.get("discount_code") or "").strip()]

    if discounted and non_discounted:
        disc_items = Decimal("0")
        for o in discounted:
            for li in data.line_items:
                if li["order_id"] == o["order_id"]:
                    disc_items += D(li["quantity"])
        non_disc_items = Decimal("0")
        for o in non_discounted:
            for li in data.line_items:
                if li["order_id"] == o["order_id"]:
                    non_disc_items += D(li["quantity"])

        avg_disc_basket = _ratio(disc_items, len(discounted))
        avg_non_basket = _ratio(non_disc_items, len(non_discounted))
        _line("  Avg items (discounted)", f"{avg_disc_basket:.2f}", indent=2)
        _line("  Avg items (non-discounted)", f"{avg_non_basket:.2f}", indent=2)
        _line("  Signal", "Discounted baskets smaller ◄" if avg_disc_basket <
              avg_non_basket else "Baskets similar (check magnitudes)", indent=2)


def _weakness_5(data):
    print("\n  #5: Margin compression (caps & sweatpants)")
    print("  " + "─" * 40)
    # Already covered in report_category_margins, just summary
    rev_by_type = defaultdict(lambda: Decimal("0"))
    cogs_by_type = defaultdict(lambda: Decimal("0"))
    for li in data.line_items:
        vid = li["variant_id"]
        pid = data.variant_product.get(vid, "")
        ptype = data.product_type.get(pid, "unknown")
        rev_by_type[ptype] += D(li["price"]) * D(li["quantity"])
        cogs_by_type[ptype] += data.landed_cost.get(vid, Decimal("0")) * D(
            li["quantity"])

    for ptype in sorted(rev_by_type):
        rev = rev_by_type[ptype]
        cogs = cogs_by_type[ptype]
        margin = _pct(rev - cogs, rev) if rev > 0 else Decimal("0")
        flag = " ◄" if ptype.lower() in ("cap", "caps", "sweatpants") else ""
        _line(f"  {ptype}", f"{_fmt_pct(margin)} margin{flag}", indent=2)


def _weakness_6(data):
    print("\n  #6: Dead-weight SaaS (Mixview Analytics)")
    print("  " + "─" * 40)

    mixview_total = Decimal("0")
    mixview_months = set()
    for bt in data.bank_txns:
        desc = bt.get("description", "").upper()
        if "MIXVIEW" in desc:
            mixview_total += abs(D(bt["amount_gbp"]))
            mixview_months.add(_ym(bt["date"]))

    if mixview_total > 0:
        _line("  Mixview total spend", _fmt_gbp(mixview_total), indent=2)
        _line("  Months active", f"{len(mixview_months)}", indent=2)
        avg_monthly = _ratio(mixview_total, len(mixview_months))
        _line("  Avg monthly cost", f"{_fmt_gbp(avg_monthly)} ◄", indent=2)
    else:
        _line("  Mixview transactions", "None found (check generation)", indent=2)


def _weakness_7(data):
    print("\n  #7: Womens sizing support tickets")
    print("  " + "─" * 40)
    # Already computed in report_support, just summary here
    mens_tickets = 0
    mens_sizing = 0
    womens_tickets = 0
    womens_sizing = 0

    li_by_order = defaultdict(list)
    for li in data.line_items:
        li_by_order[li["order_id"]].append(li)

    for t in data.support_tickets:
        rpid = (t.get("related_product_id") or "").strip()
        gender = data.product_gender.get(rpid, None)
        if gender is None:
            roid = (t.get("related_order_id") or "").strip()
            if roid:
                for li in li_by_order.get(roid, []):
                    pid = data.variant_product.get(li["variant_id"], "")
                    gender = data.product_gender.get(pid, "mens")
                    break
        if gender == "womens":
            womens_tickets += 1
            if t.get("category", "").lower() in ("sizing_fit", "sizing & fit",
                                                   "sizing_and_fit"):
                womens_sizing += 1
        elif gender == "mens":
            mens_tickets += 1
            if t.get("category", "").lower() in ("sizing_fit", "sizing & fit",
                                                   "sizing_and_fit"):
                mens_sizing += 1

    m_pct = _pct(mens_sizing, mens_tickets) if mens_tickets else Decimal("0")
    w_pct = _pct(womens_sizing, womens_tickets) if womens_tickets else Decimal("0")
    _line("  Mens sizing ticket %", _fmt_pct(m_pct), indent=2)
    _line("  Womens sizing ticket %", f"{_fmt_pct(w_pct)} ◄", indent=2)
    _line("  Target: ~31% womens vs ~12% mens", "", indent=2)


def _weakness_8(data):
    print("\n  #8: Slow-moving womens inventory")
    print("  " + "─" * 40)

    # Same DIO logic as report_inventory_health but focused on womens
    order_dates = [o["created_at"][:10] for o in data.orders if o.get("created_at")]
    if not order_dates:
        _line("  DIO", _na(), indent=2)
        return

    first_date = min(order_dates)
    last_date = max(order_dates)
    try:
        d0 = datetime.strptime(first_date, "%Y-%m-%d").date()
        d1 = datetime.strptime(last_date, "%Y-%m-%d").date()
        total_days = max((d1 - d0).days, 1)
    except ValueError:
        total_days = 730

    sold = defaultdict(int)
    for li in data.line_items:
        sold[li["variant_id"]] += int(D(li["quantity"]))

    prod_titles = {p["product_id"]: p.get("title", "") for p in data.products}
    womens_high_dio = []

    for v in data.variants:
        vid = v["variant_id"]
        pid = data.variant_product.get(vid, "")
        if data.product_gender.get(pid) != "womens":
            continue
        qty = int(D(v["inventory_quantity"]))
        cost = data.landed_cost.get(vid, Decimal("0"))
        units_sold = sold.get(vid, 0)
        if qty <= 0:
            continue
        dio = qty * total_days / units_sold if units_sold > 0 else float("inf")
        if dio > 180:
            sku = v.get("sku", vid)
            ptitle = prod_titles.get(pid, "")
            inv_val = Decimal(str(qty)) * cost
            womens_high_dio.append((dio, sku, ptitle, qty, units_sold, inv_val))

    if womens_high_dio:
        womens_high_dio.sort(key=lambda x: -x[0])
        total_tied = sum(x[5] for x in womens_high_dio)
        _line("  Womens SKUs with DIO > 180",
              f"{len(womens_high_dio)} found ◄", indent=2)
        _line("  Cash tied up in dead stock", _fmt_gbp(total_tied), indent=2)
        for dio, sku, ptitle, qty, sold_qty, inv_val in womens_high_dio[:5]:
            dio_str = f"{dio:.0f}" if dio != float("inf") else "INF"
            _line(f"    {sku[:30]}",
                  f"DIO={dio_str}, stock={qty}, sold={sold_qty}", indent=2)
    else:
        _line("  Womens high-DIO SKUs", "None found (check generation)", indent=2)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print("Usage: python sanity_report.py <data_directory>")
        print("  e.g. python sanity_report.py data/sample/")
        sys.exit(1)

    data_dir = Path(sys.argv[1])
    if not data_dir.is_dir():
        print(f"Error: {data_dir} is not a directory")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"  Pretty Fly Sanity Report — {data_dir}")
    print(f"{'='*60}")

    data = Data(data_dir)

    if not data.orders:
        print("\n  No orders found. Cannot produce report.")
        sys.exit(0)

    report_topline(data)
    report_growth(data)
    report_channel_mix(data)
    report_product_mix(data)
    report_category_margins(data)
    report_returns(data)
    report_discounting(data)
    report_support(data)
    report_cash(data)
    report_inventory_health(data)
    report_weakness_dashboard(data)

    print(f"\n{'='*60}")
    print(f"  End of report")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
