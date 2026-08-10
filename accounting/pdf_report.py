"""Classic accounting-package style PDF reports (balance sheet, P&L).

Layout: US Letter portrait; corner block with generation time/date and
basis; centered bold company name, report title and date line over a thick
rule; bold account tree indented ~11pt per level; regular-weight amounts
right-aligned in one or two date columns; a rule above every subtotal and
a double rule under grand totals; page number bottom right.
"""

from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas as rl_canvas

from .reports import _balances

PAGE_W, PAGE_H = letter          # 612 x 792
LEFT, RIGHT = 36, 576
BASE_X = 123                     # x of the outermost tree level
INDENT = 10.7
COL2_RIGHT = 489.0               # right edge of the last amount column
COL1_RIGHT = 416.0               # right edge of the first column (comparative)
COL_W = 63                       # width of the rule under/over amount columns
ROW_H = 9.6
SECTION_GAP = 7                  # extra space before sections and totals
HEADER_BOTTOM = 94              # first row's top coordinate
FOOTER_TOP = 745
NAME_MAX_RIGHT = 348             # truncate names that would hit the columns

FONT_B = "Helvetica-Bold"
FONT_R = "Helvetica"
SIZE = 8


def _fmt(value):
    return f"{value:,.2f}"


def _pretty_date(iso):
    return datetime.strptime(iso, "%Y-%m-%d").strftime("%B %d, %Y").replace(" 0", " ")


def _short_date(iso):
    d = datetime.strptime(iso, "%Y-%m-%d")
    return d.strftime("%b %d, %y").replace(" 0", " ")


class _Canvas:
    """Page state: header on every page, row cursor, pagination."""

    def __init__(self, path, company, title, subtitle, basis, col_heads):
        self.c = rl_canvas.Canvas(path, pagesize=letter)
        self.company = company.upper()
        self.title = title
        self.subtitle = subtitle
        self.basis = basis
        self.col_heads = col_heads       # list of 1 or 2 column headers
        self.last_kind = None
        self.now = datetime.now()
        self.page = 0
        self.top = None
        self._new_page()

    # y conversion: we track "top" coordinates like the design; reportlab
    # draws from the bottom.
    def _y(self, top):
        return PAGE_H - top

    def _new_page(self):
        if self.page > 0:
            self._footer()
            self.c.showPage()
        self.page += 1
        c = self.c
        c.setFont(FONT_B, SIZE)
        c.drawString(LEFT, self._y(48), self.now.strftime("%I:%M %p").lstrip("0"))
        c.drawString(LEFT, self._y(64), self.now.strftime("%m/%d/%y"))
        c.drawString(LEFT, self._y(76), self.basis)
        c.setFont(FONT_B, 12)
        c.drawCentredString(PAGE_W / 2, self._y(48), self.company)
        c.setFont(FONT_B, 14)
        c.drawCentredString(PAGE_W / 2, self._y(64), self.title)
        c.setFont(FONT_B, 10)
        c.drawCentredString(PAGE_W / 2, self._y(77), self.subtitle)
        c.setLineWidth(2)
        c.line(LEFT, self._y(84), RIGHT, self._y(84))
        # column headers
        c.setFont(FONT_B, SIZE)
        cols = self._col_rights()
        for head, right in zip(self.col_heads, cols):
            c.drawRightString(right, self._y(101), head)
            c.setLineWidth(1)
            c.line(right - COL_W, self._y(105), right, self._y(105))
        self.top = HEADER_BOTTOM + ROW_H

    def _col_rights(self):
        if len(self.col_heads) == 2:
            return [COL1_RIGHT, COL2_RIGHT]
        return [COL2_RIGHT]

    def _footer(self):
        self.c.setFont(FONT_B, SIZE)
        self.c.drawRightString(RIGHT, self._y(FOOTER_TOP + SIZE), f"Page {self.page}")

    def _advance(self, extra=0):
        self.top += ROW_H + extra
        if self.top > FOOTER_TOP - 6:
            self._new_page()

    def _truncate(self, text, x):
        while self.c.stringWidth(text, FONT_B, SIZE) > NAME_MAX_RIGHT - x and len(text) > 1:
            text = text[:-1]
        return text

    def row(self, label, level=0, amounts=None, kind="detail"):
        """kind: section | detail | total | grand"""
        if kind in ("total", "grand") or (
                kind == "section" and self.last_kind != "section"):
            self._advance(SECTION_GAP)
        else:
            self._advance()
        self.last_kind = kind
        c = self.c
        x = BASE_X + level * INDENT
        y = self._y(self.top)
        cols = self._col_rights()
        if kind in ("total", "grand"):
            c.setLineWidth(1)
            for right in cols[:len(amounts or [])]:
                c.line(right - COL_W, y + SIZE + 1, right, y + SIZE + 1)
        c.setFont(FONT_B, SIZE)
        c.drawString(x, y, self._truncate(label, x))
        if amounts is not None:
            c.setFont(FONT_B if kind == "grand" else FONT_R, SIZE)
            for value, right in zip(amounts, cols):
                c.drawRightString(right, y, _fmt(value))
        if kind == "grand":
            c.setLineWidth(1)
            for right in cols[:len(amounts or [])]:
                c.line(right - COL_W, y - 3, right, y - 3)
                c.line(right - COL_W, y - 5, right, y - 5)

    def save(self):
        self._footer()
        self.c.save()


