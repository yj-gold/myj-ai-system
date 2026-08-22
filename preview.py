"""
Run this once to generate a browser-viewable HTML preview of the email.
  python preview.py
Then open  preview_email.html  in any browser.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from email_report import build_html_email

# ── Realistic mock analytics ─────────────────────────────────────────────────
MOCK = {
    "summary": {
        "total_trades": 147,
        "first_trade":  "2024-04-15 08:32:00",
        "last_trade":   "2026-04-11 15:48:00",
        "instruments_traded": 18,
        "currencies": ["GBP"],
    },
    "pnl_metrics": {
        "net_pnl":               6_842.50,
        "gross_profit":          14_210.00,
        "gross_loss":            7_367.50,
        "largest_win":           1_540.00,
        "largest_loss":          -820.00,
        "average_pnl_per_trade": 46.55,
        "average_win":           218.62,
        "average_loss":          -112.42,
        "winning_trades":        65,
        "losing_trades":         74,
        "breakeven_trades":      8,
    },
    "trade_statistics": {
        "win_rate_pct":            44.22,
        "loss_rate_pct":           50.34,
        "profit_factor":           1.929,
        "expectancy":              46.55,
        "reward_risk_ratio":       1.945,
        "kelly_criterion_pct":     21.80,
        "max_consecutive_wins":    8,
        "max_consecutive_losses":  7,
    },
    "risk_metrics": {
        "sharpe_ratio":       1.384,
        "sortino_ratio":      2.041,
        "calmar_ratio":       0.912,
        "annualised_return":  3_182.00,
        "daily_pnl_mean":     12.64,
        "daily_pnl_std":      63.80,
        "trading_days":       542,
    },
    "drawdown": {
        "max_drawdown_absolute":        -3_490.00,
        "max_drawdown_pct":             -22.6,
        "average_drawdown":             -418.30,
        "max_drawdown_duration_trades":  14,
        "total_drawdown_trades":         52,
    },
    "by_instrument": [
        {"instrument": "Gold",                "trades": 24, "net_pnl": 2_840.00, "win_rate_pct": 58.3, "profit_factor": 3.12, "avg_pnl": 118.33, "largest_win": 780.00,  "largest_loss": -310.00},
        {"instrument": "Wall Street (Dow)",   "trades": 19, "net_pnl": 1_620.00, "win_rate_pct": 52.6, "profit_factor": 2.44, "avg_pnl":  85.26, "largest_win": 540.00,  "largest_loss": -280.00},
        {"instrument": "FTSE 100",            "trades": 21, "net_pnl": 1_140.00, "win_rate_pct": 47.6, "profit_factor": 2.01, "avg_pnl":  54.29, "largest_win": 420.00,  "largest_loss": -220.00},
        {"instrument": "US Tech 100 (NAS)",   "trades": 14, "net_pnl":   840.00, "win_rate_pct": 57.1, "profit_factor": 2.68, "avg_pnl":  60.00, "largest_win": 480.00,  "largest_loss": -290.00},
        {"instrument": "EUR/USD",             "trades": 16, "net_pnl":   720.00, "win_rate_pct": 56.3, "profit_factor": 2.21, "avg_pnl":  45.00, "largest_win": 310.00,  "largest_loss": -150.00},
        {"instrument": "Brent Crude Oil",     "trades": 11, "net_pnl":   390.00, "win_rate_pct": 45.5, "profit_factor": 1.72, "avg_pnl":  35.45, "largest_win": 240.00,  "largest_loss": -180.00},
        {"instrument": "GBP/USD",             "trades":  9, "net_pnl":   280.00, "win_rate_pct": 55.6, "profit_factor": 1.98, "avg_pnl":  31.11, "largest_win": 175.00,  "largest_loss": -110.00},
        {"instrument": "Germany 40 (DAX)",    "trades":  8, "net_pnl":   145.00, "win_rate_pct": 50.0, "profit_factor": 1.43, "avg_pnl":  18.13, "largest_win": 260.00,  "largest_loss": -200.00},
        {"instrument": "Silver",              "trades":  7, "net_pnl":   -82.00, "win_rate_pct": 28.6, "profit_factor": 0.61, "avg_pnl": -11.71, "largest_win": 120.00,  "largest_loss": -230.00},
        {"instrument": "Bitcoin",             "trades":  6, "net_pnl":  -148.00, "win_rate_pct": 33.3, "profit_factor": 0.72, "avg_pnl": -24.67, "largest_win": 340.00,  "largest_loss": -490.00},
    ],
    "by_direction": {
        "BUY":  {"trades": 91, "net_pnl": 4_920.00, "win_rate_pct": 46.2, "profit_factor": 2.08},
        "SELL": {"trades": 56, "net_pnl": 1_922.50, "win_rate_pct": 41.1, "profit_factor": 1.71},
    },
    "by_month": [
        {"month": "2024-04", "trades":  7, "net_pnl":   480.00, "win_rate_pct": 57.1},
        {"month": "2024-05", "trades": 10, "net_pnl":   720.00, "win_rate_pct": 60.0},
        {"month": "2024-06", "trades":  8, "net_pnl":  -240.00, "win_rate_pct": 37.5},
        {"month": "2024-07", "trades": 11, "net_pnl":   890.00, "win_rate_pct": 54.5},
        {"month": "2024-08", "trades":  7, "net_pnl":   320.00, "win_rate_pct": 57.1},
        {"month": "2024-09", "trades":  9, "net_pnl":  -410.00, "win_rate_pct": 33.3},
        {"month": "2024-10", "trades": 12, "net_pnl":   780.00, "win_rate_pct": 58.3},
        {"month": "2024-11", "trades":  9, "net_pnl":   510.00, "win_rate_pct": 55.6},
        {"month": "2024-12", "trades":  8, "net_pnl":   290.00, "win_rate_pct": 50.0},
        {"month": "2025-01", "trades": 10, "net_pnl":   640.00, "win_rate_pct": 60.0},
        {"month": "2025-02", "trades":  9, "net_pnl":   420.00, "win_rate_pct": 55.6},
        {"month": "2025-03", "trades": 11, "net_pnl":   870.00, "win_rate_pct": 63.6},
        {"month": "2025-04", "trades":  8, "net_pnl":  -310.00, "win_rate_pct": 37.5},
        {"month": "2025-05", "trades":  9, "net_pnl":   380.00, "win_rate_pct": 55.6},
        {"month": "2025-06", "trades": 10, "net_pnl":   560.00, "win_rate_pct": 60.0},
        {"month": "2025-07", "trades":  8, "net_pnl":   342.50, "win_rate_pct": 50.0},
        {"month": "2025-08", "trades":  7, "net_pnl":   200.00, "win_rate_pct": 57.1},
        {"month": "2025-09", "trades":  9, "net_pnl":  -180.00, "win_rate_pct": 44.4},
        {"month": "2025-10", "trades": 10, "net_pnl":   580.00, "win_rate_pct": 60.0},
        {"month": "2025-11", "trades":  8, "net_pnl":   310.00, "win_rate_pct": 50.0},
        {"month": "2025-12", "trades":  9, "net_pnl":   390.00, "win_rate_pct": 55.6},
        {"month": "2026-01", "trades": 10, "net_pnl":   520.00, "win_rate_pct": 60.0},
        {"month": "2026-02", "trades":  8, "net_pnl":   280.00, "win_rate_pct": 50.0},
        {"month": "2026-03", "trades":  9, "net_pnl":   440.00, "win_rate_pct": 55.6},
        {"month": "2026-04", "trades":  7, "net_pnl":   338.00, "win_rate_pct": 57.1},
    ],
    "by_day_of_week": [
        {"day": "Monday",    "trades": 28, "net_pnl": 1_240.00, "win_rate_pct": 50.0, "avg_pnl":  44.29},
        {"day": "Tuesday",   "trades": 34, "net_pnl": 1_820.00, "win_rate_pct": 52.9, "avg_pnl":  53.53},
        {"day": "Wednesday", "trades": 31, "net_pnl": 1_540.00, "win_rate_pct": 51.6, "avg_pnl":  49.68},
        {"day": "Thursday",  "trades": 30, "net_pnl": 1_380.00, "win_rate_pct": 50.0, "avg_pnl":  46.00},
        {"day": "Friday",    "trades": 24, "net_pnl":   862.50, "win_rate_pct": 41.7, "avg_pnl":  35.94},
    ],
    "by_hour": [],
    "equity_curve": [],
    "recent_trades": [
        {"date": "2026-04-11 15:48:00", "instrument": "Gold",              "direction": "BUY",  "size": 2.0, "open_level": 3271.0, "close_level": 3309.0, "pnl":  760.00, "result": "WIN"},
        {"date": "2026-04-11 10:22:00", "instrument": "FTSE 100",          "direction": "BUY",  "size": 5.0, "open_level": 8395.0, "close_level": 8421.0, "pnl":  130.00, "result": "WIN"},
        {"date": "2026-04-10 16:05:00", "instrument": "EUR/USD",           "direction": "SELL", "size":10.0, "open_level":  1.0948,"close_level":  1.0912,"pnl":  360.00, "result": "WIN"},
        {"date": "2026-04-10 09:18:00", "instrument": "Wall Street (Dow)", "direction": "BUY",  "size": 3.0, "open_level":40812.0,"close_level":40760.0, "pnl": -156.00, "result": "LOSS"},
        {"date": "2026-04-09 14:32:00", "instrument": "US Tech 100",       "direction": "SELL", "size": 2.0, "open_level":17840.0,"close_level":17910.0, "pnl": -140.00, "result": "LOSS"},
        {"date": "2026-04-09 08:55:00", "instrument": "Gold",              "direction": "BUY",  "size": 1.0, "open_level": 3255.0,"close_level": 3268.0, "pnl":  130.00, "result": "WIN"},
        {"date": "2026-04-08 14:10:00", "instrument": "Brent Crude Oil",   "direction": "BUY",  "size": 5.0, "open_level":   85.4,"close_level":   86.1, "pnl":  350.00, "result": "WIN"},
        {"date": "2026-04-08 09:02:00", "instrument": "GBP/USD",           "direction": "BUY",  "size": 8.0, "open_level":  1.284,"close_level":  1.2795,"pnl": -360.00, "result": "LOSS"},
        {"date": "2026-04-07 15:48:00", "instrument": "FTSE 100",          "direction": "SELL", "size": 4.0, "open_level": 8380.0,"close_level": 8355.0, "pnl":  100.00, "result": "WIN"},
        {"date": "2026-04-07 10:30:00", "instrument": "Germany 40 (DAX)",  "direction": "BUY",  "size": 2.0, "open_level":21240.0,"close_level":21310.0,"pnl":  140.00, "result": "WIN"},
        {"date": "2026-04-04 14:20:00", "instrument": "Gold",              "direction": "SELL", "size": 1.5, "open_level": 3298.0,"close_level": 3245.0, "pnl":  795.00, "result": "WIN"},
        {"date": "2026-04-04 09:45:00", "instrument": "EUR/USD",           "direction": "BUY",  "size": 8.0, "open_level":  1.0872,"close_level": 1.0831,"pnl": -328.00, "result": "LOSS"},
        {"date": "2026-04-03 16:12:00", "instrument": "Wall Street (Dow)", "direction": "SELL", "size": 2.0, "open_level":40950.0,"close_level":40880.0,"pnl":  140.00, "result": "WIN"},
        {"date": "2026-04-03 08:50:00", "instrument": "Silver",            "direction": "BUY",  "size": 5.0, "open_level":   32.4,"close_level":   31.8,"pnl": -300.00, "result": "LOSS"},
        {"date": "2026-04-02 13:30:00", "instrument": "US Tech 100",       "direction": "BUY",  "size": 1.0, "open_level":17620.0,"close_level":17780.0,"pnl":  160.00, "result": "WIN"},
    ],
}

MOCK_ACCOUNTS = [
    {
        "accountId":   "BRAHYA68881394",
        "accountName": "MYJ Capital",
        "accountType": "SPREADBET",
        "currency":    "GBP",
        "balance": {
            "balance":     15_842.50,
            "available":   11_204.80,
            "deposit":      4_637.70,
            "profitLoss":   6_842.50,
        },
    }
]

if __name__ == "__main__":
    html = build_html_email(
        analytics=MOCK,
        accounts=MOCK_ACCOUNTS,
        from_date="2024-04-12",
        to_date="2026-04-12",
    )

    out = "preview_email.html"
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Preview saved → {out}")
    print("Open it in your browser to see the exact email design.")
