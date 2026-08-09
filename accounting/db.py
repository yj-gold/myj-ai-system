"""SQLite storage for the accounting module.

The database lives in a local directory (default ./accounting_data) that is
git-ignored. File permissions are restricted to the owner on creation.
"""

import os
import sqlite3

DATA_DIR = os.getenv("ACCOUNTING_DATA_DIR", "./accounting_data")
DB_PATH = os.path.join(DATA_DIR, "ledger.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS entities (
    id INTEGER PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    currency TEXT NOT NULL DEFAULT 'EUR',
    country TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY,
    entity_id INTEGER NOT NULL REFERENCES entities(id),
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    -- asset / liability / equity / income / expense
    type TEXT NOT NULL,
    -- free-form refinement: cash, receivable, payable, intercompany,
    -- fixed_asset, financing, tax, operating, contra ...
    subtype TEXT DEFAULT '',
    is_capex INTEGER NOT NULL DEFAULT 0,
    is_intercompany INTEGER NOT NULL DEFAULT 0,
    -- for intercompany accounts: which entity is on the other side
    counterparty_entity_id INTEGER REFERENCES entities(id),
    -- empty means the entity's base currency
    currency TEXT DEFAULT '',
    UNIQUE (entity_id, code)
);

CREATE TABLE IF NOT EXISTS journal_entries (
    id INTEGER PRIMARY KEY,
    entity_id INTEGER NOT NULL REFERENCES entities(id),
    date TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    reference TEXT DEFAULT '',
    source TEXT NOT NULL DEFAULT 'manual',  -- manual / import
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS journal_lines (
    id INTEGER PRIMARY KEY,
    entry_id INTEGER NOT NULL REFERENCES journal_entries(id) ON DELETE CASCADE,
    account_id INTEGER NOT NULL REFERENCES accounts(id),
    debit REAL NOT NULL DEFAULT 0,
    credit REAL NOT NULL DEFAULT 0,
    memo TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS statements (
    id INTEGER PRIMARY KEY,
    entity_id INTEGER NOT NULL REFERENCES entities(id),
    filename TEXT NOT NULL,
    cash_account_code TEXT NOT NULL,
    imported_at TEXT NOT NULL DEFAULT (datetime('now')),
    tx_count INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS statement_transactions (
    id INTEGER PRIMARY KEY,
    statement_id INTEGER NOT NULL REFERENCES statements(id) ON DELETE CASCADE,
    date TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    amount REAL NOT NULL,
    currency TEXT DEFAULT '',
    balance_after REAL,
    matched_account_code TEXT DEFAULT '',
    entry_id INTEGER REFERENCES journal_entries(id)
);

CREATE TABLE IF NOT EXISTS categorization_rules (
    id INTEGER PRIMARY KEY,
    -- entity_id NULL means the rule applies to all entities
    entity_id INTEGER REFERENCES entities(id),
    pattern TEXT NOT NULL,          -- case-insensitive substring or /regex/
    account_code TEXT NOT NULL,     -- counter-account for matching transactions
    note TEXT DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_lines_account ON journal_lines(account_id);
CREATE INDEX IF NOT EXISTS idx_entries_entity_date ON journal_entries(entity_id, date);
"""


def connect(db_path: str = None) -> sqlite3.Connection:
    """Open (and initialize if needed) the local accounting database."""
    path = db_path or DB_PATH
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, mode=0o700, exist_ok=True)
    created = not os.path.exists(path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    # Migrations for databases created by earlier versions
    account_cols = [r[1] for r in conn.execute("PRAGMA table_info(accounts)")]
    if "currency" not in account_cols:
        # empty currency means the entity's base currency
        conn.execute("ALTER TABLE accounts ADD COLUMN currency TEXT DEFAULT ''")
        conn.commit()
    if created:
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
    return conn