# --------------------------------------------------------------- data prep

ASSET_GROUPS = [
    ("Checking/Savings", lambda a: a["subtype"] == "cash"),
    ("Other Current Assets",
     lambda a: a["subtype"] in ("receivable", "intercompany", "suspense",
                                "clearing", "investment")),
    ("Fixed Assets", lambda a: a["is_capex"] or a["subtype"] in
     ("fixed_asset", "contra")),
    ("Other Assets", lambda a: True),
]

LIABILITY_GROUPS = [
    ("Other Current Liabilities",
     lambda a: a["subtype"] in ("payable", "tax", "intercompany",
                                "investor", "")),
    ("Long Term Liabilities", lambda a: True),
]


def _collect(conn, entity, as_of, compare, currency):
    """Balances keyed by account code for each report column."""
    dates = [as_of] + ([compare] if compare else [])
    columns = []
    for d in dates:
        rows = _balances(conn, entity["id"], as_of=d)
        by_code = {}
        for r in rows:
            ccy = r["currency"] or entity["currency"]
            if ccy == currency:
                by_code[r["code"]] = r
        columns.append(by_code)
    # accounts present in any column, in code order
    codes = sorted({c for col in columns for c in col})
    meta = {}
    for col in columns:
        meta.update(col)
    return codes, [{c: col[c]["bal"] if c in col else 0.0 for c in codes}
                   for col in columns], meta


def _grouped(codes, meta, type_, groups):
    """Assign each account of a type to its first matching group."""
    result = {name: [] for name, _ in groups}
    for code in codes:
        acct = meta[code]
        if acct["type"] != type_:
            continue
        for name, test in groups:
            if test(acct):
                result[name].append(code)
                break
    return result


