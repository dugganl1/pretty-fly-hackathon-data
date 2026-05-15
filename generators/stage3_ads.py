"""
Stage 3: Google Ads and Meta Ads daily data.
Generates daily ad performance for the reporting window.
"""

from decimal import Decimal
from datetime import date, timedelta
from . import config


# Google campaigns (name, type, monthly_spend_range, roas_target)
GOOGLE_CAMPAIGNS = [
    ("Brand_Search_UK", "search", (1500, 2500), 5.0),
    ("Brand_Search_EU", "search", (400, 800), 4.0),
    ("Shopping_Hoodies_UK", "shopping", (1200, 2000), 3.5),
    ("Shopping_Tees_UK", "shopping", (800, 1500), 3.8),
    ("Shopping_All_EU", "shopping", (500, 900), 3.0),
    ("Generic_Streetwear_UK", "search", (700, 900), 1.2),  # Weakness #2
    ("PMax_Menswear_UK", "pmax", (2000, 3500), 3.5),
]

# Meta campaigns (name, objective, monthly_spend_range, roas_target, placement_weights)
META_CAMPAIGNS = [
    ("Prospecting_Mens_UK", "conversions", (2500, 4000), 3.0,
     {"instagram_feed": 0.4, "facebook_feed": 0.3, "instagram_stories": 0.2, "reels": 0.1}),
    ("Prospecting_Mens_EU", "conversions", (800, 1500), 2.5,
     {"instagram_feed": 0.4, "facebook_feed": 0.3, "instagram_stories": 0.2, "reels": 0.1}),
    ("Retargeting_AllUsers", "conversions", (1000, 2000), 5.0,
     {"instagram_feed": 0.3, "facebook_feed": 0.4, "instagram_stories": 0.2, "reels": 0.1}),
    ("Brand_Awareness_UK", "awareness", (500, 1000), 0.0,
     {"instagram_feed": 0.3, "reels": 0.4, "instagram_stories": 0.3}),
]

# Womens Meta campaign (starts Dec 2025) — Weakness #1
WOMENS_META_CAMPAIGN = (
    "Womens_Launch_Prospecting", "conversions", (4000, 6000), 1.0,
    {"instagram_feed": 0.35, "facebook_feed": 0.25, "instagram_stories": 0.25, "reels": 0.15}
)


def generate(cfg, prior_data):
    rng = config.make_rng(config.SEED + 3)
    start_date, end_date = cfg["start_date"], cfg["end_date"]

    google_rows = []
    meta_rows = []

    current = start_date
    while current <= end_date:
        month = current.month
        seasonal = config.SEASONALITY.get(month, 1.0)
        dow_mult = 1.1 if current.weekday() < 5 else 0.85

        # Google Ads
        for camp_name, camp_type, (spend_lo, spend_hi), roas in GOOGLE_CAMPAIGNS:
            daily_spend = _daily_spend(spend_lo, spend_hi, seasonal, dow_mult, rng)
            conv_value = config.quantize(daily_spend * Decimal(str(roas))
                                         * Decimal(str(1.0 + rng.uniform(-0.15, 0.15))))
            impressions = max(10, int(float(daily_spend) * rng.uniform(8, 20)))
            ctr = rng.uniform(0.02, 0.08)
            clicks = max(1, int(impressions * ctr))
            # Platform-reported conversions (overclaim ~15%)
            if roas > 0 and daily_spend > 0:
                true_convs = max(0, int(float(conv_value) / rng.uniform(100, 180)))
                platform_convs = max(0, int(true_convs * rng.uniform(1.10, 1.20)))
            else:
                platform_convs = 0

            google_rows.append({
                "date": current.isoformat(),
                "campaign_name": camp_name,
                "campaign_type": camp_type,
                "ad_group": f"{camp_name}_AG1",
                "impressions": impressions,
                "clicks": clicks,
                "spend_gbp": str(daily_spend),
                "conversions": platform_convs,
                "conversion_value_gbp": str(conv_value),
            })

        # Meta Ads
        active_meta = list(META_CAMPAIGNS)
        if current >= config.WOMENS_LAUNCH:
            active_meta.append(WOMENS_META_CAMPAIGN)

        for camp_name, objective, (spend_lo, spend_hi), roas, placements in active_meta:
            daily_spend = _daily_spend(spend_lo, spend_hi, seasonal, dow_mult, rng)

            # Womens campaign: high spend but poor conversion
            if camp_name == "Womens_Launch_Prospecting":
                daily_spend = config.quantize(
                    Decimal(str(rng.uniform(150, 200))) * Decimal(str(seasonal)))
                conv_value = config.quantize(daily_spend * Decimal(str(
                    rng.uniform(0.8, 1.2))))  # ROAS ~1.0
                roas_eff = 1.0
            else:
                conv_value = config.quantize(daily_spend * Decimal(str(roas))
                                             * Decimal(str(1.0 + rng.uniform(-0.15, 0.15))))
                roas_eff = roas

            impressions = max(50, int(float(daily_spend) * rng.uniform(15, 40)))
            ctr = rng.uniform(0.01, 0.04)
            clicks = max(1, int(impressions * ctr))

            if objective == "conversions" and roas_eff > 0 and daily_spend > 0:
                true_convs = max(0, int(float(conv_value) / rng.uniform(100, 180)))
                platform_convs = max(0, int(true_convs * rng.uniform(1.10, 1.20)))
            else:
                platform_convs = 0

            # Pick a placement
            placement = rng.choice(list(placements.keys()),
                                   p=list(placements.values()))

            meta_rows.append({
                "date": current.isoformat(),
                "campaign_name": camp_name,
                "campaign_objective": objective,
                "ad_set": f"{camp_name}_AS1",
                "ad_name": f"{camp_name}_Ad1",
                "placement": placement,
                "impressions": impressions,
                "clicks": clicks,
                "spend_gbp": str(daily_spend),
                "conversions": platform_convs,
                "conversion_value_gbp": str(conv_value),
            })

        current += timedelta(days=1)

    return {
        "google_ads_daily": google_rows,
        "meta_ads_daily": meta_rows,
    }


def _daily_spend(monthly_lo, monthly_hi, seasonal, dow_mult, rng):
    """Calculate a single day's spend from a monthly budget range."""
    monthly_avg = (monthly_lo + monthly_hi) / 2.0
    daily_base = monthly_avg / 30.0
    daily = daily_base * seasonal * dow_mult * (1.0 + rng.uniform(-0.15, 0.15))
    return config.quantize(Decimal(str(max(0, daily))))
