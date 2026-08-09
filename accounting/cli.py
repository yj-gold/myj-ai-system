"""Command-line interface for the MYJ accounting tool.

Run via:  python myj_accounting.py <command> ...
"""

import argparse
import sys

from . import db
from .importer import add_rule, import_csv, recategorize_suspense
from .ledger import (LedgerError, add_account, add_entity, add_entry,
                     get_entity, list_accounts, list_entities)
from .reports import (balance_sheet, capex_register, cash_flow,
                      cash_pooling_overview, income_statement,
                      intercompany_matrix)


def _money(value, currency=""):
    formatted = f"{value:,.2f}"
    return f"{formatted} {currency}".strip() if currency else formatted


def _print_section(title, rows, currency, total_label, total):
    print(f"\n{title}")
    print("-" * 62)
    for code, name, amount in rows:
        label = f"{code}  {name}" if code else name
        print(f"  {label:<44} {_money(amount, ''):>15}")
    print(f"  {total_label:<44} {_money(total, ''):>15}")


# ------------------------------------------------------------- commands

def cmd_entity_add(conn, args):
    entity_id = add_entity(conn, args.code, args.name,
                           currency=args.currency, country=args.country)
    print(f"Added entity {args.code.upper()} — {args.name} "
          f"({args.currency.upper()}), id={entity_id}. "
          f"Default chart of accounts created.")


def cmd_entity_list(conn, args):
    rows = list_entities(conn)
    if not rows:
        print("No entities yet. Add one:\n"
              '  python myj_accounting.py entity add MYJCT '
              '"MYJ Currency Trading S.C.Sp." --currency EUR')
        return
    for r in rows:
        print(f"  {r['code']:<8} {r['name']:<45} {r['currency']} {r['country']}")


def cmd_accounts_list(conn, args):
    entity = get_entity(conn, args.entity)
    for a in list_accounts(conn, entity["id"]):
        flags = []
        if a["is_capex"]:
            flags.append("CAPEX")
        if a["is_intercompany"]:
            flags.append("IC")
        flag_str = f" [{','.join(flags)}]" if flags else ""
        print(f"  {a['code']:<6} {a['name']:<52} {a['type']:<9}{flag_str}")


def cmd_account_add(conn, args):
    entity = get_entity(conn, args.entity)
    counterparty_id = None
    if args.counterparty:
        counterparty_id = get_entity(conn, args.counterparty)["id"]
    add_account(conn, entity["id"], args.code, args.name, args.type,
                subtype=args.subtype, is_capex=args.capex,
                is_intercompany=args.intercompany or bool(counterparty_id),
                counterparty_entity_id=counterparty_id)
    print(f"Added account {args.code} — {args.name} ({args.type}).")


def cmd_import(conn, args):
    entity = get_entity(conn, args.entity)
    statement_id, imported, uncategorized = import_csv(
        conn, entity, args.file, cash_account_code=args.cash_account,
        date_col=args.date_col, desc_col=args.desc_col,
        amount_col=args.amount_col, debit_col=args.debit_col,
        credit_col=args.credit_col, delimiter=args.delimiter)
    print(f"Imported {imported} transactions from {args.file} "
          f"(statement #{statement_id}) into {entity['code']} "
          f"account {args.cash_account}.")
    if uncategorized:
        print(f"  {uncategorized} transactions went to suspense (9000).")
        print("  Add rules with:  rule add \"<text in description>\" <account code>")
        print("  Then run:        recategorize --entity", entity["code"])


def cmd_rule_add(conn, args):
    entity_id = get_entity(conn, args.entity)["id"] if args.entity else None
    add_rule(conn, args.pattern, args.account, entity_id=entity_id,
             note=args.note)
    scope = args.entity.upper() if args.entity else "all entities"
    print(f"Rule added ({scope}): '{args.pattern}' -> account {args.account}")


def cmd_rule_list(conn, args):
    rows = conn.execute(
        """SELECT r.*, e.code AS entity_code FROM categorization_rules r
           LEFT JOIN entities e ON e.id = r.entity_id ORDER BY r.id"""
    ).fetchall()
    if not rows:
        print("No custom rules (built-in defaults still apply).")
        return
    for r in rows:
        scope = r["entity_code"] or "ALL"
        print(f"  #{r['id']:<4} [{scope:<6}] '{r['pattern']}' -> {r['account_code']}"
              f"  {r['note']}")


def cmd_recategorize(conn, args):
    entity = get_entity(conn, args.entity)
    moved = recategorize_suspense(conn, entity)
    print(f"Recategorized {moved} suspense transactions for {entity['code']}.")


def cmd_entry_add(conn, args):
    entity = get_entity(conn, args.entity)
    lines = []
    for spec in args.line:
        parts = spec.split(":")
        if len(parts) < 2:
            raise LedgerError(
                "Line format: ACCOUNT:AMOUNT (positive=debit, negative=credit), "
                "e.g. 1500:2500 1000:-2500")
        code = parts[0]
        amount = float(parts[1])
        memo = parts[2] if len(parts) > 2 else ""
        if amount >= 0:
            lines.append((code, amount, 0, memo))
        else:
            lines.append((code, 0, -amount, memo))
    entry_id = add_entry(conn, entity["id"], args.date, args.description, lines)
    print(f"Journal entry #{entry_id} recorded for {entity['code']}.")


