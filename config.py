"""
Central configuration: company universe, symbols, market-context tickers,
prediction horizons, and file paths.
"""

import os

# =========================
# COMPANY LIST
# =========================

HOSPITAL_COMPANIES = [
    "Apollo Hospitals", "Fortis Healthcare", "Max Healthcare", "Narayana Hrudayalaya",
    "KIMS", "Metropolis Healthcare", "Thyrocare", "Kovai Medical",
    "Jupiter Life Line", "Rainbow Children", "Global Health Medanta",
    "Yatharth Hospitals", "Aster DM Healthcare", "Health Global HCG Oncology",
    "Indraprastha Medical Apollo", "Artemis Medicare", "Park Medi World"
]

PHARMA_COMPANIES = [
    "Sun Pharma", "Dr Reddy", "Cipla", "Divis Laboratories",
    "Aurobindo Pharma", "Lupin", "Torrent Pharma", "Alkem Laboratories",
    "Biocon", "Glenmark Pharma"
]

STOCK_SYMBOLS = {
    "Apollo Hospitals": "APOLLOHOSP",
    "Fortis Healthcare": "FORTIS",
    "Max Healthcare": "MAXHEALTH",
    "Narayana Hrudayalaya": "NH",
    "Metropolis Healthcare": "METROPOLIS",
    "Thyrocare": "THYROCARE",
    "Aster DM Healthcare": "ASTERDM",
    "Global Health Medanta": "MEDANTA",
    "Yatharth Hospitals": "YATHARTH",
    "KIMS": "KIMS",
    "Rainbow Children": "RAINBOW",
    "Jupiter Life Line": "JLHL",
    "Kovai Medical": "KOVAI",
    "Health Global HCG Oncology": "HCG",
    "Indraprastha Medical Apollo": "INDRAMEDCO",
    "Park Medi World": "PARKHOSPS",
    "Artemis Medicare": "ARTEMISMED",

    "Sun Pharma": "SUNPHARMA",
    "Dr Reddy": "DRREDDY",
    "Cipla": "CIPLA",
    "Divis Laboratories": "DIVISLAB",
    "Aurobindo Pharma": "AUROPHARMA",
    "Lupin": "LUPIN",
    "Torrent Pharma": "TORNTPHARM",
    "Alkem Laboratories": "ALKEM",
    "Biocon": "BIOCON",
    "Glenmark Pharma": "GLENMARK"
}

BSE_CODES = {
    "Kovai Medical": "523323",
    "Jupiter Life Line": "543980",
    "Rainbow Children": "543524",
    "Park Medi World": "544645",
    "Artemis Medicare": "542919",
    "KIMS": "543308"
}

# =========================
# MANUAL PRICE FALLBACK (last resort)
# =========================
# A handful of illiquid / recently-listed small caps don't reliably have
# usable Yahoo history AND the BSE scrape can fail (rate limits, API
# changes). Restored from the original script after a real run showed
# Kovai Medical and Park Medi World coming back with zero price data --
# the original's 3-tier NSE->Yahoo->BSE->manual fallback existed for
# exactly this reason. Update these manually if they go stale; this is
# strictly a last resort after NSE/Yahoo/BSE have all been tried.
MANUAL_PRICE_FALLBACK = {
    "Park Medi World": 216,
    "Jupiter Life Line": 1250,
    "Rainbow Children": 1249,
    "Kovai Medical": 5389,
}

# =========================
# AUTOMATION ON/OFF SWITCH
# =========================
# Single place that controls whether the pipeline opens simulated
# positions at all. AUTOMATION_MODE is "PAPER" only right now -- no
# broker is connected, so nothing here can ever touch real money. When
# you're ready to connect a real broker later, this is the flag/mode
# pair that would gate it (a "LIVE" mode should only ever be added
# alongside real, explicit broker credentials and its own extra
# confirmation step -- never flip this to something that places real
# orders without that being a deliberate, separate change).
AUTOMATION_ENABLED = True     # master ON/OFF switch for the paper-trading step
AUTOMATION_MODE = "PAPER"     # "PAPER" = simulation only. No "LIVE" mode exists yet.

