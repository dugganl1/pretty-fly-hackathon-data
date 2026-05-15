"""
Stage 4: Customers, addresses, orders, line items, refunds, discount codes.
The core transactional engine. Generates orders driven by seasonality and drops.
"""

from decimal import Decimal
from datetime import date, timedelta, datetime
from collections import defaultdict
from . import config
from . import stage1_products
from . import stage3_ads

# UTM sources with weights
UTM_SOURCES = [
    ("google", "cpc", 0.25),
    ("facebook", "paid_social", 0.18),
    ("instagram", "paid_social", 0.12),
    ("klaviyo", "email", 0.15),
    ("direct", "none", 0.15),
    ("organic", "organic", 0.10),
    ("tiktok", "organic_social", 0.05),
]

# Map UTM sources to campaign names
def _pick_campaign(utm_source, order_date, gender, rng):
    if utm_source == "google":
        camps = [c[0] for c in stage3_ads.GOOGLE_CAMPAIGNS]
        # Weight toward brand/shopping, low weight for generic
        weights = [3, 1, 3, 3, 1, 0.5, 3]
        weights = [w / sum(weights) for w in weights]
        return rng.choice(camps, p=weights)
    elif utm_source in ("facebook", "instagram"):
        camps = [c[0] for c in stage3_ads.META_CAMPAIGNS]
        weights = [3, 1, 2, 0.5]
        # Add womens campaign if applicable
        if order_date >= config.WOMENS_LAUNCH and gender == "womens":
            camps.append("Womens_Launch_Prospecting")
            weights.append(4)
        elif order_date >= config.WOMENS_LAUNCH:
            camps.append("Womens_Launch_Prospecting")
            weights.append(0.3)  # Some mens also see it
        weights = [w / sum(weights) for w in weights]
        return rng.choice(camps, p=weights)
    elif utm_source == "klaviyo":
        if gender == "womens" and order_date >= config.WOMENS_LAUNCH:
            return "Womens_Welcome_Flow"
        return rng.choice(["Welcome_Flow", "Abandoned_Cart", "Drop_Announcement",
                           "Restock_Alert", "Win_Back"])
    return ""


