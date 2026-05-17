"""
44-ticker small-cap momentum universe.

# Universe intentionally 44 tickers (not 50).
# Industrials and Energy sectors thin at $50M-$500M cap with 500k+ ADV.
# Borderline acceptances documented below. Re-screen quarterly.

Original 25 tickers (backtest baseline, verified active 2026-05-17):
  Industrials (5), Consumer Disc (5), Healthcare (5), Technology (5), Energy (5)

New additions — 19 tickers (live-screened 2026-05-17):
  Consumer Disc (+5): JACK, ANGI, PTLO, PLAY, DIN
  Healthcare    (+5): MYGN, CCRN, AGEN, FATE, IRWD
  Technology    (+5): TTGT, EGHT, DOMO, BMBL, RMNI
  Industrials   (+2): TBI, KELYA   — ADV ~413k each; sector exception (no 5 qualify)
  Energy        (+2): REI, AMPY

Borderline notes:
  IRWD : cap ~$589M, 18% over $500M ceiling — accepted
  RMNI : ADV ~494k, 1% under 500k floor     — accepted
  TBI  : ADV ~414k                           — sector exception
  KELYA: ADV ~413k                           — sector exception
  DIN  : ADV ~466k, 7% under floor          — accepted
  SOC  : dropped — cap $2.3B (4.7× ceiling) after Platform Harmony approval
"""

