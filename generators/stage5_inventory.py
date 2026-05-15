"""
Stage 5: Inventory movements.
Reconciles PO receipts, sales, and returns into a movement ledger.
Sets final inventory_quantity on variants.
"""

from decimal import Decimal
from collections import defaultdict
import json
from . import config


def generate(cfg, prior_data):
    variants = prior_data["variants"]
    po_line_items = prior_data["po_line_items"]
    purchase_orders = prior_data["purchase_orders"]
    line_items = prior_data["line_items"]
    orders = prior_data["orders"]
    refunds = prior_data["refunds"]

    # Build lookups
    var_map = {v["variant_id"]: v for v in variants}
    po_map = {po["po_id"]: po for po in purchase_orders}
    order_map = {o["order_id"]: o for o in orders}

    movements = []
    mv_counter = 0
    # Track running balance per variant
    balances = defaultdict(int)

    # 1. PO receipts (ordered by delivery date)
    pli_with_date = []
    for pli in po_line_items:
        po = po_map.get(pli["po_id"])
        if po and po["status"] == "received":
            delivery_date = po["actual_delivery"]
            pli_with_date.append((delivery_date, pli))

    pli_with_date.sort(key=lambda x: x[0])

    for delivery_date, pli in pli_with_date:
        mv_counter += 1
        vid = pli["variant_id"]
        qty = int(pli["quantity_received"])
        balances[vid] += qty
        movements.append({
            "movement_id": f"mv_{mv_counter:07d}",
            "variant_id": vid,
            "date": f"{delivery_date}T08:00:00",
            "type": "po_receipt",
            "quantity_delta": qty,
            "running_balance": balances[vid],
            "reference_id": pli["po_id"],
        })

    # 2. Sales (ordered by order date)
    # Group line items by order for ordering
    li_by_order = defaultdict(list)
    for li in line_items:
        li_by_order[li["order_id"]].append(li)

    order_dates = [(o["created_at"], o["order_id"]) for o in orders]
    order_dates.sort()

    for order_time, oid in order_dates:
        for li in li_by_order.get(oid, []):
            mv_counter += 1
            vid = li["variant_id"]
            qty = int(li["quantity"])
            balances[vid] -= qty
            movements.append({
                "movement_id": f"mv_{mv_counter:07d}",
                "variant_id": vid,
                "date": order_time,
                "type": "sale",
                "quantity_delta": -qty,
                "running_balance": balances[vid],
                "reference_id": oid,
            })

    # 3. Returns (ordered by refund date)
    refund_sorted = sorted(refunds, key=lambda r: r["created_at"])
    for r in refund_sorted:
        raw = r.get("refund_line_items", "[]")
        try:
            variant_ids = json.loads(raw) if raw else []
        except (json.JSONDecodeError, TypeError):
            variant_ids = []

        for vid in variant_ids:
            mv_counter += 1
            balances[vid] += 1
            movements.append({
                "movement_id": f"mv_{mv_counter:07d}",
                "variant_id": vid,
                "date": r["created_at"],
                "type": "return",
                "quantity_delta": 1,
                "running_balance": balances[vid],
                "reference_id": r["order_id"],
            })

    # Update variant inventory_quantity to final balance
    for v in variants:
        vid = v["variant_id"]
        v["inventory_quantity"] = balances.get(vid, 0)

    return {
        "inventory_movements": movements,
        "variants": variants,  # Updated with final inventory quantities
    }
