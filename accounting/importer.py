"""CSV statement import with rule-based categorization.

Works with most bank/broker CSV exports. Column names are auto-detected from
common headers, or can be forced with explicit options. Each transaction
becomes a balanced journal entry against the chosen cash account; the
counter-account is picked by categorization rules, falling back to the
suspense account (9000) so nothing is silently misclassified.
"""

import csv
import re
from datetime import datetime

from .ledger import add_entry, get_account, LedgerError

DATE_HEADERS = ("date", "transaction date", "booking date", "value date",
                "datum", "fecha", "data")
DESC_HEADERS = ("description", "label", "narrative", "details", "reference",
                "libelle", "libellé", "memo", "text", "counterparty")
AMOUNT_HEADERS = ("amount", "montant", "value", "betrag", "importe")
DEBIT_HEADERS = ("debit", "débit", "withdrawal", "money out", "out")
CREDIT_HEADERS = ("credit", "crédit", "deposit", "money in", "in")
BALANCE_HEADERS = ("balance", "solde", "saldo", "running balance")
CURRENCY_HEADERS = ("currency", "devise", "ccy")

DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y",
                "%m/%d/%Y", "%Y/%m/%d", "%d %b %Y", "%d %B %Y")

# Sensible default rules applied to every entity (substring, account code).
DEFAULT_RULES = [
    ("interest", "4100"),
    ("dividend", "4900"),
    ("fee", "5100"),
    ("commission", "5100"),
    ("bank charge", "5100"),
    ("salary", "5400"),
    ("payroll", "5400"),
    ("tax", "2300"),
    ("tva", "2300"),
    ("vat", "2300"),
    ("rent", "5300"),
    ("subscription", "5800"),
    ("bloomberg", "5800"),
    ("refinitiv", "5800"),
    ("audit", "5200"),
    ("legal", "5200"),
    ("notary", "5200"),
]


def _find_column(headers, candidates):
    lowered = {h.lower().strip(): h for h in headers}
    for cand in candidates:
        if cand in lowered:
            return lowered[cand]
    for cand in candidates:
        for low, orig in lowered.items():
            if cand in low:
                return orig
    return None


def _parse_date(value):
    value = value.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    raise LedgerError(f"Unrecognized date format: '{value}'")


def _parse_amount(value):
    """Handle 1,234.56 / 1.234,56 / (123.45) / -123,45 / €1 234,56."""
    value = value.strip().replace(" ", "").replace(" ", "")
    if not value:
        return 0.0
    negative = value.startswith("(") and value.endswith(")")
    value = value.strip("()")
    value = re.sub(r"[^\d,.\-+]", "", value)
    if "," in value and "." in value:
        if value.rfind(",") > value.rfind("."):
            value = value.replace(".", "").replace(",", ".")  # 1.234,56
        else:
            value = value.replace(",", "")                    # 1,234.56
    elif "," in value:
        # single comma with 1-2 trailing digits -> decimal comma
        if re.search(r",\d{1,2}$", value):
            value = value.replace(",", ".")
        else:
            value = value.replace(",", "")
    result = float(value) if value not in ("", "-", "+") else 0.0
    return -result if negative else result


def load_rules(conn, entity_id):
    """User rules (entity-specific first, then global), then built-in defaults."""
    rows = conn.execute(
        """SELECT pattern, account_code FROM categorization_rules
           WHERE entity_id = ? OR entity_id IS NULL
           ORDER BY entity_id IS NULL, id""",
        (entity_id,),
    ).fetchall()
    rules = [(r["pattern"], r["account_code"]) for r in rows]
    rules.extend(DEFAULT_RULES)
    return rules


def categorize(description, amount, rules):
    """Return counter-account code for a transaction, or None."""
    desc = description.lower()
    for pattern, code in rules:
        if pattern.startswith("/") and pattern.endswith("/") and len(pattern) > 2:
            if re.search(pattern[1:-1], description, re.IGNORECASE):
                return code
        elif pattern.lower() in desc:
            return code
    return None


