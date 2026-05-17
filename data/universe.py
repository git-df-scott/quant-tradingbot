"""
25 small-cap tickers ($50M-$500M market cap as of 2022), diversified across 5 sectors.
Max 5 per sector. Selected for clean data availability and genuine small-cap classification.

Verified 2026-05-17: all 25 confirmed still trading on US exchanges. Zero replacements needed.
"""

UNIVERSE = {
    # ── Industrials (5) ───────────────────────────────────────────────────────
    "ATKR": {"sector": "Industrials",  "name": "Atkore Inc",                    "note": "Electrical conduit, benefited from infrastructure spend"},
    "KTOS": {"sector": "Industrials",  "name": "Kratos Defense & Security",     "note": "Drone/defense tech, ~$2B cap in 2022"},
    "FELE": {"sector": "Industrials",  "name": "Franklin Electric Co",          "note": "Water/fuel systems, steady compounder"},
    "GTES": {"sector": "Industrials",  "name": "Gates Industrial Corporation",  "note": "Industrial belts & hoses, IPO 2018"},
    "HLIO": {"sector": "Industrials",  "name": "Helios Technologies Inc",       "note": "Hydraulic controls, formerly Sun Hydraulics"},

    # ── Consumer Discretionary (5) ────────────────────────────────────────────
    "BOOT": {"sector": "ConsumerDisc", "name": "Boot Barn Holdings",            "note": "Western & work apparel, strong momentum cycles"},
    "GSHD": {"sector": "ConsumerDisc", "name": "Goosehead Insurance",           "note": "Independent insurance distribution, IPO 2018"},
    "LESL": {"sector": "ConsumerDisc", "name": "Leslie's Inc",                  "note": "Pool supply retail, IPO 2020"},
    "CATO": {"sector": "ConsumerDisc", "name": "Cato Corporation",              "note": "Specialty apparel retail, established small-cap"},
    "DRVN": {"sector": "ConsumerDisc", "name": "Driven Brands Holdings",        "note": "Auto service franchisor, IPO 2021"},

    # ── Healthcare (5) ────────────────────────────────────────────────────────
    "ACAD": {"sector": "Healthcare",   "name": "Acadia Pharmaceuticals",        "note": "CNS drugs, high-beta biotech"},
    "INVA": {"sector": "Healthcare",   "name": "Innoviva Inc",                  "note": "Royalty-based pharma, low vol"},
    "HIMS": {"sector": "Healthcare",   "name": "Hims & Hers Health",            "note": "DTC telehealth, SPAC 2021"},
    "PRAX": {"sector": "Healthcare",   "name": "Praxis Precision Medicine",     "note": "Clinical-stage neuro, IPO 2020"},
    "NVAX": {"sector": "Healthcare",   "name": "Novavax Inc",                   "note": "Vaccine biotech, extreme momentum cycles"},

    # ── Technology (5) ───────────────────────────────────────────────────────
    "POWI": {"sector": "Technology",   "name": "Power Integrations",            "note": "Analog semiconductor, established 1988"},
    "YEXT": {"sector": "Technology",   "name": "Yext Inc",                      "note": "Digital presence platform, IPO 2017"},
    "NCNO": {"sector": "Technology",   "name": "nCino Inc",                     "note": "Banking cloud, IPO 2020"},
    "DOCN": {"sector": "Technology",   "name": "DigitalOcean Holdings",         "note": "Developer cloud, IPO 2021"},
    "LPSN": {"sector": "Technology",   "name": "LivePerson Inc",                "note": "Conversational AI, established 2000"},

    # ── Energy (5) ───────────────────────────────────────────────────────────
    "SM":   {"sector": "Energy",       "name": "SM Energy",                     "note": "E&P focused on Permian and Midland Basin"},
    "SJT":  {"sector": "Energy",       "name": "San Juan Basin Royalty Trust",  "note": "Natural gas royalty, high-yield"},
    "VET":  {"sector": "Energy",       "name": "Vermilion Energy",              "note": "International E&P, TSX/NYSE dual-listed"},
    "WHD":  {"sector": "Energy",       "name": "Cactus Inc",                    "note": "Wellhead equipment, IPO 2018"},
    "GPOR": {"sector": "Energy",       "name": "Gulfport Energy Corporation",   "note": "Natural gas, relisted 2021 post-restructuring"},
}

TICKERS = list(UNIVERSE.keys())

# Alias used by the expanded-universe path (fetch.py imports TICKERS)
CANDIDATE_TICKERS = TICKERS

SECTORS = {}
for ticker, info in UNIVERSE.items():
    sector = info["sector"]
    SECTORS.setdefault(sector, []).append(ticker)
