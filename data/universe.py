"""
36-ticker small-cap momentum universe.

# Universe intentionally 36 tickers (not 50).
# Industrials: only 3 tickers (HLIO, TBI, KELYA) — sector-wide ADV shortage at $50M-$500M cap.
#   No 5 qualifying industrial names exist at this screen; FELE and GTES slots left empty.
# All tickers verified active on US exchanges 2026-05-17.
# Borderlines accepted: TBI (ADV ~414k), KELYA (ADV ~413k), DIN (ADV ~466k),
#   IRWD (cap ~$589M, 18% over $500M ceiling), RMNI (ADV ~494k, 1% under 500k floor).
# Re-screen quarterly — small-cap universe drifts fast.

Removed from original 25 (cap ceiling failures, May 2026):
  ATKR  : $2.5B  — 5× ceiling
  KTOS  : $9.8B  — 20× ceiling
  FELE  : $4.2B  — 8× ceiling (slot empty)
  GTES  : $6.2B  — 12× ceiling (slot empty)
  BOOT  : $4.4B  — 9× ceiling  → replaced by JACK (already in additions)
  HIMS  : $5.8B  — 12× ceiling → replaced by MYGN (already in additions)
  DOCN  : $16B   — 32× ceiling → replaced by TTGT (already in additions)
  LPSN  : $27M   — below $50M floor → replaced by EGHT (already in additions)
"""

UNIVERSE = {
    # ── Industrials (3) ───────────────────────────────────────────────────────
    # ADV ~413-414k each; sector exception — no small-cap industrials clear 500k ADV
    "HLIO":  {"sector": "Industrials",  "name": "Helios Technologies Inc",       "note": "Hydraulic controls"},
    "TBI":   {"sector": "Industrials",  "name": "TrueBlue Inc",                  "note": "Workforce staffing; cap $172M ADV 414k"},
    "KELYA": {"sector": "Industrials",  "name": "Kelly Services Class A",        "note": "Industrial staffing; cap $333M ADV 413k"},

    # ── Consumer Discretionary (9) ────────────────────────────────────────────
    "GSHD":  {"sector": "ConsumerDisc", "name": "Goosehead Insurance",           "note": "Independent insurance distribution"},
    "LESL":  {"sector": "ConsumerDisc", "name": "Leslie's Inc",                  "note": "Pool supply retail"},
    "CATO":  {"sector": "ConsumerDisc", "name": "Cato Corporation",              "note": "Specialty apparel retail"},
    "DRVN":  {"sector": "ConsumerDisc", "name": "Driven Brands Holdings",        "note": "Auto service franchisor"},
    "JACK":  {"sector": "ConsumerDisc", "name": "Jack in the Box",               "note": "QSR; cap $207M ADV 842k"},
    "ANGI":  {"sector": "ConsumerDisc", "name": "Angi Inc",                      "note": "Home services marketplace; cap $201M ADV 1524k"},
    "PTLO":  {"sector": "ConsumerDisc", "name": "Portillo's Inc",                "note": "Chicago-style restaurants; cap $288M ADV 2247k"},
    "PLAY":  {"sector": "ConsumerDisc", "name": "Dave & Buster's Entertainment", "note": "Entertainment/dining; cap $351M ADV 1824k"},
    "DIN":   {"sector": "ConsumerDisc", "name": "Dine Brands Global",            "note": "IHOP & Applebee's franchisor; cap $378M ADV 466k (borderline)"},

    # ── Healthcare (9) ────────────────────────────────────────────────────────
    "ACAD":  {"sector": "Healthcare",   "name": "Acadia Pharmaceuticals",        "note": "CNS drugs"},
    "INVA":  {"sector": "Healthcare",   "name": "Innoviva Inc",                  "note": "Royalty-based pharma"},
    "PRAX":  {"sector": "Healthcare",   "name": "Praxis Precision Medicine",     "note": "Clinical-stage neuro"},
    "NVAX":  {"sector": "Healthcare",   "name": "Novavax Inc",                   "note": "Vaccine biotech"},
    "MYGN":  {"sector": "Healthcare",   "name": "Myriad Genetics",               "note": "Genetic testing; cap $338M ADV 1588k"},
    "CCRN":  {"sector": "Healthcare",   "name": "Cross Country Healthcare",      "note": "Healthcare staffing; cap $407M ADV 827k"},
    "AGEN":  {"sector": "Healthcare",   "name": "Agenus Inc",                    "note": "Immuno-oncology; cap $149M ADV 913k"},
    "FATE":  {"sector": "Healthcare",   "name": "Fate Therapeutics",             "note": "Cell therapy; cap $205M ADV 3113k"},
    "IRWD":  {"sector": "Healthcare",   "name": "Ironwood Pharmaceuticals",      "note": "GI drugs; cap $589M ADV 2367k (cap borderline)"},

    # ── Technology (8) ────────────────────────────────────────────────────────
    "POWI":  {"sector": "Technology",   "name": "Power Integrations",            "note": "Analog semiconductor"},
    "YEXT":  {"sector": "Technology",   "name": "Yext Inc",                      "note": "Digital presence platform"},
    "NCNO":  {"sector": "Technology",   "name": "nCino Inc",                     "note": "Banking cloud"},
    "TTGT":  {"sector": "Technology",   "name": "TechTarget Inc",                "note": "B2B tech media/data; cap $375M ADV 757k"},
    "EGHT":  {"sector": "Technology",   "name": "8x8 Inc",                       "note": "Cloud communications; cap $329M ADV 1558k"},
    "DOMO":  {"sector": "Technology",   "name": "Domo Inc",                      "note": "Cloud BI platform; cap $158M ADV 789k"},
    "BMBL":  {"sector": "Technology",   "name": "Bumble Inc",                    "note": "Dating/social app; cap $410M ADV 3333k"},
    "RMNI":  {"sector": "Technology",   "name": "Rimini Street Inc",             "note": "Enterprise SW support; cap $320M ADV 494k (borderline)"},

    # ── Energy (7) ────────────────────────────────────────────────────────────
    "SM":    {"sector": "Energy",       "name": "SM Energy",                     "note": "E&P, Permian/Midland Basin"},
    "SJT":   {"sector": "Energy",       "name": "San Juan Basin Royalty Trust",  "note": "Natural gas royalty"},
    "VET":   {"sector": "Energy",       "name": "Vermilion Energy",              "note": "International E&P"},
    "WHD":   {"sector": "Energy",       "name": "Cactus Inc",                    "note": "Wellhead equipment"},
    "GPOR":  {"sector": "Energy",       "name": "Gulfport Energy Corporation",   "note": "Natural gas E&P"},
    "REI":   {"sector": "Energy",       "name": "Ring Energy Inc",               "note": "Permian E&P; cap $345M ADV 6680k"},
    "AMPY":  {"sector": "Energy",       "name": "Amplify Energy Corp",           "note": "Diversified E&P; cap $216M ADV 748k"},
}

TICKERS = list(UNIVERSE.keys())
CANDIDATE_TICKERS = TICKERS  # backward-compatible alias

SECTORS: dict[str, list[str]] = {}
for _t, _info in UNIVERSE.items():
    SECTORS.setdefault(_info["sector"], []).append(_t)