def balance_sheet_pdf(conn, entity, path, as_of, compare=None,
                      currency=None, basis="Cash Basis"):
    currency = currency or entity["currency"]
    codes, cols, meta = _collect(conn, entity, as_of, compare, currency)
    codes = [c for c in codes
             if any(round(col.get(c, 0.0), 2) != 0 for col in cols)]

    def bals(code, sign=1):
        return [round(sign * col.get(code, 0.0), 2) for col in cols]

    def total(code_list, sign=1):
        return [round(sum(sign * col.get(c, 0.0) for c in code_list), 2)
                for col in cols]

    heads = [_short_date(as_of)] + ([_short_date(compare)] if compare else [])
    subtitle = f"As of {_pretty_date(as_of)} ({currency})"
    doc = _Canvas(path, entity["name"], "Balance Sheet", subtitle, basis, heads)

    # ---- assets
    doc.row("ASSETS", 0, kind="section")
    asset_groups = _grouped(codes, meta, "asset", ASSET_GROUPS)
    current = (asset_groups["Checking/Savings"]
               + asset_groups["Other Current Assets"])
    doc.row("Current Assets", 1, kind="section")
    for group in ("Checking/Savings", "Other Current Assets"):
        members = asset_groups[group]
        if not members:
            continue
        doc.row(group, 2, kind="section")
        for code in members:
            doc.row(meta[code]["name"], 3, bals(code))
        doc.row(f"Total {group}", 2, total(members), kind="total")
    doc.row("Total Current Assets", 1, total(current), kind="total")
    for group in ("Fixed Assets", "Other Assets"):
        members = asset_groups[group]
        if not members:
            continue
        doc.row(group, 1, kind="section")
        for code in members:
            doc.row(meta[code]["name"], 2, bals(code))
        doc.row(f"Total {group}", 1, total(members), kind="total")
    all_assets = [c for c in codes if meta[c]["type"] == "asset"]
    doc.row("TOTAL ASSETS", 0, total(all_assets), kind="grand")

    # ---- liabilities & equity
    doc.row("LIABILITIES & EQUITY", 0, kind="section")
    doc.row("Liabilities", 1, kind="section")
    liability_groups = _grouped(codes, meta, "liability", LIABILITY_GROUPS)
    current_liabs = liability_groups["Other Current Liabilities"]
    if current_liabs:
        doc.row("Current Liabilities", 2, kind="section")
        doc.row("Other Current Liabilities", 3, kind="section")
        for code in current_liabs:
            doc.row(meta[code]["name"], 4, bals(code, sign=-1))
        doc.row("Total Other Current Liabilities", 3,
                total(current_liabs, sign=-1), kind="total")
        doc.row("Total Current Liabilities", 2,
                total(current_liabs, sign=-1), kind="total")
    long_term = liability_groups["Long Term Liabilities"]
    if long_term:
        doc.row("Long Term Liabilities", 2, kind="section")
        for code in long_term:
            doc.row(meta[code]["name"], 3, bals(code, sign=-1))
        doc.row("Total Long Term Liabilities", 2,
                total(long_term, sign=-1), kind="total")
    all_liabs = [c for c in codes if meta[c]["type"] == "liability"]
    doc.row("Total Liabilities", 1, total(all_liabs, sign=-1), kind="total")

    doc.row("Equity", 1, kind="section")
    equity_codes = [c for c in codes if meta[c]["type"] == "equity"]
    for code in equity_codes:
        doc.row(meta[code]["name"], 2, bals(code, sign=-1))
    pnl_codes = [c for c in codes
                 if meta[c]["type"] in ("income", "expense")]
    net_income = total(pnl_codes, sign=-1)
    doc.row("Net Income", 2, net_income)
    total_equity = [round(a + b, 2) for a, b in
                    zip(total(equity_codes, sign=-1), net_income)]
    doc.row("Total Equity", 1, total_equity, kind="total")
    total_le = [round(a + b, 2) for a, b in
                zip(total(all_liabs, sign=-1), total_equity)]
    doc.row("TOTAL LIABILITIES & EQUITY", 0, total_le, kind="grand")

    doc.save()
    return path


def pnl_pdf(conn, entity, path, date_from, date_to,
            currency=None, basis="Cash Basis"):
    currency = currency or entity["currency"]
    rows = _balances(conn, entity["id"], as_of=date_to, date_from=date_from)
    income, expenses = [], []
    for r in rows:
        ccy = r["currency"] or entity["currency"]
        if ccy != currency or round(r["bal"], 2) == 0:
            continue
        if r["type"] == "income":
            income.append((r["name"], round(-r["bal"], 2)))
        elif r["type"] == "expense":
            expenses.append((r["name"], round(r["bal"], 2)))

    subtitle = (f"{_pretty_date(date_from)} through {_pretty_date(date_to)}"
                f" ({currency})")
    head = f"{_short_date(date_from)} - {_short_date(date_to)}"
    doc = _Canvas(path, entity["name"], "Profit & Loss", subtitle, basis,
                  [head])

    doc.row("Ordinary Income/Expense", 0, kind="section")
    doc.row("Income", 1, kind="section")
    for name, value in income:
        doc.row(name, 2, [value])
    total_income = round(sum(v for _, v in income), 2)
    doc.row("Total Income", 1, [total_income], kind="total")
    doc.row("Expense", 1, kind="section")
    for name, value in expenses:
        doc.row(name, 2, [value])
    total_expenses = round(sum(v for _, v in expenses), 2)
    doc.row("Total Expense", 1, [total_expenses], kind="total")
    doc.row("Net Ordinary Income", 0,
            [round(total_income - total_expenses, 2)], kind="total")
    doc.row("Net Income", 0, [round(total_income - total_expenses, 2)],
            kind="grand")

    doc.save()
    return path


def currencies_in_use(conn, entity):
    rows = _balances(conn, entity["id"])
    seen = []
    for r in rows:
        ccy = r["currency"] or entity["currency"]
        if round(r["bal"], 2) != 0 and ccy not in seen:
            seen.append(ccy)
    return seen or [entity["currency"]]


