#!/usr/bin/env python3
"""
IG Markets Trading Analytics
==============================

Connects to the IG REST API, downloads your complete trade history, and
produces a detailed strategy performance report including:

  • Net / gross P&L, win rate, profit factor, expectancy
  • Sharpe, Sortino and Calmar ratios
  • Drawdown analysis (max / average / duration)
  • Breakdown by instrument, direction, month, day-of-week and hour
  • Open positions summary
  • CSV exports for transactions, activity and equity curve
  • JSON export of the full analytics object
  • HTML email report sent automatically via SMTP

Usage
-----
1. Copy .env.example → .env and fill in your IG credentials + API key.
2. Add EMAIL_* settings to .env for automatic email delivery.
3. pip install -r requirements.txt
4. python main.py

Optional CLI flags
------------------
  --from YYYY-MM-DD   Start date (default: 2 years ago)
  --to   YYYY-MM-DD   End date   (default: today)
  --no-activity       Skip fetching activity log (faster)
  --no-export         Do not write CSV / JSON files
  --no-email          Skip sending the email report
  --output-dir PATH   Directory for exports (default: ./output)
  --demo              Force demo account endpoint
  --debug             Enable verbose logging
"""

import argparse
import logging
import sys

import config
from ig_client import IGClient, IGAPIError
from data_extractor import DataExtractor
from analytics import TradingAnalytics
from report import (
    generate_console_report,
    export_transactions_csv,
    export_activity_csv,
    export_analytics_json,
    export_equity_curve_csv,
)
from email_report import build_html_email, send_email_report


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="IG Markets trading analytics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--from", dest="from_date", metavar="YYYY-MM-DD",
        default=config.ANALYSIS_FROM_DATE,
        help=f"Start date (default: {config.ANALYSIS_FROM_DATE})",
    )
    p.add_argument(
        "--to", dest="to_date", metavar="YYYY-MM-DD",
        default=config.ANALYSIS_TO_DATE,
        help=f"End date (default: {config.ANALYSIS_TO_DATE})",
    )
    p.add_argument(
        "--no-activity", action="store_true",
        help="Skip fetching the activity log (transactions only)",
    )
    p.add_argument(
        "--no-export", action="store_true",
        help="Do not write CSV / JSON output files",
    )
    p.add_argument(
        "--output-dir", default=config.OUTPUT_DIR,
        help=f"Directory for exported files (default: {config.OUTPUT_DIR})",
    )
    p.add_argument(
        "--demo", action="store_true",
        help="Use the IG demo endpoint regardless of IG_ACCOUNT_TYPE",
    )
    p.add_argument(
        "--no-email", action="store_true",
        help="Skip sending the HTML email report",
    )
    p.add_argument(
        "--debug", action="store_true",
        help="Enable verbose DEBUG logging",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s – %(message)s",
        datefmt="%H:%M:%S",
    )
    # Suppress noisy urllib3 logs unless in debug mode
    if not args.debug:
        logging.getLogger("urllib3").setLevel(logging.WARNING)

    base_url = (
        config.BASE_URL_DEMO if args.demo else config.BASE_URL
    )

    print(f"\n  Account type : {'DEMO' if args.demo else config.IG_ACCOUNT_TYPE}")
    print(f"  API endpoint : {base_url}")
    print(f"  Date range   : {args.from_date}  →  {args.to_date}")
    print(f"  Output dir   : {args.output_dir}")
    print()

    client = IGClient(base_url=base_url)

    try:
        # -----------------------------------------------------------------
        # 1. Login
        # -----------------------------------------------------------------
        client.login()

        extractor = DataExtractor(client)

        # -----------------------------------------------------------------
        # 2. Account info
        # -----------------------------------------------------------------
        accounts = extractor.get_accounts()

        # -----------------------------------------------------------------
        # 3. Open positions
        # -----------------------------------------------------------------
        open_positions = extractor.get_open_positions()

        # -----------------------------------------------------------------
        # 4. Transaction history (the main P&L data source)
        # -----------------------------------------------------------------
        transactions_df = extractor.get_transactions(
            from_date=args.from_date,
            to_date=args.to_date,
        )

        if transactions_df.empty:
            print(
                "\n  No transactions found for the requested period.\n"
                "  Check your date range and ensure your account has closed trades."
            )
            return

        print(f"\n  Loaded {len(transactions_df):,} transactions.")

        # -----------------------------------------------------------------
        # 5. Activity history (optional – richer deal-level detail)
        # -----------------------------------------------------------------
        activity_df = None
        if not args.no_activity:
            activity_df = extractor.get_activity(
                from_date=args.from_date,
                to_date=args.to_date,
            )
            print(f"  Loaded {len(activity_df):,} activity records.")

        # -----------------------------------------------------------------
        # 6. Analytics
        # -----------------------------------------------------------------
        print("\n  Running analytics …")
        engine = TradingAnalytics(transactions_df)
        analytics = engine.calculate_all()

        # -----------------------------------------------------------------
        # 7. Console report
        # -----------------------------------------------------------------
        generate_console_report(
            analytics=analytics,
            accounts=accounts,
            open_positions=open_positions if not open_positions.empty else None,
        )

        # -----------------------------------------------------------------
        # 8. Exports
        # -----------------------------------------------------------------
        if not args.no_export:
            print("  Exporting data …")
            export_transactions_csv(transactions_df, args.output_dir)
            if activity_df is not None and not activity_df.empty:
                export_activity_csv(activity_df, args.output_dir)
            export_analytics_json(analytics, args.output_dir)
            if "equity_curve" in analytics and analytics["equity_curve"]:
                export_equity_curve_csv(analytics["equity_curve"], args.output_dir)
            print()

        # -----------------------------------------------------------------
        # 9. Email report
        # -----------------------------------------------------------------
        if not args.no_email:
            print("  Building and sending email report …")
            html = build_html_email(
                analytics=analytics,
                accounts=accounts,
                from_date=args.from_date,
                to_date=args.to_date,
            )
            send_email_report(
                html=html,
                analytics=analytics,
                from_date=args.from_date,
                to_date=args.to_date,
            )
            print()

    except IGAPIError as exc:
        print(f"\n  IG API Error: {exc}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n  Interrupted by user.")
    finally:
        client.logout()


if __name__ == "__main__":
    main()
