#!/usr/bin/env python3

from __future__ import annotations

import sys

from amr_warehouse_sim import mock_wms_api as _pkg

# Re-export package symbols so tests and other code that import
# scripts/mock_wms_api.py get the expected `create_app` and parser helpers.
create_app = _pkg.create_app
build_parser = _pkg.build_parser
main = _pkg.main


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