def generate(cfg, prior_data):
    rng = config.make_rng(config.SEED + 4)
    start_date, end_date = cfg["start_date"], cfg["end_date"]

    products = prior_data["products"]
    variants = prior_data["variants"]

    # Build lookups
    prod_map = {p["product_id"]: p for p in products}
    var_map = {v["variant_id"]: v for v in variants}
    var_by_product = defaultdict(list)
    for v in variants:
        var_by_product[v["product_id"]].append(v)

    # Products available by date (only sell products whose collection has launched)
    prod_launch = {p["product_id"]: date.fromisoformat(p["created_at"][:10])
                   for p in products}

    # Build product selection weights by category revenue target
    prod_by_type = defaultdict(list)
    for p in products:
        prod_by_type[p["product_type"]].append(p)

    # Drop dates for spike calculation
    drop_dates = set()
    for coll_name, launch_date, _ in stage1_products.DROPS:
        drop_dates.add(date.fromisoformat(launch_date))

    # Generate daily order counts
    customers = []
    addresses = []
    orders = []
    line_items = []
    refunds = []
    customer_map = {}  # email -> customer dict
    cust_counter = 0
    order_counter = 0
    li_counter = 0
    refund_counter = 0
    order_number = config.ORDER_NUMBER_START

    # Track discount code usage
    discount_usage = defaultdict(int)

    # Calculate total orders target for the period
    total_days = (end_date - start_date).days + 1
    months_count = max(1, total_days / 30)
    # Target ~22k orders over 24 months = ~917/month in Y1, growing to ~1083 in Y2
    base_daily = 30  # ~900/month base

    current = start_date
    while current <= end_date:
        # Daily order volume
        month = current.month
        seasonal = config.SEASONALITY.get(month, 1.0)
        dow_mult = 1.15 if current.weekday() < 5 else 0.80

        # Growth trend: ~2% per month compound
        months_from_start = ((current.year - start_date.year) * 12
                             + current.month - start_date.month)
        growth = 1.0 + 0.02 * months_from_start

        # Drop spike
        spike = 1.0
        for dd in drop_dates:
            days_since = (current - dd).days
            if days_since == 0:
                spike = max(spike, 4.0)
            elif 0 < days_since <= 3:
                spike = max(spike, 3.0 * (0.7 ** days_since))
            elif 3 < days_since <= 10:
                spike = max(spike, 1.5 * (0.8 ** (days_since - 3)))

        # Black Friday spike
        if current.month == 11 and current.day >= 25:
            bf_friday = _black_friday(current.year)
            days_from_bf = (current - bf_friday).days
            if days_from_bf == 0:
                spike = max(spike, 6.0)
            elif 1 <= days_from_bf <= 3:
                spike = max(spike, 4.0 * (0.7 ** days_from_bf))
            elif -3 <= days_from_bf < 0:
                spike = max(spike, 2.0)

        # January sale
        if current.month == 1 and current.day <= 10:
            spike = max(spike, 2.5 * (0.9 ** (current.day - 1)))

        daily_volume = max(1, int(
            base_daily * seasonal * dow_mult * growth * spike
            * (1.0 + rng.uniform(-0.15, 0.15))
        ))

        # Generate orders for this day
        for _ in range(daily_volume):
            order_counter += 1
            order_number_val = order_number
            order_number += 1

            # Determine market
            market = rng.choice(list(config.MARKET_WEIGHTS.keys()),
                                p=list(config.MARKET_WEIGHTS.values()))
            is_uk = market == "UK"
            country = rng.choice(config.MARKET_COUNTRIES[market])

            # Pick available products
            available = [p for p in products
                         if prod_launch[p["product_id"]] <= current]
            if not available:
                continue

            # Determine if this is a womens order
            womens_available = [p for p in available
                                if p["gender_segment"] == "womens"]
            is_womens_order = (len(womens_available) > 0
                               and rng.random() < 0.15  # 15% of orders post-launch
                               and current >= config.WOMENS_LAUNCH)

            # Pick UTM source
            utm_idx = rng.choice(len(UTM_SOURCES),
                                 p=[w for _, _, w in UTM_SOURCES])
            utm_source, utm_medium, _ = UTM_SOURCES[utm_idx]

            gender = "womens" if is_womens_order else "mens"
            utm_campaign = _pick_campaign(utm_source, current, gender, rng)

            # Determine if customer is new or returning
            is_repeat = len(customer_map) > 0 and rng.random() < _repeat_prob(
                current, gender)

            if is_repeat:
                # Pick an existing customer
                cust_email = rng.choice(list(customer_map.keys()))
                cust = customer_map[cust_email]
                cust_id = cust["customer_id"]
            else:
                # New customer
                cust_counter += 1
                cust_id = f"cust_{cust_counter:06d}"
                is_female = is_womens_order or rng.random() < 0.35
                if is_female:
                    first = rng.choice(config.FIRST_NAMES_F)
                else:
                    first = rng.choice(config.FIRST_NAMES_M)
                last = rng.choice(config.LAST_NAMES)
                email = f"{first.lower()}.{last.lower()}.{cust_counter}@example-fake.com"

                cust = {
                    "customer_id": cust_id,
                    "email": email,
                    "first_name": first,
                    "last_name": last,
                    "created_at": f"{current.isoformat()}T{_rand_time(rng)}",
                    "accepts_marketing": "true" if rng.random() < 0.70 else "false",
                    "total_spent": "0",
                    "orders_count": "0",
                    "acquisition_source": f"{utm_source}/{utm_medium}/{utm_campaign}" if utm_campaign else f"{utm_source}/{utm_medium}/direct",
                    "acquisition_date": current.isoformat(),
                    "default_country": country,
                    "gender_segment_affinity": gender,
                }
                customers.append(cust)
                customer_map[email] = cust

                # Address
                addr = _make_address(cust_id, first, last, country, rng)
                addresses.append(addr)

            # Build line items for this order
            n_items = _pick_item_count(rng, has_discount=False)  # adjusted below

            # Discount code?
            discount_code = ""
            discount_amount = Decimal("0")
            active_codes = [c for c in config.DISCOUNT_CODES
                            if c["starts_at"] <= current.isoformat()
                            <= c["ends_at"]]

            # ~15% of orders use a discount
            if active_codes and rng.random() < 0.15:
                code_info = rng.choice(active_codes)
                discount_code = code_info["code"]
                # Weakness #4: discounted orders have smaller baskets
                n_items = _pick_item_count(rng, has_discount=True)

            # Select products for this order
            order_products = _select_products(
                available, n_items, is_womens_order, rng)

            order_li = []
            subtotal = Decimal("0")
            oid = f"ord_{order_counter:06d}"
            order_time = f"{current.isoformat()}T{_rand_time(rng)}"

            for p in order_products:
                li_counter += 1
                lid = f"li_{li_counter:07d}"
                # Pick a random variant
                p_variants = var_by_product.get(p["product_id"], [])
                if not p_variants:
                    continue
                v = rng.choice(p_variants)
                retail_price = Decimal(v["price"])
                # Line item price is net (ex-VAT)
                line_price = config.net_price(retail_price)
                qty = 1

                li_disc = Decimal("0")  # per-line discount assigned later

                order_li.append({
                    "line_item_id": lid,
                    "order_id": oid,
                    "variant_id": v["variant_id"],
                    "product_id": p["product_id"],
                    "title": f"{p['title']} - {v['option2_value']} / {v['option1_value']}",
                    "quantity": qty,
                    "price": str(line_price),
                    "total_discount": "0",  # set below
                })
                subtotal += line_price * qty

            if not order_li:
                order_number -= 1
                order_counter -= 1
                continue

            # Apply discount
            if discount_code:
                code_info = next(c for c in config.DISCOUNT_CODES
                                 if c["code"] == discount_code)
                if code_info["type"] == "percentage":
                    discount_amount = config.quantize(
                        subtotal * code_info["value"] / Decimal("100"))
                elif code_info["type"] == "fixed_amount":
                    discount_amount = min(code_info["value"], subtotal)
                elif code_info["type"] == "free_shipping":
                    discount_amount = Decimal("0")

                # Distribute discount proportionally across line items
                if discount_amount > 0 and subtotal > 0:
                    for li in order_li:
                        li_val = Decimal(li["price"]) * int(li["quantity"])
                        li_share = config.quantize(
                            discount_amount * li_val / subtotal)
                        li["total_discount"] = str(li_share)

                discount_usage[discount_code] += 1

            # Shipping
            net_after_disc = subtotal - discount_amount
            if net_after_disc >= config.FREE_SHIPPING_THRESHOLD:
                shipping = Decimal("0")
            else:
                shipping = config.SHIPPING_RATES.get(market, Decimal("4.95"))

            # Tax (UK only)
            if is_uk:
                tax = config.vat_amount(net_after_disc + shipping)
            else:
                tax = Decimal("0")

            total_price = config.quantize(
                subtotal - discount_amount + shipping + tax)

            # Update customer aggregates
            cust["total_spent"] = str(
                Decimal(cust["total_spent"]) + total_price)
            cust["orders_count"] = str(int(cust["orders_count"]) + 1)

            orders.append({
                "order_id": oid,
                "order_number": order_number_val,
                "customer_id": cust_id,
                "created_at": order_time,
                "currency": "GBP",
                "subtotal": str(subtotal),
                "total_discounts": str(discount_amount),
                "total_shipping": str(shipping),
                "total_tax": str(tax),
                "total_price": str(total_price),
                "financial_status": "paid",
                "fulfillment_status": "fulfilled",
                "utm_source": utm_source,
                "utm_medium": utm_medium,
                "utm_campaign": utm_campaign,
                "landing_site": "/",
                "referring_site": "",
                "tags": "",
                "discount_code": discount_code,
            })

            line_items.extend(order_li)

        current += timedelta(days=1)

    # Generate refunds
    refunds = _generate_refunds(orders, line_items, var_map, prod_map, rng,
                                 end_date)

    # Update financial_status for refunded orders
    refunded_orders = {r["order_id"] for r in refunds}
    for o in orders:
        if o["order_id"] in refunded_orders:
            o["financial_status"] = "partially_refunded"

    # Build discount_codes table
    discount_codes = []
    for code_info in config.DISCOUNT_CODES:
        discount_codes.append({
            "code": code_info["code"],
            "type": code_info["type"],
            "value": str(code_info["value"]),
            "usage_count": discount_usage.get(code_info["code"], 0),
            "starts_at": code_info["starts_at"],
            "ends_at": code_info["ends_at"],
        })

    return {
        "customers": customers,
        "addresses": addresses,
        "orders": orders,
        "line_items": line_items,
        "refunds": refunds,
        "discount_codes": discount_codes,
    }


