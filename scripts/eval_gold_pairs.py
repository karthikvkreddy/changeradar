#!/usr/bin/env python3
"""Back-compat wrapper — prefer: python -m changeradar eval --suite public"""

from changeradar.cli import main

raise SystemExit(main(["eval", "--suite", "public"]))
