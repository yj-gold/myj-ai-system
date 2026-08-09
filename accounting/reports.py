"""Financial reports: balance sheet, income statement, cash flow, CAPEX,
intercompany positions and cash pooling overview.

All reports are multi-currency aware: accounts carry a currency (empty =
entity base currency), and totals are reported per currency — amounts in
different currencies are never summed together.
"""

from .ledger import list_entities


def _balances(conn, entity_id, as_of=None, date_from=None):
    """Per-account debit-positive balances, keyed by account code."""
    query = """SELECT a.code, a.name, a.type, a.subtype, a.is_capex,
                      a.is_intercompany, a.counterparty_entity_id, a.currency,
                      COALESCE(SUM(l.debit - l.credit), 0) AS bal
               FROM accounts a
               LEFT JOIN journal_lines l ON l.account_id = a.id
               LEFT JOIN journal_entries e ON e.id = l.entry_id"""
    conditions = ["a.entity_id = :eid"]
    params = {"eid": entity_id}
    if as_of:
        conditions.append("(e.date IS NULL OR e.date <= :as_of)")
        params["as_of"] = as_of
    if date_from:
        conditions.append("(e.date IS NULL OR e.date >= :date_from)")
        params["date_from"] = date_from
    query += " WHERE " + " AND ".join(conditions)
    query += " GROUP BY a.id ORDER BY a.code"
    return conn.execute(query, params).fetchall()


def balance_sheet(conn, entity, as_of=None):
    """Assets / liabilities / equity as of a date, with per-currency totals.
    Net income for the period is folded into equity so the sheet balances."""
    base = entity["currency"]
    rows = _balances(conn, entity["id"], as_of=as_of)
    assets, liabilities, equity = [], [], []
    net_income = {}
    currencies = set()
    for r in rows:
        bal = round(r["bal"], 2)
        ccy = r["currency"] or base
        if bal == 0 and r["type"] not in ("income", "expense"):
            continue
        currencies.add(ccy)
        if r["type"] == "asset":
            assets.append((r["code"], r["name"], bal, ccy))
        elif r["type"] == "liability":
            liabilities.append((r["code"], r["name"], -bal, ccy))
        elif r["type"] == "equity":
            equity.append((r["code"], r["name"], -bal, ccy))
        elif r["type"] == "income":
            net_income[ccy] = net_income.get(ccy, 0.0) - bal
        elif r["type"] == "expense":
            net_income[ccy] = net_income.get(ccy, 0.0) - bal
    for ccy, amount in sorted(net_income.items()):
        if round(amount, 2) != 0:
            equity.append(("", "Net income (period to date)",
                           round(amount, 2), ccy))
            currencies.add(ccy)

    totals = {}
    for ccy in sorted(currencies):
        total_assets = round(sum(a[2] for a in assets if a[3] == ccy), 2)
        total_liabilities = round(
            sum(l[2] for l in liabilities if l[3] == ccy), 2)
        total_equity = round(sum(e[2] for e in equity if e[3] == ccy), 2)
        totals[ccy] = {
            "assets": total_assets,
            "liabilities": total_liabilities,
            "equity": total_equity,
            "net_worth": round(total_assets - total_liabilities, 2),
        }
    return {"assets": assets, "liabilities": liabilities, "equity": equity,
            "totals": totals}


def income_statement(conn, entity, date_from=None, date_to=None):
    base = entity["currency"]
    rows = _balances(conn, entity["id"], as_of=date_to, date_from=date_from)
    income, expenses = [], []
    currencies = set()
    for r in rows:
        bal = round(r["bal"], 2)
        if bal == 0:
            continue
        ccy = r["currency"] or base
        if r["type"] == "income":
            income.append((r["code"], r["name"], -bal, ccy))
            currencies.add(ccy)
        elif r["type"] == "expense":
            expenses.append((r["code"], r["name"], bal, ccy))
            currencies.add(ccy)
    totals = {}
    for ccy in sorted(currencies):
        total_income = round(sum(i[2] for i in income if i[3] == ccy), 2)
        total_expenses = round(sum(e[2] for e in expenses if e[3] == ccy), 2)
        totals[ccy] = {
            "income": total_income,
            "expenses": total_expenses,
            "net_income": round(total_income - total_expenses, 2),
        }
    return {"income": income, "expenses": expenses, "totals": totals}


