"""
Shared configuration, constants, and helpers for Pretty Fly data generation.
All monetary values use Decimal. Single random seed controls all randomness.
"""

from decimal import Decimal, ROUND_HALF_UP
from datetime import date, datetime, timedelta
import numpy as np

SEED = 42
DATASET_START = date(2024, 6, 1)
DATASET_END = date(2026, 5, 31)
WOMENS_LAUNCH = date(2025, 12, 1)
OPENING_BANK_BALANCE = Decimal("400000.00")
CURRENCY = "GBP"
ORDER_NUMBER_START = 1001

# VAT
UK_VAT_RATE = Decimal("0.20")
UK_VAT_DIVISOR = Decimal("1.20")  # prices are VAT-inclusive; net = price / 1.20

# Shopify
SHOPIFY_PAYMENT_FEE_RATE = Decimal("0.02")  # 2% of total_price
SHOPIFY_SUBSCRIPTION = Decimal("79.00")

# Market mix (probability of order being from each market)
MARKET_WEIGHTS = {"UK": 0.75, "EU": 0.15, "US": 0.10}
MARKET_COUNTRIES = {
    "UK": ["GB"],
    "EU": ["FR", "DE", "NL", "IE", "ES", "IT"],
    "US": ["US"],
}

# Shipping
FREE_SHIPPING_THRESHOLD = Decimal("75.00")  # net subtotal
SHIPPING_RATES = {
    "UK": Decimal("4.95"),
    "EU": Decimal("9.95"),
    "US": Decimal("12.95"),
}

# FX rates (base, used for supplier payments)
FX_EUR_GBP_BASE = Decimal("0.86")
FX_USD_GBP_BASE = Decimal("0.79")

# Product category margins (landed cost as fraction of VAT-inclusive retail)
CATEGORY_COST_FRACTIONS = {
    "Tee": Decimal("0.40"),
    "Hoodie": Decimal("0.38"),
    "Sweatpants": Decimal("0.55"),
    "Cap": Decimal("0.58"),
    "Trainer": Decimal("0.43"),
    "Outerwear": Decimal("0.40"),
}

# Revenue share targets (product selection weights)
CATEGORY_REVENUE_WEIGHTS = {
    "Tee": 0.28,
    "Hoodie": 0.32,
    "Sweatpants": 0.13,
    "Cap": 0.04,
    "Trainer": 0.13,
    "Outerwear": 0.10,
}

# Monthly seasonality multipliers (1-indexed: 1=Jan ... 12=Dec)
SEASONALITY = {
    1: 1.05, 2: 0.85, 3: 1.00, 4: 1.00, 5: 0.95, 6: 0.90,
    7: 0.80, 8: 0.85, 9: 1.05, 10: 1.00, 11: 1.30, 12: 1.10,
}

# Colourways
COLOURWAYS = [
    "Washed Black", "Vintage Cream", "Faded Olive", "Charcoal",
    "Off-White", "Deep Navy", "Burgundy", "Sage",
]

# Sizes
APPAREL_SIZES = ["XS", "S", "M", "L", "XL"]
WOMENS_APPAREL_SIZES = ["XS", "S", "M", "L"]
TRAINER_SIZES = ["UK6", "UK7", "UK8", "UK9", "UK10", "UK11", "UK12"]
# Note: spec says UK 6-12 but that's 7 sizes; spec says ~8 sizes, close enough

# Discount codes
DISCOUNT_CODES = [
    {"code": "WELCOME10", "type": "percentage", "value": Decimal("10"),
     "starts_at": "2024-06-01", "ends_at": "2026-05-31"},
    {"code": "SUMMER24", "type": "percentage", "value": Decimal("15"),
     "starts_at": "2024-06-01", "ends_at": "2024-08-31"},
    {"code": "AUTUMN24", "type": "percentage", "value": Decimal("15"),
     "starts_at": "2024-09-01", "ends_at": "2024-11-15"},
    {"code": "BLACKFRIDAY20", "type": "percentage", "value": Decimal("20"),
     "starts_at": "2024-11-25", "ends_at": "2024-12-02"},
    {"code": "PRETTYNEW", "type": "fixed_amount", "value": Decimal("10"),
     "starts_at": "2024-06-01", "ends_at": "2026-05-31"},
    {"code": "NEWYEAR15", "type": "percentage", "value": Decimal("15"),
     "starts_at": "2025-01-01", "ends_at": "2025-01-15"},
    {"code": "WOMENSLAUNCH", "type": "percentage", "value": Decimal("10"),
     "starts_at": "2025-12-01", "ends_at": "2026-01-31"},
    {"code": "SPRING26", "type": "percentage", "value": Decimal("10"),
     "starts_at": "2026-02-15", "ends_at": "2026-04-30"},
]

