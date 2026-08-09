"""Default chart of accounts seeded for every new entity.

Codes follow a conventional layout:
  1xxx assets, 2xxx liabilities, 3xxx equity, 4xxx income, 5xxx expenses,
  9xxx suspense/technical.
"""

# (code, name, type, subtype, is_capex, is_intercompany)
DEFAULT_CHART = [
    # Assets
    ("1000", "Cash at bank", "asset", "cash", 0, 0),
    ("1010", "Brokerage / trading account", "asset", "cash", 0, 0),
    ("1100", "Accounts receivable", "asset", "receivable", 0, 0),
    ("1200", "Intercompany receivable", "asset", "intercompany", 0, 1),
    ("1500", "Fixed assets - equipment", "asset", "fixed_asset", 1, 0),
    ("1510", "Fixed assets - IT & software", "asset", "fixed_asset", 1, 0),
    ("1590", "Accumulated depreciation", "asset", "contra", 0, 0),
    ("1800", "Prepaid expenses & deposits", "asset", "receivable", 0, 0),
    ("1900", "FX / internal transfer clearing", "asset", "clearing", 0, 0),
    # Liabilities
    ("2000", "Accounts payable", "liability", "payable", 0, 0),
    ("2100", "Intercompany payable", "liability", "intercompany", 0, 1),
    ("2200", "Loans payable", "liability", "financing", 0, 0),
    ("2300", "Taxes payable", "liability", "tax", 0, 0),
    ("2400", "Accrued expenses", "liability", "payable", 0, 0),
    # Equity
    ("3000", "Partner / shareholder capital", "equity", "financing", 0, 0),
    ("3100", "Retained earnings", "equity", "", 0, 0),
    ("3200", "Owner contributions / drawings", "equity", "financing", 0, 0),
    ("3900", "Opening balance equity", "equity", "", 0, 0),
    # Income
    ("4000", "Trading income", "income", "operating", 0, 0),
    ("4100", "Interest income", "income", "operating", 0, 0),
    ("4200", "FX gains", "income", "operating", 0, 0),
    ("4900", "Other income", "income", "", 0, 0),
    # Expenses
    ("5000", "Trading losses", "expense", "operating", 0, 0),
    ("5100", "Bank & broker fees", "expense", "operating", 0, 0),
    ("5200", "Professional services (legal, audit, accounting)", "expense", "operating", 0, 0),
    ("5300", "Office & administration", "expense", "operating", 0, 0),
    ("5400", "Salaries & social charges", "expense", "operating", 0, 0),
    ("5500", "Interest expense", "expense", "financing", 0, 0),
    ("5600", "Depreciation", "expense", "operating", 0, 0),
    ("5700", "FX losses", "expense", "operating", 0, 0),
    ("5800", "Subscriptions & data services", "expense", "operating", 0, 0),
    ("5900", "Other expenses", "expense", "", 0, 0),
    # Technical
    ("9000", "Suspense (to categorize)", "asset", "suspense", 0, 0),
]


def seed_chart(conn, entity_id: int) -> None:
    conn.executemany(
        """INSERT OR IGNORE INTO accounts
           (entity_id, code, name, type, subtype, is_capex, is_intercompany)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        [(entity_id, *row) for row in DEFAULT_CHART],
    )
    conn.commit()