def _repeat_prob(order_date, gender):
    """Probability that an order is from a returning customer."""
    base = 0.22
    if gender == "womens":
        base = 0.35  # Womens repeat higher
    return base


def _pick_item_count(rng, has_discount):
    """Pick number of items in an order."""
    if has_discount:
        # Weakness #4: smaller baskets when discounted
        return rng.choice([1, 1, 1, 1, 2], p=[0.80, 0.0, 0.0, 0.0, 0.20])
    # Normal distribution: 70% single, 20% two, 8% three, 2% four
    return rng.choice([1, 2, 3, 4], p=[0.70, 0.20, 0.08, 0.02])


def _select_products(available, n_items, is_womens, rng):
    """Select products for an order based on category revenue weights."""
    if is_womens:
        pool = [p for p in available if p["gender_segment"] == "womens"]
        if not pool:
            pool = available
    else:
        pool = [p for p in available if p["gender_segment"] != "womens"]
        if not pool:
            pool = available

    # Weight by category revenue targets
    weights = []
    for p in pool:
        w = config.CATEGORY_REVENUE_WEIGHTS.get(p["product_type"], 0.05)
        weights.append(w)
    total_w = sum(weights)
    if total_w == 0:
        weights = [1.0 / len(pool)] * len(pool)
    else:
        weights = [w / total_w for w in weights]

    selected = []
    for _ in range(n_items):
        idx = rng.choice(len(pool), p=weights)
        selected.append(pool[idx])
    return selected


