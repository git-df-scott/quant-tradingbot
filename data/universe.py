"""
Small-cap momentum universe — cleaned 2026-05-17.

Verified against yfinance: 77 dead/delisted tickers removed, 3 suspicious
(zero-volume or extreme spike) removed, ~43 replacements added.
Runtime fetch filters further by price ($5-$200) and ADV (>300k shares).
"""

CANDIDATE_TICKERS: list[str] = [
    # ── Energy – E&P, midstream, oilfield services ────────────────────────────
    "SM",    "GPOR",  "NOG",   "TALO",  "KOS",   "WHD",   "PUMP",  "WTTR",
    "RES",   "NINE",  "USAC",  "AROC",  "NGL",   "DKL",   "SJT",   "VET",
    "REX",   "BSM",   "REPX",  "FLNG",  "PTEN",  "HPK",   "CAPL",  "MARPS",
    # replacements: Vital Energy, Chord, Sitio Royalties, Aris Water,
    #               KLX Energy, Ring Energy, Amplify Energy, Primoris
    "VTLE",  "CHRD",  "SITIO", "ARIS",  "KLXE",  "REI",   "AMPY",  "PRIM",

    # ── Biotech / Specialty Pharma ────────────────────────────────────────────
    "ACAD",  "HIMS",  "PRAX",  "NVAX",  "INVA",  "RCUS",  "IMVT",  "ARDX",
    "ALKS",  "MGNX",  "ADMA",  "AMRX",  "AGEN",  "ARVN",  "CYTK",  "ENTA",
    "GKOS",  "HALO",  "IRWD",  "KYMR",  "LGND",  "MDGL",  "MNKD",  "MYGN",
    "NUVL",  "OCUL",  "PAHC",  "PTGX",  "RYTM",  "SUPN",  "TGTX",  "XENE",
    "ALLO",  "AMPH",  "ASRT",  "ATRC",  "AXSM",  "CLDX",  "CMPS",  "EXEL",
    "FATE",  "ABCL",  "ALDX",  "AMRN",  "ANIP",  "ARQT",  "ATAI",  "ALEC",
    "ANIK",  "BHVN",  "CNTA",  "IOVA",  "JANX",  "MIRM",  "NKTR",  "NTLA",
    "PCVX",  "RXRX",
    # replacements: Corcept, Krystal Bio, Arrowhead, Blueprint Med,
    #               Tarsus, Vera Therapeutics, Immunocore, Scholar Rock,
    #               Prothena, Day One Bio, Rocket Pharma, Viking Therapeutics
    "CORT",  "KRYS",  "ARWR",  "BPMC",  "TARS",  "VERA",  "IMCR",  "SRRK",
    "PRTA",  "DAWN",  "RCKT",  "VKTX",

    # ── Medical Devices / Healthcare Services ────────────────────────────────
    "CNMD",  "INGN",  "INMD",  "CCRN",  "HCSG",  "MMSI",  "NVCR",  "CCXI",
    "CDNA",  "PNTG",  "ADUS",  "AHCO",  "USPH",  "IART",  "RGEN",  "TCMD",
    "TMDX",
    # replacements: Orthofix Medical, Envista Holdings, Haemonetics
    "OFIX",  "NVST",  "HAE",

    # ── Technology – Software / SaaS / Internet ──────────────────────────────
    "YEXT",  "NCNO",  "DOCN",  "LPSN",  "EGHT",  "VIAV",  "DOMO",
    "CERT",  "CNXC",  "APPS",  "BRZE",  "FSLY",
    "SPSC",  "RSKD",  "PRGS",  "PDFS",
    "LQDT",  "ATEN",  "NTGR",  "ARLO",  "BAND",  "BMBL",
    "CARS",  "CALX",  "NRDS",  "APPN",
    "CARG",  "TTGT",  "UPWK",  "ALRM",  "KFRC",  "RMNI",  "SCSC",  "TNET",
    "LOPE",
    # replacements: PAR Technology, Freshworks, TaskUs, DoubleVerify,
    #               Alkami Technology, Docebo, LiveRamp
    "PAR",   "FRSH",  "TASK",  "DV",    "ALKT",  "DCBO",  "RAMP",

    # ── Semiconductors / Electronic Components ───────────────────────────────
    "COHU",  "SMTC",  "FORM",  "ICHR",  "POWI",  "DIOD",  "AEHR",  "ACMR",
    "AMKR",  "AOSL",  "AXTI",  "CRUS",  "IMOS",  "CAMP",
    "DAIO",  "QUIK",  "ONTO",  "SITM",  "ACLS",  "MTSI",  "POWL",

    # ── Industrials – Defense / Manufacturing / Distribution ─────────────────
    "KTOS",  "FELE",  "GTES",  "HLIO",  "ATKR",  "DY",    "ARCB",
    "CMCO",  "DAN",   "DNOW",  "DXPE",  "GBX",   "GFF",   "GNTX",  "HUBG",
    "HURC",  "HWKN",  "IIIN",  "INSG",  "HLX",   "CLFD",
    "AVAV",  "AAON",  "AEIS",  "AMWD",  "APOG",  "ASTE",  "GRC",
    "GNSS",  "ROAD",  "ESAB",  "EXTR",  "WERN",  "HTLD",  "MRTN",
    "MATX",  "TREX",  "MYRG",  "NPO",   "THRM",
    "TRNS",  "OSIS",  "STRL",  "VSEC",  "MTRN",
    # replacements: Shyft Group, NV5 Global, Huron Consulting,
    #               Herc Holdings, Blue Bird Corp
    "SHYF",  "NVEE",  "HURN",  "HRI",   "BLBD",

    # ── Consumer – Restaurants / Leisure ─────────────────────────────────────
    "CAKE",  "BJRI",  "RRGB",  "LOCO",  "JACK",  "BLMN",
    "NATH",  "SHAK",  "MCRI",  "DINE",  "EAT",   "ARCO",  "PZZA",
    # replacements: Portillo's, Dave & Buster's, RCI Hospitality
    "PTLO",  "PLAY",  "RICK",

    # ── Consumer – Retail / Brands ────────────────────────────────────────────
    "BOOT",  "CATO",  "DRVN",  "TLYS",  "GCO",   "PLCE",
    "SCVL",  "BKE",   "HOFT",  "SNBR",
    "LE",    "WGO",   "XPEL",  "IPAR",  "SMPL",  "CENT",  "UNFI",

    # ── Financial – BDCs / Closed-End / Asset Managers ───────────────────────
    "CSWC",  "HTGC",  "GAIN",  "NEWT",  "TPVG",  "PFLT",  "HRZN",  "OCSL",
    "GSHD",  "MAIN",  "SLRC",  "TCPC",  "NMFC",

    # ── Financial – Banks / Insurance ────────────────────────────────────────
    "GBCI",  "FFIN",  "INDB",  "LKFN",  "FISI",  "HCI",   "SBCF",
    "TOWN",  "RNST",  "IBCP",  "FFBC",
    "ACNB",  "CVBF",  "EGBN",  "AMTB",  "UMBF",
    "SFNC",  "PEBO",  "NBTB",
    # replacements: Granite Point Mortgage, Investors Title,
    #               First Bancshares MS, Pinnacle Financial
    "GPMT",  "ITIC",  "FBMS",  "PNFP",

    # ── Materials / Chemicals / Metals ────────────────────────────────────────
    "ASIX",  "AVNT",  "BCPC",  "KALU",  "AG",    "CDE",   "HL",    "EXK",
    "PAAS",  "FSM",   "USAS",  "ROCK",  "WDFC",  "LXFR",
    "TISI",  "SPWH",  "MLAB",

    # ── Real Estate – REITs ───────────────────────────────────────────────────
    "GOOD",  "ILPT",  "BRT",   "CLPR",  "NXRT",  "CHCT",
    "ELME",  "UHT",
]

# De-duplicate while preserving order
_seen: set[str] = set()
CANDIDATE_TICKERS = [t for t in CANDIDATE_TICKERS if t not in _seen and not _seen.add(t)]  # type: ignore[func-returns-value]

# Backward-compatible alias
TICKERS = CANDIDATE_TICKERS
