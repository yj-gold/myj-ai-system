"""MYJ private accounting module.

Local-first, multi-entity double-entry accounting:
- Entities (companies) with their own chart of accounts and base currency
- Bank/broker statement import (CSV) with rule-based categorization
- Balance sheet, income statement, cash flow, CAPEX register
- Intercompany positions and cash-pooling overview

All data is stored in a local SQLite database (default: ./accounting_data/),
which is excluded from git. Nothing is sent to any external service.
"""

__version__ = "0.1.0"
