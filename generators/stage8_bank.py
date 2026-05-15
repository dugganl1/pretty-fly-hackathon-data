"""
Stage 8: Bank transactions.
Must reconcile to the penny with all other datasets.
"""

from decimal import Decimal
from datetime import date, timedelta
from collections import defaultdict
from . import config


def generate(cfg, prior_data):
    rng = config.make_rng(config.SEED + 8)
    start_date, end_date = cfg["start_date"], cfg["end_date"]

    orders = prior_data["orders"]
    refunds = prior_data["refunds"]
    purchase_orders = prior_data["purchase_orders"]
    google_ads = prior_data["google_ads_daily"]
    meta_ads = prior_data["meta_ads_daily"]

    txns = []
    txn_counter = 0
    balance = config.OPENING_BANK_BALANCE

    def _add(txn_date, description, amount_gbp, counterparty=""):
        nonlocal txn_counter, balance
        txn_counter += 1
        amount = config.quantize(Decimal(str(amount_gbp)))
        balance += amount
        txns.append({
            "transaction_id": f"bt_{txn_counter:06d}",
            "date": txn_date.isoformat() if isinstance(txn_date, date) else txn_date,
            "description": description,
            "amount_gbp": str(amount),
            "balance_gbp": str(balance),
            "counterparty": counterparty,
            "category": "",
        })

    # --- 1. Shopify payouts (weekly, settle on Wednesday for prior Mon-Sun) ---
    # Group orders by settlement week
    order_by_week = defaultdict(list)
    for o in orders:
        odate = date.fromisoformat(o["created_at"][:10])
        # Find the Wednesday following the end of this order's week
        # Week ends on Sunday. Settlement = following Wednesday (2 biz days later)
        days_to_sunday = (6 - odate.weekday()) % 7
        week_end = odate + timedelta(days=days_to_sunday)
        settle_date = week_end + timedelta(days=3)  # Wednesday
        # Ensure within dataset
        if settle_date <= end_date:
            order_by_week[settle_date].append(o)

    # Group refunds by settlement week (cap to end_date)
    refund_by_week = defaultdict(list)
    for r in refunds:
        rdate = date.fromisoformat(r["created_at"][:10])
        days_to_sunday = (6 - rdate.weekday()) % 7
        week_end = rdate + timedelta(days=days_to_sunday)
        settle_date = week_end + timedelta(days=3)
        # Cap settlement to end_date so all refunds in window get a bank entry
        if settle_date > end_date:
            settle_date = end_date
        refund_by_week[settle_date].append(r)

    # Generate payout and refund batch transactions
    all_settle_dates = sorted(set(order_by_week.keys()) | set(refund_by_week.keys()))
    payout_ref = 82900
    refund_batch = 880

    for sd in all_settle_dates:
        week_orders = order_by_week.get(sd, [])
        week_refunds = refund_by_week.get(sd, [])

        if week_orders:
            gross = sum(Decimal(o["total_price"]) for o in week_orders)
            fees = config.quantize(gross * config.SHOPIFY_PAYMENT_FEE_RATE)
            payout = config.quantize(gross - fees)
            payout_ref += 1
            _add(sd,
                 f"SHOPIFY* {rng.integers(1000, 9999)} PAYOUT REF#{payout_ref}",
                 payout, "Shopify")

        if week_refunds:
            refund_total = sum(Decimal(r["amount"]) for r in week_refunds)
            refund_batch += 1
            _add(sd,
                 f"SHOPIFY REFUND BATCH {refund_batch}",
                 -refund_total, "Shopify")

    # --- 2. Google Ads (monthly, on 1st of following month) ---
    google_monthly = defaultdict(lambda: Decimal("0"))
    for row in google_ads:
        d = date.fromisoformat(row["date"])
        ym = (d.year, d.month)
        google_monthly[ym] += Decimal(row["spend_gbp"])

    for (y, m), spend in sorted(google_monthly.items()):
        # Payment on last day of spending month
        if m == 12:
            pay_date = date(y, 12, 31)
        else:
            pay_date = date(y, m + 1, 1) - timedelta(days=1)
        if pay_date <= end_date and pay_date >= start_date:
            ref = rng.integers(1000, 9999)
            _add(pay_date,
                 f"GOOGLE*ADS{ref} CC@GOOGLE.COM",
                 -spend, "Google Ads")

    # --- 3. Meta Ads (monthly, on 1st of following month) ---
    meta_monthly = defaultdict(lambda: Decimal("0"))
    for row in meta_ads:
        d = date.fromisoformat(row["date"])
        ym = (d.year, d.month)
        meta_monthly[ym] += Decimal(row["spend_gbp"])

    for (y, m), spend in sorted(meta_monthly.items()):
        if m == 12:
            pay_date = date(y, 12, 31)
        else:
            pay_date = date(y, m + 1, 1) - timedelta(days=1)
        if pay_date <= end_date and pay_date >= start_date:
            ref = rng.integers(1000, 9999)
            _add(pay_date,
                 f"FB*ADS{ref}XK MENLO PARK",
                 -spend, "Meta Ads")

    # --- 4. Supplier payments (from POs) ---
    for po in purchase_orders:
        total_gbp = Decimal(po["total_cost_gbp"])

        # Deposit (50%)
        dep_date_str = po.get("deposit_paid_at", "")
        if dep_date_str:
            dep_date = date.fromisoformat(dep_date_str)
            if dep_date >= start_date and dep_date <= end_date:
                deposit = config.quantize(total_gbp / 2)
                supplier_name = _supplier_name(po["supplier_id"], prior_data)
                _add(dep_date,
                     f"SWIFT XFER {supplier_name.upper()} "
                     f"{_supplier_ccy(po['supplier_id'], prior_data)}",
                     -deposit, supplier_name)

        # Balance (50%)
        bal_date_str = po.get("balance_paid_at", "")
        if bal_date_str:
            bal_date = date.fromisoformat(bal_date_str)
            if bal_date >= start_date and bal_date <= end_date:
                balance_amt = config.quantize(total_gbp - config.quantize(total_gbp / 2))
                supplier_name = _supplier_name(po["supplier_id"], prior_data)
                _add(bal_date,
                     f"SWIFT XFER {supplier_name.upper()} "
                     f"{_supplier_ccy(po['supplier_id'], prior_data)}",
                     -balance_amt, supplier_name)

    # --- 5. Recurring costs (monthly) ---
    for y, m in config.months_in_range(start_date, end_date):
        month_date = date(y, m, 1)

        # Payroll (25th of month)
        payroll_date = date(y, m, 25) if date(y, m, 25) <= end_date else end_date
        payroll = Decimal("18000.00")
        if y >= 2025 and m >= 6:
            payroll = Decimal("19200.00")  # Raise in Jun 2025
        # Small variation
        variation = Decimal(str(rng.uniform(-200, 200)))
        payroll = config.quantize(payroll + variation)
        _add(payroll_date,
             f"BACS PAYROLL {payroll_date.strftime('%d%b').upper()} STAFF",
             -payroll, "Payroll")

        # Klaviyo (variable based on list growth)
        months_elapsed = (y - 2024) * 12 + m - 6
        klaviyo_cost = config.quantize(
            Decimal("150") + Decimal(str(months_elapsed)) * Decimal("8.33"))
        klaviyo_cost = min(klaviyo_cost, Decimal("350"))
        ref = rng.integers(1000, 9999)
        _add(date(y, m, 5) if date(y, m, 5) <= end_date else month_date,
             f"SQ *KLAVIYO INC {ref} DUB",
             -klaviyo_cost, "Klaviyo")

        # Other recurring
        for desc_tmpl, amount in config.RECURRING_COSTS:
            if amount is None:
                continue  # Klaviyo handled above
            if "KLAVIYO" in desc_tmpl:
                continue
            ref_str = str(rng.integers(10000, 99999))
            desc = desc_tmpl.replace("{ref}", ref_str)
            pay_day = min(date(y, m, 3), end_date)
            _add(pay_day, desc, -amount, "")

        # 3PL costs (variable, based on order volume)
        month_orders = [o for o in orders
                        if o["created_at"][:7] == f"{y:04d}-{m:02d}"]
        if month_orders:
            threePL_cost = config.quantize(
                Decimal(str(len(month_orders))) * Decimal("3.50"))
            _add(date(y, m, 28) if date(y, m, 28) <= end_date else end_date,
                 f"HUB3PL LONDON N1 INVC{rng.integers(1000, 9999)}",
                 -threePL_cost, "HUB3PL")

        # Shipping carriers
        if month_orders:
            ship_cost = config.quantize(
                Decimal(str(len(month_orders))) * Decimal("6.00"))
            _add(date(y, m, 28) if date(y, m, 28) <= end_date else end_date,
                 rng.choice(["DHL EXPRESS IRL", "ROYAL MAIL BUSINESS"]),
                 -ship_cost, "Shipping")

        # Misc (coffee, small expenses)
        for _ in range(rng.integers(2, 5)):
            misc_date = date(y, m, int(rng.uniform(1, 28)))
            if misc_date > end_date:
                continue
            misc_amt = config.quantize(Decimal(str(rng.uniform(3, 12))))
            _add(misc_date,
                 rng.choice(["PRET A MANGER", "WORKSHOP COFFEE",
                             "TESCO EXPRESS", "AMAZON MARKETPLACE"]),
                 -misc_amt, "")

    # Sort all transactions by date, then by transaction_id for stability
    txns.sort(key=lambda t: (t["date"], t["transaction_id"]))

    # Recompute running balance after sort
    balance = config.OPENING_BANK_BALANCE
    for t in txns:
        balance += Decimal(t["amount_gbp"])
        t["balance_gbp"] = str(balance)

    return {
        "bank_transactions": txns,
    }


def _supplier_name(supplier_id, prior_data):
    for s in prior_data.get("suppliers", []):
        if s["supplier_id"] == supplier_id:
            return s["name"]
    return "UNKNOWN SUPPLIER"


def _supplier_ccy(supplier_id, prior_data):
    for s in prior_data.get("suppliers", []):
        if s["supplier_id"] == supplier_id:
            return s["currency"]
    return "GBP"