def import_csv(conn, entity, filepath, cash_account_code="1000",
               date_col=None, desc_col=None, amount_col=None,
               debit_col=None, credit_col=None, delimiter=None):
    """Import a bank/broker statement CSV for an entity.

    Returns (statement_id, imported_count, uncategorized_count).
    """
    entity_id = entity["id"]
    get_account(conn, entity_id, cash_account_code)  # validate early
    rules = load_rules(conn, entity_id)

    with open(filepath, newline="", encoding="utf-8-sig") as f:
        sample = f.read(4096)
        f.seek(0)
        if delimiter is None:
            try:
                delimiter = csv.Sniffer().sniff(sample, delimiters=",;\t").delimiter
            except csv.Error:
                delimiter = ","
        reader = csv.DictReader(f, delimiter=delimiter)
        headers = reader.fieldnames or []

        date_col = date_col or _find_column(headers, DATE_HEADERS)
        desc_col = desc_col or _find_column(headers, DESC_HEADERS)
        amount_col = amount_col or _find_column(headers, AMOUNT_HEADERS)
        if debit_col is None and credit_col is None and amount_col is None:
            debit_col = _find_column(headers, DEBIT_HEADERS)
            credit_col = _find_column(headers, CREDIT_HEADERS)
        balance_col = _find_column(headers, BALANCE_HEADERS)
        currency_col = _find_column(headers, CURRENCY_HEADERS)

        if date_col is None or (amount_col is None and debit_col is None):
            raise LedgerError(
                f"Could not detect columns in {filepath} (headers: {headers}). "
                "Specify them with --date-col / --amount-col or --debit-col/--credit-col."
            )

        cur = conn.execute(
            """INSERT INTO statements (entity_id, filename, cash_account_code)
               VALUES (?, ?, ?)""",
            (entity_id, filepath, cash_account_code),
        )
        statement_id = cur.lastrowid

        imported = 0
        uncategorized = 0
        for row in reader:
            raw_date = (row.get(date_col) or "").strip()
            if not raw_date:
                continue
            date = _parse_date(raw_date)
            description = (row.get(desc_col) or "").strip() if desc_col else ""

            if amount_col:
                amount = _parse_amount(row.get(amount_col) or "")
            else:
                debit = _parse_amount(row.get(debit_col) or "") if debit_col else 0.0
                credit = _parse_amount(row.get(credit_col) or "") if credit_col else 0.0
                # statement debit = money out -> negative
                amount = credit - abs(debit)
            if amount == 0:
                continue

            counter = categorize(description, amount, rules)
            if counter is None:
                counter = "9000"
                uncategorized += 1

            if amount > 0:  # money in: debit cash, credit counter-account
                lines = [(cash_account_code, amount, 0, description),
                         (counter, 0, amount, description)]
            else:           # money out: credit cash, debit counter-account
                lines = [(counter, -amount, 0, description),
                         (cash_account_code, 0, -amount, description)]

            entry_id = add_entry(conn, entity_id, date, description,
                                 lines, reference=f"stmt:{statement_id}",
                                 source="import")

            balance_after = None
            if balance_col and (row.get(balance_col) or "").strip():
                balance_after = _parse_amount(row[balance_col])
            currency = (row.get(currency_col) or "").strip() if currency_col else ""
            conn.execute(
                """INSERT INTO statement_transactions
                   (statement_id, date, description, amount, currency,
                    balance_after, matched_account_code, entry_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (statement_id, date, description, amount, currency,
                 balance_after, counter, entry_id),
            )
            imported += 1

        conn.execute("UPDATE statements SET tx_count = ? WHERE id = ?",
                     (imported, statement_id))
        conn.commit()

    return statement_id, imported, uncategorized


def add_rule(conn, pattern, account_code, entity_id=None, note=""):
    conn.execute(
        """INSERT INTO categorization_rules (entity_id, pattern, account_code, note)
           VALUES (?, ?, ?, ?)""",
        (entity_id, pattern, account_code, note),
    )
    conn.commit()


def recategorize_suspense(conn, entity):
    """Re-apply rules to entries currently sitting in suspense (9000)."""
    entity_id = entity["id"]
    rules = load_rules(conn, entity_id)
    suspense = get_account(conn, entity_id, "9000")
    rows = conn.execute(
        """SELECT l.id AS line_id, l.debit, l.credit, e.description
           FROM journal_lines l
           JOIN journal_entries e ON e.id = l.entry_id
           WHERE l.account_id = ? AND e.entity_id = ?""",
        (suspense["id"], entity_id),
    ).fetchall()
    moved = 0
    for row in rows:
        amount = row["debit"] - row["credit"]
        code = categorize(row["description"], amount, rules)
        if code and code != "9000":
            account = get_account(conn, entity_id, code)
            conn.execute("UPDATE journal_lines SET account_id = ? WHERE id = ?",
                         (account["id"], row["line_id"]))
            conn.execute(
                """UPDATE statement_transactions SET matched_account_code = ?
                   WHERE entry_id = (SELECT entry_id FROM journal_lines WHERE id = ?)""",
                (code, row["line_id"]),
            )
            moved += 1
    conn.commit()
    return moved