# Recurring costs (monthly, for bank transactions)
RECURRING_COSTS = [
    ("SHOPIFY* SUB {ref}", SHOPIFY_SUBSCRIPTION),
    ("SQ *KLAVIYO INC {ref} DUB", None),  # variable, set per month
    ("INTERCOM INC SF CA {ref}", Decimal("199.00")),
    ("XERO LTD {ref}", Decimal("42.00")),
    ("NOTION LABS INC {ref}", Decimal("24.00")),
    ("FIGMA INC {ref}", Decimal("33.00")),
    ("MIXVIEW ANALYTICS LTD {ref}", Decimal("349.00")),
    ("STANDING ORDER STUDIO N1 LDN", Decimal("3200.00")),
]

# Diverse name pools for realistic London customer base
FIRST_NAMES_M = [
    "James", "Oliver", "Mohammed", "Kwame", "Liam", "Raj", "Tomasz", "Yusuf",
    "Daniel", "Samuel", "Wei", "Adebayo", "Patrick", "Ravi", "Jakub", "Tariq",
    "Marcus", "Chen", "Ade", "Nikolai", "Finn", "Kofi", "Arjun", "Eoin",
    "Stefan", "Idris", "Callum", "Hassan", "Dmitri", "Leo", "Jamal", "Emeka",
]
FIRST_NAMES_F = [
    "Sophie", "Amara", "Priya", "Fatima", "Chloe", "Aisha", "Ewa", "Yuki",
    "Grace", "Oluwaseun", "Mei", "Zara", "Isla", "Kamila", "Nneka", "Elena",
    "Nadia", "Suki", "Ama", "Freya", "Blessing", "Ananya", "Sienna", "Khadija",
    "Marta", "Chioma", "Aoife", "Layla", "Ingrid", "Rosa", "Damilola", "Nina",
]
LAST_NAMES = [
    "Smith", "Okafor", "Patel", "Nowak", "Jones", "Ahmed", "Garcia", "Kim",
    "Williams", "Osei", "Singh", "Kowalski", "Brown", "Hassan", "Rossi", "Chen",
    "Taylor", "Mensah", "Sharma", "Muller", "Davies", "Ibrahim", "Martinez", "Tanaka",
    "Wilson", "Adeyemi", "Gupta", "Larsson", "Thompson", "Ali", "Lopez", "Watanabe",
    "Evans", "Asante", "Kumar", "Nowicki", "Johnson", "Hussain", "Fernandez", "Park",
]

# UK postcodes for addresses
UK_POSTCODES = [
    "E1 6AN", "N1 7GU", "SE1 9SG", "SW1A 1AA", "W1D 3SE", "EC1V 9NQ",
    "E2 8DP", "N7 8NL", "SE15 5DQ", "SW6 1HS", "W11 2BQ", "EC2A 4NE",
    "E8 1HT", "NW1 8JR", "SE10 0DX", "SW11 3TN", "W4 5PY", "N16 8JH",
    "BR1 1LU", "CR0 1NR", "DA1 1DJ", "IG1 1AT", "KT1 1HN", "RM1 3AD",
    "M1 1AD", "LS1 4DY", "B1 1BB", "BS1 1EW", "EH1 1RE", "CF10 1EP",
]
EU_CITIES = [
    ("Paris", "75001", "FR"), ("Berlin", "10115", "DE"),
    ("Amsterdam", "1012", "NL"), ("Dublin", "D01", "IE"),
    ("Madrid", "28001", "ES"), ("Rome", "00100", "IT"),
]
US_CITIES = [
    ("New York", "10001", "NY"), ("Los Angeles", "90001", "CA"),
    ("Chicago", "60601", "IL"), ("Brooklyn", "11201", "NY"),
]


def D(value):
    """Convert to Decimal safely."""
    if value is None or str(value).strip() in ("", "null", "None"):
        return Decimal("0")
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def quantize(value):
    """Round a Decimal to 2 decimal places."""
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def net_price(vat_inclusive_price):
    """Extract VAT-exclusive net price from a VAT-inclusive price."""
    return quantize(Decimal(str(vat_inclusive_price)) / UK_VAT_DIVISOR)


def vat_amount(net_value):
    """Calculate VAT on a net value."""
    return quantize(Decimal(str(net_value)) * UK_VAT_RATE)


def make_rng(seed=SEED):
    """Create a numpy random generator with the given seed."""
    return np.random.default_rng(seed)


def date_range(start, months):
    """Return (start_date, end_date) for the generation window."""
    end = date(start.year + (start.month - 1 + months) // 12,
               (start.month - 1 + months) % 12 + 1, 1) - timedelta(days=1)
    # Cap at dataset end
    end = min(end, DATASET_END)
    return start, end


def months_in_range(start, end):
    """Yield (year, month) tuples for each month in [start, end]."""
    current = start.replace(day=1)
    while current <= end:
        yield current.year, current.month
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)
