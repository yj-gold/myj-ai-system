"""Core ledger operations: entities, accounts, journal entries."""

from .chart import seed_chart


class LedgerError(Exception):
    pass


# ---------------------------------------------------------------- entities

def add_entity(conn, code, name, currency="EUR", country=""):
    cur = conn.execute(
        "INSERT INTO entities (code, name, currency, country) VALUES (?, ?, ?, ?)",
        (code.upper(), name, currency.upper(), country),
    )
    entity_id = cur.lastrowid
    seed_chart(conn, entity_id)
    conn.commit()
    return entity_id


def get_entity(conn, code):
    row = conn.execute(
        "SELECT * FROM entities WHERE code = ?", (code.upper(),)
    ).fetchone()
    if row is None:
        raise LedgerError(
            f"Unknown entity '{code}'. Add it first: entity add {code} \"Name\""
        )
    return row


def list_entities(conn):
    return conn.execute("SELECT * FROM entities ORDER BY code").fetchall()


# ---------------------------------------------------------------- accounts

def get_account(conn, entity_id, code):
    row = conn.execute(
        "SELECT * FROM accounts WHERE entity_id = ? AND code = ?",
        (entity_id, str(code)),
    ).fetchone()
    if row is None:
        raise LedgerError(f"Unknown account code '{code}' for this entity.")
    return row


def list_accounts(conn, entity_id):
    return conn.execute(
        "SELECT * FROM accounts WHERE entity_id = ? ORDER BY code", (entity_id,)
    ).fetchall()


def add_account(conn, entity_id, code, name, type_, subtype="",
                is_capex=0, is_intercompany=0, counterparty_entity_id=None):
    if type_ not in ("asset", "liability", "equity", "income", "expense"):
        raise LedgerError(
            "Account type must be one of: asset, liability, equity, income, expense"
        )
    cur = conn.execute(
        """INSERT INTO accounts
           (entity_id, code, name, type, subtype, is_capex, is_intercompany,
            counterparty_entity_id)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (entity_id, str(code), name, type_, subtype,
         int(is_capex), int(is_intercompany), counterparty_entity_id),
    )
    conn.commit()
    return cur.lastrowid


# ---------------------------------------------------------------- entries

def add_entry(conn, entity_id, date, description, lines, reference="",
              source="manual"):
    """Add a balanced journal entry.

    lines: list of (account_code, debit, credit, memo) tuples.
    """
    total_debit = round(sum(l[1] for l in lines), 2)
    total_credit = round(sum(l[2] for l in lines), 2)
    if abs(total_debit - total_credit) > 0.005:
        raise LedgerError(
            f"Entry does not balance: debits {total_debit} != credits {total_credit}"
        )
    if total_debit == 0:
        raise LedgerError("Entry has zero amount.")

    cur = conn.execute(
        """INSERT INTO journal_entries (entity_id, date, description, reference, source)
           VALUES (?, ?, ?, ?, ?)""",
        (entity_id, date, description, reference, source),
    )
    entry_id = cur.lastrowid
    for code, debit, credit, memo in lines:
        account = get_account(conn, entity_id, code)
        conn.execute(
            """INSERT INTO journal_lines (entry_id, account_id, debit, credit, memo)
               VALUES (?, ?, ?, ?, ?)""",
            (entry_id, account["id"], round(debit, 2), round(credit, 2), memo),
        )
    conn.commit()
    return entry_id


def account_balance(conn, account_id, as_of=None):
    """Debit-positive balance of an account (assets/expenses positive when
    debit-heavy; liabilities/equity/income positive when credit-heavy is
    handled by callers via sign convention)."""
    query = """SELECT COALESCE(SUM(l.debit - l.credit), 0) AS bal
               FROM journal_lines l
               JOIN journal_entries e ON e.id = l.entry_id
               WHERE l.account_id = ?"""
    params = [account_id]
    if as_of:
        query += " AND e.date <= ?"
        params.append(as_of)
    return conn.execute(query, params).fetchone()["bal"]