def cmd_report_balance(conn, args):
    entity = get_entity(conn, args.entity)
    report = balance_sheet(conn, entity, as_of=args.as_of)
    currency = entity["currency"]
    when = args.as_of or "today"
    print(f"\nBALANCE SHEET — {entity['name']} ({currency}) as of {when}")
    _print_section("ASSETS", report["assets"], currency,
                   "TOTAL ASSETS", report["total_assets"])
    _print_section("LIABILITIES", report["liabilities"], currency,
                   "TOTAL LIABILITIES", report["total_liabilities"])
    _print_section("EQUITY", report["equity"], currency,
                   "TOTAL EQUITY", report["total_equity"])
    print(f"\n  NET WORTH (assets - liabilities): "
          f"{_money(report['net_worth'], currency)}")


def cmd_report_pnl(conn, args):
    entity = get_entity(conn, args.entity)
    report = income_statement(conn, entity, date_from=args.date_from,
                              date_to=args.date_to)
    currency = entity["currency"]
    period = f"{args.date_from or 'start'} to {args.date_to or 'today'}"
    print(f"\nINCOME STATEMENT — {entity['name']} ({currency}), {period}")
    _print_section("INCOME", report["income"], currency,
                   "TOTAL INCOME", report["total_income"])
    _print_section("EXPENSES", report["expenses"], currency,
                   "TOTAL EXPENSES", report["total_expenses"])
    print(f"\n  NET INCOME: {_money(report['net_income'], currency)}")


def cmd_report_cashflow(conn, args):
    entity = get_entity(conn, args.entity)
    report = cash_flow(conn, entity, date_from=args.date_from,
                       date_to=args.date_to)
    currency = entity["currency"]
    period = f"{args.date_from or 'start'} to {args.date_to or 'today'}"
    print(f"\nCASH FLOW — {entity['name']} ({currency}), {period}")
    print("-" * 62)
    for bucket in ("operating", "investing", "financing"):
        print(f"  {bucket.capitalize():<44} {_money(report[bucket]):>15}")
        if args.detail:
            for date, desc, delta in report["details"][bucket]:
                print(f"      {date}  {desc[:36]:<36} {_money(delta):>12}")
    print(f"  {'NET CHANGE IN CASH':<44} {_money(report['net_change']):>15}")


def cmd_report_capex(conn, args):
    entity = get_entity(conn, args.entity)
    report = capex_register(conn, entity, date_from=args.date_from,
                            date_to=args.date_to)
    currency = entity["currency"]
    print(f"\nCAPEX REGISTER — {entity['name']} ({currency})")
    print("-" * 62)
    if not report["items"]:
        print("  No CAPEX movements recorded.")
    for r in report["items"]:
        print(f"  {r['date']}  {r['code']}  {r['description'][:34]:<34} "
              f"{_money(r['amount']):>12}")
    print(f"  {'TOTAL CAPEX':<48} {_money(report['total']):>12}")


def cmd_report_pooling(conn, args):
    overview = cash_pooling_overview(conn, as_of=args.as_of)
    print("\nCASH POOLING OVERVIEW (all entities)")
    print("-" * 70)
    print(f"  {'Entity':<10} {'Cash':>14} {'IC net':>14} {'Pooled':>14}  Ccy")
    for row in overview["entities"]:
        ent = row["entity"]
        print(f"  {ent['code']:<10} {_money(row['cash']):>14} "
              f"{_money(row['intercompany_net']):>14} "
              f"{_money(row['pooled_position']):>14}  {ent['currency']}")
    print(f"\n  Total cash across entities: {_money(overview['total_cash'])}")
    print("  (positions are in each entity's own currency — do not sum across"
          " currencies)")
    surplus = [r for r in overview["entities"] if r["pooled_position"] > 0]
    deficit = [r for r in overview["entities"] if r["pooled_position"] < 0]
    if surplus and deficit:
        print("\n  Pooling opportunity: surplus at "
              + ", ".join(r["entity"]["code"] for r in surplus)
              + " could fund " + ", ".join(r["entity"]["code"] for r in deficit)
              + " via intercompany loans (document terms and arm's-length"
                " interest).")


def cmd_report_intercompany(conn, args):
    positions = intercompany_matrix(conn)
    print("\nINTERCOMPANY POSITIONS")
    print("-" * 62)
    if not positions:
        print("  No intercompany accounts with activity.")
    for pos in positions:
        ent = pos["entity"]
        print(f"  {ent['code']} net intercompany: "
              f"{_money(pos['net'], ent['currency'])}")
        for a in pos["accounts"]:
            if a["bal"]:
                print(f"      {a['code']} {a['name']:<40} {_money(a['bal']):>12}")


# ------------------------------------------------------------- parser

