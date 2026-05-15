"""
Stage 1: Products, variants, collections, product_collections, suppliers.
Generated for the full catalogue regardless of --months.
"""

from decimal import Decimal
from . import config


# Drop calendar: (collection_name, launch_date, product_defs)
# product_defs: list of (title, product_type, gender, price, colours, sizes_override)
DROPS = [
    ("Core", "2024-06-01", [
        ("Essential Tee", "Tee", "mens", Decimal("50"), ["Washed Black", "Vintage Cream", "Charcoal"], None),
        ("Classic Hoodie", "Hoodie", "mens", Decimal("155"), ["Washed Black", "Deep Navy", "Charcoal"], None),
        ("Everyday Sweatpants", "Sweatpants", "mens", Decimal("135"), ["Charcoal", "Faded Olive"], None),
        ("Logo Cap", "Cap", "mens", Decimal("45"), ["Washed Black", "Vintage Cream", "Deep Navy"], ["ONE"]),
        ("Court Trainer", "Trainer", "mens", Decimal("195"), ["Off-White", "Washed Black"], config.TRAINER_SIZES),
        ("Staple Tee", "Tee", "mens", Decimal("48"), ["Off-White", "Sage", "Deep Navy"], None),
        ("Relaxed Hoodie", "Hoodie", "mens", Decimal("160"), ["Faded Olive", "Burgundy", "Off-White"], None),
        ("Slim Sweatpants", "Sweatpants", "mens", Decimal("140"), ["Washed Black", "Deep Navy"], None),
        ("Arch Logo Tee", "Tee", "mens", Decimal("52"), ["Washed Black", "Vintage Cream"], None),
        ("Heavyweight Hoodie", "Hoodie", "mens", Decimal("170"), ["Charcoal", "Washed Black"], None),
        ("Script Cap", "Cap", "mens", Decimal("42"), ["Charcoal", "Faded Olive", "Burgundy"], ["ONE"]),
        ("Heritage Tee", "Tee", "mens", Decimal("55"), ["Deep Navy", "Washed Black", "Vintage Cream"], None),
        ("Utility Sweatpants", "Sweatpants", "mens", Decimal("145"), ["Sage", "Charcoal"], None),
        ("Emblem Cap", "Cap", "mens", Decimal("48"), ["Washed Black", "Off-White", "Sage"], ["ONE"]),
        ("Track Hoodie", "Hoodie", "mens", Decimal("150"), ["Washed Black", "Vintage Cream"], None),
    ]),
    ("Summer 24", "2024-06-03", [
        ("Washed Logo Tee", "Tee", "mens", Decimal("52"), ["Vintage Cream", "Faded Olive", "Sage"], None),
        ("Mesh Panel Cap", "Cap", "mens", Decimal("44"), ["Washed Black", "Off-White", "Deep Navy"], ["ONE"]),
        ("Boxy Crop Tee", "Tee", "mens", Decimal("48"), ["Washed Black", "Vintage Cream"], None),
        ("Linen Blend Tee", "Tee", "mens", Decimal("58"), ["Off-White", "Sage"], None),
        ("Summer Knit Hoodie", "Hoodie", "mens", Decimal("145"), ["Faded Olive", "Vintage Cream"], None),
        ("Boardshort Sweatpants", "Sweatpants", "mens", Decimal("130"), ["Charcoal", "Sage"], None),
    ]),
    ("Autumn 24", "2024-09-02", [
        ("Fleece Hoodie", "Hoodie", "mens", Decimal("165"), ["Washed Black", "Burgundy", "Deep Navy"], None),
        ("Brushed Sweatpants", "Sweatpants", "mens", Decimal("150"), ["Charcoal", "Faded Olive"], None),
        ("Varsity Tee", "Tee", "mens", Decimal("55"), ["Washed Black", "Vintage Cream", "Burgundy"], None),
        ("Wool Blend Cap", "Cap", "mens", Decimal("52"), ["Charcoal", "Deep Navy", "Burgundy"], ["ONE"]),
        ("Mid Runner Trainer", "Trainer", "mens", Decimal("210"), ["Charcoal", "Off-White"], config.TRAINER_SIZES),
        ("Quilted Overshirt", "Outerwear", "mens", Decimal("225"), ["Faded Olive", "Washed Black"], None),
    ]),
    ("Winter 24", "2024-11-15", [
        ("Puffer Jacket", "Outerwear", "mens", Decimal("295"), ["Washed Black", "Deep Navy"], None),
        ("Sherpa Hoodie", "Hoodie", "mens", Decimal("175"), ["Charcoal", "Vintage Cream"], None),
        ("Thermal Sweatpants", "Sweatpants", "mens", Decimal("155"), ["Washed Black", "Charcoal"], None),
        ("Winter Logo Tee", "Tee", "mens", Decimal("50"), ["Deep Navy", "Burgundy"], None),
    ]),
    ("Spring 25", "2025-02-24", [
        ("Garment Dyed Tee", "Tee", "mens", Decimal("55"), ["Sage", "Vintage Cream", "Faded Olive"], None),
        ("Zip Hoodie", "Hoodie", "mens", Decimal("165"), ["Washed Black", "Charcoal", "Off-White"], None),
        ("Cropped Sweatpants", "Sweatpants", "mens", Decimal("135"), ["Faded Olive", "Sage"], None),
        ("Cord Cap", "Cap", "mens", Decimal("46"), ["Burgundy", "Sage", "Charcoal"], ["ONE"]),
        ("Canvas Trainer", "Trainer", "mens", Decimal("185"), ["Off-White", "Sage"], config.TRAINER_SIZES),
    ]),
    ("Summer 25", "2025-06-02", [
        ("Resort Tee", "Tee", "mens", Decimal("52"), ["Off-White", "Vintage Cream"], None),
        ("Open Knit Hoodie", "Hoodie", "mens", Decimal("148"), ["Sage", "Faded Olive"], None),
        ("Tech Runner Trainer", "Trainer", "mens", Decimal("220"), ["Washed Black", "Off-White"], config.TRAINER_SIZES),
        ("Pigment Dyed Tee", "Tee", "mens", Decimal("56"), ["Charcoal", "Burgundy", "Sage"], None),
    ]),
    ("Autumn 25", "2025-09-01", [
        ("Heavy Fleece Hoodie", "Hoodie", "mens", Decimal("172"), ["Washed Black", "Deep Navy", "Burgundy"], None),
        ("Cargo Sweatpants", "Sweatpants", "mens", Decimal("155"), ["Washed Black", "Faded Olive"], None),
        ("Vintage Wash Tee", "Tee", "mens", Decimal("54"), ["Vintage Cream", "Charcoal", "Sage"], None),
        ("Wool Overcoat", "Outerwear", "mens", Decimal("345"), ["Charcoal", "Deep Navy"], None),
        ("Structured Cap", "Cap", "mens", Decimal("50"), ["Washed Black", "Charcoal", "Off-White"], ["ONE"]),
    ]),
    ("Womens Launch / Winter 25", "2025-12-01", [
        # Womens products
        ("Essential Relaxed Tee", "Tee", "womens", Decimal("48"), ["Vintage Cream", "Washed Black", "Sage"], config.WOMENS_APPAREL_SIZES),
        ("Womens Relaxed Hoodie", "Hoodie", "womens", Decimal("150"), ["Vintage Cream", "Burgundy", "Washed Black"], config.WOMENS_APPAREL_SIZES),
        ("Womens Wide-Leg Sweatpant", "Sweatpants", "womens", Decimal("130"), ["Charcoal", "Sage", "Vintage Cream"], config.WOMENS_APPAREL_SIZES),
        ("Womens Logo Cap", "Cap", "womens", Decimal("42"), ["Washed Black", "Vintage Cream", "Sage"], ["ONE"]),
        ("Womens Cropped Hoodie", "Hoodie", "womens", Decimal("145"), ["Washed Black", "Off-White"], config.WOMENS_APPAREL_SIZES),
        ("Womens Fitted Tee", "Tee", "womens", Decimal("46"), ["Deep Navy", "Vintage Cream", "Off-White"], config.WOMENS_APPAREL_SIZES),
        ("Womens Boxy Tee", "Tee", "womens", Decimal("50"), ["Charcoal", "Sage"], config.WOMENS_APPAREL_SIZES),
        ("Womens Mini Sweatpant", "Sweatpants", "womens", Decimal("125"), ["Washed Black", "Faded Olive"], config.WOMENS_APPAREL_SIZES),
        # Mens winter additions
        ("Down Puffer Vest", "Outerwear", "mens", Decimal("265"), ["Washed Black", "Deep Navy"], None),
        ("Fleece Lined Sweatpants", "Sweatpants", "mens", Decimal("158"), ["Charcoal", "Washed Black"], None),
        ("Holiday Graphic Tee", "Tee", "mens", Decimal("52"), ["Washed Black", "Vintage Cream", "Deep Navy"], None),
        ("Beanie Cap", "Cap", "mens", Decimal("35"), ["Washed Black", "Charcoal", "Burgundy"], ["ONE"]),
    ]),
    ("Spring 26", "2026-02-23", [
        ("Pastel Tee", "Tee", "mens", Decimal("50"), ["Sage", "Off-White"], None),
        ("Spring Zip Hoodie", "Hoodie", "mens", Decimal("158"), ["Vintage Cream", "Faded Olive"], None),
        ("Womens Spring Tee", "Tee", "womens", Decimal("48"), ["Sage", "Vintage Cream", "Off-White"], config.WOMENS_APPAREL_SIZES),
        ("Womens Relaxed Sweatpant", "Sweatpants", "womens", Decimal("128"), ["Charcoal", "Vintage Cream"], config.WOMENS_APPAREL_SIZES),
        ("Light Parka", "Outerwear", "mens", Decimal("235"), ["Faded Olive", "Deep Navy"], None),
    ]),
]