# =========================
# MARKET CONTEXT (new)
# =========================
# Broad + sector benchmarks used as extra features so models aren't limited
# to single-stock technicals (this was a major gap in the original model).

MARKET_INDEX_TICKERS = {
    "NIFTY50": "^NSEI",
    "NIFTY_PHARMA": "^CNXPHARMA",
    "USDINR": "INR=X",
}

# =========================
# PREDICTION HORIZONS (trading days ahead)
# =========================
# NOTE: these must be REAL separate targets (see features.py / models.py).
# The old code faked "week/month/3-month" by only changing a "Day" feature
# at inference time while every other input stayed frozen at today's value
# -> tree models produced identical output for every horizon.

HORIZONS = {
    "Next Day": 1,
    "Next Week": 5,
    "Next Month": 21,   # ~21 trading days in a month, not 30 calendar days
    "Next 3 Months": 63,
}

MODEL_NAMES = ["LR", "RF", "XGB", "LGBM", "CAT"]

# Lowered from 260 (~1 trading year) to 100 (~5 months). Checked why Park
# Medi World and Kovai Medical kept getting skipped: their NSE symbols
# (PARKHOSPS, KOVAI) are correct -- verified against TradingView, Yahoo
# Finance and Business Standard, both trade normally under these exact
# symbols. Park Medi World IPO'd in December 2025, so it mathematically
# cannot have 3 years (or even 1 year) of history yet -- 260 was simply
# too strict for a stock this young. Kovai Medical is an older, very
# thinly-traded stock (small free float), which can leave it short of a
# clean 260-row window even over 3 years. 100 rows is enough for the
# rolling features (longest window used is 20) and for walk-forward CV
# to run meaningfully; predictions from less history will show lower
# confidence automatically, which is the honest way to reflect it rather
# than refusing to predict at all.
MIN_HISTORY_ROWS = 100
HISTORY_PERIOD = "3y"   # yfinance returns whatever it has if less than this is available

# =========================
# PATHS
# =========================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(BASE_DIR, "cache")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
LEDGER_PATH = os.path.join(OUTPUT_DIR, "paper_trade_ledger.csv")
HISTORY_FILE = os.path.join(OUTPUT_DIR, "prediction_models.csv")
FINAL_FILE = os.path.join(OUTPUT_DIR, "healthcare_full_data.csv")
BACKTEST_REPORT = os.path.join(OUTPUT_DIR, "backtest_report.csv")
NEWS_ARCHIVE_FILE = os.path.join(OUTPUT_DIR, "news_archive.csv")

for d in (CACHE_DIR, OUTPUT_DIR):
    os.makedirs(d, exist_ok=True)

# =========================
# DATAVERSE SYNC (optional -- for org-wide sharing via Power BI/Power Apps)
# =========================
# Off by default. Leave DATAVERSE_SYNC_ENABLED = False until your Power
# Platform admin has completed the one-time setup in DATAVERSE_SETUP.md
# and handed you the 4 secret values below, and you've created the 4
# tables listed there. Nothing here can run without all 4 values filled
# in -- dataverse_sync.py checks for that and skips quietly (with a
# printed message) if they're blank, so main.py always still works
# locally even if this is never configured.
DATAVERSE_SYNC_ENABLED = False
DATAVERSE_ENV_URL = ""          # e.g. "https://yourorg.crm.dynamics.com" (no trailing slash)
DATAVERSE_TENANT_ID = ""        # Azure AD tenant ID, from your admin
DATAVERSE_CLIENT_ID = ""        # App registration (Application) ID, from your admin
DATAVERSE_CLIENT_SECRET = ""    # App registration client secret, from your admin
DATAVERSE_PREFIX = ""           # your publisher prefix shown when creating tables, e.g. "new_" or "cr123_"

# Exact "Entity Set Name" for each table -- found in the table's API
# settings after you create it (Power Apps maker portal -> table ->
# "..." -> Table properties -> look for "Entity set name" or check the
# API docs page). Dataverse pluralizes these automatically and not
# always predictably, so copy the real value rather than guessing.
DATAVERSE_ENTITY_SETS = {
    "predictions": "",
    "news_archive": "",
    "paper_trades": "",
    "market_indexes": "",
}
