"""
Stage 7: Support tickets and messages.
Tickets reference real orders/products. ~40% bot-resolved.
"""

import json
from decimal import Decimal
from datetime import timedelta, date
from collections import defaultdict
from . import config


# Category distribution
TICKET_CATEGORIES = [
    ("order_status", 0.30),
    ("sizing_fit", 0.20),
    ("returns_exchanges", 0.15),
    ("discount_code", 0.10),
    ("drop_restock", 0.10),
    ("product_quality", 0.10),
    ("other", 0.05),
]

CHANNELS = [("email", 0.50), ("chat", 0.35), ("instagram_dm", 0.15)]


def generate(cfg, prior_data):
    rng = config.make_rng(config.SEED + 7)
    start_date, end_date = cfg["start_date"], cfg["end_date"]
    orders = prior_data["orders"]
    products = prior_data["products"]
    customers = prior_data["customers"]

    # Target: ~50 tickets per month
    total_days = (end_date - start_date).days + 1
    total_months = max(1, total_days / 30)
    target_tickets = int(total_months * 50)

    prod_map = {p["product_id"]: p for p in products}
    cust_map = {c["customer_id"]: c for c in customers}

    tickets = []
    messages = []
    ticket_counter = 0

    # Spread tickets across orders
    if not orders:
        return {"support_tickets": tickets, "support_messages": messages}

    # Sample orders to generate tickets from
    n_tickets = min(target_tickets, len(orders))
    ticket_order_indices = rng.choice(len(orders), size=n_tickets, replace=False)

    for idx in ticket_order_indices:
        o = orders[idx]
        ticket_counter += 1
        tid = f"tkt_{ticket_counter:05d}"

        order_date = date.fromisoformat(o["created_at"][:10])
        # Ticket created 0-14 days after order
        delay = int(rng.uniform(0, 14))
        ticket_date = order_date + timedelta(days=delay)
        if ticket_date > end_date:
            continue

        # Channel
        channel = rng.choice([c[0] for c in CHANNELS],
                             p=[c[1] for c in CHANNELS])

        # Category
        cat_names = [c[0] for c in TICKET_CATEGORIES]
        cat_weights = [c[1] for c in TICKET_CATEGORIES]
        category = rng.choice(cat_names, p=cat_weights)

        # Priority
        priority = rng.choice(["low", "normal", "high"], p=[0.2, 0.6, 0.2])

        # Related product (from order's line items)
        related_product_id = ""
        olis = [li for li in prior_data["line_items"]
                if li["order_id"] == o["order_id"]]
        if olis:
            li = rng.choice(olis)
            related_product_id = li["product_id"]

        # Resolution
        is_bot = rng.random() < 0.40
        resolved_by = "bot" if is_bot else "human"
        status = "resolved" if rng.random() < 0.92 else "closed"

        # Timing
        first_response_mins = int(rng.uniform(30, 240))  # 30 min to 4 hours
        resolution_mins = int(rng.uniform(60, 1440))  # 1 hour to 24 hours
        if is_bot:
            first_response_mins = int(rng.uniform(1, 5))
            resolution_mins = int(rng.uniform(5, 30))

        first_response_at = f"{ticket_date.isoformat()}T{_offset_time(rng, first_response_mins)}"
        resolved_at = f"{ticket_date.isoformat()}T{_offset_time(rng, resolution_mins)}"

        # Satisfaction
        satisfaction = ""
        if rng.random() < 0.30:
            satisfaction = int(rng.choice([1, 2, 3, 4, 5], p=[0.05, 0.10, 0.20, 0.35, 0.30]))

        subject = _subject(category, related_product_id, prod_map, rng)

        tickets.append({
            "ticket_id": tid,
            "customer_id": o["customer_id"],
            "created_at": f"{ticket_date.isoformat()}T{_rand_time(rng)}",
            "channel": channel,
            "status": status,
            "priority": priority,
            "category": category,
            "subject": subject,
            "related_order_id": o["order_id"],
            "related_product_id": related_product_id,
            "first_response_at": first_response_at,
            "resolved_at": resolved_at,
            "resolution_time_minutes": resolution_mins,
            "satisfaction_rating": str(satisfaction) if satisfaction else "",
            "resolved_by": resolved_by,
        })

        # Generate conversation messages
        cust = cust_map.get(o["customer_id"], {})
        cust_name = f"{cust.get('first_name', 'Customer')} {cust.get('last_name', '')}"
        msg_thread = _generate_messages(
            tid, category, o, related_product_id, prod_map,
            cust_name, is_bot, ticket_date, rng
        )
        messages.append({
            "ticket_id": tid,
            "messages": msg_thread,
        })

    return {
        "support_tickets": tickets,
        "support_messages": messages,
    }