SUPPLIERS = [
    {"supplier_id": "sup_001", "name": "Porto Knit Co.", "country": "Portugal",
     "payment_terms": "50% deposit / 50% on shipment", "lead_time_days": 60,
     "currency": "EUR", "categories": ["Tee", "Hoodie", "Sweatpants"]},
    {"supplier_id": "sup_002", "name": "Milano Trims SRL", "country": "Italy",
     "payment_terms": "50% deposit / 50% on shipment", "lead_time_days": 75,
     "currency": "EUR", "categories": ["Cap", "Outerwear"]},
    {"supplier_id": "sup_003", "name": "Lisbon Garment Works", "country": "Portugal",
     "payment_terms": "50% deposit / 50% on shipment", "lead_time_days": 55,
     "currency": "EUR", "categories": ["Tee", "Sweatpants"]},
    {"supplier_id": "sup_004", "name": "Anatolian Textile Ltd", "country": "Turkey",
     "payment_terms": "Net 60", "lead_time_days": 45,
     "currency": "USD", "categories": ["Tee"]},
    {"supplier_id": "sup_005", "name": "Iberia Footwear SA", "country": "Portugal",
     "payment_terms": "50% deposit / 50% on shipment", "lead_time_days": 90,
     "currency": "EUR", "categories": ["Trainer"]},
]


