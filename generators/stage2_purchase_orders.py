"""
Stage 2: Purchase orders and PO line items.
Creates POs paced to drops — inventory arrives before each drop launches.
"""

from decimal import Decimal
from datetime import date, timedelta
from . import config


def generate(cfg, prior_data):
    products = prior_data["products"]
    variants = prior_data["variants"]
    suppliers = prior_data["suppliers"]
    end_date = cfg["end_date"]

    rng = config.make_rng(config.SEED + 2)

    # Build lookups
    prod_map = {p["product_id"]: p for p in products}
    var_by_product = {}
    for v in variants:
        var_by_product.setdefault(v["product_id"], []).append(v)

    # Category -> supplier
    cat_supplier = {}
    for s in config.stage1_products.SUPPLIERS:
        for cat in s["categories"]:
            if cat not in cat_supplier:
                cat_supplier[cat] = s["supplier_id"]

    # Supplier lead times
    supplier_lead = {s["supplier_id"]: s["lead_time_days"]
                     for s in config.stage1_products.SUPPLIERS}
    supplier_currency = {s["supplier_id"]: s["currency"]
                         for s in config.stage1_products.SUPPLIERS}
    supplier_terms = {s["supplier_id"]: s["payment_terms"]
                      for s in config.stage1_products.SUPPLIERS}

    pos = []
    po_lines = []
    po_counter = 0

    # For each product, create a PO that arrives before its collection launch date
    for p in products:
        pid = p["product_id"]
        ptype = p["product_type"]
        gender = p["gender_segment"]
        launch_str = p["created_at"][:10]
        launch = date.fromisoformat(launch_str)

        sid = cat_supplier.get(ptype, "sup_001")
        lead = supplier_lead.get(sid, 60)
        currency = supplier_currency.get(sid, "EUR")
        terms = supplier_terms.get(sid, "50% deposit / 50% on shipment")

        # PO created lead_time days before launch
        po_date = launch - timedelta(days=lead)
        if po_date < config.DATASET_START:
            po_date = config.DATASET_START

        po_counter += 1
        po_id = f"PO-{po_date.year}-{po_counter:04d}"

        # FX rate with noise
        month_offset = (po_date.year - 2024) * 12 + po_date.month
        fx_noise = Decimal(str(1.0 + rng.uniform(-0.02, 0.02)))
        if currency == "EUR":
            fx_rate = config.quantize(config.FX_EUR_GBP_BASE * fx_noise)
        elif currency == "USD":
            fx_rate = config.quantize(config.FX_USD_GBP_BASE * fx_noise)
        else:
            fx_rate = Decimal("1.00")

        # Delivery = PO date + lead time = launch date (simplified)
        delivery = launch

        # Deposit and balance payment dates
        deposit_date = po_date
        balance_date = delivery

        total_cost_ccy = Decimal("0")
        total_cost_gbp = Decimal("0")
        po_line_counter = 0

        for v in var_by_product.get(pid, []):
            po_line_counter += 1
            vid = v["variant_id"]

            # Order quantity depends on product type, size, and weakness targets
            qty = _order_quantity(p, v, gender, rng)

            # Unit cost = retail price * cost fraction / VAT divisor (cost is on net price)
            retail_price = Decimal(v["price"])
            net_retail = config.net_price(retail_price)
            cost_fraction = config.CATEGORY_COST_FRACTIONS.get(ptype, Decimal("0.40"))
            unit_cost_gbp = config.quantize(net_retail * cost_fraction)

            # Convert to supplier currency
            if fx_rate > 0:
                unit_cost_ccy = config.quantize(unit_cost_gbp / fx_rate)
            else:
                unit_cost_ccy = unit_cost_gbp

            # Landed cost includes freight + duties (15-25% markup)
            landed_markup = Decimal("1.00")  # Cost fraction already represents landed
            landed_cost_gbp = unit_cost_gbp

            line_cost_ccy = config.quantize(unit_cost_ccy * qty)
            line_cost_gbp = config.quantize(unit_cost_gbp * qty)
            total_cost_ccy += line_cost_ccy
            total_cost_gbp += line_cost_gbp

            pl_id = f"{po_id}-L{po_line_counter:03d}"
            po_lines.append({
                "po_line_id": pl_id,
                "po_id": po_id,
                "variant_id": vid,
                "quantity_ordered": qty,
                "quantity_received": qty,
                "unit_cost_supplier_ccy": str(unit_cost_ccy),
                "landed_cost_per_unit_gbp": str(landed_cost_gbp),
            })

        # Set status and payment dates based on whether events occurred by end_date
        if delivery <= end_date:
            status = "received"
            dep_paid = deposit_date.isoformat() if deposit_date <= end_date else ""
            bal_paid = balance_date.isoformat()
            actual_del = delivery.isoformat()
            qty_received_mult = 1
        elif po_date <= end_date:
            status = "in_production"
            dep_paid = deposit_date.isoformat() if deposit_date <= end_date else ""
            bal_paid = ""
            actual_del = ""
            qty_received_mult = 0
        else:
            status = "placed"
            dep_paid = ""
            bal_paid = ""
            actual_del = ""
            qty_received_mult = 0

        # Update quantity_received for unreceived POs
        if qty_received_mult == 0:
            for pli in po_lines:
                if pli["po_id"] == po_id:
                    pli["quantity_received"] = 0

        pos.append({
            "po_id": po_id,
            "supplier_id": sid,
            "created_at": po_date.isoformat(),
            "expected_delivery": delivery.isoformat(),
            "actual_delivery": actual_del,
            "status": status,
            "total_cost_supplier_ccy": str(total_cost_ccy),
            "total_cost_gbp": str(total_cost_gbp),
            "deposit_paid_at": dep_paid,
            "balance_paid_at": bal_paid,
        })

    return {
        "purchase_orders": pos,
        "po_line_items": po_lines,
    }


def _order_quantity(product, variant, gender, rng):
    """Determine PO quantity for a variant."""
    ptype = product["product_type"]
    size = variant["option1_value"]
    colour = variant["option2_value"]
    title = product["title"]

    # Base quantities by type
    base = {"Tee": 80, "Hoodie": 50, "Sweatpants": 45, "Cap": 60,
            "Trainer": 30, "Outerwear": 25}
    qty = base.get(ptype, 40)

    # Size curve: M and L get more
    size_mult = {"XS": 0.5, "S": 0.8, "M": 1.2, "L": 1.0, "XL": 0.6, "ONE": 1.0}
    for s, m in size_mult.items():
        if s in size:
            qty = int(qty * m)
            break
    # Trainer sizes: middle sizes get more
    if ptype == "Trainer":
        mid_sizes = ["UK8", "UK9", "UK10"]
        if size in mid_sizes:
            qty = int(qty * 1.3)
        else:
            qty = int(qty * 0.7)

    # Weakness #8: slow-moving womens SKUs get over-ordered
    if gender == "womens":
        if "Relaxed Hoodie" in title and colour == "Burgundy" and size in ("M", "L"):
            qty = 120 if size == "M" else 80
        elif "Wide-Leg Sweatpant" in title and colour == "Sage" and size in ("M", "L"):
            qty = 100 if size == "M" else 60

    # Add small noise
    qty = max(10, int(qty * (1.0 + rng.uniform(-0.1, 0.1))))

    return qty
