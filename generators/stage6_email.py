"""
Stage 6: Email campaigns and email events (Klaviyo-style).
Attribution must reconcile with orders utm_source='klaviyo'.
"""

from decimal import Decimal
from datetime import date, timedelta
from collections import defaultdict
from . import config


# Campaign templates (flows are automated, campaigns are one-off)
FLOW_TEMPLATES = [
    ("Welcome_Flow", "flow"),
    ("Abandoned_Cart", "flow"),
    ("Win_Back", "flow"),
    ("Restock_Alert", "flow"),
]

# One-off campaigns tied to drops
DROP_CAMPAIGN_NAMES = [
    "Drop_Announcement",
]


def generate(cfg, prior_data):
    rng = config.make_rng(config.SEED + 6)
    start_date, end_date = cfg["start_date"], cfg["end_date"]
    orders = prior_data["orders"]
    customers = prior_data["customers"]

    # Count klaviyo-attributed orders by utm_campaign
    kl_orders = defaultdict(list)
    for o in orders:
        if (o.get("utm_source") or "").lower() == "klaviyo":
            camp = (o.get("utm_campaign") or "").strip()
            if camp:
                kl_orders[camp].append(o)

    # Determine all campaign names referenced in orders
    all_camp_names = set(kl_orders.keys())

    # Ensure we have flows + any drop announcements
    for name, _ in FLOW_TEMPLATES:
        all_camp_names.add(name)

    # Add womens flow if womens orders exist
    has_womens = any(o.get("utm_campaign") == "Womens_Welcome_Flow" for o in orders)
    if has_womens:
        all_camp_names.add("Womens_Welcome_Flow")

    # Build email campaigns
    campaigns = []
    events = []
    camp_counter = 0
    event_counter = 0

    # Customer list for event generation
    cust_accepts = {c["customer_id"] for c in customers
                    if c.get("accepts_marketing") == "true"}
    list_size = len(cust_accepts)

    for camp_name in sorted(all_camp_names):
        camp_counter += 1
        cid = f"ec_{camp_counter:04d}"

        # Determine type
        is_flow = any(camp_name == ft[0] for ft in FLOW_TEMPLATES)
        is_flow = is_flow or camp_name == "Womens_Welcome_Flow"
        camp_type = "flow" if is_flow else "campaign"

        # Attribution from orders
        attributed = kl_orders.get(camp_name, [])
        attributed_orders = len(attributed)
        attributed_revenue = sum(Decimal(o["total_price"]) for o in attributed)

        # Estimate recipients and engagement
        if is_flow:
            recipients = max(attributed_orders * 8, int(list_size * 0.3))
        else:
            recipients = max(attributed_orders * 6, int(list_size * 0.5))

        # Womens flows: higher engagement (Weakness #4 from original — now just
        # visible in sanity report as strong email engagement)
        if "Womens" in camp_name or "womens" in camp_name.lower():
            open_rate = rng.uniform(0.35, 0.42)
            click_rate = rng.uniform(0.06, 0.10)
        else:
            open_rate = rng.uniform(0.22, 0.28)
            click_rate = rng.uniform(0.025, 0.045)

        opens = int(recipients * open_rate)
        clicks = int(recipients * click_rate)
        unsubs = int(recipients * rng.uniform(0.001, 0.005))

        # Sent date
        if is_flow:
            sent_at = ""
        else:
            sent_at = f"{start_date.isoformat()}T10:00:00"

        campaigns.append({
            "campaign_id": cid,
            "name": camp_name,
            "type": camp_type,
            "sent_at": sent_at,
            "recipients": recipients,
            "opens": opens,
            "clicks": clicks,
            "unsubscribes": unsubs,
            "attributed_orders": attributed_orders,
            "attributed_revenue_gbp": str(config.quantize(attributed_revenue)),
        })

        # Generate email events
        cust_list = list(cust_accepts)
        if len(cust_list) == 0:
            continue

        # Generate sent events for a sample of customers
        n_sent = min(recipients, len(cust_list))
        sent_custs = rng.choice(cust_list, size=n_sent, replace=False)

        for sc in sent_custs[:min(n_sent, 500)]:  # Cap events per campaign
            event_counter += 1
            events.append({
                "event_id": f"ee_{event_counter:07d}",
                "campaign_id": cid,
                "customer_id": sc,
                "event_type": "sent",
                "timestamp": f"{start_date.isoformat()}T10:00:00",
            })

            # Opens
            if rng.random() < open_rate:
                event_counter += 1
                events.append({
                    "event_id": f"ee_{event_counter:07d}",
                    "campaign_id": cid,
                    "customer_id": sc,
                    "event_type": "opened",
                    "timestamp": f"{start_date.isoformat()}T{10 + int(rng.uniform(0, 12)):02d}:00:00",
                })

                # Clicks (subset of opens)
                if rng.random() < (click_rate / max(open_rate, 0.01)):
                    event_counter += 1
                    events.append({
                        "event_id": f"ee_{event_counter:07d}",
                        "campaign_id": cid,
                        "customer_id": sc,
                        "event_type": "clicked",
                        "timestamp": f"{start_date.isoformat()}T{10 + int(rng.uniform(0, 12)):02d}:30:00",
                    })

        # Converted events for attributed orders
        for o in attributed:
            event_counter += 1
            events.append({
                "event_id": f"ee_{event_counter:07d}",
                "campaign_id": cid,
                "customer_id": o["customer_id"],
                "event_type": "converted",
                "timestamp": o["created_at"],
            })

    return {
        "email_campaigns": campaigns,
        "email_events": events,
    }