def _subject(category, product_id, prod_map, rng):
    """Generate a realistic ticket subject line."""
    product = prod_map.get(product_id, {})
    pname = product.get("title", "my order")

    subjects = {
        "order_status": [
            "Where's my order?", "Tracking not updating",
            f"No delivery update for {pname}", "Order hasn't arrived",
        ],
        "sizing_fit": [
            f"Sizing question about {pname}", f"Is the {pname} true to size?",
            f"{pname} doesn't fit right", "Size exchange needed",
        ],
        "returns_exchanges": [
            "How do I return?", f"Want to return {pname}",
            "Return label not working", "Exchange for different size",
        ],
        "discount_code": [
            "Discount code not working", "Code expired before I could use it",
            "Can I get a code?", "Applied wrong code",
        ],
        "drop_restock": [
            f"When will {pname} restock?", "Restock notification",
            "Will there be more sizes?", "Next drop date?",
        ],
        "product_quality": [
            f"Issue with {pname} quality", "Stitching coming loose",
            "Colour faded after wash", "Print peeling",
        ],
        "other": [
            "General enquiry", "Question about your brand",
            "Collaboration enquiry", "Gift wrapping?",
        ],
    }
    options = subjects.get(category, ["Question about my order"])
    return rng.choice(options)


def _generate_messages(tid, category, order, product_id, prod_map,
                        cust_name, is_bot, ticket_date, rng):
    """Generate a realistic conversation thread."""
    product = prod_map.get(product_id, {})
    pname = product.get("title", "the item")
    oid = order["order_id"]
    tracking = f"PF{rng.integers(100000, 999999)}"

    msgs = []
    msg_counter = 0
    base_time = f"{ticket_date.isoformat()}T{10 + int(rng.uniform(0, 8)):02d}"

    # Customer opening message
    msg_counter += 1
    customer_msg = _customer_opening(category, pname, oid, rng)
    msgs.append({
        "message_id": f"{tid}_msg_{msg_counter:02d}",
        "sender": "customer",
        "sender_name": cust_name,
        "timestamp": f"{base_time}:00:00",
        "body": customer_msg,
    })

    # Bot response
    msg_counter += 1
    bot_msg = _bot_response(category, oid, tracking, rng)
    msgs.append({
        "message_id": f"{tid}_msg_{msg_counter:02d}",
        "sender": "bot",
        "sender_name": None,
        "timestamp": f"{base_time}:02:00",
        "body": bot_msg,
    })

    if is_bot:
        # Bot resolves
        msg_counter += 1
        msgs.append({
            "message_id": f"{tid}_msg_{msg_counter:02d}",
            "sender": "customer",
            "sender_name": cust_name,
            "timestamp": f"{base_time}:10:00",
            "body": rng.choice([
                "That's sorted it, thanks!", "Perfect, cheers.",
                "All good now, thank you.", "Got it, ta!",
            ]),
        })
    else:
        # Escalate to human
        msg_counter += 1
        msgs.append({
            "message_id": f"{tid}_msg_{msg_counter:02d}",
            "sender": "customer",
            "sender_name": cust_name,
            "timestamp": f"{base_time}:15:00",
            "body": rng.choice([
                "That doesn't help, can I speak to someone?",
                "I need more help with this please.",
                "Still not resolved, can a person look at this?",
            ]),
        })

        msg_counter += 1
        agent_name = rng.choice(["Alex M.", "Jordan K.", "Sam T.", "Charlie D."])
        msgs.append({
            "message_id": f"{tid}_msg_{msg_counter:02d}",
            "sender": "agent",
            "sender_name": agent_name,
            "timestamp": f"{base_time}:45:00",
            "body": _agent_response(category, pname, oid, tracking, rng),
        })

        msg_counter += 1
        msgs.append({
            "message_id": f"{tid}_msg_{msg_counter:02d}",
            "sender": "customer",
            "sender_name": cust_name,
            "timestamp": f"{base_time}:55:00",
            "body": rng.choice([
                "Brilliant, thanks for sorting that.",
                "Great, appreciate the help.",
                "That's perfect, thank you!",
                "Lovely, cheers for that.",
            ]),
        })

    return msgs