def build_parser():
    parser = argparse.ArgumentParser(
        prog="myj_accounting",
        description="MYJ private multi-entity accounting tool (local data only).")
    sub = parser.add_subparsers(dest="command", required=True)

    entity = sub.add_parser("entity", help="Manage entities (companies)")
    entity_sub = entity.add_subparsers(dest="subcommand", required=True)
    add_ent = entity_sub.add_parser("add")
    add_ent.add_argument("code", help="Short code, e.g. MYJCT")
    add_ent.add_argument("name", help='Full name, e.g. "MYJ Currency Trading S.C.Sp."')
    add_ent.add_argument("--currency", default="EUR")
    add_ent.add_argument("--country", default="")
    add_ent.set_defaults(func=cmd_entity_add)
    entity_sub.add_parser("list").set_defaults(func=cmd_entity_list)

    accounts = sub.add_parser("accounts", help="List chart of accounts")
    accounts.add_argument("--entity", required=True)
    accounts.set_defaults(func=cmd_accounts_list)

    account = sub.add_parser("account", help="Add a custom account")
    account_sub = account.add_subparsers(dest="subcommand", required=True)
    acc_add = account_sub.add_parser("add")
    acc_add.add_argument("code")
    acc_add.add_argument("name")
    acc_add.add_argument("type",
                         choices=["asset", "liability", "equity", "income", "expense"])
    acc_add.add_argument("--entity", required=True)
    acc_add.add_argument("--subtype", default="")
    acc_add.add_argument("--capex", action="store_true")
    acc_add.add_argument("--intercompany", action="store_true")
    acc_add.add_argument("--counterparty",
                         help="Entity code on the other side (intercompany)")
    acc_add.set_defaults(func=cmd_account_add)

    imp = sub.add_parser("import", help="Import a bank/broker statement CSV")
    imp.add_argument("file")
    imp.add_argument("--entity", required=True)
    imp.add_argument("--cash-account", default="1000",
                     help="Cash account the statement belongs to (default 1000; "
                          "use 1010 for a brokerage account)")
    imp.add_argument("--date-col")
    imp.add_argument("--desc-col")
    imp.add_argument("--amount-col")
    imp.add_argument("--debit-col")
    imp.add_argument("--credit-col")
    imp.add_argument("--delimiter")
    imp.set_defaults(func=cmd_import)

    rule = sub.add_parser("rule", help="Categorization rules for imports")
    rule_sub = rule.add_subparsers(dest="subcommand", required=True)
    rule_add_p = rule_sub.add_parser("add")
    rule_add_p.add_argument("pattern",
                            help="Substring to match in description, or /regex/")
    rule_add_p.add_argument("account", help="Counter-account code, e.g. 5100")
    rule_add_p.add_argument("--entity", help="Limit rule to one entity")
    rule_add_p.add_argument("--note", default="")
    rule_add_p.set_defaults(func=cmd_rule_add)
    rule_sub.add_parser("list").set_defaults(func=cmd_rule_list)

    recat = sub.add_parser("recategorize",
                           help="Re-apply rules to suspense transactions")
    recat.add_argument("--entity", required=True)
    recat.set_defaults(func=cmd_recategorize)

    entry = sub.add_parser("entry", help="Manual journal entries")
    entry_sub = entry.add_subparsers(dest="subcommand", required=True)
    entry_add_p = entry_sub.add_parser("add")
    entry_add_p.add_argument("--entity", required=True)
    entry_add_p.add_argument("--date", required=True, help="YYYY-MM-DD")
    entry_add_p.add_argument("--description", required=True)
    entry_add_p.add_argument("line", nargs="+",
                             help="ACCOUNT:AMOUNT[:memo]; positive=debit, "
                                  "negative=credit. Must balance to zero.")
    entry_add_p.set_defaults(func=cmd_entry_add)

    report = sub.add_parser("report", help="Financial reports")
    report_sub = report.add_subparsers(dest="subcommand", required=True)

    bs = report_sub.add_parser("balance-sheet")
    bs.add_argument("--entity", required=True)
    bs.add_argument("--as-of")
    bs.set_defaults(func=cmd_report_balance)

    pnl = report_sub.add_parser("pnl")
    pnl.add_argument("--entity", required=True)
    pnl.add_argument("--date-from")
    pnl.add_argument("--date-to")
    pnl.set_defaults(func=cmd_report_pnl)

    cf = report_sub.add_parser("cashflow")
    cf.add_argument("--entity", required=True)
    cf.add_argument("--date-from")
    cf.add_argument("--date-to")
    cf.add_argument("--detail", action="store_true")
    cf.set_defaults(func=cmd_report_cashflow)

    capex = report_sub.add_parser("capex")
    capex.add_argument("--entity", required=True)
    capex.add_argument("--date-from")
    capex.add_argument("--date-to")
    capex.set_defaults(func=cmd_report_capex)

    pooling = report_sub.add_parser("pooling")
    pooling.add_argument("--as-of")
    pooling.set_defaults(func=cmd_report_pooling)

    ic = report_sub.add_parser("intercompany")
    ic.set_defaults(func=cmd_report_intercompany)

    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    conn = db.connect()
    try:
        args.func(conn, args)
    except LedgerError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