def generate(cfg_unused=None, prior_data=None):
    products = []
    variants = []
    collections = []
    product_collections = []

    prod_counter = 0
    var_counter = 0
    coll_counter = 0

    # Category -> supplier mapping (first match)
    cat_supplier = {}
    for s in SUPPLIERS:
        for cat in s["categories"]:
            if cat not in cat_supplier:
                cat_supplier[cat] = s["supplier_id"]

    for coll_name, launch_date, product_defs in DROPS:
        coll_counter += 1
        coll_id = f"coll_{coll_counter:04d}"
        collections.append({
            "collection_id": coll_id,
            "title": coll_name,
            "created_at": f"{launch_date}T00:00:00",
        })

        for title, ptype, gender, price, colours, sizes_override in product_defs:
            prod_counter += 1
            pid = f"prod_{prod_counter:05d}"

            # Determine sizes
            if sizes_override:
                sizes = sizes_override
            elif gender == "womens":
                sizes = config.WOMENS_APPAREL_SIZES
            else:
                sizes = config.APPAREL_SIZES

            # Build handle
            handle = title.lower().replace(" ", "-").replace("'", "")

            # Brand-voiced description
            desc = _product_description(title, ptype, gender)

            # Tags
            drop_tag = coll_name.lower().replace(" ", "_").replace("/", "_")
            tags = [
                f"drop:{drop_tag}",
                f"category:{ptype.lower()}",
                f"gender:{gender}",
            ]

            products.append({
                "product_id": pid,
                "title": title,
                "handle": handle,
                "description": desc,
                "product_type": ptype,
                "vendor": "Pretty Fly",
                "collection": coll_name,
                "gender_segment": gender,
                "tags": str(tags),
                "status": "active",
                "created_at": f"{launch_date}T00:00:00",
            })

            product_collections.append({
                "product_id": pid,
                "collection_id": coll_id,
            })

            # Generate variants
            for colour in colours:
                for size in sizes:
                    var_counter += 1
                    vid = f"var_{var_counter:06d}"

                    # SKU: PF-[W-]TYPE-TITLE_ABBR-COLOUR_ABBR-SIZE
                    gender_prefix = "W-" if gender == "womens" else ""
                    type_abbr = ptype[:4].upper()
                    title_abbr = "".join(w[0:3].upper() for w in title.split()[:2])
                    colour_abbr = colour[:3].upper()
                    size_str = size.replace(" ", "")
                    sku = f"PF-{gender_prefix}{type_abbr}-{title_abbr}-{colour_abbr}-{size_str}"

                    # Barcode (12-digit EAN-like)
                    barcode = f"5{var_counter:011d}"

                    # Weight
                    weight = _weight_for_type(ptype)

                    variants.append({
                        "variant_id": vid,
                        "product_id": pid,
                        "sku": sku,
                        "option1_name": "Size",
                        "option1_value": size,
                        "option2_name": "Colour",
                        "option2_value": colour,
                        "price": str(price),
                        "compare_at_price": "",
                        "barcode": barcode,
                        "weight_grams": weight,
                        "inventory_quantity": 0,  # Will be set by stage 5
                    })

    suppliers = []
    for s in SUPPLIERS:
        suppliers.append({
            "supplier_id": s["supplier_id"],
            "name": s["name"],
            "country": s["country"],
            "payment_terms": s["payment_terms"],
            "lead_time_days": s["lead_time_days"],
            "currency": s["currency"],
        })

    return {
        "products": products,
        "variants": variants,
        "collections": collections,
        "product_collections": product_collections,
        "suppliers": suppliers,
    }