def cash_flow(conn, entity, date_from=None, date_to=None):
    """Cash movements per currency, classified operating / investing /
    financing based on the counter-accounts of entries touching cash."""
    base = entity["currency"]
    query = """
        SELECT e.id AS entry_id, e.date, e.description,
               COALESCE(NULLIF(a.currency, ''), :base) AS ccy,
               SUM(l.debit - l.credit) AS cash_delta
        FROM journal_entries e
        JOIN journal_lines l ON l.entry_id = e.id
        JOIN accounts a ON a.id = l.account_id
        WHERE e.entity_id = :eid AND a.subtype = 'cash'"""
    params = {"eid": entity["id"], "base": base}
    if date_from:
        query += " AND e.date >= :dfrom"
        params["dfrom"] = date_from
    if date_to:
        query += " AND e.date <= :dto"
        params["dto"] = date_to
    query += " GROUP BY e.id, ccy HAVING cash_delta != 0"
    entries = conn.execute(query, params).fetchall()

    result = {}
    for entry in entries:
        ccy = entry["ccy"]
        if ccy not in result:
            result[ccy] = {"operating": 0.0, "investing": 0.0,
                           "financing": 0.0, "net_change": 0.0,
                           "details": {"operating": [], "investing": [],
                                       "financing": []}}
        counters = conn.execute(
            """SELECT a.type, a.subtype, a.is_capex, a.is_intercompany
               FROM journal_lines l JOIN accounts a ON a.id = l.account_id
               WHERE l.entry_id = ? AND a.subtype != 'cash'""",
            (entry["entry_id"],),
        ).fetchall()
        bucket = "operating"
        for c in counters:
            if c["is_capex"] or c["subtype"] == "fixed_asset":
                bucket = "investing"
                break
            if (c["subtype"] == "financing" or c["type"] == "equity"
                    or c["is_intercompany"]):
                bucket = "financing"
                break
        delta = round(entry["cash_delta"], 2)
        result[ccy][bucket] = round(result[ccy][bucket] + delta, 2)
        result[ccy]["net_change"] = round(result[ccy]["net_change"] + delta, 2)
        result[ccy]["details"][bucket].append(
            (entry["date"], entry["description"], delta))
    return result


def capex_register(conn, entity, date_from=None, date_to=None):
    """All movements on CAPEX (fixed asset) accounts, with currency."""
    query = """
        SELECT e.date, e.description, a.code, a.name,
               COALESCE(NULLIF(a.currency, ''), :base) AS ccy,
               l.debit - l.credit AS amount
        FROM journal_lines l
        JOIN accounts a ON a.id = l.account_id
        JOIN journal_entries e ON e.id = l.entry_id
        WHERE a.entity_id = :eid AND a.is_capex = 1"""
    params = {"eid": entity["id"], "base": entity["currency"]}
    if date_from:
        query += " AND e.date >= :dfrom"
        params["dfrom"] = date_from
    if date_to:
        query += " AND e.date <= :dto"
        params["dto"] = date_to
    query += " ORDER BY e.date"
    rows = conn.execute(query, params).fetchall()
    totals = {}
    for r in rows:
        totals[r["ccy"]] = round(totals.get(r["ccy"], 0.0) + r["amount"], 2)
    return {"items": rows, "totals": totals}


def intercompany_matrix(conn):
    """Net intercompany position per entity and currency."""
    entities = list_entities(conn)
    positions = []
    for ent in entities:
        rows = conn.execute(
            """SELECT a.code, a.name, a.type, a.counterparty_entity_id,
                      COALESCE(NULLIF(a.currency, ''), :base) AS ccy,
                      COALESCE(SUM(l.debit - l.credit), 0) AS bal
               FROM accounts a
               LEFT JOIN journal_lines l ON l.account_id = a.id
               WHERE a.entity_id = :eid AND a.is_intercompany = 1
               GROUP BY a.id""",
            {"eid": ent["id"], "base": ent["currency"]},
        ).fetchall()
        nets = {}
        for r in rows:
            nets[r["ccy"]] = round(nets.get(r["ccy"], 0.0) + r["bal"], 2)
        if any(r["bal"] for r in rows):
            positions.append({"entity": ent, "nets": nets, "accounts": rows})
    return positions


def cash_pooling_overview(conn, as_of=None):
    """Cash and net intercompany position per entity AND currency — the
    basis for a notional cash pool: who holds surplus, who is short."""
    entities = list_entities(conn)
    rows_out = []
    totals = {}
    for ent in entities:
        rows = _balances(conn, ent["id"], as_of=as_of)
        per_ccy = {}
        for r in rows:
            ccy = r["currency"] or ent["currency"]
            bucket = per_ccy.setdefault(ccy, {"cash": 0.0, "ic": 0.0})
            if r["subtype"] == "cash":
                bucket["cash"] += r["bal"]
            elif r["is_intercompany"]:
                bucket["ic"] += r["bal"]
        for ccy in sorted(per_ccy):
            cash = round(per_ccy[ccy]["cash"], 2)
            ic = round(per_ccy[ccy]["ic"], 2)
            if cash == 0 and ic == 0:
                continue
            rows_out.append({
                "entity": ent,
                "ccy": ccy,
                "cash": cash,
                "intercompany_net": ic,
                "pooled_position": round(cash + ic, 2),
            })
            totals[ccy] = round(totals.get(ccy, 0.0) + cash, 2)
    return {"rows": rows_out, "total_cash": totals}