def _customer_opening(category, pname, oid, rng):
    """Generate a realistic customer opening message."""
    msgs = {
        "order_status": [
            f"Hi, I ordered {pname} (order {oid}) and it's been ages with no update. Can you check?",
            f"My tracking for order {oid} hasn't moved in days. What's going on?",
            f"Hiya, any idea when order {oid} will arrive? Been waiting a while now.",
        ],
        "sizing_fit": [
            f"Hey, I'm looking at the {pname} — I'm usually a medium but your stuff can run big. What size should I go for?",
            f"The {pname} I got in order {oid} is way too small. Do your sizes run small?",
            f"Quick question — is the {pname} true to size? I'm between sizes and don't want to get it wrong.",
        ],
        "returns_exchanges": [
            f"Need to return the {pname} from order {oid}. How do I do that?",
            f"Hi, the {pname} doesn't work for me — can I exchange for a different size?",
        ],
        "discount_code": [
            "I've got a code but it's saying invalid at checkout. Can you help?",
            f"Tried to use my discount on the {pname} but it won't apply.",
        ],
        "drop_restock": [
            f"When is the {pname} coming back in stock? I missed it last time.",
            "Any idea when the next drop is? Need to plan my purchase.",
        ],
        "product_quality": [
            f"My {pname} from order {oid} has a loose thread after one wear. Not happy.",
            f"The print on my {pname} is already peeling and I've barely worn it.",
        ],
        "other": [
            "Hi there, got a general question about your returns policy.",
            "Do you do gift cards? Want to get one for my mate.",
        ],
    }
    options = msgs.get(category, [f"Question about order {oid}"])
    return rng.choice(options)


def _bot_response(category, oid, tracking, rng):
    """Generate a bot triage response."""
    msgs = {
        "order_status": [
            f"Hi! I've found order {oid}. Your tracking reference is {tracking}. "
            "Delivery is currently on schedule. You can track your parcel at "
            "royalmail.com/track. Is there anything else I can help with?",
        ],
        "sizing_fit": [
            "Thanks for getting in touch! Our sizing guide is at prettyfly.com/sizing. "
            "Generally our pieces are designed for a relaxed fit. "
            "Would you like me to connect you with our styling team for specific advice?",
        ],
        "returns_exchanges": [
            "I can help with that! You can start a return at prettyfly.com/returns. "
            "Returns are free within 30 days of delivery for UK orders. "
            "Would you like me to generate a return label?",
        ],
        "discount_code": [
            "Let me look into that for you. Could you confirm the exact code "
            "you're trying to use and what's in your basket?",
        ],
        "drop_restock": [
            "Thanks for your interest! I don't have specific restock dates but "
            "you can sign up for notifications at the product page. "
            "Is there anything else I can help with?",
        ],
        "product_quality": [
            "I'm sorry to hear that. We take quality seriously and want to make "
            "this right. Let me connect you with our team who can sort this out.",
        ],
        "other": [
            "Hi there! Thanks for reaching out. Let me see how I can help.",
        ],
    }
    options = msgs.get(category, ["Thanks for contacting Pretty Fly support!"])
    return rng.choice(options)


def _agent_response(category, pname, oid, tracking, rng):
    """Generate a human agent response."""
    return rng.choice([
        f"Hey, I've had a look at order {oid} and I can see what's happened. "
        f"I've sorted this for you — you should get a confirmation email shortly.",
        f"Hi there, thanks for your patience. I've reviewed the {pname} from "
        f"order {oid} and I've processed this for you. Let me know if "
        f"you need anything else!",
        f"No worries, I've taken care of this. For order {oid}, I've "
        f"[updated the tracking / arranged a replacement / issued a refund]. "
        f"You'll get an email confirming everything.",
    ])


def _rand_time(rng):
    h = int(rng.uniform(8, 22))
    m = int(rng.uniform(0, 60))
    s = int(rng.uniform(0, 60))
    return f"{h:02d}:{m:02d}:{s:02d}"


def _offset_time(rng, minutes_offset):
    h = 10 + minutes_offset // 60
    m = minutes_offset % 60
    if h > 23:
        h = 23
    return f"{h:02d}:{m:02d}:00"
