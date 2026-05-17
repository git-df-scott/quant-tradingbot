"""
Small-cap momentum universe: ~380 candidate tickers filtered at runtime by
price ($5-$200) and ADV (>300k shares).  Targets NYSE/NASDAQ companies with
historical market cap roughly $300M-$3B.
"""

CANDIDATE_TICKERS: list[str] = [
    # ── Energy – E&P, midstream, oilfield services ────────────────────────────
    "SM",    "GPOR",  "NOG",   "CIVI",  "TALO",  "SBOW",  "ESTE",  "VAALCO",
    "KOS",   "WHD",   "PUMP",  "WTTR",  "MRC",   "RES",   "NINE",  "USAC",
    "AROC",  "NGL",   "DKL",   "SJT",   "VET",   "REX",   "BSM",   "REPX",
    "FLNG",  "MNRL",  "PTEN",  "HPK",   "SRLP",  "CAPL",  "BATL",  "NGAS",
    "CDEV",  "SWN",   "MARPS",

    # ── Biotech / Specialty Pharma ────────────────────────────────────────────
    "ACAD",  "HIMS",  "PRAX",  "NVAX",  "INVA",  "RCUS",  "IMVT",  "ARDX",
    "ITCI",  "ALKS",  "MGNX",  "ADMA",  "AMRX",  "APLT",  "RVNC",  "AGEN",
    "AKRO",  "ARVN",  "CDMO",  "CYTK",  "ENTA",  "GKOS",  "HALO",  "HRTX",
    "IRWD",  "KYMR",  "LGND",  "MDGL",  "MNKD",  "MYGN",  "NUVL",  "OCUL",
    "PAHC",  "PTGX",  "RYTM",  "SILK",  "SUPN",  "TGTX",  "XENE",  "YMAB",
    "ALLO",  "AMPH",  "ASRT",  "ATRC",  "AXSM",  "CARA",  "CBAY",  "CLDX",
    "CMPS",  "CRIS",  "EXEL",  "FOLD",  "FATE",  "SAGE",  "ABCL",  "ALDX",
    "AMRN",  "ANIP",  "ARQT",  "ATAI",  "ALEC",  "ANIK",  "BHVN",  "CNTA",
    "IOVA",  "JANX",  "KROS",  "LBPH",  "MIRM",  "NKTR",  "NTLA",  "ONCT",
    "PCVX",  "RXRX",  "GRTS",  "GLYC",

    # ── Medical Devices / Healthcare Services ────────────────────────────────
    "CNMD",  "INGN",  "INMD",  "CCRN",  "HCSG",  "MMSI",  "NVCR",  "CCXI",
    "AXNX",  "CDNA",  "PNTG",  "ADUS",  "AHCO",  "ATRI",  "USPH",  "IART",
    "RGEN",  "TCMD",  "TMDX",

    # ── Technology – Software / SaaS / Internet ──────────────────────────────
    "YEXT",  "NCNO",  "DOCN",  "LPSN",  "UPLD",  "EGHT",  "VIAV",  "DOMO",
    "BIGC",  "CERT",  "CNXC",  "CTLP",  "APPS",  "BRZE",  "CDLX",  "FSLY",
    "SPSC",  "SMAR",  "RSKD",  "PYCR",  "PRGS",  "PDFS",  "NTUS",  "MTTR",
    "MIME",  "LQDT",  "LLNW",  "ATEN",  "NTGR",  "ARLO",  "BAND",  "BMBL",
    "CARS",  "BLNK",  "VRNT",  "AVDX",  "CALX",  "NRDS",  "PRFT",  "APPN",
    "CARG",  "TTGT",  "UPWK",  "ALRM",  "KFRC",  "RMNI",  "SCSC",  "TNET",
    "SUMO",  "LOPE",

    # ── Semiconductors / Electronic Components ───────────────────────────────
    "COHU",  "SMTC",  "FORM",  "ICHR",  "POWI",  "DIOD",  "AEHR",  "ACMR",
    "AMKR",  "AOSL",  "AXTI",  "CRUS",  "EMKR",  "IMOS",  "CCMP",  "CAMP",
    "DAIO",  "QUIK",  "ONTO",  "SITM",  "ACLS",  "MTSI",  "POWL",

    # ── Industrials – Defense / Manufacturing / Distribution ─────────────────
    "KTOS",  "FELE",  "GTES",  "HLIO",  "ATKR",  "DY",    "ARCB",  "BWEN",
    "CMCO",  "DAN",   "DNOW",  "DXPE",  "GBX",   "GFF",   "GNTX",  "HUBG",
    "HURC",  "HWKN",  "IEC",   "IIIN",  "INFN",  "INSG",  "HLX",   "CLFD",
    "AVAV",  "AAON",  "AEIS",  "AMWD",  "APOG",  "ASTE",  "AZEK",  "GRC",
    "GNSS",  "ROAD",  "ESAB",  "EXTR",  "WERN",  "HTLD",  "MRTN",  "DSKE",
    "ECHO",  "MATX",  "TREX",  "MYRG",  "HAYN",  "ZEUS",  "NPO",   "THRM",
    "TRNS",  "OSIS",  "STRL",  "VSEC",  "MTRN",

    # ── Consumer – Restaurants / Leisure ─────────────────────────────────────
    "CAKE",  "CHUY",  "BJRI",  "RRGB",  "LOCO",  "JACK",  "BLMN",  "FAT",
    "NATH",  "SHAK",  "PBPB",  "MCRI",  "FRGI",  "DINE",  "EAT",   "ARCO",
    "PZZA",

    # ── Consumer – Retail / Brands ────────────────────────────────────────────
    "BOOT",  "CATO",  "LESL",  "DRVN",  "PRTY",  "TLYS",  "GCO",   "PLCE",
    "BGFV",  "HIBB",  "SCVL",  "BKE",   "RCII",  "CONN",  "HOFT",  "SNBR",
    "LE",    "WGO",   "XPEL",  "IPAR",  "AMMO",  "SMPL",  "CENT",  "UNFI",

    # ── Financial – BDCs / Closed-End / Asset Managers ───────────────────────
    "CSWC",  "HTGC",  "GAIN",  "NEWT",  "TPVG",  "PFLT",  "HRZN",  "OCSL",
    "GSHD",  "MAIN",  "SLRC",  "TCPC",  "NMFC",

    # ── Financial – Banks / Insurance ────────────────────────────────────────
    "GBCI",  "FFIN",  "IBTX",  "INDB",  "LKFN",  "FISI",  "HCI",   "SBCF",
    "TOWN",  "RNST",  "HONE",  "HTBK",  "LBAI",  "IBCP",  "FFBC",  "HIFS",
    "HMST",  "CATC",  "ACNB",  "CVBF",  "EGBN",  "CBTX",  "AMTB",  "UMBF",
    "VBTX",  "SFNC",  "PEBO",  "NBTB",

    # ── Materials / Chemicals / Metals ────────────────────────────────────────
    "ASIX",  "AVNT",  "BCPC",  "KALU",  "AG",    "CDE",   "HL",    "EXK",
    "GATO",  "PAAS",  "MAG",   "FSM",   "USAS",  "ROCK",  "WDFC",  "LXFR",
    "TPIC",  "TISI",  "SPWH",  "MLAB",

    # ── Real Estate – REITs ───────────────────────────────────────────────────
    "GOOD",  "PLYM",  "ILPT",  "BRT",   "CLPR",  "NXRT",  "CHCT",  "GMRE",
    "ELME",  "UHT",   "PKST",  "AIRC",
]

# De-duplicate while preserving order
_seen: set[str] = set()
CANDIDATE_TICKERS = [t for t in CANDIDATE_TICKERS if t not in _seen and not _seen.add(t)]  # type: ignore[func-returns-value]

# Backward-compatible alias
TICKERS = CANDIDATE_TICKERS
