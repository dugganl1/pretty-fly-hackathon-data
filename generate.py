#!/usr/bin/env python3
"""
generate.py — Main entrypoint for Pretty Fly dataset generation.

Usage:
    python generate.py --months 1 --output data/sample/
    python generate.py --months 24 --output data/full/
"""

import argparse
import csv
import json
import sys
from pathlib import Path

from generators import config
from generators import stage1_products
from generators import stage2_purchase_orders
from generators import stage3_ads
from generators import stage4_orders
from generators import stage5_inventory
from generators import stage6_email
from generators import stage7_support
from generators import stage8_bank


def write_csv(data_dir, filename, rows):
    """Write a list of dicts to CSV."""
    if not rows:
        return
    path = data_dir / filename
    fieldnames = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"  Wrote {len(rows):>7,} rows → {filename}")


def write_json(data_dir, filename, data):
    """Write data to JSON."""
    path = data_dir / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    count = len(data) if isinstance(data, list) else "—"
    print(f"  Wrote {count:>7} items → {filename}")


def main():
    parser = argparse.ArgumentParser(description="Generate Pretty Fly dataset")
    parser.add_argument("--months", type=int, default=24,
                        help="Number of months to generate (default: 24)")
    parser.add_argument("--output", type=str, default="data/full/",
                        help="Output directory (default: data/full/)")
    args = parser.parse_args()

    data_dir = Path(args.output)
    data_dir.mkdir(parents=True, exist_ok=True)

    start_date = config.DATASET_START
    start_date, end_date = config.date_range(start_date, args.months)

    print(f"\nGenerating Pretty Fly dataset")
    print(f"  Window: {start_date} → {end_date} ({args.months} months)")
    print(f"  Output: {data_dir}\n")

    cfg = {
        "start_date": start_date,
        "end_date": end_date,
        "months": args.months,
    }

    # Accumulate all data across stages
    all_data = {}

    # Stage 1: Products, variants, collections, suppliers
    print("Stage 1: Products & suppliers...")
    s1 = stage1_products.generate(cfg, None)
    all_data.update(s1)
    write_csv(data_dir, "products.csv", s1["products"])
    write_csv(data_dir, "collections.csv", s1["collections"])
    write_csv(data_dir, "product_collections.csv", s1["product_collections"])
    write_csv(data_dir, "suppliers.csv", s1["suppliers"])
    # Variants written after stage 5 (inventory quantities updated)

    # Stage 2: Purchase orders
    print("Stage 2: Purchase orders...")
    # Need to make stage1_products accessible from stage2
    import generators.stage1_products
    config.stage1_products = generators.stage1_products
    s2 = stage2_purchase_orders.generate(cfg, all_data)
    all_data.update(s2)
    write_csv(data_dir, "purchase_orders.csv", s2["purchase_orders"])
    write_csv(data_dir, "po_line_items.csv", s2["po_line_items"])

    # Stage 3: Ads
    print("Stage 3: Ads campaigns...")
    s3 = stage3_ads.generate(cfg, all_data)
    all_data.update(s3)
    write_csv(data_dir, "google_ads_daily.csv", s3["google_ads_daily"])
    write_csv(data_dir, "meta_ads_daily.csv", s3["meta_ads_daily"])

    # Stage 4: Orders
    print("Stage 4: Customers & orders...")
    s4 = stage4_orders.generate(cfg, all_data)
    all_data.update(s4)
    write_csv(data_dir, "customers.csv", s4["customers"])
    write_csv(data_dir, "addresses.csv", s4["addresses"])
    write_csv(data_dir, "orders.csv", s4["orders"])
    write_csv(data_dir, "line_items.csv", s4["line_items"])
    write_csv(data_dir, "refunds.csv", s4["refunds"])
    write_csv(data_dir, "discount_codes.csv", s4["discount_codes"])

    # Stage 5: Inventory movements
    print("Stage 5: Inventory movements...")
    s5 = stage5_inventory.generate(cfg, all_data)
    all_data.update(s5)
    write_csv(data_dir, "inventory_movements.csv", s5["inventory_movements"])
    # Now write variants with updated inventory_quantity
    write_csv(data_dir, "variants.csv", s5["variants"])

    # Stage 6: Email
    print("Stage 6: Email campaigns...")
    s6 = stage6_email.generate(cfg, all_data)
    all_data.update(s6)
    write_csv(data_dir, "email_campaigns.csv", s6["email_campaigns"])
    write_csv(data_dir, "email_events.csv", s6["email_events"])

    # Stage 7: Support
    print("Stage 7: Support tickets...")
    s7 = stage7_support.generate(cfg, all_data)
    all_data.update(s7)
    write_csv(data_dir, "support_tickets.csv", s7["support_tickets"])
    write_json(data_dir, "support_messages.json", s7["support_messages"])

    # Stage 8: Bank transactions
    print("Stage 8: Bank transactions...")
    s8 = stage8_bank.generate(cfg, all_data)
    all_data.update(s8)
    write_csv(data_dir, "bank_transactions.csv", s8["bank_transactions"])

    print(f"\nDone. {len(list(data_dir.glob('*')))} files written to {data_dir}")


if __name__ == "__main__":
    main()
