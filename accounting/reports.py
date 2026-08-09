"""Financial reports: balance sheet, income statement, cash flow, CAPEX,
intercompany positions and cash pooling overview."""

from .ledger import list_accounts, list_entities


def _balances(conn, entity_id, as_of=None, date_from=None):
    """Per-account debit-positive balances, keyed by account code."""
    query = """SELECT a.code, a.name, a.type, a.subtype, a.is_capex,
                      a.is_intercompany, a.counterparty_entity_id,
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
    """Assets / liabilities / equity as of a date. Net income for the period
    is folded into equity so the sheet always balances."""
    rows = _balances(conn, entity["id"], as_of=as_of)
    assets, liabilities, equity = [], [], []
    net_income = 0.0
    for r in rows:
        bal = round(r["bal"], 2)
        if r["type"] == "asset":
            if bal != 0:
                assets.append((r["code"], r["name"], bal))
        elif r["type"] == "liability":
            if bal != 0:
                liabilities.append((r["code"], r["name"], -bal))
        elif r["type"] == "equity":
            if bal != 0:
                equity.append((r["code"], r["name"], -bal))
        elif r["type"] == "income":
            net_income += -bal
        elif r["type"] == "expense":
            net_income -= bal
    if round(net_income, 2) != 0:
        equity.append(("", "Net income (period to date)", round(net_income, 2)))
    total_assets = round(sum(a[2] for a in assets), 2)
    total_liabilities = round(sum(l[2] for l in liabilities), 2)
    total_equity = round(sum(e[2] for e in equity), 2)
    return {
        "assets": assets,
        "liabilities": liabilities,
        "equity": equity,
        "total_assets": total_assets,
        "total_liabilities": total_liabilities,
        "total_equity": total_equity,
        "net_worth": round(total_assets - total_liabilities, 2),
    }


def income_statement(conn, entity, date_from=None, date_to=None):
    rows = _balances(conn, entity["id"], as_of=date_to, date_from=date_from)
    income, expenses = [], []
    for r in rows:
        bal = round(r["bal"], 2)
        if r["type"] == "income" and bal != 0:
            income.append((r["code"], r["name"], -bal))
        elif r["type"] == "expense" and bal != 0:
            expenses.append((r["code"], r["name"], bal))
    total_income = round(sum(i[2] for i in income), 2)
    total_expenses = round(sum(e[2] for e in expenses), 2)
    return {
        "income": income,
        "expenses": expenses,
        "total_income": total_income,
        "total_expenses": total_expenses,
        "net_income": round(total_income - total_expenses, 2),
    }


def cash_flow(conn, entity, date_from=None, date_to=None):
    """Cash movements classified as operating / investing / financing,
    based on the counter-accounts of entries touching cash accounts."""
    query = """
        SELECT e.id AS entry_id, e.date, e.description,
               SUM(CASE WHEN a.subtype = 'cash' THEN l.debit - l.credit ELSE 0 END) AS cash_delta
        FROM journal_entries e
        JOIN journal_lines l ON l.entry_id = e.id
        JOIN accounts a ON a.id = l.account_id
        WHERE e.entity_id = :eid
        GROUP BY e.id HAVING cash_delta != 0"""
    params = {"eid": entity["id"]}
    if date_from:
        query = query.replace("WHERE e.entity_id = :eid",
                              "WHERE e.entity_id = :eid AND e.date >= :dfrom")
        params["dfrom"] = date_from
    if date_to:
        query = query.replace("GROUP BY", "AND e.date <= :dto GROUP BY")
        params["dto"] = date_to
    entries = conn.execute(query, params).fetchall()

    buckets = {"operating": 0.0, "investing": 0.0, "financing": 0.0}
    details = {"operating": [], "investing": [], "financing": []}
    for entry in entries:
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
        buckets[bucket] += delta
        details[bucket].append((entry["date"], entry["description"], delta))

    total = round(sum(buckets.values()), 2)
    return {
        "operating": round(buckets["operating"], 2),
        "investing": round(buckets["investing"], 2),
        "financing": round(buckets["financing"], 2),
        "net_change": total,
        "details": details,
    }


def capex_register(conn, entity, date_from=None, date_to=None):
    """All movements on CAPEX (fixed asset) accounts."""
    query = """
        SELECT e.date, e.description, a.code, a.name,
               l.debit - l.credit AS amount
        FROM journal_lines l
        JOIN accounts a ON a.id = l.account_id
        JOIN journal_entries e ON e.id = l.entry_id
        WHERE a.entity_id = :eid AND a.is_capex = 1"""
    params = {"eid": entity["id"]}
    if date_from:
        query += " AND e.date >= :dfrom"
        params["dfrom"] = date_from
    if date_to:
        query += " AND e.date <= :dto"
        params["dto"] = date_to
    query += " ORDER BY e.date"
    rows = conn.execute(query, params).fetchall()
    total = round(sum(r["amount"] for r in rows), 2)
    return {"items": rows, "total": total}


def intercompany_matrix(conn):
    """Net intercompany position per entity: receivables minus payables on
    intercompany accounts, per entity and (when set) per counterparty."""
    entities = list_entities(conn)
    positions = []
    for ent in entities:
        rows = conn.execute(
            """SELECT a.code, a.name, a.type, a.counterparty_entity_id,
                      COALESCE(SUM(l.debit - l.credit), 0) AS bal
               FROM accounts a
               LEFT JOIN journal_lines l ON l.account_id = a.id
               WHERE a.entity_id = ? AND a.is_intercompany = 1
               GROUP BY a.id""",
            (ent["id"],),
        ).fetchall()
        net = round(sum(r["bal"] for r in rows), 2)
        if rows:
            positions.append({"entity": ent, "net": net, "accounts": rows})
    return positions


def cash_pooling_overview(conn, as_of=None):
    """Cash per entity plus net intercompany position — the basis for a
    notional cash pool: who holds surplus cash, who is short."""
    entities = list_entities(conn)
    result = []
    for ent in entities:
        rows = _balances(conn, ent["id"], as_of=as_of)
        cash = round(sum(r["bal"] for r in rows if r["subtype"] == "cash"), 2)
        ic = round(sum(r["bal"] for r in rows if r["is_intercompany"]), 2)
        result.append({
            "entity": ent,
            "cash": cash,
            "intercompany_net": ic,
            "pooled_position": round(cash + ic, 2),
        })
    total_cash = round(sum(r["cash"] for r in result), 2)
    return {"entities": result, "total_cash": total_cash}
