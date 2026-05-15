"""
Stage 8: Bank transactions.
Must reconcile to the penny with all other datasets.
Every row has: counterparty (clean entity name), raw_category (coarse P&L bucket).
category is left blank (for tagger builds to fill).
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

    def _add(txn_date, description, amount_gbp, counterparty, raw_category):
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
            "raw_category": raw_category,
        })

    # --- 1. Shopify payouts (weekly, settle Wednesday for prior Mon-Sun) ---
    order_by_week = defaultdict(list)
    for o in orders:
        odate = date.fromisoformat(o["created_at"][:10])
        days_to_sunday = (6 - odate.weekday()) % 7
        week_end = odate + timedelta(days=days_to_sunday)
        settle_date = week_end + timedelta(days=3)
        if settle_date > end_date:
            settle_date = end_date
        order_by_week[settle_date].append(o)

    refund_by_week = defaultdict(list)
    for r in refunds:
        rdate = date.fromisoformat(r["created_at"][:10])
        days_to_sunday = (6 - rdate.weekday()) % 7
        week_end = rdate + timedelta(days=days_to_sunday)
        settle_date = week_end + timedelta(days=3)
        if settle_date > end_date:
            settle_date = end_date
        refund_by_week[settle_date].append(r)

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
                 payout, "Shopify", "PAYOUT")

        if week_refunds:
            refund_total = sum(Decimal(r["amount"]) for r in week_refunds)
            refund_batch += 1
            _add(sd,
                 f"SHOPIFY REFUND BATCH {refund_batch}",
                 -refund_total, "Shopify", "REFUND")

    # --- 2. Google Ads (monthly, last day of spending month) ---
    google_monthly = defaultdict(lambda: Decimal("0"))
    for row in google_ads:
        d = date.fromisoformat(row["date"])
        ym = (d.year, d.month)
        google_monthly[ym] += Decimal(row["spend_gbp"])

    for (y, m), spend in sorted(google_monthly.items()):
        if m == 12:
            pay_date = date(y, 12, 31)
        else:
            pay_date = date(y, m + 1, 1) - timedelta(days=1)
        if start_date <= pay_date <= end_date:
            ref = rng.integers(1000, 9999)
            _add(pay_date,
                 f"GOOGLE*ADS{ref} CC@GOOGLE.COM",
                 -spend, "Google", "MARKETING")

    # --- 3. Meta Ads (monthly, last day of spending month) ---
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
        if start_date <= pay_date <= end_date:
            ref = rng.integers(1000, 9999)
            _add(pay_date,
                 f"FB*ADS{ref}XK MENLO PARK",
                 -spend, "Meta", "MARKETING")

    # --- 4. Supplier payments (from POs — deposit + balance) ---
    for po in purchase_orders:
        total_gbp = Decimal(po["total_cost_gbp"])
        supplier_name = _supplier_name(po["supplier_id"], prior_data)
        supplier_ccy = _supplier_ccy(po["supplier_id"], prior_data)

        dep_str = (po.get("deposit_paid_at") or "").strip()
        bal_str = (po.get("balance_paid_at") or "").strip()

        if dep_str:
            dep_date = date.fromisoformat(dep_str)
            if start_date <= dep_date <= end_date:
                deposit = config.quantize(total_gbp / 2)
                _add(dep_date,
                     f"SWIFT XFER {supplier_name.upper()} {supplier_ccy}",
                     -deposit, supplier_name, "SUPPLIER")

        if bal_str:
            bal_date = date.fromisoformat(bal_str)
            if start_date <= bal_date <= end_date:
                balance_amt = config.quantize(
                    total_gbp - config.quantize(total_gbp / 2))
                _add(bal_date,
                     f"SWIFT XFER {supplier_name.upper()} {supplier_ccy}",
                     -balance_amt, supplier_name, "SUPPLIER")

    # --- 5. Recurring costs (monthly) ---
    for y, m in config.months_in_range(start_date, end_date):
        month_date = date(y, m, 1)

        # Payroll (25th)
        payroll_date = min(date(y, m, 25), end_date)
        payroll = Decimal("18000.00")
        if y >= 2025 and m >= 6:
            payroll = Decimal("19200.00")
        variation = Decimal(str(rng.uniform(-200, 200)))
        payroll = config.quantize(payroll + variation)
        _add(payroll_date,
             f"BACS PAYROLL {payroll_date.strftime('%d%b').upper()} STAFF",
             -payroll, "Pretty Fly Payroll", "PAYROLL")

        # Klaviyo (variable based on list growth)
        months_elapsed = (y - 2024) * 12 + m - 6
        klaviyo_cost = config.quantize(
            Decimal("150") + Decimal(str(max(0, months_elapsed))) * Decimal("8.33"))
        klaviyo_cost = min(klaviyo_cost, Decimal("350"))
        ref = rng.integers(1000, 9999)
        kl_date = min(date(y, m, 5), end_date)
        _add(kl_date,
             f"SQ *KLAVIYO INC {ref} DUB",
             -klaviyo_cost, "Klaviyo", "MARKETING")

        # Shopify subscription
        ref = rng.integers(10000, 99999)
        _add(min(date(y, m, 1), end_date),
             f"SHOPIFY* SUB {ref}",
             -config.SHOPIFY_SUBSCRIPTION, "Shopify", "SAAS")

        # Intercom (Fin AI)
        ref = rng.integers(10000, 99999)
        _add(min(date(y, m, 3), end_date),
             f"INTERCOM INC SF CA {ref}",
             -Decimal("199.00"), "Intercom", "SAAS")

        # Xero
        ref = rng.integers(10000, 99999)
        _add(min(date(y, m, 3), end_date),
             f"XERO LTD {ref}",
             -Decimal("42.00"), "Xero", "SAAS")

        # Notion
        ref = rng.integers(10000, 99999)
        _add(min(date(y, m, 3), end_date),
             f"NOTION LABS INC {ref}",
             -Decimal("24.00"), "Notion Labs", "SAAS")

        # Figma
        ref = rng.integers(10000, 99999)
        _add(min(date(y, m, 3), end_date),
             f"FIGMA INC {ref}",
             -Decimal("33.00"), "Figma", "SAAS")

        # Mixview Analytics — dead-weight SaaS (Weakness #6)
        ref = rng.integers(10000, 99999)
        _add(min(date(y, m, 3), end_date),
             f"MIXVIEW ANALYTICS LTD {ref}",
             -Decimal("349.00"), "Mixview Analytics", "SAAS")

        # Rent
        _add(min(date(y, m, 1), end_date),
             "STANDING ORDER STUDIO N1 LDN",
             -Decimal("3200.00"), "Studio N1 Landlord", "RENT")

        # 3PL costs (variable)
        month_orders = [o for o in orders
                        if o["created_at"][:7] == f"{y:04d}-{m:02d}"]
        if month_orders:
            threePL = config.quantize(
                Decimal(str(len(month_orders))) * Decimal("3.50"))
            _add(min(date(y, m, 28), end_date),
                 f"HUB3PL LONDON N1 INVC{rng.integers(1000, 9999)}",
                 -threePL, "Hub3PL", "FULFILMENT")

        # Shipping carriers
        if month_orders:
            ship = config.quantize(
                Decimal(str(len(month_orders))) * Decimal("6.00"))
            carrier = rng.choice(["DHL EXPRESS IRL", "ROYAL MAIL BUSINESS"])
            carrier_name = "DHL" if "DHL" in carrier else "Royal Mail"
            _add(min(date(y, m, 28), end_date),
                 carrier, -ship, carrier_name, "SHIPPING")

        # Misc (coffee, small expenses)
        for _ in range(rng.integers(2, 5)):
            misc_date = date(y, m, max(1, min(28, int(rng.uniform(1, 28)))))
            if misc_date > end_date:
                continue
            misc_amt = config.quantize(Decimal(str(rng.uniform(3, 12))))
            misc_choice = rng.choice([
                ("PRET A MANGER", "Pret A Manger"),
                ("WORKSHOP COFFEE", "Workshop Coffee"),
                ("TESCO EXPRESS", "Tesco"),
                ("AMAZON MARKETPLACE", "Amazon"),
            ])
            _add(misc_date, misc_choice[0], -misc_amt, misc_choice[1], "OTHER")

    # --- 6. HMRC VAT payments (quarterly) ---
    # UK VAT quarters end Mar/Jun/Sep/Dec, payment due ~37 days later
    vat_by_quarter = defaultdict(lambda: Decimal("0"))
    for o in orders:
        odate = date.fromisoformat(o["created_at"][:10])
        # Quarter: Q1=Jan-Mar, Q2=Apr-Jun, Q3=Jul-Sep, Q4=Oct-Dec
        q = (odate.month - 1) // 3
        vat_by_quarter[(odate.year, q)] += Decimal(o["total_tax"])

    for (y, q), vat_amount in sorted(vat_by_quarter.items()):
        if vat_amount <= 0:
            continue
        # Payment due ~37 days after quarter end
        quarter_end_month = (q + 1) * 3
        quarter_end = date(y, quarter_end_month, 1) + timedelta(days=30)
        # Simplify: pay on 7th of month+1 after quarter end
        pay_month = quarter_end_month + 1
        pay_year = y
        if pay_month > 12:
            pay_month -= 12
            pay_year += 1
        try:
            vat_pay_date = date(pay_year, pay_month, 7)
        except ValueError:
            vat_pay_date = date(pay_year, pay_month, 1)

        if start_date <= vat_pay_date <= end_date:
            _add(vat_pay_date,
                 f"HMRC VAT PAYMENT Q{q+1} {y}",
                 -vat_amount, "HMRC", "OTHER")

    # Sort all transactions by date then transaction_id
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
    return "Unknown Supplier"


def _supplier_ccy(supplier_id, prior_data):
    for s in prior_data.get("suppliers", []):
        if s["supplier_id"] == supplier_id:
            return s["currency"]
    return "GBP"