def _product_description(title, ptype, gender):
    """Generate brand-voiced product copy."""
    descs = {
        "Tee": "Cut from heavyweight 240gsm cotton. Relaxed fit, ribbed collar, "
               "woven label at back neck. The one you'll reach for every time.",
        "Hoodie": "Brushed-back 400gsm French terry. Oversized fit, kangaroo pocket, "
                  "flat-cord drawstring. Looks better lived in.",
        "Sweatpants": "Same 400gsm French terry as the hoodies. Elasticated waist, "
                      "tapered leg, side pockets deep enough for your phone and your pride.",
        "Cap": "Six-panel construction, curved brim, adjustable strap. "
               "Embroidered logo. Sits right on day one.",
        "Trainer": "Full-grain leather upper, chunky rubber sole, padded collar. "
                   "Handmade in Portugal. Breaks in, never breaks down.",
        "Outerwear": "Premium outerwear built for London weather and everywhere else. "
                     "Technical fabrics, considered details, no compromise.",
    }
    return descs.get(ptype, f"{title}. Premium streetwear, made properly.")


def _weight_for_type(ptype):
    weights = {
        "Tee": 280, "Hoodie": 650, "Sweatpants": 520,
        "Cap": 120, "Trainer": 850, "Outerwear": 900,
    }
    return weights.get(ptype, 400)