def journal_pdf(conn, entity, path, date_from=None, date_to=None):
    """Numbered transaction register for line-by-line review."""
    from .reports import journal
    rows = journal(conn, entity, date_from=date_from, date_to=date_to)
    period = f"{date_from or 'start'} to {date_to or 'today'}"
    doc = _Canvas(path, entity["name"], "Transaction Register",
                  f"For review - {period}", "All accounts", [])
    c = doc.c
    y_cols = {"num": 38, "date": 64, "desc": 112, "counter": 330,
              "amount_r": 523, "ccy": 528}
    doc.top = HEADER_BOTTOM
    for i, (eid_, date, desc, amount, ccy, counter) in enumerate(rows):
        doc._advance()
        y = doc._y(doc.top)
        c.setFont(FONT_B, 7)
        c.drawString(y_cols["num"], y, f"#{eid_}")
        c.setFont(FONT_R, 7)
        c.drawString(y_cols["date"], y, date)
        label = desc
        while c.stringWidth(label, FONT_R, 7) > 212 and len(label) > 1:
            label = label[:-1]
        c.drawString(y_cols["desc"], y, label)
        clabel = counter
        while c.stringWidth(clabel, FONT_R, 7) > 125 and len(clabel) > 1:
            clabel = clabel[:-1]
        c.drawString(y_cols["counter"], y, clabel)
        c.drawRightString(y_cols["amount_r"], y, _fmt(amount))
        c.drawString(y_cols["ccy"], y, ccy)
    doc.save()
    return path


def cash_flow_pdf(conn, entity, path, date_from, date_to, currency=None,
                  basis="Cash Basis"):
    from .reports import cash_flow
    currency = currency or entity["currency"]
    flows = cash_flow(conn, entity, date_from=date_from, date_to=date_to)
    data = flows.get(currency)
    subtitle = (f"{_pretty_date(date_from)} through {_pretty_date(date_to)}"
                f" ({currency})")
    doc = _Canvas(path, entity["name"], "Statement of Cash Flows", subtitle,
                  basis, [f"{_short_date(date_from)} - {_short_date(date_to)}"])
    if not data:
        doc.row("No cash movements in the period.", 0)
        doc.save()
        return path
    labels = {"operating": "OPERATING ACTIVITIES",
              "investing": "INVESTING ACTIVITIES",
              "financing": "FINANCING ACTIVITIES"}
    for bucket in ("operating", "investing", "financing"):
        doc.row(labels[bucket], 0, kind="section")
        for date, desc, delta in data["details"][bucket]:
            doc.row(f"{date}  {desc}", 1, [delta])
        doc.row(f"Net cash from {bucket} activities", 0,
                [data[bucket]], kind="total")
    doc.row("NET CHANGE IN CASH", 0, [data["net_change"]], kind="grand")
    doc.save()
    return path


def equity_changes_pdf(conn, entity, path, date_from, date_to,
                       basis="Cash Basis"):
    from .reports import equity_changes
    data = equity_changes(conn, entity, date_from, date_to)
    subtitle = f"{_pretty_date(date_from)} through {_pretty_date(date_to)}"
    doc = _Canvas(path, entity["name"], "Statement of Changes in Equity",
                  subtitle, basis, [])
    for ccy, row in data.items():
        doc.row(f"EQUITY ({ccy})", 0, kind="section")
        doc.row(f"Equity at {_pretty_date(date_from)} (opening)", 1,
                [row["opening"]])
        doc.row("Partner capital contributions / withdrawals", 1,
                [row["capital_movements"]])
        doc.row("Net result for the period", 1, [row["net_result"]])
        doc.row(f"Equity at {_pretty_date(date_to)} (closing)", 1,
                [row["closing"]], kind="grand")
    doc.save()
    return path


def notes_pdf(entity, path, as_of, sections, basis="Cash Basis"):
    """sections: list of (heading, [paragraph, ...])."""
    doc = _Canvas(path, entity["name"], "Notes to the Financial Statements",
                  f"As of {_pretty_date(as_of)}", basis, [])
    c = doc.c
    n = 0
    for heading, paragraphs in sections:
        n += 1
        doc._advance(SECTION_GAP)
        c.setFont(FONT_B, 9)
        c.drawString(BASE_X - 60, doc._y(doc.top), f"{n}. {heading}")
        c.setFont(FONT_R, 8)
        for para in paragraphs:
            words = para.split()
            line = ""
            for w in words:
                test = (line + " " + w).strip()
                if c.stringWidth(test, FONT_R, 8) > 440:
                    doc._advance()
                    c.setFont(FONT_R, 8)
                    c.drawString(BASE_X - 50, doc._y(doc.top), line)
                    line = w
                else:
                    line = test
            if line:
                doc._advance()
                c.setFont(FONT_R, 8)
                c.drawString(BASE_X - 50, doc._y(doc.top), line)
            doc._advance(2)
    doc.save()
    return path
