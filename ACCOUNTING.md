# MYJ Private Accounting Tool

A local-first, multi-entity, double-entry accounting tool. Import bank and
broker statements, and get balance sheets, P&L, cash flow, a CAPEX register,
and an intercompany / cash-pooling overview across all your companies.

## Privacy & security

- **All data stays on your machine.** Everything lives in a single SQLite file
  at `accounting_data/ledger.db`. Nothing is sent to any external service.
- **Nothing private is ever committed to git.** `accounting_data/`,
  `statements/`, and all `*.db` files are git-ignored. Only the code is in
  the repository — never your figures or statements.
- The data directory and database file are created with owner-only
  permissions (`0700` / `0600`).
- To move the data elsewhere (e.g. an encrypted volume), set
  `ACCOUNTING_DATA_DIR=/path/to/secure/location`. For encryption at rest,
  keep the data directory on an encrypted disk/volume (FileVault, LUKS,
  BitLocker, or an encrypted container such as VeraCrypt).
- Back up `accounting_data/ledger.db` regularly — it is the single source of
  truth.

## Quick start

```bash
# 1. Create your first entity
python myj_accounting.py entity add MYJCT "MYJ Currency Trading S.C.Sp." --currency EUR --country LU

# 2. Import a bank statement CSV (auto-detects date/description/amount columns)
python myj_accounting.py import statements/bank_2026_07.csv --entity MYJCT

# For a broker statement, book it against the brokerage cash account:
python myj_accounting.py import statements/ig_2026_07.csv --entity MYJCT --cash-account 1010

# 3. Reports
python myj_accounting.py report balance-sheet --entity MYJCT
python myj_accounting.py report pnl --entity MYJCT --date-from 2026-01-01
python myj_accounting.py report cashflow --entity MYJCT --detail
python myj_accounting.py report capex --entity MYJCT
python myj_accounting.py report pooling          # all entities
python myj_accounting.py report intercompany     # all entities
```

## Adding more companies

```bash
python myj_accounting.py entity add MYJHOLD "MYJ Holding" --currency EUR
python myj_accounting.py entity list
```

Every entity gets its own standard chart of accounts (see below) and its own
ledger; reports like `pooling` and `intercompany` look across all of them.

## Opening balances (starting the books, e.g. as of 2016)

Book the position each entity had on day one; the history you import then
builds on top of it. Enter balances as they appear on the balance sheet
(positive numbers) — the tool picks the right debit/credit side and books
any difference to `3900 Opening balance equity`:

```bash
# As of 1 Jan 2016: 100k in the bank, 25k at the broker, a 30k loan
python myj_accounting.py opening --entity MYJCT --date 2016-01-01 \
    1000:100000 1010:25000 2200:30000
```

If you know the split of equity (capital vs. retained earnings), book those
accounts explicitly instead of letting it fall into 3900.

## Importing statements

The importer accepts most bank/broker CSV exports. It auto-detects common
column names (date, description, amount — or separate debit/credit columns,
balance, currency) in English, French, German and Spanish, and handles both
`1,234.56` and `1.234,56` number formats. If detection fails, force columns:

```bash
python myj_accounting.py import file.csv --entity MYJCT \
    --date-col "Booking date" --desc-col "Narrative" --amount-col "Value" \
    --delimiter ";"
```

Each transaction becomes a balanced double-entry: the cash account on one
side, a category account on the other. Categories are chosen by rules
matching the transaction description; anything unmatched goes to the
**suspense account 9000** so you can see exactly what still needs a category:

```bash
# 'IG Markets' in the description -> trading income account
python myj_accounting.py rule add "IG Markets" 4000 --entity MYJCT
# regex rules also work
python myj_accounting.py rule add "/AWS|OVH|HETZNER/" 5800
# re-run the rules over anything sitting in suspense
python myj_accounting.py recategorize --entity MYJCT
```

PDF statements: export/convert them to CSV first (most banks offer CSV
export), or send the rows through a manual journal entry.

