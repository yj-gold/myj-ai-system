#!/usr/bin/env python3
"""Entry point for the MYJ private accounting tool.

Usage examples:
  python myj_accounting.py entity add MYJCT "MYJ Currency Trading S.C.Sp." --currency EUR
  python myj_accounting.py import statement.csv --entity MYJCT --cash-account 1010
  python myj_accounting.py report balance-sheet --entity MYJCT
  python myj_accounting.py report pooling

See ACCOUNTING.md for the full guide.
"""

import sys

from accounting.cli import main

if __name__ == "__main__":
    sys.exit(main())