def _generate_refunds(orders, line_items, var_map, prod_map, rng, end_date):
    """Generate refunds. Weakness #3: trainers have 22% rate, apparel ~8%."""
    refunds = []
    refund_counter = 0

    # Build order -> line items
    li_by_order = defaultdict(list)
    for li in line_items:
        li_by_order[li["order_id"]].append(li)

    for o in orders:
        oid = o["order_id"]
        olis = li_by_order.get(oid, [])
        if not olis:
            continue

        # Check if any line item triggers a refund
        for li in olis:
            vid = li["variant_id"]
            pid = li["product_id"]
            v = var_map.get(vid, {})
            p = prod_map.get(pid, {})
            ptype = p.get("product_type", "")

            # Refund probability by product type
            if ptype == "Trainer":
                refund_prob = 0.22  # Weakness #3
            else:
                refund_prob = 0.08

            if rng.random() < refund_prob:
                refund_counter += 1
                rid = f"ref_{refund_counter:06d}"

                # Refund timing: 7-30 days after order
                delay = int(rng.uniform(7, 30))
                order_date = date.fromisoformat(o["created_at"][:10])
                refund_date = order_date + timedelta(days=delay)
                if refund_date > end_date:
                    continue

                # Refund amount = line item price (net)
                refund_amount = config.quantize(
                    Decimal(li["price"]) * int(li["quantity"]))

                # Add tax portion for UK orders
                if Decimal(o["total_tax"]) > 0 and Decimal(o["subtotal"]) > 0:
                    tax_ratio = Decimal(o["total_tax"]) / (
                        Decimal(o["subtotal"]) - Decimal(o["total_discounts"])
                        + Decimal(o["total_shipping"]))
                    refund_amount += config.quantize(refund_amount * tax_ratio)

                # Refund reason
                if ptype == "Trainer":
                    reason = rng.choice(["size_too_small", "size_too_large"],
                                        p=[0.55, 0.45])
                else:
                    reason = rng.choice([
                        "size_too_small", "size_too_large", "not_as_described",
                        "quality_issue", "changed_mind", "damaged_in_transit"
                    ], p=[0.15, 0.15, 0.15, 0.15, 0.25, 0.15])

                refunds.append({
                    "refund_id": rid,
                    "order_id": oid,
                    "created_at": f"{refund_date.isoformat()}T12:00:00",
                    "amount": str(refund_amount),
                    "reason": reason,
                    "refund_line_items": f'["{vid}"]',
                })
                break  # One refund per order max

    return refunds


def _rand_time(rng):
    """Generate a random time string HH:MM:SS."""
    h = int(rng.uniform(8, 23))
    m = int(rng.uniform(0, 60))
    s = int(rng.uniform(0, 60))
    return f"{h:02d}:{m:02d}:{s:02d}"


def _black_friday(year):
    """Return Black Friday date for a given year (4th Thursday of November + 1)."""
    nov1 = date(year, 11, 1)
    # Find first Thursday
    first_thu = nov1 + timedelta(days=(3 - nov1.weekday()) % 7)
    # 4th Thursday
    fourth_thu = first_thu + timedelta(weeks=3)
    return fourth_thu + timedelta(days=1)  # Friday


def _make_address(customer_id, first, last, country, rng):
    """Generate a shipping address."""
    if country == "GB":
        pc = rng.choice(config.UK_POSTCODES)
        return {
            "customer_id": customer_id,
            "first_name": first,
            "last_name": last,
            "address1": f"{rng.integers(1, 200)} {rng.choice(['High St', 'Church Rd', 'Station Rd', 'Park Lane', 'Victoria St', 'King St', 'Queen St', 'Mill Lane', 'Green Lane', 'Manor Rd'])}",
            "address2": "",
            "city": "London",
            "province": "",
            "postcode": pc,
            "country": "GB",
        }
    elif country in ("FR", "DE", "NL", "IE", "ES", "IT"):
        city_info = rng.choice(config.EU_CITIES)
        return {
            "customer_id": customer_id,
            "first_name": first,
            "last_name": last,
            "address1": f"{rng.integers(1, 200)} Rue Example",
            "address2": "",
            "city": city_info[0],
            "province": "",
            "postcode": city_info[1],
            "country": city_info[2],
        }
    else:
        city_info = rng.choice(config.US_CITIES)
        return {
            "customer_id": customer_id,
            "first_name": first,
            "last_name": last,
            "address1": f"{rng.integers(1, 999)} Broadway",
            "address2": "",
            "city": city_info[0],
            "province": city_info[2],
            "postcode": city_info[1],
            "country": "US",
        }