## Multiple currencies

Accounts are single-currency; each currency gets its own sub-account
automatically (e.g. `1000.USD`, `4000.USD`) and all reports show per-currency
figures — amounts in different currencies are never summed together.

- The importer picks the currency from (in order): `--currency FLAG`, a
  currency column in the file, or the entity's base currency.
- For transfers between your own accounts in different currencies, route
  both legs to `1900 FX / internal transfer clearing` with a rule; whatever
  balance remains on 1900 after both legs is the FX effect, which you can
  clear to `4200 FX gains` / `5700 FX losses` periodically:

```bash
python myj_accounting.py rule add "Transfer to USD account" 1900 --entity MYJCT
python myj_accounting.py rule add "Incoming transfer from EUR" 1900 --entity MYJCT
```

## Starting from statements only (no separate opening figures)

If all you have is statements, import the oldest statement of each account
with `--opening-from-balance`: the opening balance is derived from the first
row's running balance (balance minus that row's amount) and booked to
`3900 Opening balance equity` automatically:

```bash
python myj_accounting.py import statements/bank_2016.csv --entity MYJCT \
    --cash-account 1000 --opening-from-balance
```

Use the flag only on the oldest statement of each account, then import the
later statements normally in chronological order.

## Manual journal entries

Format: `ACCOUNT:AMOUNT[:memo]`, positive = debit, negative = credit; the
lines must balance to zero.

```bash
# Bought a server for 2,500 paid from the bank -> CAPEX
python myj_accounting.py entry add --entity MYJCT --date 2026-08-01 \
    --description "Dell server" 1510:2500 1000:-2500

# Intercompany loan: MYJCT lends 50,000 to MYJHOLD
python myj_accounting.py entry add --entity MYJCT --date 2026-08-01 \
    --description "IC loan to MYJHOLD" 1200:50000 1000:-50000
python myj_accounting.py entry add --entity MYJHOLD --date 2026-08-01 \
    --description "IC loan from MYJCT" 1000:50000 2100:-50000
```

## Chart of accounts (per entity)

| Range | Type | Notable accounts |
|-------|------|------------------|
| 1xxx | Assets | 1000 bank, 1010 brokerage, 1200 intercompany receivable, 1500/1510 fixed assets (CAPEX), 1590 accumulated depreciation |
| 2xxx | Liabilities | 2000 payables, 2100 intercompany payable, 2200 loans, 2300 taxes |
| 3xxx | Equity | 3000 capital, 3100 retained earnings |
| 4xxx | Income | 4000 trading income, 4100 interest, 4200 FX gains |
| 5xxx | Expenses | 5000 trading losses, 5100 bank/broker fees, 5600 depreciation |
| 9000 | Suspense | uncategorized imports land here |

Add custom accounts as needed:

```bash
python myj_accounting.py account add 1520 "Vehicles" asset --entity MYJCT --capex
python myj_accounting.py account add 1210 "IC receivable - MYJHOLD" asset \
    --entity MYJCT --counterparty MYJHOLD
```

## What the reports tell you

- **balance-sheet** — assets, liabilities, equity, and net worth as of a
  date. Period profit is folded into equity so it always balances.
- **pnl** — income vs. expenses for a period; where the money is made and
  where it leaks (fees, subscriptions, services).
- **cashflow** — cash movement split into operating / investing (CAPEX) /
  financing, with `--detail` for the underlying transactions.
- **capex** — every fixed-asset movement, so you can track investment spend
  and plan depreciation.
- **pooling** — cash and net intercompany position per entity, and flags
  when surplus entities could fund deficit entities via documented
  intercompany loans (keep terms at arm's length for tax purposes).
- **intercompany** — receivable/payable detail between your entities;
  positions should mirror each other and net to zero across the group.

> Note: this tool is for management accounting and decision-making. For
> statutory filings (e.g. Luxembourg S.C.Sp. requirements), have your
> accountant review the figures.
