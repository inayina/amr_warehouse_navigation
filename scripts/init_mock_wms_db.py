#!/usr/bin/env python3

from __future__ import annotations

import sys

from amr_warehouse_sim.init_mock_wms_db import main


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