UNIVERSE = {
    # ── Industrials (7) ───────────────────────────────────────────────────────
    # Original 5
    "ATKR":  {"sector": "Industrials",  "name": "Atkore Inc",                    "note": "Electrical conduit"},
    "KTOS":  {"sector": "Industrials",  "name": "Kratos Defense & Security",     "note": "Drone/defense tech"},
    "FELE":  {"sector": "Industrials",  "name": "Franklin Electric Co",          "note": "Water/fuel systems"},
    "GTES":  {"sector": "Industrials",  "name": "Gates Industrial Corporation",  "note": "Industrial belts & hoses"},
    "HLIO":  {"sector": "Industrials",  "name": "Helios Technologies Inc",       "note": "Hydraulic controls"},
    # Added 2 (ADV ~413k each; sector exception — no small-cap industrials clear 500k ADV)
    "TBI":   {"sector": "Industrials",  "name": "TrueBlue Inc",                  "note": "Workforce staffing; cap $172M ADV 414k"},
    "KELYA": {"sector": "Industrials",  "name": "Kelly Services Class A",        "note": "Industrial staffing; cap $333M ADV 413k"},

    # ── Consumer Discretionary (10) ───────────────────────────────────────────
    # Original 5
    "BOOT":  {"sector": "ConsumerDisc", "name": "Boot Barn Holdings",            "note": "Western & work apparel"},
    "GSHD":  {"sector": "ConsumerDisc", "name": "Goosehead Insurance",           "note": "Independent insurance distribution"},
    "LESL":  {"sector": "ConsumerDisc", "name": "Leslie's Inc",                  "note": "Pool supply retail"},
    "CATO":  {"sector": "ConsumerDisc", "name": "Cato Corporation",              "note": "Specialty apparel retail"},
    "DRVN":  {"sector": "ConsumerDisc", "name": "Driven Brands Holdings",        "note": "Auto service franchisor"},
    # Added 5 (all pass or borderline)
    "JACK":  {"sector": "ConsumerDisc", "name": "Jack in the Box",               "note": "QSR; cap $207M ADV 842k ✓"},
    "ANGI":  {"sector": "ConsumerDisc", "name": "Angi Inc",                      "note": "Home services marketplace; cap $201M ADV 1524k ✓"},
    "PTLO":  {"sector": "ConsumerDisc", "name": "Portillo's Inc",                "note": "Chicago-style restaurants; cap $288M ADV 2247k ✓"},
    "PLAY":  {"sector": "ConsumerDisc", "name": "Dave & Buster's Entertainment", "note": "Entertainment/dining; cap $351M ADV 1824k ✓"},
    "DIN":   {"sector": "ConsumerDisc", "name": "Dine Brands Global",            "note": "IHOP & Applebee's franchisor; cap $378M ADV 466k (borderline)"},

    # ── Healthcare (10) ───────────────────────────────────────────────────────
    # Original 5
    "ACAD":  {"sector": "Healthcare",   "name": "Acadia Pharmaceuticals",        "note": "CNS drugs"},
    "INVA":  {"sector": "Healthcare",   "name": "Innoviva Inc",                  "note": "Royalty-based pharma"},
    "HIMS":  {"sector": "Healthcare",   "name": "Hims & Hers Health",            "note": "DTC telehealth"},
    "PRAX":  {"sector": "Healthcare",   "name": "Praxis Precision Medicine",     "note": "Clinical-stage neuro"},
    "NVAX":  {"sector": "Healthcare",   "name": "Novavax Inc",                   "note": "Vaccine biotech"},
    # Added 5
    "MYGN":  {"sector": "Healthcare",   "name": "Myriad Genetics",               "note": "Genetic testing; cap $338M ADV 1588k ✓"},
    "CCRN":  {"sector": "Healthcare",   "name": "Cross Country Healthcare",      "note": "Healthcare staffing; cap $407M ADV 827k ✓"},
    "AGEN":  {"sector": "Healthcare",   "name": "Agenus Inc",                    "note": "Immuno-oncology; cap $149M ADV 913k ✓"},
    "FATE":  {"sector": "Healthcare",   "name": "Fate Therapeutics",             "note": "Cell therapy; cap $205M ADV 3113k ✓"},
    "IRWD":  {"sector": "Healthcare",   "name": "Ironwood Pharmaceuticals",      "note": "GI drugs; cap $589M ADV 2367k (cap borderline)"},

    # ── Technology (10) ───────────────────────────────────────────────────────
    # Original 5
    "POWI":  {"sector": "Technology",   "name": "Power Integrations",            "note": "Analog semiconductor"},
    "YEXT":  {"sector": "Technology",   "name": "Yext Inc",                      "note": "Digital presence platform"},
    "NCNO":  {"sector": "Technology",   "name": "nCino Inc",                     "note": "Banking cloud"},
    "DOCN":  {"sector": "Technology",   "name": "DigitalOcean Holdings",         "note": "Developer cloud"},
    "LPSN":  {"sector": "Technology",   "name": "LivePerson Inc",                "note": "Conversational AI"},
    # Added 5
    "TTGT":  {"sector": "Technology",   "name": "TechTarget Inc",                "note": "B2B tech media/data; cap $375M ADV 757k ✓"},
    "EGHT":  {"sector": "Technology",   "name": "8x8 Inc",                       "note": "Cloud communications; cap $329M ADV 1558k ✓"},
    "DOMO":  {"sector": "Technology",   "name": "Domo Inc",                      "note": "Cloud BI platform; cap $158M ADV 789k ✓"},
    "BMBL":  {"sector": "Technology",   "name": "Bumble Inc",                    "note": "Dating/social app; cap $410M ADV 3333k ✓"},
    "RMNI":  {"sector": "Technology",   "name": "Rimini Street Inc",             "note": "Enterprise SW support; cap $320M ADV 494k (borderline)"},

    # ── Energy (7) ───────────────────────────────────────────────────────────
    # Original 5
    "SM":    {"sector": "Energy",       "name": "SM Energy",                     "note": "E&P, Permian/Midland Basin"},
    "SJT":   {"sector": "Energy",       "name": "San Juan Basin Royalty Trust",  "note": "Natural gas royalty"},
    "VET":   {"sector": "Energy",       "name": "Vermilion Energy",              "note": "International E&P"},
    "WHD":   {"sector": "Energy",       "name": "Cactus Inc",                    "note": "Wellhead equipment"},
    "GPOR":  {"sector": "Energy",       "name": "Gulfport Energy Corporation",   "note": "Natural gas E&P"},
    # Added 2 (sector thin — energy caps expanded 3-10× since 2022)
    "REI":   {"sector": "Energy",       "name": "Ring Energy Inc",               "note": "Permian E&P; cap $345M ADV 6680k ✓"},
    "AMPY":  {"sector": "Energy",       "name": "Amplify Energy Corp",           "note": "Diversified E&P; cap $216M ADV 748k ✓"},
}

TICKERS = list(UNIVERSE.keys())
CANDIDATE_TICKERS = TICKERS  # backward-compatible alias

SECTORS: dict[str, list[str]] = {}
for _t, _info in UNIVERSE.items():
    SECTORS.setdefault(_info["sector"], []).append(_t)
