"""
MYJ Capital — Market universe configuration.

Contains IG epic codes for all commodities and FX pairs we scan.
Epic codes are for UK Spread Bet (Daily Funded Bet) accounts.

If an epic doesn't work on your account, use the search helper:
    python market_scanner.py --search "Gold"
which calls GET /markets?searchTerm=... and lists valid epics.
"""

# Each entry:
#   name        : human-readable label
#   epic        : IG spreadbet DFB epic code
#   type        : COMMODITY | FX | INDEX
#   point_value : £ per point per £1/point bet (always 1 for spreadbet)
#   min_size    : minimum bet size (£/point)
#   currency    : price currency
#   pip_size    : smallest price increment (for display)

MARKETS = [
    # ── COMMODITIES ──────────────────────────────────────────────────────────
    {
        "name":        "Gold",
        "epic":        "CS.D.CFDGOLD.CFDQ.IP",
        "type":        "COMMODITY",
        "point_value": 1.0,
        "min_size":    0.5,
        "currency":    "USD",
        "pip_size":    0.1,
    },
    {
        "name":        "Silver",
        "epic":        "CS.D.CFDSILVER.CFD.IP",
        "type":        "COMMODITY",
        "point_value": 1.0,
        "min_size":    0.5,
        "currency":    "USD",
        "pip_size":    0.01,
    },
    {
        "name":        "Brent Crude Oil",
        "epic":        "IC.D.BRENT.DAILY.IP",
        "type":        "COMMODITY",
        "point_value": 1.0,
        "min_size":    0.5,
        "currency":    "USD",
        "pip_size":    0.01,
    },
    {
        "name":        "WTI Crude Oil",
        "epic":        "IC.D.OIL.DAILY.IP",
        "type":        "COMMODITY",
        "point_value": 1.0,
        "min_size":    0.5,
        "currency":    "USD",
        "pip_size":    0.01,
    },
    {
        "name":        "Natural Gas",
        "epic":        "IC.D.NATGAS.DAILY.IP",
        "type":        "COMMODITY",
        "point_value": 1.0,
        "min_size":    0.5,
        "currency":    "USD",
        "pip_size":    0.001,
    },
    # ── FX MAJORS ────────────────────────────────────────────────────────────
    {
        "name":        "EUR/USD",
        "epic":        "CS.D.EURUSD.MINI.IP",
        "type":        "FX",
        "point_value": 1.0,
        "min_size":    0.5,
        "currency":    "USD",
        "pip_size":    0.0001,
    },
    {
        "name":        "GBP/USD",
        "epic":        "CS.D.GBPUSD.MINI.IP",
        "type":        "FX",
        "point_value": 1.0,
        "min_size":    0.5,
        "currency":    "USD",
        "pip_size":    0.0001,
    },
    {
        "name":        "USD/JPY",
        "epic":        "CS.D.USDJPY.MINI.IP",
        "type":        "FX",
        "point_value": 1.0,
        "min_size":    0.5,
        "currency":    "JPY",
        "pip_size":    0.01,
    },
    {
        "name":        "AUD/USD",
        "epic":        "CS.D.AUDUSD.MINI.IP",
        "type":        "FX",
        "point_value": 1.0,
        "min_size":    0.5,
        "currency":    "USD",
        "pip_size":    0.0001,
    },
    {
        "name":        "USD/CHF",
        "epic":        "CS.D.USDCHF.MINI.IP",
        "type":        "FX",
        "point_value": 1.0,
        "min_size":    0.5,
        "currency":    "CHF",
        "pip_size":    0.0001,
    },
    {
        "name":        "EUR/GBP",
        "epic":        "CS.D.EURGBP.MINI.IP",
        "type":        "FX",
        "point_value": 1.0,
        "min_size":    0.5,
        "currency":    "GBP",
        "pip_size":    0.0001,
    },
    {
        "name":        "USD/CAD",
        "epic":        "CS.D.USDCAD.MINI.IP",
        "type":        "FX",
        "point_value": 1.0,
        "min_size":    0.5,
        "currency":    "CAD",
        "pip_size":    0.0001,
    },
    {
        "name":        "NZD/USD",
        "epic":        "CS.D.NZDUSD.MINI.IP",
        "type":        "FX",
        "point_value": 1.0,
        "min_size":    0.5,
        "currency":    "USD",
        "pip_size":    0.0001,
    },
]

# Risk parameters (can be overridden via .env)
DEFAULT_RISK_PCT      = 1.0   # % of account equity risked per trade
MAX_UNITS_PER_MARKET  = 4     # Turtle rule: max 4 units in one market
MAX_UNITS_CORRELATED  = 10    # max units in correlated markets (e.g. all FX)
MAX_UNITS_DIRECTION   = 12    # max total long or short units across all markets
ATR_STOP_MULTIPLIER   = 2.0   # stop loss distance = N * ATR
ATR_TARGET_MULTIPLIER = 4.0   # take profit = N * ATR  (2:1 R:R)
PYRAMID_STEP          = 0.5   # add unit every 0.5 ATR in your favour
