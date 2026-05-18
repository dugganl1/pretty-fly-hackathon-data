"""
Stage 2: Purchase orders and PO line items.
One PO per drop per supplier. Deposit paid when PO is placed (lead_time before
delivery), balance paid on delivery. With ~9 drops × ~3 suppliers = ~25-30 POs.
"""

from decimal import Decimal
from datetime import date, timedelta
from collections import defaultdict
from . import config
from . import stage1_products


# Primary supplier per product type
CATEGORY_SUPPLIER = {
    "Tee": "sup_001",       # Porto Knit Co.
    "Hoodie": "sup_001",
    "Sweatpants": "sup_001",
    "Cap": "sup_002",       # Milano Trims SRL
    "Outerwear": "sup_002",
    "Trainer": "sup_005",   # Iberia Footwear SA
}


def generate(cfg, prior_data):
    products = prior_data["products"]
    variants = prior_data["variants"]
    end_date = cfg["end_date"]
    rng = config.make_rng(config.SEED + 2)

    var_by_product = defaultdict(list)
    for v in variants:
        var_by_product[v["product_id"]].append(v)

    # Supplier info lookup
    supplier_info = {s["supplier_id"]: s for s in stage1_products.SUPPLIERS}

    # Group products by (drop_collection, supplier_id)
    # Each drop in stage1_products.DROPS has a collection name, launch date, and products
    drop_groups = defaultdict(list)  # (coll_name, supplier_id) -> list of products
    prod_launch = {}  # product_id -> launch date
    drop_launch_dates = {}  # coll_name -> date

    for coll_name, launch_str, product_defs in stage1_products.DROPS:
        launch = date.fromisoformat(launch_str)
        drop_launch_dates[coll_name] = launch

        for title, ptype, gender, price, colours, sizes_override in product_defs:
            # Find the product in our products list
            matching = [p for p in products if p["title"] == title
                        and p["collection"] == coll_name]
            if not matching:
                continue
            p = matching[0]
            prod_launch[p["product_id"]] = launch
            sid = CATEGORY_SUPPLIER.get(ptype, "sup_001")
            drop_groups[(coll_name, sid)].append(p)

    pos = []
    po_lines = []
    po_counter = 0

    for (coll_name, sid), group_products in sorted(drop_groups.items()):
        launch = drop_launch_dates[coll_name]
        sup = supplier_info.get(sid, {})
        lead_days = sup.get("lead_time_days", 60)
        currency = sup.get("currency", "EUR")

        # PO created lead_time days before launch
        po_date = launch - timedelta(days=lead_days)
        delivery = launch

        # Deposit paid when PO is placed, balance on delivery
        deposit_date = po_date
        balance_date = delivery

        po_counter += 1
        po_id = f"PO-{launch.year}-{po_counter:04d}"

        # FX rate with small noise
        fx_noise = Decimal(str(1.0 + rng.uniform(-0.02, 0.02)))
        if currency == "EUR":
            fx_rate = config.quantize(config.FX_EUR_GBP_BASE * fx_noise)
        elif currency == "USD":
            fx_rate = config.quantize(config.FX_USD_GBP_BASE * fx_noise)
        else:
            fx_rate = Decimal("1.00")

        total_cost_ccy = Decimal("0")
        total_cost_gbp = Decimal("0")
        pl_counter = 0

        for p in group_products:
            pid = p["product_id"]
            ptype = p["product_type"]
            gender = p["gender_segment"]

            # How many months this product will be sellable
            months_avail = max(1, (end_date - launch).days / 30)

            for v in var_by_product.get(pid, []):
                pl_counter += 1
                vid = v["variant_id"]
                qty = _order_quantity(p, v, gender, rng, months_avail)

                retail_price = Decimal(v["price"])
                net_retail = config.net_price(retail_price)
                cost_fraction = config.CATEGORY_COST_FRACTIONS.get(
                    ptype, Decimal("0.40"))
                unit_cost_gbp = config.quantize(net_retail * cost_fraction)

                if fx_rate > 0:
                    unit_cost_ccy = config.quantize(unit_cost_gbp / fx_rate)
                else:
                    unit_cost_ccy = unit_cost_gbp

                landed_cost_gbp = unit_cost_gbp
                line_cost_ccy = config.quantize(unit_cost_ccy * qty)
                line_cost_gbp = config.quantize(unit_cost_gbp * qty)
                total_cost_ccy += line_cost_ccy
                total_cost_gbp += line_cost_gbp

                pl_id = f"{po_id}-L{pl_counter:03d}"
                po_lines.append({
                    "po_line_id": pl_id,
                    "po_id": po_id,
                    "variant_id": vid,
                    "quantity_ordered": qty,
                    "quantity_received": qty if delivery <= end_date else 0,
                    "unit_cost_supplier_ccy": str(unit_cost_ccy),
                    "landed_cost_per_unit_gbp": str(landed_cost_gbp),
                })

        # Status and payment dates gated by end_date
        if delivery <= end_date:
            status = "received"
            dep_paid = deposit_date.isoformat() if deposit_date <= end_date else ""
            bal_paid = balance_date.isoformat()
        elif deposit_date <= end_date:
            status = "in_production"
            dep_paid = deposit_date.isoformat()
            bal_paid = ""
        else:
            status = "placed"
            dep_paid = ""
            bal_paid = ""

        pos.append({
            "po_id": po_id,
            "supplier_id": sid,
            "created_at": po_date.isoformat(),
            "expected_delivery": delivery.isoformat(),
            "actual_delivery": delivery.isoformat() if delivery <= end_date else "",
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


def _order_quantity(product, variant, gender, rng, months_avail=24):
    """Determine PO quantity for a variant, scaled by months available."""
    ptype = product["product_type"]
    size = variant["option1_value"]
    colour = variant["option2_value"]
    title = product["title"]

    # Base per-variant quantities sized for ~8 months of demand.
    # Products available longer get proportionally more stock.
    base = {"Tee": 75, "Hoodie": 48, "Sweatpants": 42, "Cap": 50,
            "Trainer": 26, "Outerwear": 24}
    qty = base.get(ptype, 40)

    # Scale by months available (relative to 8-month base, capped at 3.0)
    time_scale = max(0.3, min(months_avail / 8.0, 3.0))
    qty = int(qty * time_scale)

    size_mult = {"XS": 0.5, "S": 0.8, "M": 1.2, "L": 1.0, "XL": 0.6, "ONE": 1.0}
    for s, m in size_mult.items():
        if s in size:
            qty = int(qty * m)
            break

    if ptype == "Trainer":
        mid_sizes = ["UK8", "UK9", "UK10"]
        qty = int(qty * 1.3) if size in mid_sizes else int(qty * 0.7)

    # Weakness #8: slow-moving womens SKUs moderately over-ordered
    # Produces DIO ~200-350 (clearly above portfolio avg ~75 but not absurd)
    if gender == "womens":
        if "Relaxed Hoodie" in title and colour == "Burgundy" and size in ("M", "L"):
            qty = 50 if size == "M" else 40
        elif "Wide-Leg Sweatpant" in title and colour == "Sage" and size in ("M", "L"):
            qty = 25 if size == "M" else 18

    qty = max(10, int(qty * (1.0 + rng.uniform(-0.1, 0.1))))
    return qty
